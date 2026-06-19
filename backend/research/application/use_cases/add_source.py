from __future__ import annotations

from uuid import UUID

from backend.research.application.ports.outbox import ResearchOutboxPort
from backend.research.application.ports.repository import (
    ResearchJobRepositoryPort,
    ResearchSourceRepositoryPort,
)
from backend.research.application.use_cases.dto import (
    AddSourceRequest,
    AddSourceResponse,
)
from backend.research.application.use_cases.exceptions import (
    ResearchJobNotFoundError,
)
from backend.research.domain.factory import ResearchFactory
from backend.research.domain.model import ResearchJobId


class AddSourceUseCase:
    def __init__(
        self,
        job_repo: ResearchJobRepositoryPort,
        source_repo: ResearchSourceRepositoryPort,
        outbox: ResearchOutboxPort,
    ) -> None:
        self._job_repo = job_repo
        self._source_repo = source_repo
        self._outbox = outbox

    def execute(self, request: AddSourceRequest) -> AddSourceResponse:
        job_id = ResearchJobId(value=UUID(request.job_id))
        job = self._job_repo.find_by_id(job_id)
        if job is None:
            raise ResearchJobNotFoundError(request.job_id)

        source = ResearchFactory.add_source(
            job=job,
            reference=request.reference,
            source_type=request.source_type,
            confidence_score=request.confidence_score,
        )
        source_events = [e for e in job.events if hasattr(e, "source_id")]
        if source_events:
            self._outbox.append(source_events[-1])
        self._job_repo.save(job)
        self._source_repo.save(source)

        return AddSourceResponse(
            source_id=str(source.source_id),
            job_id=request.job_id,
            source_type=source.source_type.value,
            reference=str(source.reference) if source.reference else None,
            confidence_score=float(source.confidence_score)
            if source.confidence_score else None,
        )
