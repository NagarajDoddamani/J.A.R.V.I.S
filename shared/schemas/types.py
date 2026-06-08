from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from shared.schemas.enums import ActorType, Classification


def new_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class CorrelationId(BaseModel):
    value: str = Field(default_factory=new_uuid)

    model_config = ConfigDict(extra="forbid")


class CausationId(BaseModel):
    value: str | None = None

    model_config = ConfigDict(extra="forbid")


class RequestId(BaseModel):
    value: str = Field(default_factory=new_uuid)

    model_config = ConfigDict(extra="forbid")


class Actor(BaseModel):
    type: ActorType
    id: str

    model_config = ConfigDict(extra="forbid")


class IdempotencyKey(BaseModel):
    value: str = Field(default_factory=new_uuid)

    model_config = ConfigDict(extra="forbid")


class CapabilityGrantId(BaseModel):
    value: str = Field(default_factory=new_uuid)

    model_config = ConfigDict(extra="forbid")


class ClassificationField(BaseModel):
    value: Classification

    model_config = ConfigDict(extra="forbid")
