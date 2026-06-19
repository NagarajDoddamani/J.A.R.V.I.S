from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.api.endpoints import automation as automation_router
from backend.automation.adapters.outbound.mapper import (
    AutomationMapperImpl,
    AutomationOutboxMapperImpl,
    TriggerMapperImpl,
)
from backend.automation.adapters.outbound.models import Base, AutomationOutboxModel
from backend.automation.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyAutomationExecutionRepository,
    SqlAlchemyAutomationOutboxAdapter,
    SqlAlchemyAutomationRepository,
    SqlAlchemyTriggerRepository,
)
from backend.automation.domain.model import (
    ActionAdded,
    AutomationActivated,
    AutomationCreated,
    AutomationDisabled,
    AutomationExecutionCompleted,
    AutomationExecutionFailed,
    AutomationExecutionStarted,
    AutomationId,
    AutomationPaused,
    TriggerAdded,
    TriggerDisabled,
    TriggerEnabled,
    TriggerId,
    WorkflowExecutionId,
)
from backend.automation.nats import (
    publish_automation_outbox_events,
)
from backend.core.database import get_db

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)
NOT_FOUND_ID = "00000000-0000-0000-0000-000000000000"

for _table in Base.metadata.tables.values():
    _table.schema = None


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite://", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    return e


@pytest.fixture
def session(engine):
    conn = engine.connect()
    transaction = conn.begin()
    s = Session(bind=conn)
    yield s
    s.close()
    transaction.rollback()
    conn.close()


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


@pytest.fixture
def mock_js():
    js = AsyncMock()
    js.publish = AsyncMock()
    return js


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
    app.include_router(automation_router.router, prefix="/api/v1/automation")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_automation(client, name: str = "Test Automation", description: str = "Test Description", execution_mode: str = "once") -> str:
    resp = client.post(
        "/api/v1/automation/automations",
        json={"name": name, "description": description, "execution_mode": execution_mode},
    )
    assert resp.status_code == 201
    return resp.json()["automation_id"]


def _add_trigger(client, automation_id: str, trigger_type: str = "manual", expression: str | None = None) -> str:
    body = {"automation_id": automation_id, "trigger_type": trigger_type}
    if expression:
        body["expression"] = expression
    resp = client.post(f"/api/v1/automation/automations/{automation_id}/triggers", json=body)
    assert resp.status_code == 201
    return resp.json()["trigger_id"]


def _add_action(client, automation_id: str, action_type: str = "notification") -> str:
    resp = client.post(
        f"/api/v1/automation/automations/{automation_id}/actions",
        json={"automation_id": automation_id, "action_type": action_type},
    )
    assert resp.status_code == 201
    return resp.json().get("action_type", action_type)


