from __future__ import annotations

from uuid import UUID

from backend.agent.application.ports.repository import (
    AgentTaskRepositoryPort,
)
from backend.agent.application.use_cases.dto import (
    GetTaskRequest,
    TaskResponse,
)
from backend.agent.application.use_cases.exceptions import (
    AgentTaskNotFoundError,
)
from backend.agent.domain.model import AgentTaskId


class GetTaskUseCase:
    def __init__(
        self,
        task_repo: AgentTaskRepositoryPort,
    ) -> None:
        self._task_repo = task_repo

    def execute(self, request: GetTaskRequest) -> TaskResponse:
        task_id = AgentTaskId(value=UUID(request.task_id))
        task = self._task_repo.find_by_id(task_id)
        if task is None:
            raise AgentTaskNotFoundError(request.task_id)

        return TaskResponse(
            task_id=str(task.task_id),
            agent_id=str(task.agent_id) if task.agent_id else None,
            goal=str(task.goal) if task.goal else None,
            instruction=str(task.instruction) if task.instruction else None,
            status=task.status.value,
            result=task.result.value if task.result else None,
            failure_reason=task.failure_reason.value
            if task.failure_reason
            else None,
        )
