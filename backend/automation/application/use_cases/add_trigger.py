from __future__ import annotations

from uuid import UUID

from backend.automation.application.ports.outbox import AutomationOutboxPort
from backend.automation.application.ports.repository import (
    AutomationRepositoryPort,
    TriggerRepositoryPort,
)
from backend.automation.application.use_cases.dto import (
    AddTriggerRequest,
    AddTriggerResponse,
)
from backend.automation.application.use_cases.exceptions import (
    AutomationNotFoundError,
)
from backend.automation.domain.factory import AutomationFactory
from backend.automation.domain.model import AutomationId


class AddTriggerUseCase:
    def __init__(
        self,
        automation_repo: AutomationRepositoryPort,
        trigger_repo: TriggerRepositoryPort,
        outbox: AutomationOutboxPort,
    ) -> None:
        self._automation_repo = automation_repo
        self._trigger_repo = trigger_repo
        self._outbox = outbox

    def execute(self, request: AddTriggerRequest) -> AddTriggerResponse:
        automation_id = AutomationId(value=UUID(request.automation_id))
        automation = self._automation_repo.find_by_id(automation_id)
        if automation is None:
            raise AutomationNotFoundError(request.automation_id)

        trigger, event = AutomationFactory.add_trigger(
            automation=automation,
            trigger_type=request.trigger_type,
            expression=request.expression,
        )
        self._automation_repo.save(automation)
        self._trigger_repo.save(trigger, automation_id=str(automation.automation_id))
        self._outbox.append(event)

        return AddTriggerResponse(
            trigger_id=str(trigger.trigger_id),
            automation_id=str(automation.automation_id),
            trigger_type=trigger.trigger_type.value,
            expression=str(trigger.expression) if trigger.expression else None,
            enabled=trigger.enabled,
        )
