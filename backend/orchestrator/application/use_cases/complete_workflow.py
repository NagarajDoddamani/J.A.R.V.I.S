from __future__ import annotations

from uuid import UUID

from backend.orchestrator.application.ports.outbox import OrchestratorOutboxPort
from backend.orchestrator.application.ports.repository import (
    OrchestratorWorkflowRepositoryPort,
)
from backend.orchestrator.application.use_cases.dto import (
    WorkflowLifecycleRequest,
    WorkflowLifecycleResponse,
)
from backend.orchestrator.application.use_cases.exceptions import (
    WorkflowNotFoundError,
)
from backend.orchestrator.domain.model import WorkflowId


class CompleteWorkflowUseCase:
    def __init__(
        self,
        workflow_repo: OrchestratorWorkflowRepositoryPort,
        outbox: OrchestratorOutboxPort,
    ) -> None:
        self._workflow_repo = workflow_repo
        self._outbox = outbox

    def execute(
        self, request: WorkflowLifecycleRequest
    ) -> WorkflowLifecycleResponse:
        wid = WorkflowId(value=UUID(request.workflow_id))
        wf = self._workflow_repo.find_by_id(wid)
        if wf is None:
            raise WorkflowNotFoundError(request.workflow_id)

        wf.complete()
        event = wf.events[-1]
        self._workflow_repo.save(wf)
        self._outbox.append(event)

        return WorkflowLifecycleResponse(
            workflow_id=str(wf.workflow_id),
            status=wf.status.value,
        )
