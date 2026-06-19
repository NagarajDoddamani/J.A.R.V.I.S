from __future__ import annotations

from uuid import UUID

from backend.policy.application.ports.outbox import PolicyOutboxPort
from backend.policy.application.ports.repository import (
    PolicyEvaluationRepositoryPort,
    PolicyRepositoryPort,
)
from backend.policy.application.use_cases.dto import (
    StartEvaluationRequest,
    StartEvaluationResponse,
)
from backend.policy.application.use_cases.exceptions import (
    PolicyNotFoundError,
)
from backend.policy.domain.factory import PolicyFactory
from backend.policy.domain.model import PolicyId


class StartEvaluationUseCase:
    def __init__(
        self,
        policy_repo: PolicyRepositoryPort,
        evaluation_repo: PolicyEvaluationRepositoryPort,
        outbox: PolicyOutboxPort,
    ) -> None:
        self._policy_repo = policy_repo
        self._evaluation_repo = evaluation_repo
        self._outbox = outbox

    def execute(
        self, request: StartEvaluationRequest
    ) -> StartEvaluationResponse:
        policy_id = PolicyId(value=UUID(request.policy_id))
        policy = self._policy_repo.find_by_id(policy_id)
        if policy is None:
            raise PolicyNotFoundError(request.policy_id)

        evaluation, event = PolicyFactory.start_evaluation(policy=policy)
        self._policy_repo.save(policy)
        self._evaluation_repo.save(evaluation)
        self._outbox.append(event)

        return StartEvaluationResponse(
            evaluation_id=str(evaluation.evaluation_id),
            policy_id=str(policy.policy_id),
            status=evaluation.status.value,
            started_at=evaluation.started_at,
        )
