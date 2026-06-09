from __future__ import annotations

from backend.knowledge.application.ports.repository import (
    KnowledgeChunkRepositoryPort,
)
from backend.knowledge.application.use_cases.dto import (
    ChunkResponse,
    GetChunksByDocumentRequest,
    GetChunksByDocumentResponse,
)
from backend.knowledge.domain.model import DocumentId


class GetChunksByDocumentUseCase:
    def __init__(
        self,
        chunk_repo: KnowledgeChunkRepositoryPort,
    ) -> None:
        self._chunk_repo = chunk_repo

    def execute(
        self, request: GetChunksByDocumentRequest
    ) -> GetChunksByDocumentResponse:
        document_id = DocumentId(value=__import__("uuid").UUID(request.document_id))
        chunks = self._chunk_repo.find_by_document_id(document_id)
        return GetChunksByDocumentResponse(
            chunks=[
                ChunkResponse(
                    chunk_id=str(c.chunk_id),
                    document_id=str(c.document_id) if c.document_id else None,
                    chunk_index=int(c.chunk_index) if c.chunk_index else None,
                    content=c.content.value if c.content else None,
                    classification=c.classification,
                    created_at=c.created_at,
                )
                for c in chunks
            ]
        )
