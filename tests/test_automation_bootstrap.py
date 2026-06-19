from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.api.endpoints import automation
from backend.automation.adapters.outbound.models import Base
from backend.automation.bootstrap import (
    activate_automation_use_case,
    add_action_use_case,
    add_trigger_use_case,
    complete_execution_use_case,
    create_automation_use_case,
    disable_automation_use_case,
    disable_trigger_use_case,
    enable_trigger_use_case,
    fail_execution_use_case,
    get_automation_use_case,
    get_execution_use_case,
    get_trigger_use_case,
    list_automations_use_case,
    list_executions_use_case,
    list_triggers_use_case,
    pause_automation_use_case,
    start_execution_use_case,
)
from backend.automation.application.use_cases.activate_automation import (
    ActivateAutomationUseCase,
)
from backend.automation.application.use_cases.add_action import AddActionUseCase
from backend.automation.application.use_cases.add_trigger import AddTriggerUseCase
from backend.automation.application.use_cases.complete_execution import (
    CompleteExecutionUseCase,
)
from backend.automation.application.use_cases.create_automation import (
    CreateAutomationUseCase,
)
from backend.automation.application.use_cases.disable_automation import (
    DisableAutomationUseCase,
)
from backend.automation.application.use_cases.disable_trigger import (
    DisableTriggerUseCase,
)
from backend.automation.application.use_cases.enable_trigger import (
    EnableTriggerUseCase,
)
from backend.automation.application.use_cases.fail_execution import (
    FailExecutionUseCase,
)
from backend.automation.application.use_cases.get_automation import (
    GetAutomationUseCase,
)
from backend.automation.application.use_cases.get_execution import (
    GetExecutionUseCase,
)
from backend.automation.application.use_cases.get_trigger import (
    GetTriggerUseCase,
)
from backend.automation.application.use_cases.list_automations import (
    ListAutomationsUseCase,
)
from backend.automation.application.use_cases.list_executions import (
    ListExecutionsUseCase,
)
from backend.automation.application.use_cases.list_triggers import (
    ListTriggersUseCase,
)
from backend.automation.application.use_cases.pause_automation import (
    PauseAutomationUseCase,
)
from backend.automation.application.use_cases.start_execution import (
    StartExecutionUseCase,
)
from backend.core.database import get_db

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
    app.include_router(automation.router, prefix="/api/v1/automation")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


class TestBootstrapProviders:
    def test_create_automation_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = create_automation_use_case()
            assert isinstance(uc, CreateAutomationUseCase)

    def test_activate_automation_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = activate_automation_use_case()
            assert isinstance(uc, ActivateAutomationUseCase)

    def test_pause_automation_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = pause_automation_use_case()
            assert isinstance(uc, PauseAutomationUseCase)

    def test_disable_automation_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = disable_automation_use_case()
            assert isinstance(uc, DisableAutomationUseCase)

    def test_add_trigger_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = add_trigger_use_case()
            assert isinstance(uc, AddTriggerUseCase)

    def test_enable_trigger_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = enable_trigger_use_case()
            assert isinstance(uc, EnableTriggerUseCase)

    def test_disable_trigger_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = disable_trigger_use_case()
            assert isinstance(uc, DisableTriggerUseCase)

    def test_add_action_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = add_action_use_case()
            assert isinstance(uc, AddActionUseCase)

    def test_start_execution_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = start_execution_use_case()
            assert isinstance(uc, StartExecutionUseCase)

    def test_complete_execution_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = complete_execution_use_case()
            assert isinstance(uc, CompleteExecutionUseCase)

    def test_fail_execution_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = fail_execution_use_case()
            assert isinstance(uc, FailExecutionUseCase)

    def test_get_automation_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = get_automation_use_case()
            assert isinstance(uc, GetAutomationUseCase)

    def test_list_automations_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = list_automations_use_case()
            assert isinstance(uc, ListAutomationsUseCase)

    def test_get_trigger_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = get_trigger_use_case()
            assert isinstance(uc, GetTriggerUseCase)

    def test_list_triggers_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = list_triggers_use_case()
            assert isinstance(uc, ListTriggersUseCase)

    def test_get_execution_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = get_execution_use_case()
            assert isinstance(uc, GetExecutionUseCase)

    def test_list_executions_use_case_provider(self) -> None:
        with patch("backend.automation.bootstrap.get_db"):
            uc = list_executions_use_case()
            assert isinstance(uc, ListExecutionsUseCase)
