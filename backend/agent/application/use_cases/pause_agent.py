from __future__ import annotations

from uuid import UUID

from backend.agent.application.ports.outbox import AgentOutboxPort
from backend.agent.application.ports.repository import (
    AgentRepositoryPort,
)
from backend.agent.application.use_cases.dto import (
    AgentLifecycleRequest,
    AgentLifecycleResponse,
)
from backend.agent.application.use_cases.exceptions import (
    AgentNotFoundError,
)
from backend.agent.domain.factory import AgentFactory
from backend.agent.domain.model import AgentId


class PauseAgentUseCase:
    def __init__(
        self,
        agent_repo: AgentRepositoryPort,
        outbox: AgentOutboxPort,
    ) -> None:
        self._agent_repo = agent_repo
        self._outbox = outbox

    def execute(
        self, request: AgentLifecycleRequest
    ) -> AgentLifecycleResponse:
        agent_id = AgentId(value=UUID(request.agent_id))
        agent = self._agent_repo.find_by_id(agent_id)
        if agent is None:
            raise AgentNotFoundError(request.agent_id)

        AgentFactory.pause_agent(agent)
        self._agent_repo.save(agent)
        self._outbox.append(agent.events[-1])

        return AgentLifecycleResponse(
            agent_id=str(agent.agent_id),
            status=agent.status.value,
            updated_at=agent.updated_at,
        )
