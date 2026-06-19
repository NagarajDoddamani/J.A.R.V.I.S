from __future__ import annotations

from typing import Protocol, Union

from backend.orchestrator.application.persistence.dto import (
    OrchestrationStorageDTO,
    OrchestratorOutboxStorageDTO,
    WorkflowStepStorageDTO,
    WorkflowStorageDTO,
)
from backend.orchestrator.domain.model import (
    Orchestration,
    OrchestrationCancelled,
    OrchestrationCompleted,
    OrchestrationCreated,
    OrchestrationExecutionStarted,
    OrchestrationFailed,
    OrchestrationPlanningStarted,
    OrchestrationResearchStarted,
    Workflow,
    WorkflowCompleted,
    WorkflowCreated,
    WorkflowFailed,
    WorkflowStep,
    WorkflowStepCompleted,
    WorkflowStepFailed,
    WorkflowStepStarted,
)


OrchestratorOutboxDomainEvent = Union[
    OrchestrationCreated,
    OrchestrationPlanningStarted,
    OrchestrationResearchStarted,
    OrchestrationExecutionStarted,
    OrchestrationCompleted,
    OrchestrationFailed,
    OrchestrationCancelled,
    WorkflowCreated,
    WorkflowCompleted,
    WorkflowFailed,
    WorkflowStepStarted,
    WorkflowStepCompleted,
    WorkflowStepFailed,
]


class OrchestrationMapper(Protocol):
    def domain_to_dto(
        self, orchestration: Orchestration
    ) -> OrchestrationStorageDTO:
        ...

    def dto_to_domain(
        self, dto: OrchestrationStorageDTO
    ) -> Orchestration:
        ...


class WorkflowMapper(Protocol):
    def domain_to_dto(self, workflow: Workflow) -> WorkflowStorageDTO:
        ...

    def dto_to_domain(self, dto: WorkflowStorageDTO) -> Workflow:
        ...


class WorkflowStepMapper(Protocol):
    def domain_to_dto(self, step: WorkflowStep) -> WorkflowStepStorageDTO:
        ...

    def dto_to_domain(self, dto: WorkflowStepStorageDTO) -> WorkflowStep:
        ...


class OrchestratorOutboxMapper(Protocol):
    def event_to_dto(
        self, event: OrchestratorOutboxDomainEvent
    ) -> OrchestratorOutboxStorageDTO:
        ...

    def dto_to_event(
        self, dto: OrchestratorOutboxStorageDTO
    ) -> OrchestratorOutboxDomainEvent:
        ...
