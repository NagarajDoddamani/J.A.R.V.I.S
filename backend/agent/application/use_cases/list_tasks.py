from __future__ import annotations

from uuid import UUID

from backend.agent.application.ports.repository import (
    AgentTaskRepositoryPort,
)
from backend.agent.application.use_cases.dto import (
    ListTasksRequest,
    ListTasksResponse,
    TaskResponse,
)
from backend.agent.domain.model import AgentId, AgentTaskStatus


class ListTasksUseCase:
    def __init__(
        self,
        task_repo: AgentTaskRepositoryPort,
    ) -> None:
        self._task_repo = task_repo

    def execute(
        self, request: ListTasksRequest
    ) -> ListTasksResponse:
        if request.agent_id is not None:
            agent_id = AgentId(value=UUID(request.agent_id))
            tasks = self._task_repo.find_by_agent_id(agent_id)
        elif request.status is not None:
            status = AgentTaskStatus(request.status)
            tasks = self._task_repo.find_by_status(status)
        else:
            tasks = self._task_repo.find_all()

        return ListTasksResponse(
            tasks=[
                TaskResponse(
                    task_id=str(t.task_id),
                    agent_id=str(t.agent_id) if t.agent_id else None,
                    goal=str(t.goal) if t.goal else None,
                    instruction=str(t.instruction) if t.instruction else None,
                    status=t.status.value,
                    result=t.result.value if t.result else None,
                    failure_reason=t.failure_reason.value
                    if t.failure_reason
                    else None,
                )
                for t in tasks
            ],
            total=len(tasks),
        )
