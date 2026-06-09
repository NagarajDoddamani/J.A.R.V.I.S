from __future__ import annotations

from backend.knowledge.application.ports.outbox import KnowledgeOutboxPort
from backend.knowledge.application.ports.repository import (
    IngestionJobRepositoryPort,
)
from backend.knowledge.application.use_cases.dto import (
    FailIngestionRequest,
    FailIngestionResponse,
)
from backend.knowledge.application.use_cases.exceptions import (
    IngestionJobNotFoundError,
    InvalidIngestionTransitionError,
)
from backend.knowledge.domain.model import IngestionJobId, IngestionStatus


class FailIngestionUseCase:
    def __init__(
        self,
        job_repo: IngestionJobRepositoryPort,
        outbox: KnowledgeOutboxPort,
    ) -> None:
        self._job_repo = job_repo
        self._outbox = outbox

    def execute(self, request: FailIngestionRequest) -> FailIngestionResponse:
        job_id = IngestionJobId(value=__import__("uuid").UUID(request.job_id))
        job = self._job_repo.find_by_id(job_id)
        if job is None:
            raise IngestionJobNotFoundError(request.job_id)
        if job.status != IngestionStatus.RUNNING:
            raise InvalidIngestionTransitionError(
                job.status.value, IngestionStatus.FAILED.value
            )
        job.fail(request.error_message)
        events = job.events
        self._job_repo.save(job)
        for event in events:
            self._outbox.append(event)
        return FailIngestionResponse(
            job_id=str(job.job_id),
            status=job.status.value,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )
