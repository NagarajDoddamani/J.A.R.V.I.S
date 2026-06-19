from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from backend.policy.adapters.outbound.clock import SystemClockAdapter
from backend.policy.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.policy.adapters.outbound.mapper import (
    PolicyEvaluationMapperImpl,
    PolicyMapperImpl,
    PolicyOutboxMapperImpl,
    PolicyRuleMapperImpl,
)
from backend.policy.application.persistence.dto import (
    PolicyEvaluationStorageDTO,
    PolicyOutboxStorageDTO,
    PolicyRuleStorageDTO,
    PolicyStorageDTO,
)
from backend.policy.domain.model import (
    EvaluationId,
    EvaluationResult,
    FailureReason,
    Policy,
    PolicyAction,
    PolicyActivated,
    PolicyArchived,
    PolicyCondition,
    PolicyCreated,
    PolicyDecision,
    PolicyDescription,
    PolicyDisabled,
    PolicyEvaluation,
    PolicyEvaluationCompleted,
    PolicyEvaluationFailed,
    PolicyEvaluationStarted,
    PolicyEvaluationStatus,
    PolicyId,
    PolicyName,
    PolicyPriority,
    PolicyRule,
    PolicyRuleAdded,
    PolicyRuleDisabled,
    PolicyRuleEnabled,
    PolicyRuleId,
    PolicyRuleRemoved,
    PolicyScope,
    PolicyStatus,
    PolicyVersion,
)

_NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)
_NOW2 = datetime(2026, 6, 13, 13, 0, 0, tzinfo=timezone.utc)


class TestPolicyMapperImpl:
    def test_conforms_to_protocol(self) -> None:
        mapper: PolicyMapperImpl = PolicyMapperImpl()
        assert mapper is not None

    def test_domain_to_dto(self) -> None:
        pid = PolicyId(value=UUID("00000000-0000-0000-0000-000000000001"))
        policy = Policy(
            policy_id=pid,
            name=PolicyName(value="Test"),
            description=PolicyDescription(value="Desc"),
            priority=PolicyPriority.HIGH,
            scope=PolicyScope.USER,
            version=PolicyVersion(value="1.0.0"),
            created_at=_NOW,
        )
        mapper = PolicyMapperImpl()
        dto = mapper.domain_to_dto(policy)
        assert dto.policy_id == str(pid)
        assert dto.name == "Test"
        assert dto.description == "Desc"
        assert dto.status == "draft"
        assert dto.priority == "high"
        assert dto.scope == "user"
        assert dto.version == "1.0.0"
        assert dto.created_at == _NOW

    def test_dto_to_domain(self) -> None:
        dto = PolicyStorageDTO(
            policy_id="00000000-0000-0000-0000-000000000001",
            name="Test",
            description="Desc",
            status="active",
            priority="high",
            scope="global",
            version="2.0.0",
            created_at=_NOW,
            updated_at=_NOW2,
        )
        mapper = PolicyMapperImpl()
        domain = mapper.dto_to_domain(dto)
        assert domain.policy_id == PolicyId(value=UUID("00000000-0000-0000-0000-000000000001"))
        assert domain.name is not None
        assert domain.name.value == "Test"
        assert domain.description is not None
        assert domain.description.value == "Desc"
        assert domain.status == PolicyStatus.ACTIVE
        assert domain.priority == PolicyPriority.HIGH
        assert domain.scope == PolicyScope.GLOBAL
        assert domain.version is not None
        assert domain.version.value == "2.0.0"
        assert domain.created_at == _NOW
        assert domain.updated_at == _NOW2

    def test_roundtrip(self) -> None:
        pid = PolicyId(value=UUID("00000000-0000-0000-0000-000000000001"))
        original = Policy(
            policy_id=pid,
            name=PolicyName(value="Roundtrip"),
            description=PolicyDescription(value="Roundtrip test"),
            priority=PolicyPriority.HIGH,
            scope=PolicyScope.AGENT,
            version=PolicyVersion(value="1.0.0"),
            created_at=_NOW,
        )
        mapper = PolicyMapperImpl()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.policy_id == original.policy_id
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.status == original.status
        assert restored.priority == original.priority
        assert restored.scope == original.scope
        assert restored.version == original.version
        assert restored.created_at == original.created_at

    def test_nullable_fields(self) -> None:
        policy = Policy()
        mapper = PolicyMapperImpl()
        dto = mapper.domain_to_dto(policy)
        assert dto.name is None
        assert dto.description is None
        assert dto.version is None
        assert dto.updated_at is None

    def test_dto_to_domain_nullable(self) -> None:
        dto = PolicyStorageDTO(
            policy_id="00000000-0000-0000-0000-000000000001",
        )
        mapper = PolicyMapperImpl()
        domain = mapper.dto_to_domain(dto)
        assert domain.name is None
        assert domain.description is None
        assert domain.version is None
        assert domain.updated_at is None


