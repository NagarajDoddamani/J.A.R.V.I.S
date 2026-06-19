from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PolicyStorageDTO:
    policy_id: str
    name: str | None = None
    description: str | None = None
    status: str = "draft"
    priority: str = "medium"
    scope: str = "global"
    version: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class PolicyRuleStorageDTO:
    rule_id: str
    policy_id: str | None = None
    condition: str | None = None
    action: str | None = None
    priority: int = 0
    enabled: bool = True


@dataclass(frozen=True)
class PolicyEvaluationStorageDTO:
    evaluation_id: str
    policy_id: str | None = None
    status: str = "pending"
    decision: str | None = None
    result: str | None = None
    failure_reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class PolicyOutboxStorageDTO:
    event_id: str
    event_type: str
    aggregate_id: str
    occurred_at: datetime
    payload: str | None = None
    published: bool = False
