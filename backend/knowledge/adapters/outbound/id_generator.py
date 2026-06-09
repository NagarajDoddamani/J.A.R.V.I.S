from __future__ import annotations

from backend.knowledge.domain.model import (
    ChunkId,
    DocumentId,
    IngestionJobId,
    KnowledgeSourceId,
)


class UuidGeneratorAdapter:
    def generate_source_id(self) -> KnowledgeSourceId:
        return KnowledgeSourceId()

    def generate_document_id(self) -> DocumentId:
        return DocumentId()

    def generate_chunk_id(self) -> ChunkId:
        return ChunkId()

    def generate_job_id(self) -> IngestionJobId:
        return IngestionJobId()
