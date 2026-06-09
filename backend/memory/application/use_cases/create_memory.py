from __future__ import annotations

from uuid import UUID

from backend.memory.application.ports.clock import MemoryClockPort
from backend.memory.application.ports.id_generator import MemoryIdGeneratorPort
from backend.memory.application.ports.outbox import MemoryOutboxPort
from backend.memory.application.ports.repository import (
    ConsentRepositoryPort,
    MemoryRepositoryPort,
)
from backend.memory.application.use_cases.dto import (
    CreateMemoryRequest,
    CreateMemoryResponse,
)
from backend.memory.application.use_cases.exceptions import (
    ConsentNotActiveError,
    ConsentNotFoundError,
)
from backend.memory.domain.factory import MemoryFactory
from backend.memory.domain.model import (
    ConsentId,
    ConsentRecord,
    ConsentStatus,
    Provenance,
    RetentionPolicy,
)


class CreateMemoryUseCase:
    """Create a new memory.

    Loads the associated consent, validates it is ACTIVE, creates
    the ``Memory`` aggregate through the domain factory, persists it,
    and writes the resulting ``MemoryCreated`` event to the outbox.
    """

    def __init__(
        self,
        memory_repo: MemoryRepositoryPort,
        consent_repo: ConsentRepositoryPort,
        outbox: MemoryOutboxPort,
        clock: MemoryClockPort,
        id_generator: MemoryIdGeneratorPort,
    ) -> None:
        self._memory_repo = memory_repo
        self._consent_repo = consent_repo
        self._outbox = outbox
        self._clock = clock
        self._id_generator = id_generator

    def execute(self, request: CreateMemoryRequest) -> CreateMemoryResponse:
        consent_id = ConsentId(value=UUID(request.consent_id))
        consent = self._consent_repo.find_by_id(consent_id)
        if consent is None:
            raise ConsentNotFoundError(request.consent_id)
        if consent.status != ConsentStatus.ACTIVE:
            raise ConsentNotActiveError(request.consent_id)

        now = self._clock.now()
        provenance = Provenance(
            source=request.provenance_source,
            timestamp=now,
            actor_id=request.provenance_actor_id,
        )
        retention = RetentionPolicy(
            policy=request.retention_policy,
            ttl_days=request.retention_ttl_days,
        )

        memory, event = MemoryFactory.create(
            consent=consent,
            content=request.content,
            category=request.category,
            source_type=request.source_type,
            source_id=request.source_id,
            provenance=provenance,
            retention=retention,
            classification=request.classification,
            sensitivity=request.sensitivity,
            redaction_metadata=request.redaction_metadata,
        )

        self._memory_repo.save(memory)
        self._outbox.append(event)

        return CreateMemoryResponse(
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
        )
