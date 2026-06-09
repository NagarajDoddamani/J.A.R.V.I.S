from __future__ import annotations

from backend.knowledge.application.ports.repository import (
    KnowledgeSourceRepositoryPort,
)
from backend.knowledge.application.use_cases.dto import (
    GetSourceRequest,
    SourceResponse,
)
from backend.knowledge.application.use_cases.exceptions import SourceNotFoundError
from backend.knowledge.domain.model import KnowledgeSourceId


class GetSourceUseCase:
    def __init__(
        self,
        source_repo: KnowledgeSourceRepositoryPort,
    ) -> None:
        self._source_repo = source_repo

    def execute(self, request: GetSourceRequest) -> SourceResponse:
        source_id = KnowledgeSourceId(value=__import__("uuid").UUID(request.source_id))
        source = self._source_repo.find_by_id(source_id)
        if source is None:
            raise SourceNotFoundError(request.source_id)
        return SourceResponse(
            source_id=str(source.source_id),
            name=source.name,
            source_type=source.source_type.value,
            location=str(source.location) if source.location else None,
            classification=source.classification,
            status=source.status.value,
            created_at=source.created_at,
            updated_at=source.updated_at,
            deleted_at=source.deleted_at,
        )
