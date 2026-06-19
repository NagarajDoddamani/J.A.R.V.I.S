from __future__ import annotations

from uuid import UUID

from backend.automation.application.ports.outbox import AutomationOutboxPort
from backend.automation.application.ports.repository import (
    AutomationRepositoryPort,
    TriggerRepositoryPort,
)
from backend.automation.application.use_cases.dto import (
    TriggerLifecycleRequest,
    TriggerLifecycleResponse,
)
from backend.automation.application.use_cases.exceptions import (
    TriggerNotFoundError,
)
from backend.automation.domain.factory import AutomationFactory
from backend.automation.domain.model import TriggerId


class EnableTriggerUseCase:
    def __init__(
        self,
        trigger_repo: TriggerRepositoryPort,
        automation_repo: AutomationRepositoryPort,
        outbox: AutomationOutboxPort,
    ) -> None:
        self._trigger_repo = trigger_repo
        self._automation_repo = automation_repo
        self._outbox = outbox

    def execute(
        self, request: TriggerLifecycleRequest
    ) -> TriggerLifecycleResponse:
        trigger_id = TriggerId(value=UUID(request.trigger_id))
        trigger = self._trigger_repo.find_by_id(trigger_id)
        if trigger is None:
            raise TriggerNotFoundError(request.trigger_id)

        automation_id = trigger.automation_id
        if automation_id is None:
            raise TriggerNotFoundError(request.trigger_id)
        automation = self._automation_repo.find_by_id(automation_id)
        if automation is None:
            raise TriggerNotFoundError(request.trigger_id)

        AutomationFactory.enable_trigger(
            automation=automation,
            trigger_id=trigger_id,
        )

        modified_trigger = next(
            t for t in automation.triggers if t.trigger_id == trigger_id
        )
        self._trigger_repo.save(modified_trigger)
        self._automation_repo.save(automation)
        self._outbox.append(automation.events[-1])

        return TriggerLifecycleResponse(
            trigger_id=str(trigger_id),
            enabled=modified_trigger.enabled,
        )
