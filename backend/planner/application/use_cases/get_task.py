from __future__ import annotations

from uuid import UUID

from backend.planner.application.ports.repository import TaskRepositoryPort
from backend.planner.application.use_cases.dto import (
    GetTaskRequest,
    TaskResponse,
)
from backend.planner.application.use_cases.exceptions import TaskNotFoundError
from backend.planner.domain.model import TaskId


class GetTaskUseCase:
    def __init__(
        self,
        task_repo: TaskRepositoryPort,
    ) -> None:
        self._task_repo = task_repo

    def execute(self, request: GetTaskRequest) -> TaskResponse:
        task_id = TaskId(value=UUID(request.task_id))
        task = self._task_repo.find_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(request.task_id)

        return TaskResponse(
            task_id=str(task.task_id),
            description=str(task.description) if task.description else None,
            assigned_agent=task.assigned_agent.value if task.assigned_agent else None,
            status=task.status.value,
            failure_reason=str(task.failure_reason) if task.failure_reason else None,
            estimated_duration=float(task.estimated_duration) if task.estimated_duration else None,
        )
