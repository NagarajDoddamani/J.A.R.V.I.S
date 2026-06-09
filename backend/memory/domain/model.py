from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import auto, StrEnum
from typing import Any
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================


class MemoryCategory(StrEnum):
    GENERAL = auto()
    CONVERSATION = auto()
    DOCUMENT = auto()
    INSIGHT = auto()
    PREFERENCE = auto()
    EPHEMERAL = auto()


class MemoryState(StrEnum):
    CREATED = auto()
    UPDATED = auto()
    DELETED = auto()


class ConsentStatus(StrEnum):
    PROPOSED = auto()
    ACTIVE = auto()
    REVOKED = auto()
    PURGED = auto()


class MemorySource(StrEnum):
    USER_INPUT = auto()
    CONVERSATION = auto()
    INFERENCE = auto()
    SYSTEM = auto()
    EXTERNAL = auto()


class RetentionStatus(StrEnum):
    ACTIVE = auto()
    EXPIRED = auto()
    PURGE_PENDING = auto()
    PURGED = auto()


# =============================================================================
# Value Objects
# =============================================================================


@dataclass(frozen=True)
class MemoryId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class ConsentId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class RevisionNumber:
    value: int = 1

    def __post_init__(self) -> None:
        if self.value < 1:
            msg = f"Revision must be >= 1, got {self.value}"
            raise ValueError(msg)

    def increment(self) -> RevisionNumber:
        return RevisionNumber(value=self.value + 1)

    def __int__(self) -> int:
        return self.value


@dataclass(frozen=True)
class MemoryContent:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"MemoryContent value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class Provenance:
    """Tracks the origin of a memory."""

    source: str
    timestamp: datetime
    actor_id: str | None = None

    def __post_init__(self) -> None:
        if not self.source or not self.source.strip():
            from backend.memory.domain.exceptions import InvalidProvenanceError
            raise InvalidProvenanceError("source must not be empty")
        if self.timestamp.tzinfo is None:
            object.__setattr__(
                self, "timestamp", self.timestamp.replace(tzinfo=timezone.utc)
            )


@dataclass(frozen=True)
class RetentionPolicy:
    """Defines how long a memory should be retained."""

    policy: str
    ttl_days: int | None = None

    def __post_init__(self) -> None:
        valid_policies = ("persistent", "ephemeral", "time_bound")
        if self.policy not in valid_policies:
            from backend.memory.domain.exceptions import InvalidRetentionPolicyError
            raise InvalidRetentionPolicyError(
                f"policy must be one of {valid_policies}, got {self.policy!r}"
            )
        if self.policy == "time_bound" and (self.ttl_days is None or self.ttl_days < 1):
            from backend.memory.domain.exceptions import InvalidRetentionPolicyError
            raise InvalidRetentionPolicyError(
                "time_bound policy requires ttl_days >= 1"
            )
        if self.policy != "time_bound" and self.ttl_days is not None:
            from backend.memory.domain.exceptions import InvalidRetentionPolicyError
            raise InvalidRetentionPolicyError(
                f"ttl_days must be None for {self.policy!r} policy"
            )


# =============================================================================
# Domain Events
# =============================================================================


@dataclass(frozen=True)
class MemoryCreated:
    memory_id: MemoryId
    consent_id: ConsentId
    category: MemoryCategory
    source_type: str
    source_id: str | None
    sensitivity: str
    occurred_at: datetime


@dataclass(frozen=True)
class MemoryUpdated:
    memory_id: MemoryId
    revision: int
    occurred_at: datetime


@dataclass(frozen=True)
class MemoryDeleted:
    memory_id: MemoryId
    revision: int
    occurred_at: datetime


@dataclass(frozen=True)
class MemoryRetentionExpired:
    memory_id: MemoryId
    revision: int
    occurred_at: datetime


@dataclass(frozen=True)
class MemoryPurgeScheduled:
    memory_id: MemoryId
    revision: int
    occurred_at: datetime


@dataclass(frozen=True)
class MemoryPurged:
    memory_id: MemoryId
    revision: int
    occurred_at: datetime


@dataclass(frozen=True)
class ConsentGranted:
    consent_id: ConsentId
    occurred_at: datetime


