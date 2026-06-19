from __future__ import annotations

from backend.policy.application.ports.repository import (
    PolicyRuleRepositoryPort,
)
from backend.policy.application.use_cases.dto import (
    ListRulesRequest,
    ListRulesResponse,
    RuleResponse,
)
from backend.policy.domain.model import PolicyId
from uuid import UUID


class ListRulesUseCase:
    def __init__(
        self,
        rule_repo: PolicyRuleRepositoryPort,
    ) -> None:
        self._rule_repo = rule_repo

    def execute(self, request: ListRulesRequest) -> ListRulesResponse:
        if request.policy_id is not None:
            policy_id = PolicyId(value=UUID(request.policy_id))
            rules = self._rule_repo.find_by_policy_id(policy_id)
        elif request.enabled is not None:
            rules = self._rule_repo.find_enabled() if request.enabled else []
        else:
            rules = self._rule_repo.find_all()

        filtered = rules
        if request.priority is not None:
            filtered = [r for r in filtered if r.priority == request.priority]

        return ListRulesResponse(
            rules=[
                RuleResponse(
                    rule_id=str(r.rule_id),
                    condition=str(r.condition) if r.condition else None,
                    action=str(r.action) if r.action else None,
                    priority=r.priority,
                    enabled=r.enabled,
                )
                for r in filtered
            ],
            total=len(filtered),
        )
