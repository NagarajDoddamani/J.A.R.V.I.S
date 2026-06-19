from __future__ import annotations

from uuid import UUID

from backend.orchestrator.application.ports.repository import (
    OrchestratorWorkflowRepositoryPort,
)
from backend.orchestrator.application.use_cases.dto import (
    ListWorkflowsRequest,
    ListWorkflowsResponse,
    WorkflowResponse,
)
from backend.orchestrator.domain.model import (
    OrchestrationId,
    WorkflowStatus,
)


class ListWorkflowsUseCase:
    def __init__(
        self,
        workflow_repo: OrchestratorWorkflowRepositoryPort,
    ) -> None:
        self._workflow_repo = workflow_repo

    def execute(
        self, request: ListWorkflowsRequest
    ) -> ListWorkflowsResponse:
        if request.status is not None:
            status = WorkflowStatus(request.status)
            workflows = self._workflow_repo.find_by_status(status)
        elif request.orchestration_id is not None:
            oid = OrchestrationId(value=UUID(request.orchestration_id))
            workflows = self._workflow_repo.find_by_orchestration_id(oid)
        else:
            workflows = self._workflow_repo.find_all()

        items = [
            WorkflowResponse(
                workflow_id=str(w.workflow_id),
                goal=str(w.goal) if w.goal else None,
                mode=w.mode.value,
                status=w.status.value,
                step_count=len(w.steps),
            )
            for w in workflows
        ]

        return ListWorkflowsResponse(
            workflows=items, total=len(items)
        )