class TestPolicyRuleMapperImpl:
    def test_conforms_to_protocol(self) -> None:
        mapper: PolicyRuleMapperImpl = PolicyRuleMapperImpl()
        assert mapper is not None

    def test_domain_to_dto(self) -> None:
        rid = PolicyRuleId(value=UUID("00000000-0000-0000-0000-000000000002"))
        rule = PolicyRule(
            rule_id=rid,
            condition=PolicyCondition(value="true"),
            action=PolicyAction(value="allow"),
            priority=10,
            enabled=True,
        )
        mapper = PolicyRuleMapperImpl()
        dto = mapper.domain_to_dto(rule)
        assert dto.rule_id == str(rid)
        assert dto.condition == "true"
        assert dto.action == "allow"
        assert dto.priority == 10
        assert dto.enabled is True

    def test_dto_to_domain(self) -> None:
        dto = PolicyRuleStorageDTO(
            rule_id="00000000-0000-0000-0000-000000000002",
            condition="user.role == admin",
            action="deny",
            priority=5,
            enabled=False,
        )
        mapper = PolicyRuleMapperImpl()
        domain = mapper.dto_to_domain(dto)
        assert domain.rule_id == PolicyRuleId(value=UUID("00000000-0000-0000-0000-000000000002"))
        assert domain.condition is not None
        assert domain.condition.value == "user.role == admin"
        assert domain.action is not None
        assert domain.action.value == "deny"
        assert domain.priority == 5
        assert domain.enabled is False

    def test_roundtrip(self) -> None:
        rid = PolicyRuleId(value=UUID("00000000-0000-0000-0000-000000000002"))
        original = PolicyRule(
            rule_id=rid,
            condition=PolicyCondition(value="resource.type == document"),
            action=PolicyAction(value="review"),
            priority=1,
            enabled=True,
        )
        mapper = PolicyRuleMapperImpl()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.rule_id == original.rule_id
        assert restored.condition == original.condition
        assert restored.action == original.action
        assert restored.priority == original.priority
        assert restored.enabled == original.enabled

    def test_nullable_fields(self) -> None:
        rule = PolicyRule()
        mapper = PolicyRuleMapperImpl()
        dto = mapper.domain_to_dto(rule)
        assert dto.condition is None
        assert dto.action is None

    def test_dto_to_domain_nullable(self) -> None:
        dto = PolicyRuleStorageDTO(
            rule_id="00000000-0000-0000-0000-000000000002",
        )
        mapper = PolicyRuleMapperImpl()
        domain = mapper.dto_to_domain(dto)
        assert domain.condition is None
        assert domain.action is None
        assert domain.priority == 0
        assert domain.enabled is True

    def test_domain_to_dto_with_policy_id(self) -> None:
        rid = PolicyRuleId(value=UUID("00000000-0000-0000-0000-000000000002"))
        rule = PolicyRule(
            rule_id=rid,
            condition=PolicyCondition(value="x"),
            action=PolicyAction(value="y"),
            priority=5,
            enabled=True,
        )
        mapper = PolicyRuleMapperImpl()
        dto = mapper.domain_to_dto(rule, policy_id="p1")
        assert dto.policy_id == "p1"


