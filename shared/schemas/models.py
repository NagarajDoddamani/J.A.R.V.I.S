"""Shared schema primitives (JDOS v1.2).

The Foundation layer in Phase 01 ships the cross-service envelope
primitives only. No business DTOs, no repositories, no use cases.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Identity primitives
# ---------------------------------------------------------------------------


class CorrelationId(BaseModel):
    """A v1.2 correlation identifier (UUIDv4 or UUIDv7 string)."""

    value: str = Field(default_factory=_new_uuid)

    model_config = ConfigDict(extra="forbid")


class CausationId(BaseModel):
    """A v1.2 causation identifier (UUIDv4 or UUIDv7 string)."""

    value: str = Field(default_factory=_new_uuid)

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Base messages
# ---------------------------------------------------------------------------


class BaseMessage(BaseModel):
    """Shared envelope fields for every command and event."""

    id: str = Field(default_factory=_new_uuid)
    timestamp: datetime = Field(default_factory=_utc_now)
    correlation_id: str = Field(default_factory=_new_uuid)
    causation_id: str | None = None
    version: str = "1.0"

    model_config = ConfigDict(extra="forbid")


class BaseCommand(BaseMessage):
    """Base class for all commands.

    The owning handler is the only component permitted to acknowledge
    and execute a command (Correction 1).
    """

    model_config = ConfigDict(extra="forbid")


class BaseEvent(BaseMessage):
    """Base class for all events.

    Events describe facts that already happened and may have multiple
    subscribers (Correction 1).
    """

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Envelopes
# ---------------------------------------------------------------------------


class CommandEnvelope(BaseModel, Generic[T]):
    """Envelope used by the API Gateway when emitting a command.

    The actual wire format on the NATS subject is the JSON serialized
    command envelope; the producer is responsible for filling
    ``correlation_id`` and ``causation_id`` before publishing.
    """

    command: str
    payload: T
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class EventEnvelope(BaseModel, Generic[T]):
    """Envelope used by services when publishing a factual event."""

    event: str
    payload: T
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")
