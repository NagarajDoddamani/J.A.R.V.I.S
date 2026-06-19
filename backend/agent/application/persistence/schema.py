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


AGENTS_TABLE: TableContract = TableContract(
    name="agents",
    schema="agent",
    columns=(
        ColumnContract("agent_id", str, nullable=False),
        ColumnContract("agent_type", str, nullable=False, max_length=16,
                       enum_values=("coordinator", "research", "knowledge",
                                    "automation")),
        ColumnContract("name", str, nullable=True),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("idle", "active", "paused", "disabled")),
        ColumnContract("created_at", datetime, nullable=False),
        ColumnContract("updated_at", datetime, nullable=True),
    ),
    primary_key="agent_id",
    indexes=(
        "ix_agents_status",
        "ix_agents_agent_type",
    ),
)

AGENT_TASKS_TABLE: TableContract = TableContract(
    name="agent_tasks",
    schema="agent",
    columns=(
        ColumnContract("task_id", str, nullable=False),
        ColumnContract("agent_id", str, nullable=True),
        ColumnContract("goal", str, nullable=True),
        ColumnContract("instruction", str, nullable=True),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("pending", "running", "completed",
                                    "failed", "cancelled")),
        ColumnContract("result", str, nullable=True),
        ColumnContract("failure_reason", str, nullable=True),
    ),
    primary_key="task_id",
    indexes=(
        "ix_agent_tasks_agent_id",
        "ix_agent_tasks_status",
    ),
)

AGENT_EXECUTIONS_TABLE: TableContract = TableContract(
    name="agent_executions",
    schema="agent",
    columns=(
        ColumnContract("execution_id", str, nullable=False),
        ColumnContract("agent_id", str, nullable=True),
        ColumnContract("task_id", str, nullable=True),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("pending", "executing", "completed",
                                    "failed")),
        ColumnContract("result", str, nullable=True),
        ColumnContract("failure_reason", str, nullable=True),
    ),
    primary_key="execution_id",
    indexes=(
        "ix_agent_executions_agent_id",
        "ix_agent_executions_task_id",
        "ix_agent_executions_status",
    ),
)

AGENT_OUTBOX_TABLE: TableContract = TableContract(
    name="agent_outbox",
    schema="agent",
    columns=(
        ColumnContract("event_id", str, nullable=False),
        ColumnContract("event_type", str, nullable=False, max_length=32,
                       enum_values=("agent.created",
                                    "agent.activated",
                                    "agent.paused",
                                    "agent.disabled",
                                    "agent.task_created",
                                    "agent.task_started",
                                    "agent.task_completed",
                                    "agent.task_failed",
                                    "agent.task_cancelled",
                                    "agent.execution_started",
                                    "agent.execution_completed",
                                    "agent.execution_failed")),
        ColumnContract("aggregate_id", str, nullable=False),
        ColumnContract("occurred_at", datetime, nullable=False),
        ColumnContract("payload", str, nullable=True),
        ColumnContract("published", bool, nullable=False),
    ),
    primary_key="event_id",
    indexes=(
        "ix_agent_outbox_unpublished",
        "ix_agent_outbox_aggregate",
    ),
)
