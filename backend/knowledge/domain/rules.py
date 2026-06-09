from __future__ import annotations

from backend.knowledge.domain.exceptions import (
    ChunkContentTooLongError,
    CompletedIngestionRollbackError,
    DeletedDocumentBlocksChunkError,
    DeletedDocumentModificationError,
    DeletedSourceBlocksIngestionError,
    DeletedSourceReactivationError,
    EmptyChecksumError,
    EmptyChunkContentError,
    EmptyDocumentTitleError,
    EmptyLocationError,
    EmptySourceNameError,
    FailedIngestionCompletionError,
    IngestionErrorMessageRequiredError,
    InvalidClassificationError,
    InvalidIngestionTransitionError,
    InvalidSourceTransitionError,
    InvalidSourceTypeError,
    NegativeChunkIndexError,
    NonMonotonicChunkIndexError,
    ReindexRequiresActiveSourceError,
    SourceNotActiveError,
    SourceRequiredForDocumentError,
    DocumentRequiredForChunkError,
)
from backend.knowledge.domain.model import (
    ChunkContent,
    ChunkIndex,
    DocumentChecksum,
    DocumentStatus,
    IngestionStatus,
    KnowledgeDocument,
    KnowledgeSource,
    SourceLocation,
    SourceStatus,
    SourceType,
)

# GLOBAL CONFIGURATION
MAX_CHUNK_CONTENT_LENGTH: int = 10000

VALID_CLASSIFICATIONS: frozenset[str] = frozenset(
    {"public", "internal", "sensitive", "restricted"}
)

VALID_SOURCE_TRANSITIONS: dict[SourceStatus, set[SourceStatus]] = {
    SourceStatus.REGISTERED: {SourceStatus.ACTIVE, SourceStatus.DELETED},
    SourceStatus.ACTIVE: {SourceStatus.DISABLED, SourceStatus.DELETED},
    SourceStatus.DISABLED: {SourceStatus.ACTIVE, SourceStatus.DELETED},
    SourceStatus.DELETED: set(),
}

VALID_DOCUMENT_TRANSITIONS: dict[DocumentStatus, set[DocumentStatus]] = {
    DocumentStatus.PENDING: {DocumentStatus.INGESTED, DocumentStatus.INDEXED, DocumentStatus.DELETED},
    DocumentStatus.INGESTED: {DocumentStatus.INDEXED, DocumentStatus.DELETED},
    DocumentStatus.INDEXED: {DocumentStatus.DELETED},
    DocumentStatus.DELETED: set(),
}

VALID_INGESTION_TRANSITIONS: dict[IngestionStatus, set[IngestionStatus]] = {
    IngestionStatus.QUEUED: {IngestionStatus.RUNNING},
    IngestionStatus.RUNNING: {IngestionStatus.COMPLETED, IngestionStatus.FAILED},
    IngestionStatus.COMPLETED: set(),
    IngestionStatus.FAILED: set(),
}


# -- Rule 1: Source name cannot be empty ------------------------------------

def assert_source_name_not_empty(name: str) -> None:
    if not name or not name.strip():
        raise EmptySourceNameError()


# -- Rule 2: Source location required ---------------------------------------

def assert_location_provided(location: SourceLocation | None) -> None:
    if location is None:
        raise EmptyLocationError()


# -- Rule 3: Source type must be valid --------------------------------------

def assert_source_type_valid(source_type: str | SourceType) -> None:
    if isinstance(source_type, SourceType):
        return
    try:
        SourceType(source_type)
    except ValueError:
        raise InvalidSourceTypeError(source_type)


# -- Rule 4: Classification must match governance values --------------------

def assert_classification_valid(classification: str) -> None:
    if classification not in VALID_CLASSIFICATIONS:
        raise InvalidClassificationError(classification)


# -- Rule 5: Deleted source cannot be reactivated ---------------------------

def assert_source_not_deleted(source: KnowledgeSource) -> None:
    if source.is_deleted:
        raise DeletedSourceReactivationError()


# -- Rule 6: Source must be ACTIVE before ingestion -------------------------

def assert_source_active(source: KnowledgeSource) -> None:
    if not source.is_active:
        raise SourceNotActiveError(source.status.value)


# -- Rule 7: Document title cannot be empty ---------------------------------

def assert_document_title_not_empty(title: str) -> None:
    if not title or not title.strip():
        raise EmptyDocumentTitleError()


# -- Rule 8: Document checksum required -------------------------------------

def assert_checksum_provided(checksum: DocumentChecksum | None) -> None:
    if checksum is None:
        raise EmptyChecksumError()


# -- Rule 9: Revision numbers must increase monotonically -------------------

def assert_revision_monotonic(current: int, expected: int) -> None:
    if current != expected:
        from backend.knowledge.domain.exceptions import RevisionMonotonicityError

        raise RevisionMonotonicityError(current, expected)


# -- Rule 10: Deleted document cannot be modified ---------------------------

