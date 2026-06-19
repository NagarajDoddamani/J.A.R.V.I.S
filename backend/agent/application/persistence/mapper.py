from __future__ import annotations

from typing import Protocol, Union

from backend.agent.application.persistence.dto import (
    AgentExecutionStorageDTO,
    AgentOutboxStorageDTO,
    AgentStorageDTO,
    AgentTaskStorageDTO,
)
from backend.agent.domain.model import (
    Agent,
    AgentActivated,
    AgentCreated,
    AgentDisabled,
    AgentExecution,
    AgentExecutionCompleted,
    AgentExecutionFailed,
    AgentExecutionStarted,
    AgentPaused,
    AgentTask,
    AgentTaskCancelled,
    AgentTaskCompleted,
    AgentTaskCreated,
    AgentTaskFailed,
    AgentTaskStarted,
)

AgentOutboxDomainEvent = Union[
    AgentCreated,
    AgentActivated,
    AgentPaused,
    AgentDisabled,
    AgentTaskCreated,
    AgentTaskStarted,
    AgentTaskCompleted,
    AgentTaskFailed,
    AgentTaskCancelled,
    AgentExecutionStarted,
    AgentExecutionCompleted,
    AgentExecutionFailed,
]


class AgentMapper(Protocol):
    def domain_to_dto(self, agent: Agent) -> AgentStorageDTO:
        ...

    def dto_to_domain(self, dto: AgentStorageDTO) -> Agent:
        ...


class AgentTaskMapper(Protocol):
    def domain_to_dto(self, task: AgentTask) -> AgentTaskStorageDTO:
        ...

    def dto_to_domain(self, dto: AgentTaskStorageDTO) -> AgentTask:
        ...


class AgentExecutionMapper(Protocol):
    def domain_to_dto(self, execution: AgentExecution) -> AgentExecutionStorageDTO:
        ...

    def dto_to_domain(self, dto: AgentExecutionStorageDTO) -> AgentExecution:
        ...


class AgentOutboxMapper(Protocol):
    def event_to_dto(
        self, event: AgentOutboxDomainEvent
    ) -> AgentOutboxStorageDTO:
        ...

    def dto_to_event(
        self, dto: AgentOutboxStorageDTO
    ) -> AgentOutboxDomainEvent:
        ...
