from __future__ import annotations

from backend.planner.application.ports.repository import PlanRepositoryPort
from backend.planner.application.use_cases.dto import (
    ListPlansRequest,
    ListPlansResponse,
    PlanResponse,
)
from backend.planner.domain.model import PlanPriority, PlanStatus


class ListPlansUseCase:
    def __init__(
        self,
        plan_repo: PlanRepositoryPort,
    ) -> None:
        self._plan_repo = plan_repo

    def execute(self, request: ListPlansRequest) -> ListPlansResponse:
        results: list | None = None

        if request.status is not None:
            results = self._plan_repo.find_by_status(
                PlanStatus(request.status)
            )

        if request.priority is not None:
            priority_results = self._plan_repo.find_by_priority(
                PlanPriority(request.priority)
            )
            if results is not None:
                result_ids = {p.plan_id.value for p in results}
                results = [
                    p for p in priority_results
                    if p.plan_id.value in result_ids
                ]
            else:
                results = priority_results

        if results is None:
            results = list(self._plan_repo.find_active())
            active_ids = {p.plan_id.value for p in results}
            for status in PlanStatus:
                if status.value in ("completed", "failed", "cancelled"):
                    for p in self._plan_repo.find_by_status(status):
                        if p.plan_id.value not in active_ids:
                            results.append(p)

        plans = [
            PlanResponse(
                plan_id=str(p.plan_id),
                user_request=str(p.user_request) if p.user_request else None,
                goal=str(p.goal) if p.goal else None,
                priority=p.priority.value,
                strategy=p.strategy.value,
                status=p.status.value,
                created_at=p.created_at,
                updated_at=p.updated_at,
                task_count=len(p.tasks),
            )
            for p in results
        ]

        return ListPlansResponse(
            plans=plans,
            total=len(plans),
        )
