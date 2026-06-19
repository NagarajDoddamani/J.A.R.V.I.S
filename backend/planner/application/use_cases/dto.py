from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


# =====================================================================
# Response DTOs (shared by queries and command responses)
# =====================================================================


@dataclass
class TaskResponse:
    task_id: str
    plan_id: str | None = None
    description: str | None = None
    assigned_agent: str | None = None
    status: str = "pending"
    failure_reason: str | None = None
    estimated_duration: float | None = None


@dataclass
class PlanResponse:
    plan_id: str
    user_request: str | None = None
    goal: str | None = None
    priority: str = "normal"
    strategy: str = "sequential"
    status: str = "draft"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    failure_reason: str | None = None
    task_count: int = 0


# =====================================================================
# CreatePlan
# =====================================================================


@dataclass
class CreatePlanRequest:
    user_request: str
    goal: str
    priority: str = "normal"
    strategy: str = "sequential"


@dataclass
class CreatePlanResponse:
    plan_id: str
    user_request: str | None
    goal: str | None
    priority: str
    strategy: str
    status: str
    created_at: datetime


# =====================================================================
# Plan lifecycle commands
# =====================================================================


@dataclass
class PlanLifecycleRequest:
    plan_id: str


@dataclass
class PlanLifecycleResponse:
    plan_id: str
    status: str
    updated_at: datetime | None = None


@dataclass
class FailPlanRequest:
    plan_id: str
    failure_reason: str


@dataclass
class FailPlanResponse:
    plan_id: str
    status: str
    failure_reason: str | None = None
    updated_at: datetime | None = None


# =====================================================================
# AddTask
# =====================================================================


@dataclass
class AddTaskRequest:
    plan_id: str
    description: str


@dataclass
class AddTaskResponse:
    task_id: str
    plan_id: str | None
    description: str | None
    status: str


# =====================================================================
# Task lifecycle commands
# =====================================================================


@dataclass
class TaskLifecycleRequest:
    task_id: str


@dataclass
class TaskLifecycleResponse:
    task_id: str
    status: str


@dataclass
class AssignTaskRequest:
    task_id: str
    agent: str


@dataclass
class AssignTaskResponse:
    task_id: str
    assigned_agent: str | None
    status: str


@dataclass
class FailTaskRequest:
    task_id: str
    failure_reason: str


@dataclass
class FailTaskResponse:
    task_id: str
    status: str
    failure_reason: str | None = None


# =====================================================================
# Queries
# =====================================================================


@dataclass
class GetPlanRequest:
    plan_id: str


@dataclass
class ListPlansRequest:
    status: str | None = None
    priority: str | None = None


@dataclass
class ListPlansResponse:
    plans: list[PlanResponse] = field(default_factory=list)
    total: int = 0


@dataclass
class GetTaskRequest:
    task_id: str


@dataclass
class ListTasksRequest:
    status: str | None = None
    assigned_agent: str | None = None
    plan_id: str | None = None


@dataclass
class ListTasksResponse:
    tasks: list[TaskResponse] = field(default_factory=list)
    total: int = 0
