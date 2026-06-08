from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from shared.schemas.enums import RetentionPolicyType


class TraceContext(BaseModel):
    traceparent: str = ""
    tracestate: str = ""

    model_config = ConfigDict(extra="forbid")


class RetentionPolicy(BaseModel):
    policy: RetentionPolicyType
    expires_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class Source(BaseModel):
    type: str
    resource_id: str

    model_config = ConfigDict(extra="forbid")


class AttachmentRef(BaseModel):
    resource_id: str
    media_type: str

    model_config = ConfigDict(extra="forbid")


class Transition(BaseModel):
    type: str
    duration_ms: int

    model_config = ConfigDict(extra="forbid")


class CitationRef(BaseModel):
    source_id: str
    chunk_id: str

    model_config = ConfigDict(extra="forbid")


class ConsentScope(BaseModel):
    memory_types: list[str]
    source_types: list[str]

    model_config = ConfigDict(extra="forbid")


class ApprovalConstraints(BaseModel):
    expires_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")
