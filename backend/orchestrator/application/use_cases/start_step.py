from __future__ import annotations

from uuid import UUID

from backend.orchestrator.application.ports.outbox import OrchestratorOutboxPort
from backend.orchestrator.application.ports.repository import (
    OrchestratorStepRepositoryPort,
)
from backend.orchestrator.application.use_cases.dto import (
    StepLifecycleRequest,
    StepLifecycleResponse,
)
from backend.orchestrator.application.use_cases.exceptions import (
    WorkflowStepNotFoundError,
)
from backend.orchestrator.domain.model import WorkflowId


class StartStepUseCase:
    def __init__(
        self,
        step_repo: OrchestratorStepRepositoryPort,
        outbox: OrchestratorOutboxPort,
    ) -> None:
        self._step_repo = step_repo
        self._outbox = outbox

    def execute(
        self, request: StepLifecycleRequest
    ) -> StepLifecycleResponse:
        sid = WorkflowId(value=UUID(request.step_id))
        step = self._step_repo.find_by_id(sid)
        if step is None:
            raise WorkflowStepNotFoundError(request.step_id)

        step.start()
        event = step.events[-1]
        self._step_repo.save(step)
        self._outbox.append(event)

        return StepLifecycleResponse(
            step_id=str(step.step_id),
            status=step.status.value,
        )
