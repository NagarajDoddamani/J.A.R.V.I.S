from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from shared.schemas.types import new_uuid


# ---------------------------------------------------------------------------
# Common Error DTO
# ---------------------------------------------------------------------------


class ApiError(BaseModel):
    code: str
    message: str
    correlation_id: str = Field(default_factory=new_uuid)
    details: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Health & Readiness
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"

    model_config = ConfigDict(extra="forbid")


class ReadyResponse(BaseModel):
    status: str = "ok"
    dependencies: dict[str, bool] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class SystemStatusResponse(BaseModel):
    status: str = "ok"
    services: dict[str, str] = Field(default_factory=dict)
    models: dict[str, str] = Field(default_factory=dict)
    storage: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Request DTOs
# ---------------------------------------------------------------------------


class SubmitRequestPayload(BaseModel):
    conversation_id: str | None = None
    input: dict[str, str]
    attachments: list[dict[str, str]] = Field(default_factory=list)
    preferences: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class SubmitRequestResponse(BaseModel):
    request_id: str
    conversation_id: str | None = None
    status: str = "received"
    events_url: str = ""
    created_at: datetime

    model_config = ConfigDict(extra="forbid")


class RequestStatusResponse(BaseModel):
    request_id: str
    conversation_id: str | None = None
    status: str
    events_url: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(extra="forbid")


class ApprovalDecisionPayload(BaseModel):
    decision: str
    constraints: dict[str, str | None] | None = None

    model_config = ConfigDict(extra="forbid")


class ApprovalResponse(BaseModel):
    approval_id: str
    status: str
    decided_at: datetime

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Memory DTOs
# ---------------------------------------------------------------------------


class CreateMemoryPayload(BaseModel):
    consent_id: str
    content: str
    memory_type: str = "preference"
    sensitivity: str = "internal"
    retention: dict[str, str | None]
    provenance: dict[str, str | None]

    model_config = ConfigDict(extra="forbid")


class CreateMemoryResponse(BaseModel):
    memory_id: str
    consent_id: str
    revision: int = 1
    created_at: datetime
    sensitivity: str = "internal"
    retention_policy: dict[str, str | None]

    model_config = ConfigDict(extra="forbid")


class MemorySearchQuery(BaseModel):
    query: str | None = None
    type: str | None = None
    sensitivity: str | None = None
    created_after: datetime | None = None
    limit: int = 20
    cursor: str | None = None

    model_config = ConfigDict(extra="forbid")


class UpdateMemoryPayload(BaseModel):
    content: str | None = None
    sensitivity: str | None = None
    retention: dict[str, str | None] | None = None

    model_config = ConfigDict(extra="forbid")


class DeleteMemoryResponse(BaseModel):
    memory_id: str
    deletion_job_id: str
    status: str = "purge_pending"
    backup_expiry_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Consent DTOs
# ---------------------------------------------------------------------------


class CreateConsentPayload(BaseModel):
    purpose: str
    scope: dict[str, list[str]]
    retention_policy: dict[str, str | None]
    decision: str = "approve"

    model_config = ConfigDict(extra="forbid")


class ConsentResponse(BaseModel):
    consent_id: str
    status: str
    policy_version: int = 1
    granted_at: datetime
    expires_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class RevokeConsentResponse(BaseModel):
    consent_id: str
    status: str = "revoked"
    deletion_job_id: str
    revoked_at: datetime

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Knowledge Source DTOs
# ---------------------------------------------------------------------------


class CreateKnowledgeSourcePayload(BaseModel):
    kind: str
    local_path_token: str
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    retention: str = "reference_source"

    model_config = ConfigDict(extra="forbid")


class KnowledgeSourceResponse(BaseModel):
    source_id: str
    kind: str
    retention: str
    status: str = "registered"
    created_at: datetime

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Notification DTOs
# ---------------------------------------------------------------------------


class NotificationResponse(BaseModel):
    notification_id: str
    title: str = ""
    body: str = ""
    priority: str = "normal"
    sensitive: bool = False
    status: str = "pending"
    created_at: datetime
    expires_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Settings DTOs
# ---------------------------------------------------------------------------


class SettingsPatchPayload(BaseModel):
    voice: dict[str, bool] | None = None
    privacy: dict[str, int | bool] | None = None
    ui: dict[str, bool] | None = None

    model_config = ConfigDict(extra="forbid")


class SettingsResponse(BaseModel):
    settings: dict[str, object]

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Deletion Job DTOs
# ---------------------------------------------------------------------------


class DeletionJobResponse(BaseModel):
    job_id: str
    resource_id: str
    status: str
    stages: dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Audit DTOs
# ---------------------------------------------------------------------------


class AuditQuery(BaseModel):
    limit: int = 50
    offset: int = 0
    actor: str | None = None
    action: str | None = None
    correlation_id: str | None = None
    after: datetime | None = None
    before: datetime | None = None

    model_config = ConfigDict(extra="forbid")
