from __future__ import annotations

from uuid import UUID

from backend.research.application.ports.repository import (
    ResearchJobRepositoryPort,
)
from backend.research.application.use_cases.dto import (
    ListJobsRequest,
    ListJobsResponse,
    JobResponse,
)
from backend.research.domain.model import (
    ResearchJobId,
    ResearchRequestId,
    ResearchStatus,
)


class ListJobsUseCase:
    def __init__(
        self,
        job_repo: ResearchJobRepositoryPort,
    ) -> None:
        self._job_repo = job_repo

    def execute(self, request: ListJobsRequest) -> ListJobsResponse:
        if request.status is not None:
            status = ResearchStatus(request.status)
            jobs = self._job_repo.find_by_status(status)
        elif request.request_id is not None:
            req_id = ResearchRequestId(value=UUID(request.request_id))
            jobs = self._job_repo.find_by_request_id(req_id)
        else:
            jobs = []

        items = [
            JobResponse(
                job_id=str(j.job_id),
                goal=str(j.goal) if j.goal else None,
                priority=j.priority.value,
                status=j.status.value,
                summary=str(j.summary) if j.summary else None,
                failure_reason=str(j.failure_reason)
                if j.failure_reason else None,
                created_at=j.created_at,
                completed_at=j.completed_at,
                source_count=len(j.sources),
            )
            for j in jobs
        ]

        return ListJobsResponse(jobs=items, total=len(items))
