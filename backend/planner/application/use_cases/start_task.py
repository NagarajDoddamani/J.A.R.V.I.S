from __future__ import annotations

from uuid import UUID

from backend.planner.application.ports.repository import TaskRepositoryPort
from backend.planner.application.use_cases.dto import (
    TaskLifecycleRequest,
    TaskLifecycleResponse,
)
from backend.planner.application.use_cases.exceptions import TaskNotFoundError
from backend.planner.domain.factory import PlannerFactory
from backend.planner.domain.model import TaskId


class StartTaskUseCase:
    def __init__(
        self,
        task_repo: TaskRepositoryPort,
    ) -> None:
        self._task_repo = task_repo

    def execute(self, request: TaskLifecycleRequest) -> TaskLifecycleResponse:
        task_id = TaskId(value=UUID(request.task_id))
        task = self._task_repo.find_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(request.task_id)

        PlannerFactory.start_task(task=task)
        self._task_repo.save(task)

        return TaskLifecycleResponse(
            task_id=str(task.task_id),
            status=task.status.value,
        )
