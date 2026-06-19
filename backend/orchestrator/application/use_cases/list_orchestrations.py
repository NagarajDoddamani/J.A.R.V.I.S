from __future__ import annotations

from backend.orchestrator.application.ports.repository import (
    OrchestrationRepositoryPort,
)
from backend.orchestrator.application.use_cases.dto import (
    ListOrchestrationsRequest,
    ListOrchestrationsResponse,
    OrchestrationResponse,
)
from backend.orchestrator.domain.model import OrchestrationStatus


class ListOrchestrationsUseCase:
    def __init__(
        self,
        orchestration_repo: OrchestrationRepositoryPort,
    ) -> None:
        self._orchestration_repo = orchestration_repo

    def execute(
        self, request: ListOrchestrationsRequest
    ) -> ListOrchestrationsResponse:
        if request.status is not None:
            status = OrchestrationStatus(request.status)
            orchestrations = self._orchestration_repo.find_by_status(status)
        else:
            orchestrations = self._orchestration_repo.find_all()

        items = [
            OrchestrationResponse(
                orchestration_id=str(o.orchestration_id),
                intent=str(o.intent) if o.intent else None,
                goal=str(o.goal) if o.goal else None,
                status=o.status.value,
                created_at=o.created_at,
                updated_at=o.updated_at,
                workflow_count=len(o.workflows),
            )
            for o in orchestrations
        ]

        return ListOrchestrationsResponse(
            orchestrations=items, total=len(items)
        )
