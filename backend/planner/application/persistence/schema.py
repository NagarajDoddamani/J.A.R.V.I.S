from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ColumnContract:
    name: str
    py_type: type[Any]
    nullable: bool
    max_length: int | None = None
    enum_values: tuple[str, ...] | None = None


@dataclass(frozen=True)
class TableContract:
    name: str
    schema: str
    columns: tuple[ColumnContract, ...]
    primary_key: str | tuple[str, ...]
    indexes: tuple[str, ...] = ()
    unique_constraints: tuple[str, ...] = ()


PLANS_TABLE: TableContract = TableContract(
    name="plans",
    schema="planner",
    columns=(
        ColumnContract("plan_id", str, nullable=False),
        ColumnContract("user_request", str, nullable=True),
        ColumnContract("goal", str, nullable=True),
        ColumnContract("priority", str, nullable=False, max_length=16,
                       enum_values=("low", "normal", "high", "critical")),
        ColumnContract("strategy", str, nullable=False, max_length=16,
                       enum_values=("sequential", "parallel", "hybrid")),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("draft", "approved", "planning", "ready",
                                    "executing", "completed", "failed",
                                    "cancelled")),
        ColumnContract("created_at", datetime, nullable=False),
        ColumnContract("updated_at", datetime, nullable=True),
        ColumnContract("failure_reason", str, nullable=True),
    ),
    primary_key="plan_id",
    indexes=(
        "ix_plans_status",
        "ix_plans_priority",
    ),
)

TASKS_TABLE: TableContract = TableContract(
    name="tasks",
    schema="planner",
    columns=(
        ColumnContract("task_id", str, nullable=False),
        ColumnContract("plan_id", str, nullable=True),
        ColumnContract("description", str, nullable=True),
        ColumnContract("assigned_agent", str, nullable=True, max_length=16,
                       enum_values=("planner", "research", "automation",
                                    "memory", "knowledge", "notification",
                                    "policy")),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("pending", "assigned", "running",
                                    "completed", "failed", "cancelled")),
        ColumnContract("failure_reason", str, nullable=True),
        ColumnContract("estimated_duration", float, nullable=True),
    ),
    primary_key="task_id",
    indexes=(
        "ix_tasks_plan_id",
        "ix_tasks_status",
        "ix_tasks_assigned_agent",
    ),
)

EXECUTION_STEPS_TABLE: TableContract = TableContract(
    name="execution_steps",
    schema="planner",
    columns=(
        ColumnContract("step_id", str, nullable=False),
        ColumnContract("task_id", str, nullable=True),
        ColumnContract("step_order", int, nullable=False),
        ColumnContract("description", str, nullable=False),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("pending", "assigned", "running",
                                    "completed", "failed", "cancelled")),
    ),
    primary_key="step_id",
    indexes=(
        "ix_execution_steps_task_id",
        "ix_execution_steps_step_order",
    ),
)

PLANNER_OUTBOX_TABLE: TableContract = TableContract(
    name="outbox",
    schema="planner",
    columns=(
        ColumnContract("event_id", str, nullable=False),
        ColumnContract("event_type", str, nullable=False, max_length=32,
                       enum_values=("plan.created",
                                    "plan.approved",
                                    "plan.ready",
                                    "plan.execution_started",
                                    "plan.completed",
                                    "plan.failed",
                                    "plan.cancelled",
                                    "task.created",
                                    "task.assigned",
                                    "task.completed",
                                    "task.failed")),
        ColumnContract("aggregate_id", str, nullable=False),
        ColumnContract("occurred_at", datetime, nullable=False),
        ColumnContract("payload", str, nullable=True),
        ColumnContract("published", bool, nullable=False),
    ),
    primary_key="event_id",
    indexes=(
        "ix_planner_outbox_unpublished",
        "ix_planner_outbox_aggregate",
    ),
)
