from __future__ import annotations

from backend.research.application.ports.outbox import ResearchOutboxPort
from backend.research.application.ports.repository import (
    ResearchRequestRepositoryPort,
)
from backend.research.application.use_cases.dto import (
    CreateRequestRequest,
    CreateRequestResponse,
)
from backend.research.domain.factory import ResearchFactory


class CreateRequestUseCase:
    def __init__(
        self,
        request_repo: ResearchRequestRepositoryPort,
        outbox: ResearchOutboxPort,
    ) -> None:
        self._request_repo = request_repo
        self._outbox = outbox

    def execute(
        self, request: CreateRequestRequest
    ) -> CreateRequestResponse:
        req, event = ResearchFactory.create_request(
            query=request.query,
            goal=request.goal,
            priority=request.priority,
        )
        self._request_repo.save(req)
        self._outbox.append(event)

        return CreateRequestResponse(
            request_id=str(req.request_id),
            query=str(req.query) if req.query else None,
            goal=str(req.goal) if req.goal else None,
            priority=req.priority.value,
            status=req.status.value,
            created_at=req.created_at,
        )
