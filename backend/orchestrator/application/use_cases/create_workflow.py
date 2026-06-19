from __future__ import annotations

from uuid import UUID

from backend.orchestrator.application.ports.outbox import OrchestratorOutboxPort
from backend.orchestrator.application.ports.repository import (
    OrchestrationRepositoryPort,
    OrchestratorWorkflowRepositoryPort,
)
from backend.orchestrator.application.use_cases.dto import (
    CreateWorkflowRequest,
    CreateWorkflowResponse,
)
from backend.orchestrator.application.use_cases.exceptions import (
    OrchestrationNotFoundError,
)
from backend.orchestrator.domain.factory import OrchestratorFactory
from backend.orchestrator.domain.model import OrchestrationId


class CreateWorkflowUseCase:
    def __init__(
        self,
        orchestration_repo: OrchestrationRepositoryPort,
        workflow_repo: OrchestratorWorkflowRepositoryPort,
        outbox: OrchestratorOutboxPort,
    ) -> None:
        self._orchestration_repo = orchestration_repo
        self._workflow_repo = workflow_repo
        self._outbox = outbox

    def execute(
        self, request: CreateWorkflowRequest
    ) -> CreateWorkflowResponse:
        oid = OrchestrationId(value=UUID(request.orchestration_id))
        orch = self._orchestration_repo.find_by_id(oid)
        if orch is None:
            raise OrchestrationNotFoundError(request.orchestration_id)

        wf, event = OrchestratorFactory.create_workflow(
            orchestration=orch,
            goal=request.goal,
            mode=request.mode,
        )
        self._orchestration_repo.save(orch)
        self._workflow_repo.save(wf)
        self._outbox.append(event)

        return CreateWorkflowResponse(
            workflow_id=str(wf.workflow_id),
            orchestration_id=str(orch.orchestration_id),
            goal=str(wf.goal) if wf.goal else None,
            mode=wf.mode.value,
            status=wf.status.value,
        )