def assert_document_not_deleted(document: KnowledgeDocument) -> None:
    if document.is_deleted:
        raise DeletedDocumentModificationError()


# -- Rule 11: Chunk content cannot be empty ---------------------------------

def assert_chunk_content_not_empty(content: ChunkContent) -> None:
    if not content.value.strip():
        raise EmptyChunkContentError()


# -- Rule 12: Chunk content cannot exceed configured maximum ----------------

def assert_chunk_content_max_length(
    content: ChunkContent, max_length: int = MAX_CHUNK_CONTENT_LENGTH
) -> None:
    if len(content) > max_length:
        raise ChunkContentTooLongError(len(content), max_length)


# -- Rule 13: Chunk index must be non-negative (enforced by ChunkIndex VO) --

# -- Rule 14: Chunk indices must be monotonically increasing within a doc ---

def assert_chunk_index_monotonic(
    new_index: ChunkIndex, existing_indices: list[ChunkIndex]
) -> None:
    if existing_indices:
        last = max(existing_indices, key=lambda ci: int(ci))
        if int(new_index) <= int(last):
            raise NonMonotonicChunkIndexError(int(new_index), int(last))


# -- Rule 15: Document must belong to an existing source --------------------

def assert_source_provided_for_document(source: KnowledgeSource | None) -> None:
    if source is None:
        raise SourceRequiredForDocumentError()


# -- Rule 16: Chunk must belong to an existing document ---------------------

def assert_document_provided_for_chunk(document: KnowledgeDocument | None) -> None:
    if document is None:
        raise DocumentRequiredForChunkError()


# -- Rule 17: Reindex only allowed for ACTIVE source ------------------------

def assert_reindex_allowed(source: KnowledgeSource) -> None:
    if not source.is_active:
        raise ReindexRequiresActiveSourceError(source.status.value)


# -- Rule 18: Ingestion failure requires non-empty error_message ------------

def assert_failure_has_message(error_message: str) -> None:
    if not error_message or not error_message.strip():
        raise IngestionErrorMessageRequiredError()


# -- Rule 19: Completed ingestion cannot transition back to RUNNING ---------

# -- Rule 20: Failed ingestion cannot become COMPLETED without new job ------

# Both rules 19 and 20 are enforced by VALID_INGESTION_TRANSITIONS


def assert_ingestion_can_transition(
    current: IngestionStatus, target: IngestionStatus
) -> None:
    allowed = VALID_INGESTION_TRANSITIONS.get(current, set())
    if target not in allowed:
        if current == IngestionStatus.COMPLETED and target == IngestionStatus.RUNNING:
            raise CompletedIngestionRollbackError()
        if current == IngestionStatus.FAILED and target == IngestionStatus.COMPLETED:
            raise FailedIngestionCompletionError()
        raise InvalidIngestionTransitionError(current.value, target.value)


# -- Rule 21: Deleted source blocks new document ingestion ------------------

def assert_source_allows_ingestion(source: KnowledgeSource) -> None:
    if source.is_deleted:
        raise DeletedSourceBlocksIngestionError()


# -- Rule 22: Deleted document blocks chunk creation ------------------------

def assert_document_allows_chunk_creation(document: KnowledgeDocument) -> None:
    if document.is_deleted:
        raise DeletedDocumentBlocksChunkError()


# -- Source transitions -----------------------------------------------------

def assert_source_can_transition(
    current: SourceStatus, target: SourceStatus
) -> None:
    allowed = VALID_SOURCE_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidSourceTransitionError(current.value, target.value)


# -- Document transitions ---------------------------------------------------

def assert_document_can_transition(
    current: DocumentStatus, target: DocumentStatus
) -> None:
    allowed = VALID_DOCUMENT_TRANSITIONS.get(current, set())
    if target not in allowed:
        from backend.knowledge.domain.exceptions import InvalidDocumentTransitionError

        raise InvalidDocumentTransitionError(current.value, target.value)


# -- Composite validators ---------------------------------------------------


def validate_source_registration(
    name: str,
    source_type: str | SourceType,
    location: SourceLocation | None,
    classification: str,
) -> None:
    assert_source_name_not_empty(name)
    assert_source_type_valid(source_type)
    assert_location_provided(location)
    assert_classification_valid(classification)


def validate_document_ingestion(
    source: KnowledgeSource,
    title: str,
    checksum: DocumentChecksum | None,
    classification: str,
) -> None:
    assert_source_provided_for_document(source)
    assert_source_active(source)
    assert_source_not_deleted(source)
    assert_source_allows_ingestion(source)
    assert_document_title_not_empty(title)
    assert_checksum_provided(checksum)
    assert_classification_valid(classification)


def validate_chunk_creation(
    document: KnowledgeDocument,
    content: ChunkContent,
    existing_indices: list[ChunkIndex],
) -> None:
    assert_document_provided_for_chunk(document)
    assert_document_not_deleted(document)
    assert_document_allows_chunk_creation(document)
    assert_chunk_content_not_empty(content)
    assert_chunk_content_max_length(content)
