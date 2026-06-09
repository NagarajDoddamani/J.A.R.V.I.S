from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MemoryStorageDTO:
    """Flat, serializable representation of a ``Memory`` aggregate for storage.

    All nested domain value objects (``MemoryId``, ``ConsentId``,
    ``MemoryContent``, ``Provenance``, ``RevisionNumber``,
    ``RetentionPolicy``) are flattened into primitive fields. This
    DTO maps directly to a row in the ``memory.memories`` table and
    is the interchange format between the domain and any persistence
    adapter.

    Nullable fields mirror the database column nullability exactly.
    """

    memory_id: str
    consent_id: str
    content: str
    category: str
    source_type: str
    source_id: str | None
    provenance_actor_id: str | None
    provenance_timestamp: datetime
    classification: str
    sensitivity: str
    retention_policy: str
    retention_status: str
    revision: int
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


@dataclass(frozen=True)
class ConsentStorageDTO:
    """Flat, serializable representation of a ``ConsentRecord`` for storage.

    Maps directly to a row in the ``memory.consents`` table. All
    domain value objects (``ConsentId``) are flattened to strings.
    """

    consent_id: str
    status: str
    policy_version: str
    granted_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None


@dataclass(frozen=True)
class MemoryOutboxStorageDTO:
    """Flat representation of a memory domain event for outbox storage.

    Carries enough context to reconstruct the originating domain event
    at the adapter layer. The ``payload`` field holds event-specific
    data as a JSON string. The generic outbox table
    (``memory.outbox``) wraps these values in its standard envelope.
    """

    event_id: str
    event_type: str
    aggregate_id: str
    occurred_at: datetime
    correlation_id: str | None = None
    causation_id: str | None = None
    payload: str | None = None
    published: bool = False
