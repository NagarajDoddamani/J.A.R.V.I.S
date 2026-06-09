from __future__ import annotations

from backend.knowledge.application.ports.clock import KnowledgeClockPort
from backend.knowledge.application.ports.id_generator import KnowledgeIdGeneratorPort
from backend.knowledge.application.ports.outbox import KnowledgeOutboxPort
from backend.knowledge.application.ports.repository import (
    KnowledgeSourceRepositoryPort,
)
from backend.knowledge.application.use_cases.dto import (
    RegisterSourceRequest,
    RegisterSourceResponse,
)
from backend.knowledge.domain.factory import KnowledgeFactory


class RegisterSourceUseCase:
    def __init__(
        self,
        source_repo: KnowledgeSourceRepositoryPort,
        outbox: KnowledgeOutboxPort,
        clock: KnowledgeClockPort,
        id_generator: KnowledgeIdGeneratorPort,
    ) -> None:
        self._source_repo = source_repo
        self._outbox = outbox
        self._clock = clock
        self._id_generator = id_generator

    def execute(self, request: RegisterSourceRequest) -> RegisterSourceResponse:
        source, event = KnowledgeFactory.register_source(
            name=request.name,
            source_type=request.source_type,
            location=request.location,
            classification=request.classification,
        )
        self._source_repo.save(source)
        self._outbox.append(event)
        return RegisterSourceResponse(
            source_id=str(source.source_id),
            name=source.name,
            source_type=source.source_type.value,
            location=str(source.location) if source.location else None,
            classification=source.classification,
            status=source.status.value,
            created_at=source.created_at,
        )
