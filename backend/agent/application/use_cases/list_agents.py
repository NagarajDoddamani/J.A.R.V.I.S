from __future__ import annotations

from backend.agent.application.ports.repository import (
    AgentRepositoryPort,
)
from backend.agent.application.use_cases.dto import (
    AgentResponse,
    ListAgentsRequest,
    ListAgentsResponse,
)
from backend.agent.domain.model import AgentStatus, AgentType


class ListAgentsUseCase:
    def __init__(
        self,
        agent_repo: AgentRepositoryPort,
    ) -> None:
        self._agent_repo = agent_repo

    def execute(
        self, request: ListAgentsRequest
    ) -> ListAgentsResponse:
        if request.status is not None:
            status = AgentStatus(request.status)
            agents = self._agent_repo.find_by_status(status)
        elif request.agent_type is not None:
            agent_type = AgentType(request.agent_type)
            agents = self._agent_repo.find_by_type(agent_type)
        else:
            agents = self._agent_repo.find_all()

        return ListAgentsResponse(
            agents=[
                AgentResponse(
                    agent_id=str(a.agent_id),
                    agent_type=a.agent_type.value,
                    name=str(a.name) if a.name else None,
                    status=a.status.value,
                    created_at=a.created_at,
                    updated_at=a.updated_at,
                    task_count=len(a.tasks),
                    execution_count=len(a.executions),
                )
                for a in agents
            ],
            total=len(agents),
        )
