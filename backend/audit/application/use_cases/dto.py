from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


# ---------------------------------------------------------------------------
# RecordAuditEntryUseCase
# ---------------------------------------------------------------------------


@dataclass
class RecordAuditEntryRequest:
    chain_name: str
    action: str
    policy_decision: str
    classification: str
    correlation_id: str
    result: str
    actor_type: str
    actor_id: str | None = None
    causation_id: str | None = None
    target_type: str | None = None
    target_ref: str | None = None
    redacted_reason: str | None = None
    occurred_at: datetime | None = None


@dataclass
class RecordAuditEntryResponse:
    entry_id: str
    chain_name: str
    action: str
    policy_decision: str
    classification: str
    correlation_id: str
    causation_id: str | None
    result: str
    actor_type: str
    actor_id: str | None
    entry_index: int
    entry_hash_hex: str
    previous_hash_hex: str | None
    occurred_at: datetime


# ---------------------------------------------------------------------------
# GetAuditEntryUseCase
# ---------------------------------------------------------------------------


@dataclass
class GetAuditEntryRequest:
    entry_id: str


@dataclass
class AuditEntryResponse:
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
    previous_hash_hex: str | None
    entry_hash_hex: str
    entry_index: int


# ---------------------------------------------------------------------------
# GetAuditChainUseCase
# ---------------------------------------------------------------------------


@dataclass
class GetAuditChainRequest:
    chain_name: str
    since_index: int | None = None
    limit: int = 100
    offset: int = 0


@dataclass
class GetAuditChainResponse:
    entries: list[AuditEntryResponse] = field(default_factory=list)
    total: int = 0


# ---------------------------------------------------------------------------
# GetAuditEntriesByCorrelationUseCase
# ---------------------------------------------------------------------------


@dataclass
class GetAuditEntriesByCorrelationRequest:
    correlation_id: str


@dataclass
class GetAuditEntriesByCorrelationResponse:
    entries: list[AuditEntryResponse] = field(default_factory=list)


# ---------------------------------------------------------------------------
# GetAuditChainHeadUseCase
# ---------------------------------------------------------------------------


@dataclass
class GetAuditChainHeadRequest:
    chain_name: str


@dataclass
class AuditChainHeadResponse:
    chain_name: str
    head_hash_hex: str | None
    entries_count: int
