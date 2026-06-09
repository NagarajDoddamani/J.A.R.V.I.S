from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


# ---------------------------------------------------------------------------
# Shared response pieces
# ---------------------------------------------------------------------------


@dataclass
class MemoryResponse:
    memory_id: str
    consent_id: str
    content: str
    category: str
    source_type: str
    source_id: str | None
    classification: str
    sensitivity: str
    retention_policy: str
    retention_status: str
    revision: int
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None


@dataclass
class ConsentResponse:
    consent_id: str
    status: str
    granted_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    policy_version: str


# ---------------------------------------------------------------------------
# CreateMemoryUseCase
# ---------------------------------------------------------------------------


@dataclass
class CreateMemoryRequest:
    consent_id: str
    content: str
    category: str
    source_type: str
    provenance_source: str
    classification: str = "public"
    sensitivity: str = "public"
    retention_policy: str = "persistent"
    source_id: str | None = None
    provenance_actor_id: str | None = None
    retention_ttl_days: int | None = None
    redaction_metadata: str | None = None


@dataclass
class CreateMemoryResponse:
    memory_id: str
    consent_id: str
    content: str
    category: str
    source_type: str
    source_id: str | None
    classification: str
    sensitivity: str
    retention_policy: str
    retention_status: str
    revision: int
    created_at: datetime


# ---------------------------------------------------------------------------
# UpdateMemoryUseCase
# ---------------------------------------------------------------------------


@dataclass
class UpdateMemoryRequest:
    memory_id: str
    content: str


@dataclass
class UpdateMemoryResponse:
    memory_id: str
    consent_id: str
    content: str
    category: str
    revision: int
    updated_at: datetime


# ---------------------------------------------------------------------------
# DeleteMemoryUseCase
# ---------------------------------------------------------------------------


@dataclass
class DeleteMemoryRequest:
    memory_id: str


@dataclass
class DeleteMemoryResponse:
    memory_id: str
    deleted_at: datetime
    revision: int


# ---------------------------------------------------------------------------
# GetMemoryUseCase
# ---------------------------------------------------------------------------


@dataclass
class GetMemoryRequest:
    memory_id: str


# ---------------------------------------------------------------------------
# SearchMemoriesUseCase
# ---------------------------------------------------------------------------


@dataclass
class SearchMemoriesRequest:
    category: str | None = None
    consent_id: str | None = None
    source_type: str | None = None
    source_id: str | None = None


@dataclass
class SearchMemoriesResponse:
    memories: list[MemoryResponse] = field(default_factory=list)
    total: int = 0


# ---------------------------------------------------------------------------
# GrantConsentUseCase
# ---------------------------------------------------------------------------


@dataclass
class GrantConsentRequest:
    expires_at: datetime | None = None
    policy_version: str = "1.0"


@dataclass
class GrantConsentResponse:
    consent_id: str
    status: str
    granted_at: datetime
    expires_at: datetime | None
    policy_version: str


# ---------------------------------------------------------------------------
# RevokeConsentUseCase
# ---------------------------------------------------------------------------


@dataclass
class RevokeConsentRequest:
    consent_id: str


@dataclass
class RevokeConsentResponse:
    consent_id: str
    status: str
    revoked_at: datetime


# ---------------------------------------------------------------------------
# GetConsentUseCase
# ---------------------------------------------------------------------------


@dataclass
class GetConsentRequest:
    consent_id: str
