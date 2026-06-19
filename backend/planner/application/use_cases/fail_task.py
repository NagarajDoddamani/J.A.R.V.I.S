from __future__ import annotations

from uuid import UUID

from backend.planner.application.ports.outbox import PlannerOutboxPort
from backend.planner.application.ports.repository import TaskRepositoryPort
from backend.planner.application.use_cases.dto import (
    FailTaskRequest,
    FailTaskResponse,
)
from backend.planner.application.use_cases.exceptions import TaskNotFoundError
from backend.planner.domain.factory import PlannerFactory
from backend.planner.domain.model import TaskId


class FailTaskUseCase:
    def __init__(
        self,
        task_repo: TaskRepositoryPort,
        outbox: PlannerOutboxPort,
    ) -> None:
        self._task_repo = task_repo
        self._outbox = outbox

    def execute(self, request: FailTaskRequest) -> FailTaskResponse:
        task_id = TaskId(value=UUID(request.task_id))
        task = self._task_repo.find_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(request.task_id)

        event = PlannerFactory.fail_task(
            task=task,
            reason=request.failure_reason,
        )
        self._task_repo.save(task)
        self._outbox.append(event)

        return FailTaskResponse(
            task_id=str(task.task_id),
            status=task.status.value,
            failure_reason=request.failure_reason,
        )
