from __future__ import annotations

from uuid import UUID

from backend.automation.application.ports.outbox import AutomationOutboxPort
from backend.automation.application.ports.repository import (
    AutomationExecutionRepositoryPort,
    AutomationRepositoryPort,
)
from backend.automation.application.use_cases.dto import (
    FailExecutionRequest,
    FailExecutionResponse,
)
from backend.automation.application.use_cases.exceptions import (
    AutomationNotFoundError,
)
from backend.automation.domain.factory import AutomationFactory
from backend.automation.domain.model import AutomationId, WorkflowExecutionId


class FailExecutionUseCase:
    def __init__(
        self,
        automation_repo: AutomationRepositoryPort,
        execution_repo: AutomationExecutionRepositoryPort,
        outbox: AutomationOutboxPort,
    ) -> None:
        self._automation_repo = automation_repo
        self._execution_repo = execution_repo
        self._outbox = outbox

    def execute(self, request: FailExecutionRequest) -> FailExecutionResponse:
        automation_id = AutomationId(value=UUID(request.automation_id))
        automation = self._automation_repo.find_by_id(automation_id)
        if automation is None:
            raise AutomationNotFoundError(request.automation_id)

        execution_id = WorkflowExecutionId(value=UUID(request.execution_id))
        event = AutomationFactory.fail_execution(
            automation=automation,
            execution_id=execution_id,
            reason=request.failure_reason,
        )
        execution = next(
            (e for e in automation.executions if e.execution_id == execution_id),
            None,
        )
        self._automation_repo.save(automation)
        if execution is not None:
            self._execution_repo.save(execution)
        self._outbox.append(event)

        return FailExecutionResponse(
            execution_id=request.execution_id,
            automation_id=str(automation.automation_id),
            status=execution.status.value if execution else "failed",
            completed_at=execution.completed_at if execution else None,
            failure_reason=request.failure_reason,
        )
