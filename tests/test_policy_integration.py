from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.api.endpoints import policy as policy_router
from backend.core.database import get_db
from backend.policy.adapters.outbound.clock import SystemClockAdapter
from backend.policy.adapters.outbound.mapper import (
    PolicyEvaluationMapperImpl,
    PolicyMapperImpl,
    PolicyOutboxDomainEvent,
    PolicyOutboxMapperImpl,
    PolicyRuleMapperImpl,
)
from backend.policy.adapters.outbound.models import Base, PolicyOutboxModel
from backend.policy.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyPolicyEvaluationRepository,
    SqlAlchemyPolicyOutboxAdapter,
    SqlAlchemyPolicyRepository,
    SqlAlchemyPolicyRuleRepository,
)
from backend.policy.domain.model import (
    EvaluationId,
    Policy,
    PolicyActivated,
    PolicyArchived,
    PolicyCreated,
    PolicyDisabled,
    PolicyEvaluation,
    PolicyEvaluationCompleted,
    PolicyEvaluationFailed,
    PolicyEvaluationStarted,
    PolicyId,
    PolicyPriority,
    PolicyRule,
    PolicyRuleAdded,
    PolicyRuleDisabled,
    PolicyRuleEnabled,
    PolicyRuleId,
    PolicyRuleRemoved,
    PolicyScope,
    PolicyStatus,
)
from backend.policy.nats import (
    _EVENT_TYPE_MAP,
    _NATS_SUBJECT_MAP,
    publish_policy_outbox_events,
)

for _table in Base.metadata.tables.values():
    _table.schema = None

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)


# ===================================================================
# Fixtures
# ===================================================================


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
    app.include_router(policy_router.router, prefix="/api/v1/policy")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


# ===================================================================
# Helpers
# ===================================================================


def _create_policy_dto():
    return type("PolicyDTO", (), {
        "policy_id": str(uuid4()),
        "name": "Integration Policy",
        "description": "Created during integration test",
        "status": "draft",
        "priority": "medium",
        "scope": "global",
        "version": "1.0.0",
        "created_at": NOW,
        "updated_at": None,
    })()


def _make_policy(policy_id=None, status=PolicyStatus.DRAFT):
    pid = policy_id or PolicyId()
    return Policy(
        policy_id=pid,
        status=status,
        priority=PolicyPriority.MEDIUM,
        scope=PolicyScope.GLOBAL,
    )


def _make_rule(rule_id=None, enabled=True):
    rid = rule_id or PolicyRuleId()
    return PolicyRule(rule_id=rid, enabled=enabled, priority=0)


def _create_policy_via_api(client, name="Integration Policy"):
    return client.post(
        "/api/v1/policy/",
        json={
            "name": name,
            "description": "Integration test policy",
            "priority": "medium",
            "scope": "global",
            "version": "1.0.0",
        },
    )


def _add_rule_via_api(client, policy_id):
    return client.post(
        f"/api/v1/policy/{policy_id}/rules",
        json={
            "policy_id": policy_id,
            "condition": "true",
            "action": "allow",
            "priority": 0,
        },
    )


# ===================================================================
# 1. Policy Lifecycle — Create → Activate → Disable → Archive
# ===================================================================


