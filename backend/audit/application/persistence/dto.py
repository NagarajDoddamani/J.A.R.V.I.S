from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuditEntryStorageDTO:
    """Flat, serializable representation of an ``AuditEntry`` for storage.

    All nested domain value objects (``ActorRef``, ``TargetRef``,
    ``EntryHash``, ``EntryIndex``, ``OccurredAt``) are flattened
    into primitive fields. This DTO maps directly to a row in the
    ``audit.audit_entries`` table and is the interchange format
    between the domain and any persistence adapter.

    Nullable fields mirror the database column nullability exactly.
    """

    entry_id: str
    chain_name: str
    actor_type: str
    actor_id: str | None
    action: str
    target_type: str | None
    target_ref: str | None
    policy_decision: str
    classification: str
    correlation_id: str
    causation_id: str | None
    result: str
    redacted_reason: str | None
    occurred_at: datetime
    previous_hash: bytes | None
    entry_hash: bytes
    entry_index: int


@dataclass(frozen=True)
class AuditChainHeadStorageDTO:
    """Flat, serializable representation of an ``AuditChainHead`` for storage.

    Includes ``updated_at`` as infrastructure metadata (the domain
    ``AuditChainHead`` entity does not carry a timestamp — it is
    managed by the adapter).
    """

    chain_name: str
    head_hash: bytes | None
    entries_count: int
    updated_at: datetime | None = None


@dataclass(frozen=True)
class AuditOutboxStorageDTO:
    """Flat representation of an ``AuditEntryRecorded`` domain event for outbox storage.

    This DTO carries only the fields the audit domain publishes;
    the generic outbox table (``audit.outbox``) wraps these values
    in its standard envelope (``message_id``, ``subject``,
    ``headers``, ``created_at``, etc.) at the adapter level.
    """

    entry_id: str
    chain_name: str
    action: str
    actor_type: str
    actor_id: str | None
    correlation_id: str
    entry_index: int
    occurred_at: datetime
    published: bool = False
