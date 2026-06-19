from __future__ import annotations

from uuid import UUID

from backend.orchestrator.application.ports.repository import (
    OrchestratorStepRepositoryPort,
    OrchestratorWorkflowRepositoryPort,
)
from backend.orchestrator.application.use_cases.dto import (
    AddStepRequest,
    AddStepResponse,
)
from backend.orchestrator.application.use_cases.exceptions import (
    WorkflowNotFoundError,
)
from backend.orchestrator.domain.factory import OrchestratorFactory
from backend.orchestrator.domain.model import WorkflowId


class AddStepUseCase:
    def __init__(
        self,
        workflow_repo: OrchestratorWorkflowRepositoryPort,
        step_repo: OrchestratorStepRepositoryPort,
    ) -> None:
        self._workflow_repo = workflow_repo
        self._step_repo = step_repo

    def execute(
        self, request: AddStepRequest
    ) -> AddStepResponse:
        wid = WorkflowId(value=UUID(request.workflow_id))
        wf = self._workflow_repo.find_by_id(wid)
        if wf is None:
            raise WorkflowNotFoundError(request.workflow_id)

        step = OrchestratorFactory.add_step(
            workflow=wf,
            agent_role=request.agent_role,
            execution_order=request.execution_order,
        )
        self._workflow_repo.save(wf)
        self._step_repo.save(step)

        return AddStepResponse(
            step_id=str(step.step_id),
            agent_role=step.agent_role.value,
            execution_order=int(step.execution_order),
            status=step.status.value,
        )
