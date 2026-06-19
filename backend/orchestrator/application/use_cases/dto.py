from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


# =====================================================================
# Response DTOs (shared by queries and command responses)
# =====================================================================


@dataclass
class OrchestrationResponse:
    orchestration_id: str
    intent: str | None = None
    goal: str | None = None
    status: str = "created"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    workflow_count: int = 0


@dataclass
class WorkflowResponse:
    workflow_id: str
    goal: str | None = None
    mode: str = "sequential"
    status: str = "pending"
    step_count: int = 0


@dataclass
class WorkflowStepResponse:
    step_id: str
    agent_role: str = "research"
    execution_order: int = 0
    status: str = "pending"
    result: str | None = None
    failure_reason: str | None = None


# =====================================================================
# CreateOrchestration
# =====================================================================


@dataclass
class CreateOrchestrationRequest:
    intent: str
    goal: str


@dataclass
class CreateOrchestrationResponse:
    orchestration_id: str
    intent: str | None
    goal: str | None
    status: str
    created_at: datetime


# =====================================================================
# Orchestration lifecycle commands
# =====================================================================


@dataclass
class OrchestrationLifecycleRequest:
    orchestration_id: str


@dataclass
class OrchestrationLifecycleResponse:
    orchestration_id: str
    status: str
    updated_at: datetime | None = None


@dataclass
class FailOrchestrationRequest:
    orchestration_id: str
    failure_reason: str


@dataclass
class FailOrchestrationResponse:
    orchestration_id: str
    status: str
    failure_reason: str | None = None
    updated_at: datetime | None = None


# =====================================================================
# CreateWorkflow
# =====================================================================


@dataclass
class CreateWorkflowRequest:
    orchestration_id: str
    goal: str
    mode: str = "sequential"


@dataclass
class CreateWorkflowResponse:
    workflow_id: str
    orchestration_id: str | None
    goal: str | None
    mode: str
    status: str


# =====================================================================
# Workflow lifecycle commands
# =====================================================================


@dataclass
class WorkflowLifecycleRequest:
    workflow_id: str


@dataclass
class WorkflowLifecycleResponse:
    workflow_id: str
    status: str


@dataclass
class FailWorkflowRequest:
    workflow_id: str
    failure_reason: str


@dataclass
class FailWorkflowResponse:
    workflow_id: str
    status: str
    failure_reason: str | None = None


# =====================================================================
# AddStep
# =====================================================================


@dataclass
class AddStepRequest:
    workflow_id: str
    agent_role: str = "research"
    execution_order: int = 0


@dataclass
class AddStepResponse:
    step_id: str
    agent_role: str
    execution_order: int
    status: str


# =====================================================================
# Step lifecycle commands
# =====================================================================


@dataclass
class StepLifecycleRequest:
    step_id: str


@dataclass
class StepLifecycleResponse:
    step_id: str
    status: str


@dataclass
class CompleteStepRequest:
    step_id: str
    result: str


@dataclass
class CompleteStepResponse:
    step_id: str
    status: str
    result: str | None = None


@dataclass
class FailStepRequest:
    step_id: str
    failure_reason: str


@dataclass
class FailStepResponse:
    step_id: str
    status: str
    failure_reason: str | None = None


# =====================================================================
# Queries
# =====================================================================


@dataclass
class GetOrchestrationRequest:
    orchestration_id: str


@dataclass
class ListOrchestrationsRequest:
    status: str | None = None


@dataclass
class ListOrchestrationsResponse:
    orchestrations: list[OrchestrationResponse] = field(default_factory=list)
    total: int = 0


@dataclass
class GetWorkflowRequest:
    workflow_id: str


@dataclass
class ListWorkflowsRequest:
    status: str | None = None
    orchestration_id: str | None = None


@dataclass
class ListWorkflowsResponse:
    workflows: list[WorkflowResponse] = field(default_factory=list)
    total: int = 0


@dataclass
class GetStepRequest:
    step_id: str
