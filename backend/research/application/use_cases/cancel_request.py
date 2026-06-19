from __future__ import annotations

from uuid import UUID

from backend.research.application.ports.outbox import ResearchOutboxPort
from backend.research.application.ports.repository import (
    ResearchRequestRepositoryPort,
)
from backend.research.application.use_cases.dto import (
    RequestLifecycleRequest,
    RequestLifecycleResponse,
)
from backend.research.application.use_cases.exceptions import (
    ResearchRequestNotFoundError,
)
from backend.research.domain.model import ResearchRequestId


class CancelRequestUseCase:
    def __init__(
        self,
        request_repo: ResearchRequestRepositoryPort,
        outbox: ResearchOutboxPort,
    ) -> None:
        self._request_repo = request_repo
        self._outbox = outbox

    def execute(
        self, request: RequestLifecycleRequest
    ) -> RequestLifecycleResponse:
        req_id = ResearchRequestId(value=UUID(request.request_id))
        req = self._request_repo.find_by_id(req_id)
        if req is None:
            raise ResearchRequestNotFoundError(request.request_id)

        req.cancel()
        event = req.events[-1]
        self._request_repo.save(req)
        self._outbox.append(event)

        return RequestLifecycleResponse(
            request_id=str(req.request_id),
            status=req.status.value,
            updated_at=req.updated_at,
        )
