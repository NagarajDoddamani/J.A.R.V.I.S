from __future__ import annotations

from uuid import UUID

from backend.orchestrator.application.ports.repository import (
    OrchestratorWorkflowRepositoryPort,
)
from backend.orchestrator.application.use_cases.dto import (
    GetWorkflowRequest,
    WorkflowResponse,
)
from backend.orchestrator.application.use_cases.exceptions import (
    WorkflowNotFoundError,
)
from backend.orchestrator.domain.model import WorkflowId


class GetWorkflowUseCase:
    def __init__(
        self,
        workflow_repo: OrchestratorWorkflowRepositoryPort,
    ) -> None:
        self._workflow_repo = workflow_repo

    def execute(
        self, request: GetWorkflowRequest
    ) -> WorkflowResponse:
        wid = WorkflowId(value=UUID(request.workflow_id))
        wf = self._workflow_repo.find_by_id(wid)
        if wf is None:
            raise WorkflowNotFoundError(request.workflow_id)

        return WorkflowResponse(
            workflow_id=str(wf.workflow_id),
            goal=str(wf.goal) if wf.goal else None,
            mode=wf.mode.value,
            status=wf.status.value,
            step_count=len(wf.steps),
        )
