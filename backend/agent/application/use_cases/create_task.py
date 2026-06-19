from __future__ import annotations

from uuid import UUID

from backend.agent.application.ports.outbox import AgentOutboxPort
from backend.agent.application.ports.repository import (
    AgentRepositoryPort,
)
from backend.agent.application.use_cases.dto import (
    CreateTaskRequest,
    CreateTaskResponse,
)
from backend.agent.application.use_cases.exceptions import (
    AgentNotFoundError,
)
from backend.agent.domain.factory import AgentFactory
from backend.agent.domain.model import AgentId


class CreateTaskUseCase:
    def __init__(
        self,
        agent_repo: AgentRepositoryPort,
        outbox: AgentOutboxPort,
    ) -> None:
        self._agent_repo = agent_repo
        self._outbox = outbox

    def execute(self, request: CreateTaskRequest) -> CreateTaskResponse:
        agent_id = AgentId(value=UUID(request.agent_id))
        agent = self._agent_repo.find_by_id(agent_id)
        if agent is None:
            raise AgentNotFoundError(request.agent_id)

        task, event = AgentFactory.create_task(
            agent=agent,
            goal=request.goal,
            instruction=request.instruction,
        )
        self._agent_repo.save(agent)
        self._outbox.append(event)

        return CreateTaskResponse(
            task_id=str(task.task_id),
            agent_id=str(agent.agent_id),
            goal=str(task.goal) if task.goal else None,
            instruction=str(task.instruction) if task.instruction else None,
            status=task.status.value,
        )