class TestPolicyEvaluationMapperImpl:
    def test_conforms_to_protocol(self) -> None:
        mapper: PolicyEvaluationMapperImpl = PolicyEvaluationMapperImpl()
        assert mapper is not None

    def test_domain_to_dto(self) -> None:
        eid = EvaluationId(value=UUID("00000000-0000-0000-0000-000000000003"))
        pid = PolicyId(value=UUID("00000000-0000-0000-0000-000000000001"))
        evaluation = PolicyEvaluation(
            evaluation_id=eid,
            policy_id=pid,
            status=PolicyEvaluationStatus.EVALUATING,
            started_at=_NOW,
        )
        mapper = PolicyEvaluationMapperImpl()
        dto = mapper.domain_to_dto(evaluation)
        assert dto.evaluation_id == str(eid)
        assert dto.policy_id == str(pid)
        assert dto.status == "evaluating"
        assert dto.started_at == _NOW
        assert dto.completed_at is None

    def test_dto_to_domain(self) -> None:
        dto = PolicyEvaluationStorageDTO(
            evaluation_id="00000000-0000-0000-0000-000000000003",
            policy_id="00000000-0000-0000-0000-000000000001",
            status="completed",
            decision="allow",
            result="ALLOW",
            started_at=_NOW,
            completed_at=_NOW2,
        )
        mapper = PolicyEvaluationMapperImpl()
        domain = mapper.dto_to_domain(dto)
        assert domain.evaluation_id == EvaluationId(value=UUID("00000000-0000-0000-0000-000000000003"))
        assert domain.policy_id == PolicyId(value=UUID("00000000-0000-0000-0000-000000000001"))
        assert domain.status == PolicyEvaluationStatus.COMPLETED
        assert domain.decision is not None
        assert domain.decision == PolicyDecision.ALLOW
        assert domain.result is not None
        assert domain.result.value == "ALLOW"
        assert domain.started_at == _NOW
        assert domain.completed_at == _NOW2

    def test_roundtrip(self) -> None:
        eid = EvaluationId(value=UUID("00000000-0000-0000-0000-000000000003"))
        pid = PolicyId(value=UUID("00000000-0000-0000-0000-000000000001"))
        original = PolicyEvaluation(
            evaluation_id=eid,
            policy_id=pid,
            status=PolicyEvaluationStatus.PENDING,
        )
        mapper = PolicyEvaluationMapperImpl()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.evaluation_id == original.evaluation_id
        assert restored.policy_id == original.policy_id
        assert restored.status == original.status
        assert restored.decision is None
        assert restored.result is None

    def test_failure_reason(self) -> None:
        dto = PolicyEvaluationStorageDTO(
            evaluation_id="00000000-0000-0000-0000-000000000003",
            status="failed",
            failure_reason="Policy violation detected",
        )
        mapper = PolicyEvaluationMapperImpl()
        domain = mapper.dto_to_domain(dto)
        assert domain.status == PolicyEvaluationStatus.FAILED
        assert domain.failure_reason is not None
        assert domain.failure_reason.value == "Policy violation detected"


