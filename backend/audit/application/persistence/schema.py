"""Persistence schema contracts for the Audit Service.

Each ``TableContract`` enumerates the expected columns, types,
nullability, and constraints that any adapter implementation
MUST satisfy. Adapters that deviate from these contracts will
fail schema-validation tests.

These contracts mirror the foundation migration at
``backend/migrations/versions/743a95f81f31_initial_foundation_setup.py``.
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
# audit.audit_entries
# ---------------------------------------------------------------------------

AUDIT_ENTRIES_TABLE: TableContract = TableContract(
    name="audit_entries",
    schema="audit",
    columns=(
        ColumnContract("entry_id", str, nullable=False),
        ColumnContract("chain_name", str, nullable=False, max_length=128),
        ColumnContract("actor_type", str, nullable=False, max_length=16,
                       enum_values=("user", "service", "agent")),
        ColumnContract("actor_id", str, nullable=True, max_length=256),
        ColumnContract("action", str, nullable=False, max_length=128),
        ColumnContract("target_type", str, nullable=True, max_length=64),
        ColumnContract("target_ref", str, nullable=True, max_length=512),
        ColumnContract("policy_decision", str, nullable=False, max_length=32),
        ColumnContract("classification", str, nullable=False, max_length=16,
                       enum_values=("public", "internal", "sensitive", "restricted")),
        ColumnContract("correlation_id", str, nullable=False),
        ColumnContract("causation_id", str, nullable=True),
        ColumnContract("result", str, nullable=False, max_length=32),
        ColumnContract("redacted_reason", str, nullable=True),
        ColumnContract("occurred_at", datetime, nullable=False),
        ColumnContract("previous_hash", bytes, nullable=True),
        ColumnContract("entry_hash", bytes, nullable=False),
        ColumnContract("entry_index", int, nullable=False),
    ),
    primary_key="entry_id",
    indexes=(
        "ix_audit_entries_chain_index",
        "ix_audit_entries_correlation",
        "ix_audit_entries_actor",
    ),
    unique_constraints=("ix_audit_entries_chain_index",),
)

# ---------------------------------------------------------------------------
# audit.audit_chain_heads
# ---------------------------------------------------------------------------

AUDIT_CHAIN_HEADS_TABLE: TableContract = TableContract(
    name="audit_chain_heads",
    schema="audit",
    columns=(
        ColumnContract("chain_name", str, nullable=False, max_length=128),
        ColumnContract("head_hash", bytes, nullable=True),
        ColumnContract("entries_count", int, nullable=False),
        ColumnContract("updated_at", datetime, nullable=False),
    ),
    primary_key="chain_name",
)

# ---------------------------------------------------------------------------
# audit.outbox  (audit-specific fields only)
# ---------------------------------------------------------------------------

AUDIT_OUTBOX_TABLE: TableContract = TableContract(
    name="outbox",
    schema="audit",
    columns=(
        ColumnContract("message_id", str, nullable=False),
        ColumnContract("aggregate_id", str, nullable=True),
        ColumnContract("subject", str, nullable=False, max_length=512),
        ColumnContract("correlation_id", str, nullable=False),
        ColumnContract("causation_id", str, nullable=True),
        ColumnContract("created_at", datetime, nullable=False),
        ColumnContract("published_at", datetime, nullable=True),
        ColumnContract("attempts", int, nullable=False),
        ColumnContract("last_error", str, nullable=True),
    ),
    primary_key="message_id",
    indexes=(
        "ix_audit_outbox_unpublished",
        "ix_audit_outbox_correlation",
    ),
)
