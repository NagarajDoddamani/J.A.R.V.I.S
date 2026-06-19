from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PlanStorageDTO:
    plan_id: str
    user_request: str | None = None
    goal: str | None = None
    priority: str = "normal"
    strategy: str = "sequential"
    status: str = "draft"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    failure_reason: str | None = None


@dataclass(frozen=True)
class TaskStorageDTO:
    task_id: str
    plan_id: str | None = None
    description: str | None = None
    assigned_agent: str | None = None
    status: str = "pending"
    failure_reason: str | None = None
    estimated_duration: float | None = None


@dataclass(frozen=True)
class ExecutionStepStorageDTO:
    step_id: str
    task_id: str | None = None
    step_order: int = 0
    description: str = ""
    status: str = "pending"


@dataclass(frozen=True)
class PlannerOutboxStorageDTO:
    event_id: str
    event_type: str
    aggregate_id: str
    occurred_at: datetime
    payload: str | None = None
    published: bool = False
