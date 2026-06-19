from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.api.endpoints import policy
from backend.policy.adapters.outbound.clock import SystemClockAdapter
from backend.policy.adapters.outbound.models import Base
from backend.policy.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyPolicyEvaluationRepository,
    SqlAlchemyPolicyOutboxAdapter,
    SqlAlchemyPolicyRepository,
    SqlAlchemyPolicyRuleRepository,
)
from backend.core.database import get_db

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)

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
    app.include_router(policy.router, prefix="/api/v1/policy")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def policy_repo(session):
    return SqlAlchemyPolicyRepository(session)


@pytest.fixture
def rule_repo(session):
    return SqlAlchemyPolicyRuleRepository(session)


@pytest.fixture
def evaluation_repo(session):
    return SqlAlchemyPolicyEvaluationRepository(session)


@pytest.fixture
def outbox(session):
    return SqlAlchemyPolicyOutboxAdapter(session)


@pytest.fixture
def clock():
    return SystemClockAdapter()


def _create_policy(client, name="Test Policy", status_code=201):
    return client.post(
        "/api/v1/policy/",
        json={
            "name": name,
            "description": "A test policy",
            "priority": "medium",
            "scope": "global",
            "version": "1.0.0",
        },
    )


def _add_rule(client, policy_id, condition="true", action="allow"):
    return client.post(
        f"/api/v1/policy/{policy_id}/rules",
        json={"policy_id": policy_id, "condition": condition, "action": action, "priority": 0},
    )


# ===================================================================
# Policy CRUD
# ===================================================================


class TestCreatePolicy:
    def test_create_policy(self, client) -> None:
        resp = _create_policy(client)
        assert resp.status_code == 201
        data = resp.json()
        assert "policy_id" in data
        assert data["status"] == "draft"
        assert data["name"] == "Test Policy"

    def test_create_policy_invalid_body(self, client) -> None:
        resp = client.post("/api/v1/policy/", json={})
        assert resp.status_code == 422


