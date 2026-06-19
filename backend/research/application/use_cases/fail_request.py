from __future__ import annotations

from uuid import UUID

from backend.research.application.ports.outbox import ResearchOutboxPort
from backend.research.application.ports.repository import (
    ResearchRequestRepositoryPort,
)
from backend.research.application.use_cases.dto import (
    FailRequestRequest,
    FailRequestResponse,
)
from backend.research.application.use_cases.exceptions import (
    ResearchRequestNotFoundError,
)
from backend.research.domain.model import FailureReason, ResearchRequestId


class FailRequestUseCase:
    def __init__(
        self,
        request_repo: ResearchRequestRepositoryPort,
        outbox: ResearchOutboxPort,
    ) -> None:
        self._request_repo = request_repo
        self._outbox = outbox

    def execute(
        self, request: FailRequestRequest
    ) -> FailRequestResponse:
        req_id = ResearchRequestId(value=UUID(request.request_id))
        req = self._request_repo.find_by_id(req_id)
        if req is None:
            raise ResearchRequestNotFoundError(request.request_id)

        reason = FailureReason(value=request.failure_reason)
        req.fail(reason)
        event = req.events[-1]
        self._request_repo.save(req)
        self._outbox.append(event)

        return FailRequestResponse(
            request_id=str(req.request_id),
            status=req.status.value,
            failure_reason=request.failure_reason,
            updated_at=req.updated_at,
        )
