from __future__ import annotations


class UseCaseError(Exception):
    """Base exception for all use-case-level errors."""


class SourceNotFoundError(UseCaseError):
    def __init__(self, source_id: str) -> None:
        super().__init__(f"Knowledge source not found: {source_id}")
        self.source_id = source_id


class DocumentNotFoundError(UseCaseError):
    def __init__(self, document_id: str) -> None:
        super().__init__(f"Knowledge document not found: {document_id}")
        self.document_id = document_id


class ChunkNotFoundError(UseCaseError):
    def __init__(self, chunk_id: str) -> None:
        super().__init__(f"Knowledge chunk not found: {chunk_id}")
        self.chunk_id = chunk_id


class IngestionJobNotFoundError(UseCaseError):
    def __init__(self, job_id: str) -> None:
        super().__init__(f"Ingestion job not found: {job_id}")
        self.job_id = job_id


class SourceInactiveError(UseCaseError):
    def __init__(self, source_id: str) -> None:
        super().__init__(f"Knowledge source is not active: {source_id}")
        self.source_id = source_id


class DocumentDeletedError(UseCaseError):
    def __init__(self, document_id: str) -> None:
        super().__init__(f"Knowledge document is deleted: {document_id}")
        self.document_id = document_id


class InvalidIngestionTransitionError(UseCaseError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            f"Invalid ingestion transition from '{current}' to '{target}'"
        )
        self.current = current
        self.target = target
