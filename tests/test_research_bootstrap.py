from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.research.adapters.outbound.clock import SystemClockAdapter
from backend.research.adapters.outbound.id_generator import UuidGeneratorAdapter
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
from backend.research.bootstrap import (
    _clock,
    _id_generator,
    _job_repo,
    _outbox,
    _request_repo,
    _source_repo,
    add_source_use_case,
    cancel_request_use_case,
    complete_job_use_case,
    complete_request_use_case,
    create_job_use_case,
    create_request_use_case,
    fail_job_use_case,
    fail_request_use_case,
    generate_summary_use_case,
    get_job_use_case,
    get_request_use_case,
    list_jobs_use_case,
    list_requests_use_case,
    start_job_use_case,
    start_request_use_case,
)


# ===================================================================
# Internal provider tests
# ===================================================================


def test_request_repo_provider() -> None:
    with patch("backend.research.bootstrap.get_db") as mock_db:
        mock_db.return_value = MagicMock()
        repo = _request_repo()
        from backend.research.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyResearchRequestRepository,
        )

        assert isinstance(repo, SqlAlchemyResearchRequestRepository)


def test_job_repo_provider() -> None:
    with patch("backend.research.bootstrap.get_db") as mock_db:
        mock_db.return_value = MagicMock()
        repo = _job_repo()
        from backend.research.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyResearchJobRepository,
        )

        assert isinstance(repo, SqlAlchemyResearchJobRepository)


def test_source_repo_provider() -> None:
    with patch("backend.research.bootstrap.get_db") as mock_db:
        mock_db.return_value = MagicMock()
        repo = _source_repo()
        from backend.research.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyResearchSourceRepository,
        )

        assert isinstance(repo, SqlAlchemyResearchSourceRepository)


def test_outbox_provider() -> None:
    with patch("backend.research.bootstrap.get_db") as mock_db:
        mock_db.return_value = MagicMock()
        ob = _outbox()
        from backend.research.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyResearchOutboxAdapter,
        )

        assert isinstance(ob, SqlAlchemyResearchOutboxAdapter)


def test_clock_provider() -> None:
    clock = _clock()
    assert isinstance(clock, SystemClockAdapter)


def test_id_generator_provider() -> None:
    gen = _id_generator()
    assert isinstance(gen, UuidGeneratorAdapter)


# ===================================================================
# Use case provider tests
# ===================================================================


def test_create_request_use_case_provider() -> None:
    use_case = create_request_use_case(
        request_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(use_case, CreateRequestUseCase)


def test_start_request_use_case_provider() -> None:
    use_case = start_request_use_case(
        request_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(use_case, StartRequestUseCase)


def test_complete_request_use_case_provider() -> None:
    use_case = complete_request_use_case(
        request_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(use_case, CompleteRequestUseCase)


def test_fail_request_use_case_provider() -> None:
    use_case = fail_request_use_case(
        request_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(use_case, FailRequestUseCase)


def test_cancel_request_use_case_provider() -> None:
    use_case = cancel_request_use_case(
        request_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(use_case, CancelRequestUseCase)


def test_create_job_use_case_provider() -> None:
    use_case = create_job_use_case(
        request_repo=MagicMock(), job_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(use_case, CreateJobUseCase)


def test_start_job_use_case_provider() -> None:
    use_case = start_job_use_case(
        job_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(use_case, StartJobUseCase)


def test_complete_job_use_case_provider() -> None:
    use_case = complete_job_use_case(
        job_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(use_case, CompleteJobUseCase)


def test_fail_job_use_case_provider() -> None:
    use_case = fail_job_use_case(
        job_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(use_case, FailJobUseCase)


def test_add_source_use_case_provider() -> None:
    use_case = add_source_use_case(
        job_repo=MagicMock(), source_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(use_case, AddSourceUseCase)


def test_generate_summary_use_case_provider() -> None:
    use_case = generate_summary_use_case(
        job_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(use_case, GenerateSummaryUseCase)


def test_get_request_use_case_provider() -> None:
    use_case = get_request_use_case(request_repo=MagicMock())
    assert isinstance(use_case, GetRequestUseCase)


def test_list_requests_use_case_provider() -> None:
    use_case = list_requests_use_case(request_repo=MagicMock())
    assert isinstance(use_case, ListRequestsUseCase)


def test_get_job_use_case_provider() -> None:
    use_case = get_job_use_case(job_repo=MagicMock())
    assert isinstance(use_case, GetJobUseCase)


def test_list_jobs_use_case_provider() -> None:
    use_case = list_jobs_use_case(job_repo=MagicMock())
    assert isinstance(use_case, ListJobsUseCase)
