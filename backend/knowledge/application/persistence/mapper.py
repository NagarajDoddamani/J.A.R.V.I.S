from __future__ import annotations

from typing import Protocol, Union

from backend.knowledge.application.persistence.dto import (
    IngestionJobStorageDTO,
    KnowledgeChunkStorageDTO,
    KnowledgeDocumentStorageDTO,
    KnowledgeOutboxStorageDTO,
    KnowledgeSourceStorageDTO,
)
from backend.knowledge.domain.model import (
    ChunkCreated,
    DocumentDeleted,
    DocumentIndexed,
    DocumentIngested,
    IngestionCompleted,
    IngestionFailed,
    IngestionJob,
    IngestionStarted,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSourceDeleted,
    KnowledgeSourceRegistered,
    ReindexRequested,
)

KnowledgeOutboxDomainEvent = Union[
    KnowledgeSourceRegistered,
    KnowledgeSourceDeleted,
    DocumentIngested,
    DocumentIndexed,
    DocumentDeleted,
    ChunkCreated,
    ReindexRequested,
    IngestionStarted,
    IngestionCompleted,
    IngestionFailed,
]


class KnowledgeSourceMapper(Protocol):
    def domain_to_dto(self, source: KnowledgeSource) -> KnowledgeSourceStorageDTO:
        ...

    def dto_to_domain(self, dto: KnowledgeSourceStorageDTO) -> KnowledgeSource:
        ...


class KnowledgeDocumentMapper(Protocol):
    def domain_to_dto(self, document: KnowledgeDocument) -> KnowledgeDocumentStorageDTO:
        ...

    def dto_to_domain(self, dto: KnowledgeDocumentStorageDTO) -> KnowledgeDocument:
        ...


class KnowledgeChunkMapper(Protocol):
    def domain_to_dto(self, chunk: KnowledgeChunk) -> KnowledgeChunkStorageDTO:
        ...

    def dto_to_domain(self, dto: KnowledgeChunkStorageDTO) -> KnowledgeChunk:
        ...


class IngestionJobMapper(Protocol):
    def domain_to_dto(self, job: IngestionJob) -> IngestionJobStorageDTO:
        ...

    def dto_to_domain(self, dto: IngestionJobStorageDTO) -> IngestionJob:
        ...


class KnowledgeOutboxMapper(Protocol):
    def event_to_dto(self, event: KnowledgeOutboxDomainEvent) -> KnowledgeOutboxStorageDTO:
        ...

    def dto_to_event(self, dto: KnowledgeOutboxStorageDTO) -> KnowledgeOutboxDomainEvent:
        ...
