from __future__ import annotations

from uuid import UUID

from backend.automation.application.ports.repository import (
    AutomationExecutionRepositoryPort,
)
from backend.automation.application.use_cases.dto import (
    ExecutionResponse,
    GetExecutionRequest,
)
from backend.automation.application.use_cases.exceptions import (
    AutomationExecutionNotFoundError,
)
from backend.automation.domain.model import WorkflowExecutionId


class GetExecutionUseCase:
    def __init__(
        self,
        execution_repo: AutomationExecutionRepositoryPort,
    ) -> None:
        self._execution_repo = execution_repo

    def execute(self, request: GetExecutionRequest) -> ExecutionResponse:
        execution_id = WorkflowExecutionId(value=UUID(request.execution_id))
        execution = self._execution_repo.find_by_id(execution_id)
        if execution is None:
            raise AutomationExecutionNotFoundError(request.execution_id)

        return ExecutionResponse(
            execution_id=str(execution.execution_id),
            automation_id=str(execution.automation_id),
            status=execution.status.value,
            result=str(execution.result) if execution.result else None,
            failure_reason=str(execution.failure_reason)
            if execution.failure_reason
            else None,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
        )
