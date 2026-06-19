from __future__ import annotations

from backend.automation.application.ports.repository import (
    TriggerRepositoryPort,
)
from backend.automation.application.use_cases.dto import (
    ListTriggersRequest,
    ListTriggersResponse,
    TriggerResponse,
)
from backend.automation.domain.model import TriggerType


class ListTriggersUseCase:
    def __init__(
        self,
        trigger_repo: TriggerRepositoryPort,
    ) -> None:
        self._trigger_repo = trigger_repo

    def execute(self, request: ListTriggersRequest) -> ListTriggersResponse:
        if request.enabled is True and request.trigger_type is not None:
            all_triggers = self._trigger_repo.find_all()
            trigger_type = TriggerType(request.trigger_type)
            triggers = [
                t
                for t in all_triggers
                if t.trigger_type == trigger_type and t.enabled
            ]
        elif request.enabled is True:
            triggers = self._trigger_repo.find_enabled()
        elif request.trigger_type is not None:
            trigger_type = TriggerType(request.trigger_type)
            triggers = self._trigger_repo.find_by_type(trigger_type)
        else:
            triggers = self._trigger_repo.find_all()

        return ListTriggersResponse(
            triggers=[
                TriggerResponse(
                    trigger_id=str(t.trigger_id),
                    trigger_type=t.trigger_type.value,
                    expression=str(t.expression) if t.expression else None,
                    enabled=t.enabled,
                )
                for t in triggers
            ],
            total=len(triggers),
        )