class TestPolicyOutboxMapperImpl:
    def test_conforms_to_protocol(self) -> None:
        mapper: PolicyOutboxMapperImpl = PolicyOutboxMapperImpl()
        assert mapper is not None

    def test_event_type_created(self) -> None:
        event = PolicyCreated(
            policy_id=PolicyId(),
            name="Test",
            description="Desc",
            priority="medium",
            scope="global",
            version="1.0.0",
            occurred_at=_NOW,
        )
        mapper = PolicyOutboxMapperImpl()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.created"
        assert dto.occurred_at == _NOW
        assert dto.aggregate_id == str(event.policy_id)
        assert dto.payload is not None
        assert "Test" in dto.payload

    def test_event_type_activated(self) -> None:
        event = PolicyActivated(policy_id=PolicyId(), occurred_at=_NOW)
        mapper = PolicyOutboxMapperImpl()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.activated"
        assert dto.payload is None

    def test_event_type_disabled(self) -> None:
        event = PolicyDisabled(policy_id=PolicyId(), occurred_at=_NOW)
        mapper = PolicyOutboxMapperImpl()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.disabled"

    def test_event_type_archived(self) -> None:
        event = PolicyArchived(policy_id=PolicyId(), occurred_at=_NOW)
        mapper = PolicyOutboxMapperImpl()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.archived"

    def test_event_type_rule_added(self) -> None:
        event = PolicyRuleAdded(
            rule_id=PolicyRuleId(), policy_id=PolicyId(),
            condition="true", action="allow", occurred_at=_NOW,
        )
        mapper = PolicyOutboxMapperImpl()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.rule_added"
        assert dto.payload is not None
        assert "rule_id" in dto.payload

    def test_event_type_rule_removed(self) -> None:
        event = PolicyRuleRemoved(
            rule_id=PolicyRuleId(), policy_id=PolicyId(), occurred_at=_NOW,
        )
        mapper = PolicyOutboxMapperImpl()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.rule_removed"
        assert dto.payload is None

    def test_event_type_rule_enabled(self) -> None:
        event = PolicyRuleEnabled(
            rule_id=PolicyRuleId(), policy_id=PolicyId(), occurred_at=_NOW,
        )
        mapper = PolicyOutboxMapperImpl()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.rule_enabled"
        assert dto.payload is None

    def test_event_type_rule_disabled(self) -> None:
        event = PolicyRuleDisabled(
            rule_id=PolicyRuleId(), policy_id=PolicyId(), occurred_at=_NOW,
        )
        mapper = PolicyOutboxMapperImpl()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.rule_disabled"
        assert dto.payload is None

    def test_event_type_evaluation_started(self) -> None:
        event = PolicyEvaluationStarted(
            policy_id=PolicyId(), evaluation_id=EvaluationId(), occurred_at=_NOW,
        )
        mapper = PolicyOutboxMapperImpl()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.evaluation_started"
        assert dto.payload is not None
        assert "evaluation_id" in dto.payload

    def test_event_type_evaluation_completed(self) -> None:
        event = PolicyEvaluationCompleted(
            policy_id=PolicyId(), evaluation_id=EvaluationId(),
            decision="allow", result="ok", occurred_at=_NOW,
        )
        mapper = PolicyOutboxMapperImpl()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.evaluation_completed"
        assert dto.payload is not None
        assert "decision" in dto.payload

    def test_event_type_evaluation_failed(self) -> None:
        event = PolicyEvaluationFailed(
            policy_id=PolicyId(), evaluation_id=EvaluationId(),
            failure_reason="err", occurred_at=_NOW,
        )
        mapper = PolicyOutboxMapperImpl()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.evaluation_failed"
        assert dto.payload is not None
        assert "failure_reason" in dto.payload

    def test_dto_to_event_created(self) -> None:
        pid = PolicyId()
        dto = PolicyOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type="policy.created",
            aggregate_id=str(pid),
            occurred_at=_NOW,
            payload='{"name":"Test","description":"Desc","priority":"medium","scope":"global","version":"1.0.0"}',
        )
        mapper = PolicyOutboxMapperImpl()
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PolicyCreated)
        assert event.policy_id == pid
        assert event.name == "Test"

    def test_dto_to_event_activated(self) -> None:
        pid = PolicyId()
        dto = PolicyOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type="policy.activated",
            aggregate_id=str(pid),
            occurred_at=_NOW,
        )
        mapper = PolicyOutboxMapperImpl()
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PolicyActivated)
        assert event.policy_id == pid

    def test_dto_to_event_disabled(self) -> None:
        pid = PolicyId()
        dto = PolicyOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type="policy.disabled",
            aggregate_id=str(pid),
            occurred_at=_NOW,
        )
        mapper = PolicyOutboxMapperImpl()
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PolicyDisabled)

    def test_dto_to_event_archived(self) -> None:
        pid = PolicyId()
        dto = PolicyOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type="policy.archived",
            aggregate_id=str(pid),
            occurred_at=_NOW,
        )
        mapper = PolicyOutboxMapperImpl()
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PolicyArchived)

    def test_dto_to_event_rule_added(self) -> None:
        pid = PolicyId()
        rid = PolicyRuleId()
        dto = PolicyOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type="policy.rule_added",
            aggregate_id=str(pid),
            occurred_at=_NOW,
            payload=f'{{"rule_id":"{rid}"}}',
        )
        mapper = PolicyOutboxMapperImpl()
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PolicyRuleAdded)
        assert event.rule_id == rid

    def test_dto_to_event_rule_removed(self) -> None:
        dto = PolicyOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type="policy.rule_removed",
            aggregate_id=str(PolicyId()),
            occurred_at=_NOW,
            payload="{}",
        )
        mapper = PolicyOutboxMapperImpl()
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PolicyRuleRemoved)

    def test_dto_to_event_rule_enabled(self) -> None:
        dto = PolicyOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type="policy.rule_enabled",
            aggregate_id=str(PolicyId()),
            occurred_at=_NOW,
        )
        mapper = PolicyOutboxMapperImpl()
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PolicyRuleEnabled)

    def test_dto_to_event_rule_disabled(self) -> None:
        dto = PolicyOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type="policy.rule_disabled",
            aggregate_id=str(PolicyId()),
            occurred_at=_NOW,
        )
        mapper = PolicyOutboxMapperImpl()
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PolicyRuleDisabled)

    def test_dto_to_event_evaluation_started(self) -> None:
        pid = PolicyId()
        eid = EvaluationId()
        dto = PolicyOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type="policy.evaluation_started",
            aggregate_id=str(pid),
            occurred_at=_NOW,
            payload=f'{{"evaluation_id":"{eid}"}}',
        )
        mapper = PolicyOutboxMapperImpl()
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PolicyEvaluationStarted)
        assert event.evaluation_id == eid

    def test_dto_to_event_evaluation_completed(self) -> None:
        pid = PolicyId()
        eid = EvaluationId()
        dto = PolicyOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type="policy.evaluation_completed",
            aggregate_id=str(pid),
            occurred_at=_NOW,
            payload=f'{{"evaluation_id":"{eid}","decision":"allow","result":"ok"}}',
        )
        mapper = PolicyOutboxMapperImpl()
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PolicyEvaluationCompleted)
        assert event.evaluation_id == eid
        assert event.decision == "allow"

    def test_dto_to_event_evaluation_failed(self) -> None:
        pid = PolicyId()
        eid = EvaluationId()
        dto = PolicyOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type="policy.evaluation_failed",
            aggregate_id=str(pid),
            occurred_at=_NOW,
            payload=f'{{"evaluation_id":"{eid}","failure_reason":"err"}}',
        )
        mapper = PolicyOutboxMapperImpl()
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PolicyEvaluationFailed)
        assert event.evaluation_id == eid
        assert event.failure_reason == "err"

    def test_dto_to_event_unknown_type(self) -> None:
        dto = PolicyOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type="policy.unknown",
            aggregate_id=str(PolicyId()),
            occurred_at=_NOW,
        )
        mapper = PolicyOutboxMapperImpl()
        with pytest.raises(ValueError, match="Unknown event_type"):
            mapper.dto_to_event(dto)