class TestPolicyLifecycle:
    def test_create_policy(self, client) -> None:
        resp = _create_policy_via_api(client)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "draft"

    def test_create_activate(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        resp = client.post(f"/api/v1/policy/{pid}/activate")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_create_activate_disable(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        resp = client.post(f"/api/v1/policy/{pid}/disable")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disabled"

    def test_create_activate_disable_archive(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        client.post(f"/api/v1/policy/{pid}/disable")
        resp = client.post(f"/api/v1/policy/{pid}/archive")
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"

    def test_full_lifecycle_status_sequence(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        assert created["status"] == "draft"
        _add_rule_via_api(client, pid)
        r1 = client.post(f"/api/v1/policy/{pid}/activate")
        assert r1.json()["status"] == "active"
        r2 = client.post(f"/api/v1/policy/{pid}/disable")
        assert r2.json()["status"] == "disabled"
        r3 = client.post(f"/api/v1/policy/{pid}/archive")
        assert r3.json()["status"] == "archived"

    def test_activate_without_rule_returns_400(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        resp = client.post(f"/api/v1/policy/{pid}/activate")
        assert resp.status_code == 400
        assert "rule" in resp.json()["detail"].lower()

    def test_disable_draft_returns_400(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        resp = client.post(f"/api/v1/policy/{pid}/disable")
        assert resp.status_code == 400

    def test_archive_allowed_from_active(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        resp = client.post(f"/api/v1/policy/{pid}/archive")
        assert resp.status_code == 200

    def test_re_activate_after_disable(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        client.post(f"/api/v1/policy/{pid}/disable")
        resp = client.post(f"/api/v1/policy/{pid}/activate")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_archive_allowed_from_draft(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        resp = client.post(f"/api/v1/policy/{pid}/archive")
        assert resp.status_code == 200


# ===================================================================
# 2. Rule Lifecycle — Add → Enable → Disable → Remove
# ===================================================================


class TestRuleLifecycle:
    def test_add_rule(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        resp = _add_rule_via_api(client, pid)
        assert resp.status_code == 201
        assert resp.json()["enabled"] is True

    def test_add_multiple_rules(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(
            f"/api/v1/policy/{pid}/rules",
            json={"policy_id": pid, "condition": "false", "action": "deny", "priority": 1},
        )
        resp = client.get("/api/v1/policy/rules")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2

    def test_add_rule_not_modifiable_when_active(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        resp = _add_rule_via_api(client, pid)
        assert resp.status_code == 400

    def test_disable_rule(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule_via_api(client, pid)
        rid = rule_resp.json()["rule_id"]
        resp = client.post(f"/api/v1/policy/rules/{rid}/disable")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

    def test_enable_rule(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule_via_api(client, pid)
        rid = rule_resp.json()["rule_id"]
        client.post(f"/api/v1/policy/rules/{rid}/disable")
        resp = client.post(f"/api/v1/policy/rules/{rid}/enable")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    def test_disable_already_disabled_returns_400(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule_via_api(client, pid)
        rid = rule_resp.json()["rule_id"]
        client.post(f"/api/v1/policy/rules/{rid}/disable")
        resp = client.post(f"/api/v1/policy/rules/{rid}/disable")
        assert resp.status_code == 400

    def test_enable_already_enabled_returns_400(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule_via_api(client, pid)
        rid = rule_resp.json()["rule_id"]
        resp = client.post(f"/api/v1/policy/rules/{rid}/enable")
        assert resp.status_code == 400

    def test_remove_rule(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule_via_api(client, pid)
        rid = rule_resp.json()["rule_id"]
        resp = client.delete(f"/api/v1/policy/rules/{rid}?policy_id={pid}")
        assert resp.status_code == 200

    def test_remove_rule_not_modifiable_when_active(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule_via_api(client, pid)
        rid = rule_resp.json()["rule_id"]
        client.post(f"/api/v1/policy/{pid}/activate")
        resp = client.delete(f"/api/v1/policy/rules/{rid}?policy_id={pid}")
        assert resp.status_code == 400

    def test_remove_nonexistent_rule_returns_404(self, client) -> None:
        resp = client.delete(f"/api/v1/policy/rules/{uuid4()}?policy_id={uuid4()}")
        assert resp.status_code == 404

    def test_get_rule(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule_via_api(client, pid)
        rid = rule_resp.json()["rule_id"]
        resp = client.get(f"/api/v1/policy/rules/{rid}")
        assert resp.status_code == 200
        assert resp.json()["rule_id"] == rid

    def test_get_nonexistent_rule_returns_404(self, client) -> None:
        resp = client.get(f"/api/v1/policy/rules/{uuid4()}")
        assert resp.status_code == 404

    def test_list_rules(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        resp = client.get("/api/v1/policy/rules")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


# ===================================================================
# 3. Evaluation Lifecycle — Start → Complete / Fail
# ===================================================================


class TestEvaluationLifecycle:
    def test_start_evaluation(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        resp = client.post(f"/api/v1/policy/{pid}/evaluations/start")
        assert resp.status_code == 201
        assert resp.json()["status"] == "evaluating"

    def test_start_then_complete(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        eval_resp = client.post(f"/api/v1/policy/{pid}/evaluations/start")
        eid = eval_resp.json()["evaluation_id"]
        resp = client.post(
            f"/api/v1/policy/evaluations/{eid}/complete",
            json={"policy_id": pid, "evaluation_id": eid, "decision": "allow", "result": "ok"},
        )
        assert resp.status_code == 200
        assert resp.json()["decision"] == "allow"

    def test_start_then_fail(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        eval_resp = client.post(f"/api/v1/policy/{pid}/evaluations/start")
        eid = eval_resp.json()["evaluation_id"]
        resp = client.post(
            f"/api/v1/policy/evaluations/{eid}/fail",
            json={"policy_id": pid, "evaluation_id": eid, "failure_reason": "timeout"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_get_evaluation(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        eval_resp = client.post(f"/api/v1/policy/{pid}/evaluations/start")
        eid = eval_resp.json()["evaluation_id"]
        resp = client.get(f"/api/v1/policy/evaluations/{eid}")
        assert resp.status_code == 200
        assert resp.json()["evaluation_id"] == eid

    def test_get_nonexistent_evaluation_returns_404(self, client) -> None:
        resp = client.get(f"/api/v1/policy/evaluations/{uuid4()}")
        assert resp.status_code == 404

    def test_list_evaluations(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        client.post(f"/api/v1/policy/{pid}/evaluations/start")
        resp = client.get("/api/v1/policy/evaluations")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_start_evaluation_allowed_for_draft(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        resp = client.post(f"/api/v1/policy/{pid}/evaluations/start")
        assert resp.status_code == 201

    def test_complete_nonexistent_evaluation_returns_404(self, client) -> None:
        resp = client.post(
            f"/api/v1/policy/evaluations/{uuid4()}/complete",
            json={"policy_id": str(uuid4()), "evaluation_id": str(uuid4()), "decision": "allow", "result": "ok"},
        )
        assert resp.status_code == 404

    def test_fail_nonexistent_evaluation_returns_404(self, client) -> None:
        resp = client.post(
            f"/api/v1/policy/evaluations/{uuid4()}/fail",
            json={"policy_id": str(uuid4()), "evaluation_id": str(uuid4()), "failure_reason": "error"},
        )
        assert resp.status_code == 404

    def test_list_evaluations_filter_by_status(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        resp = client.get("/api/v1/policy/evaluations?status=pending")
        assert resp.status_code == 200

    def test_complete_invalid_decision_returns_422(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        eval_resp = client.post(f"/api/v1/policy/{pid}/evaluations/start")
        eid = eval_resp.json()["evaluation_id"]
        resp = client.post(
            f"/api/v1/policy/evaluations/{eid}/complete",
            json={"policy_id": pid, "evaluation_id": eid, "decision": "invalid", "result": "ok"},
        )
        assert resp.status_code == 422


# ===================================================================
# 4. Repository Roundtrip
# ===================================================================


class TestRepositoryRoundtrip:
    def test_policy_roundtrip(self, policy_repo, session) -> None:
        pid = PolicyId()
        policy = _make_policy(policy_id=pid)
        policy_repo.save(policy)
        session.flush()
        loaded = policy_repo.find_by_id(pid)
        assert loaded is not None
        assert loaded.policy_id == pid
        assert loaded.status == PolicyStatus.DRAFT

    def test_policy_update_roundtrip(self, policy_repo, session) -> None:
        pid = PolicyId()
        policy = _make_policy(policy_id=pid)
        policy_repo.save(policy)
        session.flush()
        policy._status = PolicyStatus.ACTIVE
        policy_repo.save(policy)
        session.flush()
        loaded = policy_repo.find_by_id(pid)
        assert loaded is not None
        assert loaded.status == PolicyStatus.ACTIVE

    def test_rule_roundtrip(self, rule_repo, session) -> None:
        rid = PolicyRuleId()
        rule = _make_rule(rule_id=rid)
        rule_repo.save(rule, policy_id=str(uuid4()))
        session.flush()
        loaded = rule_repo.find_by_id(rid)
        assert loaded is not None
        assert loaded.rule_id == rid

    def test_rule_disable_roundtrip(self, rule_repo, session) -> None:
        rid = PolicyRuleId()
        rule = _make_rule(rule_id=rid, enabled=True)
        rule_repo.save(rule, policy_id=str(uuid4()))
        session.flush()
        loaded = rule_repo.find_by_id(rid)
        assert loaded is not None
        assert loaded.enabled is True
        loaded._enabled = False
        rule_repo.save(loaded)
        session.flush()
        reloaded = rule_repo.find_by_id(rid)
        assert reloaded is not None
        assert reloaded.enabled is False

    def test_evaluation_roundtrip(self, evaluation_repo, session) -> None:
        from backend.policy.domain.model import PolicyEvaluation as PE
        from backend.policy.domain.model import EvaluationId as EID
        eid = EID()
        ev = PE(policy_id=PolicyId(), evaluation_id=eid)
        ev.start()
        evaluation_repo.save(ev)
        session.flush()
        loaded = evaluation_repo.find_by_id(eid)
        assert loaded is not None
        assert loaded.evaluation_id == eid

    def test_policy_count(self, policy_repo, session) -> None:
        before = policy_repo.count()
        policy_repo.save(_make_policy())
        session.flush()
        assert policy_repo.count() == before + 1

    def test_rule_count(self, rule_repo, session) -> None:
        before = rule_repo.count()
        pid = PolicyId()
        rule = _make_rule()
        rule_repo.save(rule, policy_id=str(pid))
        session.flush()
        assert rule_repo.count() == before + 1

    def test_evaluation_count(self, evaluation_repo, session) -> None:
        before = evaluation_repo.count()
        ev = PolicyEvaluation(policy_id=PolicyId())
        ev.start()
        evaluation_repo.save(ev)
        session.flush()
        assert evaluation_repo.count() == before + 1

    def test_find_policy_by_status(self, policy_repo, session) -> None:
        policy_repo.save(_make_policy(status=PolicyStatus.DRAFT))
        policy_repo.save(_make_policy(status=PolicyStatus.ACTIVE))
        session.flush()
        drafts = policy_repo.find_by_status(PolicyStatus.DRAFT)
        assert len(drafts) >= 1
        assert all(p.status == PolicyStatus.DRAFT for p in drafts)

    def test_find_policy_by_priority(self, policy_repo, session) -> None:
        p1 = _make_policy()
        p1._priority = PolicyPriority.HIGH
        policy_repo.save(p1)
        session.flush()
        results = policy_repo.find_by_priority(PolicyPriority.HIGH)
        assert len(results) >= 1

    def test_find_policy_by_scope(self, policy_repo, session) -> None:
        p1 = _make_policy()
        p1._scope = PolicyScope.AGENT
        policy_repo.save(p1)
        session.flush()
        results = policy_repo.find_by_scope(PolicyScope.AGENT)
        assert len(results) >= 1

    def test_find_all_policies(self, policy_repo, session) -> None:
        before = len(policy_repo.find_all())
        policy_repo.save(_make_policy())
        session.flush()
        assert len(policy_repo.find_all()) == before + 1

    def test_find_rule_by_policy_id(self, rule_repo, session) -> None:
        pid = str(uuid4())
        rule = _make_rule()
        rule_repo.save(rule, policy_id=pid)
        session.flush()
        result = rule_repo.find_by_policy_id(PolicyId(value=UUID(pid)))
        assert len(result) == 1

    def test_find_enabled_rules(self, rule_repo, session) -> None:
        r1 = _make_rule(enabled=True)
        r2 = _make_rule(enabled=False)
        rule_repo.save(r1, policy_id=str(uuid4()))
        rule_repo.save(r2, policy_id=str(uuid4()))
        session.flush()
        enabled = rule_repo.find_enabled()
        assert all(r.enabled for r in enabled)

    def test_find_evaluation_by_policy_id(self, evaluation_repo, session) -> None:
        pid = PolicyId()
        ev = PolicyEvaluation(policy_id=pid)
        ev.start()
        evaluation_repo.save(ev)
        session.flush()
        results = evaluation_repo.find_by_policy_id(pid)
        assert len(results) == 1

    def test_find_evaluation_by_status(self, evaluation_repo, session) -> None:
        from backend.policy.domain.model import PolicyEvaluationStatus
        ev = PolicyEvaluation(policy_id=PolicyId())
        ev.start()
        evaluation_repo.save(ev)
        session.flush()
        results = evaluation_repo.find_by_status(PolicyEvaluationStatus.EVALUATING)
        assert len(results) == 1


# ===================================================================
# 5. Outbox Lifecycle
# ===================================================================


class TestOutboxLifecycle:
    def test_append_event(self, outbox, session) -> None:
        from backend.policy.domain.model import PolicyCreated
        event = PolicyCreated(
            policy_id=PolicyId(), name="test", description="d", priority="medium", scope="global", version="1.0.0", occurred_at=NOW,
        )
        outbox.append(event)
        session.flush()
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1

    def test_fetch_unpublished_empty_initially(self, outbox) -> None:
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_mark_published(self, outbox, session) -> None:
        event = PolicyCreated(
            policy_id=PolicyId(), name="test", description="d", priority="medium", scope="global", version="1.0.0", occurred_at=NOW,
        )
        outbox.append(event)
        session.flush()
        entries = outbox.fetch_unpublished()
        event_id = str(entries[0].event_id)
        outbox.mark_published(event_id)
        session.flush()
        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 0

    def test_append_multiple_events(self, outbox, session) -> None:
        outbox.append(PolicyCreated(
            policy_id=PolicyId(), name="test", description="d", priority="medium", scope="global", version="1.0.0", occurred_at=NOW,
        ))
        outbox.append(PolicyActivated(policy_id=PolicyId(), occurred_at=NOW))
        session.flush()
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 2

    def test_partial_mark_published(self, outbox, session) -> None:
        outbox.append(PolicyCreated(
            policy_id=PolicyId(), name="test", description="d", priority="medium", scope="global", version="1.0.0", occurred_at=NOW,
        ))
        outbox.append(PolicyDisabled(policy_id=PolicyId(), occurred_at=NOW))
        session.flush()
        entries = outbox.fetch_unpublished()
        outbox.mark_published(str(entries[0].event_id))
        session.flush()
        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 1

    def test_outbox_with_domain_event_through_mapper(self, outbox, session) -> None:
        mapper = PolicyOutboxMapperImpl()
        event = PolicyRuleAdded(
            policy_id=PolicyId(),
            rule_id=PolicyRuleId(),
            condition="true",
            action="allow",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        import json
        model = PolicyOutboxModel(
            message_id=dto.event_id,
            subject=dto.event_type,
            aggregate_id=dto.aggregate_id,
            created_at=dto.occurred_at,
            payload=json.loads(dto.payload) if dto.payload else {},
            published_at=None,
        )
        session.add(model)
        session.flush()
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        restored = unpublished[0]
        assert type(restored) is PolicyRuleAdded
        assert restored.policy_id == event.policy_id
        assert restored.rule_id == event.rule_id
        assert restored.condition == event.condition
        assert restored.action == event.action

    def test_fifo_ordering(self, outbox, session) -> None:
        for i in range(5):
            e = PolicyCreated(
                policy_id=PolicyId(), name="test", description="d", priority="medium", scope="global", version="1.0.0", occurred_at=NOW,
            )
            outbox.append(e)
        session.flush()
        entries = outbox.fetch_unpublished()
        assert len(entries) == 5
        assert all(type(e) is PolicyCreated for e in entries)


# ===================================================================
# 6. FIFO Ordering — All 11 Events
# ===================================================================


class TestFIFOOrdering:
    def test_outbox_preserves_insertion_order(self, outbox, session) -> None:
        events = [
            PolicyCreated(policy_id=PolicyId(), name="test", description="d", priority="medium", scope="global", version="1.0.0", occurred_at=NOW),
            PolicyActivated(policy_id=PolicyId(), occurred_at=NOW),
            PolicyDisabled(policy_id=PolicyId(), occurred_at=NOW),
            PolicyArchived(policy_id=PolicyId(), occurred_at=NOW),
        ]
        for e in events:
            outbox.append(e)
        session.flush()
        entries = outbox.fetch_unpublished()
        assert len(entries) == 4
        for i, entry in enumerate(entries):
            assert type(entry) is type(events[i])

    def test_fifo_across_rule_events(self, outbox, session) -> None:
        events = [
            PolicyRuleAdded(policy_id=PolicyId(), rule_id=PolicyRuleId(), condition="true", action="allow", occurred_at=NOW),
            PolicyRuleRemoved(policy_id=PolicyId(), rule_id=PolicyRuleId(), occurred_at=NOW),
            PolicyRuleEnabled(policy_id=PolicyId(), rule_id=PolicyRuleId(), occurred_at=NOW),
            PolicyRuleDisabled(policy_id=PolicyId(), rule_id=PolicyRuleId(), occurred_at=NOW),
        ]
        for e in events:
            outbox.append(e)
        session.flush()
        entries = outbox.fetch_unpublished()
        assert len(entries) == 4
        for i, entry in enumerate(entries):
            assert type(entry) is type(events[i])

    def test_fifo_across_evaluation_events(self, outbox, session) -> None:
        events = [
            PolicyEvaluationStarted(policy_id=PolicyId(), evaluation_id=EvaluationId(), occurred_at=NOW),
            PolicyEvaluationCompleted(
                policy_id=PolicyId(), evaluation_id=EvaluationId(), decision="allow", result="ok", occurred_at=NOW
            ),
            PolicyEvaluationFailed(
                policy_id=PolicyId(), evaluation_id=EvaluationId(), failure_reason="err", occurred_at=NOW
            ),
        ]
        for e in events:
            outbox.append(e)
        session.flush()
        entries = outbox.fetch_unpublished()
        assert len(entries) == 3
        for i, entry in enumerate(entries):
            assert type(entry) is type(events[i])

    def test_fifo_all_11_events(self, outbox, session) -> None:
        events: list[PolicyOutboxDomainEvent] = [
            PolicyCreated(policy_id=PolicyId(), name="test", description="d", priority="medium", scope="global", version="1.0.0", occurred_at=NOW),
            PolicyActivated(policy_id=PolicyId(), occurred_at=NOW),
            PolicyDisabled(policy_id=PolicyId(), occurred_at=NOW),
            PolicyArchived(policy_id=PolicyId(), occurred_at=NOW),
            PolicyRuleAdded(policy_id=PolicyId(), rule_id=PolicyRuleId(), condition="true", action="allow", occurred_at=NOW),
            PolicyRuleRemoved(policy_id=PolicyId(), rule_id=PolicyRuleId(), occurred_at=NOW),
            PolicyRuleEnabled(policy_id=PolicyId(), rule_id=PolicyRuleId(), occurred_at=NOW),
            PolicyRuleDisabled(policy_id=PolicyId(), rule_id=PolicyRuleId(), occurred_at=NOW),
            PolicyEvaluationStarted(policy_id=PolicyId(), evaluation_id=EvaluationId(), occurred_at=NOW),
            PolicyEvaluationCompleted(
                policy_id=PolicyId(), evaluation_id=EvaluationId(), decision="allow", result="ok", occurred_at=NOW
            ),
            PolicyEvaluationFailed(
                policy_id=PolicyId(), evaluation_id=EvaluationId(), failure_reason="err", occurred_at=NOW
            ),
        ]
        for e in events:
            outbox.append(e)
        session.flush()
        entries = outbox.fetch_unpublished()
        assert len(entries) == 11
        for i, entry in enumerate(entries):
            assert type(entry) is type(events[i])


# ===================================================================
# 7. REST Contract Coverage — All 17 Routes
# ===================================================================


class TestRESTContractCoverage:
    def test_post_policies_201(self, client) -> None:
        resp = _create_policy_via_api(client)
        assert resp.status_code == 201

    def test_get_policies_200(self, client) -> None:
        resp = client.get("/api/v1/policy/")
        assert resp.status_code == 200

    def test_get_policies_invalid_status_returns_422(self, client) -> None:
        resp = client.get("/api/v1/policy/?status=nonexistent")
        assert resp.status_code == 422

    def test_get_policy_by_id_200(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        resp = client.get(f"/api/v1/policy/{pid}")
        assert resp.status_code == 200
        assert resp.json()["policy_id"] == pid

    def test_get_policy_by_id_404(self, client) -> None:
        resp = client.get(f"/api/v1/policy/{uuid4()}")
        assert resp.status_code == 404

    def test_activate_policy_200(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        resp = client.post(f"/api/v1/policy/{pid}/activate")
        assert resp.status_code == 200

    def test_activate_policy_404(self, client) -> None:
        resp = client.post(f"/api/v1/policy/{uuid4()}/activate")
        assert resp.status_code == 404

    def test_disable_policy_200(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        resp = client.post(f"/api/v1/policy/{pid}/disable")
        assert resp.status_code == 200

    def test_archive_policy_200(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        client.post(f"/api/v1/policy/{pid}/disable")
        resp = client.post(f"/api/v1/policy/{pid}/archive")
        assert resp.status_code == 200

    def test_add_rule_201(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        resp = _add_rule_via_api(client, pid)
        assert resp.status_code == 201

    def test_add_rule_404(self, client) -> None:
        resp = client.post(
            f"/api/v1/policy/{uuid4()}/rules",
            json={"policy_id": str(uuid4()), "condition": "true", "action": "allow"},
        )
        assert resp.status_code == 404

    def test_remove_rule_200(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule_via_api(client, pid)
        rid = rule_resp.json()["rule_id"]
        resp = client.delete(f"/api/v1/policy/rules/{rid}?policy_id={pid}")
        assert resp.status_code == 200

    def test_enable_rule_200(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule_via_api(client, pid)
        rid = rule_resp.json()["rule_id"]
        client.post(f"/api/v1/policy/rules/{rid}/disable")
        resp = client.post(f"/api/v1/policy/rules/{rid}/enable")
        assert resp.status_code == 200

    def test_disable_rule_200(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule_via_api(client, pid)
        rid = rule_resp.json()["rule_id"]
        resp = client.post(f"/api/v1/policy/rules/{rid}/disable")
        assert resp.status_code == 200

    def test_get_rule_200(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule_via_api(client, pid)
        rid = rule_resp.json()["rule_id"]
        resp = client.get(f"/api/v1/policy/rules/{rid}")
        assert resp.status_code == 200

    def test_get_rule_404(self, client) -> None:
        resp = client.get(f"/api/v1/policy/rules/{uuid4()}")
        assert resp.status_code == 404

    def test_list_rules_200(self, client) -> None:
        resp = client.get("/api/v1/policy/rules")
        assert resp.status_code == 200

    def test_start_evaluation_201(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        resp = client.post(f"/api/v1/policy/{pid}/evaluations/start")
        assert resp.status_code == 201

    def test_complete_evaluation_200(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        eval_resp = client.post(f"/api/v1/policy/{pid}/evaluations/start")
        eid = eval_resp.json()["evaluation_id"]
        resp = client.post(
            f"/api/v1/policy/evaluations/{eid}/complete",
            json={"policy_id": pid, "evaluation_id": eid, "decision": "allow", "result": "ok"},
        )
        assert resp.status_code == 200

    def test_fail_evaluation_200(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        eval_resp = client.post(f"/api/v1/policy/{pid}/evaluations/start")
        eid = eval_resp.json()["evaluation_id"]
        resp = client.post(
            f"/api/v1/policy/evaluations/{eid}/fail",
            json={"policy_id": pid, "evaluation_id": eid, "failure_reason": "err"},
        )
        assert resp.status_code == 200

    def test_get_evaluation_200(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        eval_resp = client.post(f"/api/v1/policy/{pid}/evaluations/start")
        eid = eval_resp.json()["evaluation_id"]
        resp = client.get(f"/api/v1/policy/evaluations/{eid}")
        assert resp.status_code == 200

    def test_list_evaluations_200(self, client) -> None:
        resp = client.get("/api/v1/policy/evaluations")
        assert resp.status_code == 200

    def test_list_evaluations_filter_policy_id(self, client) -> None:
        resp = client.get(f"/api/v1/policy/evaluations?policy_id={uuid4()}")
        assert resp.status_code == 200


# ===================================================================
# 8. Query Filtering
# ===================================================================


class TestQueryFiltering:
    def test_filter_policies_by_status(self, client) -> None:
        _create_policy_via_api(client)
        resp = client.get("/api/v1/policy/?status=draft")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_policies_by_priority(self, client) -> None:
        _create_policy_via_api(client)
        resp = client.get("/api/v1/policy/?priority=medium")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_policies_by_scope(self, client) -> None:
        _create_policy_via_api(client)
        resp = client.get("/api/v1/policy/?scope=global")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_policies_combined(self, client) -> None:
        _create_policy_via_api(client)
        resp = client.get("/api/v1/policy/?status=draft&priority=medium")
        assert resp.status_code == 200

    def test_filter_rules_by_policy_id(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        resp = client.get(f"/api/v1/policy/rules?policy_id={pid}")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_rules_by_enabled(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        resp = client.get("/api/v1/policy/rules?enabled=true")
        assert resp.status_code == 200

    def test_filter_rules_by_priority(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        resp = client.get("/api/v1/policy/rules?priority=0")
        assert resp.status_code == 200

    def test_filter_evaluations_by_policy_id(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        client.post(f"/api/v1/policy/{pid}/evaluations/start")
        resp = client.get(f"/api/v1/policy/evaluations?policy_id={pid}")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_evaluations_by_status(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        resp = client.get("/api/v1/policy/evaluations?status=pending")
        assert resp.status_code == 200


# ===================================================================
# 9. Event Coverage — All 11 Domain Events
# ===================================================================


class TestEventCoverage:
    def test_policy_created_event_type(self) -> None:
        assert PolicyCreated in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[PolicyCreated] == "policy_created"

    def test_policy_activated_event_type(self) -> None:
        assert PolicyActivated in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[PolicyActivated] == "policy_activated"

    def test_policy_disabled_event_type(self) -> None:
        assert PolicyDisabled in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[PolicyDisabled] == "policy_disabled"

    def test_policy_archived_event_type(self) -> None:
        assert PolicyArchived in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[PolicyArchived] == "policy_archived"

    def test_rule_added_event_type(self) -> None:
        assert PolicyRuleAdded in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[PolicyRuleAdded] == "rule_added"

    def test_rule_removed_event_type(self) -> None:
        assert PolicyRuleRemoved in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[PolicyRuleRemoved] == "rule_removed"

    def test_rule_enabled_event_type(self) -> None:
        assert PolicyRuleEnabled in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[PolicyRuleEnabled] == "rule_enabled"

    def test_rule_disabled_event_type(self) -> None:
        assert PolicyRuleDisabled in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[PolicyRuleDisabled] == "rule_disabled"

    def test_evaluation_started_event_type(self) -> None:
        assert PolicyEvaluationStarted in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[PolicyEvaluationStarted] == "evaluation_started"

    def test_evaluation_completed_event_type(self) -> None:
        assert PolicyEvaluationCompleted in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[PolicyEvaluationCompleted] == "evaluation_completed"

    def test_evaluation_failed_event_type(self) -> None:
        assert PolicyEvaluationFailed in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[PolicyEvaluationFailed] == "evaluation_failed"

    def test_all_11_events_have_nats_subject(self) -> None:
        assert len(_NATS_SUBJECT_MAP) == 11

    def test_all_events_have_event_type_in_outbox_mapper(self) -> None:
        from backend.policy.adapters.outbound.mapper import _EVENT_TYPE_MAP
        assert len(_EVENT_TYPE_MAP) == 11


# ===================================================================
# 10. Cross-Entity Validation
# ===================================================================


class TestCrossEntityValidation:
    def test_rules_belong_to_policy(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        rule_resp = _add_rule_via_api(client, pid)
        assert rule_resp.json()["policy_id"] == pid

    def test_evaluations_belong_to_policy(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        eval_resp = client.post(f"/api/v1/policy/{pid}/evaluations/start")
        assert eval_resp.json()["policy_id"] == pid

    def test_rules_isolation_between_policies(self, client) -> None:
        p1 = _create_policy_via_api(client, name="Policy A").json()
        p2 = _create_policy_via_api(client, name="Policy B").json()
        _add_rule_via_api(client, p1["policy_id"])
        resp = client.get(f"/api/v1/policy/rules?policy_id={p1['policy_id']}")
        assert resp.json()["total"] == 1
        resp2 = client.get(f"/api/v1/policy/rules?policy_id={p2['policy_id']}")
        assert resp2.json()["total"] == 0

    def test_archived_policy_immutable(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        _add_rule_via_api(client, pid)
        client.post(f"/api/v1/policy/{pid}/activate")
        client.post(f"/api/v1/policy/{pid}/disable")
        client.post(f"/api/v1/policy/{pid}/archive")
        resp = client.post(f"/api/v1/policy/{pid}/activate")
        assert resp.status_code == 400

    def test_nonexistent_policy_returns_404(self, client) -> None:
        pid = str(uuid4())
        assert client.get(f"/api/v1/policy/{pid}").status_code == 404
        assert client.post(f"/api/v1/policy/{pid}/activate").status_code == 404
        assert client.post(f"/api/v1/policy/{pid}/disable").status_code == 404
        assert client.post(f"/api/v1/policy/{pid}/archive").status_code == 404
        assert client.post(f"/api/v1/policy/{pid}/rules", json={"policy_id": pid, "condition": "true", "action": "allow"}).status_code == 404
        assert client.post(f"/api/v1/policy/{pid}/evaluations/start").status_code == 404

    def test_policy_response_shape(self, client) -> None:
        resp = _create_policy_via_api(client)
        data = resp.json()
        assert "policy_id" in data
        assert "name" in data
        assert "description" in data
        assert "status" in data
        assert "priority" in data
        assert "scope" in data
        assert "version" in data
        assert "created_at" in data

    def test_create_policy_invalid_body_returns_422(self, client) -> None:
        resp = client.post("/api/v1/policy/", json={})
        assert resp.status_code == 422

    def test_add_rule_invalid_body_returns_422(self, client) -> None:
        created = _create_policy_via_api(client).json()
        pid = created["policy_id"]
        resp = client.post(f"/api/v1/policy/{pid}/rules", json={})
        assert resp.status_code == 422
