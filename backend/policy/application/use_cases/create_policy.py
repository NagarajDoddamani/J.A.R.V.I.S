from __future__ import annotations

from backend.policy.application.ports.outbox import PolicyOutboxPort
from backend.policy.application.ports.repository import (
    PolicyRepositoryPort,
)
from backend.policy.application.use_cases.dto import (
    CreatePolicyRequest,
    CreatePolicyResponse,
)
from backend.policy.domain.factory import PolicyFactory


class CreatePolicyUseCase:
    def __init__(
        self,
        policy_repo: PolicyRepositoryPort,
        outbox: PolicyOutboxPort,
    ) -> None:
        self._policy_repo = policy_repo
        self._outbox = outbox

    def execute(self, request: CreatePolicyRequest) -> CreatePolicyResponse:
        policy, event = PolicyFactory.create_policy(
            name=request.name,
            description=request.description,
            priority=request.priority,
            scope=request.scope,
            version=request.version,
        )
        self._policy_repo.save(policy)
        self._outbox.append(event)

        return CreatePolicyResponse(
            policy_id=str(policy.policy_id),
            name=str(policy.name) if policy.name else None,
            description=str(policy.description) if policy.description else None,
            status=policy.status.value,
            priority=policy.priority.value,
            scope=policy.scope.value,
            version=str(policy.version) if policy.version else None,
            created_at=policy.created_at,
        )