@dataclass(frozen=True)
class ConsentRevoked:
    consent_id: ConsentId
    occurred_at: datetime


# =============================================================================
# Entities
# =============================================================================


class ConsentRecord:
    """Tracks the consent lifecycle for memory storage."""

    def __init__(
        self,
        consent_id: ConsentId | None = None,
        status: ConsentStatus = ConsentStatus.PROPOSED,
        granted_at: datetime | None = None,
        expires_at: datetime | None = None,
        revoked_at: datetime | None = None,
        policy_version: str = "1.0",
    ) -> None:
        self._consent_id = consent_id or ConsentId()
        self._status = status
        self._granted_at = granted_at
        self._expires_at = expires_at
        self._revoked_at = revoked_at
        self._policy_version = policy_version
        self._events: list[ConsentGranted | ConsentRevoked] = []

    # -- properties ---------------------------------------------------------

    @property
    def consent_id(self) -> ConsentId:
        return self._consent_id

    @property
    def status(self) -> ConsentStatus:
        return self._status

    @property
    def granted_at(self) -> datetime | None:
        return self._granted_at

    @property
    def expires_at(self) -> datetime | None:
        return self._expires_at

    @property
    def revoked_at(self) -> datetime | None:
        return self._revoked_at

    @property
    def policy_version(self) -> str:
        return self._policy_version

    @property
    def events(self) -> list[ConsentGranted | ConsentRevoked]:
        return list(self._events)

    @property
    def is_active(self) -> bool:
        if self._status != ConsentStatus.ACTIVE:
            return False
        if self._expires_at is not None and self._expires_at < datetime.now(tz=timezone.utc):
            return False
        return True

    # -- commands -----------------------------------------------------------

    def grant(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.memory.domain.rules import (
            assert_consent_can_transition,
            assert_expiration_after_grant,
        )

        assert_consent_can_transition(self._status, ConsentStatus.ACTIVE)

        if self._expires_at is not None:
            assert_expiration_after_grant(self._expires_at, now)

        self._status = ConsentStatus.ACTIVE
        self._granted_at = now
        self._events.append(
            ConsentGranted(consent_id=self._consent_id, occurred_at=now)
        )

    def revoke(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.memory.domain.rules import assert_consent_can_transition

        assert_consent_can_transition(self._status, ConsentStatus.REVOKED)
        self._status = ConsentStatus.REVOKED
        self._revoked_at = now
        self._events.append(
            ConsentRevoked(consent_id=self._consent_id, occurred_at=now)
        )

    def purge(self) -> None:
        from backend.memory.domain.rules import assert_consent_can_transition

        assert_consent_can_transition(self._status, ConsentStatus.PURGED)
        self._status = ConsentStatus.PURGED

    # -- internal -----------------------------------------------------------

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"ConsentRecord(id={self._consent_id}, "
            f"status={self._status.value})"
        )


class Memory:
    """Aggregate root for the memory domain."""

    def __init__(
        self,
        memory_id: MemoryId,
        consent_id: ConsentId,
        content: MemoryContent,
        category: MemoryCategory,
        source_type: str,
        source_id: str | None,
        provenance: Provenance,
        classification: str,
        sensitivity: str,
        retention: RetentionPolicy,
        revision: RevisionNumber | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        deleted_at: datetime | None = None,
        state: MemoryState = MemoryState.CREATED,
        retention_status: RetentionStatus = RetentionStatus.ACTIVE,
        redaction_metadata: str | None = None,
    ) -> None:
        self._memory_id = memory_id
        self._consent_id = consent_id
        self._content = content
        self._category = category
        self._source_type = source_type
        self._source_id = source_id
        self._provenance = provenance
        self._classification = classification
        self._sensitivity = sensitivity
        self._retention = retention
        self._revision = revision or RevisionNumber()
        self._created_at = created_at or datetime.now(tz=timezone.utc)
        self._updated_at = updated_at
        self._deleted_at = deleted_at
        self._state = state
        self._retention_status = retention_status
        self._redaction_metadata = redaction_metadata
        self._events: list[
            MemoryUpdated | MemoryDeleted | MemoryRetentionExpired | MemoryPurgeScheduled | MemoryPurged
        ] = []

    # -- properties ---------------------------------------------------------

    @property
    def memory_id(self) -> MemoryId:
        return self._memory_id

    @property
    def consent_id(self) -> ConsentId:
        return self._consent_id

    @property
    def content(self) -> MemoryContent:
        return self._content

    @property
    def category(self) -> MemoryCategory:
        return self._category

    @property
    def source_type(self) -> str:
        return self._source_type

    @property
    def source_id(self) -> str | None:
        return self._source_id

    @property
    def provenance(self) -> Provenance:
        return self._provenance

    @property
    def classification(self) -> str:
        return self._classification

    @property
    def sensitivity(self) -> str:
        return self._sensitivity

    @property
    def retention(self) -> RetentionPolicy:
        return self._retention

    @property
    def revision(self) -> RevisionNumber:
        return self._revision

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @property
    def deleted_at(self) -> datetime | None:
        return self._deleted_at

    @property
    def state(self) -> MemoryState:
        return self._state

    @property
    def retention_status(self) -> RetentionStatus:
        return self._retention_status

    @property
    def redaction_metadata(self) -> str | None:
        return self._redaction_metadata

    @property
    def events(
        self,
    ) -> list[
        MemoryUpdated | MemoryDeleted | MemoryRetentionExpired | MemoryPurgeScheduled | MemoryPurged
    ]:
        return list(self._events)

    @property
    def is_deleted(self) -> bool:
        return self._state == MemoryState.DELETED

    # -- commands -----------------------------------------------------------

    def update(self, content: MemoryContent, consent: ConsentRecord) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.memory.domain.rules import (
            assert_content_not_empty,
            assert_content_no_secrets,
            assert_not_deleted,
            assert_not_purged,
            assert_consent_allows_updates,
        )

        assert_not_purged(self._retention_status)
        assert_not_deleted(self._state)
        assert_consent_allows_updates(consent)
        assert_content_not_empty(content.value)
        assert_content_no_secrets(content.value)
        # provenance preserved from original (rule 19)
        # content NOT stored in domain event (rule 20)

        self._content = content
        self._revision = self._revision.increment()
        self._updated_at = now
        self._state = MemoryState.UPDATED

        self._events.append(
            MemoryUpdated(
                memory_id=self._memory_id,
                revision=int(self._revision),
                occurred_at=now,
            )
        )

    def delete(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.memory.domain.rules import assert_not_deleted, assert_not_purged

        assert_not_purged(self._retention_status)
        assert_not_deleted(self._state)

        self._deleted_at = now
        self._state = MemoryState.DELETED

        self._events.append(
            MemoryDeleted(
                memory_id=self._memory_id,
                revision=int(self._revision),
                occurred_at=now,
            )
        )

    def expire_retention(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.memory.domain.rules import assert_not_purged, assert_retention_can_expire

        assert_not_purged(self._retention_status)
        assert_retention_can_expire(self._retention_status)

        self._retention_status = RetentionStatus.EXPIRED

        self._events.append(
            MemoryRetentionExpired(
                memory_id=self._memory_id,
                revision=int(self._revision),
                occurred_at=now,
            )
        )

    def schedule_purge(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.memory.domain.rules import assert_not_purged

        assert_not_purged(self._retention_status)

        self._retention_status = RetentionStatus.PURGE_PENDING

        self._events.append(
            MemoryPurgeScheduled(
                memory_id=self._memory_id,
                revision=int(self._revision),
                occurred_at=now,
            )
        )

    def purge_memory(self) -> None:
        now = datetime.now(tz=timezone.utc)
        self._retention_status = RetentionStatus.PURGED
        self._deleted_at = now
        self._state = MemoryState.DELETED

        self._events.append(
            MemoryPurged(
                memory_id=self._memory_id,
                revision=int(self._revision),
                occurred_at=now,
            )
        )

    # -- internal -----------------------------------------------------------

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"Memory(id={self._memory_id}, "
            f"category={self._category.value}, "
            f"state={self._state.value}, "
            f"rev={self._revision}, "
            f"retention_status={self._retention_status.value})"
        )
