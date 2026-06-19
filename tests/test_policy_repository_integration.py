from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.policy.adapters.outbound.mapper import (
    PolicyEvaluationMapperImpl,
    PolicyMapperImpl,
    PolicyOutboxMapperImpl,
    PolicyRuleMapperImpl,
)
from backend.policy.adapters.outbound.models import (
    Base,
    PolicyEvaluationModel,
    PolicyModel,
    PolicyOutboxModel,
    PolicyRuleModel,
)
from backend.policy.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyPolicyEvaluationRepository,
    SqlAlchemyPolicyOutboxAdapter,
    SqlAlchemyPolicyRepository,
    SqlAlchemyPolicyRuleRepository,
)
from backend.policy.domain.model import (
    EvaluationId,
    Policy,
    PolicyAction,
    PolicyActivated,
    PolicyCreated,
    PolicyCondition,
    PolicyDescription,
    PolicyEvaluation,
    PolicyEvaluationCompleted,
    PolicyEvaluationFailed,
    PolicyEvaluationStatus,
    PolicyId,
    PolicyName,
    PolicyPriority,
    PolicyRule,
    PolicyRuleAdded,
    PolicyRuleEnabled,
    PolicyRuleId,
    PolicyScope,
    PolicyStatus,
    PolicyVersion,
)

_NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def session():
    engine = create_engine("sqlite://", echo=False)
    for t in Base.metadata.tables.values():
        t.schema = None
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    sess = TestSession()
    try:
        yield sess
    finally:
        sess.close()


# ===================================================================
# Policy Repository
# ===================================================================


class TestSqlAlchemyPolicyRepository:
    def test_save_and_find_by_id(self, session: Session) -> None:
        repo = SqlAlchemyPolicyRepository(session)
        pid = PolicyId(value=UUID("00000000-0000-0000-0000-000000000001"))
        policy = Policy(
            policy_id=pid,
            name=PolicyName(value="Test"),
            description=PolicyDescription(value="Desc"),
            priority=PolicyPriority.HIGH,
            scope=PolicyScope.USER,
            version=PolicyVersion(value="1.0.0"),
        )
        object.__setattr__(policy, "_created_at", _NOW)
        repo.save(policy)
        found = repo.find_by_id(pid)
        assert found is not None
        assert found.policy_id == pid
        assert found.name is not None
        assert found.name.value == "Test"

    def test_find_by_id_not_found(self, session: Session) -> None:
        repo = SqlAlchemyPolicyRepository(session)
        found = repo.find_by_id(PolicyId())
        assert found is None

    def test_find_by_status(self, session: Session) -> None:
        repo = SqlAlchemyPolicyRepository(session)
        p1 = Policy(priority=PolicyPriority.LOW, scope=PolicyScope.GLOBAL)
        object.__setattr__(p1, "_status", PolicyStatus.ACTIVE)
        object.__setattr__(p1, "_created_at", _NOW)
        p2 = Policy(priority=PolicyPriority.LOW, scope=PolicyScope.GLOBAL)
        object.__setattr__(p2, "_status", PolicyStatus.DRAFT)
        object.__setattr__(p2, "_created_at", _NOW)
        repo.save(p1)
        repo.save(p2)
        active = repo.find_by_status(PolicyStatus.ACTIVE)
        assert len(active) == 1
        draft = repo.find_by_status(PolicyStatus.DRAFT)
        assert len(draft) == 1

    def test_find_by_priority(self, session: Session) -> None:
        repo = SqlAlchemyPolicyRepository(session)
        p1 = Policy(scope=PolicyScope.GLOBAL)
        object.__setattr__(p1, "_priority", PolicyPriority.HIGH)
        object.__setattr__(p1, "_created_at", _NOW)
        p2 = Policy(scope=PolicyScope.GLOBAL)
        object.__setattr__(p2, "_priority", PolicyPriority.LOW)
        object.__setattr__(p2, "_created_at", _NOW)
        repo.save(p1)
        repo.save(p2)
        high = repo.find_by_priority(PolicyPriority.HIGH)
        assert len(high) == 1

    def test_find_by_scope(self, session: Session) -> None:
        repo = SqlAlchemyPolicyRepository(session)
        p1 = Policy()
        object.__setattr__(p1, "_scope", PolicyScope.USER)
        object.__setattr__(p1, "_created_at", _NOW)
        p2 = Policy()
        object.__setattr__(p2, "_scope", PolicyScope.AGENT)
        object.__setattr__(p2, "_created_at", _NOW)
        repo.save(p1)
        repo.save(p2)
        user = repo.find_by_scope(PolicyScope.USER)
        assert len(user) == 1

    def test_update(self, session: Session) -> None:
        repo = SqlAlchemyPolicyRepository(session)
        pid = PolicyId()
        policy = Policy(policy_id=pid, scope=PolicyScope.GLOBAL)
        object.__setattr__(policy, "_created_at", _NOW)
        repo.save(policy)
        policy2 = Policy(
            policy_id=pid,
            name=PolicyName(value="Updated"),
            scope=PolicyScope.GLOBAL,
        )
        object.__setattr__(policy2, "_created_at", _NOW)
        repo.save(policy2)
        found = repo.find_by_id(pid)
        assert found is not None
        assert found.name is not None
        assert found.name.value == "Updated"

    def test_count(self, session: Session) -> None:
        repo = SqlAlchemyPolicyRepository(session)
        assert repo.count() == 0
        p1 = Policy(scope=PolicyScope.GLOBAL)
        object.__setattr__(p1, "_created_at", _NOW)
        p2 = Policy(scope=PolicyScope.GLOBAL)
        object.__setattr__(p2, "_created_at", _NOW)
        repo.save(p1)
        repo.save(p2)
        assert repo.count() == 2