def _activate(client, automation_id: str) -> None:
    resp = client.post(f"/api/v1/automation/automations/{automation_id}/activate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


def _start_execution(client, automation_id: str) -> str:
    resp = client.post(f"/api/v1/automation/automations/{automation_id}/executions")
    assert resp.status_code == 201
    return resp.json()["execution_id"]


def _full_automation(client) -> str:
    aid = _create_automation(client)
    _add_trigger(client, aid)
    _add_action(client, aid)
    _activate(client, aid)
    return aid


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------

class TestAutomationLifecycle:
    def test_full_lifecycle_via_http(self, client) -> None:
        aid = _create_automation(client)

        get_resp = client.get(f"/api/v1/automation/automations/{aid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "draft"

        _add_trigger(client, aid)
        _add_action(client, aid)
        _activate(client, aid)

        get_resp = client.get(f"/api/v1/automation/automations/{aid}")
        assert get_resp.json()["status"] == "active"

        eid = _start_execution(client, aid)
        get_resp = client.get(f"/api/v1/automation/automations/{aid}")
        assert get_resp.json()["status"] == "running"

        resp = client.post(
            f"/api/v1/automation/executions/{eid}/complete",
            json={"automation_id": aid, "execution_id": eid, "result": "done"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_failure_lifecycle_via_http(self, client) -> None:
        aid = _full_automation(client)
        eid = _start_execution(client, aid)
        resp = client.post(
            f"/api/v1/automation/executions/{eid}/fail",
            json={"automation_id": aid, "execution_id": eid, "failure_reason": "something broke"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_pause_reactivate_lifecycle(self, client) -> None:
        aid = _full_automation(client)
        resp = client.post(f"/api/v1/automation/automations/{aid}/pause")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

        resp = client.post(f"/api/v1/automation/automations/{aid}/activate")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

        eid = _start_execution(client, aid)
        resp = client.post(
            f"/api/v1/automation/executions/{eid}/complete",
            json={"automation_id": aid, "execution_id": eid, "result": "ok"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_disable_from_draft(self, client) -> None:
        aid = _create_automation(client)
        resp = client.post(f"/api/v1/automation/automations/{aid}/disable")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disabled"

    def test_list_automations_filters(self, client) -> None:
        a1 = _create_automation(client, "Draft1")
        a2 = _create_automation(client, "Draft2")
        resp = client.get("/api/v1/automation/automations")
        assert resp.json()["total"] >= 2

        resp = client.get("/api/v1/automation/automations?status=draft")
        assert resp.json()["total"] >= 2

        client.post(f"/api/v1/automation/automations/{a1}/disable")
        resp = client.get("/api/v1/automation/automations?status=disabled")
        assert resp.json()["total"] >= 1


class TestExecutionLifecycle:
    def test_complete_execution_persists_result(self, client) -> None:
        aid = _full_automation(client)
        eid = _start_execution(client, aid)
        client.post(
            f"/api/v1/automation/executions/{eid}/complete",
            json={"automation_id": aid, "execution_id": eid, "result": "success"},
        )
        resp = client.get(f"/api/v1/automation/executions/{eid}")
        assert resp.json()["status"] == "completed"
        assert resp.json()["result"] == "success"

    def test_fail_execution_persists_reason(self, client) -> None:
        aid = _full_automation(client)
        eid = _start_execution(client, aid)
        client.post(
            f"/api/v1/automation/executions/{eid}/fail",
            json={"automation_id": aid, "execution_id": eid, "failure_reason": "error occurred"},
        )
        resp = client.get(f"/api/v1/automation/executions/{eid}")
        assert resp.json()["status"] == "failed"
        assert resp.json()["failure_reason"] == "error occurred"

    def test_list_executions_by_status(self, client) -> None:
        aid = _full_automation(client)
        eid1 = _start_execution(client, aid)
        client.post(
            f"/api/v1/automation/executions/{eid1}/complete",
            json={"automation_id": aid, "execution_id": eid1, "result": "ok"},
        )
        resp = client.get("/api/v1/automation/executions?status=completed")
        assert resp.json()["total"] >= 1

        resp = client.get("/api/v1/automation/executions?status=running")
        assert resp.json()["total"] == 0

    def test_list_executions_by_automation_id(self, client) -> None:
        aid = _full_automation(client)
        _start_execution(client, aid)
        resp = client.get(f"/api/v1/automation/executions?automation_id={aid}")
        assert resp.json()["total"] >= 1

    def test_get_execution_not_found(self, client) -> None:
        resp = client.get(f"/api/v1/automation/executions/{NOT_FOUND_ID}")
        assert resp.status_code == 404

    def test_execution_list_empty(self, client) -> None:
        resp = client.get("/api/v1/automation/executions")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestTriggerLifecycle:
    def test_add_scheduled_trigger(self, client) -> None:
        aid = _create_automation(client)
        tid = _add_trigger(client, aid, "scheduled", "0 8 * * *")
        resp = client.get(f"/api/v1/automation/triggers/{tid}")
        assert resp.json()["trigger_type"] == "scheduled"
        assert resp.json()["expression"] == "0 8 * * *"

    def test_enable_disable_trigger(self, client) -> None:
        aid = _create_automation(client)
        tid = _add_trigger(client, aid)
        resp = client.post(f"/api/v1/automation/triggers/{tid}/disable")
        assert resp.json()["enabled"] is False
        resp = client.post(f"/api/v1/automation/triggers/{tid}/enable")
        assert resp.json()["enabled"] is True

    def test_list_triggers_by_type(self, client) -> None:
        aid = _create_automation(client)
        _add_trigger(client, aid, "manual")
        _add_trigger(client, aid, "scheduled", "0 0 * * *")
        resp = client.get("/api/v1/automation/triggers?trigger_type=manual")
        assert resp.json()["total"] >= 1

    def test_list_triggers_by_enabled(self, client) -> None:
        aid = _create_automation(client)
        tid = _add_trigger(client, aid)
        resp = client.get("/api/v1/automation/triggers?enabled=true")
        assert resp.json()["total"] >= 1

        client.post(f"/api/v1/automation/triggers/{tid}/disable")
        resp = client.get("/api/v1/automation/triggers?enabled=false")
        assert resp.json()["total"] >= 1

    def test_get_trigger_not_found(self, client) -> None:
        resp = client.get(f"/api/v1/automation/triggers/{NOT_FOUND_ID}")
        assert resp.status_code == 404


class TestErrorTransitions:
    def test_activate_without_triggers_returns_400(self, client) -> None:
        aid = _create_automation(client)
        _add_action(client, aid)
        resp = client.post(f"/api/v1/automation/automations/{aid}/activate")
        assert resp.status_code == 400

    def test_activate_without_actions_returns_400(self, client) -> None:
        aid = _create_automation(client)
        _add_trigger(client, aid)
        resp = client.post(f"/api/v1/automation/automations/{aid}/activate")
        assert resp.status_code == 400

    def test_start_execution_on_paused_returns_400(self, client) -> None:
        aid = _full_automation(client)
        client.post(f"/api/v1/automation/automations/{aid}/pause")
        resp = client.post(f"/api/v1/automation/automations/{aid}/executions")
        assert resp.status_code == 400

    def test_start_execution_on_draft_returns_400(self, client) -> None:
        aid = _create_automation(client)
        resp = client.post(f"/api/v1/automation/automations/{aid}/executions")
        assert resp.status_code == 400

    def test_double_complete_returns_400(self, client) -> None:
        aid = _full_automation(client)
        eid = _start_execution(client, aid)
        client.post(
            f"/api/v1/automation/executions/{eid}/complete",
            json={"automation_id": aid, "execution_id": eid, "result": "ok"},
        )
        resp = client.post(
            f"/api/v1/automation/executions/{eid}/complete",
            json={"automation_id": aid, "execution_id": eid, "result": "again"},
        )
        assert resp.status_code == 400

    def test_double_fail_returns_400(self, client) -> None:
        aid = _full_automation(client)
        eid = _start_execution(client, aid)
        client.post(
            f"/api/v1/automation/executions/{eid}/fail",
            json={"automation_id": aid, "execution_id": eid, "failure_reason": "err"},
        )
        resp = client.post(
            f"/api/v1/automation/executions/{eid}/fail",
            json={"automation_id": aid, "execution_id": eid, "failure_reason": "again"},
        )
        assert resp.status_code == 400

    def test_double_disable_returns_400(self, client) -> None:
        aid = _create_automation(client)
        client.post(f"/api/v1/automation/automations/{aid}/disable")
        resp = client.post(f"/api/v1/automation/automations/{aid}/disable")
        assert resp.status_code == 400

    def test_double_activate_returns_400(self, client) -> None:
        aid = _full_automation(client)
        resp = client.post(f"/api/v1/automation/automations/{aid}/activate")
        assert resp.status_code == 400


class TestRepositoryRoundtrip:
    def test_automation_fields_roundtrip(self, session, automation_repo) -> None:
        from backend.automation.domain.factory import AutomationFactory
        from backend.automation.domain.model import AutomationId, ExecutionMode

        automation, _ = AutomationFactory.create_automation(
            name="Roundtrip",
            description="Test",
            execution_mode=ExecutionMode.RECURRING,
        )
        automation_repo.save(automation)
        session.commit()

        loaded = automation_repo.find_by_id(automation.automation_id)
        assert loaded is not None
        assert str(loaded.name) == "Roundtrip"
        assert str(loaded.description) == "Test"
        assert loaded.execution_mode == ExecutionMode.RECURRING
        assert loaded.status.value == "draft"

    def test_automation_with_triggers_roundtrip(self, session, automation_repo, trigger_repo) -> None:
        from backend.automation.domain.factory import AutomationFactory
        from backend.automation.domain.model import ExecutionMode, TriggerType

        automation, _ = AutomationFactory.create_automation(
            name="WithTriggers",
            description="Triggers test",
            execution_mode=ExecutionMode.ONCE,
        )
        trigger, _ = AutomationFactory.add_trigger(
            automation=automation,
            trigger_type=TriggerType.MANUAL,
        )
        automation_repo.save(automation)
        trigger_repo.save(trigger, automation_id=str(automation.automation_id))
        session.commit()

        loaded = automation_repo.find_by_id(automation.automation_id)
        assert loaded is not None
        assert len(loaded.triggers) >= 1

    def test_find_by_status(self, session, automation_repo) -> None:
        from backend.automation.domain.factory import AutomationFactory
        from backend.automation.domain.model import AutomationStatus, ExecutionMode

        a1, _ = AutomationFactory.create_automation(
            name="A1",
            description="test",
            execution_mode=ExecutionMode.ONCE,
        )
        automation_repo.save(a1)
        session.commit()

        results = automation_repo.find_by_status(AutomationStatus.DRAFT)
        assert any(a.automation_id == a1.automation_id for a in results)

    def test_count(self, session, automation_repo) -> None:
        from backend.automation.domain.factory import AutomationFactory
        from backend.automation.domain.model import ExecutionMode

        n = automation_repo.count()
        a2, _ = AutomationFactory.create_automation(
            name="CountTest2",
            description="test",
            execution_mode=ExecutionMode.ONCE,
        )
        automation_repo.save(a2)
        session.commit()
        assert automation_repo.count() >= n + 1


class TestOutboxLifecycle:
    def test_append_then_fetch(self, session, outbox) -> None:
        event = AutomationCreated(
            automation_id=AutomationId(),
            name="test",
            description="desc",
            execution_mode="once",
            occurred_at=NOW,
        )
        outbox.append(event)
        session.commit()

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], AutomationCreated)

    def test_mark_published(self, session, outbox) -> None:
        aid = AutomationId()
        event = AutomationCreated(
            automation_id=aid,
            name="test",
            description="desc",
            execution_mode="once",
            occurred_at=NOW,
        )
        outbox.append(event)
        session.commit()

        unpublished = outbox.fetch_unpublished()
        outbox.mark_published(str(unpublished[0].event_id))
        session.commit()

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_mark_published_idempotent(self, session, outbox) -> None:
        aid = AutomationId()
        event = AutomationCreated(
            automation_id=aid,
            name="test",
            description="desc",
            execution_mode="once",
            occurred_at=NOW,
        )
        outbox.append(event)
        session.commit()

        fetched = outbox.fetch_unpublished()
        outbox.mark_published(str(fetched[0].event_id))
        outbox.mark_published(str(fetched[0].event_id))
        session.commit()

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_fetch_respects_limit(self, session, outbox) -> None:
        for i in range(5):
            outbox.append(AutomationCreated(
                automation_id=AutomationId(),
                name=f"test-{i}",
                description="desc",
                execution_mode="once",
                occurred_at=NOW,
            ))
        session.commit()

        results = outbox.fetch_unpublished(limit=3)
        assert len(results) == 3


class TestFifoOrdering:
    def test_mixed_events_fifo(self, session, outbox) -> None:
        aid = AutomationId()
        tid = TriggerId()
        events = [
            AutomationCreated(aid, "n", "d", "once", NOW),
            TriggerAdded(tid, aid, "manual", "", NOW),
            AutomationActivated(aid, NOW),
        ]
        for e in events:
            outbox.append(e)
        session.commit()

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 3
        assert isinstance(unpublished[0], AutomationCreated)
        assert isinstance(unpublished[1], TriggerAdded)
        assert isinstance(unpublished[2], AutomationActivated)


class TestQueryFiltering:
    def test_get_automation_not_found(self, client) -> None:
        resp = client.get(f"/api/v1/automation/automations/{NOT_FOUND_ID}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_automation_by_id(self, client) -> None:
        aid = _create_automation(client)
        resp = client.get(f"/api/v1/automation/automations/{aid}")
        assert resp.status_code == 200
        assert resp.json()["automation_id"] == aid

    def test_list_automations_by_execution_mode(self, client) -> None:
        _create_automation(client, "Once", execution_mode="once")
        _create_automation(client, "Recurring", execution_mode="recurring")
        resp = client.get("/api/v1/automation/automations?execution_mode=once")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_triggers_by_type(self, client) -> None:
        aid = _create_automation(client)
        _add_trigger(client, aid, "manual")
        resp = client.get("/api/v1/automation/triggers?trigger_type=manual")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


class TestEventCoverage:
    EVENT_FACTORIES = [
        ("AutomationCreated", lambda: AutomationCreated(AutomationId(), "n", "d", "once", NOW)),
        ("AutomationActivated", lambda: AutomationActivated(AutomationId(), NOW)),
        ("AutomationPaused", lambda: AutomationPaused(AutomationId(), NOW)),
        ("AutomationDisabled", lambda: AutomationDisabled(AutomationId(), NOW)),
        ("AutomationExecutionStarted", lambda: AutomationExecutionStarted(AutomationId(), WorkflowExecutionId(), NOW)),
        ("AutomationExecutionCompleted", lambda: AutomationExecutionCompleted(AutomationId(), WorkflowExecutionId(), "ok", NOW)),
        ("AutomationExecutionFailed", lambda: AutomationExecutionFailed(AutomationId(), WorkflowExecutionId(), "err", NOW)),
        ("TriggerAdded", lambda: TriggerAdded(TriggerId(), AutomationId(), "manual", "", NOW)),
        ("TriggerEnabled", lambda: TriggerEnabled(TriggerId(), AutomationId(), NOW)),
        ("TriggerDisabled", lambda: TriggerDisabled(TriggerId(), AutomationId(), NOW)),
        ("ActionAdded", lambda: ActionAdded(AutomationId(), "notification", NOW)),
    ]

    @pytest.mark.parametrize("name,factory", EVENT_FACTORIES, ids=[e[0] for e in EVENT_FACTORIES])
    def test_event_type_append_and_fetch(self, session, outbox, name, factory) -> None:
        event = factory()
        outbox.append(event)
        session.commit()
        unpublished = outbox.fetch_unpublished()
        found = any(type(e).__name__ == name for e in unpublished)
        assert found, f"Event type {name} not found in outbox"

    def test_all_11_events_roundtrip(self, session, outbox) -> None:
        aid = AutomationId()
        wid = WorkflowExecutionId()
        tid = TriggerId()
        events = [
            AutomationCreated(aid, "n", "d", "once", NOW),
            AutomationActivated(aid, NOW),
            AutomationPaused(aid, NOW),
            AutomationDisabled(aid, NOW),
            AutomationExecutionStarted(aid, wid, NOW),
            AutomationExecutionCompleted(aid, wid, "ok", NOW),
            AutomationExecutionFailed(aid, wid, "err", NOW),
            TriggerAdded(tid, aid, "manual", "", NOW),
            TriggerEnabled(tid, aid, NOW),
            TriggerDisabled(tid, aid, NOW),
            ActionAdded(aid, "notification", NOW),
        ]
        for e in events:
            outbox.append(e)
        session.commit()

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 11

    def test_event_field_correctness(self, session, outbox) -> None:
        aid = AutomationId()
        event = AutomationCreated(aid, "FieldTest", "FieldDesc", "recurring", NOW)
        outbox.append(event)
        session.commit()

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        loaded = unpublished[0]
        assert loaded.name == "FieldTest"
        assert loaded.description == "FieldDesc"
        assert loaded.execution_mode == "recurring"


# ---------------------------------------------------------------------------
# API + Outbox integration tests
# ---------------------------------------------------------------------------

class TestApiOutboxPipeline:
    def test_create_automation_creates_outbox_event(self, client, session, outbox) -> None:
        client.post(
            "/api/v1/automation/automations",
            json={"name": "Outbox Test", "description": "desc", "execution_mode": "once"},
        )
        session.commit()
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, AutomationCreated) for e in events)

    def test_activate_creates_outbox_event(self, client, session, outbox) -> None:
        aid = _create_automation(client)
        _add_trigger(client, aid)
        _add_action(client, aid)
        session.commit()
        client.post(f"/api/v1/automation/automations/{aid}/activate")
        session.commit()
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, AutomationActivated) for e in events)

    def test_pause_creates_outbox_event(self, client, session, outbox) -> None:
        aid = _full_automation(client)
        session.commit()
        client.post(f"/api/v1/automation/automations/{aid}/pause")
        session.commit()
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, AutomationPaused) for e in events)

    def test_disable_creates_outbox_event(self, client, session, outbox) -> None:
        aid = _create_automation(client)
        session.commit()
        client.post(f"/api/v1/automation/automations/{aid}/disable")
        session.commit()
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, AutomationDisabled) for e in events)

    def test_add_trigger_creates_outbox_event(self, client, session, outbox) -> None:
        aid = _create_automation(client)
        session.commit()
        client.post(
            f"/api/v1/automation/automations/{aid}/triggers",
            json={"automation_id": aid, "trigger_type": "manual"},
        )
        session.commit()
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, TriggerAdded) for e in events)

    def test_start_execution_creates_outbox_event(self, client, session, outbox) -> None:
        aid = _full_automation(client)
        session.commit()
        client.post(f"/api/v1/automation/automations/{aid}/executions")
        session.commit()
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, AutomationExecutionStarted) for e in events)

    def test_complete_execution_creates_outbox_event(self, client, session, outbox) -> None:
        aid = _full_automation(client)
        eid = _start_execution(client, aid)
        session.commit()
        client.post(
            f"/api/v1/automation/executions/{eid}/complete",
            json={"automation_id": aid, "execution_id": eid, "result": "success"},
        )
        session.commit()
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, AutomationExecutionCompleted) for e in events)

    def test_fail_execution_creates_outbox_event(self, client, session, outbox) -> None:
        aid = _full_automation(client)
        eid = _start_execution(client, aid)
        session.commit()
        client.post(
            f"/api/v1/automation/executions/{eid}/fail",
            json={"automation_id": aid, "execution_id": eid, "failure_reason": "error"},
        )
        session.commit()
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, AutomationExecutionFailed) for e in events)


