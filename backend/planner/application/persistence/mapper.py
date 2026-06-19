from __future__ import annotations

from typing import Protocol, Union

from backend.planner.application.persistence.dto import (
    ExecutionStepStorageDTO,
    PlanStorageDTO,
    PlannerOutboxStorageDTO,
    TaskStorageDTO,
)
from backend.planner.domain.model import (
    ExecutionStep,
    Plan,
    PlanApproved,
    PlanCancelled,
    PlanCompleted,
    PlanCreated,
    PlanExecutionStarted,
    PlanFailed,
    PlanReady,
    Task,
    TaskAssigned,
    TaskCompleted,
    TaskCreated,
    TaskFailed,
)


PlannerOutboxDomainEvent = Union[
    PlanCreated,
    PlanApproved,
    PlanReady,
    PlanExecutionStarted,
    PlanCompleted,
    PlanFailed,
    PlanCancelled,
    TaskCreated,
    TaskAssigned,
    TaskCompleted,
    TaskFailed,
]


class PlanMapper(Protocol):
    def domain_to_dto(self, plan: Plan) -> PlanStorageDTO:
        ...

    def dto_to_domain(self, dto: PlanStorageDTO) -> Plan:
        ...


class TaskMapper(Protocol):
    def domain_to_dto(self, task: Task) -> TaskStorageDTO:
        ...

    def dto_to_domain(self, dto: TaskStorageDTO) -> Task:
        ...


class ExecutionStepMapper(Protocol):
    def domain_to_dto(
        self, step: ExecutionStep
    ) -> ExecutionStepStorageDTO:
        ...

    def dto_to_domain(
        self, dto: ExecutionStepStorageDTO
    ) -> ExecutionStep:
        ...


class PlannerOutboxMapper(Protocol):
    def event_to_dto(
        self, event: PlannerOutboxDomainEvent
    ) -> PlannerOutboxStorageDTO:
        ...

    def dto_to_event(
        self, dto: PlannerOutboxStorageDTO
    ) -> PlannerOutboxDomainEvent:
        ...
