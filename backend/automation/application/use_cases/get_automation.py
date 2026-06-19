from __future__ import annotations

from uuid import UUID

from backend.automation.application.ports.repository import (
    AutomationRepositoryPort,
)
from backend.automation.application.use_cases.dto import (
    AutomationResponse,
    GetAutomationRequest,
)
from backend.automation.application.use_cases.exceptions import (
    AutomationNotFoundError,
)
from backend.automation.domain.model import AutomationId


class GetAutomationUseCase:
    def __init__(
        self,
        automation_repo: AutomationRepositoryPort,
    ) -> None:
        self._automation_repo = automation_repo

    def execute(self, request: GetAutomationRequest) -> AutomationResponse:
        automation_id = AutomationId(value=UUID(request.automation_id))
        automation = self._automation_repo.find_by_id(automation_id)
        if automation is None:
            raise AutomationNotFoundError(request.automation_id)

        return AutomationResponse(
            automation_id=str(automation.automation_id),
            name=str(automation.name) if automation.name else None,
            description=str(automation.description) if automation.description else None,
            status=automation.status.value,
            execution_mode=automation.execution_mode.value,
            created_at=automation.created_at,
            updated_at=automation.updated_at,
            trigger_count=len(automation.triggers),
            action_count=len(automation.actions),
            execution_count=len(automation.executions),
        )
