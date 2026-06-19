from __future__ import annotations

from uuid import UUID

from backend.research.application.ports.outbox import ResearchOutboxPort
from backend.research.application.ports.repository import (
    ResearchJobRepositoryPort,
)
from backend.research.application.use_cases.dto import (
    GenerateSummaryRequest,
    GenerateSummaryResponse,
)
from backend.research.application.use_cases.exceptions import (
    ResearchJobNotFoundError,
)
from backend.research.domain.factory import ResearchFactory
from backend.research.domain.model import ResearchJobId


class CompleteJobUseCase:
    def __init__(
        self,
        job_repo: ResearchJobRepositoryPort,
        outbox: ResearchOutboxPort,
    ) -> None:
        self._job_repo = job_repo
        self._outbox = outbox

    def execute(
        self, request: GenerateSummaryRequest
    ) -> GenerateSummaryResponse:
        job_id = ResearchJobId(value=UUID(request.job_id))
        job = self._job_repo.find_by_id(job_id)
        if job is None:
            raise ResearchJobNotFoundError(request.job_id)

        ResearchFactory.complete_job(job=job, summary=request.summary)
        gen_event = [e for e in job.events if hasattr(e, "summary")]
        if gen_event:
            self._outbox.append(gen_event[-1])
        self._job_repo.save(job)

        return GenerateSummaryResponse(
            job_id=str(job.job_id),
            summary=request.summary,
            status=job.status.value,
        )
