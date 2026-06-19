from __future__ import annotations

from uuid import UUID

from backend.orchestrator.application.ports.repository import (
    OrchestrationRepositoryPort,
)
from backend.orchestrator.application.use_cases.dto import (
    GetOrchestrationRequest,
    OrchestrationResponse,
)
from backend.orchestrator.application.use_cases.exceptions import (
    OrchestrationNotFoundError,
)
from backend.orchestrator.domain.model import OrchestrationId


class GetOrchestrationUseCase:
    def __init__(
        self,
        orchestration_repo: OrchestrationRepositoryPort,
    ) -> None:
        self._orchestration_repo = orchestration_repo

    def execute(
        self, request: GetOrchestrationRequest
    ) -> OrchestrationResponse:
        oid = OrchestrationId(value=UUID(request.orchestration_id))
        orch = self._orchestration_repo.find_by_id(oid)
        if orch is None:
            raise OrchestrationNotFoundError(request.orchestration_id)

        return OrchestrationResponse(
            orchestration_id=str(orch.orchestration_id),
            intent=str(orch.intent) if orch.intent else None,
            goal=str(orch.goal) if orch.goal else None,
            status=orch.status.value,
            created_at=orch.created_at,
            updated_at=orch.updated_at,
            workflow_count=len(orch.workflows),
        )
