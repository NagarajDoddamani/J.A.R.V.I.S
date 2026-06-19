from __future__ import annotations

from uuid import UUID

from backend.policy.application.ports.outbox import PolicyOutboxPort
from backend.policy.application.ports.repository import (
    PolicyRepositoryPort,
)
from backend.policy.application.use_cases.dto import (
    PolicyLifecycleRequest,
    PolicyLifecycleResponse,
)
from backend.policy.application.use_cases.exceptions import (
    PolicyNotFoundError,
)
from backend.policy.domain.factory import PolicyFactory
from backend.policy.domain.model import PolicyId


class DisablePolicyUseCase:
    def __init__(
        self,
        policy_repo: PolicyRepositoryPort,
        outbox: PolicyOutboxPort,
    ) -> None:
        self._policy_repo = policy_repo
        self._outbox = outbox

    def execute(
        self, request: PolicyLifecycleRequest
    ) -> PolicyLifecycleResponse:
        policy_id = PolicyId(value=UUID(request.policy_id))
        policy = self._policy_repo.find_by_id(policy_id)
        if policy is None:
            raise PolicyNotFoundError(request.policy_id)

        PolicyFactory.disable(policy)
        self._policy_repo.save(policy)
        self._outbox.append(policy.events[-1])

        return PolicyLifecycleResponse(
            policy_id=str(policy.policy_id),
            status=policy.status.value,
            updated_at=policy.updated_at,
        )
