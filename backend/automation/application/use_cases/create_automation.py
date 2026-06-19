from __future__ import annotations

from backend.automation.application.ports.outbox import AutomationOutboxPort
from backend.automation.application.ports.repository import (
    AutomationRepositoryPort,
)
from backend.automation.application.use_cases.dto import (
    CreateAutomationRequest,
    CreateAutomationResponse,
)
from backend.automation.domain.factory import AutomationFactory


class CreateAutomationUseCase:
    def __init__(
        self,
        automation_repo: AutomationRepositoryPort,
        outbox: AutomationOutboxPort,
    ) -> None:
        self._automation_repo = automation_repo
        self._outbox = outbox

    def execute(self, request: CreateAutomationRequest) -> CreateAutomationResponse:
        automation, event = AutomationFactory.create_automation(
            name=request.name,
            description=request.description,
            execution_mode=request.execution_mode,
        )
        self._automation_repo.save(automation)
        self._outbox.append(event)

        return CreateAutomationResponse(
            automation_id=str(automation.automation_id),
            name=str(automation.name) if automation.name else None,
            description=str(automation.description) if automation.description else None,
            execution_mode=automation.execution_mode.value,
            status=automation.status.value,
            created_at=automation.created_at,
        )
