from __future__ import annotations

from uuid import UUID

from backend.policy.application.ports.outbox import PolicyOutboxPort
from backend.policy.application.ports.repository import (
    PolicyEvaluationRepositoryPort,
    PolicyRepositoryPort,
)
from backend.policy.application.use_cases.dto import (
    CompleteEvaluationRequest,
    CompleteEvaluationResponse,
)
from backend.policy.application.use_cases.exceptions import (
    PolicyNotFoundError,
)
from backend.policy.domain.factory import PolicyFactory
from backend.policy.domain.model import EvaluationId, PolicyId


class CompleteEvaluationUseCase:
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
        self, request: CompleteEvaluationRequest
    ) -> CompleteEvaluationResponse:
        policy_id = PolicyId(value=UUID(request.policy_id))
        policy = self._policy_repo.find_by_id(policy_id)
        if policy is None:
            raise PolicyNotFoundError(request.policy_id)

        evaluation_id = EvaluationId(value=UUID(request.evaluation_id))
        event = PolicyFactory.complete_evaluation(
            policy=policy,
            evaluation_id=evaluation_id,
            decision=request.decision,
            result=request.result,
        )
        evaluation = policy._find_evaluation(evaluation_id)
        self._policy_repo.save(policy)
        self._evaluation_repo.save(evaluation)
        self._outbox.append(event)

        return CompleteEvaluationResponse(
            evaluation_id=str(evaluation_id),
            policy_id=str(policy.policy_id),
            status=evaluation.status.value,
            decision=evaluation.decision.value if evaluation.decision else None,
            result=str(evaluation.result) if evaluation.result else None,
            completed_at=evaluation.completed_at,
        )
