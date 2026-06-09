from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class KnowledgeSourceStorageDTO:
    source_id: str
    name: str
    source_type: str
    location: str | None = None
    classification: str = "public"
    status: str = "registered"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


@dataclass(frozen=True)
class KnowledgeDocumentStorageDTO:
    document_id: str
    source_id: str | None = None
    title: str = ""
    checksum: str | None = None
    classification: str = "public"
    status: str = "pending"
    revision: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


@dataclass(frozen=True)
class KnowledgeChunkStorageDTO:
    chunk_id: str
    document_id: str | None = None
    chunk_index: int | None = None
    content: str | None = None
    classification: str = "public"
    created_at: datetime | None = None


@dataclass(frozen=True)
class IngestionJobStorageDTO:
    job_id: str
    source_id: str | None = None
    status: str = "running"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class KnowledgeOutboxStorageDTO:
    event_id: str
    event_type: str
    aggregate_id: str
    occurred_at: datetime
    correlation_id: str | None = None
    causation_id: str | None = None
    payload: str | None = None
    published: bool = False
