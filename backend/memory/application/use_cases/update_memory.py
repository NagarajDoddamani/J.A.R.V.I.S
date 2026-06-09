from __future__ import annotations

from uuid import UUID

from backend.memory.application.ports.outbox import MemoryOutboxPort
from backend.memory.application.ports.repository import (
    ConsentRepositoryPort,
    MemoryRepositoryPort,
)
from backend.memory.application.use_cases.dto import (
    UpdateMemoryRequest,
    UpdateMemoryResponse,
)
from backend.memory.application.use_cases.exceptions import (
    ConsentNotFoundError,
    MemoryDeletedError,
    MemoryNotFoundError,
)
from backend.memory.domain.model import ConsentId, MemoryContent, MemoryState


class UpdateMemoryUseCase:
    """Update an existing memory's content.

    Loads the memory and its associated consent, validates the
    update is permitted, increments the revision, persists, and
    emits a ``MemoryUpdated`` event to the outbox.
    """

    def __init__(
        self,
        memory_repo: MemoryRepositoryPort,
        consent_repo: ConsentRepositoryPort,
        outbox: MemoryOutboxPort,
    ) -> None:
        self._memory_repo = memory_repo
        self._consent_repo = consent_repo
        self._outbox = outbox

    def execute(self, request: UpdateMemoryRequest) -> UpdateMemoryResponse:
        memory_id = UUID(request.memory_id)
        memory = self._memory_repo.find_by_id(memory_id)
        if memory is None:
            raise MemoryNotFoundError(request.memory_id)
        if memory.state == MemoryState.DELETED:
            raise MemoryDeletedError(request.memory_id)

        consent = self._consent_repo.find_by_id(memory.consent_id)
        if consent is None:
            raise ConsentNotFoundError(str(memory.consent_id))

        new_content = MemoryContent(value=request.content)
        memory.update(content=new_content, consent=consent)

        self._memory_repo.save(memory)
        for event in memory.events:
            self._outbox.append(event)
        memory._clear_events()

        return UpdateMemoryResponse(
            memory_id=str(memory.memory_id),
            consent_id=str(memory.consent_id),
            content=memory.content.value,
            category=memory.category.value,
            revision=int(memory.revision),
            updated_at=memory.updated_at,  # type: ignore[arg-type]
        )
