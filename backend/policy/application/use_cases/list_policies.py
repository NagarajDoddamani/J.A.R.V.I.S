from __future__ import annotations

from backend.policy.application.ports.repository import (
    PolicyRepositoryPort,
)
from backend.policy.application.use_cases.dto import (
    ListPoliciesRequest,
    ListPoliciesResponse,
    PolicyResponse,
)
from backend.policy.domain.model import PolicyPriority, PolicyScope, PolicyStatus


class ListPoliciesUseCase:
    def __init__(
        self,
        policy_repo: PolicyRepositoryPort,
    ) -> None:
        self._policy_repo = policy_repo

    def execute(
        self, request: ListPoliciesRequest
    ) -> ListPoliciesResponse:
        if request.status is not None:
            status = PolicyStatus(request.status)
            policies = self._policy_repo.find_by_status(status)
        elif request.priority is not None:
            priority = PolicyPriority(request.priority)
            policies = self._policy_repo.find_by_priority(priority)
        elif request.scope is not None:
            scope = PolicyScope(request.scope)
            policies = self._policy_repo.find_by_scope(scope)
        else:
            policies = self._policy_repo.find_all()

        return ListPoliciesResponse(
            policies=[
                PolicyResponse(
                    policy_id=str(p.policy_id),
                    name=str(p.name) if p.name else None,
                    description=str(p.description) if p.description else None,
                    status=p.status.value,
                    priority=p.priority.value,
                    scope=p.scope.value,
                    version=str(p.version) if p.version else None,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                    rule_count=len(p.rules),
                    evaluation_count=len(p.evaluations),
                )
                for p in policies
            ],
            total=len(policies),
        )
