from __future__ import annotations

from backend.knowledge.application.ports.repository import (
    KnowledgeSourceRepositoryPort,
)
from backend.knowledge.application.use_cases.dto import (
    ListSourcesRequest,
    ListSourcesResponse,
    SourceResponse,
)
from backend.knowledge.domain.model import SourceStatus, SourceType


class ListSourcesUseCase:
    def __init__(
        self,
        source_repo: KnowledgeSourceRepositoryPort,
    ) -> None:
        self._source_repo = source_repo

    def execute(self, request: ListSourcesRequest) -> ListSourcesResponse:
        if request.status is not None:
            sources = self._source_repo.find_by_status(
                SourceStatus(request.status)
            )
        elif request.source_type is not None:
            sources = self._source_repo.find_by_type(
                SourceType(request.source_type)
            )
        else:
            all_sources: list = []
            for status in SourceStatus:
                all_sources.extend(self._source_repo.find_by_status(status))
            sources = all_sources

        return ListSourcesResponse(
            sources=[
                SourceResponse(
                    source_id=str(s.source_id),
                    name=s.name,
                    source_type=s.source_type.value,
                    location=str(s.location) if s.location else None,
                    classification=s.classification,
                    status=s.status.value,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                    deleted_at=s.deleted_at,
                )
                for s in sources
            ]
        )
