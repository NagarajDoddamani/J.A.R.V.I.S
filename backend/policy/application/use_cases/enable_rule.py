from __future__ import annotations

from uuid import UUID

from backend.policy.application.ports.outbox import PolicyOutboxPort
from backend.policy.application.ports.repository import (
    PolicyRepositoryPort,
    PolicyRuleRepositoryPort,
)
from backend.policy.application.use_cases.dto import (
    RuleLifecycleRequest,
    RuleLifecycleResponse,
)
from backend.policy.application.use_cases.exceptions import (
    PolicyRuleNotFoundError,
)
from backend.policy.domain.factory import PolicyFactory
from backend.policy.domain.model import PolicyRuleId


class EnableRuleUseCase:
    def __init__(
        self,
        rule_repo: PolicyRuleRepositoryPort,
        policy_repo: PolicyRepositoryPort,
        outbox: PolicyOutboxPort,
    ) -> None:
        self._rule_repo = rule_repo
        self._policy_repo = policy_repo
        self._outbox = outbox

    def execute(self, request: RuleLifecycleRequest) -> RuleLifecycleResponse:
        rule_id = PolicyRuleId(value=UUID(request.rule_id))
        rule = self._rule_repo.find_by_id(rule_id)
        if rule is None:
            raise PolicyRuleNotFoundError(request.rule_id)

        policy_id = rule.policy_id
        if policy_id is None:
            raise PolicyRuleNotFoundError(request.rule_id)
        policy = self._policy_repo.find_by_id(policy_id)
        if policy is None:
            raise PolicyRuleNotFoundError(request.rule_id)

        PolicyFactory.enable_rule(policy=policy, rule_id=rule_id)

        modified_rule = next(
            r for r in policy.rules if r.rule_id == rule_id
        )
        self._rule_repo.save(modified_rule)
        self._policy_repo.save(policy)
        self._outbox.append(policy.events[-1])

        return RuleLifecycleResponse(
            rule_id=str(rule_id),
            enabled=modified_rule.enabled,
        )
