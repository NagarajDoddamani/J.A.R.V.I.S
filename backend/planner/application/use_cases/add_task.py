from __future__ import annotations

from uuid import UUID

from backend.planner.application.ports.outbox import PlannerOutboxPort
from backend.planner.application.ports.repository import (
    PlanRepositoryPort,
    TaskRepositoryPort,
)
from backend.planner.application.use_cases.dto import (
    AddTaskRequest,
    AddTaskResponse,
)
from backend.planner.application.use_cases.exceptions import PlanNotFoundError
from backend.planner.domain.factory import PlannerFactory
from backend.planner.domain.model import PlanId


class AddTaskUseCase:
    def __init__(
        self,
        plan_repo: PlanRepositoryPort,
        task_repo: TaskRepositoryPort,
        outbox: PlannerOutboxPort,
    ) -> None:
        self._plan_repo = plan_repo
        self._task_repo = task_repo
        self._outbox = outbox

    def execute(self, request: AddTaskRequest) -> AddTaskResponse:
        plan_id = PlanId(value=UUID(request.plan_id))
        plan = self._plan_repo.find_by_id(plan_id)
        if plan is None:
            raise PlanNotFoundError(request.plan_id)

        task, event = PlannerFactory.add_task(
            plan=plan,
            description=request.description,
        )
        self._plan_repo.save(plan)
        self._task_repo.save(task)
        self._outbox.append(event)

        return AddTaskResponse(
            task_id=str(task.task_id),
            plan_id=request.plan_id,
            description=str(task.description) if task.description else None,
            status=task.status.value,
        )
