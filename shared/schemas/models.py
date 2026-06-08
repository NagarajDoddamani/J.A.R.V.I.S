from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from shared.schemas.enums import Classification
from shared.schemas.types import Actor, new_uuid, utc_now


class CommandEnvelope(BaseModel):
    command_id: str = Field(default_factory=new_uuid)
    command_type: str
    command_version: int = 1
    issued_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime
    producer: str
    correlation_id: str = Field(default_factory=new_uuid)
    causation_id: str = Field(default_factory=new_uuid)
    idempotency_key: str = Field(default_factory=new_uuid)
    actor: Actor
    classification: Classification
    capability_grant_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=new_uuid)
    event_type: str
    event_version: int = 1
    occurred_at: datetime = Field(default_factory=utc_now)
    producer: str
    correlation_id: str = Field(default_factory=new_uuid)
    causation_id: str = Field(default_factory=new_uuid)
    actor: Actor
    classification: Classification
    trace_context: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")
