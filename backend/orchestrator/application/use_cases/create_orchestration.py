from __future__ import annotations

from backend.orchestrator.application.ports.outbox import OrchestratorOutboxPort
from backend.orchestrator.application.ports.repository import (
    OrchestrationRepositoryPort,
)
from backend.orchestrator.application.use_cases.dto import (
    CreateOrchestrationRequest,
    CreateOrchestrationResponse,
)
from backend.orchestrator.domain.factory import OrchestratorFactory


class CreateOrchestrationUseCase:
    def __init__(
        self,
        orchestration_repo: OrchestrationRepositoryPort,
        outbox: OrchestratorOutboxPort,
    ) -> None:
        self._orchestration_repo = orchestration_repo
        self._outbox = outbox

    def execute(
        self, request: CreateOrchestrationRequest
    ) -> CreateOrchestrationResponse:
        orch, event = OrchestratorFactory.create_orchestration(
            intent=request.intent,
            goal=request.goal,
        )
        self._orchestration_repo.save(orch)
        self._outbox.append(event)

        return CreateOrchestrationResponse(
            orchestration_id=str(orch.orchestration_id),
            intent=str(orch.intent) if orch.intent else None,
            goal=str(orch.goal) if orch.goal else None,
            status=orch.status.value,
            created_at=orch.created_at,
        )
