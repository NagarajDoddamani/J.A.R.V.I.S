"""JARVIS service-owned schemas and foundation entities (JDOS v1.2).

This single foundation migration establishes:

* The shared ``platform`` schema hosting the ``pgcrypto`` extension and
  a deterministic ``uuidv7()`` generator used as the default primary
  key for every foundation table.
* Six service-owned PostgreSQL schemas, one per bounded service
  (``orchestration``, ``memory``, ``knowledge``, ``notification``,
  ``settings``, ``audit``).
* An outbox and inbox table inside every service schema, providing
  the durable transport surfaces the application layer will use in
  later phases.
* The first foundation entities:

    - ``memory.memories``
    - ``memory.consent_records``
    - ``audit.audit_entries``
    - ``audit.audit_chain_heads``
    - ``settings.user_settings``

Per the JDOS v1.2 architecture corrections:

* Memory consent is explicit and active before any memory becomes
  active (Correction 3).
* Audit is append-only, hash-chained, and content-minimized
  (Correction 8).
* Settings owns the ``settings`` schema and is the only writer
  (Correction 7).
* Sensitive payload columns are explicitly classified in this
  migration (database_strategy.md).

This migration contains **no business logic**; no repositories, no
use cases, no API routes.

Revision ID: 743a95f81f31
Revises:
Create Date: 2026-06-07 13:09:18.173802
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "743a95f81f31"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Service schema registry
# ---------------------------------------------------------------------------

SERVICE_SCHEMAS: tuple[str, ...] = (
    "orchestration",
    "memory",
    "knowledge",
    "notification",
    "settings",
    "audit",
)

# Per-service role names (JDOS v1.2, Corrections 7 & 8). Roles are
# created with NOLOGIN so the dev path may continue to connect as the
# schema-owning ``jarvis_admin`` user while production paths grant
# these roles to per-service application users.
SERVICE_ROLES: dict[str, str] = {
    "orchestration": "jarvis_orchestration_app",
    "memory": "jarvis_memory_app",
    "knowledge": "jarvis_knowledge_app",
    "notification": "jarvis_notification_app",
    "settings": "jarvis_settings_app",
    "audit": "jarvis_audit_app",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _exec(sql: str) -> None:
    op.execute(sql)


def _create_schemas() -> None:
    for schema in SERVICE_SCHEMAS:
        _exec(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')


def _create_roles() -> None:
    for role in SERVICE_ROLES.values():
        # Roles are created NOLOGIN; production deployment grants the
        # role to a per-service application user. Idempotent guard.
        _exec(
            f"DO $$ BEGIN "
            f"IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN "
            f"CREATE ROLE \"{role}\" NOLOGIN; "
            f"END IF; "
            f"END $$;"
        )


def _grant_schema_privileges() -> None:
    """Apply least-privilege grants: USAGE only on the per-service schema."""
    for schema, role in SERVICE_ROLES.items():
        _exec(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"')


def _install_platform() -> None:
    """Install the ``platform`` schema and the ``uuidv7()`` generator."""
    _exec('CREATE SCHEMA IF NOT EXISTS "platform"')
    # pgcrypto provides gen_random_bytes() used by the uuidv7() body.
    _exec('CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA "platform"')
    _exec(
        """
        CREATE OR REPLACE FUNCTION "platform".uuidv7() RETURNS uuid
        LANGUAGE plpgsql
        VOLATILE
        PARALLEL SAFE
        AS $$
        DECLARE
            ts_ms bigint;
            rand bytea;
            bytes bytea;
        BEGIN
            -- 48 bits of Unix-epoch milliseconds
            ts_ms := (extract(epoch from clock_timestamp()) * 1000)::bigint;
            rand := gen_random_bytes(10);
            bytes :=
                decode(lpad(to_hex(ts_ms), 12, '0'), 'hex') || rand;
            -- Set the UUIDv7 version (0111) in the high nibble of byte 6
            bytes := set_byte(bytes, 6, (get_byte(bytes, 6) & 15) OR 112);
            -- Set the RFC 4122 variant (10xx) in the high two bits of byte 8
            bytes := set_byte(bytes, 8, (get_byte(bytes, 8) & 63) OR 128);
            RETURN encode(bytes, 'hex')::uuid;
        END;
        $$;
        """
    )


def _drop_platform() -> None:
    _exec('DROP FUNCTION IF EXISTS "platform".uuidv7()')
    # pgcrypto is left in place; other migrations may depend on it.


# ---------------------------------------------------------------------------
# Outbox / Inbox factories
# ---------------------------------------------------------------------------


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "message_id",
        postgresql.UUID(),
        primary_key=True,
        server_default=sa.text('"platform".uuidv7()'),
    )


def _correlation_causation() -> list[sa.Column]:
    return [
        sa.Column("correlation_id", postgresql.UUID(), nullable=False),
        sa.Column("causation_id", postgresql.UUID(), nullable=True),
    ]


def _create_outbox(schema: str) -> None:
    op.create_table(
        "outbox",
        _uuid_pk(),
        sa.Column("aggregate_id", postgresql.UUID(), nullable=True),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("headers", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        *_correlation_causation(),
        schema=schema,
    )
    op.create_index(
        f"ix_{schema}_outbox_unpublished",
        "outbox",
        ["created_at"],
        unique=False,
        schema=schema,
        postgresql_where=sa.text("published_at IS NULL"),
    )
    op.create_index(
        f"ix_{schema}_outbox_correlation",
        "outbox",
        ["correlation_id"],
        unique=False,
        schema=schema,
    )


def _create_inbox(schema: str) -> None:
    op.create_table(
        "inbox",
        _uuid_pk(),
        sa.Column(
            "consumer_group",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("aggregate_id", postgresql.UUID(), nullable=True),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("headers", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        *_correlation_causation(),
        schema=schema,
    )
    op.create_index(
        f"uq_{schema}_inbox_dedup",
        "inbox",
        ["message_id", "consumer_group"],
        unique=True,
        schema=schema,
    )
    op.create_index(
        f"ix_{schema}_inbox_correlation",
        "inbox",
        ["correlation_id"],
        unique=False,
        schema=schema,
    )


# ---------------------------------------------------------------------------
# Soft delete + optimistic-locking columns (helpers)
# ---------------------------------------------------------------------------


def _soft_delete() -> list[sa.Column]:
    return [sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)]


def _optimistic_lock() -> sa.Column:
    return sa.Column(
        "version",
        sa.Integer(),
        nullable=False,
        server_default=sa.text("1"),
    )


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", sa.String(length=256), nullable=True),
        sa.Column("updated_by", sa.String(length=256), nullable=True),
    ]


# ---------------------------------------------------------------------------
# Foundation entities
# ---------------------------------------------------------------------------


def _create_memory_entities() -> None:
    # ---- memory.consent_records ------------------------------------------
    op.create_table(
        "consent_records",
        sa.Column(
            "consent_id",
            postgresql.UUID(),
            primary_key=True,
            server_default=sa.text('"platform".uuidv7()'),
        ),
        sa.Column("subject_id", postgresql.UUID(), nullable=False),
        sa.Column("purpose", sa.String(length=256), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_id", postgresql.UUID(), nullable=True),
        sa.Column("policy_version", sa.String(length=32), nullable=False, server_default=sa.text("'1.0'")),
        _optimistic_lock(),
        *_audit_columns(),
        *_soft_delete(),
        schema="memory",
    )
    op.create_index(
        "ix_memory_consent_subject",
        "consent_records",
        ["subject_id"],
        schema="memory",
    )
    op.create_index(
        "ix_memory_consent_status",
        "consent_records",
        ["status"],
        schema="memory",
    )
    op.create_check_constraint(
        "ck_memory_consent_status",
        "consent_records",
        sa.text("status IN ('active', 'revoked', 'expired')"),
        schema="memory",
    )
    op.execute(
        'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "memory"."consent_records" '
        f'TO "{SERVICE_ROLES["memory"]}"'
    )

    # ---- memory.memories -------------------------------------------------
    op.create_table(
        "memories",
        sa.Column(
            "memory_id",
            postgresql.UUID(),
            primary_key=True,
            server_default=sa.text('"platform".uuidv7()'),
        ),
        sa.Column(
            "consent_id",
            postgresql.UUID(),
            sa.ForeignKey(
                "memory.consent_records.consent_id",
                name="fk_memory_memories_consent",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column("memory_type", sa.String(length=64), nullable=False),
        sa.Column(
            "source_type",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'explicit_user_input'"),
        ),
        sa.Column("source_id", postgresql.UUID(), nullable=True),
        sa.Column(
            "sensitivity",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'internal'"),
        ),
        sa.Column(
            "retention_policy",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        _optimistic_lock(),
        *_audit_columns(),
        *_soft_delete(),
        schema="memory",
    )
    op.create_index("ix_memory_memories_consent", "memories", ["consent_id"], schema="memory")
    op.create_index("ix_memory_memories_type", "memories", ["memory_type"], schema="memory")
    op.create_index("ix_memory_memories_created", "memories", ["created_at"], schema="memory")
    op.create_check_constraint(
        "ck_memory_memories_sensitivity",
        "memories",
        sa.text("sensitivity IN ('public', 'internal', 'sensitive', 'restricted')"),
        schema="memory",
    )
    # The content column is intentionally absent from the foundation
    # entity. The v1.2 addendum requires content minimization; Phase 02
    # will introduce an explicit content-store relationship with its
    # own access policy.
    op.execute(
        'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "memory"."memories" '
        f'TO "{SERVICE_ROLES["memory"]}"'
    )


def _create_audit_entities() -> None:
    # ---- audit.audit_chain_heads ----------------------------------------
    op.create_table(
        "audit_chain_heads",
        sa.Column("chain_name", sa.String(length=128), primary_key=True),
        sa.Column("head_hash", sa.LargeBinary(length=64), nullable=True),
        sa.Column("entries_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="audit",
    )
    op.execute(
        'GRANT SELECT, INSERT, UPDATE ON TABLE "audit"."audit_chain_heads" '
        f'TO "{SERVICE_ROLES["audit"]}"'
    )

    # ---- audit.audit_entries --------------------------------------------
    # Audit entries are append-only. There is intentionally no
    # ``updated_at`` column and no mutable content column; updates
    # require a compensating entry. Optimistic locking is therefore
    # expressed through the chain hash rather than a ``version``.
    op.create_table(
        "audit_entries",
        sa.Column(
            "entry_id",
            postgresql.UUID(),
            primary_key=True,
            server_default=sa.text('"platform".uuidv7()'),
        ),
        sa.Column("chain_name", sa.String(length=128), nullable=False),
        sa.Column("actor_type", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.String(length=256), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_ref", sa.String(length=512), nullable=True),
        sa.Column(
            "policy_decision",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "classification",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column("correlation_id", postgresql.UUID(), nullable=False),
        sa.Column("causation_id", postgresql.UUID(), nullable=True),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("redacted_reason", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("previous_hash", sa.LargeBinary(length=64), nullable=True),
        sa.Column("entry_hash", sa.LargeBinary(length=64), nullable=False),
        sa.Column("entry_index", sa.BigInteger(), nullable=False),
        schema="audit",
    )
    op.create_index(
        "ix_audit_entries_chain_index",
        "audit_entries",
        ["chain_name", "entry_index"],
        unique=True,
        schema="audit",
    )
    op.create_index(
        "ix_audit_entries_correlation",
        "audit_entries",
        ["correlation_id"],
        schema="audit",
    )
    op.create_index(
        "ix_audit_entries_actor",
        "audit_entries",
        ["actor_type", "actor_id"],
        schema="audit",
    )
    op.create_check_constraint(
        "ck_audit_actor_type",
        "audit_entries",
        sa.text("actor_type IN ('user', 'service', 'agent')"),
        schema="audit",
    )
    op.create_check_constraint(
        "ck_audit_classification",
        "audit_entries",
        sa.text("classification IN ('public', 'internal', 'sensitive', 'restricted')"),
        schema="audit",
    )
    op.execute(
        'GRANT SELECT, INSERT ON TABLE "audit"."audit_entries" '
        f'TO "{SERVICE_ROLES["audit"]}"'
    )
    # ``audit`` is append-only; no UPDATE/DELETE grants.


def _create_settings_entities() -> None:
    op.create_table(
        "user_settings",
        sa.Column(
            "settings_id",
            postgresql.UUID(),
            primary_key=True,
            server_default=sa.text('"platform".uuidv7()'),
        ),
        sa.Column("subject_id", postgresql.UUID(), nullable=False),
        sa.Column(
            "schema_version",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'1.0'"),
        ),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        _optimistic_lock(),
        *_audit_columns(),
        *_soft_delete(),
        schema="settings",
    )
    op.create_index(
        "ix_settings_user_settings_subject",
        "user_settings",
        ["subject_id"],
        unique=True,
        schema="settings",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.execute(
        'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "settings"."user_settings" '
        f'TO "{SERVICE_ROLES["settings"]}"'
    )


# ---------------------------------------------------------------------------
# Migration entry points
# ---------------------------------------------------------------------------


def upgrade() -> None:
    _install_platform()
    _create_schemas()
    _create_roles()
    _grant_schema_privileges()

    for schema in SERVICE_SCHEMAS:
        _create_outbox(schema)
        _create_inbox(schema)

    _create_memory_entities()
    _create_audit_entities()
    _create_settings_entities()


def downgrade() -> None:
    # Foundation entities first, then infrastructure.
    op.drop_table("user_settings", schema="settings")
    op.execute('DROP TABLE IF EXISTS "audit"."audit_entries" CASCADE')
    op.execute('DROP TABLE IF EXISTS "audit"."audit_chain_heads" CASCADE')
    op.execute('DROP TABLE IF EXISTS "memory"."memories" CASCADE')
    op.execute('DROP TABLE IF EXISTS "memory"."consent_records" CASCADE')

    for schema in SERVICE_SCHEMAS:
        op.drop_table("outbox", schema=schema)
        op.drop_table("inbox", schema=schema)

    for schema in SERVICE_SCHEMAS:
        _exec(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')

    _drop_platform()
    _exec('DROP SCHEMA IF EXISTS "platform" CASCADE')
