from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import orchestrator
from backend.core.database import get_db
from backend.orchestrator.adapters.outbound.models import Base

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)

for _table in Base.metadata.tables.values():
    _table.schema = None


@pytest.fixture
def session():
    e = create_engine(
        "sqlite://", echo=False, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=e)
    conn = e.connect()
    s = Session(bind=conn, autobegin=True)
    yield s
    s.close()
    conn.close()
    e.dispose()


@pytest.fixture
def client(session):
    def _override_get_db():
        yield session
        session.commit()

    app = FastAPI()
    app.include_router(orchestrator.router, prefix="/api/v1/orchestrator")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


def _create_orch(client, intent="test intent", goal="test goal"):
    return client.post(
        "/api/v1/orchestrator/orchestrations",
        json={"intent": intent, "goal": goal},
    )


def _create_wf(client, oid, goal="wf goal", mode="sequential"):
    return client.post(
        f"/api/v1/orchestrator/orchestrations/{oid}/workflows",
        json={"goal": goal, "mode": mode},
    )


# ===================================================================
# POST /orchestrations
# ===================================================================


class TestCreateOrchestration:
    def test_201_created(self, client):
        resp = _create_orch(client)
        assert resp.status_code == 201
        data = resp.json()
        assert "orchestration_id" in data
        assert data["status"] == "created"

    def test_422_empty_intent(self, client):
        resp = _create_orch(client, intent="")
        assert resp.status_code == 422

    def test_422_empty_goal(self, client):
        resp = _create_orch(client, goal="")
        assert resp.status_code == 422

    def test_422_missing_fields(self, client):
        resp = client.post(
            "/api/v1/orchestrator/orchestrations", json={}
        )
        assert resp.status_code == 422


# ===================================================================
# Orchestration lifecycle
# ===================================================================