# ===================================================================
# Rule Repository
# ===================================================================


class TestSqlAlchemyPolicyRuleRepository:
    def test_save_and_find_by_id(self, session: Session) -> None:
        repo = SqlAlchemyPolicyRuleRepository(session)
        rid = PolicyRuleId(value=UUID("00000000-0000-0000-0000-000000000002"))
        rule = PolicyRule(
            rule_id=rid,
            condition=PolicyCondition(value="true"),
            action=PolicyAction(value="allow"),
            priority=10,
            enabled=True,
        )
        repo.save(rule)
        found = repo.find_by_id(rid)
        assert found is not None
        assert found.rule_id == rid

    def test_find_by_id_not_found(self, session: Session) -> None:
        repo = SqlAlchemyPolicyRuleRepository(session)
        found = repo.find_by_id(PolicyRuleId())
        assert found is None

    def test_find_by_policy_id(self, session: Session) -> None:
        repo = SqlAlchemyPolicyRuleRepository(session)
        pid = str(PolicyId())
        r1 = PolicyRule()
        r2 = PolicyRule()
        repo.save(r1)
        repo.save(r2)
        found = repo.find_all()
        assert len(found) == 2

    def test_find_enabled(self, session: Session) -> None:
        repo = SqlAlchemyPolicyRuleRepository(session)
        r1 = PolicyRule(enabled=False)
        r2 = PolicyRule(enabled=True)
        repo.save(r1)
        repo.save(r2)
        enabled = repo.find_enabled()
        assert len(enabled) == 1

    def test_update(self, session: Session) -> None:
        repo = SqlAlchemyPolicyRuleRepository(session)
        rid = PolicyRuleId()
        rule = PolicyRule(rule_id=rid, priority=1, enabled=False)
        repo.save(rule)
        rule2 = PolicyRule(rule_id=rid, priority=5, enabled=True)
        repo.save(rule2)
        found = repo.find_by_id(rid)
        assert found is not None
        assert found.priority == 5
        assert found.enabled is True

    def test_count(self, session: Session) -> None:
        repo = SqlAlchemyPolicyRuleRepository(session)
        assert repo.count() == 0
        repo.save(PolicyRule())
        repo.save(PolicyRule())
        assert repo.count() == 2


# ===================================================================
# Evaluation Repository
# ===================================================================


