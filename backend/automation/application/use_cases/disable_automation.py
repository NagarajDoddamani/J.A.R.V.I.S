from __future__ import annotations

from uuid import UUID

from backend.automation.application.ports.outbox import AutomationOutboxPort
from backend.automation.application.ports.repository import (
    AutomationRepositoryPort,
)
from backend.automation.application.use_cases.dto import (
    AutomationLifecycleRequest,
    AutomationLifecycleResponse,
)
from backend.automation.application.use_cases.exceptions import (
    AutomationNotFoundError,
)
from backend.automation.domain.factory import AutomationFactory
from backend.automation.domain.model import AutomationId


class DisableAutomationUseCase:
    def __init__(
        self,
        automation_repo: AutomationRepositoryPort,
        outbox: AutomationOutboxPort,
    ) -> None:
        self._automation_repo = automation_repo
        self._outbox = outbox

    def execute(
        self, request: AutomationLifecycleRequest
    ) -> AutomationLifecycleResponse:
        automation_id = AutomationId(value=UUID(request.automation_id))
        automation = self._automation_repo.find_by_id(automation_id)
        if automation is None:
            raise AutomationNotFoundError(request.automation_id)

        AutomationFactory.disable(automation)
        self._automation_repo.save(automation)
        self._outbox.append(automation.events[-1])

        return AutomationLifecycleResponse(
            automation_id=str(automation.automation_id),
            status=automation.status.value,
            updated_at=automation.updated_at,
        )
