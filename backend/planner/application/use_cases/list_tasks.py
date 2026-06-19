from __future__ import annotations

from uuid import UUID

from backend.planner.application.ports.repository import TaskRepositoryPort
from backend.planner.application.use_cases.dto import (
    ListTasksRequest,
    ListTasksResponse,
    TaskResponse,
)
from backend.planner.domain.model import AgentType, PlanId, TaskStatus


class ListTasksUseCase:
    def __init__(
        self,
        task_repo: TaskRepositoryPort,
    ) -> None:
        self._task_repo = task_repo

    def execute(self, request: ListTasksRequest) -> ListTasksResponse:
        results: list | None = None

        if request.status is not None:
            results = self._task_repo.find_by_status(
                TaskStatus(request.status)
            )

        if request.assigned_agent is not None:
            agent_results = self._task_repo.find_by_agent(
                AgentType(request.assigned_agent)
            )
            if results is not None:
                result_ids = {t.task_id.value for t in results}
                results = [
                    t for t in agent_results
                    if t.task_id.value in result_ids
                ]
            else:
                results = agent_results

        if request.plan_id is not None:
            plan_id = PlanId(value=UUID(request.plan_id))
            plan_results = self._task_repo.find_by_plan_id(plan_id)
            if results is not None:
                result_ids = {t.task_id.value for t in results}
                results = [
                    t for t in plan_results
                    if t.task_id.value in result_ids
                ]
            else:
                results = plan_results

        if results is None:
            total = self._task_repo.count()
            if total == 0:
                return ListTasksResponse(tasks=[], total=0)
            results = []
            for status in TaskStatus:
                results.extend(self._task_repo.find_by_status(status))

        tasks = [
            TaskResponse(
                task_id=str(t.task_id),
                description=str(t.description) if t.description else None,
                assigned_agent=t.assigned_agent.value if t.assigned_agent else None,
                status=t.status.value,
                failure_reason=str(t.failure_reason) if t.failure_reason else None,
                estimated_duration=float(t.estimated_duration) if t.estimated_duration else None,
            )
            for t in results
        ]

        return ListTasksResponse(
            tasks=tasks,
            total=len(tasks),
        )
