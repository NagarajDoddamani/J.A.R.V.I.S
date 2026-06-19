from __future__ import annotations

from uuid import UUID

from backend.research.application.ports.repository import (
    ResearchRequestRepositoryPort,
)
from backend.research.application.use_cases.dto import (
    GetRequestRequest,
    RequestResponse,
)
from backend.research.application.use_cases.exceptions import (
    ResearchRequestNotFoundError,
)
from backend.research.domain.model import ResearchRequestId


class GetRequestUseCase:
    def __init__(
        self,
        request_repo: ResearchRequestRepositoryPort,
    ) -> None:
        self._request_repo = request_repo

    def execute(
        self, request: GetRequestRequest
    ) -> RequestResponse:
        req_id = ResearchRequestId(value=UUID(request.request_id))
        req = self._request_repo.find_by_id(req_id)
        if req is None:
            raise ResearchRequestNotFoundError(request.request_id)

        return RequestResponse(
            request_id=str(req.request_id),
            query=str(req.query) if req.query else None,
            goal=str(req.goal) if req.goal else None,
            priority=req.priority.value,
            status=req.status.value,
            failure_reason=str(req.failure_reason)
            if req.failure_reason else None,
            created_at=req.created_at,
            updated_at=req.updated_at,
            job_count=len(req.jobs),
        )
