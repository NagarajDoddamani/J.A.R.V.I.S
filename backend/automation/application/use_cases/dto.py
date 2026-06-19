from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TriggerResponse:
    trigger_id: str
    trigger_type: str = "manual"
    expression: str | None = None
    enabled: bool = True


@dataclass
class ExecutionResponse:
    execution_id: str
    automation_id: str | None = None
    status: str = "pending"
    result: str | None = None
    failure_reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class AutomationResponse:
    automation_id: str
    name: str | None = None
    description: str | None = None
    status: str = "draft"
    execution_mode: str = "once"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    trigger_count: int = 0
    action_count: int = 0
    execution_count: int = 0


@dataclass
class CreateAutomationRequest:
    name: str
    description: str
    execution_mode: str = "once"


@dataclass
class CreateAutomationResponse:
    automation_id: str
    name: str | None
    description: str | None
    execution_mode: str
    status: str
    created_at: datetime


@dataclass
class AutomationLifecycleRequest:
    automation_id: str


@dataclass
class AutomationLifecycleResponse:
    automation_id: str
    status: str
    updated_at: datetime | None = None


@dataclass
class AddTriggerRequest:
    automation_id: str
    trigger_type: str = "manual"
    expression: str | None = None


@dataclass
class AddTriggerResponse:
    trigger_id: str
    automation_id: str | None
    trigger_type: str
    expression: str | None
    enabled: bool


@dataclass
class TriggerLifecycleRequest:
    trigger_id: str


@dataclass
class TriggerLifecycleResponse:
    trigger_id: str
    enabled: bool


@dataclass
class AddActionRequest:
    automation_id: str
    action_type: str


@dataclass
class AddActionResponse:
    automation_id: str
    action_type: str


@dataclass
class StartExecutionRequest:
    automation_id: str


@dataclass
class StartExecutionResponse:
    automation_id: str
    execution_id: str
    status: str
    started_at: datetime | None = None


@dataclass
class CompleteExecutionRequest:
    automation_id: str
    execution_id: str
    result: str


@dataclass
class CompleteExecutionResponse:
    execution_id: str
    automation_id: str | None
    status: str
    completed_at: datetime | None = None
    result: str | None = None


@dataclass
class FailExecutionRequest:
    automation_id: str
    execution_id: str
    failure_reason: str


@dataclass
class FailExecutionResponse:
    execution_id: str
    automation_id: str | None
    status: str
    completed_at: datetime | None = None
    failure_reason: str | None = None


@dataclass
class GetAutomationRequest:
    automation_id: str


@dataclass
class ListAutomationsRequest:
    status: str | None = None
    execution_mode: str | None = None


@dataclass
class ListAutomationsResponse:
    automations: list[AutomationResponse] = field(default_factory=list)
    total: int = 0


@dataclass
class GetTriggerRequest:
    trigger_id: str


@dataclass
class ListTriggersRequest:
    trigger_type: str | None = None
    enabled: bool | None = None


@dataclass
class ListTriggersResponse:
    triggers: list[TriggerResponse] = field(default_factory=list)
    total: int = 0


@dataclass
class GetExecutionRequest:
    execution_id: str


@dataclass
class ListExecutionsRequest:
    status: str | None = None
    automation_id: str | None = None


@dataclass
class ListExecutionsResponse:
    executions: list[ExecutionResponse] = field(default_factory=list)
    total: int = 0
