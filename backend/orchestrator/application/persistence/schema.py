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


ORCHESTRATIONS_TABLE: TableContract = TableContract(
    name="orchestrations",
    schema="orchestrator",
    columns=(
        ColumnContract("orchestration_id", str, nullable=False),
        ColumnContract("intent", str, nullable=True),
        ColumnContract("goal", str, nullable=True),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("created", "planning", "researching",
                                    "executing", "completed", "failed",
                                    "cancelled")),
        ColumnContract("created_at", datetime, nullable=False),
        ColumnContract("updated_at", datetime, nullable=True),
    ),
    primary_key="orchestration_id",
    indexes=("ix_orchestrations_status",),
)

WORKFLOWS_TABLE: TableContract = TableContract(
    name="workflows",
    schema="orchestrator",
    columns=(
        ColumnContract("workflow_id", str, nullable=False),
        ColumnContract("orchestration_id", str, nullable=True),
        ColumnContract("goal", str, nullable=True),
        ColumnContract("mode", str, nullable=False, max_length=16,
                       enum_values=("sequential", "parallel", "hybrid")),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("pending", "running", "completed",
                                    "failed")),
    ),
    primary_key="workflow_id",
    indexes=(
        "ix_workflows_orchestration_id",
        "ix_workflows_status",
    ),
)

WORKFLOW_STEPS_TABLE: TableContract = TableContract(
    name="workflow_steps",
    schema="orchestrator",
    columns=(
        ColumnContract("step_id", str, nullable=False),
        ColumnContract("workflow_id", str, nullable=True),
        ColumnContract("agent_role", str, nullable=False, max_length=16,
                       enum_values=("planner", "research", "automation",
                                    "memory", "knowledge", "policy")),
        ColumnContract("execution_order", int, nullable=False),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("pending", "running", "completed",
                                    "failed", "skipped")),
        ColumnContract("result", str, nullable=True),
        ColumnContract("failure_reason", str, nullable=True),
    ),
    primary_key="step_id",
    indexes=(
        "ix_workflow_steps_workflow_id",
        "ix_workflow_steps_status",
        "ix_workflow_steps_agent_role",
    ),
)

ORCHESTRATOR_OUTBOX_TABLE: TableContract = TableContract(
    name="outbox",
    schema="orchestrator",
    columns=(
        ColumnContract("event_id", str, nullable=False),
        ColumnContract("event_type", str, nullable=False, max_length=32,
                       enum_values=("orchestration.created",
                                    "orchestration.planning_started",
                                    "orchestration.research_started",
                                    "orchestration.execution_started",
                                    "orchestration.completed",
                                    "orchestration.failed",
                                    "orchestration.cancelled",
                                    "workflow.created",
                                    "workflow.completed",
                                    "workflow.failed",
                                    "workflow.step_started",
                                    "workflow.step_completed",
                                    "workflow.step_failed")),
        ColumnContract("aggregate_id", str, nullable=False),
        ColumnContract("occurred_at", datetime, nullable=False),
        ColumnContract("payload", str, nullable=True),
        ColumnContract("published", bool, nullable=False),
    ),
    primary_key="event_id",
    indexes=(
        "ix_orchestrator_outbox_unpublished",
        "ix_orchestrator_outbox_aggregate",
    ),
)
