from __future__ import annotations

from uuid import UUID

from backend.agent.application.ports.repository import (
    AgentExecutionRepositoryPort,
)
from backend.agent.application.use_cases.dto import (
    ExecutionResponse,
    ListExecutionsRequest,
    ListExecutionsResponse,
)
from backend.agent.domain.model import (
    AgentExecutionStatus,
    AgentId,
    AgentTaskId,
)


class ListExecutionsUseCase:
    def __init__(
        self,
        execution_repo: AgentExecutionRepositoryPort,
    ) -> None:
        self._execution_repo = execution_repo

    def execute(
        self, request: ListExecutionsRequest
    ) -> ListExecutionsResponse:
        if request.agent_id is not None:
            agent_id = AgentId(value=UUID(request.agent_id))
            executions = self._execution_repo.find_by_agent_id(agent_id)
        elif request.task_id is not None:
            task_id = AgentTaskId(value=UUID(request.task_id))
            executions = self._execution_repo.find_by_task_id(task_id)
        elif request.status is not None:
            status = AgentExecutionStatus(request.status)
            executions = self._execution_repo.find_by_status(status)
        else:
            executions = self._execution_repo.find_all()

        return ListExecutionsResponse(
            executions=[
                ExecutionResponse(
                    execution_id=str(e.execution_id),
                    agent_id=str(e.agent_id) if e.agent_id else None,
                    task_id=str(e.task_id) if e.task_id else None,
                    status=e.status.value,
                    result=e.result.value if e.result else None,
                    failure_reason=e.failure_reason.value
                    if e.failure_reason
                    else None,
                    started_at=e.started_at,
                    completed_at=e.completed_at,
                )
                for e in executions
            ],
            total=len(executions),
        )
