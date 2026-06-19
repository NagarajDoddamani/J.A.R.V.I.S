from __future__ import annotations

from uuid import UUID

from backend.automation.application.ports.outbox import AutomationOutboxPort
from backend.automation.application.ports.repository import (
    AutomationRepositoryPort,
)
from backend.automation.application.use_cases.dto import (
    AddActionRequest,
    AddActionResponse,
)
from backend.automation.application.use_cases.exceptions import (
    AutomationNotFoundError,
)
from backend.automation.domain.factory import AutomationFactory
from backend.automation.domain.model import AutomationId


class AddActionUseCase:
    def __init__(
        self,
        automation_repo: AutomationRepositoryPort,
        outbox: AutomationOutboxPort,
    ) -> None:
        self._automation_repo = automation_repo
        self._outbox = outbox

    def execute(self, request: AddActionRequest) -> AddActionResponse:
        automation_id = AutomationId(value=UUID(request.automation_id))
        automation = self._automation_repo.find_by_id(automation_id)
        if automation is None:
            raise AutomationNotFoundError(request.automation_id)

        AutomationFactory.add_action(
            automation=automation,
            action_type=request.action_type,
        )
        self._automation_repo.save(automation)
        self._outbox.append(automation.events[-1])

        return AddActionResponse(
            automation_id=str(automation.automation_id),
            action_type=request.action_type,
        )