class TestFullNatsPipeline:
    @pytest.mark.asyncio
    async def test_api_to_outbox_to_nats(self, client, session, outbox, mock_js) -> None:
        client.post(
            "/api/v1/automation/automations",
            json={"name": "NATS Pipeline", "description": "desc", "execution_mode": "once"},
        )
        session.commit()

        await publish_automation_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

        assert mock_js.publish.call_count >= 1

    @pytest.mark.asyncio
    async def test_full_lifecycle_produces_nats_events(self, client, session, outbox, mock_js) -> None:
        aid = _full_automation(client)
        eid = _start_execution(client, aid)
        session.commit()

        await publish_automation_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=2,
        )

        assert mock_js.publish.call_count >= 3

        subjects = [call[0][0] for call in mock_js.publish.call_args_list]
        assert any("automation_created" in s for s in subjects)
        assert any("trigger_added" in s for s in subjects)
        assert any("action_added" in s for s in subjects)
        assert any("automation_activated" in s for s in subjects)
        assert any("automation_execution_started" in s for s in subjects)

    @pytest.mark.asyncio
    async def test_nats_envelope_structure(self, client, session, outbox, mock_js) -> None:
        client.post(
            "/api/v1/automation/automations",
            json={"name": "Envelope", "description": "Envelope desc", "execution_mode": "once"},
        )
        session.commit()

        await publish_automation_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

        args, _ = mock_js.publish.call_args
        payload = json.loads(args[1].decode())
        assert payload["producer"] == "automation"
        assert payload["kind"] == "event"
        assert "event_id" in payload
        assert "event_type" in payload
        assert "aggregate_id" in payload
        assert "occurred_at" in payload
        assert payload["name"] == "Envelope"
        assert payload["description"] == "Envelope desc"
        assert payload["execution_mode"] == "once"


