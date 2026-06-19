from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AutomationStorageDTO:
    automation_id: str
    name: str | None = None
    description: str | None = None
    status: str = "draft"
    execution_mode: str = "once"
    actions: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class TriggerStorageDTO:
    trigger_id: str
    automation_id: str | None = None
    trigger_type: str = "manual"
    expression: str | None = None
    enabled: bool = True


@dataclass(frozen=True)
class AutomationExecutionStorageDTO:
    execution_id: str
    automation_id: str | None = None
    status: str = "pending"
    result: str | None = None
    failure_reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class AutomationOutboxStorageDTO:
    event_id: str
    event_type: str
    aggregate_id: str
    occurred_at: datetime
    payload: str | None = None
    published: bool = False
