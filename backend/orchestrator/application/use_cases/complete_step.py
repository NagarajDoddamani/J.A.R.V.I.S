from __future__ import annotations

from uuid import UUID

from backend.orchestrator.application.ports.outbox import OrchestratorOutboxPort
from backend.orchestrator.application.ports.repository import (
    OrchestratorStepRepositoryPort,
)
from backend.orchestrator.application.use_cases.dto import (
    CompleteStepRequest,
    CompleteStepResponse,
)
from backend.orchestrator.application.use_cases.exceptions import (
    WorkflowStepNotFoundError,
)
from backend.orchestrator.domain.factory import OrchestratorFactory
from backend.orchestrator.domain.model import WorkflowId


class CompleteStepUseCase:
    def __init__(
        self,
        step_repo: OrchestratorStepRepositoryPort,
        outbox: OrchestratorOutboxPort,
    ) -> None:
        self._step_repo = step_repo
        self._outbox = outbox

    def execute(
        self, request: CompleteStepRequest
    ) -> CompleteStepResponse:
        step = self._step_repo.find_by_id(WorkflowId(value=UUID(request.step_id)))
        if step is None:
            raise WorkflowStepNotFoundError(request.step_id)

        event = OrchestratorFactory.complete_step(
            step=step,
            result=request.result,
        )
        self._step_repo.save(step)
        self._outbox.append(event)

        return CompleteStepResponse(
            step_id=str(step.step_id),
            status=step.status.value,
            result=request.result,
        )
