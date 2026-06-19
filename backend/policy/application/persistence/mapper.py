from __future__ import annotations

from typing import Protocol, Union

from backend.policy.application.persistence.dto import (
    PolicyEvaluationStorageDTO,
    PolicyOutboxStorageDTO,
    PolicyRuleStorageDTO,
    PolicyStorageDTO,
)
from backend.policy.domain.model import (
    Policy,
    PolicyActivated,
    PolicyArchived,
    PolicyCreated,
    PolicyDisabled,
    PolicyEvaluation,
    PolicyEvaluationCompleted,
    PolicyEvaluationFailed,
    PolicyEvaluationStarted,
    PolicyRule,
    PolicyRuleAdded,
    PolicyRuleDisabled,
    PolicyRuleEnabled,
    PolicyRuleRemoved,
)

PolicyOutboxDomainEvent = Union[
    PolicyCreated,
    PolicyActivated,
    PolicyDisabled,
    PolicyArchived,
    PolicyRuleAdded,
    PolicyRuleRemoved,
    PolicyRuleEnabled,
    PolicyRuleDisabled,
    PolicyEvaluationStarted,
    PolicyEvaluationCompleted,
    PolicyEvaluationFailed,
]


class PolicyMapper(Protocol):
    def domain_to_dto(self, policy: Policy) -> PolicyStorageDTO:
        ...

    def dto_to_domain(self, dto: PolicyStorageDTO) -> Policy:
        ...


class PolicyRuleMapper(Protocol):
    def domain_to_dto(self, rule: PolicyRule) -> PolicyRuleStorageDTO:
        ...

    def dto_to_domain(self, dto: PolicyRuleStorageDTO) -> PolicyRule:
        ...


class PolicyEvaluationMapper(Protocol):
    def domain_to_dto(
        self, evaluation: PolicyEvaluation
    ) -> PolicyEvaluationStorageDTO:
        ...

    def dto_to_domain(
        self, dto: PolicyEvaluationStorageDTO
    ) -> PolicyEvaluation:
        ...


class PolicyOutboxMapper(Protocol):
    def event_to_dto(
        self, event: PolicyOutboxDomainEvent
    ) -> PolicyOutboxStorageDTO:
        ...

    def dto_to_event(
        self, dto: PolicyOutboxStorageDTO
    ) -> PolicyOutboxDomainEvent:
        ...
