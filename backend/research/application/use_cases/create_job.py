from __future__ import annotations

from uuid import UUID

from backend.research.application.ports.outbox import ResearchOutboxPort
from backend.research.application.ports.repository import (
    ResearchJobRepositoryPort,
    ResearchRequestRepositoryPort,
)
from backend.research.application.use_cases.dto import (
    CreateJobRequest,
    CreateJobResponse,
)
from backend.research.application.use_cases.exceptions import (
    ResearchRequestNotFoundError,
)
from backend.research.domain.factory import ResearchFactory
from backend.research.domain.model import ResearchRequestId


class CreateJobUseCase:
    def __init__(
        self,
        request_repo: ResearchRequestRepositoryPort,
        job_repo: ResearchJobRepositoryPort,
        outbox: ResearchOutboxPort,
    ) -> None:
        self._request_repo = request_repo
        self._job_repo = job_repo
        self._outbox = outbox

    def execute(self, request: CreateJobRequest) -> CreateJobResponse:
        req_id = ResearchRequestId(value=UUID(request.request_id))
        req = self._request_repo.find_by_id(req_id)
        if req is None:
            raise ResearchRequestNotFoundError(request.request_id)

        job = ResearchFactory.create_job(
            request=req,
            goal=request.goal,
            priority=request.priority,
        )
        self._request_repo.save(req)
        self._job_repo.save(job)

        return CreateJobResponse(
            job_id=str(job.job_id),
            request_id=request.request_id,
            goal=str(job.goal) if job.goal else None,
            priority=job.priority.value,
            status=job.status.value,
        )
