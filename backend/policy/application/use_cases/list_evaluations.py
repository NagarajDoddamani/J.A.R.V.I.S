from __future__ import annotations

from uuid import UUID

from backend.policy.application.ports.repository import (
    PolicyEvaluationRepositoryPort,
)
from backend.policy.application.use_cases.dto import (
    EvaluationResponse,
    ListEvaluationsRequest,
    ListEvaluationsResponse,
)
from backend.policy.domain.model import EvaluationId, PolicyEvaluationStatus


class ListEvaluationsUseCase:
    def __init__(
        self,
        evaluation_repo: PolicyEvaluationRepositoryPort,
    ) -> None:
        self._evaluation_repo = evaluation_repo

    def execute(
        self, request: ListEvaluationsRequest
    ) -> ListEvaluationsResponse:
        if request.status is not None:
            status = PolicyEvaluationStatus(request.status)
            evaluations = self._evaluation_repo.find_by_status(status)
        elif request.policy_id is not None:
            from backend.policy.domain.model import PolicyId
            policy_id = PolicyId(value=UUID(request.policy_id))
            evaluations = self._evaluation_repo.find_by_policy_id(policy_id)
        else:
            evaluations = self._evaluation_repo.find_all()

        return ListEvaluationsResponse(
            evaluations=[
                EvaluationResponse(
                    evaluation_id=str(e.evaluation_id),
                    policy_id=str(e.policy_id),
                    status=e.status.value,
                    decision=e.decision.value if e.decision else None,
                    result=str(e.result) if e.result else None,
                    failure_reason=str(e.failure_reason) if e.failure_reason else None,
                    started_at=e.started_at,
                    completed_at=e.completed_at,
                )
                for e in evaluations
            ],
            total=len(evaluations),
        )
