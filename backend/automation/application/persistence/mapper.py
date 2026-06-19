from __future__ import annotations

from typing import Protocol, Union

from backend.automation.application.persistence.dto import (
    AutomationExecutionStorageDTO,
    AutomationOutboxStorageDTO,
    AutomationStorageDTO,
    TriggerStorageDTO,
)
from backend.automation.domain.model import (
    ActionAdded,
    Automation,
    AutomationActivated,
    AutomationCreated,
    AutomationDisabled,
    AutomationExecution,
    AutomationExecutionCompleted,
    AutomationExecutionFailed,
    AutomationExecutionStarted,
    AutomationPaused,
    Trigger,
    TriggerAdded,
    TriggerDisabled,
    TriggerEnabled,
)

AutomationOutboxDomainEvent = Union[
    AutomationCreated,
    AutomationActivated,
    AutomationPaused,
    AutomationDisabled,
    AutomationExecutionStarted,
    AutomationExecutionCompleted,
    AutomationExecutionFailed,
    TriggerAdded,
    TriggerEnabled,
    TriggerDisabled,
    ActionAdded,
]


class AutomationMapper(Protocol):
    def domain_to_dto(
        self, automation: Automation
    ) -> AutomationStorageDTO:
        ...

    def dto_to_domain(
        self, dto: AutomationStorageDTO
    ) -> Automation:
        ...


class TriggerMapper(Protocol):
    def domain_to_dto(self, trigger: Trigger) -> TriggerStorageDTO:
        ...

    def dto_to_domain(self, dto: TriggerStorageDTO) -> Trigger:
        ...


class AutomationExecutionMapper(Protocol):
    def domain_to_dto(
        self, execution: AutomationExecution
    ) -> AutomationExecutionStorageDTO:
        ...

    def dto_to_domain(
        self, dto: AutomationExecutionStorageDTO
    ) -> AutomationExecution:
        ...


class AutomationOutboxMapper(Protocol):
    def event_to_dto(
        self, event: AutomationOutboxDomainEvent
    ) -> AutomationOutboxStorageDTO:
        ...

    def dto_to_event(
        self, dto: AutomationOutboxStorageDTO
    ) -> AutomationOutboxDomainEvent:
        ...
