from __future__ import annotations

from uuid import UUID

from backend.planner.application.ports.outbox import PlannerOutboxPort
from backend.planner.application.ports.repository import TaskRepositoryPort
from backend.planner.application.use_cases.dto import (
    AssignTaskRequest,
    AssignTaskResponse,
)
from backend.planner.application.use_cases.exceptions import TaskNotFoundError
from backend.planner.domain.factory import PlannerFactory
from backend.planner.domain.model import TaskId


class AssignTaskUseCase:
    def __init__(
        self,
        task_repo: TaskRepositoryPort,
        outbox: PlannerOutboxPort,
    ) -> None:
        self._task_repo = task_repo
        self._outbox = outbox

    def execute(self, request: AssignTaskRequest) -> AssignTaskResponse:
        task_id = TaskId(value=UUID(request.task_id))
        task = self._task_repo.find_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(request.task_id)

        event = PlannerFactory.assign_task(
            task=task,
            agent=request.agent,
        )
        self._task_repo.save(task)
        self._outbox.append(event)

        return AssignTaskResponse(
            task_id=str(task.task_id),
            assigned_agent=task.assigned_agent.value if task.assigned_agent else None,
            status=task.status.value,
        )
