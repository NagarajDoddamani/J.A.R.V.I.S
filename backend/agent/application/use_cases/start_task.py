from __future__ import annotations

from uuid import UUID

from backend.agent.application.ports.outbox import AgentOutboxPort
from backend.agent.application.ports.repository import (
    AgentRepositoryPort,
)
from backend.agent.application.use_cases.dto import (
    TaskLifecycleRequest,
    TaskLifecycleResponse,
)
from backend.agent.application.use_cases.exceptions import (
    AgentNotFoundError,
)
from backend.agent.domain.factory import AgentFactory
from backend.agent.domain.model import AgentId, AgentTaskId


class StartTaskUseCase:
    def __init__(
        self,
        agent_repo: AgentRepositoryPort,
        outbox: AgentOutboxPort,
    ) -> None:
        self._agent_repo = agent_repo
        self._outbox = outbox

    def execute(
        self, request: TaskLifecycleRequest
    ) -> TaskLifecycleResponse:
        agent_id = AgentId(value=UUID(request.agent_id))
        agent = self._agent_repo.find_by_id(agent_id)
        if agent is None:
            raise AgentNotFoundError(request.agent_id)

        task_id = AgentTaskId(value=UUID(request.task_id))
        event = AgentFactory.start_task(agent=agent, task_id=task_id)
        self._agent_repo.save(agent)
        self._outbox.append(event)

        task = agent._find_task(task_id)
        return TaskLifecycleResponse(
            task_id=str(task.task_id),
            agent_id=str(agent.agent_id),
            status=task.status.value,
        )
