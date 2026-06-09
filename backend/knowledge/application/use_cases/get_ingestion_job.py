from __future__ import annotations

from backend.knowledge.application.ports.repository import (
    IngestionJobRepositoryPort,
)
from backend.knowledge.application.use_cases.dto import (
    GetIngestionJobRequest,
    IngestionJobResponse,
)
from backend.knowledge.application.use_cases.exceptions import (
    IngestionJobNotFoundError,
)
from backend.knowledge.domain.model import IngestionJobId


class GetIngestionJobUseCase:
    def __init__(
        self,
        job_repo: IngestionJobRepositoryPort,
    ) -> None:
        self._job_repo = job_repo

    def execute(self, request: GetIngestionJobRequest) -> IngestionJobResponse:
        job_id = IngestionJobId(value=__import__("uuid").UUID(request.job_id))
        job = self._job_repo.find_by_id(job_id)
        if job is None:
            raise IngestionJobNotFoundError(request.job_id)
        return IngestionJobResponse(
            job_id=str(job.job_id),
            source_id=str(job.source_id) if job.source_id else None,
            status=job.status.value,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )
