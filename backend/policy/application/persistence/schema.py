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


POLICIES_TABLE: TableContract = TableContract(
    name="policies",
    schema="policy",
    columns=(
        ColumnContract("policy_id", str, nullable=False),
        ColumnContract("name", str, nullable=True),
        ColumnContract("description", str, nullable=True),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("draft", "active", "disabled", "archived")),
        ColumnContract("priority", str, nullable=False, max_length=16,
                       enum_values=("low", "medium", "high", "critical")),
        ColumnContract("scope", str, nullable=False, max_length=16,
                       enum_values=("global", "user", "agent", "automation", "workflow")),
        ColumnContract("version", str, nullable=True),
        ColumnContract("created_at", datetime, nullable=False),
        ColumnContract("updated_at", datetime, nullable=True),
    ),
    primary_key="policy_id",
    indexes=(
        "ix_policies_status",
        "ix_policies_priority",
        "ix_policies_scope",
    ),
)

POLICY_RULES_TABLE: TableContract = TableContract(
    name="rules",
    schema="policy",
    columns=(
        ColumnContract("rule_id", str, nullable=False),
        ColumnContract("policy_id", str, nullable=True),
        ColumnContract("condition", str, nullable=True),
        ColumnContract("action", str, nullable=True),
        ColumnContract("priority", int, nullable=False),
        ColumnContract("enabled", bool, nullable=False),
    ),
    primary_key="rule_id",
    indexes=(
        "ix_policy_rules_policy_id",
        "ix_policy_rules_priority",
        "ix_policy_rules_enabled",
    ),
)

POLICY_EVALUATIONS_TABLE: TableContract = TableContract(
    name="evaluations",
    schema="policy",
    columns=(
        ColumnContract("evaluation_id", str, nullable=False),
        ColumnContract("policy_id", str, nullable=True),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("pending", "evaluating", "completed", "failed")),
        ColumnContract("decision", str, nullable=True, max_length=16,
                       enum_values=("allow", "deny", "review")),
        ColumnContract("result", str, nullable=True),
        ColumnContract("failure_reason", str, nullable=True),
        ColumnContract("started_at", datetime, nullable=True),
        ColumnContract("completed_at", datetime, nullable=True),
    ),
    primary_key="evaluation_id",
    indexes=(
        "ix_policy_evaluations_policy_id",
        "ix_policy_evaluations_status",
    ),
)

POLICY_OUTBOX_TABLE: TableContract = TableContract(
    name="outbox",
    schema="policy",
    columns=(
        ColumnContract("event_id", str, nullable=False),
        ColumnContract("event_type", str, nullable=False, max_length=32,
                       enum_values=("policy.created",
                                    "policy.activated",
                                    "policy.disabled",
                                    "policy.archived",
                                    "policy.rule_added",
                                    "policy.rule_removed",
                                    "policy.rule_enabled",
                                    "policy.rule_disabled",
                                    "policy.evaluation_started",
                                    "policy.evaluation_completed",
                                    "policy.evaluation_failed",)),
        ColumnContract("aggregate_id", str, nullable=False),
        ColumnContract("occurred_at", datetime, nullable=False),
        ColumnContract("payload", str, nullable=True),
        ColumnContract("published", bool, nullable=False),
    ),
    primary_key="event_id",
    indexes=(
        "ix_policy_outbox_unpublished",
        "ix_policy_outbox_aggregate",
    ),
)
