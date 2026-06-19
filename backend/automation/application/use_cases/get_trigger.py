from __future__ import annotations

from uuid import UUID

from backend.automation.application.ports.repository import (
    TriggerRepositoryPort,
)
from backend.automation.application.use_cases.dto import (
    GetTriggerRequest,
    TriggerResponse,
)
from backend.automation.application.use_cases.exceptions import (
    TriggerNotFoundError,
)
from backend.automation.domain.model import TriggerId


class GetTriggerUseCase:
    def __init__(
        self,
        trigger_repo: TriggerRepositoryPort,
    ) -> None:
        self._trigger_repo = trigger_repo

    def execute(self, request: GetTriggerRequest) -> TriggerResponse:
        trigger_id = TriggerId(value=UUID(request.trigger_id))
        trigger = self._trigger_repo.find_by_id(trigger_id)
        if trigger is None:
            raise TriggerNotFoundError(request.trigger_id)

        return TriggerResponse(
            trigger_id=str(trigger.trigger_id),
            trigger_type=trigger.trigger_type.value,
            expression=str(trigger.expression) if trigger.expression else None,
            enabled=trigger.enabled,
        )
