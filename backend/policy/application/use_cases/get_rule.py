from __future__ import annotations

from uuid import UUID

from backend.policy.application.ports.repository import (
    PolicyRuleRepositoryPort,
)
from backend.policy.application.use_cases.dto import (
    GetRuleRequest,
    RuleResponse,
)
from backend.policy.application.use_cases.exceptions import (
    PolicyRuleNotFoundError,
)
from backend.policy.domain.model import PolicyRuleId


class GetRuleUseCase:
    def __init__(
        self,
        rule_repo: PolicyRuleRepositoryPort,
    ) -> None:
        self._rule_repo = rule_repo

    def execute(self, request: GetRuleRequest) -> RuleResponse:
        rule_id = PolicyRuleId(value=UUID(request.rule_id))
        rule = self._rule_repo.find_by_id(rule_id)
        if rule is None:
            raise PolicyRuleNotFoundError(request.rule_id)

        return RuleResponse(
            rule_id=str(rule.rule_id),
            condition=str(rule.condition) if rule.condition else None,
            action=str(rule.action) if rule.action else None,
            priority=rule.priority,
            enabled=rule.enabled,
        )
