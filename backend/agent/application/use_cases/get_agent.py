from __future__ import annotations

from uuid import UUID

from backend.agent.application.ports.repository import (
    AgentRepositoryPort,
)
from backend.agent.application.use_cases.dto import (
    AgentResponse,
    GetAgentRequest,
)
from backend.agent.application.use_cases.exceptions import (
    AgentNotFoundError,
)
from backend.agent.domain.model import AgentId


class GetAgentUseCase:
    def __init__(
        self,
        agent_repo: AgentRepositoryPort,
    ) -> None:
        self._agent_repo = agent_repo

    def execute(self, request: GetAgentRequest) -> AgentResponse:
        agent_id = AgentId(value=UUID(request.agent_id))
        agent = self._agent_repo.find_by_id(agent_id)
        if agent is None:
            raise AgentNotFoundError(request.agent_id)

        return AgentResponse(
            agent_id=str(agent.agent_id),
            agent_type=agent.agent_type.value,
            name=str(agent.name) if agent.name else None,
            status=agent.status.value,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            task_count=len(agent.tasks),
            execution_count=len(agent.executions),
        )