class TestOrchestrationLifecycle:
    @pytest.fixture
    def oid(self, client):
        resp = _create_orch(client)
        return resp.json()["orchestration_id"]

    def test_start_planning_200(self, client, oid):
        resp = client.post(
            f"/api/v1/orchestrator/orchestrations/{oid}/planning"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "planning"

    def test_start_planning_404(self, client):
        resp = client.post(
            "/api/v1/orchestrator/orchestrations/00000000-0000-0000-0000-000000000000/planning"
        )
        assert resp.status_code == 404

    def test_start_research_200(self, client, oid):
        client.post(f"/api/v1/orchestrator/orchestrations/{oid}/planning")
        resp = client.post(
            f"/api/v1/orchestrator/orchestrations/{oid}/research"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "researching"

    def test_start_research_404(self, client):
        resp = client.post(
            "/api/v1/orchestrator/orchestrations/00000000-0000-0000-0000-000000000000/research"
        )
        assert resp.status_code == 404

    def test_start_execution_200(self, client, oid):
        client.post(f"/api/v1/orchestrator/orchestrations/{oid}/planning")
        client.post(f"/api/v1/orchestrator/orchestrations/{oid}/research")
        resp = client.post(
            f"/api/v1/orchestrator/orchestrations/{oid}/execution"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "executing"

    def test_start_execution_404(self, client):
        resp = client.post(
            "/api/v1/orchestrator/orchestrations/00000000-0000-0000-0000-000000000000/execution"
        )
        assert resp.status_code == 404

    def test_complete_200(self, client, oid):
        client.post(f"/api/v1/orchestrator/orchestrations/{oid}/planning")
        client.post(f"/api/v1/orchestrator/orchestrations/{oid}/research")
        client.post(f"/api/v1/orchestrator/orchestrations/{oid}/execution")
        resp = client.post(
            f"/api/v1/orchestrator/orchestrations/{oid}/complete"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_complete_404(self, client):
        resp = client.post(
            "/api/v1/orchestrator/orchestrations/00000000-0000-0000-0000-000000000000/complete"
        )
        assert resp.status_code == 404

    def test_complete_400_bad_transition(self, client, oid):
        resp = client.post(
            f"/api/v1/orchestrator/orchestrations/{oid}/complete"
        )
        assert resp.status_code == 400

    def test_fail_200(self, client, oid):
        client.post(f"/api/v1/orchestrator/orchestrations/{oid}/planning")
        resp = client.post(
            f"/api/v1/orchestrator/orchestrations/{oid}/fail",
            json={"failure_reason": "error"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_fail_404(self, client):
        resp = client.post(
            "/api/v1/orchestrator/orchestrations/00000000-0000-0000-0000-000000000000/fail",
            json={"failure_reason": "error"},
        )
        assert resp.status_code == 404

    def test_fail_400_bad_transition(self, client, oid):
        resp = client.post(
            f"/api/v1/orchestrator/orchestrations/{oid}/fail",
            json={"failure_reason": "error"},
        )
        assert resp.status_code == 400

    def test_cancel_200(self, client, oid):
        resp = client.post(
            f"/api/v1/orchestrator/orchestrations/{oid}/cancel"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_cancel_404(self, client):
        resp = client.post(
            "/api/v1/orchestrator/orchestrations/00000000-0000-0000-0000-000000000000/cancel"
        )
        assert resp.status_code == 404

    def test_double_cancel_400(self, client, oid):
        client.post(f"/api/v1/orchestrator/orchestrations/{oid}/cancel")
        resp = client.post(
            f"/api/v1/orchestrator/orchestrations/{oid}/cancel"
        )
        assert resp.status_code == 400


# ===================================================================
# GET /orchestrations
# ===================================================================


class TestGetOrchestration:
    def test_200(self, client):
        create_resp = _create_orch(client)
        oid = create_resp.json()["orchestration_id"]
        resp = client.get(
            f"/api/v1/orchestrator/orchestrations/{oid}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["orchestration_id"] == oid
        assert data["status"] == "created"

    def test_404(self, client):
        resp = client.get(
            "/api/v1/orchestrator/orchestrations/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404


class TestListOrchestrations:
    def test_empty(self, client):
        resp = client.get("/api/v1/orchestrator/orchestrations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_with_results(self, client):
        _create_orch(client)
        _create_orch(client)
        resp = client.get("/api/v1/orchestrator/orchestrations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_filter_by_status(self, client):
        _create_orch(client)
        resp = client.get(
            "/api/v1/orchestrator/orchestrations?status=created"
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


# ===================================================================
# Workflow routes
# ===================================================================


class TestCreateWorkflow:
    @pytest.fixture
    def oid(self, client):
        resp = _create_orch(client)
        return resp.json()["orchestration_id"]

    def test_201_created(self, client, oid):
        resp = _create_wf(client, oid)
        assert resp.status_code == 201
        data = resp.json()
        assert "workflow_id" in data
        assert data["status"] == "pending"

    def test_404_orch_not_found(self, client):
        resp = _create_wf(client, "00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_422_empty_goal(self, client, oid):
        resp = client.post(
            f"/api/v1/orchestrator/orchestrations/{oid}/workflows",
            json={"goal": ""},
        )
        assert resp.status_code == 422


class TestWorkflowLifecycle:
    @pytest.fixture
    def wid_with_step(self, client, request):
        o_resp = _create_orch(client)
        oid = o_resp.json()["orchestration_id"]
        w_resp = _create_wf(client, oid)
        wid = w_resp.json()["workflow_id"]
        client.post(
            f"/api/v1/orchestrator/workflows/{wid}/steps",
            json={"agent_role": "research", "execution_order": 0},
        )
        return wid

    def test_complete_400_not_started(self, client, wid_with_step):
        resp = client.post(
            f"/api/v1/orchestrator/workflows/{wid_with_step}/complete"
        )
        assert resp.status_code == 400

    def test_complete_404(self, client):
        resp = client.post(
            "/api/v1/orchestrator/workflows/00000000-0000-0000-0000-000000000000/complete"
        )
        assert resp.status_code == 404

    def test_fail_400_not_started(self, client, wid_with_step):
        resp = client.post(
            f"/api/v1/orchestrator/workflows/{wid_with_step}/fail",
            json={"failure_reason": "wf error"},
        )
        assert resp.status_code == 400

    def test_fail_404(self, client):
        resp = client.post(
            "/api/v1/orchestrator/workflows/00000000-0000-0000-0000-000000000000/fail",
            json={"failure_reason": "error"},
        )
        assert resp.status_code == 404


class TestGetWorkflow:
    def test_200(self, client):
        o_resp = _create_orch(client)
        oid = o_resp.json()["orchestration_id"]
        w_resp = _create_wf(client, oid)
        wid = w_resp.json()["workflow_id"]
        resp = client.get(
            f"/api/v1/orchestrator/workflows/{wid}"
        )
        assert resp.status_code == 200
        assert resp.json()["workflow_id"] == wid

    def test_404(self, client):
        resp = client.get(
            "/api/v1/orchestrator/workflows/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404


class TestListWorkflows:
    def test_empty(self, client):
        resp = client.get("/api/v1/orchestrator/workflows")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_with_results(self, client):
        o_resp = _create_orch(client)
        oid = o_resp.json()["orchestration_id"]
        _create_wf(client, oid)
        resp = client.get("/api/v1/orchestrator/workflows")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_by_orchestration_id(self, client):
        o_resp = _create_orch(client)
        oid = o_resp.json()["orchestration_id"]
        _create_wf(client, oid)
        resp = client.get(
            f"/api/v1/orchestrator/workflows?orchestration_id={oid}"
        )
        assert resp.status_code == 200


# ===================================================================
# Step routes
# ===================================================================


class TestAddStep:
    @pytest.fixture
    def wid(self, client):
        o_resp = _create_orch(client)
        oid = o_resp.json()["orchestration_id"]
        w_resp = _create_wf(client, oid)
        return w_resp.json()["workflow_id"]

    def test_201_created(self, client, wid):
        resp = client.post(
            f"/api/v1/orchestrator/workflows/{wid}/steps",
            json={"agent_role": "research", "execution_order": 0},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "step_id" in data
        assert data["status"] == "pending"

    def test_404_workflow_not_found(self, client):
        resp = client.post(
            "/api/v1/orchestrator/workflows/00000000-0000-0000-0000-000000000000/steps",
            json={"agent_role": "research", "execution_order": 0},
        )
        assert resp.status_code == 404

    def test_400_invalid_role(self, client, wid):
        resp = client.post(
            f"/api/v1/orchestrator/workflows/{wid}/steps",
            json={"agent_role": "invalid", "execution_order": 0},
        )
        assert resp.status_code == 400


class TestStepLifecycle:
    @pytest.fixture
    def sid(self, client):
        o_resp = _create_orch(client)
        oid = o_resp.json()["orchestration_id"]
        w_resp = _create_wf(client, oid)
        wid = w_resp.json()["workflow_id"]
        s_resp = client.post(
            f"/api/v1/orchestrator/workflows/{wid}/steps",
            json={"agent_role": "research", "execution_order": 0},
        )
        return s_resp.json()["step_id"]

    def test_start_200(self, client, sid):
        resp = client.post(
            f"/api/v1/orchestrator/steps/{sid}/start"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_start_404(self, client):
        resp = client.post(
            "/api/v1/orchestrator/steps/00000000-0000-0000-0000-000000000000/start"
        )
        assert resp.status_code == 404

    def test_start_400_already_running(self, client, sid):
        client.post(f"/api/v1/orchestrator/steps/{sid}/start")
        resp = client.post(
            f"/api/v1/orchestrator/steps/{sid}/start"
        )
        assert resp.status_code == 400

    def test_complete_200(self, client, sid):
        client.post(f"/api/v1/orchestrator/steps/{sid}/start")
        resp = client.post(
            f"/api/v1/orchestrator/steps/{sid}/complete",
            json={"result": "done"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_complete_404(self, client):
        resp = client.post(
            "/api/v1/orchestrator/steps/00000000-0000-0000-0000-000000000000/complete",
            json={"result": "done"},
        )
        assert resp.status_code == 404

    def test_complete_400_not_started(self, client, sid):
        resp = client.post(
            f"/api/v1/orchestrator/steps/{sid}/complete",
            json={"result": "done"},
        )
        assert resp.status_code == 400

    def test_fail_200(self, client, sid):
        client.post(f"/api/v1/orchestrator/steps/{sid}/start")
        resp = client.post(
            f"/api/v1/orchestrator/steps/{sid}/fail",
            json={"failure_reason": "step error"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_fail_404(self, client):
        resp = client.post(
            "/api/v1/orchestrator/steps/00000000-0000-0000-0000-000000000000/fail",
            json={"failure_reason": "error"},
        )
        assert resp.status_code == 404

    def test_fail_400_not_started(self, client, sid):
        resp = client.post(
            f"/api/v1/orchestrator/steps/{sid}/fail",
            json={"failure_reason": "error"},
        )
        assert resp.status_code == 400

    def test_get_step_200(self, client, sid):
        resp = client.get(
            f"/api/v1/orchestrator/steps/{sid}"
        )
        assert resp.status_code == 200
        assert resp.json()["step_id"] == sid

    def test_get_step_404(self, client):
        resp = client.get(
            "/api/v1/orchestrator/steps/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404
