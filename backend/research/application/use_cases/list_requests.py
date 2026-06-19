from __future__ import annotations

from backend.research.application.ports.repository import (
    ResearchRequestRepositoryPort,
)
from backend.research.application.use_cases.dto import (
    ListRequestsRequest,
    ListRequestsResponse,
    RequestResponse,
)
from backend.research.domain.model import ResearchPriority, ResearchStatus


class ListRequestsUseCase:
    def __init__(
        self,
        request_repo: ResearchRequestRepositoryPort,
    ) -> None:
        self._request_repo = request_repo

    def execute(
        self, request: ListRequestsRequest
    ) -> ListRequestsResponse:
        if request.status is not None:
            status = ResearchStatus(request.status)
            requests = self._request_repo.find_by_status(status)
        elif request.priority is not None:
            priority = ResearchPriority(request.priority)
            requests = self._request_repo.find_by_priority(priority)
        else:
            requests = []

        items = [
            RequestResponse(
                request_id=str(r.request_id),
                query=str(r.query) if r.query else None,
                goal=str(r.goal) if r.goal else None,
                priority=r.priority.value,
                status=r.status.value,
                failure_reason=str(r.failure_reason)
                if r.failure_reason else None,
                created_at=r.created_at,
                updated_at=r.updated_at,
                job_count=len(r.jobs),
            )
            for r in requests
        ]

        return ListRequestsResponse(requests=items, total=len(items))
