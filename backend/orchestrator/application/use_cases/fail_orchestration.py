from __future__ import annotations

from uuid import UUID

from backend.orchestrator.application.ports.outbox import OrchestratorOutboxPort
from backend.orchestrator.application.ports.repository import (
    OrchestrationRepositoryPort,
)
from backend.orchestrator.application.use_cases.dto import (
    FailOrchestrationRequest,
    FailOrchestrationResponse,
)
from backend.orchestrator.application.use_cases.exceptions import (
    OrchestrationNotFoundError,
)
from backend.orchestrator.domain.model import (
    FailureReason,
    OrchestrationId,
)


class FailOrchestrationUseCase:
    def __init__(
        self,
        orchestration_repo: OrchestrationRepositoryPort,
        outbox: OrchestratorOutboxPort,
    ) -> None:
        self._orchestration_repo = orchestration_repo
        self._outbox = outbox

    def execute(
        self, request: FailOrchestrationRequest
    ) -> FailOrchestrationResponse:
        oid = OrchestrationId(value=UUID(request.orchestration_id))
        orch = self._orchestration_repo.find_by_id(oid)
        if orch is None:
            raise OrchestrationNotFoundError(request.orchestration_id)

        reason = FailureReason(value=request.failure_reason)
        orch.fail(reason)
        event = orch.events[-1]
        self._orchestration_repo.save(orch)
        self._outbox.append(event)

        return FailOrchestrationResponse(
            orchestration_id=str(orch.orchestration_id),
            status=orch.status.value,
            failure_reason=request.failure_reason,
            updated_at=orch.updated_at,
        )
