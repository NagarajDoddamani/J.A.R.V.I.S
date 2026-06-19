from __future__ import annotations

from backend.planner.application.ports.outbox import PlannerOutboxPort
from backend.planner.application.ports.repository import PlanRepositoryPort
from backend.planner.application.use_cases.dto import (
    CreatePlanRequest,
    CreatePlanResponse,
)
from backend.planner.domain.factory import PlannerFactory


class CreatePlanUseCase:
    def __init__(
        self,
        plan_repo: PlanRepositoryPort,
        outbox: PlannerOutboxPort,
    ) -> None:
        self._plan_repo = plan_repo
        self._outbox = outbox

    def execute(self, request: CreatePlanRequest) -> CreatePlanResponse:
        plan, event = PlannerFactory.create_plan(
            user_request=request.user_request,
            goal=request.goal,
            priority=request.priority,
            strategy=request.strategy,
        )
        self._plan_repo.save(plan)
        self._outbox.append(event)

        return CreatePlanResponse(
            plan_id=str(plan.plan_id),
            user_request=str(plan.user_request) if plan.user_request else None,
            goal=str(plan.goal) if plan.goal else None,
            priority=plan.priority.value,
            strategy=plan.strategy.value,
            status=plan.status.value,
            created_at=plan.created_at,
        )
