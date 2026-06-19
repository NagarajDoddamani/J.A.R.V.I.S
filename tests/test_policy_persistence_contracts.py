from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Union
from uuid import UUID, uuid4

import pytest

from backend.policy.application.persistence.dto import (
    PolicyEvaluationStorageDTO,
    PolicyOutboxStorageDTO,
    PolicyRuleStorageDTO,
    PolicyStorageDTO,
)
from backend.policy.application.persistence.mapper import (
    PolicyEvaluationMapper,
    PolicyMapper,
    PolicyOutboxDomainEvent,
    PolicyOutboxMapper,
    PolicyRuleMapper,
)
from backend.policy.application.persistence.schema import (
    POLICIES_TABLE,
    POLICY_EVALUATIONS_TABLE,
    POLICY_OUTBOX_TABLE,
    POLICY_RULES_TABLE,
    ColumnContract,
    TableContract,
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


# ===================================================================
# Stub mapper implementations
# ===================================================================


class StubPolicyMapper:
    def domain_to_dto(self, policy: Policy) -> PolicyStorageDTO:
        return PolicyStorageDTO(
            policy_id=str(policy.policy_id),
            name=str(policy.name) if policy.name else None,
            description=str(policy.description) if policy.description else None,
            status=policy.status.value,
            priority=policy.priority.value,
            scope=policy.scope.value,
            version=str(policy.version) if policy.version else None,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )

    def dto_to_domain(self, dto: PolicyStorageDTO) -> Policy:
        policy = Policy(
            policy_id=PolicyId(value=UUID(dto.policy_id)),
            name=PolicyName(value=dto.name) if dto.name else None,
            description=PolicyDescription(value=dto.description) if dto.description else None,
            priority=PolicyPriority(dto.priority),
            scope=PolicyScope(dto.scope),
            version=PolicyVersion(value=dto.version) if dto.version else None,
        )
        object.__setattr__(policy, "_status", PolicyStatus(dto.status))
        if dto.created_at:
            object.__setattr__(policy, "_created_at", dto.created_at)
        if dto.updated_at:
            object.__setattr__(policy, "_updated_at", dto.updated_at)
        return policy


class StubRuleMapper:
    def domain_to_dto(self, rule: PolicyRule) -> PolicyRuleStorageDTO:
        return PolicyRuleStorageDTO(
            rule_id=str(rule.rule_id),
            condition=str(rule.condition) if rule.condition else None,
            action=str(rule.action) if rule.action else None,
            priority=rule.priority,
            enabled=rule.enabled,
        )

    def dto_to_domain(self, dto: PolicyRuleStorageDTO) -> PolicyRule:
        condition: PolicyCondition | None = None
        if dto.condition:
            condition = PolicyCondition(value=dto.condition)
        action: PolicyAction | None = None
        if dto.action:
            action = PolicyAction(value=dto.action)
        return PolicyRule(
            rule_id=PolicyRuleId(value=UUID(dto.rule_id)),
            condition=condition,
            action=action,
            priority=dto.priority,
            enabled=dto.enabled,
        )


class StubEvaluationMapper:
    def domain_to_dto(
        self, evaluation: PolicyEvaluation
    ) -> PolicyEvaluationStorageDTO:
        return PolicyEvaluationStorageDTO(
            evaluation_id=str(evaluation.evaluation_id),
            policy_id=str(evaluation.policy_id),
            status=evaluation.status.value,
            decision=evaluation.decision.value if evaluation.decision else None,
            result=str(evaluation.result) if evaluation.result else None,
            failure_reason=str(evaluation.failure_reason) if evaluation.failure_reason else None,
            started_at=evaluation.started_at,
            completed_at=evaluation.completed_at,
        )

    def dto_to_domain(
        self, dto: PolicyEvaluationStorageDTO
    ) -> PolicyEvaluation:
        decision: PolicyDecision | None = None
        if dto.decision:
            decision = PolicyDecision(dto.decision)
        result: EvaluationResult | None = None
        if dto.result:
            result = EvaluationResult(value=dto.result)
        failure_reason: FailureReason | None = None
        if dto.failure_reason:
            failure_reason = FailureReason(value=dto.failure_reason)
        evaluation = PolicyEvaluation(
            evaluation_id=EvaluationId(value=UUID(dto.evaluation_id)),
            policy_id=PolicyId(value=UUID(dto.policy_id)) if dto.policy_id else None,
            status=PolicyEvaluationStatus(dto.status),
            decision=decision,
            result=result,
            failure_reason=failure_reason,
            started_at=dto.started_at,
            completed_at=dto.completed_at,
        )
        return evaluation


class StubOutboxMapper:
    def event_to_dto(
        self, event: PolicyOutboxDomainEvent
    ) -> PolicyOutboxStorageDTO:
        event_type = _event_type_map(type(event))
        return PolicyOutboxStorageDTO(
            event_id=str(event.event_id),
            event_type=event_type,
            aggregate_id=str(getattr(event, "policy_id", event.event_id)),
            occurred_at=event.occurred_at,
            payload=_payload_for_event(event),
        )

    def dto_to_event(
        self, dto: PolicyOutboxStorageDTO
    ) -> PolicyOutboxDomainEvent:
        raise NotImplementedError("Outbox dto_to_event requires event reconstruction logic")


def _event_type_map(event_cls: type) -> str:
    mapping = {
        PolicyCreated: "policy.created",
        PolicyActivated: "policy.activated",
        PolicyDisabled: "policy.disabled",
        PolicyArchived: "policy.archived",
        PolicyRuleAdded: "policy.rule_added",
        PolicyRuleRemoved: "policy.rule_removed",
        PolicyRuleEnabled: "policy.rule_enabled",
        PolicyRuleDisabled: "policy.rule_disabled",
        PolicyEvaluationStarted: "policy.evaluation_started",
        PolicyEvaluationCompleted: "policy.evaluation_completed",
        PolicyEvaluationFailed: "policy.evaluation_failed",
    }
    return mapping[event_cls]


def _payload_for_event(event: PolicyOutboxDomainEvent) -> str | None:
    if isinstance(event, PolicyCreated):
        return f'{{"name":"{event.name}","description":"{event.description}"}}'
    return None


# ===================================================================
# Section 1: DTO Tests
# ===================================================================


class TestPolicyStorageDTO:
    def test_construction(self) -> None:
        dto = PolicyStorageDTO(policy_id="policy-1")
        assert dto.policy_id == "policy-1"

    def test_all_fields(self) -> None:
        dto = PolicyStorageDTO(
            policy_id="p1",
            name="Test Policy",
            description="A test policy",
            status="active",
            priority="high",
            scope="global",
            version="1.0.0",
            created_at=_NOW,
            updated_at=_NOW2,
        )
        assert dto.policy_id == "p1"
        assert dto.name == "Test Policy"
        assert dto.description == "A test policy"
        assert dto.status == "active"
        assert dto.priority == "high"
        assert dto.scope == "global"
        assert dto.version == "1.0.0"
        assert dto.created_at == _NOW
        assert dto.updated_at == _NOW2

    def test_frozen(self) -> None:
        dto = PolicyStorageDTO(policy_id="p1")
        with pytest.raises(AttributeError):
            dto.policy_id = "p2"

    def test_default_status(self) -> None:
        dto = PolicyStorageDTO(policy_id="p1")
        assert dto.status == "draft"

    def test_default_priority(self) -> None:
        dto = PolicyStorageDTO(policy_id="p1")
        assert dto.priority == "medium"

    def test_default_scope(self) -> None:
        dto = PolicyStorageDTO(policy_id="p1")
        assert dto.scope == "global"

    def test_default_name_none(self) -> None:
        dto = PolicyStorageDTO(policy_id="p1")
        assert dto.name is None

    def test_default_description_none(self) -> None:
        dto = PolicyStorageDTO(policy_id="p1")
        assert dto.description is None

    def test_default_version_none(self) -> None:
        dto = PolicyStorageDTO(policy_id="p1")
        assert dto.version is None

    def test_default_created_at_none(self) -> None:
        dto = PolicyStorageDTO(policy_id="p1")
        assert dto.created_at is None

    def test_default_updated_at_none(self) -> None:
        dto = PolicyStorageDTO(policy_id="p1")
        assert dto.updated_at is None

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(PolicyStorageDTO)
        assert len(fields) == 9

    def test_equality(self) -> None:
        dto1 = PolicyStorageDTO(policy_id="p1")
        dto2 = PolicyStorageDTO(policy_id="p1")
        assert dto1 == dto2

    def test_inequality(self) -> None:
        dto1 = PolicyStorageDTO(policy_id="p1")
        dto2 = PolicyStorageDTO(policy_id="p2")
        assert dto1 != dto2

    def test_repr(self) -> None:
        dto = PolicyStorageDTO(policy_id="p1")
        r = repr(dto)
        assert "PolicyStorageDTO" in r
        assert "p1" in r


class TestPolicyRuleStorageDTO:
    def test_construction(self) -> None:
        dto = PolicyRuleStorageDTO(rule_id="rule-1")
        assert dto.rule_id == "rule-1"

    def test_all_fields(self) -> None:
        dto = PolicyRuleStorageDTO(
            rule_id="r1",
            policy_id="p1",
            condition="user.role == admin",
            action="allow",
            priority=10,
            enabled=False,
        )
        assert dto.rule_id == "r1"
        assert dto.policy_id == "p1"
        assert dto.condition == "user.role == admin"
        assert dto.action == "allow"
        assert dto.priority == 10
        assert dto.enabled is False

    def test_frozen(self) -> None:
        dto = PolicyRuleStorageDTO(rule_id="r1")
        with pytest.raises(AttributeError):
            dto.rule_id = "r2"

    def test_default_priority(self) -> None:
        dto = PolicyRuleStorageDTO(rule_id="r1")
        assert dto.priority == 0

    def test_default_enabled(self) -> None:
        dto = PolicyRuleStorageDTO(rule_id="r1")
        assert dto.enabled is True

    def test_default_policy_id_none(self) -> None:
        dto = PolicyRuleStorageDTO(rule_id="r1")
        assert dto.policy_id is None

    def test_default_condition_none(self) -> None:
        dto = PolicyRuleStorageDTO(rule_id="r1")
        assert dto.condition is None

    def test_default_action_none(self) -> None:
        dto = PolicyRuleStorageDTO(rule_id="r1")
        assert dto.action is None

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(PolicyRuleStorageDTO)
        assert len(fields) == 6

    def test_equality(self) -> None:
        dto1 = PolicyRuleStorageDTO(rule_id="r1")
        dto2 = PolicyRuleStorageDTO(rule_id="r1")
        assert dto1 == dto2

    def test_inequality(self) -> None:
        dto1 = PolicyRuleStorageDTO(rule_id="r1")
        dto2 = PolicyRuleStorageDTO(rule_id="r2")
        assert dto1 != dto2

    def test_repr(self) -> None:
        dto = PolicyRuleStorageDTO(rule_id="r1")
        r = repr(dto)
        assert "PolicyRuleStorageDTO" in r


class TestPolicyEvaluationStorageDTO:
    def test_construction(self) -> None:
        dto = PolicyEvaluationStorageDTO(evaluation_id="eval-1")
        assert dto.evaluation_id == "eval-1"

    def test_all_fields(self) -> None:
        dto = PolicyEvaluationStorageDTO(
            evaluation_id="e1",
            policy_id="p1",
            status="evaluating",
            decision="allow",
            result="ALLOW",
            failure_reason=None,
            started_at=_NOW,
            completed_at=_NOW2,
        )
        assert dto.evaluation_id == "e1"
        assert dto.policy_id == "p1"
        assert dto.status == "evaluating"
        assert dto.decision == "allow"
        assert dto.result == "ALLOW"
        assert dto.failure_reason is None
        assert dto.started_at == _NOW
        assert dto.completed_at == _NOW2

    def test_frozen(self) -> None:
        dto = PolicyEvaluationStorageDTO(evaluation_id="e1")
        with pytest.raises(AttributeError):
            dto.evaluation_id = "e2"

    def test_default_status(self) -> None:
        dto = PolicyEvaluationStorageDTO(evaluation_id="e1")
        assert dto.status == "pending"

    def test_default_decision_none(self) -> None:
        dto = PolicyEvaluationStorageDTO(evaluation_id="e1")
        assert dto.decision is None

    def test_default_result_none(self) -> None:
        dto = PolicyEvaluationStorageDTO(evaluation_id="e1")
        assert dto.result is None

    def test_default_failure_reason_none(self) -> None:
        dto = PolicyEvaluationStorageDTO(evaluation_id="e1")
        assert dto.failure_reason is None

    def test_default_started_at_none(self) -> None:
        dto = PolicyEvaluationStorageDTO(evaluation_id="e1")
        assert dto.started_at is None

    def test_default_completed_at_none(self) -> None:
        dto = PolicyEvaluationStorageDTO(evaluation_id="e1")
        assert dto.completed_at is None

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(PolicyEvaluationStorageDTO)
        assert len(fields) == 8

    def test_equality(self) -> None:
        dto1 = PolicyEvaluationStorageDTO(evaluation_id="e1")
        dto2 = PolicyEvaluationStorageDTO(evaluation_id="e1")
        assert dto1 == dto2

    def test_inequality(self) -> None:
        dto1 = PolicyEvaluationStorageDTO(evaluation_id="e1")
        dto2 = PolicyEvaluationStorageDTO(evaluation_id="e2")
        assert dto1 != dto2

    def test_repr(self) -> None:
        dto = PolicyEvaluationStorageDTO(evaluation_id="e1")
        r = repr(dto)
        assert "PolicyEvaluationStorageDTO" in r


class TestPolicyOutboxStorageDTO:
    def test_construction(self) -> None:
        dto = PolicyOutboxStorageDTO(
            event_id="evt-1", event_type="policy.created",
            aggregate_id="agg-1", occurred_at=_NOW,
        )
        assert dto.event_id == "evt-1"
        assert dto.event_type == "policy.created"
        assert dto.aggregate_id == "agg-1"
        assert dto.occurred_at == _NOW

    def test_frozen(self) -> None:
        dto = PolicyOutboxStorageDTO(
            event_id="e1", event_type="t", aggregate_id="a", occurred_at=_NOW,
        )
        with pytest.raises(AttributeError):
            dto.event_id = "e2"

    def test_default_payload_none(self) -> None:
        dto = PolicyOutboxStorageDTO(
            event_id="e1", event_type="t", aggregate_id="a", occurred_at=_NOW,
        )
        assert dto.payload is None

    def test_default_published_false(self) -> None:
        dto = PolicyOutboxStorageDTO(
            event_id="e1", event_type="t", aggregate_id="a", occurred_at=_NOW,
        )
        assert dto.published is False

    def test_equality(self) -> None:
        dto1 = PolicyOutboxStorageDTO(
            event_id="e1", event_type="t", aggregate_id="a", occurred_at=_NOW,
        )
        dto2 = PolicyOutboxStorageDTO(
            event_id="e1", event_type="t", aggregate_id="a", occurred_at=_NOW,
        )
        assert dto1 == dto2

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(PolicyOutboxStorageDTO)
        assert len(fields) == 6

    def test_nullable_payload(self) -> None:
        dto = PolicyOutboxStorageDTO(
            event_id="e1", event_type="t", aggregate_id="a",
            occurred_at=_NOW, payload="{}",
        )
        assert dto.payload == "{}"

    def test_published_true(self) -> None:
        dto = PolicyOutboxStorageDTO(
            event_id="e1", event_type="t", aggregate_id="a",
            occurred_at=_NOW, published=True,
        )
        assert dto.published is True


# ===================================================================
# Section 2: Mapper Protocol Tests (Stub Roundtrips)
# ===================================================================


class TestPolicyMapper:
    def test_stub_conforms_to_protocol(self) -> None:
        mapper: PolicyMapper = StubPolicyMapper()
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
        mapper = StubPolicyMapper()
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
        mapper = StubPolicyMapper()
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
        mapper = StubPolicyMapper()
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

    def test_domain_to_dto_nullable_fields(self) -> None:
        policy = Policy()
        mapper = StubPolicyMapper()
        dto = mapper.domain_to_dto(policy)
        assert dto.name is None
        assert dto.description is None
        assert dto.version is None
        assert dto.updated_at is None

    def test_dto_to_domain_nullable_fields(self) -> None:
        dto = PolicyStorageDTO(
            policy_id="00000000-0000-0000-0000-000000000001",
        )
        mapper = StubPolicyMapper()
        domain = mapper.dto_to_domain(dto)
        assert domain.name is None
        assert domain.description is None
        assert domain.version is None
        assert domain.updated_at is None


class TestRuleMapper:
    def test_stub_conforms_to_protocol(self) -> None:
        mapper: PolicyRuleMapper = StubRuleMapper()
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
        mapper = StubRuleMapper()
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
        mapper = StubRuleMapper()
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
        mapper = StubRuleMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.rule_id == original.rule_id
        assert restored.condition == original.condition
        assert restored.action == original.action
        assert restored.priority == original.priority
        assert restored.enabled == original.enabled

    def test_domain_to_dto_nullable_fields(self) -> None:
        rule = PolicyRule()
        mapper = StubRuleMapper()
        dto = mapper.domain_to_dto(rule)
        assert dto.condition is None
        assert dto.action is None
        assert dto.policy_id is None

    def test_dto_to_domain_nullable_fields(self) -> None:
        dto = PolicyRuleStorageDTO(
            rule_id="00000000-0000-0000-0000-000000000002",
        )
        mapper = StubRuleMapper()
        domain = mapper.dto_to_domain(dto)
        assert domain.condition is None
        assert domain.action is None
        assert domain.priority == 0
        assert domain.enabled is True


class TestEvaluationMapper:
    def test_stub_conforms_to_protocol(self) -> None:
        mapper: PolicyEvaluationMapper = StubEvaluationMapper()
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
        mapper = StubEvaluationMapper()
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
        mapper = StubEvaluationMapper()
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
        mapper = StubEvaluationMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.evaluation_id == original.evaluation_id
        assert restored.policy_id == original.policy_id
        assert restored.status == original.status
        assert restored.decision is None
        assert restored.result is None

    def test_domain_to_dto_nullable_result(self) -> None:
        evaluation = PolicyEvaluation()
        mapper = StubEvaluationMapper()
        dto = mapper.domain_to_dto(evaluation)
        assert dto.decision is None
        assert dto.result is None
        assert dto.failure_reason is None
        assert dto.started_at is None
        assert dto.completed_at is None

    def test_dto_to_domain_with_failure_reason(self) -> None:
        dto = PolicyEvaluationStorageDTO(
            evaluation_id="00000000-0000-0000-0000-000000000003",
            status="failed",
            failure_reason="Policy violation detected",
        )
        mapper = StubEvaluationMapper()
        domain = mapper.dto_to_domain(dto)
        assert domain.status == PolicyEvaluationStatus.FAILED
        assert domain.failure_reason is not None
        assert domain.failure_reason.value == "Policy violation detected"


class TestOutboxMapper:
    def test_stub_conforms_to_protocol(self) -> None:
        mapper: PolicyOutboxMapper = StubOutboxMapper()
        assert mapper is not None

    def test_event_to_dto_created(self) -> None:
        event = PolicyCreated(
            policy_id=PolicyId(),
            name="Test",
            description="Desc",
            priority="medium",
            scope="global",
            version="1.0.0",
            occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.created"
        assert dto.occurred_at == _NOW
        assert dto.payload is not None

    def test_event_to_dto_activated(self) -> None:
        event = PolicyActivated(
            policy_id=PolicyId(), occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.activated"

    def test_event_to_dto_disabled(self) -> None:
        event = PolicyDisabled(
            policy_id=PolicyId(), occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.disabled"

    def test_event_to_dto_archived(self) -> None:
        event = PolicyArchived(
            policy_id=PolicyId(), occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.archived"

    def test_event_to_dto_rule_added(self) -> None:
        event = PolicyRuleAdded(
            rule_id=PolicyRuleId(), policy_id=PolicyId(),
            condition="true", action="allow", occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.rule_added"

    def test_event_to_dto_rule_removed(self) -> None:
        event = PolicyRuleRemoved(
            rule_id=PolicyRuleId(), policy_id=PolicyId(),
            occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.rule_removed"

    def test_event_to_dto_rule_enabled(self) -> None:
        event = PolicyRuleEnabled(
            rule_id=PolicyRuleId(), policy_id=PolicyId(),
            occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.rule_enabled"

    def test_event_to_dto_rule_disabled(self) -> None:
        event = PolicyRuleDisabled(
            rule_id=PolicyRuleId(), policy_id=PolicyId(),
            occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.rule_disabled"

    def test_event_to_dto_evaluation_started(self) -> None:
        event = PolicyEvaluationStarted(
            policy_id=PolicyId(), evaluation_id=EvaluationId(),
            occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.evaluation_started"

    def test_event_to_dto_evaluation_completed(self) -> None:
        event = PolicyEvaluationCompleted(
            policy_id=PolicyId(), evaluation_id=EvaluationId(),
            decision="allow", result="ok", occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.evaluation_completed"

    def test_event_to_dto_evaluation_failed(self) -> None:
        event = PolicyEvaluationFailed(
            policy_id=PolicyId(), evaluation_id=EvaluationId(),
            failure_reason="err", occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "policy.evaluation_failed"


# ===================================================================
# Section 3: Schema Contract Tests
# ===================================================================


class TestColumnContract:
    def test_creation(self) -> None:
        col = ColumnContract(name="id", py_type=str, nullable=False)
        assert col.name == "id"
        assert col.py_type is str
        assert col.nullable is False

    def test_frozen(self) -> None:
        col = ColumnContract(name="id", py_type=str, nullable=False)
        with pytest.raises(AttributeError):
            col.name = "changed"


class TestTableContract:
    def test_creation(self) -> None:
        col = ColumnContract(name="id", py_type=str, nullable=False)
        table = TableContract(
            name="test", schema="policy", columns=(col,),
            primary_key="id", indexes=("ix_id",),
        )
        assert table.name == "test"
        assert table.schema == "policy"
        assert len(table.columns) == 1
        assert table.primary_key == "id"
        assert table.indexes == ("ix_id",)

    def test_frozen(self) -> None:
        col = ColumnContract(name="id", py_type=str, nullable=False)
        table = TableContract(
            name="test", schema="policy", columns=(col,), primary_key="id",
        )
        with pytest.raises(AttributeError):
            table.name = "changed"


class TestPoliciesTableSchema:
    def test_table_name(self) -> None:
        assert POLICIES_TABLE.name == "policies"

    def test_schema_name(self) -> None:
        assert POLICIES_TABLE.schema == "policy"

    def test_primary_key(self) -> None:
        assert POLICIES_TABLE.primary_key == "policy_id"

    def test_column_count(self) -> None:
        assert len(POLICIES_TABLE.columns) == 9

    def test_policy_id_column(self) -> None:
        col = POLICIES_TABLE.columns[0]
        assert col.name == "policy_id"
        assert col.py_type is str
        assert col.nullable is False

    def test_name_column(self) -> None:
        col = POLICIES_TABLE.columns[1]
        assert col.name == "name"
        assert col.py_type is str
        assert col.nullable is True

    def test_description_column(self) -> None:
        col = POLICIES_TABLE.columns[2]
        assert col.name == "description"
        assert col.py_type is str
        assert col.nullable is True

    def test_status_column(self) -> None:
        col = POLICIES_TABLE.columns[3]
        assert col.name == "status"
        assert col.py_type is str
        assert col.nullable is False
        assert col.max_length == 16
        assert col.enum_values == (
            "draft", "active", "disabled", "archived",
        )

    def test_priority_column(self) -> None:
        col = POLICIES_TABLE.columns[4]
        assert col.name == "priority"
        assert col.py_type is str
        assert col.nullable is False
        assert col.max_length == 16
        assert col.enum_values == ("low", "medium", "high", "critical")

    def test_scope_column(self) -> None:
        col = POLICIES_TABLE.columns[5]
        assert col.name == "scope"
        assert col.py_type is str
        assert col.nullable is False
        assert col.max_length == 16
        assert col.enum_values == (
            "global", "user", "agent", "automation", "workflow",
        )

    def test_version_column(self) -> None:
        col = POLICIES_TABLE.columns[6]
        assert col.name == "version"
        assert col.py_type is str
        assert col.nullable is True

    def test_created_at_column(self) -> None:
        col = POLICIES_TABLE.columns[7]
        assert col.name == "created_at"
        assert col.py_type is datetime
        assert col.nullable is False

    def test_updated_at_column(self) -> None:
        col = POLICIES_TABLE.columns[8]
        assert col.name == "updated_at"
        assert col.py_type is datetime
        assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_policies_status" in POLICIES_TABLE.indexes
        assert "ix_policies_priority" in POLICIES_TABLE.indexes
        assert "ix_policies_scope" in POLICIES_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(POLICIES_TABLE.indexes) == 3


class TestPolicyRulesTableSchema:
    def test_table_name(self) -> None:
        assert POLICY_RULES_TABLE.name == "rules"

    def test_schema_name(self) -> None:
        assert POLICY_RULES_TABLE.schema == "policy"

    def test_primary_key(self) -> None:
        assert POLICY_RULES_TABLE.primary_key == "rule_id"

    def test_column_count(self) -> None:
        assert len(POLICY_RULES_TABLE.columns) == 6

    def test_rule_id_column(self) -> None:
        col = POLICY_RULES_TABLE.columns[0]
        assert col.name == "rule_id"
        assert col.py_type is str
        assert col.nullable is False

    def test_policy_id_column(self) -> None:
        col = POLICY_RULES_TABLE.columns[1]
        assert col.name == "policy_id"
        assert col.py_type is str
        assert col.nullable is True

    def test_condition_column(self) -> None:
        col = POLICY_RULES_TABLE.columns[2]
        assert col.name == "condition"
        assert col.py_type is str
        assert col.nullable is True

    def test_action_column(self) -> None:
        col = POLICY_RULES_TABLE.columns[3]
        assert col.name == "action"
        assert col.py_type is str
        assert col.nullable is True

    def test_priority_column(self) -> None:
        col = POLICY_RULES_TABLE.columns[4]
        assert col.name == "priority"
        assert col.py_type is int
        assert col.nullable is False

    def test_enabled_column(self) -> None:
        col = POLICY_RULES_TABLE.columns[5]
        assert col.name == "enabled"
        assert col.py_type is bool
        assert col.nullable is False

    def test_indexes(self) -> None:
        assert "ix_policy_rules_policy_id" in POLICY_RULES_TABLE.indexes
        assert "ix_policy_rules_priority" in POLICY_RULES_TABLE.indexes
        assert "ix_policy_rules_enabled" in POLICY_RULES_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(POLICY_RULES_TABLE.indexes) == 3


class TestPolicyEvaluationsTableSchema:
    def test_table_name(self) -> None:
        assert POLICY_EVALUATIONS_TABLE.name == "evaluations"

    def test_schema_name(self) -> None:
        assert POLICY_EVALUATIONS_TABLE.schema == "policy"

    def test_primary_key(self) -> None:
        assert POLICY_EVALUATIONS_TABLE.primary_key == "evaluation_id"

    def test_column_count(self) -> None:
        assert len(POLICY_EVALUATIONS_TABLE.columns) == 8

    def test_evaluation_id_column(self) -> None:
        col = POLICY_EVALUATIONS_TABLE.columns[0]
        assert col.name == "evaluation_id"
        assert col.py_type is str
        assert col.nullable is False

    def test_policy_id_column(self) -> None:
        col = POLICY_EVALUATIONS_TABLE.columns[1]
        assert col.name == "policy_id"
        assert col.py_type is str
        assert col.nullable is True

    def test_status_column(self) -> None:
        col = POLICY_EVALUATIONS_TABLE.columns[2]
        assert col.name == "status"
        assert col.py_type is str
        assert col.nullable is False
        assert col.max_length == 16
        assert col.enum_values == (
            "pending", "evaluating", "completed", "failed",
        )

    def test_decision_column(self) -> None:
        col = POLICY_EVALUATIONS_TABLE.columns[3]
        assert col.name == "decision"
        assert col.py_type is str
        assert col.nullable is True
        assert col.max_length == 16
        assert col.enum_values == ("allow", "deny", "review")

    def test_result_column(self) -> None:
        col = POLICY_EVALUATIONS_TABLE.columns[4]
        assert col.name == "result"
        assert col.py_type is str
        assert col.nullable is True

    def test_failure_reason_column(self) -> None:
        col = POLICY_EVALUATIONS_TABLE.columns[5]
        assert col.name == "failure_reason"
        assert col.py_type is str
        assert col.nullable is True

    def test_started_at_column(self) -> None:
        col = POLICY_EVALUATIONS_TABLE.columns[6]
        assert col.name == "started_at"
        assert col.py_type is datetime
        assert col.nullable is True

    def test_completed_at_column(self) -> None:
        col = POLICY_EVALUATIONS_TABLE.columns[7]
        assert col.name == "completed_at"
        assert col.py_type is datetime
        assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_policy_evaluations_policy_id" in POLICY_EVALUATIONS_TABLE.indexes
        assert "ix_policy_evaluations_status" in POLICY_EVALUATIONS_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(POLICY_EVALUATIONS_TABLE.indexes) == 2


class TestPolicyOutboxTableSchema:
    def test_table_name(self) -> None:
        assert POLICY_OUTBOX_TABLE.name == "outbox"

    def test_schema_name(self) -> None:
        assert POLICY_OUTBOX_TABLE.schema == "policy"

    def test_primary_key(self) -> None:
        assert POLICY_OUTBOX_TABLE.primary_key == "event_id"

    def test_column_count(self) -> None:
        assert len(POLICY_OUTBOX_TABLE.columns) == 6

    def test_event_id_column(self) -> None:
        col = POLICY_OUTBOX_TABLE.columns[0]
        assert col.name == "event_id"
        assert col.py_type is str
        assert col.nullable is False

    def test_event_type_column(self) -> None:
        col = POLICY_OUTBOX_TABLE.columns[1]
        assert col.name == "event_type"
        assert col.py_type is str
        assert col.nullable is False
        assert col.max_length == 32
        assert col.enum_values == (
            "policy.created",
            "policy.activated",
            "policy.disabled",
            "policy.archived",
            "policy.rule_added",
            "policy.rule_removed",
            "policy.rule_enabled",
            "policy.rule_disabled",
            "policy.evaluation_started",
            "policy.evaluation_completed",
            "policy.evaluation_failed",
        )

    def test_aggregate_id_column(self) -> None:
        col = POLICY_OUTBOX_TABLE.columns[2]
        assert col.name == "aggregate_id"
        assert col.py_type is str
        assert col.nullable is False

    def test_occurred_at_column(self) -> None:
        col = POLICY_OUTBOX_TABLE.columns[3]
        assert col.name == "occurred_at"
        assert col.py_type is datetime
        assert col.nullable is False

    def test_payload_column(self) -> None:
        col = POLICY_OUTBOX_TABLE.columns[4]
        assert col.name == "payload"
        assert col.py_type is str
        assert col.nullable is True

    def test_published_column(self) -> None:
        col = POLICY_OUTBOX_TABLE.columns[5]
        assert col.name == "published"
        assert col.py_type is bool
        assert col.nullable is False

    def test_indexes(self) -> None:
        assert "ix_policy_outbox_unpublished" in POLICY_OUTBOX_TABLE.indexes
        assert "ix_policy_outbox_aggregate" in POLICY_OUTBOX_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(POLICY_OUTBOX_TABLE.indexes) == 2


# ===================================================================
# Section 4: Alignment Tests
# ===================================================================


class TestDTOAlignmentPolicy:
    def test_dto_field_count_matches_schema_column_count(self) -> None:
        import dataclasses
        dto_fields = dataclasses.fields(PolicyStorageDTO)
        schema_cols = POLICIES_TABLE.columns
        assert len(dto_fields) == len(schema_cols)

    def test_dto_field_names_match_schema_column_names(self) -> None:
        import dataclasses
        dto_names = {f.name for f in dataclasses.fields(PolicyStorageDTO)}
        schema_names = {c.name for c in POLICIES_TABLE.columns}
        assert dto_names == schema_names

    def test_domain_enum_values_match_schema_status_enum(self) -> None:
        schema_values = set(POLICIES_TABLE.columns[3].enum_values or ())
        domain_values = {s.value for s in PolicyStatus}
        assert schema_values == domain_values

    def test_domain_enum_values_match_schema_priority_enum(self) -> None:
        schema_values = set(POLICIES_TABLE.columns[4].enum_values or ())
        domain_values = {p.value for p in PolicyPriority}
        assert schema_values == domain_values

    def test_domain_enum_values_match_schema_scope_enum(self) -> None:
        schema_values = set(POLICIES_TABLE.columns[5].enum_values or ())
        domain_values = {s.value for s in PolicyScope}
        assert schema_values == domain_values

    def test_domain_nullable_fields_match_dto_nullable(self) -> None:
        assert PolicyStorageDTO.__dataclass_fields__["name"].default is None
        assert PolicyStorageDTO.__dataclass_fields__["description"].default is None
        assert PolicyStorageDTO.__dataclass_fields__["version"].default is None
        assert PolicyStorageDTO.__dataclass_fields__["updated_at"].default is None


class TestDTOAlignmentRules:
    def test_dto_field_count_matches_schema_column_count(self) -> None:
        import dataclasses
        dto_fields = dataclasses.fields(PolicyRuleStorageDTO)
        schema_cols = POLICY_RULES_TABLE.columns
        assert len(dto_fields) == len(schema_cols)

    def test_dto_field_names_match_schema_column_names(self) -> None:
        import dataclasses
        dto_names = {f.name for f in dataclasses.fields(PolicyRuleStorageDTO)}
        schema_names = {c.name for c in POLICY_RULES_TABLE.columns}
        assert dto_names == schema_names

    def test_condition_nullable_parity(self) -> None:
        schema_col = POLICY_RULES_TABLE.columns[2]
        assert schema_col.nullable is True
        assert PolicyRuleStorageDTO.__dataclass_fields__["condition"].default is None

    def test_action_nullable_parity(self) -> None:
        schema_col = POLICY_RULES_TABLE.columns[3]
        assert schema_col.nullable is True
        assert PolicyRuleStorageDTO.__dataclass_fields__["action"].default is None


class TestDTOAlignmentEvaluations:
    def test_dto_field_count_matches_schema_column_count(self) -> None:
        import dataclasses
        dto_fields = dataclasses.fields(PolicyEvaluationStorageDTO)
        schema_cols = POLICY_EVALUATIONS_TABLE.columns
        assert len(dto_fields) == len(schema_cols)

    def test_dto_field_names_match_schema_column_names(self) -> None:
        import dataclasses
        dto_names = {f.name for f in dataclasses.fields(PolicyEvaluationStorageDTO)}
        schema_names = {c.name for c in POLICY_EVALUATIONS_TABLE.columns}
        assert dto_names == schema_names

    def test_domain_enum_values_match_schema_status_enum(self) -> None:
        schema_values = set(POLICY_EVALUATIONS_TABLE.columns[2].enum_values or ())
        domain_values = {s.value for s in PolicyEvaluationStatus}
        assert schema_values == domain_values

    def test_domain_enum_values_match_schema_decision_enum(self) -> None:
        schema_values = set(POLICY_EVALUATIONS_TABLE.columns[3].enum_values or ())
        domain_values = {d.value for d in PolicyDecision}
        assert schema_values == domain_values

    def test_decision_nullable_parity(self) -> None:
        schema_col = POLICY_EVALUATIONS_TABLE.columns[3]
        assert schema_col.nullable is True
        assert PolicyEvaluationStorageDTO.__dataclass_fields__["decision"].default is None

    def test_result_nullable_parity(self) -> None:
        schema_col = POLICY_EVALUATIONS_TABLE.columns[4]
        assert schema_col.nullable is True
        assert PolicyEvaluationStorageDTO.__dataclass_fields__["result"].default is None

    def test_failure_reason_nullable_parity(self) -> None:
        schema_col = POLICY_EVALUATIONS_TABLE.columns[5]
        assert schema_col.nullable is True
        assert PolicyEvaluationStorageDTO.__dataclass_fields__["failure_reason"].default is None

    def test_started_at_nullable_parity(self) -> None:
        schema_col = POLICY_EVALUATIONS_TABLE.columns[6]
        assert schema_col.nullable is True
        assert PolicyEvaluationStorageDTO.__dataclass_fields__["started_at"].default is None

    def test_completed_at_nullable_parity(self) -> None:
        schema_col = POLICY_EVALUATIONS_TABLE.columns[7]
        assert schema_col.nullable is True
        assert PolicyEvaluationStorageDTO.__dataclass_fields__["completed_at"].default is None


class TestDTOAlignmentOutbox:
    def test_dto_field_count_matches_schema_column_count(self) -> None:
        import dataclasses
        dto_fields = dataclasses.fields(PolicyOutboxStorageDTO)
        schema_cols = POLICY_OUTBOX_TABLE.columns
        assert len(dto_fields) == len(schema_cols)

    def test_dto_field_names_match_schema_column_names(self) -> None:
        import dataclasses
        dto_names = {f.name for f in dataclasses.fields(PolicyOutboxStorageDTO)}
        schema_names = {c.name for c in POLICY_OUTBOX_TABLE.columns}
        assert dto_names == schema_names

    def test_payload_nullable_parity(self) -> None:
        schema_col = POLICY_OUTBOX_TABLE.columns[4]
        assert schema_col.nullable is True
        assert PolicyOutboxStorageDTO.__dataclass_fields__["payload"].default is None


# ===================================================================
# Section 5: Outbox Event Union Conformance
# ===================================================================


class TestPolicyOutboxEventUnion:
    def test_policy_created_is_event(self) -> None:
        event: PolicyOutboxDomainEvent = PolicyCreated(
            policy_id=PolicyId(),
            name="n", description="d", priority="medium",
            scope="global", version="1.0.0",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_activated_is_event(self) -> None:
        event: PolicyOutboxDomainEvent = PolicyActivated(
            policy_id=PolicyId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_disabled_is_event(self) -> None:
        event: PolicyOutboxDomainEvent = PolicyDisabled(
            policy_id=PolicyId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_archived_is_event(self) -> None:
        event: PolicyOutboxDomainEvent = PolicyArchived(
            policy_id=PolicyId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_rule_added_is_event(self) -> None:
        event: PolicyOutboxDomainEvent = PolicyRuleAdded(
            rule_id=PolicyRuleId(), policy_id=PolicyId(),
            condition="true", action="allow",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_rule_removed_is_event(self) -> None:
        event: PolicyOutboxDomainEvent = PolicyRuleRemoved(
            rule_id=PolicyRuleId(), policy_id=PolicyId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_rule_enabled_is_event(self) -> None:
        event: PolicyOutboxDomainEvent = PolicyRuleEnabled(
            rule_id=PolicyRuleId(), policy_id=PolicyId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_rule_disabled_is_event(self) -> None:
        event: PolicyOutboxDomainEvent = PolicyRuleDisabled(
            rule_id=PolicyRuleId(), policy_id=PolicyId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_evaluation_started_is_event(self) -> None:
        event: PolicyOutboxDomainEvent = PolicyEvaluationStarted(
            policy_id=PolicyId(),
            evaluation_id=EvaluationId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_evaluation_completed_is_event(self) -> None:
        event: PolicyOutboxDomainEvent = PolicyEvaluationCompleted(
            policy_id=PolicyId(),
            evaluation_id=EvaluationId(),
            decision="allow", result="ok",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_evaluation_failed_is_event(self) -> None:
        event: PolicyOutboxDomainEvent = PolicyEvaluationFailed(
            policy_id=PolicyId(),
            evaluation_id=EvaluationId(),
            failure_reason="err",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_all_events_count(self) -> None:
        event_types = PolicyOutboxDomainEvent.__args__
        assert len(event_types) == 11

    def test_schema_enum_count_matches(self) -> None:
        schema_values = POLICY_OUTBOX_TABLE.columns[1].enum_values
        assert schema_values is not None
        assert len(schema_values) == 11

    def test_schema_enum_values_match_event_types(self) -> None:
        schema_values = set(POLICY_OUTBOX_TABLE.columns[1].enum_values or ())
        expected = {
            "policy.created",
            "policy.activated",
            "policy.disabled",
            "policy.archived",
            "policy.rule_added",
            "policy.rule_removed",
            "policy.rule_enabled",
            "policy.rule_disabled",
            "policy.evaluation_started",
            "policy.evaluation_completed",
            "policy.evaluation_failed",
        }
        assert schema_values == expected


# ===================================================================
# Section 6: Mapper Protocol Method Signature Verification
# ===================================================================


class TestPolicyMapperProtocol:
    def test_domain_to_dto_signature(self) -> None:
        method = PolicyMapper.domain_to_dto
        assert callable(method)

    def test_dto_to_domain_signature(self) -> None:
        method = PolicyMapper.dto_to_domain
        assert callable(method)

    def test_protocol_has_required_methods(self) -> None:
        methods = {"domain_to_dto", "dto_to_domain"}
        protocol_methods = {
            m for m in dir(PolicyMapper) if not m.startswith("_")
        }
        assert methods.issubset(protocol_methods)


class TestRuleMapperProtocol:
    def test_protocol_has_required_methods(self) -> None:
        methods = {"domain_to_dto", "dto_to_domain"}
        protocol_methods = {
            m for m in dir(PolicyRuleMapper) if not m.startswith("_")
        }
        assert methods.issubset(protocol_methods)


class TestEvaluationMapperProtocol:
    def test_protocol_has_required_methods(self) -> None:
        methods = {"domain_to_dto", "dto_to_domain"}
        protocol_methods = {
            m for m in dir(PolicyEvaluationMapper) if not m.startswith("_")
        }
        assert methods.issubset(protocol_methods)


class TestOutboxMapperProtocol:
    def test_protocol_has_required_methods(self) -> None:
        methods = {"event_to_dto", "dto_to_event"}
        protocol_methods = {
            m for m in dir(PolicyOutboxMapper) if not m.startswith("_")
        }
        assert methods.issubset(protocol_methods)


class TestMapperInstantiation:
    def test_policy_mapper_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            PolicyMapper()

    def test_rule_mapper_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            PolicyRuleMapper()

    def test_evaluation_mapper_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            PolicyEvaluationMapper()

    def test_outbox_mapper_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            PolicyOutboxMapper()


# ===================================================================
# Section 7: Module Importability
# ===================================================================


class TestModuleImportability:
    def test_persistence_modules_importable(self) -> None:
        from backend.policy.application.persistence import (
            PolicyEvaluationStorageDTO,
            PolicyOutboxStorageDTO,
            PolicyRuleStorageDTO,
            PolicyStorageDTO,
        )
        assert PolicyStorageDTO is not None
        assert PolicyRuleStorageDTO is not None
        assert PolicyEvaluationStorageDTO is not None
        assert PolicyOutboxStorageDTO is not None
