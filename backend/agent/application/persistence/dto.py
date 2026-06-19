from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AgentStorageDTO:
    agent_id: str
    agent_type: str = "coordinator"
    name: str | None = None
    status: str = "idle"
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class AgentTaskStorageDTO:
    task_id: str
    agent_id: str | None = None
    goal: str | None = None
    instruction: str | None = None
    status: str = "pending"
    result: str | None = None
    failure_reason: str | None = None


@dataclass(frozen=True)
class AgentExecutionStorageDTO:
    execution_id: str
    agent_id: str | None = None
    task_id: str | None = None
    status: str = "pending"
    result: str | None = None
    failure_reason: str | None = None


@dataclass(frozen=True)
class AgentOutboxStorageDTO:
    event_id: str
    event_type: str
    aggregate_id: str
    occurred_at: datetime
    payload: str | None = None
    published: bool = False
