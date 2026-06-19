from __future__ import annotations

from backend.agent.application.ports.outbox import AgentOutboxPort
from backend.agent.application.ports.repository import (
    AgentRepositoryPort,
)
from backend.agent.application.use_cases.dto import (
    CreateAgentRequest,
    CreateAgentResponse,
)
from backend.agent.domain.factory import AgentFactory


class CreateAgentUseCase:
    def __init__(
        self,
        agent_repo: AgentRepositoryPort,
        outbox: AgentOutboxPort,
    ) -> None:
        self._agent_repo = agent_repo
        self._outbox = outbox

    def execute(self, request: CreateAgentRequest) -> CreateAgentResponse:
        agent, event = AgentFactory.create_agent(
            name=request.name,
            agent_type=request.agent_type,
        )
        self._agent_repo.save(agent)
        self._outbox.append(event)

        return CreateAgentResponse(
            agent_id=str(agent.agent_id),
            agent_type=agent.agent_type.value,
            name=str(agent.name) if agent.name else None,
            status=agent.status.value,
            created_at=agent.created_at,
        )
