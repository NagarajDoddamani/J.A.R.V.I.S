from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Payload DTOs — each event envelope carries one of these as its ``payload``.
# All use ``extra="forbid"`` so unknown fields are rejected.
# ---------------------------------------------------------------------------


class UserRequestReceivedPayload(BaseModel):
    request_id: str
    conversation_id: str | None = None
    input_mode: str = "text"
    request_content_ref: str
    received_at: datetime

    model_config = ConfigDict(extra="forbid")


class MemoryCreatedPayload(BaseModel):
    memory_id: str
    consent_id: str
    memory_type: str = "preference"
    source_ref: str | None = None
    revision: int = 1
    sensitivity: str = "internal"
    retention_policy: dict[str, str | None]
    created_at: datetime

    model_config = ConfigDict(extra="forbid")


class MemoryUpdatedPayload(BaseModel):
    memory_id: str
    consent_id: str
    revision: int
    changed_fields: list[str] = Field(default_factory=list)
    sensitivity: str = "internal"
    retention_policy: dict[str, str | None]
    updated_at: datetime

    model_config = ConfigDict(extra="forbid")


class MemoryDeletedPayload(BaseModel):
    memory_id: str
    deletion_job_id: str
    deleted_at: datetime

    model_config = ConfigDict(extra="forbid")


class ResearchStartedPayload(BaseModel):
    research_id: str
    request_id: str
    source_scopes: list[str] = Field(default_factory=list)
    network_allowed: bool = False
    started_at: datetime

    model_config = ConfigDict(extra="forbid")


class ResearchCompletedPayload(BaseModel):
    research_id: str
    request_id: str
    status: str = "completed"
    result_ref: str | None = None
    citation_refs: list[dict[str, str]] = Field(default_factory=list)
    source_count: int = 0
    completed_at: datetime

    model_config = ConfigDict(extra="forbid")


class ApplicationOpenedPayload(BaseModel):
    action_id: str
    application_id: str
    process_id: int | None = None
    capability_grant_id: str | None = None
    result: str = "success"
    opened_at: datetime

    model_config = ConfigDict(extra="forbid")


class RequestCompletedPayload(BaseModel):
    request_id: str
    result_ref: str | None = None
    completed_at: datetime

    model_config = ConfigDict(extra="forbid")


class RequestFailedPayload(BaseModel):
    request_id: str
    error_code: str
    failed_at: datetime

    model_config = ConfigDict(extra="forbid")


class RequestCancelledPayload(BaseModel):
    request_id: str
    reason: str = "user_requested"
    cancelled_at: datetime

    model_config = ConfigDict(extra="forbid")


class ConsentGrantedPayload(BaseModel):
    consent_id: str
    purpose: str
    granted_at: datetime

    model_config = ConfigDict(extra="forbid")


class ConsentRevokedPayload(BaseModel):
    consent_id: str
    deletion_job_id: str | None = None
    revoked_at: datetime

    model_config = ConfigDict(extra="forbid")


class SettingsUpdatedPayload(BaseModel):
    changed_keys: list[str] = Field(default_factory=list)
    updated_at: datetime

    model_config = ConfigDict(extra="forbid")


class KnowledgeSourceRegisteredPayload(BaseModel):
    source_id: str
    kind: str
    registered_at: datetime

    model_config = ConfigDict(extra="forbid")


class KnowledgeSourceDeletedPayload(BaseModel):
    source_id: str
    deleted_at: datetime

    model_config = ConfigDict(extra="forbid")


class KnowledgeIndexedPayload(BaseModel):
    source_id: str
    chunk_count: int = 0
    indexed_at: datetime

    model_config = ConfigDict(extra="forbid")


class NotificationShownPayload(BaseModel):
    notification_id: str
    shown_at: datetime

    model_config = ConfigDict(extra="forbid")


class NotificationAcknowledgedPayload(BaseModel):
    notification_id: str
    acknowledged_at: datetime

    model_config = ConfigDict(extra="forbid")


class NotificationDismissedPayload(BaseModel):
    notification_id: str
    dismissed_at: datetime

    model_config = ConfigDict(extra="forbid")


class WallpaperUpdatedPayload(BaseModel):
    wallpaper_update_id: str
    scene_id: str
    state: str = "applied"
    updated_at: datetime

    model_config = ConfigDict(extra="forbid")


class PolicyDecisionMadePayload(BaseModel):
    request_id: str
    capability: str
    decision: str
    decided_at: datetime

    model_config = ConfigDict(extra="forbid")


class AgentTaskStartedPayload(BaseModel):
    task_id: str
    agent_id: str
    request_id: str
    task_type: str | None = None
    started_at: datetime

    model_config = ConfigDict(extra="forbid")


class AgentTaskCompletedPayload(BaseModel):
    task_id: str
    agent_id: str
    request_id: str
    status: str = "completed"
    completed_at: datetime

    model_config = ConfigDict(extra="forbid")


class WakeWordDetectedPayload(BaseModel):
    session_id: str
    wake_word_id: str = "jarvis"
    confidence: float = 0.0
    device_id: str | None = None
    detected_at: datetime

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Registry — maps event_type string to payload model class
# ---------------------------------------------------------------------------

EVENT_PAYLOAD_REGISTRY: dict[str, type[BaseModel]] = {
    "USER_REQUEST_RECEIVED": UserRequestReceivedPayload,
    "MEMORY_CREATED": MemoryCreatedPayload,
    "MEMORY_UPDATED": MemoryUpdatedPayload,
    "MEMORY_DELETED": MemoryDeletedPayload,
    "RESEARCH_STARTED": ResearchStartedPayload,
    "RESEARCH_COMPLETED": ResearchCompletedPayload,
    "APPLICATION_OPENED": ApplicationOpenedPayload,
    "REQUEST_COMPLETED": RequestCompletedPayload,
    "REQUEST_FAILED": RequestFailedPayload,
    "REQUEST_CANCELLED": RequestCancelledPayload,
    "CONSENT_GRANTED": ConsentGrantedPayload,
    "CONSENT_REVOKED": ConsentRevokedPayload,
    "SETTINGS_UPDATED": SettingsUpdatedPayload,
    "KNOWLEDGE_SOURCE_REGISTERED": KnowledgeSourceRegisteredPayload,
    "KNOWLEDGE_SOURCE_DELETED": KnowledgeSourceDeletedPayload,
    "KNOWLEDGE_INDEXED": KnowledgeIndexedPayload,
    "NOTIFICATION_SHOWN": NotificationShownPayload,
    "NOTIFICATION_ACKNOWLEDGED": NotificationAcknowledgedPayload,
    "NOTIFICATION_DISMISSED": NotificationDismissedPayload,
    "WALLPAPER_UPDATED": WallpaperUpdatedPayload,
    "POLICY_DECISION_MADE": PolicyDecisionMadePayload,
    "AGENT_TASK_STARTED": AgentTaskStartedPayload,
    "AGENT_TASK_COMPLETED": AgentTaskCompletedPayload,
    "WAKE_WORD_DETECTED": WakeWordDetectedPayload,
}
