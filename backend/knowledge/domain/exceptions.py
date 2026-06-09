from __future__ import annotations


class KnowledgeDomainError(Exception):
    """Base exception for all knowledge domain errors."""


class EmptySourceNameError(KnowledgeDomainError):
    def __init__(self) -> None:
        super().__init__("Source name must not be empty")


class EmptyDocumentTitleError(KnowledgeDomainError):
    def __init__(self) -> None:
        super().__init__("Document title must not be empty")


class EmptyChunkContentError(KnowledgeDomainError):
    def __init__(self) -> None:
        super().__init__("Chunk content must not be empty")


class ChunkContentTooLongError(KnowledgeDomainError):
    def __init__(self, length: int, max_length: int) -> None:
        super().__init__(
            f"Chunk content length {length} exceeds maximum {max_length}"
        )
        self.length = length
        self.max_length = max_length


class EmptyChecksumError(KnowledgeDomainError):
    def __init__(self) -> None:
        super().__init__("Document checksum must not be empty")


class EmptyLocationError(KnowledgeDomainError):
    def __init__(self) -> None:
        super().__init__("Source location must not be empty")


class InvalidClassificationError(KnowledgeDomainError):
    def __init__(self, classification: str) -> None:
        super().__init__(f"Invalid classification: {classification!r}")
        self.classification = classification


class InvalidSourceTypeError(KnowledgeDomainError):
    def __init__(self, source_type: str) -> None:
        super().__init__(f"Invalid source type: {source_type!r}")
        self.source_type = source_type


class InvalidSourceTransitionError(KnowledgeDomainError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            f"Invalid source transition from {current!r} to {target!r}"
        )
        self.current = current
        self.target = target


class InvalidDocumentTransitionError(KnowledgeDomainError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            f"Invalid document transition from {current!r} to {target!r}"
        )
        self.current = current
        self.target = target


class InvalidIngestionTransitionError(KnowledgeDomainError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            f"Invalid ingestion transition from {current!r} to {target!r}"
        )
        self.current = current
        self.target = target


class DeletedSourceReactivationError(KnowledgeDomainError):
    def __init__(self) -> None:
        super().__init__("Deleted source cannot be reactivated")


class SourceNotActiveError(KnowledgeDomainError):
    def __init__(self, status: str) -> None:
        super().__init__(f"Source must be ACTIVE, got {status!r}")
        self.status = status


class DeletedSourceBlocksIngestionError(KnowledgeDomainError):
    def __init__(self) -> None:
        super().__init__("Deleted source blocks new document ingestion")


class DeletedDocumentBlocksChunkError(KnowledgeDomainError):
    def __init__(self) -> None:
        super().__init__("Deleted document blocks chunk creation")


class DeletedDocumentModificationError(KnowledgeDomainError):
    def __init__(self) -> None:
        super().__init__("Deleted document cannot be modified")


class RevisionMonotonicityError(KnowledgeDomainError):
    def __init__(self, current: int, expected: int) -> None:
        super().__init__(
            f"Revision {current} does not follow expected {expected}"
        )
        self.current = current
        self.expected = expected


class NegativeChunkIndexError(KnowledgeDomainError):
    def __init__(self, index: int) -> None:
        super().__init__(f"Chunk index must be non-negative, got {index}")
        self.index = index


class NonMonotonicChunkIndexError(KnowledgeDomainError):
    def __init__(self, index: int, last_index: int) -> None:
        super().__init__(
            f"Chunk index {index} must be greater than last index {last_index}"
        )
        self.index = index
        self.last_index = last_index


class SourceRequiredForDocumentError(KnowledgeDomainError):
    def __init__(self) -> None:
        super().__init__("Document must belong to an existing source")


class DocumentRequiredForChunkError(KnowledgeDomainError):
    def __init__(self) -> None:
        super().__init__("Chunk must belong to an existing document")


class ReindexRequiresActiveSourceError(KnowledgeDomainError):
    def __init__(self, status: str) -> None:
        super().__init__(f"Reindex only allowed for ACTIVE source, got {status!r}")
        self.status = status


class IngestionErrorMessageRequiredError(KnowledgeDomainError):
    def __init__(self) -> None:
        super().__init__("Ingestion failure requires non-empty error_message")


class CompletedIngestionRollbackError(KnowledgeDomainError):
    def __init__(self) -> None:
        super().__init__("Completed ingestion cannot transition back to RUNNING")


class FailedIngestionCompletionError(KnowledgeDomainError):
    def __init__(self) -> None:
        super().__init__("Failed ingestion cannot become COMPLETED without a new job")
