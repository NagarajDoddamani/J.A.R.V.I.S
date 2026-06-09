from __future__ import annotations

from typing import Protocol

from backend.knowledge.domain.model import (
    ChunkId,
    DocumentId,
    IngestionJobId,
    KnowledgeSourceId,
)


class KnowledgeIdGeneratorPort(Protocol):
    """Identifier generator for the knowledge domain.

    Produces unique identifiers for all knowledge domain aggregates.
    Swappable implementations allow UUID-based generation in
    production or deterministic sequences in tests.
    """

    def generate_source_id(self) -> KnowledgeSourceId:
        """Generate a unique knowledge source identifier.

        The returned ``KnowledgeSourceId`` MUST be globally unique
        and suitable for use as an aggregate identifier.

        Returns
        -------
        A unique ``KnowledgeSourceId`` value.
        """
        ...

    def generate_document_id(self) -> DocumentId:
        """Generate a unique document identifier.

        The returned ``DocumentId`` MUST be globally unique and
        suitable for use as an aggregate identifier.

        Returns
        -------
        A unique ``DocumentId`` value.
        """
        ...

    def generate_chunk_id(self) -> ChunkId:
        """Generate a unique chunk identifier.

        The returned ``ChunkId`` MUST be globally unique and
        suitable for use as an aggregate identifier.

        Returns
        -------
        A unique ``ChunkId`` value.
        """
        ...

    def generate_job_id(self) -> IngestionJobId:
        """Generate a unique ingestion job identifier.

        The returned ``IngestionJobId`` MUST be globally unique and
        suitable for use as an aggregate identifier.

        Returns
        -------
        A unique ``IngestionJobId`` value.
        """
        ...
