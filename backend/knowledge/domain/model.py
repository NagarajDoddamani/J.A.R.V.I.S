from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import auto, StrEnum
from typing import Any
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================


class SourceType(StrEnum):
    FILE = auto()
    DIRECTORY = auto()
    URL = auto()
    MANUAL = auto()
    MEMORY_EXPORT = auto()


class SourceStatus(StrEnum):
    REGISTERED = auto()
    ACTIVE = auto()
    DISABLED = auto()
    DELETED = auto()


class DocumentStatus(StrEnum):
    PENDING = auto()
    INGESTED = auto()
    INDEXED = auto()
    DELETED = auto()


class IngestionStatus(StrEnum):
    QUEUED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()


# =============================================================================
# Value Objects
# =============================================================================


@dataclass(frozen=True)
class KnowledgeSourceId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class DocumentId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class ChunkId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class IngestionJobId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class SourceLocation:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"SourceLocation value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.knowledge.domain.exceptions import EmptyLocationError

            raise EmptyLocationError()

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class DocumentChecksum:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"DocumentChecksum value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.knowledge.domain.exceptions import EmptyChecksumError

            raise EmptyChecksumError()

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ChunkIndex:
    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int):
            msg = f"ChunkIndex value must be an int, got {type(self.value).__name__}"
            raise TypeError(msg)
        if self.value < 0:
            from backend.knowledge.domain.exceptions import NegativeChunkIndexError

            raise NegativeChunkIndexError(self.value)

    def __int__(self) -> int:
        return self.value


@dataclass(frozen=True)
class ChunkContent:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"ChunkContent value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.knowledge.domain.exceptions import EmptyChunkContentError

            raise EmptyChunkContentError()

    def __len__(self) -> int:
        return len(self.value)


# =============================================================================
# Domain Events
# =============================================================================


@dataclass(frozen=True)
class KnowledgeSourceRegistered:
    source_id: KnowledgeSourceId
    name: str
    source_type: SourceType
    location: SourceLocation
    classification: str
    occurred_at: datetime


@dataclass(frozen=True)
class KnowledgeSourceDeleted:
    source_id: KnowledgeSourceId
    occurred_at: datetime


@dataclass(frozen=True)
class DocumentIngested:
    document_id: DocumentId
    source_id: KnowledgeSourceId
    title: str
    checksum: DocumentChecksum
    classification: str
    occurred_at: datetime


@dataclass(frozen=True)
class DocumentIndexed:
    document_id: DocumentId
    occurred_at: datetime


@dataclass(frozen=True)
class DocumentDeleted:
    document_id: DocumentId
    occurred_at: datetime


@dataclass(frozen=True)
class ChunkCreated:
    chunk_id: ChunkId
    document_id: DocumentId
    chunk_index: ChunkIndex
    occurred_at: datetime


@dataclass(frozen=True)
class ReindexRequested:
    source_id: KnowledgeSourceId
    occurred_at: datetime


@dataclass(frozen=True)
class IngestionStarted:
    job_id: IngestionJobId
    source_id: KnowledgeSourceId
    occurred_at: datetime


@dataclass(frozen=True)
class IngestionCompleted:
    job_id: IngestionJobId
    occurred_at: datetime


@dataclass(frozen=True)
class IngestionFailed:
    job_id: IngestionJobId
    error_message: str
    occurred_at: datetime


# =============================================================================
# Entities
# =============================================================================


