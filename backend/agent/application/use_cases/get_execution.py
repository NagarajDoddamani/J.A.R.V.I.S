from __future__ import annotations

from uuid import UUID

from backend.agent.application.ports.repository import (
    AgentExecutionRepositoryPort,
)
from backend.agent.application.use_cases.dto import (
    ExecutionResponse,
    GetExecutionRequest,
)
from backend.agent.application.use_cases.exceptions import (
    AgentExecutionNotFoundError,
)
from backend.agent.domain.model import AgentExecutionId


class GetExecutionUseCase:
    def __init__(
        self,
        execution_repo: AgentExecutionRepositoryPort,
    ) -> None:
        self._execution_repo = execution_repo

    def execute(self, request: GetExecutionRequest) -> ExecutionResponse:
        execution_id = AgentExecutionId(value=UUID(request.execution_id))
        execution = self._execution_repo.find_by_id(execution_id)
        if execution is None:
            raise AgentExecutionNotFoundError(request.execution_id)

        return ExecutionResponse(
            execution_id=str(execution.execution_id),
            agent_id=str(execution.agent_id) if execution.agent_id else None,
            task_id=str(execution.task_id) if execution.task_id else None,
            status=execution.status.value,
            result=execution.result.value if execution.result else None,
            failure_reason=execution.failure_reason.value
            if execution.failure_reason
            else None,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
        )
