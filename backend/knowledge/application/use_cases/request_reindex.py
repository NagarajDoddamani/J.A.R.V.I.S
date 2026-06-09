from __future__ import annotations

from backend.knowledge.application.ports.outbox import KnowledgeOutboxPort
from backend.knowledge.application.ports.repository import (
    KnowledgeSourceRepositoryPort,
)
from backend.knowledge.application.use_cases.dto import (
    ReindexResponse,
    RequestReindexRequest,
)
from backend.knowledge.application.use_cases.exceptions import (
    SourceInactiveError,
    SourceNotFoundError,
)
from backend.knowledge.domain.factory import KnowledgeFactory
from backend.knowledge.domain.model import KnowledgeSourceId


class RequestReindexUseCase:
    def __init__(
        self,
        source_repo: KnowledgeSourceRepositoryPort,
        outbox: KnowledgeOutboxPort,
    ) -> None:
        self._source_repo = source_repo
        self._outbox = outbox

    def execute(self, request: RequestReindexRequest) -> ReindexResponse:
        source_id = KnowledgeSourceId(value=__import__("uuid").UUID(request.source_id))
        source = self._source_repo.find_by_id(source_id)
        if source is None:
            raise SourceNotFoundError(request.source_id)
        if not source.is_active:
            raise SourceInactiveError(request.source_id)

        event = KnowledgeFactory.request_reindex(source=source)
        self._outbox.append(event)

        return ReindexResponse(
            source_id=str(source.source_id),
        )
