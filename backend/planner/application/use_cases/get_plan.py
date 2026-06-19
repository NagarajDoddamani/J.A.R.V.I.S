from __future__ import annotations

from uuid import UUID

from backend.planner.application.ports.repository import PlanRepositoryPort
from backend.planner.application.use_cases.dto import (
    GetPlanRequest,
    PlanResponse,
)
from backend.planner.application.use_cases.exceptions import PlanNotFoundError
from backend.planner.domain.model import PlanId


class GetPlanUseCase:
    def __init__(
        self,
        plan_repo: PlanRepositoryPort,
    ) -> None:
        self._plan_repo = plan_repo

    def execute(self, request: GetPlanRequest) -> PlanResponse:
        plan_id = PlanId(value=UUID(request.plan_id))
        plan = self._plan_repo.find_by_id(plan_id)
        if plan is None:
            raise PlanNotFoundError(request.plan_id)

        return PlanResponse(
            plan_id=str(plan.plan_id),
            user_request=str(plan.user_request) if plan.user_request else None,
            goal=str(plan.goal) if plan.goal else None,
            priority=plan.priority.value,
            strategy=plan.strategy.value,
            status=plan.status.value,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            task_count=len(plan.tasks),
        )
