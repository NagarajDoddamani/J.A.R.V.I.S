from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.research.adapters.outbound.clock import SystemClockAdapter
from backend.research.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.research.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyResearchJobRepository,
    SqlAlchemyResearchOutboxAdapter,
    SqlAlchemyResearchRequestRepository,
    SqlAlchemyResearchSourceRepository,
)
from backend.research.application.use_cases.add_source import AddSourceUseCase
from backend.research.application.use_cases.cancel_request import CancelRequestUseCase
from backend.research.application.use_cases.complete_job import CompleteJobUseCase
from backend.research.application.use_cases.complete_request import CompleteRequestUseCase
from backend.research.application.use_cases.create_job import CreateJobUseCase
from backend.research.application.use_cases.create_request import CreateRequestUseCase
from backend.research.application.use_cases.fail_job import FailJobUseCase
from backend.research.application.use_cases.fail_request import FailRequestUseCase
from backend.research.application.use_cases.generate_summary import GenerateSummaryUseCase
from backend.research.application.use_cases.get_job import GetJobUseCase
from backend.research.application.use_cases.get_request import GetRequestUseCase
from backend.research.application.use_cases.list_jobs import ListJobsUseCase
from backend.research.application.use_cases.list_requests import ListRequestsUseCase
from backend.research.application.use_cases.start_job import StartJobUseCase
from backend.research.application.use_cases.start_request import StartRequestUseCase


# -- Internal providers ------------------------------------------------


def _request_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyResearchRequestRepository:
    return SqlAlchemyResearchRequestRepository(db)


def _job_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyResearchJobRepository:
    return SqlAlchemyResearchJobRepository(db)


def _source_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyResearchSourceRepository:
    return SqlAlchemyResearchSourceRepository(db)


def _outbox(
    db: Session = Depends(get_db),
) -> SqlAlchemyResearchOutboxAdapter:
    return SqlAlchemyResearchOutboxAdapter(db)


def _clock() -> SystemClockAdapter:
    return SystemClockAdapter()


def _id_generator() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


# -- Request use-case providers ----------------------------------------


def create_request_use_case(
    request_repo: SqlAlchemyResearchRequestRepository = Depends(_request_repo),
    outbox: SqlAlchemyResearchOutboxAdapter = Depends(_outbox),
) -> CreateRequestUseCase:
    return CreateRequestUseCase(request_repo=request_repo, outbox=outbox)


def start_request_use_case(
    request_repo: SqlAlchemyResearchRequestRepository = Depends(_request_repo),
    outbox: SqlAlchemyResearchOutboxAdapter = Depends(_outbox),
) -> StartRequestUseCase:
    return StartRequestUseCase(request_repo=request_repo, outbox=outbox)


def complete_request_use_case(
    request_repo: SqlAlchemyResearchRequestRepository = Depends(_request_repo),
    outbox: SqlAlchemyResearchOutboxAdapter = Depends(_outbox),
) -> CompleteRequestUseCase:
    return CompleteRequestUseCase(request_repo=request_repo, outbox=outbox)


def fail_request_use_case(
    request_repo: SqlAlchemyResearchRequestRepository = Depends(_request_repo),
    outbox: SqlAlchemyResearchOutboxAdapter = Depends(_outbox),
) -> FailRequestUseCase:
    return FailRequestUseCase(request_repo=request_repo, outbox=outbox)


def cancel_request_use_case(
    request_repo: SqlAlchemyResearchRequestRepository = Depends(_request_repo),
    outbox: SqlAlchemyResearchOutboxAdapter = Depends(_outbox),
) -> CancelRequestUseCase:
    return CancelRequestUseCase(request_repo=request_repo, outbox=outbox)


# -- Job use-case providers --------------------------------------------


def create_job_use_case(
    request_repo: SqlAlchemyResearchRequestRepository = Depends(_request_repo),
    job_repo: SqlAlchemyResearchJobRepository = Depends(_job_repo),
    outbox: SqlAlchemyResearchOutboxAdapter = Depends(_outbox),
) -> CreateJobUseCase:
    return CreateJobUseCase(
        request_repo=request_repo, job_repo=job_repo, outbox=outbox
    )


def start_job_use_case(
    job_repo: SqlAlchemyResearchJobRepository = Depends(_job_repo),
    outbox: SqlAlchemyResearchOutboxAdapter = Depends(_outbox),
) -> StartJobUseCase:
    return StartJobUseCase(job_repo=job_repo, outbox=outbox)


def complete_job_use_case(
    job_repo: SqlAlchemyResearchJobRepository = Depends(_job_repo),
    outbox: SqlAlchemyResearchOutboxAdapter = Depends(_outbox),
) -> CompleteJobUseCase:
    return CompleteJobUseCase(job_repo=job_repo, outbox=outbox)


def fail_job_use_case(
    job_repo: SqlAlchemyResearchJobRepository = Depends(_job_repo),
    outbox: SqlAlchemyResearchOutboxAdapter = Depends(_outbox),
) -> FailJobUseCase:
    return FailJobUseCase(job_repo=job_repo, outbox=outbox)


# -- Source / summary use-case providers --------------------------------


def add_source_use_case(
    job_repo: SqlAlchemyResearchJobRepository = Depends(_job_repo),
    source_repo: SqlAlchemyResearchSourceRepository = Depends(_source_repo),
    outbox: SqlAlchemyResearchOutboxAdapter = Depends(_outbox),
) -> AddSourceUseCase:
    return AddSourceUseCase(
        job_repo=job_repo, source_repo=source_repo, outbox=outbox
    )


def generate_summary_use_case(
    job_repo: SqlAlchemyResearchJobRepository = Depends(_job_repo),
    outbox: SqlAlchemyResearchOutboxAdapter = Depends(_outbox),
) -> GenerateSummaryUseCase:
    return GenerateSummaryUseCase(job_repo=job_repo, outbox=outbox)


# -- Query use-case providers ------------------------------------------


def get_request_use_case(
    request_repo: SqlAlchemyResearchRequestRepository = Depends(_request_repo),
) -> GetRequestUseCase:
    return GetRequestUseCase(request_repo=request_repo)


def list_requests_use_case(
    request_repo: SqlAlchemyResearchRequestRepository = Depends(_request_repo),
) -> ListRequestsUseCase:
    return ListRequestsUseCase(request_repo=request_repo)


def get_job_use_case(
    job_repo: SqlAlchemyResearchJobRepository = Depends(_job_repo),
) -> GetJobUseCase:
    return GetJobUseCase(job_repo=job_repo)


def list_jobs_use_case(
    job_repo: SqlAlchemyResearchJobRepository = Depends(_job_repo),
) -> ListJobsUseCase:
    return ListJobsUseCase(job_repo=job_repo)