# ---------------------------------------------------------------------------
# REST Contract tests
# ---------------------------------------------------------------------------

class TestRESTContract:
    def test_create_automation_201(self, client) -> None:
        resp = client.post(
            "/api/v1/automation/automations",
            json={"name": "Contract", "description": "desc", "execution_mode": "once"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "automation_id" in data
        assert data["status"] == "draft"

    def test_create_automation_empty_name_returns_400(self, client) -> None:
        resp = client.post(
            "/api/v1/automation/automations",
            json={"name": "", "description": "desc", "execution_mode": "once"},
        )
        assert resp.status_code == 400

    def test_get_automation_404(self, client) -> None:
        resp = client.get(f"/api/v1/automation/automations/{NOT_FOUND_ID}")
        assert resp.status_code == 404

    def test_list_automations_200(self, client) -> None:
        resp = client.get("/api/v1/automation/automations")
        assert resp.status_code == 200
        assert "total" in resp.json()
        assert "automations" in resp.json()

    def test_lifecycle_error_mappings(self, client) -> None:
        resp = client.post(f"/api/v1/automation/automations/{NOT_FOUND_ID}/activate")
        assert resp.status_code == 404
        resp = client.post(f"/api/v1/automation/automations/{NOT_FOUND_ID}/pause")
        assert resp.status_code == 404
        resp = client.post(f"/api/v1/automation/automations/{NOT_FOUND_ID}/disable")
        assert resp.status_code == 404

    def test_trigger_error_mappings(self, client) -> None:
        resp = client.post(f"/api/v1/automation/triggers/{NOT_FOUND_ID}/enable")
        assert resp.status_code == 404
        resp = client.post(f"/api/v1/automation/triggers/{NOT_FOUND_ID}/disable")
        assert resp.status_code == 404

    def test_execution_error_mappings(self, client) -> None:
        resp = client.post(f"/api/v1/automation/executions/{NOT_FOUND_ID}/complete",
                           json={"automation_id": NOT_FOUND_ID, "execution_id": NOT_FOUND_ID, "result": "ok"})
        assert resp.status_code == 404
        resp = client.post(f"/api/v1/automation/executions/{NOT_FOUND_ID}/fail",
                           json={"automation_id": NOT_FOUND_ID, "execution_id": NOT_FOUND_ID, "failure_reason": "err"})
        assert resp.status_code == 404
