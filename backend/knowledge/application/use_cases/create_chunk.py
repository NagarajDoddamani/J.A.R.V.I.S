from __future__ import annotations

from backend.knowledge.application.ports.clock import KnowledgeClockPort
from backend.knowledge.application.ports.id_generator import KnowledgeIdGeneratorPort
from backend.knowledge.application.ports.outbox import KnowledgeOutboxPort
from backend.knowledge.application.ports.repository import (
    KnowledgeChunkRepositoryPort,
    KnowledgeDocumentRepositoryPort,
)
from backend.knowledge.application.use_cases.dto import (
    CreateChunkRequest,
    CreateChunkResponse,
)
from backend.knowledge.application.use_cases.exceptions import (
    DocumentDeletedError,
    DocumentNotFoundError,
)
from backend.knowledge.domain.factory import KnowledgeFactory
from backend.knowledge.domain.model import DocumentId


class CreateChunkUseCase:
    def __init__(
        self,
        document_repo: KnowledgeDocumentRepositoryPort,
        chunk_repo: KnowledgeChunkRepositoryPort,
        outbox: KnowledgeOutboxPort,
        clock: KnowledgeClockPort,
        id_generator: KnowledgeIdGeneratorPort,
    ) -> None:
        self._document_repo = document_repo
        self._chunk_repo = chunk_repo
        self._outbox = outbox
        self._clock = clock
        self._id_generator = id_generator

    def execute(self, request: CreateChunkRequest) -> CreateChunkResponse:
        document_id = DocumentId(value=__import__("uuid").UUID(request.document_id))
        document = self._document_repo.find_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(request.document_id)
        if document.is_deleted:
            raise DocumentDeletedError(request.document_id)

        existing_chunks = self._chunk_repo.find_by_document_id(document_id)
        existing_indices = [
            c.chunk_index for c in existing_chunks if c.chunk_index is not None
        ]

        chunk, event = KnowledgeFactory.create_chunk(
            document=document,
            chunk_index=request.chunk_index,
            content=request.content,
            classification=request.classification,
            existing_indices=existing_indices,
        )
        self._chunk_repo.save(chunk)
        self._outbox.append(event)

        return CreateChunkResponse(
            chunk_id=str(chunk.chunk_id),
            document_id=str(chunk.document_id) if chunk.document_id else None,
            chunk_index=int(chunk.chunk_index) if chunk.chunk_index else None,
            content=chunk.content.value if chunk.content else None,
            classification=chunk.classification,
            created_at=chunk.created_at,
        )
