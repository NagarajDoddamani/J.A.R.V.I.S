from __future__ import annotations

from uuid import UUID

from backend.policy.application.ports.repository import (
    PolicyEvaluationRepositoryPort,
)
from backend.policy.application.use_cases.dto import (
    EvaluationResponse,
    GetEvaluationRequest,
)
from backend.policy.application.use_cases.exceptions import (
    PolicyEvaluationNotFoundError,
)
from backend.policy.domain.model import EvaluationId


class GetEvaluationUseCase:
    def __init__(
        self,
        evaluation_repo: PolicyEvaluationRepositoryPort,
    ) -> None:
        self._evaluation_repo = evaluation_repo

    def execute(self, request: GetEvaluationRequest) -> EvaluationResponse:
        evaluation_id = EvaluationId(value=UUID(request.evaluation_id))
        evaluation = self._evaluation_repo.find_by_id(evaluation_id)
        if evaluation is None:
            raise PolicyEvaluationNotFoundError(request.evaluation_id)

        return EvaluationResponse(
            evaluation_id=str(evaluation.evaluation_id),
            policy_id=str(evaluation.policy_id),
            status=evaluation.status.value,
            decision=evaluation.decision.value if evaluation.decision else None,
            result=str(evaluation.result) if evaluation.result else None,
            failure_reason=str(evaluation.failure_reason) if evaluation.failure_reason else None,
            started_at=evaluation.started_at,
            completed_at=evaluation.completed_at,
        )
