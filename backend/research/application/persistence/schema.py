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


RESEARCH_REQUESTS_TABLE: TableContract = TableContract(
    name="research_requests",
    schema="research",
    columns=(
        ColumnContract("request_id", str, nullable=False),
        ColumnContract("query", str, nullable=True),
        ColumnContract("goal", str, nullable=True),
        ColumnContract("priority", str, nullable=False, max_length=16,
                       enum_values=("low", "normal", "high", "critical")),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("created", "running", "completed",
                                    "failed", "cancelled")),
        ColumnContract("failure_reason", str, nullable=True),
        ColumnContract("created_at", datetime, nullable=False),
        ColumnContract("updated_at", datetime, nullable=True),
    ),
    primary_key="request_id",
    indexes=(
        "ix_research_requests_status",
        "ix_research_requests_priority",
    ),
)

RESEARCH_JOBS_TABLE: TableContract = TableContract(
    name="research_jobs",
    schema="research",
    columns=(
        ColumnContract("job_id", str, nullable=False),
        ColumnContract("request_id", str, nullable=True),
        ColumnContract("goal", str, nullable=True),
        ColumnContract("priority", str, nullable=False, max_length=16,
                       enum_values=("low", "normal", "high", "critical")),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("created", "running", "completed",
                                    "failed", "cancelled")),
        ColumnContract("summary", str, nullable=True),
        ColumnContract("failure_reason", str, nullable=True),
        ColumnContract("created_at", datetime, nullable=False),
        ColumnContract("completed_at", datetime, nullable=True),
    ),
    primary_key="job_id",
    indexes=(
        "ix_research_jobs_request_id",
        "ix_research_jobs_status",
    ),
)

RESEARCH_SOURCES_TABLE: TableContract = TableContract(
    name="research_sources",
    schema="research",
    columns=(
        ColumnContract("source_id", str, nullable=False),
        ColumnContract("job_id", str, nullable=True),
        ColumnContract("source_type", str, nullable=False, max_length=16,
                       enum_values=("memory", "knowledge", "web",
                                    "document", "user")),
        ColumnContract("reference", str, nullable=True),
        ColumnContract("confidence_score", float, nullable=True),
    ),
    primary_key="source_id",
    indexes=(
        "ix_research_sources_job_id",
        "ix_research_sources_source_type",
    ),
)

RESEARCH_OUTBOX_TABLE: TableContract = TableContract(
    name="outbox",
    schema="research",
    columns=(
        ColumnContract("event_id", str, nullable=False),
        ColumnContract("event_type", str, nullable=False, max_length=32,
                       enum_values=("research.requested",
                                    "research.started",
                                    "research.completed",
                                    "research.failed",
                                    "research.cancelled",
                                    "source.added",
                                    "research.summary_generated")),
        ColumnContract("aggregate_id", str, nullable=False),
        ColumnContract("occurred_at", datetime, nullable=False),
        ColumnContract("payload", str, nullable=True),
        ColumnContract("published", bool, nullable=False),
    ),
    primary_key="event_id",
    indexes=(
        "ix_research_outbox_unpublished",
        "ix_research_outbox_aggregate",
    ),
)
