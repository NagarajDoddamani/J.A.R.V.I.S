from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import planner
from backend.core.database import get_db
from backend.planner.adapters.outbound.models import Base
from backend.planner.bootstrap import (
    add_task_use_case,
    approve_plan_use_case,
    assign_task_use_case,
    cancel_plan_use_case,
    complete_plan_use_case,
    complete_task_use_case,
    create_plan_use_case,
    fail_plan_use_case,
    fail_task_use_case,
    get_plan_use_case,
    get_task_use_case,
    list_plans_use_case,
    list_tasks_use_case,
    mark_plan_ready_use_case,
    start_execution_use_case,
    start_planning_use_case,
    start_task_use_case,
)
from backend.planner.application.use_cases.add_task import AddTaskUseCase
from backend.planner.application.use_cases.approve_plan import ApprovePlanUseCase
from backend.planner.application.use_cases.assign_task import AssignTaskUseCase
from backend.planner.application.use_cases.cancel_plan import CancelPlanUseCase
from backend.planner.application.use_cases.complete_plan import CompletePlanUseCase
from backend.planner.application.use_cases.complete_task import CompleteTaskUseCase
from backend.planner.application.use_cases.create_plan import CreatePlanUseCase
from backend.planner.application.use_cases.fail_plan import FailPlanUseCase
from backend.planner.application.use_cases.fail_task import FailTaskUseCase
from backend.planner.application.use_cases.get_plan import GetPlanUseCase
from backend.planner.application.use_cases.get_task import GetTaskUseCase
from backend.planner.application.use_cases.list_plans import ListPlansUseCase
from backend.planner.application.use_cases.list_tasks import ListTasksUseCase
from backend.planner.application.use_cases.mark_plan_ready import (
    MarkPlanReadyUseCase,
)
from backend.planner.application.use_cases.start_execution import (
    StartExecutionUseCase,
)
from backend.planner.application.use_cases.start_planning import (
    StartPlanningUseCase,
)
from backend.planner.application.use_cases.start_task import StartTaskUseCase

for _table in Base.metadata.tables.values():
    _table.schema = None


@pytest.fixture
def session():
    e = create_engine("sqlite://", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    conn = e.connect()
    transaction = conn.begin()
    s = Session(bind=conn)
    yield s
    s.close()
    transaction.rollback()
    conn.close()
    e.dispose()


@pytest.fixture
def client(session):
    def _override_get_db():
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    app = FastAPI()
    app.include_router(planner.router, prefix="/api/v1/planner")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


# ===================================================================
# Bootstrap provider tests
# ===================================================================


class TestBootstrapProviders:
    def test_create_plan_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = create_plan_use_case()
            assert isinstance(uc, CreatePlanUseCase)

    def test_approve_plan_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = approve_plan_use_case()
            assert isinstance(uc, ApprovePlanUseCase)

    def test_start_planning_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = start_planning_use_case()
            assert isinstance(uc, StartPlanningUseCase)

    def test_mark_plan_ready_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = mark_plan_ready_use_case()
            assert isinstance(uc, MarkPlanReadyUseCase)

    def test_start_execution_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = start_execution_use_case()
            assert isinstance(uc, StartExecutionUseCase)

    def test_complete_plan_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = complete_plan_use_case()
            assert isinstance(uc, CompletePlanUseCase)

    def test_fail_plan_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = fail_plan_use_case()
            assert isinstance(uc, FailPlanUseCase)

    def test_cancel_plan_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = cancel_plan_use_case()
            assert isinstance(uc, CancelPlanUseCase)

    def test_add_task_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = add_task_use_case()
            assert isinstance(uc, AddTaskUseCase)

    def test_assign_task_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = assign_task_use_case()
            assert isinstance(uc, AssignTaskUseCase)

    def test_start_task_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = start_task_use_case()
            assert isinstance(uc, StartTaskUseCase)

    def test_complete_task_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = complete_task_use_case()
            assert isinstance(uc, CompleteTaskUseCase)

    def test_fail_task_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = fail_task_use_case()
            assert isinstance(uc, FailTaskUseCase)

    def test_get_plan_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = get_plan_use_case()
            assert isinstance(uc, GetPlanUseCase)

    def test_list_plans_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = list_plans_use_case()
            assert isinstance(uc, ListPlansUseCase)

    def test_get_task_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = get_task_use_case()
            assert isinstance(uc, GetTaskUseCase)

    def test_list_tasks_use_case_provider(self) -> None:
        with patch("backend.planner.bootstrap.get_db"):
            uc = list_tasks_use_case()
            assert isinstance(uc, ListTasksUseCase)
