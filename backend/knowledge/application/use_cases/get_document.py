from __future__ import annotations

from backend.knowledge.application.ports.repository import (
    KnowledgeDocumentRepositoryPort,
)
from backend.knowledge.application.use_cases.dto import (
    DocumentResponse,
    GetDocumentRequest,
)
from backend.knowledge.application.use_cases.exceptions import DocumentNotFoundError
from backend.knowledge.domain.model import DocumentId


class GetDocumentUseCase:
    def __init__(
        self,
        document_repo: KnowledgeDocumentRepositoryPort,
    ) -> None:
        self._document_repo = document_repo

    def execute(self, request: GetDocumentRequest) -> DocumentResponse:
        document_id = DocumentId(value=__import__("uuid").UUID(request.document_id))
        document = self._document_repo.find_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(request.document_id)
        return DocumentResponse(
            document_id=str(document.document_id),
            source_id=str(document.source_id) if document.source_id else None,
            title=document.title,
            checksum=str(document.checksum) if document.checksum else None,
            classification=document.classification,
            status=document.status.value,
            revision=document.revision,
            created_at=document.created_at,
            updated_at=document.updated_at,
            deleted_at=document.deleted_at,
        )
