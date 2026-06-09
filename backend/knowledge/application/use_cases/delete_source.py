from __future__ import annotations

from backend.knowledge.application.ports.outbox import KnowledgeOutboxPort
from backend.knowledge.application.ports.repository import (
    KnowledgeSourceRepositoryPort,
)
from backend.knowledge.application.use_cases.dto import (
    DeleteSourceRequest,
    DeleteSourceResponse,
)
from backend.knowledge.application.use_cases.exceptions import SourceNotFoundError
from backend.knowledge.domain.model import KnowledgeSourceId


class DeleteSourceUseCase:
    def __init__(
        self,
        source_repo: KnowledgeSourceRepositoryPort,
        outbox: KnowledgeOutboxPort,
    ) -> None:
        self._source_repo = source_repo
        self._outbox = outbox

    def execute(self, request: DeleteSourceRequest) -> DeleteSourceResponse:
        source_id = KnowledgeSourceId(value=__import__("uuid").UUID(request.source_id))
        source = self._source_repo.find_by_id(source_id)
        if source is None:
            raise SourceNotFoundError(request.source_id)
        source.delete()
        for event in source.events:
            self._outbox.append(event)
        self._source_repo.save(source)
        return DeleteSourceResponse(
            source_id=str(source.source_id),
            deleted_at=source.deleted_at,
        )
