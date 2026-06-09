from __future__ import annotations

from typing import Protocol

from backend.knowledge.domain.model import (
    DocumentChecksum,
    DocumentId,
    DocumentStatus,
    IngestionJob,
    IngestionJobId,
    IngestionStatus,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSourceId,
    SourceStatus,
    SourceType,
)


class KnowledgeSourceRepositoryPort(Protocol):
    """Repository port for ``KnowledgeSource`` aggregate persistence.

    An implementation persists ``KnowledgeSource`` aggregates to a
    concrete store. Soft-deleted sources remain queryable.
    All methods are synchronous.
    """

    def save(self, source: KnowledgeSource) -> None:
        """Persist a new or updated source.

        Uses upsert semantics — if a source with the same
        ``source_id`` already exists it is replaced; otherwise
        a new record is created.

        Parameters
        ----------
        source:
            The ``KnowledgeSource`` aggregate to persist.
        """
        ...

    def find_by_id(self, source_id: KnowledgeSourceId) -> KnowledgeSource | None:
        """Retrieve a source by its unique identifier.

        Parameters
        ----------
        source_id:
            The ``KnowledgeSourceId`` to look up.

        Returns
        -------
        The matching source, or ``None`` if no source exists
        with the given identifier.
        """
        ...

    def find_by_status(self, status: SourceStatus) -> list[KnowledgeSource]:
        """Retrieve all sources with a given status.

        Parameters
        ----------
        status:
            The ``SourceStatus`` to filter by.

        Returns
        -------
        A list of ``KnowledgeSource`` instances with the given status.
        """
        ...

    def find_by_type(self, source_type: SourceType) -> list[KnowledgeSource]:
        """Retrieve all sources of a given type.

        Parameters
        ----------
        source_type:
            The ``SourceType`` to filter by.

        Returns
        -------
        A list of ``KnowledgeSource`` instances of the given type.
        """
        ...

    def count(self) -> int:
        """Return the total number of sources.

        This count includes all statuses (REGISTERED, ACTIVE,
        DISABLED, DELETED).

        Returns
        -------
        Total source count (0 if the store is empty).
        """
        ...


class KnowledgeDocumentRepositoryPort(Protocol):
    """Repository port for ``KnowledgeDocument`` persistence.

    An implementation persists ``KnowledgeDocument`` aggregates.
    Soft-deleted documents remain queryable via ``find_deleted``.
    """

    def save(self, document: KnowledgeDocument) -> None:
        """Persist a new or updated document.

        Uses upsert semantics.

        Parameters
        ----------
        document:
            The ``KnowledgeDocument`` aggregate to persist.
        """
        ...

    def find_by_id(self, document_id: DocumentId) -> KnowledgeDocument | None:
        """Retrieve a document by its unique identifier.

        Parameters
        ----------
        document_id:
            The ``DocumentId`` to look up.

        Returns
        -------
        The matching document, or ``None`` if no document exists
        with the given identifier.
        """
        ...

    def find_by_source_id(
        self, source_id: KnowledgeSourceId
    ) -> list[KnowledgeDocument]:
        """Retrieve all documents belonging to a source.

        Parameters
        ----------
        source_id:
            The ``KnowledgeSourceId`` to search for.

        Returns
        -------
        A list of ``KnowledgeDocument`` instances for the given source.
        """
        ...

    def find_by_checksum(
        self, checksum: DocumentChecksum
    ) -> list[KnowledgeDocument]:
        """Retrieve documents with an exact checksum match.

        Parameters
        ----------
        checksum:
            The ``DocumentChecksum`` to match.

        Returns
        -------
        A list of ``KnowledgeDocument`` instances with the given checksum.
        """
        ...

    def find_deleted(self) -> list[KnowledgeDocument]:
        """Retrieve all soft-deleted documents.

        Deleted documents are not physically removed from the store
        and remain queryable through this method.

        Returns
        -------
        A list of ``KnowledgeDocument`` instances in the ``DELETED`` state.
        """
        ...

    def count(self) -> int:
        """Return the total number of documents.

        Returns
        -------
        Total document count (0 if the store is empty).
        """
        ...


class KnowledgeChunkRepositoryPort(Protocol):
    """Repository port for ``KnowledgeChunk`` persistence.

    An implementation persists ``KnowledgeChunk`` value aggregates.
    Chunks are ordered by ``chunk_index`` within a document.
    """

    def save(self, chunk: KnowledgeChunk) -> None:
        """Persist a new chunk.

        Uses upsert semantics.

        Parameters
        ----------
        chunk:
            The ``KnowledgeChunk`` to persist.
        """
        ...

    def find_by_id(self, chunk_id: ChunkId) -> KnowledgeChunk | None:
        """Retrieve a chunk by its unique identifier.

        Parameters
        ----------
        chunk_id:
            The ``ChunkId`` to look up.

        Returns
        -------
        The matching chunk, or ``None`` if no chunk exists
        with the given identifier.
        """
        ...

    def find_by_document_id(
        self, document_id: DocumentId
    ) -> list[KnowledgeChunk]:
        """Retrieve all chunks for a document, ordered by index.

        Parameters
        ----------
        document_id:
            The ``DocumentId`` to search for.

        Returns
        -------
        A list of ``KnowledgeChunk`` instances ordered by
        ``chunk_index``.
        """
        ...

    def find_by_index_range(
        self, document_id: DocumentId, start_index: int, end_index: int
    ) -> list[KnowledgeChunk]:
        """Retrieve chunks within an inclusive index range.

        Parameters
        ----------
        document_id:
            The ``DocumentId`` to search within.
        start_index:
            The minimum ``chunk_index`` value (inclusive).
        end_index:
            The maximum ``chunk_index`` value (inclusive).

        Returns
        -------
        A list of ``KnowledgeChunk`` instances with indices
        between ``start_index`` and ``end_index`` inclusive.
        """
        ...

    def count(self) -> int:
        """Return the total number of chunks.

        Returns
        -------
        Total chunk count (0 if the store is empty).
        """
        ...


class IngestionJobRepositoryPort(Protocol):
    """Repository port for ``IngestionJob`` persistence.

    An implementation persists ``IngestionJob`` aggregates to a
    concrete store. Jobs are queryable by source and status.
    """

    def save(self, job: IngestionJob) -> None:
        """Persist a new or updated ingestion job.

        Uses upsert semantics.

        Parameters
        ----------
        job:
            The ``IngestionJob`` aggregate to persist.
        """
        ...

    def find_by_id(self, job_id: IngestionJobId) -> IngestionJob | None:
        """Retrieve a job by its unique identifier.

        Parameters
        ----------
        job_id:
            The ``IngestionJobId`` to look up.

        Returns
        -------
        The matching job, or ``None`` if no job exists
        with the given identifier.
        """
        ...

    def find_by_source_id(
        self, source_id: KnowledgeSourceId
    ) -> list[IngestionJob]:
        """Retrieve all jobs associated with a source.

        Parameters
        ----------
        source_id:
            The ``KnowledgeSourceId`` to search for.

        Returns
        -------
        A list of ``IngestionJob`` instances for the given source.
        """
        ...

    def find_by_status(
        self, status: IngestionStatus
    ) -> list[IngestionJob]:
        """Retrieve all jobs with a given status.

        Parameters
        ----------
        status:
            The ``IngestionStatus`` to filter by.

        Returns
        -------
        A list of ``IngestionJob`` instances with the given status.
        """
        ...

    def count(self) -> int:
        """Return the total number of ingestion jobs.

        Returns
        -------
        Total job count (0 if the store is empty).
        """
        ...
