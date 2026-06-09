from __future__ import annotations

from uuid import UUID

from backend.memory.application.ports.outbox import MemoryOutboxPort
from backend.memory.application.ports.repository import MemoryRepositoryPort
from backend.memory.application.use_cases.dto import (
    DeleteMemoryRequest,
    DeleteMemoryResponse,
)
from backend.memory.application.use_cases.exceptions import MemoryNotFoundError
class DeleteMemoryUseCase:
    """Soft-delete a memory.

    Marks the memory as deleted, persists the change, and emits
    a ``MemoryDeleted`` event to the outbox.
    """

    def __init__(
        self,
        memory_repo: MemoryRepositoryPort,
        outbox: MemoryOutboxPort,
    ) -> None:
        self._memory_repo = memory_repo
        self._outbox = outbox

    def execute(self, request: DeleteMemoryRequest) -> DeleteMemoryResponse:
        memory_id = UUID(request.memory_id)
        memory = self._memory_repo.find_by_id(memory_id)
        if memory is None:
            raise MemoryNotFoundError(request.memory_id)

        memory.delete()

        self._memory_repo.save(memory)
        for event in memory.events:
            self._outbox.append(event)
        memory._clear_events()

        return DeleteMemoryResponse(
            memory_id=request.memory_id,
            deleted_at=memory.deleted_at,  # type: ignore[arg-type]
            revision=int(memory.revision),
        )
