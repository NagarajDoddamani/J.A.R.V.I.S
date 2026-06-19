from __future__ import annotations

from uuid import UUID

from backend.policy.application.ports.repository import (
    PolicyRepositoryPort,
)
from backend.policy.application.use_cases.dto import (
    GetPolicyRequest,
    PolicyResponse,
)
from backend.policy.application.use_cases.exceptions import (
    PolicyNotFoundError,
)
from backend.policy.domain.model import PolicyId


class GetPolicyUseCase:
    def __init__(
        self,
        policy_repo: PolicyRepositoryPort,
    ) -> None:
        self._policy_repo = policy_repo

    def execute(self, request: GetPolicyRequest) -> PolicyResponse:
        policy_id = PolicyId(value=UUID(request.policy_id))
        policy = self._policy_repo.find_by_id(policy_id)
        if policy is None:
            raise PolicyNotFoundError(request.policy_id)

        return PolicyResponse(
            policy_id=str(policy.policy_id),
            name=str(policy.name) if policy.name else None,
            description=str(policy.description) if policy.description else None,
            status=policy.status.value,
            priority=policy.priority.value,
            scope=policy.scope.value,
            version=str(policy.version) if policy.version else None,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
            rule_count=len(policy.rules),
            evaluation_count=len(policy.evaluations),
        )
