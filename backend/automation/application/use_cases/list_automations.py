from __future__ import annotations

from backend.automation.application.ports.repository import (
    AutomationRepositoryPort,
)
from backend.automation.application.use_cases.dto import (
    AutomationResponse,
    ListAutomationsRequest,
    ListAutomationsResponse,
)
from backend.automation.domain.model import AutomationStatus, ExecutionMode


class ListAutomationsUseCase:
    def __init__(
        self,
        automation_repo: AutomationRepositoryPort,
    ) -> None:
        self._automation_repo = automation_repo

    def execute(
        self, request: ListAutomationsRequest
    ) -> ListAutomationsResponse:
        if request.status is not None:
            status = AutomationStatus(request.status)
            automations = self._automation_repo.find_by_status(status)
        elif request.execution_mode is not None:
            mode = ExecutionMode(request.execution_mode)
            automations = self._automation_repo.find_by_execution_mode(mode)
        else:
            automations = self._automation_repo.find_all()

        return ListAutomationsResponse(
            automations=[
                AutomationResponse(
                    automation_id=str(a.automation_id),
                    name=str(a.name) if a.name else None,
                    description=str(a.description) if a.description else None,
                    status=a.status.value,
                    execution_mode=a.execution_mode.value,
                    created_at=a.created_at,
                    updated_at=a.updated_at,
                    trigger_count=len(a.triggers),
                    action_count=len(a.actions),
                    execution_count=len(a.executions),
                )
                for a in automations
            ],
            total=len(automations),
        )