class TestSystemClockAdapter:
    def test_now_returns_utc_datetime(self) -> None:
        clock = SystemClockAdapter()
        result = clock.now()
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result) is not None
        assert result.tzinfo is timezone.utc or result.utcoffset() == timezone.utc.utcoffset(result)

    def test_now_returns_current_time(self) -> None:
        clock = SystemClockAdapter()
        before = datetime.now(tz=timezone.utc)
        result = clock.now()
        after = datetime.now(tz=timezone.utc)
        assert before <= result <= after


class TestUuidGeneratorAdapter:
    def test_generate_policy_id(self) -> None:
        gen = UuidGeneratorAdapter()
        uid = gen.generate_policy_id()
        assert isinstance(uid, str)
        assert len(uid) > 0
        UUID(uid)

    def test_generate_rule_id(self) -> None:
        gen = UuidGeneratorAdapter()
        uid = gen.generate_rule_id()
        assert isinstance(uid, str)
        UUID(uid)

    def test_generate_evaluation_id(self) -> None:
        gen = UuidGeneratorAdapter()
        uid = gen.generate_evaluation_id()
        assert isinstance(uid, str)
        UUID(uid)

    def test_unique_ids(self) -> None:
        gen = UuidGeneratorAdapter()
        ids = {gen.generate_policy_id() for _ in range(100)}
        assert len(ids) == 100
