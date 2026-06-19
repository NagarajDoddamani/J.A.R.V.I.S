from __future__ import annotations

from uuid import UUID

from backend.agent.application.ports.outbox import AgentOutboxPort
from backend.agent.application.ports.repository import (
    AgentRepositoryPort,
)
from backend.agent.application.use_cases.dto import (
    FailExecutionRequest,
    ExecutionLifecycleResponse,
)
from backend.agent.application.use_cases.exceptions import (
    AgentNotFoundError,
)
from backend.agent.domain.factory import AgentFactory
from backend.agent.domain.model import AgentExecutionId, AgentId


class FailExecutionUseCase:
    def __init__(
        self,
        agent_repo: AgentRepositoryPort,
        outbox: AgentOutboxPort,
    ) -> None:
        self._agent_repo = agent_repo
        self._outbox = outbox

    def execute(
        self, request: FailExecutionRequest
    ) -> ExecutionLifecycleResponse:
        agent_id = AgentId(value=UUID(request.agent_id))
        agent = self._agent_repo.find_by_id(agent_id)
        if agent is None:
            raise AgentNotFoundError(request.agent_id)

        execution_id = AgentExecutionId(value=UUID(request.execution_id))
        event = AgentFactory.fail_execution(
            agent=agent,
            execution_id=execution_id,
            reason=request.failure_reason,
        )
        self._agent_repo.save(agent)
        self._outbox.append(event)

        execution = agent._find_execution(execution_id)
        return ExecutionLifecycleResponse(
            execution_id=str(execution.execution_id),
            agent_id=str(agent.agent_id),
            task_id=str(execution.task_id),
            status=execution.status.value,
            failure_reason=execution.failure_reason.value
            if execution.failure_reason
            else None,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
        )
