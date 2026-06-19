from __future__ import annotations

from uuid import UUID

from backend.research.application.ports.outbox import ResearchOutboxPort
from backend.research.application.ports.repository import (
    ResearchJobRepositoryPort,
)
from backend.research.application.use_cases.dto import (
    FailJobRequest,
    FailJobResponse,
)
from backend.research.application.use_cases.exceptions import (
    ResearchJobNotFoundError,
)
from backend.research.domain.factory import ResearchFactory
from backend.research.domain.model import ResearchJobId


class FailJobUseCase:
    def __init__(
        self,
        job_repo: ResearchJobRepositoryPort,
        outbox: ResearchOutboxPort,
    ) -> None:
        self._job_repo = job_repo
        self._outbox = outbox

    def execute(self, request: FailJobRequest) -> FailJobResponse:
        job_id = ResearchJobId(value=UUID(request.job_id))
        job = self._job_repo.find_by_id(job_id)
        if job is None:
            raise ResearchJobNotFoundError(request.job_id)

        ResearchFactory.fail_job(job=job, reason=request.failure_reason)
        self._job_repo.save(job)

        return FailJobResponse(
            job_id=str(job.job_id),
            status=job.status.value,
            failure_reason=request.failure_reason,
        )
