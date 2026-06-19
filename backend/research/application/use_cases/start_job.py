from __future__ import annotations

from uuid import UUID

from backend.research.application.ports.outbox import ResearchOutboxPort
from backend.research.application.ports.repository import (
    ResearchJobRepositoryPort,
)
from backend.research.application.use_cases.dto import (
    JobLifecycleRequest,
    JobLifecycleResponse,
)
from backend.research.application.use_cases.exceptions import (
    ResearchJobNotFoundError,
)
from backend.research.domain.model import ResearchJobId


class StartJobUseCase:
    def __init__(
        self,
        job_repo: ResearchJobRepositoryPort,
        outbox: ResearchOutboxPort,
    ) -> None:
        self._job_repo = job_repo
        self._outbox = outbox

    def execute(
        self, request: JobLifecycleRequest
    ) -> JobLifecycleResponse:
        job_id = ResearchJobId(value=UUID(request.job_id))
        job = self._job_repo.find_by_id(job_id)
        if job is None:
            raise ResearchJobNotFoundError(request.job_id)

        job.start()
        self._job_repo.save(job)

        return JobLifecycleResponse(
            job_id=str(job.job_id),
            status=job.status.value,
        )
