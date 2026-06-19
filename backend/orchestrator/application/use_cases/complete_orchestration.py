from __future__ import annotations

from uuid import UUID

from backend.orchestrator.application.ports.outbox import OrchestratorOutboxPort
from backend.orchestrator.application.ports.repository import (
    OrchestrationRepositoryPort,
)
from backend.orchestrator.application.use_cases.dto import (
    OrchestrationLifecycleRequest,
    OrchestrationLifecycleResponse,
)
from backend.orchestrator.application.use_cases.exceptions import (
    OrchestrationNotFoundError,
)
from backend.orchestrator.domain.model import OrchestrationId


class CompleteOrchestrationUseCase:
    def __init__(
        self,
        orchestration_repo: OrchestrationRepositoryPort,
        outbox: OrchestratorOutboxPort,
    ) -> None:
        self._orchestration_repo = orchestration_repo
        self._outbox = outbox

    def execute(
        self, request: OrchestrationLifecycleRequest
    ) -> OrchestrationLifecycleResponse:
        oid = OrchestrationId(value=UUID(request.orchestration_id))
        orch = self._orchestration_repo.find_by_id(oid)
        if orch is None:
            raise OrchestrationNotFoundError(request.orchestration_id)

        orch.complete()
        event = orch.events[-1]
        self._orchestration_repo.save(orch)
        self._outbox.append(event)

        return OrchestrationLifecycleResponse(
            orchestration_id=str(orch.orchestration_id),
            status=orch.status.value,
            updated_at=orch.updated_at,
        )
