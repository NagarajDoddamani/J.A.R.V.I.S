from __future__ import annotations

from uuid import UUID

from backend.planner.application.ports.repository import PlanRepositoryPort
from backend.planner.application.use_cases.dto import (
    PlanLifecycleRequest,
    PlanLifecycleResponse,
)
from backend.planner.application.use_cases.exceptions import PlanNotFoundError
from backend.planner.domain.model import PlanId


class StartPlanningUseCase:
    def __init__(
        self,
        plan_repo: PlanRepositoryPort,
    ) -> None:
        self._plan_repo = plan_repo

    def execute(self, request: PlanLifecycleRequest) -> PlanLifecycleResponse:
        plan_id = PlanId(value=UUID(request.plan_id))
        plan = self._plan_repo.find_by_id(plan_id)
        if plan is None:
            raise PlanNotFoundError(request.plan_id)

        plan.start_planning()
        self._plan_repo.save(plan)

        return PlanLifecycleResponse(
            plan_id=str(plan.plan_id),
            status=plan.status.value,
            updated_at=plan.updated_at,
        )