class KnowledgeSource:
    """Aggregate root for the knowledge domain — a source of documents."""

    def __init__(
        self,
        source_id: KnowledgeSourceId | None = None,
        name: str = "",
        source_type: SourceType = SourceType.FILE,
        location: SourceLocation | None = None,
        classification: str = "public",
        status: SourceStatus = SourceStatus.REGISTERED,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        deleted_at: datetime | None = None,
    ) -> None:
        self._source_id = source_id or KnowledgeSourceId()
        self._name = name
        self._source_type = source_type
        self._location = location
        self._classification = classification
        self._status = status
        self._created_at = created_at or datetime.now(tz=timezone.utc)
        self._updated_at = updated_at
        self._deleted_at = deleted_at
        self._events: list[KnowledgeSourceDeleted] = []

    # -- properties ---------------------------------------------------------

    @property
    def source_id(self) -> KnowledgeSourceId:
        return self._source_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def source_type(self) -> SourceType:
        return self._source_type

    @property
    def location(self) -> SourceLocation | None:
        return self._location

    @property
    def classification(self) -> str:
        return self._classification

    @property
    def status(self) -> SourceStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @property
    def deleted_at(self) -> datetime | None:
        return self._deleted_at

    @property
    def events(self) -> list[KnowledgeSourceDeleted]:
        return list(self._events)

    @property
    def is_active(self) -> bool:
        return self._status == SourceStatus.ACTIVE

    @property
    def is_deleted(self) -> bool:
        return self._status == SourceStatus.DELETED

    # -- commands -----------------------------------------------------------

    def activate(self) -> None:
        from backend.knowledge.domain.rules import (
            assert_source_can_transition,
            assert_source_not_deleted,
        )

        assert_source_not_deleted(self)
        assert_source_can_transition(self._status, SourceStatus.ACTIVE)
        self._status = SourceStatus.ACTIVE
        self._updated_at = datetime.now(tz=timezone.utc)

    def disable(self) -> None:
        from backend.knowledge.domain.rules import (
            assert_source_can_transition,
            assert_source_not_deleted,
        )

        assert_source_not_deleted(self)
        assert_source_can_transition(self._status, SourceStatus.DISABLED)
        self._status = SourceStatus.DISABLED
        self._updated_at = datetime.now(tz=timezone.utc)

    def delete(self) -> None:
        from backend.knowledge.domain.rules import assert_source_can_transition

        assert_source_can_transition(self._status, SourceStatus.DELETED)
        now = datetime.now(tz=timezone.utc)
        self._status = SourceStatus.DELETED
        self._deleted_at = now
        self._updated_at = now
        self._events.append(
            KnowledgeSourceDeleted(source_id=self._source_id, occurred_at=now)
        )

    # -- internal -----------------------------------------------------------

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"KnowledgeSource(id={self._source_id}, "
            f"name={self._name!r}, "
            f"status={self._status.value})"
        )


