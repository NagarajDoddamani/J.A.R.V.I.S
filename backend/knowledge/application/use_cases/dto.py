from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SourceResponse:
    source_id: str
    name: str
    source_type: str
    location: str | None
    classification: str
    status: str
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None


@dataclass
class DocumentResponse:
    document_id: str
    source_id: str | None
    title: str
    checksum: str | None
    classification: str
    status: str
    revision: int
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None


@dataclass
class ChunkResponse:
    chunk_id: str
    document_id: str | None
    chunk_index: int | None
    content: str | None
    classification: str
    created_at: datetime | None


@dataclass
class IngestionJobResponse:
    job_id: str
    source_id: str | None
    status: str
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None


@dataclass
class RegisterSourceRequest:
    name: str
    source_type: str
    location: str
    classification: str = "public"


@dataclass
class RegisterSourceResponse:
    source_id: str
    name: str
    source_type: str
    location: str | None
    classification: str
    status: str
    created_at: datetime


@dataclass
class DeleteSourceRequest:
    source_id: str


@dataclass
class DeleteSourceResponse:
    source_id: str
    deleted_at: datetime


@dataclass
class GetSourceRequest:
    source_id: str


@dataclass
class ListSourcesRequest:
    status: str | None = None
    source_type: str | None = None


@dataclass
class ListSourcesResponse:
    sources: list[SourceResponse] = field(default_factory=list)


@dataclass
class IngestDocumentRequest:
    source_id: str
    title: str
    checksum: str
    classification: str = "public"


@dataclass
class IngestDocumentResponse:
    document_id: str
    source_id: str | None
    title: str
    checksum: str | None
    classification: str
    status: str
    revision: int
    created_at: datetime


@dataclass
class GetDocumentRequest:
    document_id: str


@dataclass
class CreateChunkRequest:
    document_id: str
    chunk_index: int
    content: str
    classification: str = "public"


@dataclass
class CreateChunkResponse:
    chunk_id: str
    document_id: str | None
    chunk_index: int | None
    content: str | None
    classification: str
    created_at: datetime


@dataclass
class GetChunksByDocumentRequest:
    document_id: str


@dataclass
class GetChunksByDocumentResponse:
    chunks: list[ChunkResponse] = field(default_factory=list)


@dataclass
class StartIngestionRequest:
    source_id: str


@dataclass
class StartIngestionResponse:
    job_id: str
    source_id: str | None
    status: str
    started_at: datetime


@dataclass
class CompleteIngestionRequest:
    job_id: str


@dataclass
class CompleteIngestionResponse:
    job_id: str
    status: str
    completed_at: datetime


@dataclass
class FailIngestionRequest:
    job_id: str
    error_message: str


@dataclass
class FailIngestionResponse:
    job_id: str
    status: str
    completed_at: datetime
    error_message: str


@dataclass
class GetIngestionJobRequest:
    job_id: str


@dataclass
class RequestReindexRequest:
    source_id: str


@dataclass
class ReindexResponse:
    source_id: str
    event_type: str = "knowledge.reindex.requested"
