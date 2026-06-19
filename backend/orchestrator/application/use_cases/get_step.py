from __future__ import annotations

from uuid import UUID

from backend.orchestrator.application.ports.repository import (
    OrchestratorStepRepositoryPort,
)
from backend.orchestrator.application.use_cases.dto import (
    GetStepRequest,
    WorkflowStepResponse,
)
from backend.orchestrator.application.use_cases.exceptions import (
    WorkflowStepNotFoundError,
)
from backend.orchestrator.domain.model import WorkflowId


class GetStepUseCase:
    def __init__(
        self,
        step_repo: OrchestratorStepRepositoryPort,
    ) -> None:
        self._step_repo = step_repo

    def execute(
        self, request: GetStepRequest
    ) -> WorkflowStepResponse:
        sid = WorkflowId(value=UUID(request.step_id))
        step = self._step_repo.find_by_id(sid)
        if step is None:
            raise WorkflowStepNotFoundError(request.step_id)

        return WorkflowStepResponse(
            step_id=str(step.step_id),
            agent_role=step.agent_role.value,
            execution_order=int(step.execution_order),
            status=step.status.value,
            result=str(step.result) if step.result else None,
            failure_reason=str(step.failure_reason)
            if step.failure_reason else None,
        )