class TestSqlAlchemyPolicyEvaluationRepository:
    def test_save_and_find_by_id(self, session: Session) -> None:
        repo = SqlAlchemyPolicyEvaluationRepository(session)
        eid = EvaluationId(value=UUID("00000000-0000-0000-0000-000000000003"))
        pid = PolicyId(value=UUID("00000000-0000-0000-0000-000000000001"))
        evaluation = PolicyEvaluation(
            evaluation_id=eid,
            policy_id=pid,
            status=PolicyEvaluationStatus.PENDING,
        )
        repo.save(evaluation)
        found = repo.find_by_id(eid)
        assert found is not None
        assert found.evaluation_id == eid

    def test_find_by_id_not_found(self, session: Session) -> None:
        repo = SqlAlchemyPolicyEvaluationRepository(session)
        found = repo.find_by_id(EvaluationId())
        assert found is None

    def test_find_by_status(self, session: Session) -> None:
        repo = SqlAlchemyPolicyEvaluationRepository(session)
        e1 = PolicyEvaluation(status=PolicyEvaluationStatus.PENDING)
        e2 = PolicyEvaluation(status=PolicyEvaluationStatus.COMPLETED)
        repo.save(e1)
        repo.save(e2)
        pending = repo.find_by_status(PolicyEvaluationStatus.PENDING)
        assert len(pending) == 1

    def test_find_by_policy_id(self, session: Session) -> None:
        repo = SqlAlchemyPolicyEvaluationRepository(session)
        pid = PolicyId()
        e1 = PolicyEvaluation(policy_id=pid)
        e2 = PolicyEvaluation(policy_id=pid)
        repo.save(e1)
        repo.save(e2)
        found = repo.find_by_policy_id(pid)
        assert len(found) == 2

    def test_update(self, session: Session) -> None:
        repo = SqlAlchemyPolicyEvaluationRepository(session)
        eid = EvaluationId()
        evaluation = PolicyEvaluation(
            evaluation_id=eid,
            status=PolicyEvaluationStatus.PENDING,
        )
        repo.save(evaluation)
        evaluation2 = PolicyEvaluation(
            evaluation_id=eid,
            status=PolicyEvaluationStatus.COMPLETED,
        )
        repo.save(evaluation2)
        found = repo.find_by_id(eid)
        assert found is not None
        assert found.status == PolicyEvaluationStatus.COMPLETED

    def test_count(self, session: Session) -> None:
        repo = SqlAlchemyPolicyEvaluationRepository(session)
        assert repo.count() == 0
        repo.save(PolicyEvaluation())
        repo.save(PolicyEvaluation())
        assert repo.count() == 2


# ===================================================================
# Outbox Adapter
# ===================================================================


class TestSqlAlchemyPolicyOutboxAdapter:
    def test_append_and_fetch(self, session: Session) -> None:
        adapter = SqlAlchemyPolicyOutboxAdapter(session)
        pid = PolicyId()
        event = PolicyActivated(policy_id=pid, occurred_at=_NOW)
        adapter.append(event)
        unpublished = adapter.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], PolicyActivated)
        assert unpublished[0].policy_id == pid

    def test_fetch_unpublished_empty(self, session: Session) -> None:
        adapter = SqlAlchemyPolicyOutboxAdapter(session)
        assert adapter.fetch_unpublished() == []

    def test_fetch_unpublished_limit(self, session: Session) -> None:
        adapter = SqlAlchemyPolicyOutboxAdapter(session)
        events = [
            PolicyActivated(policy_id=PolicyId(), occurred_at=_NOW)
            for _ in range(5)
        ]
        for e in events:
            adapter.append(e)
        fetched = adapter.fetch_unpublished(limit=3)
        assert len(fetched) == 3

    def test_mark_published(self, session: Session) -> None:
        adapter = SqlAlchemyPolicyOutboxAdapter(session)
        pid = PolicyId()
        event = PolicyActivated(policy_id=pid, occurred_at=_NOW)
        adapter.append(event)
        fetched = adapter.fetch_unpublished()
        adapter.mark_published(str(fetched[0].event_id))
        unpublished = adapter.fetch_unpublished()
        assert len(unpublished) == 0

    def test_mark_published_idempotent(self, session: Session) -> None:
        adapter = SqlAlchemyPolicyOutboxAdapter(session)
        pid = PolicyId()
        event = PolicyActivated(policy_id=pid, occurred_at=_NOW)
        adapter.append(event)
        fetched = adapter.fetch_unpublished()
        adapter.mark_published(str(fetched[0].event_id))
        adapter.mark_published(str(fetched[0].event_id))
        assert len(adapter.fetch_unpublished()) == 0

    def test_fifo_order(self, session: Session) -> None:
        adapter = SqlAlchemyPolicyOutboxAdapter(session)
        pid = PolicyId()
        e1 = PolicyActivated(policy_id=pid, occurred_at=_NOW)
        e2 = PolicyCreated(
            policy_id=pid, name="n", description="d",
            priority="medium", scope="global", version="1.0.0",
            occurred_at=datetime(2026, 6, 13, 13, 0, 0, tzinfo=timezone.utc),
        )
        adapter.append(e1)
        adapter.append(e2)
        unpublished = adapter.fetch_unpublished()
        assert len(unpublished) == 2
        assert isinstance(unpublished[0], PolicyActivated)
        assert isinstance(unpublished[1], PolicyCreated)


