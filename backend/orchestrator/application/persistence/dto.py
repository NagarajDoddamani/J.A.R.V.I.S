from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OrchestrationStorageDTO:
    orchestration_id: str
    intent: str | None = None
    goal: str | None = None
    status: str = "created"
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class WorkflowStorageDTO:
    workflow_id: str
    orchestration_id: str | None = None
    goal: str | None = None
    mode: str = "sequential"
    status: str = "pending"


@dataclass(frozen=True)
class WorkflowStepStorageDTO:
    step_id: str
    workflow_id: str | None = None
    agent_role: str = "research"
    execution_order: int = 0
    status: str = "pending"
    result: str | None = None
    failure_reason: str | None = None


@dataclass(frozen=True)
class OrchestratorOutboxStorageDTO:
    event_id: str
    event_type: str
    aggregate_id: str
    occurred_at: datetime
    payload: str | None = None
    published: bool = False