class KnowledgeDocument:
    """Represents a knowledge document ingested from a source."""

    def __init__(
        self,
        document_id: DocumentId | None = None,
        source_id: KnowledgeSourceId | None = None,
        title: str = "",
        checksum: DocumentChecksum | None = None,
        classification: str = "public",
        status: DocumentStatus = DocumentStatus.PENDING,
        revision: int = 1,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        deleted_at: datetime | None = None,
    ) -> None:
        self._document_id = document_id or DocumentId()
        self._source_id = source_id
        self._title = title
        self._checksum = checksum
        self._classification = classification
        self._status = status
        self._revision = revision
        self._created_at = created_at or datetime.now(tz=timezone.utc)
        self._updated_at = updated_at
        self._deleted_at = deleted_at
        self._events: list[DocumentIndexed | DocumentDeleted] = []

    # -- properties ---------------------------------------------------------

    @property
    def document_id(self) -> DocumentId:
        return self._document_id

    @property
    def source_id(self) -> KnowledgeSourceId | None:
        return self._source_id

    @property
    def title(self) -> str:
        return self._title

    @property
    def checksum(self) -> DocumentChecksum | None:
        return self._checksum

    @property
    def classification(self) -> str:
        return self._classification

    @property
    def status(self) -> DocumentStatus:
        return self._status

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @property
    def deleted_at(self) -> datetime | None:
        return self._deleted_at

    @property
    def events(self) -> list[DocumentIndexed | DocumentDeleted]:
        return list(self._events)

    @property
    def is_deleted(self) -> bool:
        return self._status == DocumentStatus.DELETED

    # -- commands -----------------------------------------------------------

    def mark_indexed(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.knowledge.domain.rules import assert_document_can_transition

        assert_document_can_transition(self._status, DocumentStatus.INDEXED)
        self._status = DocumentStatus.INDEXED
        self._updated_at = now
        self._events.append(
            DocumentIndexed(document_id=self._document_id, occurred_at=now)
        )

    def delete(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.knowledge.domain.rules import assert_document_can_transition

        assert_document_can_transition(self._status, DocumentStatus.DELETED)
        self._status = DocumentStatus.DELETED
        self._deleted_at = now
        self._updated_at = now
        self._events.append(
            DocumentDeleted(document_id=self._document_id, occurred_at=now)
        )

    # -- internal -----------------------------------------------------------

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"KnowledgeDocument(id={self._document_id}, "
            f"title={self._title!r}, "
            f"status={self._status.value})"
        )


class KnowledgeChunk:
    """A single chunk of content within a knowledge document."""

    def __init__(
        self,
        chunk_id: ChunkId | None = None,
        document_id: DocumentId | None = None,
        chunk_index: ChunkIndex | None = None,
        content: ChunkContent | None = None,
        classification: str = "public",
        created_at: datetime | None = None,
    ) -> None:
        self._chunk_id = chunk_id or ChunkId()
        self._document_id = document_id
        self._chunk_index = chunk_index
        self._content = content
        self._classification = classification
        self._created_at = created_at or datetime.now(tz=timezone.utc)

    # -- properties ---------------------------------------------------------

    @property
    def chunk_id(self) -> ChunkId:
        return self._chunk_id

    @property
    def document_id(self) -> DocumentId | None:
        return self._document_id

    @property
    def chunk_index(self) -> ChunkIndex | None:
        return self._chunk_index

    @property
    def content(self) -> ChunkContent | None:
        return self._content

    @property
    def classification(self) -> str:
        return self._classification

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def __repr__(self) -> str:
        return (
            f"KnowledgeChunk(id={self._chunk_id}, "
            f"document={self._document_id}, "
            f"index={self._chunk_index})"
        )


class IngestionJob:
    """Tracks the ingestion lifecycle for a knowledge source."""

    def __init__(
        self,
        job_id: IngestionJobId | None = None,
        source_id: KnowledgeSourceId | None = None,
        status: IngestionStatus = IngestionStatus.RUNNING,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error_message: str | None = None,
    ) -> None:
        self._job_id = job_id or IngestionJobId()
        self._source_id = source_id
        self._status = status
        self._started_at = started_at or datetime.now(tz=timezone.utc)
        self._completed_at = completed_at
        self._error_message = error_message
        self._events: list[IngestionCompleted | IngestionFailed] = []

    # -- properties ---------------------------------------------------------

    @property
    def job_id(self) -> IngestionJobId:
        return self._job_id

    @property
    def source_id(self) -> KnowledgeSourceId | None:
        return self._source_id

    @property
    def status(self) -> IngestionStatus:
        return self._status

    @property
    def started_at(self) -> datetime:
        return self._started_at

    @property
    def completed_at(self) -> datetime | None:
        return self._completed_at

    @property
    def error_message(self) -> str | None:
        return self._error_message

    @property
    def events(self) -> list[IngestionCompleted | IngestionFailed]:
        return list(self._events)

    # -- commands -----------------------------------------------------------

    def complete(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.knowledge.domain.rules import assert_ingestion_can_transition

        assert_ingestion_can_transition(self._status, IngestionStatus.COMPLETED)
        self._status = IngestionStatus.COMPLETED
        self._completed_at = now
        self._events.append(
            IngestionCompleted(job_id=self._job_id, occurred_at=now)
        )

    def fail(self, error_message: str) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.knowledge.domain.rules import (
            assert_ingestion_can_transition,
            assert_failure_has_message,
        )

        assert_failure_has_message(error_message)
        assert_ingestion_can_transition(self._status, IngestionStatus.FAILED)
        self._status = IngestionStatus.FAILED
        self._error_message = error_message
        self._completed_at = now
        self._events.append(
            IngestionFailed(
                job_id=self._job_id,
                error_message=error_message,
                occurred_at=now,
            )
        )

    # -- internal -----------------------------------------------------------

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"IngestionJob(id={self._job_id}, "
            f"status={self._status.value})"
        )
