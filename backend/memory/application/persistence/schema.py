"""Persistence schema contracts for the Memory Service.

Each ``TableContract`` enumerates the expected columns, types,
nullability, and constraints that any adapter implementation
MUST satisfy. Adapters that deviate from these contracts will
fail schema-validation tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ColumnContract:
    """Contract for a single database column.

    Attributes
    ----------
    name:
        The column name as it appears in the DDL.
    py_type:
        The Python type the adapter should map to/from.
    nullable:
        Whether the column accepts NULL.
    max_length:
        Maximum string/binary length, if applicable.
    enum_values:
        Permitted string values for check-constrained columns.
    """
    name: str
    py_type: type[Any]
    nullable: bool
    max_length: int | None = None
    enum_values: tuple[str, ...] | None = None


@dataclass(frozen=True)
class TableContract:
    """Contract for a database table.

    Attributes
    ----------
    name:
        The table name.
    schema:
        The PostgreSQL schema name.
    columns:
        Ordered column contracts.
    primary_key:
        Column name (or tuple of column names) that form the
        primary key.
    indexes:
        Named indexes the adapter is expected to maintain.
    unique_constraints:
        Named unique constraints the adapter is expected to
        enforce.
    """
    name: str
    schema: str
    columns: tuple[ColumnContract, ...]
    primary_key: str | tuple[str, ...]
    indexes: tuple[str, ...] = ()
    unique_constraints: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# memory.memories
# ---------------------------------------------------------------------------

MEMORIES_TABLE: TableContract = TableContract(
    name="memories",
    schema="memory",
    columns=(
        ColumnContract("memory_id", str, nullable=False),
        ColumnContract("consent_id", str, nullable=False),
        ColumnContract("content", str, nullable=False),
        ColumnContract("category", str, nullable=False, max_length=32,
                       enum_values=("general", "conversation", "document",
                                    "insight", "preference", "ephemeral")),
        ColumnContract("source_type", str, nullable=False, max_length=64),
        ColumnContract("source_id", str, nullable=True, max_length=256),
        ColumnContract("provenance_actor_id", str, nullable=True, max_length=256),
        ColumnContract("provenance_timestamp", datetime, nullable=False),
        ColumnContract("classification", str, nullable=False, max_length=16,
                       enum_values=("public", "internal", "sensitive", "restricted")),
        ColumnContract("sensitivity", str, nullable=False, max_length=16,
                       enum_values=("public", "internal", "sensitive", "restricted")),
        ColumnContract("retention_policy", str, nullable=False, max_length=16,
                       enum_values=("persistent", "ephemeral", "time_bound")),
        ColumnContract("retention_status", str, nullable=False, max_length=16,
                       enum_values=("active", "expired", "purge_pending", "purged")),
        ColumnContract("revision", int, nullable=False),
        ColumnContract("created_at", datetime, nullable=False),
        ColumnContract("updated_at", datetime, nullable=True),
        ColumnContract("deleted_at", datetime, nullable=True),
    ),
    primary_key="memory_id",
    indexes=(
        "ix_memories_consent_id",
        "ix_memories_category",
        "ix_memories_source",
        "ix_memories_retention_status",
    ),
)

# ---------------------------------------------------------------------------
# memory.consents
# ---------------------------------------------------------------------------

CONSENTS_TABLE: TableContract = TableContract(
    name="consents",
    schema="memory",
    columns=(
        ColumnContract("consent_id", str, nullable=False),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("proposed", "active", "revoked", "purged")),
        ColumnContract("granted_at", datetime, nullable=True),
        ColumnContract("expires_at", datetime, nullable=True),
        ColumnContract("revoked_at", datetime, nullable=True),
        ColumnContract("policy_version", str, nullable=False, max_length=16),
    ),
    primary_key="consent_id",
    indexes=("ix_consents_status",),
)

# ---------------------------------------------------------------------------
# memory.outbox
# ---------------------------------------------------------------------------

MEMORY_OUTBOX_TABLE: TableContract = TableContract(
    name="outbox",
    schema="memory",
    columns=(
        ColumnContract("event_id", str, nullable=False),
        ColumnContract("event_type", str, nullable=False, max_length=32,
                       enum_values=("memory.created", "memory.updated",
                                    "memory.deleted", "memory.retention_expired",
                                    "memory.purge_scheduled", "memory.purged",
                                    "consent.granted", "consent.revoked")),
        ColumnContract("aggregate_id", str, nullable=False),
        ColumnContract("occurred_at", datetime, nullable=False),
        ColumnContract("correlation_id", str, nullable=True),
        ColumnContract("causation_id", str, nullable=True),
        ColumnContract("payload", str, nullable=True),
        ColumnContract("published", bool, nullable=False),
    ),
    primary_key="event_id",
    indexes=(
        "ix_memory_outbox_unpublished",
        "ix_memory_outbox_aggregate",
    ),
)
