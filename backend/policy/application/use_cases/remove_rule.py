from __future__ import annotations

from uuid import UUID

from backend.policy.application.ports.outbox import PolicyOutboxPort
from backend.policy.application.ports.repository import (
    PolicyRepositoryPort,
)
from backend.policy.application.use_cases.dto import (
    RemoveRuleRequest,
    RemoveRuleResponse,
)
from backend.policy.application.use_cases.exceptions import (
    PolicyNotFoundError,
)
from backend.policy.domain.factory import PolicyFactory
from backend.policy.domain.model import PolicyId, PolicyRuleId


class RemoveRuleUseCase:
    def __init__(
        self,
        policy_repo: PolicyRepositoryPort,
        outbox: PolicyOutboxPort,
    ) -> None:
        self._policy_repo = policy_repo
        self._outbox = outbox

    def execute(self, request: RemoveRuleRequest) -> RemoveRuleResponse:
        policy_id = PolicyId(value=UUID(request.policy_id))
        policy = self._policy_repo.find_by_id(policy_id)
        if policy is None:
            raise PolicyNotFoundError(request.policy_id)

        rule_id = PolicyRuleId(value=UUID(request.rule_id))
        PolicyFactory.remove_rule(policy=policy, rule_id=rule_id)
        self._policy_repo.save(policy)
        self._outbox.append(policy.events[-1])

        return RemoveRuleResponse(
            policy_id=str(policy.policy_id),
            rule_id=str(rule_id),
        )
