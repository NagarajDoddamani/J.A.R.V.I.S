from __future__ import annotations

from uuid import UUID

from backend.research.application.ports.repository import (
    ResearchJobRepositoryPort,
)
from backend.research.application.use_cases.dto import (
    GetJobRequest,
    JobResponse,
)
from backend.research.application.use_cases.exceptions import (
    ResearchJobNotFoundError,
)
from backend.research.domain.model import ResearchJobId


class GetJobUseCase:
    def __init__(
        self,
        job_repo: ResearchJobRepositoryPort,
    ) -> None:
        self._job_repo = job_repo

    def execute(self, request: GetJobRequest) -> JobResponse:
        job_id = ResearchJobId(value=UUID(request.job_id))
        job = self._job_repo.find_by_id(job_id)
        if job is None:
            raise ResearchJobNotFoundError(request.job_id)

        return JobResponse(
            job_id=str(job.job_id),
            goal=str(job.goal) if job.goal else None,
            priority=job.priority.value,
            status=job.status.value,
            summary=str(job.summary) if job.summary else None,
            failure_reason=str(job.failure_reason)
            if job.failure_reason else None,
            created_at=job.created_at,
            completed_at=job.completed_at,
            source_count=len(job.sources),
        )
