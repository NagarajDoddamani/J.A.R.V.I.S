from __future__ import annotations

from uuid import UUID

from backend.policy.application.ports.outbox import PolicyOutboxPort
from backend.policy.application.ports.repository import (
    PolicyRepositoryPort,
    PolicyRuleRepositoryPort,
)
from backend.policy.application.use_cases.dto import (
    AddRuleRequest,
    AddRuleResponse,
)
from backend.policy.application.use_cases.exceptions import (
    PolicyNotFoundError,
)
from backend.policy.domain.factory import PolicyFactory
from backend.policy.domain.model import PolicyId


class AddRuleUseCase:
    def __init__(
        self,
        policy_repo: PolicyRepositoryPort,
        rule_repo: PolicyRuleRepositoryPort,
        outbox: PolicyOutboxPort,
    ) -> None:
        self._policy_repo = policy_repo
        self._rule_repo = rule_repo
        self._outbox = outbox

    def execute(self, request: AddRuleRequest) -> AddRuleResponse:
        policy_id = PolicyId(value=UUID(request.policy_id))
        policy = self._policy_repo.find_by_id(policy_id)
        if policy is None:
            raise PolicyNotFoundError(request.policy_id)

        rule, event = PolicyFactory.add_rule(
            policy=policy,
            condition=request.condition,
            action=request.action,
            priority=request.priority,
        )
        self._policy_repo.save(policy)
        self._rule_repo.save(rule, policy_id=request.policy_id)
        self._outbox.append(event)

        return AddRuleResponse(
            rule_id=str(rule.rule_id),
            policy_id=str(policy.policy_id),
            condition=str(rule.condition) if rule.condition else None,
            action=str(rule.action) if rule.action else None,
            priority=rule.priority,
            enabled=rule.enabled,
        )
