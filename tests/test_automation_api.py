from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.api.endpoints import automation
from backend.automation.adapters.outbound.clock import SystemClockAdapter
from backend.automation.adapters.outbound.mapper import (
    AutomationMapperImpl,
    TriggerMapperImpl,
)
from backend.automation.adapters.outbound.models import Base
from backend.automation.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyAutomationExecutionRepository,
    SqlAlchemyAutomationOutboxAdapter,
    SqlAlchemyAutomationRepository,
    SqlAlchemyTriggerRepository,
)
from backend.automation.application.use_cases.dto import (
    AddActionResponse,
    AddTriggerResponse,
    AutomationLifecycleResponse,
    AutomationResponse,
    CompleteExecutionResponse,
    CreateAutomationResponse,
    ExecutionResponse,
    FailExecutionResponse,
    ListAutomationsResponse,
    ListExecutionsResponse,
    ListTriggersResponse,
    StartExecutionResponse,
    TriggerLifecycleResponse,
    TriggerResponse,
)
from backend.core.database import get_db

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)
NOT_FOUND_ID = "00000000-0000-0000-0000-000000000000"

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


@pytest.fixture
def clock():
    return SystemClockAdapter()


@pytest.fixture
def automation_repo(session):
    return SqlAlchemyAutomationRepository(session, mapper=AutomationMapperImpl())


@pytest.fixture
def trigger_repo(session):
    return SqlAlchemyTriggerRepository(session)


@pytest.fixture
def execution_repo(session):
    return SqlAlchemyAutomationExecutionRepository(session)


@pytest.fixture
def outbox(session):
    return SqlAlchemyAutomationOutboxAdapter(session)


