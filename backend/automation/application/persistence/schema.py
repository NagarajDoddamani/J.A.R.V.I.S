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


AUTOMATIONS_TABLE: TableContract = TableContract(
    name="automations",
    schema="automation",
    columns=(
        ColumnContract("automation_id", str, nullable=False),
        ColumnContract("name", str, nullable=True),
        ColumnContract("description", str, nullable=True),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("draft", "active", "paused", "running",
                                    "completed", "failed", "disabled")),
        ColumnContract("execution_mode", str, nullable=False, max_length=16,
                       enum_values=("once", "recurring", "continuous")),
        ColumnContract("actions", str, nullable=True),
        ColumnContract("created_at", datetime, nullable=False),
        ColumnContract("updated_at", datetime, nullable=True),
    ),
    primary_key="automation_id",
    indexes=(
        "ix_automations_status",
        "ix_automations_execution_mode",
    ),
)

TRIGGERS_TABLE: TableContract = TableContract(
    name="triggers",
    schema="automation",
    columns=(
        ColumnContract("trigger_id", str, nullable=False),
        ColumnContract("automation_id", str, nullable=True),
        ColumnContract("trigger_type", str, nullable=False, max_length=16,
                       enum_values=("manual", "scheduled", "event", "webhook")),
        ColumnContract("expression", str, nullable=True),
        ColumnContract("enabled", bool, nullable=False),
    ),
    primary_key="trigger_id",
    indexes=(
        "ix_triggers_automation_id",
        "ix_triggers_trigger_type",
        "ix_triggers_enabled",
    ),
)

AUTOMATION_EXECUTIONS_TABLE: TableContract = TableContract(
    name="executions",
    schema="automation",
    columns=(
        ColumnContract("execution_id", str, nullable=False),
        ColumnContract("automation_id", str, nullable=True),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("pending", "running", "completed",
                                    "failed", "cancelled")),
        ColumnContract("result", str, nullable=True),
        ColumnContract("failure_reason", str, nullable=True),
        ColumnContract("started_at", datetime, nullable=True),
        ColumnContract("completed_at", datetime, nullable=True),
    ),
    primary_key="execution_id",
    indexes=(
        "ix_executions_automation_id",
        "ix_executions_status",
    ),
)

AUTOMATION_OUTBOX_TABLE: TableContract = TableContract(
    name="outbox",
    schema="automation",
    columns=(
        ColumnContract("event_id", str, nullable=False),
        ColumnContract("event_type", str, nullable=False, max_length=32,
                       enum_values=("automation.created",
                                    "automation.activated",
                                    "automation.paused",
                                    "automation.disabled",
                                    "automation.execution_started",
                                    "automation.execution_completed",
                                    "automation.execution_failed",
                                    "automation.trigger_added",
                                    "automation.trigger_enabled",
                                    "automation.trigger_disabled",
                                    "automation.action_added",)),
        ColumnContract("aggregate_id", str, nullable=False),
        ColumnContract("occurred_at", datetime, nullable=False),
        ColumnContract("payload", str, nullable=True),
        ColumnContract("published", bool, nullable=False),
    ),
    primary_key="event_id",
    indexes=(
        "ix_automation_outbox_unpublished",
        "ix_automation_outbox_aggregate",
    ),
)
