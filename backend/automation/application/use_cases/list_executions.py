from __future__ import annotations

from uuid import UUID

from backend.automation.application.ports.repository import (
    AutomationExecutionRepositoryPort,
)
from backend.automation.application.use_cases.dto import (
    ExecutionResponse,
    ListExecutionsRequest,
    ListExecutionsResponse,
)
from backend.automation.domain.model import AutomationId, ExecutionStatus


class ListExecutionsUseCase:
    def __init__(
        self,
        execution_repo: AutomationExecutionRepositoryPort,
    ) -> None:
        self._execution_repo = execution_repo

    def execute(
        self, request: ListExecutionsRequest
    ) -> ListExecutionsResponse:
        if request.status is not None and request.automation_id is not None:
            status = ExecutionStatus(request.status)
            automation_id = AutomationId(value=UUID(request.automation_id))
            all_executions = self._execution_repo.find_all()
            executions = [
                e
                for e in all_executions
                if e.status == status and e.automation_id == automation_id
            ]
        elif request.status is not None:
            status = ExecutionStatus(request.status)
            executions = self._execution_repo.find_by_status(status)
        elif request.automation_id is not None:
            automation_id = AutomationId(value=UUID(request.automation_id))
            executions = self._execution_repo.find_by_automation_id(
                automation_id
            )
        else:
            executions = self._execution_repo.find_all()

        return ListExecutionsResponse(
            executions=[
                ExecutionResponse(
                    execution_id=str(e.execution_id),
                    automation_id=str(e.automation_id),
                    status=e.status.value,
                    result=str(e.result) if e.result else None,
                    failure_reason=str(e.failure_reason)
                    if e.failure_reason
                    else None,
                    started_at=e.started_at,
                    completed_at=e.completed_at,
                )
                for e in executions
            ],
            total=len(executions),
        )
