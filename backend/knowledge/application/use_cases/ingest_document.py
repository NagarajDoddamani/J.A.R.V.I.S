from __future__ import annotations

from backend.knowledge.application.ports.clock import KnowledgeClockPort
from backend.knowledge.application.ports.id_generator import KnowledgeIdGeneratorPort
from backend.knowledge.application.ports.outbox import KnowledgeOutboxPort
from backend.knowledge.application.ports.repository import (
    KnowledgeDocumentRepositoryPort,
    KnowledgeSourceRepositoryPort,
)
from backend.knowledge.application.use_cases.dto import (
    IngestDocumentRequest,
    IngestDocumentResponse,
)
from backend.knowledge.application.use_cases.exceptions import (
    SourceInactiveError,
    SourceNotFoundError,
)
from backend.knowledge.domain.factory import KnowledgeFactory
from backend.knowledge.domain.model import KnowledgeSourceId


class IngestDocumentUseCase:
    def __init__(
        self,
        source_repo: KnowledgeSourceRepositoryPort,
        document_repo: KnowledgeDocumentRepositoryPort,
        outbox: KnowledgeOutboxPort,
        clock: KnowledgeClockPort,
        id_generator: KnowledgeIdGeneratorPort,
    ) -> None:
        self._source_repo = source_repo
        self._document_repo = document_repo
        self._outbox = outbox
        self._clock = clock
        self._id_generator = id_generator

    def execute(self, request: IngestDocumentRequest) -> IngestDocumentResponse:
        source_id = KnowledgeSourceId(value=__import__("uuid").UUID(request.source_id))
        source = self._source_repo.find_by_id(source_id)
        if source is None:
            raise SourceNotFoundError(request.source_id)
        if not source.is_active:
            raise SourceInactiveError(request.source_id)

        document, event = KnowledgeFactory.ingest_document(
            source=source,
            title=request.title,
            checksum=request.checksum,
            classification=request.classification,
        )
        self._document_repo.save(document)
        self._outbox.append(event)

        return IngestDocumentResponse(
            document_id=str(document.document_id),
            source_id=str(document.source_id) if document.source_id else None,
            title=document.title,
            checksum=str(document.checksum) if document.checksum else None,
            classification=document.classification,
            status=document.status.value,
            revision=document.revision,
            created_at=document.created_at,
        )