# ===================================================================
# SQLAlchemy Model / Schema Alignment
# ===================================================================


class TestPolicyModelSchema:
    def test_policy_model_table_name(self) -> None:
        assert PolicyModel.__tablename__ == "policies"

    def test_policy_model_columns(self) -> None:
        cols = {c.name: c for c in PolicyModel.__table__.columns}
        assert "policy_id" in cols
        assert "name" in cols
        assert "description" in cols
        assert "status" in cols
        assert "priority" in cols
        assert "scope" in cols
        assert "version" in cols
        assert "created_at" in cols
        assert "updated_at" in cols
        assert len(cols) == 9

    def test_policy_model_primary_key(self) -> None:
        pk = PolicyModel.__table__.primary_key
        assert len(pk.columns) == 1
        assert list(pk.columns)[0].name == "policy_id"

    def test_rule_model_table_name(self) -> None:
        assert PolicyRuleModel.__tablename__ == "rules"

    def test_rule_model_columns(self) -> None:
        cols = {c.name: c for c in PolicyRuleModel.__table__.columns}
        assert "rule_id" in cols
        assert "policy_id" in cols
        assert "condition" in cols
        assert "action" in cols
        assert "priority" in cols
        assert "enabled" in cols
        assert len(cols) == 6

    def test_evaluation_model_table_name(self) -> None:
        assert PolicyEvaluationModel.__tablename__ == "evaluations"

    def test_evaluation_model_columns(self) -> None:
        cols = {c.name: c for c in PolicyEvaluationModel.__table__.columns}
        assert "evaluation_id" in cols
        assert "policy_id" in cols
        assert "status" in cols
        assert "decision" in cols
        assert "result" in cols
        assert "failure_reason" in cols
        assert "started_at" in cols
        assert "completed_at" in cols
        assert len(cols) == 8

    def test_outbox_model_table_name(self) -> None:
        assert PolicyOutboxModel.__tablename__ == "outbox"

    def test_outbox_model_columns(self) -> None:
        cols = {c.name: c for c in PolicyOutboxModel.__table__.columns}
        assert "message_id" in cols
        assert "subject" in cols
        assert "aggregate_id" in cols
        assert "created_at" in cols
        assert "payload" in cols
        assert "published_at" in cols
        assert len(cols) >= 10


class TestPolicyModelCRUD:
    def test_insert_and_select_policy(self, session: Session) -> None:
        model = PolicyModel(
            policy_id="p1",
            name="Test",
            description="Desc",
            status="active",
            priority="high",
            scope="global",
            version="1.0.0",
            created_at=_NOW,
        )
        session.add(model)
        session.flush()
        found = session.get(PolicyModel, "p1")
        assert found is not None
        assert found.name == "Test"

    def test_insert_and_select_rule(self, session: Session) -> None:
        model = PolicyRuleModel(
            rule_id="r1",
            policy_id="p1",
            condition="true",
            action="allow",
            priority=5,
            enabled=True,
        )
        session.add(model)
        session.flush()
        found = session.get(PolicyRuleModel, "r1")
        assert found is not None
        assert found.priority == 5

    def test_insert_and_select_evaluation(self, session: Session) -> None:
        model = PolicyEvaluationModel(
            evaluation_id="e1",
            policy_id="p1",
            status="pending",
            started_at=_NOW,
        )
        session.add(model)
        session.flush()
        found = session.get(PolicyEvaluationModel, "e1")
        assert found is not None
        assert found.status == "pending"

    def test_insert_and_select_outbox(self, session: Session) -> None:
        from uuid import uuid4
        eid = str(uuid4())
        model = PolicyOutboxModel(
            message_id=eid,
            subject="policy.created",
            aggregate_id=eid,
            created_at=_NOW,
            payload={"name": "test"},
            published_at=None,
        )
        session.add(model)
        session.flush()
        found = session.get(PolicyOutboxModel, eid)
        assert found is not None
        assert found.subject == "policy.created"
