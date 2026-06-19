"""Add missing service schemas (automation, planner, policy, research)

This migration adds PostgreSQL schemas and outbox/inbox tables for
the four services that were omitted from the foundation migration:

* automation
* planner
* policy
* research

Each schema gets the standard outbox and inbox tables using the same
unified schema as the existing services (message_id UUID PK, subject,
payload JSONB, headers JSONB, correlation/causation tracing, etc.).

Revision ID: 0a1b2c3d4e5f
Revises: 743a95f81f31
Create Date: 2026-06-15 04:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0a1b2c3d4e5f"
down_revision: Union[str, None] = "743a95f81f31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Schemas needed by services whose code references them
NEW_SERVICE_SCHEMAS: tuple[str, ...] = (
    "automation",
    "planner",
    "policy",
    "research",
)

# Per-service NOLOGIN roles (matching the foundation pattern)
NEW_SERVICE_ROLES: dict[str, str] = {
    "automation": "jarvis_automation_app",
    "planner": "jarvis_planner_app",
    "policy": "jarvis_policy_app",
    "research": "jarvis_research_app",
}


def _exec(sql: str) -> None:
    op.execute(sql)


def _create_schemas() -> None:
    for schema in NEW_SERVICE_SCHEMAS:
        _exec(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')


def _create_roles() -> None:
    for role in NEW_SERVICE_ROLES.values():
        _exec(
            f"DO $$ BEGIN "
            f"IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN "
            f'CREATE ROLE "{role}" NOLOGIN; '
            f"END IF; "
            f"END $$;"
        )


def _grant_schema_privileges() -> None:
    for schema, role in NEW_SERVICE_ROLES.items():
        _exec(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"')


def _create_outbox(schema: str) -> None:
    op.create_table(
        "outbox",
        sa.Column(
            "message_id",
            postgresql.UUID(),
            primary_key=True,
            server_default=sa.text('"platform".uuidv7()'),
        ),
        sa.Column("aggregate_id", postgresql.UUID(), nullable=True),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "headers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(), nullable=False),
        sa.Column("causation_id", postgresql.UUID(), nullable=True),
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
    role = NEW_SERVICE_ROLES.get(schema)
    if role:
        _exec(
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{schema}"."outbox" '
            f'TO "{role}"'
        )


def _create_inbox(schema: str) -> None:
    op.create_table(
        "inbox",
        sa.Column(
            "message_id",
            postgresql.UUID(),
            primary_key=True,
            server_default=sa.text('"platform".uuidv7()'),
        ),
        sa.Column("consumer_group", sa.String(length=128), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(), nullable=True),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "headers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(), nullable=False),
        sa.Column("causation_id", postgresql.UUID(), nullable=True),
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
    role = NEW_SERVICE_ROLES.get(schema)
    if role:
        _exec(
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{schema}"."inbox" '
            f'TO "{role}"'
        )


def upgrade() -> None:
    _create_schemas()
    _create_roles()
    _grant_schema_privileges()

    for schema in NEW_SERVICE_SCHEMAS:
        _create_outbox(schema)
        _create_inbox(schema)


def downgrade() -> None:
    for schema in NEW_SERVICE_SCHEMAS:
        op.drop_table("inbox", schema=schema)
        op.drop_table("outbox", schema=schema)

    for schema in NEW_SERVICE_SCHEMAS:
        _exec(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')

    for role in NEW_SERVICE_ROLES.values():
        _exec(f'DROP ROLE IF EXISTS "{role}"')
