from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ColumnContract:
    name: str
    py_type: type[Any]
    nullable: bool
    max_length: int | None = None
    enum_values: tuple[str, ...] | None = None


@dataclass(frozen=True)
class TableContract:
    name: str
    schema: str
    columns: tuple[ColumnContract, ...]
    primary_key: str | tuple[str, ...]
    indexes: tuple[str, ...] = ()
    unique_constraints: tuple[str, ...] = ()


KNOWLEDGE_SOURCES_TABLE: TableContract = TableContract(
    name="knowledge_sources",
    schema="knowledge",
    columns=(
        ColumnContract("source_id", str, nullable=False),
        ColumnContract("name", str, nullable=False),
        ColumnContract("source_type", str, nullable=False, max_length=32,
                       enum_values=("file", "directory", "url", "manual", "memory_export")),
        ColumnContract("location", str, nullable=True),
        ColumnContract("classification", str, nullable=False, max_length=16,
                       enum_values=("public", "internal", "sensitive", "restricted")),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("registered", "active", "disabled", "deleted")),
        ColumnContract("created_at", datetime, nullable=False),
        ColumnContract("updated_at", datetime, nullable=True),
        ColumnContract("deleted_at", datetime, nullable=True),
    ),
    primary_key="source_id",
    indexes=(
        "ix_knowledge_sources_status",
        "ix_knowledge_sources_type",
    ),
)

KNOWLEDGE_DOCUMENTS_TABLE: TableContract = TableContract(
    name="knowledge_documents",
    schema="knowledge",
    columns=(
        ColumnContract("document_id", str, nullable=False),
        ColumnContract("source_id", str, nullable=True),
        ColumnContract("title", str, nullable=False),
        ColumnContract("checksum", str, nullable=True),
        ColumnContract("classification", str, nullable=False, max_length=16,
                       enum_values=("public", "internal", "sensitive", "restricted")),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("pending", "ingested", "indexed", "deleted")),
        ColumnContract("revision", int, nullable=False),
        ColumnContract("created_at", datetime, nullable=False),
        ColumnContract("updated_at", datetime, nullable=True),
        ColumnContract("deleted_at", datetime, nullable=True),
    ),
    primary_key="document_id",
    indexes=(
        "ix_knowledge_documents_source",
        "ix_knowledge_documents_status",
    ),
)

KNOWLEDGE_CHUNKS_TABLE: TableContract = TableContract(
    name="knowledge_chunks",
    schema="knowledge",
    columns=(
        ColumnContract("chunk_id", str, nullable=False),
        ColumnContract("document_id", str, nullable=True),
        ColumnContract("chunk_index", int, nullable=True),
        ColumnContract("content", str, nullable=True),
        ColumnContract("classification", str, nullable=False, max_length=16,
                       enum_values=("public", "internal", "sensitive", "restricted")),
        ColumnContract("created_at", datetime, nullable=False),
    ),
    primary_key="chunk_id",
    indexes=(
        "ix_knowledge_chunks_document",
        "ix_knowledge_chunks_index",
    ),
)

INGESTION_JOBS_TABLE: TableContract = TableContract(
    name="ingestion_jobs",
    schema="knowledge",
    columns=(
        ColumnContract("job_id", str, nullable=False),
        ColumnContract("source_id", str, nullable=True),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("queued", "running", "completed", "failed")),
        ColumnContract("started_at", datetime, nullable=False),
        ColumnContract("completed_at", datetime, nullable=True),
        ColumnContract("error_message", str, nullable=True),
    ),
    primary_key="job_id",
    indexes=(
        "ix_ingestion_jobs_status",
        "ix_ingestion_jobs_source",
    ),
)

KNOWLEDGE_OUTBOX_TABLE: TableContract = TableContract(
    name="outbox",
    schema="knowledge",
    columns=(
        ColumnContract("event_id", str, nullable=False),
        ColumnContract("event_type", str, nullable=False, max_length=32,
                       enum_values=("knowledge.source.registered",
                                    "knowledge.source.deleted",
                                    "knowledge.document.ingested",
                                    "knowledge.document.indexed",
                                    "knowledge.document.deleted",
                                    "knowledge.chunk.created",
                                    "knowledge.reindex.requested",
                                    "knowledge.ingestion.started",
                                    "knowledge.ingestion.completed",
                                    "knowledge.ingestion.failed")),
        ColumnContract("aggregate_id", str, nullable=False),
        ColumnContract("occurred_at", datetime, nullable=False),
        ColumnContract("correlation_id", str, nullable=True),
        ColumnContract("causation_id", str, nullable=True),
        ColumnContract("payload", str, nullable=True),
        ColumnContract("published", bool, nullable=False),
    ),
    primary_key="event_id",
    indexes=(
        "ix_knowledge_outbox_unpublished",
        "ix_knowledge_outbox_aggregate",
    ),
)
