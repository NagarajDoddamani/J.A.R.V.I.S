from __future__ import annotations

from uuid import UUID

from backend.automation.application.ports.outbox import AutomationOutboxPort
from backend.automation.application.ports.repository import (
    AutomationExecutionRepositoryPort,
    AutomationRepositoryPort,
)
from backend.automation.application.use_cases.dto import (
    StartExecutionRequest,
    StartExecutionResponse,
)
from backend.automation.application.use_cases.exceptions import (
    AutomationNotFoundError,
)
from backend.automation.domain.factory import AutomationFactory
from backend.automation.domain.model import AutomationId


class StartExecutionUseCase:
    def __init__(
        self,
        automation_repo: AutomationRepositoryPort,
        execution_repo: AutomationExecutionRepositoryPort,
        outbox: AutomationOutboxPort,
    ) -> None:
        self._automation_repo = automation_repo
        self._execution_repo = execution_repo
        self._outbox = outbox

    def execute(self, request: StartExecutionRequest) -> StartExecutionResponse:
        automation_id = AutomationId(value=UUID(request.automation_id))
        automation = self._automation_repo.find_by_id(automation_id)
        if automation is None:
            raise AutomationNotFoundError(request.automation_id)

        execution, event = AutomationFactory.start_execution(
            automation=automation,
        )
        self._automation_repo.save(automation)
        self._execution_repo.save(execution)
        self._outbox.append(event)

        return StartExecutionResponse(
            automation_id=str(automation.automation_id),
            execution_id=str(execution.execution_id),
            status=execution.status.value,
            started_at=execution.started_at,
        )
