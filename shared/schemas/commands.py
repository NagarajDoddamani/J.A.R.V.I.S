from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Payload DTOs — each command envelope carries one of these as its ``payload``.
# All use ``extra="forbid"`` so unknown fields are rejected.
# ---------------------------------------------------------------------------


class UserRequestCommandPayload(BaseModel):
    request_id: str
    conversation_id: str | None = None
    request_content_ref: str
    input_mode: str = "text"
    language: str = "en"
    attachment_refs: list[dict[str, str]] = Field(default_factory=list)
    requested_capability_refs: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ShowNotificationCommandPayload(BaseModel):
    notification_id: str
    notification_content_ref: str
    priority: str = "normal"
    sensitive: bool = False
    expires_at: datetime

    model_config = ConfigDict(extra="forbid")


class UpdateWallpaperCommandPayload(BaseModel):
    wallpaper_update_id: str
    display_scope: str = "all"
    scene_id: str
    state: str = "processing"
    intensity: float = 0.6
    transition: dict[str, str | int] | None = None
    expires_at: datetime

    model_config = ConfigDict(extra="forbid")


class CreateMemoryCommandPayload(BaseModel):
    memory_id: str
    consent_id: str
    memory_content_ref: str
    source: dict[str, str]
    retention_policy: dict[str, str | None]
    sensitivity: str = "internal"

    model_config = ConfigDict(extra="forbid")


class StartResearchCommandPayload(BaseModel):
    research_id: str
    request_id: str
    query_ref: str
    source_scopes: list[str] = Field(default_factory=list)
    network_allowed: bool = False

    model_config = ConfigDict(extra="forbid")


class OpenApplicationCommandPayload(BaseModel):
    action_id: str
    application_id: str
    launch_mode: str = "user_approved"
    capability_grant_id: str

    model_config = ConfigDict(extra="forbid")


class CancelRequestCommandPayload(BaseModel):
    request_id: str
    reason: str = "user_requested"

    model_config = ConfigDict(extra="forbid")


class RecordConsentCommandPayload(BaseModel):
    consent_id: str
    purpose: str
    scope: dict[str, list[str]]
    retention_policy: dict[str, str | None]
    decision: str = "approve"

    model_config = ConfigDict(extra="forbid")


class RevokeConsentCommandPayload(BaseModel):
    consent_id: str

    model_config = ConfigDict(extra="forbid")


class DeleteMemoryCommandPayload(BaseModel):
    memory_id: str
    consent_id: str

    model_config = ConfigDict(extra="forbid")


class UpdateMemoryCommandPayload(BaseModel):
    memory_id: str
    memory_content_ref: str | None = None
    sensitivity: str | None = None
    retention_policy: dict[str, str | None] | None = None

    model_config = ConfigDict(extra="forbid")


class UpdateSettingsCommandPayload(BaseModel):
    settings: dict[str, object]

    model_config = ConfigDict(extra="forbid")


class RegisterKnowledgeSourceCommandPayload(BaseModel):
    source_id: str
    kind: str
    local_path_token: str
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    retention: str = "reference_source"

    model_config = ConfigDict(extra="forbid")


class DeleteKnowledgeSourceCommandPayload(BaseModel):
    source_id: str

    model_config = ConfigDict(extra="forbid")


class ReindexKnowledgeSourceCommandPayload(BaseModel):
    source_id: str

    model_config = ConfigDict(extra="forbid")


class AcknowledgeNotificationCommandPayload(BaseModel):
    notification_id: str

    model_config = ConfigDict(extra="forbid")


class DismissNotificationCommandPayload(BaseModel):
    notification_id: str

    model_config = ConfigDict(extra="forbid")


class InvokeNotificationActionCommandPayload(BaseModel):
    notification_id: str
    action_id: str

    model_config = ConfigDict(extra="forbid")


class ApproveActionCommandPayload(BaseModel):
    approval_id: str
    decision: str = "approve_once"
    constraints: dict[str, str | None] | None = None

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Registry — maps command_type string to payload model class
# ---------------------------------------------------------------------------

COMMAND_PAYLOAD_REGISTRY: dict[str, type[BaseModel]] = {
    "USER_REQUEST_COMMAND": UserRequestCommandPayload,
    "SHOW_NOTIFICATION_COMMAND": ShowNotificationCommandPayload,
    "UPDATE_WALLPAPER_COMMAND": UpdateWallpaperCommandPayload,
    "CREATE_MEMORY_COMMAND": CreateMemoryCommandPayload,
    "START_RESEARCH_COMMAND": StartResearchCommandPayload,
    "OPEN_APPLICATION_COMMAND": OpenApplicationCommandPayload,
    "CANCEL_REQUEST_COMMAND": CancelRequestCommandPayload,
    "RECORD_CONSENT_COMMAND": RecordConsentCommandPayload,
    "REVOKE_CONSENT_COMMAND": RevokeConsentCommandPayload,
    "DELETE_MEMORY_COMMAND": DeleteMemoryCommandPayload,
    "UPDATE_MEMORY_COMMAND": UpdateMemoryCommandPayload,
    "UPDATE_SETTINGS_COMMAND": UpdateSettingsCommandPayload,
    "REGISTER_KNOWLEDGE_SOURCE_COMMAND": RegisterKnowledgeSourceCommandPayload,
    "DELETE_KNOWLEDGE_SOURCE_COMMAND": DeleteKnowledgeSourceCommandPayload,
    "REINDEX_KNOWLEDGE_SOURCE_COMMAND": ReindexKnowledgeSourceCommandPayload,
    "ACKNOWLEDGE_NOTIFICATION_COMMAND": AcknowledgeNotificationCommandPayload,
    "DISMISS_NOTIFICATION_COMMAND": DismissNotificationCommandPayload,
    "INVOKE_NOTIFICATION_ACTION_COMMAND": InvokeNotificationActionCommandPayload,
    "APPROVE_ACTION_COMMAND": ApproveActionCommandPayload,
}
