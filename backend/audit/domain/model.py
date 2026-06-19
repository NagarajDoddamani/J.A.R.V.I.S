from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import auto, StrEnum
from uuid import UUID, uuid4


class AuditEntryState(StrEnum):
    PENDING = auto()
    RECORDED = auto()


@dataclass(frozen=True)
class AuditEntryId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class EntryHash:
    value: bytes

    def __eq__(self, other: object) -> bool:
        if isinstance(other, EntryHash):
            return self.value == other.value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)

    def hex(self) -> str:
        return self.value.hex()

    @classmethod
    def from_hex(cls, hex_str: str) -> EntryHash:
        return cls(value=bytes.fromhex(hex_str))


@dataclass(frozen=True)
class EntryIndex:
    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            msg = f"Entry index must be >= 0, got {self.value}"
            raise ValueError(msg)

    def next(self) -> EntryIndex:
        return EntryIndex(value=self.value + 1)


@dataclass(frozen=True)
class OccurredAt:
    value: datetime

    def __post_init__(self) -> None:
        if self.value.tzinfo is None:
            object.__setattr__(self, "value", self.value.replace(tzinfo=timezone.utc))

    @classmethod
    def now(cls) -> OccurredAt:
        return cls(value=datetime.now(tz=timezone.utc))


@dataclass(frozen=True)
class Result:
    value: str


@dataclass(frozen=True)
class ActorRef:
    actor_type: str
    actor_id: str | None = None


@dataclass(frozen=True)
class TargetRef:
    target_type: str | None = None
    target_ref: str | None = None


@dataclass(frozen=True)
class AuditEntryRecorded:
    entry_id: AuditEntryId
    chain_name: str
    action: str
    actor_type: str
    actor_id: str | None
    correlation_id: str
    entry_index: int
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


class AuditEntry:
    """Aggregate root for the audit domain.

    An AuditEntry is immutable once created. It forms part of a
    hash chain where each entry's ``previous_hash`` points to the
    preceding entry's ``entry_hash`` in the same chain.
    """

    def __init__(
        self,
        *,
        entry_id: AuditEntryId,
        chain_name: str,
        actor: ActorRef,
        action: str,
        policy_decision: str,
        classification: str,
        correlation_id: str,
        result: str,
        causation_id: str | None = None,
        target: TargetRef | None = None,
        redacted_reason: str | None = None,
        occurred_at: OccurredAt | None = None,
        previous_hash: EntryHash | None = None,
        entry_hash: EntryHash,
        entry_index: EntryIndex,
        state: AuditEntryState = AuditEntryState.RECORDED,
    ) -> None:
        self._entry_id = entry_id
        self._chain_name = chain_name
        self._actor = actor
        self._action = action
        self._target = target
        self._policy_decision = policy_decision
        self._classification = classification
        self._correlation_id = correlation_id
        self._causation_id = causation_id
        self._result = result
        self._redacted_reason = redacted_reason
        self._occurred_at = occurred_at or OccurredAt.now()
        self._previous_hash = previous_hash
        self._entry_hash = entry_hash
        self._entry_index = entry_index
        self._state = state

    @property
    def entry_id(self) -> AuditEntryId:
        return self._entry_id

    @property
    def chain_name(self) -> str:
        return self._chain_name

    @property
    def actor(self) -> ActorRef:
        return self._actor

    @property
    def action(self) -> str:
        return self._action

    @property
    def target(self) -> TargetRef | None:
        return self._target

    @property
    def policy_decision(self) -> str:
        return self._policy_decision

    @property
    def classification(self) -> str:
        return self._classification

    @property
    def correlation_id(self) -> str:
        return self._correlation_id

    @property
    def causation_id(self) -> str | None:
        return self._causation_id

    @property
    def result(self) -> str:
        return self._result

    @property
    def redacted_reason(self) -> str | None:
        return self._redacted_reason

    @property
    def occurred_at(self) -> OccurredAt:
        return self._occurred_at

    @property
    def previous_hash(self) -> EntryHash | None:
        return self._previous_hash

    @property
    def entry_hash(self) -> EntryHash:
        return self._entry_hash

    @property
    def entry_index(self) -> EntryIndex:
        return self._entry_index

    @property
    def state(self) -> AuditEntryState:
        return self._state

    def transition_to_recorded(self) -> None:
        if self._state != AuditEntryState.PENDING:
            msg = f"Cannot transition from {self._state!r} to 'recorded'"
            raise ValueError(msg)
        self._state = AuditEntryState.RECORDED

    def __repr__(self) -> str:
        return (
            f"AuditEntry(id={self._entry_id}, chain={self._chain_name!r}, "
            f"action={self._action!r}, index={self._entry_index.value})"
        )


@dataclass(frozen=True)
class AuditChainHead:
    """Snapshot of the head of an audit chain at a point in time."""
    chain_name: str
    head_hash: EntryHash | None
    entries_count: int
