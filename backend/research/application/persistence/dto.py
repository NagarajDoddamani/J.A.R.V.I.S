from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ResearchRequestStorageDTO:
    request_id: str
    query: str | None = None
    goal: str | None = None
    priority: str = "normal"
    status: str = "created"
    failure_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class ResearchJobStorageDTO:
    job_id: str
    request_id: str | None = None
    goal: str | None = None
    priority: str = "normal"
    status: str = "created"
    summary: str | None = None
    failure_reason: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class ResearchSourceStorageDTO:
    source_id: str
    job_id: str | None = None
    source_type: str = "web"
    reference: str | None = None
    confidence_score: float | None = None


@dataclass(frozen=True)
class ResearchOutboxStorageDTO:
    event_id: str
    event_type: str
    aggregate_id: str
    occurred_at: datetime
    payload: str | None = None
    published: bool = False
