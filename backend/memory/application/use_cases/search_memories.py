from __future__ import annotations

from uuid import UUID

from backend.memory.application.ports.repository import MemoryRepositoryPort
from backend.memory.application.use_cases.dto import (
    MemoryResponse,
    SearchMemoriesRequest,
    SearchMemoriesResponse,
)
from backend.memory.domain.model import ConsentId, MemoryCategory


class SearchMemoriesUseCase:
    """Search memories by category, consent, or source."""

    def __init__(self, memory_repo: MemoryRepositoryPort) -> None:
        self._memory_repo = memory_repo

    def execute(self, request: SearchMemoriesRequest) -> SearchMemoriesResponse:
        results: list | None = None

        if request.consent_id is not None:
            consent_id = ConsentId(value=UUID(request.consent_id))
            results = self._memory_repo.find_by_consent_id(consent_id)

        if request.category is not None:
            category = MemoryCategory(request.category)
            cat_results = self._memory_repo.find_by_category(category)
            if results is not None:
                result_ids = {id(m) for m in results}
                results = [m for m in cat_results if id(m) in result_ids]
            else:
                results = cat_results

        if request.source_type is not None:
            src_results = self._memory_repo.find_by_source(
                request.source_type, request.source_id
            )
            if results is not None:
                result_ids = {id(m) for m in results}
                results = [m for m in src_results if id(m) in result_ids]
            else:
                results = src_results

        if results is None:
            return SearchMemoriesResponse(memories=[], total=0)

        memories = [
            MemoryResponse(
                memory_id=str(m.memory_id),
                consent_id=str(m.consent_id),
                content=m.content.value,
                category=m.category.value,
                source_type=m.source_type,
                source_id=m.source_id,
                classification=m.classification,
                sensitivity=m.sensitivity,
                retention_policy=m.retention.policy,
                retention_status=m.retention_status.value,
                revision=int(m.revision),
                created_at=m.created_at,
                updated_at=m.updated_at,
                deleted_at=m.deleted_at,
            )
            for m in results
        ]

        return SearchMemoriesResponse(memories=memories, total=len(memories))
