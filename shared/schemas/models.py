from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Generic, TypeVar, Optional, Any
import uuid

T = TypeVar("T")

class CorrelationId(BaseModel):
    value: str = Field(default_factory=lambda: str(uuid.uuid4()))

class RequestId(BaseModel):
    value: str = Field(default_factory=lambda: str(uuid.uuid4()))

class BaseMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "1.0"

class BaseCommand(BaseMessage):
    """Base class for all commands."""
    model_config = ConfigDict(extra="forbid")

class BaseEvent(BaseMessage):
    """Base class for all events."""
    model_config = ConfigDict(extra="forbid")

class CommandEnvelope(BaseModel, Generic[T]):
    command: str
    payload: T
    metadata: dict[str, Any] = Field(default_factory=dict)

class EventEnvelope(BaseModel, Generic[T]):
    event: str
    payload: T
    metadata: dict[str, Any] = Field(default_factory=dict)