class TestGetPolicy:
    def test_get_policy(self, client) -> None:
        created = _create_policy(client).json()
        resp = client.get(f"/api/v1/policy/{created['policy_id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["policy_id"] == created["policy_id"]

    def test_get_policy_not_found(self, client) -> None:
        resp = client.get(f"/api/v1/policy/{uuid4()}")
        assert resp.status_code == 404


class TestListPolicies:
    def test_list_policies(self, client) -> None:
        _create_policy(client)
        _create_policy(client, name="Policy 2")
        resp = client.get("/api/v1/policy/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_list_policies_filter_status(self, client) -> None:
        _create_policy(client)
        resp = client.get("/api/v1/policy/?status=draft")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_list_policies_no_results(self, client) -> None:
        resp = client.get("/api/v1/policy/?status=active")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_policies_filter_priority(self, client) -> None:
        _create_policy(client)
        resp = client.get("/api/v1/policy/?priority=medium")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1


class TestActivatePolicy:
    def test_activate_policy(self, client) -> None:
        created = _create_policy(client).json()
        pid = created["policy_id"]
        _add_rule(client, pid)
        resp = client.post(
            f"/api/v1/policy/{pid}/activate"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active"

    def test_activate_policy_not_found(self, client) -> None:
        resp = client.post(f"/api/v1/policy/{uuid4()}/activate")
        assert resp.status_code == 404


class TestDisablePolicy:
    def test_disable_policy(self, client) -> None:
        created = _create_policy(client).json()
        pid = created["policy_id"]
        _add_rule(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        resp = client.post(f"/api/v1/policy/{pid}/disable")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disabled"


class TestArchivePolicy:
    def test_archive_policy(self, client) -> None:
        created = _create_policy(client).json()
        pid = created["policy_id"]
        _add_rule(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        client.post(f"/api/v1/policy/{pid}/disable")
        resp = client.post(f"/api/v1/policy/{pid}/archive")
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"


# ===================================================================
# Rules
# ===================================================================


class TestAddRule:
    def test_add_rule(self, client) -> None:
        created = _create_policy(client).json()
        pid = created["policy_id"]
        resp = client.post(
            f"/api/v1/policy/{pid}/rules",
            json={"policy_id": pid, "condition": "true", "action": "allow", "priority": 10},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["policy_id"] == pid
        assert data["enabled"] is True

    def test_add_rule_policy_not_found(self, client) -> None:
        resp = client.post(
            f"/api/v1/policy/{uuid4()}/rules",
            json={"policy_id": str(uuid4()), "condition": "true", "action": "allow"},
        )
        assert resp.status_code == 404


class TestRemoveRule:
    def test_remove_rule(self, client) -> None:
        created = _create_policy(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule(client, pid)
        rid = rule_resp.json()["rule_id"]
        resp = client.delete(f"/api/v1/policy/rules/{rid}?policy_id={pid}")
        assert resp.status_code == 200


class TestEnableRule:
    def test_enable_rule(self, client) -> None:
        created = _create_policy(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule(client, pid)
        rid = rule_resp.json()["rule_id"]
        client.post(f"/api/v1/policy/rules/{rid}/disable")
        resp = client.post(f"/api/v1/policy/rules/{rid}/enable")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True


class TestDisableRule:
    def test_disable_rule(self, client) -> None:
        created = _create_policy(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule(client, pid)
        rid = rule_resp.json()["rule_id"]
        resp = client.post(f"/api/v1/policy/rules/{rid}/disable")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False


class TestGetRule:
    def test_get_rule(self, client) -> None:
        created = _create_policy(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule(client, pid, condition="x > 1")
        rid = rule_resp.json()["rule_id"]
        resp = client.get(f"/api/v1/policy/rules/{rid}")
        assert resp.status_code == 200
        assert resp.json()["condition"] == "x > 1"

    def test_get_rule_not_found(self, client) -> None:
        resp = client.get(f"/api/v1/policy/rules/{uuid4()}")
        assert resp.status_code == 404


class TestListRules:
    def test_list_rules(self, client) -> None:
        created = _create_policy(client).json()
        pid = created["policy_id"]
        _add_rule(client, pid)
        resp = client.get("/api/v1/policy/rules")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


# ===================================================================
# Evaluations
# ===================================================================


class TestStartEvaluation:
    def test_start_evaluation(self, client) -> None:
        created = _create_policy(client).json()
        pid = created["policy_id"]
        _add_rule(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        resp = client.post(f"/api/v1/policy/{pid}/evaluations/start")
        assert resp.status_code == 201
        assert resp.json()["status"] == "evaluating"

    def test_start_evaluation_policy_not_found(self, client) -> None:
        resp = client.post(f"/api/v1/policy/{uuid4()}/evaluations/start")
        assert resp.status_code == 404


class TestCompleteEvaluation:
    def test_complete_evaluation(self, client) -> None:
        created = _create_policy(client).json()
        pid = created["policy_id"]
        _add_rule(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        eval_resp = client.post(f"/api/v1/policy/{pid}/evaluations/start")
        eid = eval_resp.json()["evaluation_id"]
        resp = client.post(
            f"/api/v1/policy/evaluations/{eid}/complete",
            json={"policy_id": pid, "evaluation_id": eid, "decision": "allow", "result": "ok"},
        )
        assert resp.status_code == 200
        assert resp.json()["decision"] == "allow"


class TestFailEvaluation:
    def test_fail_evaluation(self, client) -> None:
        created = _create_policy(client).json()
        pid = created["policy_id"]
        _add_rule(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        eval_resp = client.post(f"/api/v1/policy/{pid}/evaluations/start")
        eid = eval_resp.json()["evaluation_id"]
        resp = client.post(
            f"/api/v1/policy/evaluations/{eid}/fail",
            json={"policy_id": pid, "evaluation_id": eid, "failure_reason": "error"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"


class TestGetEvaluation:
    def test_get_evaluation(self, client) -> None:
        created = _create_policy(client).json()
        pid = created["policy_id"]
        _add_rule(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        eval_resp = client.post(f"/api/v1/policy/{pid}/evaluations/start")
        eid = eval_resp.json()["evaluation_id"]
        resp = client.get(f"/api/v1/policy/evaluations/{eid}")
        assert resp.status_code == 200
        assert resp.json()["evaluation_id"] == eid

    def test_get_evaluation_not_found(self, client) -> None:
        resp = client.get(f"/api/v1/policy/evaluations/{uuid4()}")
        assert resp.status_code == 404


class TestListEvaluations:
    def test_list_evaluations(self, client) -> None:
        created = _create_policy(client).json()
        pid = created["policy_id"]
        _add_rule(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        client.post(f"/api/v1/policy/{pid}/evaluations/start")
        resp = client.get("/api/v1/policy/evaluations")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_evaluations_filter_status(self, client) -> None:
        created = _create_policy(client).json()
        pid = created["policy_id"]
        _add_rule(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        resp = client.get("/api/v1/policy/evaluations?status=pending")
        assert resp.status_code == 200
