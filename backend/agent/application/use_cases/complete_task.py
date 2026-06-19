from __future__ import annotations

from uuid import UUID

from backend.agent.application.ports.outbox import AgentOutboxPort
from backend.agent.application.ports.repository import (
    AgentRepositoryPort,
)
from backend.agent.application.use_cases.dto import (
    CompleteTaskRequest,
    TaskLifecycleResponse,
)
from backend.agent.application.use_cases.exceptions import (
    AgentNotFoundError,
)
from backend.agent.domain.factory import AgentFactory
from backend.agent.domain.model import AgentId, AgentTaskId


class CompleteTaskUseCase:
    def __init__(
        self,
        agent_repo: AgentRepositoryPort,
        outbox: AgentOutboxPort,
    ) -> None:
        self._agent_repo = agent_repo
        self._outbox = outbox

    def execute(
        self, request: CompleteTaskRequest
    ) -> TaskLifecycleResponse:
        agent_id = AgentId(value=UUID(request.agent_id))
        agent = self._agent_repo.find_by_id(agent_id)
        if agent is None:
            raise AgentNotFoundError(request.agent_id)

        task_id = AgentTaskId(value=UUID(request.task_id))
        event = AgentFactory.complete_task(
            agent=agent, task_id=task_id, result=request.result,
        )
        self._agent_repo.save(agent)
        self._outbox.append(event)

        task = agent._find_task(task_id)
        return TaskLifecycleResponse(
            task_id=str(task.task_id),
            agent_id=str(agent.agent_id),
            status=task.status.value,
            result=task.result.value if task.result else None,
        )
