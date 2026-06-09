from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.knowledge.adapters.outbound.clock import SystemClockAdapter
from backend.knowledge.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.knowledge.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyIngestionJobRepository,
    SqlAlchemyKnowledgeChunkRepository,
    SqlAlchemyKnowledgeDocumentRepository,
    SqlAlchemyKnowledgeOutboxAdapter,
    SqlAlchemyKnowledgeSourceRepository,
)
from backend.knowledge.application.use_cases.complete_ingestion import (
    CompleteIngestionUseCase,
)
from backend.knowledge.application.use_cases.create_chunk import (
    CreateChunkUseCase,
)
from backend.knowledge.application.use_cases.delete_source import (
    DeleteSourceUseCase,
)
from backend.knowledge.application.use_cases.fail_ingestion import (
    FailIngestionUseCase,
)
from backend.knowledge.application.use_cases.get_chunks_by_document import (
    GetChunksByDocumentUseCase,
)
from backend.knowledge.application.use_cases.get_document import (
    GetDocumentUseCase,
)
from backend.knowledge.application.use_cases.get_ingestion_job import (
    GetIngestionJobUseCase,
)
from backend.knowledge.application.use_cases.get_source import (
    GetSourceUseCase,
)
from backend.knowledge.application.use_cases.ingest_document import (
    IngestDocumentUseCase,
)
from backend.knowledge.application.use_cases.list_sources import (
    ListSourcesUseCase,
)
from backend.knowledge.application.use_cases.register_source import (
    RegisterSourceUseCase,
)
from backend.knowledge.application.use_cases.request_reindex import (
    RequestReindexUseCase,
)
from backend.knowledge.application.use_cases.start_ingestion import (
    StartIngestionUseCase,
)


def _source_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyKnowledgeSourceRepository:
    return SqlAlchemyKnowledgeSourceRepository(db)


def _document_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyKnowledgeDocumentRepository:
    return SqlAlchemyKnowledgeDocumentRepository(db)


def _chunk_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyKnowledgeChunkRepository:
    return SqlAlchemyKnowledgeChunkRepository(db)


def _job_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyIngestionJobRepository:
    return SqlAlchemyIngestionJobRepository(db)


def _outbox(
    db: Session = Depends(get_db),
) -> SqlAlchemyKnowledgeOutboxAdapter:
    return SqlAlchemyKnowledgeOutboxAdapter(db)


def _clock() -> SystemClockAdapter:
    return SystemClockAdapter()


def _id_generator() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


def register_source_use_case(
    source_repo: SqlAlchemyKnowledgeSourceRepository = Depends(_source_repo),
    outbox: SqlAlchemyKnowledgeOutboxAdapter = Depends(_outbox),
    clock: SystemClockAdapter = Depends(_clock),
    id_generator: UuidGeneratorAdapter = Depends(_id_generator),
) -> RegisterSourceUseCase:
    return RegisterSourceUseCase(
        source_repo=source_repo,
        outbox=outbox,
        clock=clock,
        id_generator=id_generator,
    )


def delete_source_use_case(
    source_repo: SqlAlchemyKnowledgeSourceRepository = Depends(_source_repo),
    outbox: SqlAlchemyKnowledgeOutboxAdapter = Depends(_outbox),
) -> DeleteSourceUseCase:
    return DeleteSourceUseCase(
        source_repo=source_repo,
        outbox=outbox,
    )


def get_source_use_case(
    source_repo: SqlAlchemyKnowledgeSourceRepository = Depends(_source_repo),
) -> GetSourceUseCase:
    return GetSourceUseCase(source_repo=source_repo)


def list_sources_use_case(
    source_repo: SqlAlchemyKnowledgeSourceRepository = Depends(_source_repo),
) -> ListSourcesUseCase:
    return ListSourcesUseCase(source_repo=source_repo)


def ingest_document_use_case(
    source_repo: SqlAlchemyKnowledgeSourceRepository = Depends(_source_repo),
    document_repo: SqlAlchemyKnowledgeDocumentRepository = Depends(_document_repo),
    outbox: SqlAlchemyKnowledgeOutboxAdapter = Depends(_outbox),
    clock: SystemClockAdapter = Depends(_clock),
    id_generator: UuidGeneratorAdapter = Depends(_id_generator),
) -> IngestDocumentUseCase:
    return IngestDocumentUseCase(
        source_repo=source_repo,
        document_repo=document_repo,
        outbox=outbox,
        clock=clock,
        id_generator=id_generator,
    )


def get_document_use_case(
    document_repo: SqlAlchemyKnowledgeDocumentRepository = Depends(_document_repo),
) -> GetDocumentUseCase:
    return GetDocumentUseCase(document_repo=document_repo)


def create_chunk_use_case(
    document_repo: SqlAlchemyKnowledgeDocumentRepository = Depends(_document_repo),
    chunk_repo: SqlAlchemyKnowledgeChunkRepository = Depends(_chunk_repo),
    outbox: SqlAlchemyKnowledgeOutboxAdapter = Depends(_outbox),
    clock: SystemClockAdapter = Depends(_clock),
    id_generator: UuidGeneratorAdapter = Depends(_id_generator),
) -> CreateChunkUseCase:
    return CreateChunkUseCase(
        document_repo=document_repo,
        chunk_repo=chunk_repo,
        outbox=outbox,
        clock=clock,
        id_generator=id_generator,
    )


def get_chunks_by_document_use_case(
    chunk_repo: SqlAlchemyKnowledgeChunkRepository = Depends(_chunk_repo),
) -> GetChunksByDocumentUseCase:
    return GetChunksByDocumentUseCase(chunk_repo=chunk_repo)


def start_ingestion_use_case(
    source_repo: SqlAlchemyKnowledgeSourceRepository = Depends(_source_repo),
    job_repo: SqlAlchemyIngestionJobRepository = Depends(_job_repo),
    outbox: SqlAlchemyKnowledgeOutboxAdapter = Depends(_outbox),
    clock: SystemClockAdapter = Depends(_clock),
    id_generator: UuidGeneratorAdapter = Depends(_id_generator),
) -> StartIngestionUseCase:
    return StartIngestionUseCase(
        source_repo=source_repo,
        job_repo=job_repo,
        outbox=outbox,
        clock=clock,
        id_generator=id_generator,
    )


def complete_ingestion_use_case(
    job_repo: SqlAlchemyIngestionJobRepository = Depends(_job_repo),
    outbox: SqlAlchemyKnowledgeOutboxAdapter = Depends(_outbox),
) -> CompleteIngestionUseCase:
    return CompleteIngestionUseCase(
        job_repo=job_repo,
        outbox=outbox,
    )


def fail_ingestion_use_case(
    job_repo: SqlAlchemyIngestionJobRepository = Depends(_job_repo),
    outbox: SqlAlchemyKnowledgeOutboxAdapter = Depends(_outbox),
) -> FailIngestionUseCase:
    return FailIngestionUseCase(
        job_repo=job_repo,
        outbox=outbox,
    )


def get_ingestion_job_use_case(
    job_repo: SqlAlchemyIngestionJobRepository = Depends(_job_repo),
) -> GetIngestionJobUseCase:
    return GetIngestionJobUseCase(job_repo=job_repo)


def request_reindex_use_case(
    source_repo: SqlAlchemyKnowledgeSourceRepository = Depends(_source_repo),
    outbox: SqlAlchemyKnowledgeOutboxAdapter = Depends(_outbox),
) -> RequestReindexUseCase:
    return RequestReindexUseCase(
        source_repo=source_repo,
        outbox=outbox,
    )