def _create_automation(client, name: str = "Test Automation", description: str = "Test Description", execution_mode: str = "once") -> str:
    resp = client.post(
        "/api/v1/automation/automations",
        json={
            "name": name,
            "description": description,
            "execution_mode": execution_mode,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "automation_id" in data
    return data["automation_id"]


class TestAutomationAPI:
    def test_create_automation(self, client) -> None:
        resp = client.post(
            "/api/v1/automation/automations",
            json={"name": "My Automation", "description": "My Description", "execution_mode": "once"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Automation"
        assert data["description"] == "My Description"
        assert data["execution_mode"] == "once"
        assert data["status"] == "draft"

    def test_create_automation_invalid_name(self, client) -> None:
        resp = client.post(
            "/api/v1/automation/automations",
            json={"name": "", "description": "desc", "execution_mode": "once"},
        )
        assert resp.status_code == 400

    def test_get_automation(self, client) -> None:
        automation_id = _create_automation(client)
        resp = client.get(f"/api/v1/automation/automations/{automation_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["automation_id"] == automation_id
        assert data["name"] == "Test Automation"

    def test_get_automation_not_found(self, client) -> None:
        resp = client.get(f"/api/v1/automation/automations/{NOT_FOUND_ID}")
        assert resp.status_code == 404

    def test_list_automations(self, client) -> None:
        _create_automation(client, "A1")
        _create_automation(client, "A2")
        resp = client.get("/api/v1/automation/automations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_list_automations_by_status(self, client) -> None:
        _create_automation(client, "A1")
        resp = client.get("/api/v1/automation/automations?status=draft")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_activate_automation(self, client) -> None:
        automation_id = _create_automation(client)
        resp = client.post(
            f"/api/v1/automation/automations/{automation_id}/triggers",
            json={"automation_id": automation_id, "trigger_type": "manual"},
        )
        assert resp.status_code == 201
        resp = client.post(
            f"/api/v1/automation/automations/{automation_id}/actions",
            json={"automation_id": automation_id, "action_type": "notification"},
        )
        assert resp.status_code == 201
        resp = client.post(
            f"/api/v1/automation/automations/{automation_id}/activate",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active"

    def test_activate_automation_not_found(self, client) -> None:
        resp = client.post(f"/api/v1/automation/automations/{NOT_FOUND_ID}/activate")
        assert resp.status_code == 404

    def test_pause_automation(self, client) -> None:
        automation_id = _create_automation(client)
        resp = client.post(
            f"/api/v1/automation/automations/{automation_id}/triggers",
            json={"automation_id": automation_id, "trigger_type": "manual"},
        )
        assert resp.status_code == 201
        resp = client.post(
            f"/api/v1/automation/automations/{automation_id}/actions",
            json={"automation_id": automation_id, "action_type": "notification"},
        )
        assert resp.status_code == 201
        client.post(f"/api/v1/automation/automations/{automation_id}/activate")
        resp = client.post(f"/api/v1/automation/automations/{automation_id}/pause")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    def test_disable_automation(self, client) -> None:
        automation_id = _create_automation(client)
        resp = client.post(f"/api/v1/automation/automations/{automation_id}/disable")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disabled"

    def test_add_trigger(self, client) -> None:
        automation_id = _create_automation(client)
        resp = client.post(
            f"/api/v1/automation/automations/{automation_id}/triggers",
            json={"automation_id": automation_id, "trigger_type": "manual"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["trigger_type"] == "manual"

    def test_add_trigger_automation_not_found(self, client) -> None:
        resp = client.post(
            f"/api/v1/automation/automations/{NOT_FOUND_ID}/triggers",
            json={"automation_id": NOT_FOUND_ID, "trigger_type": "manual"},
        )
        assert resp.status_code == 404

    def test_enable_trigger(self, client) -> None:
        automation_id = _create_automation(client)
        resp = client.post(
            f"/api/v1/automation/automations/{automation_id}/triggers",
            json={"automation_id": automation_id, "trigger_type": "manual"},
        )
        trigger_id = resp.json()["trigger_id"]
        resp = client.post(f"/api/v1/automation/triggers/{trigger_id}/disable")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False
        resp = client.post(f"/api/v1/automation/triggers/{trigger_id}/enable")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    def test_enable_trigger_not_found(self, client) -> None:
        resp = client.post(f"/api/v1/automation/triggers/{NOT_FOUND_ID}/enable")
        assert resp.status_code == 404

    def test_disable_trigger(self, client) -> None:
        automation_id = _create_automation(client)
        resp = client.post(
            f"/api/v1/automation/automations/{automation_id}/triggers",
            json={"automation_id": automation_id, "trigger_type": "manual"},
        )
        trigger_id = resp.json()["trigger_id"]
        resp = client.post(f"/api/v1/automation/triggers/{trigger_id}/disable")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

    def test_get_trigger(self, client) -> None:
        automation_id = _create_automation(client)
        resp = client.post(
            f"/api/v1/automation/automations/{automation_id}/triggers",
            json={"automation_id": automation_id, "trigger_type": "scheduled", "expression": "0 0 * * *"},
        )
        trigger_id = resp.json()["trigger_id"]
        resp = client.get(f"/api/v1/automation/triggers/{trigger_id}")
        assert resp.status_code == 200
        assert resp.json()["trigger_type"] == "scheduled"

    def test_get_trigger_not_found(self, client) -> None:
        resp = client.get(f"/api/v1/automation/triggers/{NOT_FOUND_ID}")
        assert resp.status_code == 404

    def test_list_triggers(self, client) -> None:
        automation_id = _create_automation(client)
        client.post(
            f"/api/v1/automation/automations/{automation_id}/triggers",
            json={"automation_id": automation_id, "trigger_type": "manual"},
        )
        resp = client.get("/api/v1/automation/triggers")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_add_action(self, client) -> None:
        automation_id = _create_automation(client)
        resp = client.post(
            f"/api/v1/automation/automations/{automation_id}/actions",
            json={"automation_id": automation_id, "action_type": "notification"},
        )
        assert resp.status_code == 201
        assert resp.json()["action_type"] == "notification"

    def test_add_action_not_found(self, client) -> None:
        resp = client.post(
            f"/api/v1/automation/automations/{NOT_FOUND_ID}/actions",
            json={"automation_id": NOT_FOUND_ID, "action_type": "notification"},
        )
        assert resp.status_code == 404

    def test_start_execution(self, client) -> None:
        automation_id = _create_automation(client)
        client.post(
            f"/api/v1/automation/automations/{automation_id}/triggers",
            json={"automation_id": automation_id, "trigger_type": "manual"},
        )
        client.post(
            f"/api/v1/automation/automations/{automation_id}/actions",
            json={"automation_id": automation_id, "action_type": "notification"},
        )
        client.post(f"/api/v1/automation/automations/{automation_id}/activate")
        resp = client.post(
            f"/api/v1/automation/automations/{automation_id}/executions",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "running"
        assert "execution_id" in data

    def test_start_execution_not_found(self, client) -> None:
        resp = client.post(f"/api/v1/automation/automations/{NOT_FOUND_ID}/executions")
        assert resp.status_code == 404

    def test_complete_execution(self, client) -> None:
        automation_id = _create_automation(client)
        client.post(
            f"/api/v1/automation/automations/{automation_id}/triggers",
            json={"automation_id": automation_id, "trigger_type": "manual"},
        )
        client.post(
            f"/api/v1/automation/automations/{automation_id}/actions",
            json={"automation_id": automation_id, "action_type": "notification"},
        )
        client.post(f"/api/v1/automation/automations/{automation_id}/activate")
        resp = client.post(
            f"/api/v1/automation/automations/{automation_id}/executions",
        )
        execution_id = resp.json()["execution_id"]
        resp = client.post(
            f"/api/v1/automation/executions/{execution_id}/complete",
            json={"automation_id": automation_id, "execution_id": execution_id, "result": "success"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_fail_execution(self, client) -> None:
        automation_id = _create_automation(client)
        client.post(
            f"/api/v1/automation/automations/{automation_id}/triggers",
            json={"automation_id": automation_id, "trigger_type": "manual"},
        )
        client.post(
            f"/api/v1/automation/automations/{automation_id}/actions",
            json={"automation_id": automation_id, "action_type": "notification"},
        )
        client.post(f"/api/v1/automation/automations/{automation_id}/activate")
        resp = client.post(
            f"/api/v1/automation/automations/{automation_id}/executions",
        )
        execution_id = resp.json()["execution_id"]
        resp = client.post(
            f"/api/v1/automation/executions/{execution_id}/fail",
            json={"automation_id": automation_id, "execution_id": execution_id, "failure_reason": "error occurred"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_get_execution(self, client) -> None:
        automation_id = _create_automation(client)
        client.post(
            f"/api/v1/automation/automations/{automation_id}/triggers",
            json={"automation_id": automation_id, "trigger_type": "manual"},
        )
        client.post(
            f"/api/v1/automation/automations/{automation_id}/actions",
            json={"automation_id": automation_id, "action_type": "notification"},
        )
        client.post(f"/api/v1/automation/automations/{automation_id}/activate")
        resp = client.post(
            f"/api/v1/automation/automations/{automation_id}/executions",
        )
        execution_id = resp.json()["execution_id"]
        resp = client.get(f"/api/v1/automation/executions/{execution_id}")
        assert resp.status_code == 200
        assert resp.json()["execution_id"] == execution_id

    def test_get_execution_not_found(self, client) -> None:
        resp = client.get(f"/api/v1/automation/executions/{NOT_FOUND_ID}")
        assert resp.status_code == 404

    def test_list_executions(self, client) -> None:
        automation_id = _create_automation(client)
        client.post(
            f"/api/v1/automation/automations/{automation_id}/triggers",
            json={"automation_id": automation_id, "trigger_type": "manual"},
        )
        client.post(
            f"/api/v1/automation/automations/{automation_id}/actions",
            json={"automation_id": automation_id, "action_type": "notification"},
        )
        client.post(f"/api/v1/automation/automations/{automation_id}/activate")
        client.post(f"/api/v1/automation/automations/{automation_id}/executions")
        resp = client.get("/api/v1/automation/executions")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


class TestErrorMapping:
    def test_automation_not_found(self, client) -> None:
        resp = client.get(f"/api/v1/automation/automations/{NOT_FOUND_ID}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_trigger_not_found(self, client) -> None:
        resp = client.get(f"/api/v1/automation/triggers/{NOT_FOUND_ID}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_execution_not_found(self, client) -> None:
        resp = client.get(f"/api/v1/automation/executions/{NOT_FOUND_ID}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
