from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


# =====================================================================
# Response DTOs (shared by queries and command responses)
# =====================================================================


@dataclass
class SourceResponse:
    source_id: str
    source_type: str = "web"
    reference: str | None = None
    confidence_score: float | None = None


@dataclass
class JobResponse:
    job_id: str
    goal: str | None = None
    priority: str = "normal"
    status: str = "created"
    summary: str | None = None
    failure_reason: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    source_count: int = 0


@dataclass
class RequestResponse:
    request_id: str
    query: str | None = None
    goal: str | None = None
    priority: str = "normal"
    status: str = "created"
    failure_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    job_count: int = 0


# =====================================================================
# CreateRequest
# =====================================================================


@dataclass
class CreateRequestRequest:
    query: str
    goal: str
    priority: str = "normal"


@dataclass
class CreateRequestResponse:
    request_id: str
    query: str | None
    goal: str | None
    priority: str
    status: str
    created_at: datetime


# =====================================================================
# Request lifecycle commands
# =====================================================================


@dataclass
class RequestLifecycleRequest:
    request_id: str


@dataclass
class RequestLifecycleResponse:
    request_id: str
    status: str
    updated_at: datetime | None = None


@dataclass
class FailRequestRequest:
    request_id: str
    failure_reason: str


@dataclass
class FailRequestResponse:
    request_id: str
    status: str
    failure_reason: str | None = None
    updated_at: datetime | None = None


# =====================================================================
# CreateJob
# =====================================================================


@dataclass
class CreateJobRequest:
    request_id: str
    goal: str
    priority: str | None = None


@dataclass
class CreateJobResponse:
    job_id: str
    request_id: str | None
    goal: str | None
    priority: str
    status: str


# =====================================================================
# Job lifecycle commands
# =====================================================================


@dataclass
class JobLifecycleRequest:
    job_id: str


@dataclass
class JobLifecycleResponse:
    job_id: str
    status: str


@dataclass
class FailJobRequest:
    job_id: str
    failure_reason: str


@dataclass
class FailJobResponse:
    job_id: str
    status: str
    failure_reason: str | None = None


# =====================================================================
# AddSource
# =====================================================================


@dataclass
class AddSourceRequest:
    job_id: str
    reference: str
    source_type: str = "web"
    confidence_score: float = 0.5


@dataclass
class AddSourceResponse:
    source_id: str
    job_id: str | None
    source_type: str
    reference: str | None
    confidence_score: float | None


# =====================================================================
# GenerateSummary
# =====================================================================


@dataclass
class GenerateSummaryRequest:
    job_id: str
    summary: str


@dataclass
class GenerateSummaryResponse:
    job_id: str
    summary: str | None
    status: str


# =====================================================================
# Queries
# =====================================================================


@dataclass
class GetRequestRequest:
    request_id: str


@dataclass
class ListRequestsRequest:
    status: str | None = None
    priority: str | None = None


@dataclass
class ListRequestsResponse:
    requests: list[RequestResponse] = field(default_factory=list)
    total: int = 0


@dataclass
class GetJobRequest:
    job_id: str


@dataclass
class ListJobsRequest:
    status: str | None = None
    request_id: str | None = None


@dataclass
class ListJobsResponse:
    jobs: list[JobResponse] = field(default_factory=list)
    total: int = 0
