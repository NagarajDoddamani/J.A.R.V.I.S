from __future__ import annotations

from uuid import UUID

from backend.memory.application.ports.repository import MemoryRepositoryPort
from backend.memory.application.use_cases.dto import (
    GetMemoryRequest,
    MemoryResponse,
)
from backend.memory.application.use_cases.exceptions import MemoryNotFoundError


class GetMemoryUseCase:
    """Retrieve a single memory by its unique identifier."""

    def __init__(self, memory_repo: MemoryRepositoryPort) -> None:
        self._memory_repo = memory_repo

    def execute(self, request: GetMemoryRequest) -> MemoryResponse:
        memory_id = UUID(request.memory_id)
        memory = self._memory_repo.find_by_id(memory_id)
        if memory is None:
            raise MemoryNotFoundError(request.memory_id)

        return MemoryResponse(
            memory_id=str(memory.memory_id),
            consent_id=str(memory.consent_id),
            content=memory.content.value,
            category=memory.category.value,
            source_type=memory.source_type,
            source_id=memory.source_id,
            classification=memory.classification,
            sensitivity=memory.sensitivity,
            retention_policy=memory.retention.policy,
            retention_status=memory.retention_status.value,
            revision=int(memory.revision),
            created_at=memory.created_at,
            updated_at=memory.updated_at,
            deleted_at=memory.deleted_at,
        )
