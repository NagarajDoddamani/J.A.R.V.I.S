from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.policy.domain.exceptions import (
    DecisionRequiredError,
    DuplicateRuleConditionError,
    DuplicateRuleIdError,
    EvaluationNotFoundError,
    EvaluationNotStartedError,
    InvalidEvaluationResultError,
    InvalidFailureReasonError,
    InvalidPolicyActionError,
    InvalidPolicyConditionError,
    InvalidPolicyDescriptionError,
    InvalidPolicyNameError,
    InvalidPolicyVersionError,
    InvalidPriorityError,
    InvalidTransitionError,
    PolicyDisabledError,
    PolicyHasNoRulesError,
    PolicyNotModifiableError,
    PolicyTerminalError,
    RuleAlreadyDisabledError,
    RuleAlreadyEnabledError,
    RuleNotFoundError,
)
from backend.policy.domain.factory import PolicyFactory
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
    VALID_EVALUATION_TRANSITIONS,
    VALID_POLICY_TRANSITIONS,
)
from backend.policy.domain.rules import (
    assert_decision_required,
    assert_evaluation_can_transition,
    assert_evaluation_result_required,
    assert_evaluation_started_before,
    assert_failure_reason_required,
    assert_policy_can_transition,
    assert_policy_description_required,
    assert_policy_has_rules,
    assert_policy_modifiable,
    assert_policy_name_required,
    assert_policy_not_disabled,
    assert_policy_not_terminal,
    assert_policy_version_required,
    assert_priority_valid,
    assert_rule_action_required,
    assert_rule_condition_required,
    assert_rule_condition_unique,
    assert_rule_id_unique,
    assert_rule_not_disabled_twice,
    assert_rule_not_enabled_twice,
)


# ===========================================================================
# Helpers
# ===========================================================================


def make_valid_policy(
    name: str = "Access Control",
    description: str = "Controls user access",
    priority: PolicyPriority = PolicyPriority.MEDIUM,
    scope: PolicyScope = PolicyScope.GLOBAL,
) -> Policy:
    p, _ = PolicyFactory.create_policy(
        name=name,
        description=description,
        priority=priority,
        scope=scope,
    )
    return p


def make_ready_policy() -> Policy:
    p = make_valid_policy()
    rule = PolicyRule(
        condition=PolicyCondition(value="user.role == admin"),
        action=PolicyAction(value="allow"),
    )
    p.add_rule(rule)
    return p


# =============================================================================
# 1. Value Object Tests
# =============================================================================


class TestPolicyId:
    def test_creation(self) -> None:
        pid = PolicyId()
        assert isinstance(pid.value, UUID)

    def test_str_representation(self) -> None:
        pid = PolicyId()
        assert str(pid) == str(pid.value)

    def test_equality(self) -> None:
        v = UUID("00000000-0000-0000-0000-000000000001")
        assert PolicyId(value=v) == PolicyId(value=v)

    def test_inequality(self) -> None:
        assert PolicyId() != PolicyId()

    def test_immutability(self) -> None:
        pid = PolicyId()
        with pytest.raises(AttributeError):
            pid.value = UUID(int=0)

    def test_default_factory(self) -> None:
        pid = PolicyId()
        assert pid.value is not None


class TestPolicyRuleId:
    def test_creation(self) -> None:
        rid = PolicyRuleId()
        assert isinstance(rid.value, UUID)

    def test_str_representation(self) -> None:
        rid = PolicyRuleId()
        assert str(rid) == str(rid.value)

    def test_equality(self) -> None:
        v = UUID("00000000-0000-0000-0000-000000000002")
        assert PolicyRuleId(value=v) == PolicyRuleId(value=v)

    def test_inequality(self) -> None:
        assert PolicyRuleId() != PolicyRuleId()

    def test_immutability(self) -> None:
        rid = PolicyRuleId()
        with pytest.raises(AttributeError):
            rid.value = UUID(int=0)


class TestEvaluationId:
    def test_creation(self) -> None:
        eid = EvaluationId()
        assert isinstance(eid.value, UUID)

    def test_str_representation(self) -> None:
        eid = EvaluationId()
        assert str(eid) == str(eid.value)

    def test_equality(self) -> None:
        v = UUID("00000000-0000-0000-0000-000000000003")
        assert EvaluationId(value=v) == EvaluationId(value=v)

    def test_inequality(self) -> None:
        assert EvaluationId() != EvaluationId()

    def test_immutability(self) -> None:
        eid = EvaluationId()
        with pytest.raises(AttributeError):
            eid.value = UUID(int=0)


class TestPolicyName:
    def test_creation(self) -> None:
        n = PolicyName(value="Access Control")
        assert n.value == "Access Control"

    def test_str_conversion(self) -> None:
        n = PolicyName(value="Policy")
        assert str(n) == "Policy"

    def test_length(self) -> None:
        n = PolicyName(value="abcd")
        assert len(n) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidPolicyNameError, match="not be empty"):
            PolicyName(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidPolicyNameError, match="not be empty"):
            PolicyName(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            PolicyName(value=123)

    def test_equality(self) -> None:
        assert PolicyName(value="a") == PolicyName(value="a")

    def test_frozen(self) -> None:
        n = PolicyName(value="a")
        with pytest.raises(AttributeError):
            n.value = "b"


class TestPolicyDescription:
    def test_creation(self) -> None:
        d = PolicyDescription(value="Controls access")
        assert d.value == "Controls access"

    def test_str_conversion(self) -> None:
        d = PolicyDescription(value="Desc")
        assert str(d) == "Desc"

    def test_length(self) -> None:
        d = PolicyDescription(value="abcd")
        assert len(d) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidPolicyDescriptionError, match="not be empty"):
            PolicyDescription(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidPolicyDescriptionError, match="not be empty"):
            PolicyDescription(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            PolicyDescription(value=123)

    def test_equality(self) -> None:
        assert PolicyDescription(value="a") == PolicyDescription(value="a")

    def test_frozen(self) -> None:
        d = PolicyDescription(value="a")
        with pytest.raises(AttributeError):
            d.value = "b"


class TestPolicyCondition:
    def test_creation(self) -> None:
        c = PolicyCondition(value="user.role == admin")
        assert c.value == "user.role == admin"

    def test_str_conversion(self) -> None:
        c = PolicyCondition(value="cond")
        assert str(c) == "cond"

    def test_length(self) -> None:
        c = PolicyCondition(value="abcd")
        assert len(c) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidPolicyConditionError, match="not be empty"):
            PolicyCondition(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidPolicyConditionError, match="not be empty"):
            PolicyCondition(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            PolicyCondition(value=123)

    def test_equality(self) -> None:
        assert PolicyCondition(value="a") == PolicyCondition(value="a")

    def test_frozen(self) -> None:
        c = PolicyCondition(value="a")
        with pytest.raises(AttributeError):
            c.value = "b"


class TestPolicyAction:
    def test_creation(self) -> None:
        a = PolicyAction(value="allow")
        assert a.value == "allow"

    def test_str_conversion(self) -> None:
        a = PolicyAction(value="deny")
        assert str(a) == "deny"

    def test_length(self) -> None:
        a = PolicyAction(value="abcd")
        assert len(a) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidPolicyActionError, match="not be empty"):
            PolicyAction(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidPolicyActionError, match="not be empty"):
            PolicyAction(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            PolicyAction(value=123)

    def test_equality(self) -> None:
        assert PolicyAction(value="a") == PolicyAction(value="a")

    def test_frozen(self) -> None:
        a = PolicyAction(value="a")
        with pytest.raises(AttributeError):
            a.value = "b"


class TestPolicyVersion:
    def test_creation(self) -> None:
        v = PolicyVersion(value="1.0.0")
        assert v.value == "1.0.0"

    def test_str_conversion(self) -> None:
        v = PolicyVersion(value="2.3.1")
        assert str(v) == "2.3.1"

    def test_length(self) -> None:
        v = PolicyVersion(value="1.0.0")
        assert len(v) == 5

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidPolicyVersionError, match="not be empty"):
            PolicyVersion(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidPolicyVersionError, match="not be empty"):
            PolicyVersion(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            PolicyVersion(value=123)

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(InvalidPolicyVersionError, match="semver"):
            PolicyVersion(value="abc")

    def test_invalid_format_no_patch(self) -> None:
        with pytest.raises(InvalidPolicyVersionError, match="semver"):
            PolicyVersion(value="1.0")

    def test_invalid_format_no_minor(self) -> None:
        with pytest.raises(InvalidPolicyVersionError, match="semver"):
            PolicyVersion(value="1")

    def test_equality(self) -> None:
        assert PolicyVersion(value="1.0.0") == PolicyVersion(value="1.0.0")

    def test_frozen(self) -> None:
        v = PolicyVersion(value="1.0.0")
        with pytest.raises(AttributeError):
            v.value = "2.0.0"


class TestFailureReason:
    def test_creation(self) -> None:
        r = FailureReason(value="Timeout")
        assert r.value == "Timeout"

    def test_str_conversion(self) -> None:
        r = FailureReason(value="Error")
        assert str(r) == "Error"

    def test_length(self) -> None:
        r = FailureReason(value="abcd")
        assert len(r) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidFailureReasonError, match="not be empty"):
            FailureReason(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidFailureReasonError, match="not be empty"):
            FailureReason(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            FailureReason(value=123)

    def test_equality(self) -> None:
        assert FailureReason(value="a") == FailureReason(value="a")

    def test_frozen(self) -> None:
        r = FailureReason(value="a")
        with pytest.raises(AttributeError):
            r.value = "b"


class TestEvaluationResult:
    def test_creation(self) -> None:
        r = EvaluationResult(value="Allowed")
        assert r.value == "Allowed"

    def test_str_conversion(self) -> None:
        r = EvaluationResult(value="Denied")
        assert str(r) == "Denied"

    def test_length(self) -> None:
        r = EvaluationResult(value="abcd")
        assert len(r) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidEvaluationResultError, match="not be empty"):
            EvaluationResult(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidEvaluationResultError, match="not be empty"):
            EvaluationResult(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            EvaluationResult(value=123)

    def test_equality(self) -> None:
        assert EvaluationResult(value="a") == EvaluationResult(value="a")

    def test_frozen(self) -> None:
        r = EvaluationResult(value="a")
        with pytest.raises(AttributeError):
            r.value = "b"


# =============================================================================
# 2. Enum Tests
# =============================================================================


class TestPolicyStatus:
    def test_values(self) -> None:
        assert PolicyStatus.DRAFT.value == "draft"
        assert PolicyStatus.ACTIVE.value == "active"
        assert PolicyStatus.DISABLED.value == "disabled"
        assert PolicyStatus.ARCHIVED.value == "archived"

    def test_count(self) -> None:
        assert len(PolicyStatus) == 4

    def test_ordered(self) -> None:
        values = list(PolicyStatus)
        assert values == [
            PolicyStatus.DRAFT,
            PolicyStatus.ACTIVE,
            PolicyStatus.DISABLED,
            PolicyStatus.ARCHIVED,
        ]


class TestPolicyPriority:
    def test_values(self) -> None:
        assert PolicyPriority.LOW.value == "low"
        assert PolicyPriority.MEDIUM.value == "medium"
        assert PolicyPriority.HIGH.value == "high"
        assert PolicyPriority.CRITICAL.value == "critical"

    def test_count(self) -> None:
        assert len(PolicyPriority) == 4

    def test_ordered(self) -> None:
        values = list(PolicyPriority)
        assert values == [
            PolicyPriority.LOW,
            PolicyPriority.MEDIUM,
            PolicyPriority.HIGH,
            PolicyPriority.CRITICAL,
        ]


class TestPolicyDecision:
    def test_values(self) -> None:
        assert PolicyDecision.ALLOW.value == "allow"
        assert PolicyDecision.DENY.value == "deny"
        assert PolicyDecision.REVIEW.value == "review"

    def test_count(self) -> None:
        assert len(PolicyDecision) == 3

    def test_ordered(self) -> None:
        values = list(PolicyDecision)
        assert values == [
            PolicyDecision.ALLOW,
            PolicyDecision.DENY,
            PolicyDecision.REVIEW,
        ]


class TestPolicyEvaluationStatus:
    def test_values(self) -> None:
        assert PolicyEvaluationStatus.PENDING.value == "pending"
        assert PolicyEvaluationStatus.EVALUATING.value == "evaluating"
        assert PolicyEvaluationStatus.COMPLETED.value == "completed"
        assert PolicyEvaluationStatus.FAILED.value == "failed"

    def test_count(self) -> None:
        assert len(PolicyEvaluationStatus) == 4

    def test_ordered(self) -> None:
        values = list(PolicyEvaluationStatus)
        assert values == [
            PolicyEvaluationStatus.PENDING,
            PolicyEvaluationStatus.EVALUATING,
            PolicyEvaluationStatus.COMPLETED,
            PolicyEvaluationStatus.FAILED,
        ]


class TestPolicyScope:
    def test_values(self) -> None:
        assert PolicyScope.GLOBAL.value == "global"
        assert PolicyScope.USER.value == "user"
        assert PolicyScope.AGENT.value == "agent"
        assert PolicyScope.AUTOMATION.value == "automation"
        assert PolicyScope.WORKFLOW.value == "workflow"

    def test_count(self) -> None:
        assert len(PolicyScope) == 5

    def test_ordered(self) -> None:
        values = list(PolicyScope)
        assert values == [
            PolicyScope.GLOBAL,
            PolicyScope.USER,
            PolicyScope.AGENT,
            PolicyScope.AUTOMATION,
            PolicyScope.WORKFLOW,
        ]


class TestValidTransitions:
    def test_policy_transitions_draft(self) -> None:
        assert PolicyStatus.DRAFT in VALID_POLICY_TRANSITIONS
        assert VALID_POLICY_TRANSITIONS[PolicyStatus.DRAFT] == {PolicyStatus.ACTIVE, PolicyStatus.ARCHIVED}

    def test_policy_transitions_active(self) -> None:
        assert PolicyStatus.ACTIVE in VALID_POLICY_TRANSITIONS
        assert VALID_POLICY_TRANSITIONS[PolicyStatus.ACTIVE] == {PolicyStatus.DISABLED, PolicyStatus.ARCHIVED}

    def test_policy_transitions_disabled(self) -> None:
        assert PolicyStatus.DISABLED in VALID_POLICY_TRANSITIONS
        assert VALID_POLICY_TRANSITIONS[PolicyStatus.DISABLED] == {PolicyStatus.ACTIVE, PolicyStatus.ARCHIVED}

    def test_policy_transitions_archived(self) -> None:
        assert PolicyStatus.ARCHIVED in VALID_POLICY_TRANSITIONS
        assert VALID_POLICY_TRANSITIONS[PolicyStatus.ARCHIVED] == set()

    def test_policy_transitions_count(self) -> None:
        total = sum(len(v) for v in VALID_POLICY_TRANSITIONS.values())
        assert total == 6

    def test_policy_transitions_all_keys(self) -> None:
        assert set(VALID_POLICY_TRANSITIONS.keys()) == set(PolicyStatus)

    def test_evaluation_transitions_pending(self) -> None:
        assert PolicyEvaluationStatus.PENDING in VALID_EVALUATION_TRANSITIONS
        assert VALID_EVALUATION_TRANSITIONS[PolicyEvaluationStatus.PENDING] == {PolicyEvaluationStatus.EVALUATING}

    def test_evaluation_transitions_evaluating(self) -> None:
        assert PolicyEvaluationStatus.EVALUATING in VALID_EVALUATION_TRANSITIONS
        assert VALID_EVALUATION_TRANSITIONS[PolicyEvaluationStatus.EVALUATING] == {PolicyEvaluationStatus.COMPLETED, PolicyEvaluationStatus.FAILED}

    def test_evaluation_transitions_completed(self) -> None:
        assert PolicyEvaluationStatus.COMPLETED in VALID_EVALUATION_TRANSITIONS
        assert VALID_EVALUATION_TRANSITIONS[PolicyEvaluationStatus.COMPLETED] == set()

    def test_evaluation_transitions_failed(self) -> None:
        assert PolicyEvaluationStatus.FAILED in VALID_EVALUATION_TRANSITIONS
        assert VALID_EVALUATION_TRANSITIONS[PolicyEvaluationStatus.FAILED] == set()

    def test_evaluation_transitions_count(self) -> None:
        total = sum(len(v) for v in VALID_EVALUATION_TRANSITIONS.values())
        assert total == 3

    def test_evaluation_transitions_all_keys(self) -> None:
        assert set(VALID_EVALUATION_TRANSITIONS.keys()) == set(PolicyEvaluationStatus)


# =============================================================================
# 3. Domain Event Tests
# =============================================================================


class TestPolicyCreated:
    def test_creation(self) -> None:
        pid = PolicyId()
        now = datetime.now(tz=timezone.utc)
        event = PolicyCreated(
            policy_id=pid,
            name="Test",
            description="Desc",
            priority="medium",
            scope="global",
            version="1.0.0",
            occurred_at=now,
        )
        assert event.policy_id == pid
        assert event.name == "Test"
        assert event.description == "Desc"
        assert event.priority == "medium"
        assert event.scope == "global"
        assert event.version == "1.0.0"
        assert event.occurred_at == now
        assert isinstance(event.event_id, UUID)

    def test_immutability(self) -> None:
        event = PolicyCreated(
            policy_id=PolicyId(),
            name="T",
            description="D",
            priority="high",
            scope="user",
            version="1.0.0",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            event.name = "changed"


class TestPolicyActivated:
    def test_creation(self) -> None:
        pid = PolicyId()
        now = datetime.now(tz=timezone.utc)
        event = PolicyActivated(policy_id=pid, occurred_at=now)
        assert event.policy_id == pid
        assert event.occurred_at == now
        assert isinstance(event.event_id, UUID)


class TestPolicyDisabled:
    def test_creation(self) -> None:
        event = PolicyDisabled(policy_id=PolicyId(), occurred_at=datetime.now(tz=timezone.utc))
        assert isinstance(event.event_id, UUID)


class TestPolicyArchived:
    def test_creation(self) -> None:
        event = PolicyArchived(policy_id=PolicyId(), occurred_at=datetime.now(tz=timezone.utc))
        assert isinstance(event.event_id, UUID)


class TestPolicyRuleAdded:
    def test_creation(self) -> None:
        rid = PolicyRuleId()
        pid = PolicyId()
        now = datetime.now(tz=timezone.utc)
        event = PolicyRuleAdded(rule_id=rid, policy_id=pid, condition="c", action="a", occurred_at=now)
        assert event.rule_id == rid
        assert event.policy_id == pid
        assert event.condition == "c"
        assert event.action == "a"


class TestPolicyRuleRemoved:
    def test_creation(self) -> None:
        event = PolicyRuleRemoved(rule_id=PolicyRuleId(), policy_id=PolicyId(), occurred_at=datetime.now(tz=timezone.utc))
        assert isinstance(event.event_id, UUID)


class TestPolicyRuleEnabled:
    def test_creation(self) -> None:
        event = PolicyRuleEnabled(rule_id=PolicyRuleId(), policy_id=PolicyId(), occurred_at=datetime.now(tz=timezone.utc))
        assert isinstance(event.event_id, UUID)


class TestPolicyRuleDisabled:
    def test_creation(self) -> None:
        event = PolicyRuleDisabled(rule_id=PolicyRuleId(), policy_id=PolicyId(), occurred_at=datetime.now(tz=timezone.utc))
        assert isinstance(event.event_id, UUID)


class TestPolicyEvaluationStarted:
    def test_creation(self) -> None:
        eid = EvaluationId()
        pid = PolicyId()
        event = PolicyEvaluationStarted(policy_id=pid, evaluation_id=eid, occurred_at=datetime.now(tz=timezone.utc))
        assert event.evaluation_id == eid
        assert event.policy_id == pid


class TestPolicyEvaluationCompleted:
    def test_creation(self) -> None:
        event = PolicyEvaluationCompleted(
            policy_id=PolicyId(),
            evaluation_id=EvaluationId(),
            decision="allow",
            result="success",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        assert event.decision == "allow"
        assert event.result == "success"


class TestPolicyEvaluationFailed:
    def test_creation(self) -> None:
        event = PolicyEvaluationFailed(
            policy_id=PolicyId(),
            evaluation_id=EvaluationId(),
            failure_reason="timeout",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        assert event.failure_reason == "timeout"


class TestEventCount:
    def test_all_events_exist(self) -> None:
        events = {
            PolicyCreated,
            PolicyActivated,
            PolicyDisabled,
            PolicyArchived,
            PolicyRuleAdded,
            PolicyRuleRemoved,
            PolicyRuleEnabled,
            PolicyRuleDisabled,
            PolicyEvaluationStarted,
            PolicyEvaluationCompleted,
            PolicyEvaluationFailed,
        }
        assert len(events) == 11

    def test_events_are_disjoint(self) -> None:
        types = [
            PolicyCreated,
            PolicyActivated,
            PolicyDisabled,
            PolicyArchived,
            PolicyRuleAdded,
            PolicyRuleRemoved,
            PolicyRuleEnabled,
            PolicyRuleDisabled,
            PolicyEvaluationStarted,
            PolicyEvaluationCompleted,
            PolicyEvaluationFailed,
        ]
        for i in range(len(types)):
            for j in range(i + 1, len(types)):
                assert types[i] is not types[j]


# =============================================================================
# 4. PolicyRule Tests
# =============================================================================


class TestPolicyRule:
    def test_creation(self) -> None:
        rule = PolicyRule(
            condition=PolicyCondition(value="user.role == admin"),
            action=PolicyAction(value="allow"),
        )
        assert isinstance(rule.rule_id, PolicyRuleId)
        assert rule.condition is not None
        assert rule.condition.value == "user.role == admin"
        assert rule.action is not None
        assert rule.action.value == "allow"
        assert rule.enabled is True
        assert rule.priority == 0

    def test_default_id_generated(self) -> None:
        rule = PolicyRule()
        assert isinstance(rule.rule_id, PolicyRuleId)

    def test_enable(self) -> None:
        rule = PolicyRule()
        rule.disable()
        assert rule.enabled is False
        rule.enable()
        assert rule.enabled is True

    def test_enable_twice_raises(self) -> None:
        rule = PolicyRule()
        with pytest.raises(RuleAlreadyEnabledError):
            rule.enable()

    def test_disable(self) -> None:
        rule = PolicyRule()
        rule.disable()
        assert rule.enabled is False

    def test_disable_twice_raises(self) -> None:
        rule = PolicyRule()
        rule.disable()
        with pytest.raises(RuleAlreadyDisabledError):
            rule.disable()

    def test_repr(self) -> None:
        rule = PolicyRule()
        r = repr(rule)
        assert "PolicyRule" in r

    def test_custom_priority(self) -> None:
        rule = PolicyRule(priority=5)
        assert rule.priority == 5

    def test_condition_none(self) -> None:
        rule = PolicyRule()
        assert rule.condition is None

    def test_action_none(self) -> None:
        rule = PolicyRule()
        assert rule.action is None

    def test_property_immutability(self) -> None:
        rule = PolicyRule()
        with pytest.raises(AttributeError):
            rule.enabled = False


# =============================================================================
# 5. PolicyEvaluation Tests
# =============================================================================


class TestPolicyEvaluation:
    def test_creation(self) -> None:
        e = PolicyEvaluation()
        assert isinstance(e.evaluation_id, EvaluationId)
        assert e.status == PolicyEvaluationStatus.PENDING
        assert e.decision is None
        assert e.result is None
        assert e.failure_reason is None
        assert e.started_at is None
        assert e.completed_at is None

    def test_start(self) -> None:
        e = PolicyEvaluation()
        e.start()
        assert e.status == PolicyEvaluationStatus.EVALUATING
        assert e.started_at is not None

    def test_start_twice_raises(self) -> None:
        e = PolicyEvaluation()
        e.start()
        with pytest.raises(InvalidTransitionError):
            e.start()

    def test_complete(self) -> None:
        e = PolicyEvaluation()
        e.start()
        e.complete(decision=PolicyDecision.ALLOW, result=EvaluationResult(value="approved"))
        assert e.status == PolicyEvaluationStatus.COMPLETED
        assert e.decision == PolicyDecision.ALLOW
        assert e.result is not None
        assert e.result.value == "approved"
        assert e.completed_at is not None

    def test_complete_without_start_raises(self) -> None:
        e = PolicyEvaluation()
        with pytest.raises(EvaluationNotStartedError):
            e.complete(decision=PolicyDecision.DENY, result=EvaluationResult(value="denied"))

    def test_complete_without_decision_raises(self) -> None:
        e = PolicyEvaluation()
        e.start()
        with pytest.raises(DecisionRequiredError):
            e.complete(decision=None, result=EvaluationResult(value="result"))

    def test_complete_without_result_raises(self) -> None:
        e = PolicyEvaluation()
        e.start()
        with pytest.raises(InvalidEvaluationResultError):
            e.complete(decision=PolicyDecision.ALLOW, result=None)

    def test_complete_twice_raises(self) -> None:
        e = PolicyEvaluation()
        e.start()
        e.complete(decision=PolicyDecision.ALLOW, result=EvaluationResult(value="ok"))
        with pytest.raises(EvaluationNotStartedError):
            e.complete(decision=PolicyDecision.DENY, result=EvaluationResult(value="no"))

    def test_fail(self) -> None:
        e = PolicyEvaluation()
        e.start()
        e.fail(reason=FailureReason(value="timeout"))
        assert e.status == PolicyEvaluationStatus.FAILED
        assert e.failure_reason is not None
        assert e.failure_reason.value == "timeout"
        assert e.completed_at is not None

    def test_fail_without_start_raises(self) -> None:
        e = PolicyEvaluation()
        with pytest.raises(EvaluationNotStartedError):
            e.fail(reason=FailureReason(value="error"))

    def test_fail_without_reason_raises(self) -> None:
        e = PolicyEvaluation()
        e.start()
        with pytest.raises(InvalidFailureReasonError):
            e.fail(reason=None)

    def test_fail_twice_raises(self) -> None:
        e = PolicyEvaluation()
        e.start()
        e.fail(reason=FailureReason(value="err"))
        with pytest.raises(EvaluationNotStartedError):
            e.fail(reason=FailureReason(value="again"))

    def test_complete_after_fail_raises(self) -> None:
        e = PolicyEvaluation()
        e.start()
        e.fail(reason=FailureReason(value="err"))
        with pytest.raises(EvaluationNotStartedError):
            e.complete(decision=PolicyDecision.ALLOW, result=EvaluationResult(value="ok"))

    def test_is_terminal_completed(self) -> None:
        e = PolicyEvaluation()
        e.start()
        e.complete(decision=PolicyDecision.ALLOW, result=EvaluationResult(value="ok"))
        assert e.is_terminal is True

    def test_is_terminal_failed(self) -> None:
        e = PolicyEvaluation()
        e.start()
        e.fail(reason=FailureReason(value="err"))
        assert e.is_terminal is True

    def test_is_not_terminal_pending(self) -> None:
        e = PolicyEvaluation()
        assert e.is_terminal is False

    def test_is_not_terminal_evaluating(self) -> None:
        e = PolicyEvaluation()
        e.start()
        assert e.is_terminal is False

    def test_repr(self) -> None:
        e = PolicyEvaluation()
        r = repr(e)
        assert "PolicyEvaluation" in r
        assert "pending" in r

    def test_policy_id_assigned(self) -> None:
        pid = PolicyId()
        e = PolicyEvaluation(policy_id=pid)
        assert e.policy_id == pid


# =============================================================================
# 6. Policy Aggregate Tests
# =============================================================================


class TestPolicyCreation:
    def test_create_via_init(self) -> None:
        pid = PolicyId()
        now = datetime.now(tz=timezone.utc)
        p = Policy(
            policy_id=pid,
            name=PolicyName(value="Test"),
            description=PolicyDescription(value="Desc"),
            status=PolicyStatus.DRAFT,
            priority=PolicyPriority.HIGH,
            scope=PolicyScope.USER,
            version=PolicyVersion(value="1.0.0"),
            created_at=now,
        )
        assert p.policy_id == pid
        assert str(p.name) == "Test"
        assert str(p.description) == "Desc"
        assert p.status == PolicyStatus.DRAFT
        assert p.priority == PolicyPriority.HIGH
        assert p.scope == PolicyScope.USER
        assert str(p.version) == "1.0.0"
        assert p.created_at == now
        assert p.updated_at is None
        assert len(p.rules) == 0
        assert len(p.evaluations) == 0
        assert len(p.events) == 0

    def test_defaults(self) -> None:
        p = Policy()
        assert isinstance(p.policy_id, PolicyId)
        assert p.name is None
        assert p.description is None
        assert p.status == PolicyStatus.DRAFT
        assert p.priority == PolicyPriority.MEDIUM
        assert p.scope == PolicyScope.GLOBAL
        assert p.version is None
        assert p.created_at is not None
        assert p.updated_at is None
        assert len(p.rules) == 0
        assert len(p.events) == 0

    def test_is_terminal_archived(self) -> None:
        p = Policy()
        assert p.is_terminal is False
        p.archive()
        assert p.is_terminal is True

    def test_is_terminal_draft(self) -> None:
        p = Policy()
        assert p.is_terminal is False

    def test_is_modifiable_draft(self) -> None:
        p = Policy()
        assert p.is_modifiable is True

    def test_is_modifiable_disabled(self) -> None:
        p = make_ready_policy()
        p.activate()
        p.disable()
        assert p.is_modifiable is True

    def test_is_not_modifiable_active(self) -> None:
        p = make_ready_policy()
        p.activate()
        assert p.is_modifiable is False

    def test_is_not_modifiable_archived(self) -> None:
        p = Policy()
        p.archive()
        assert p.is_modifiable is False

    def test_repr(self) -> None:
        p = Policy()
        r = repr(p)
        assert "Policy" in r
        assert "draft" in r


class TestPolicyActivate:
    def test_activate(self) -> None:
        p = make_ready_policy()
        p.activate()
        assert p.status == PolicyStatus.ACTIVE
        assert p.updated_at is not None

    def test_activate_emits_event(self) -> None:
        p = make_ready_policy()
        p.activate()
        assert any(isinstance(e, PolicyActivated) for e in p.events)

    def test_activate_without_rules_raises(self) -> None:
        p = make_valid_policy()
        with pytest.raises(PolicyHasNoRulesError):
            p.activate()

    def test_activate_twice_raises(self) -> None:
        p = make_ready_policy()
        p.activate()
        with pytest.raises(InvalidTransitionError):
            p.activate()

    def test_activate_from_archived_raises(self) -> None:
        p = make_ready_policy()
        p.archive()
        with pytest.raises(InvalidTransitionError):
            p.activate()

    def test_activate_from_disabled(self) -> None:
        p = make_ready_policy()
        p.activate()
        p.disable()
        p.activate()
        assert p.status == PolicyStatus.ACTIVE


class TestPolicyDisable:
    def test_disable(self) -> None:
        p = make_ready_policy()
        p.activate()
        p.disable()
        assert p.status == PolicyStatus.DISABLED

    def test_disable_emits_event(self) -> None:
        p = make_ready_policy()
        p.activate()
        p.disable()
        assert any(isinstance(e, PolicyDisabled) for e in p.events)

    def test_disable_from_active(self) -> None:
        p = make_ready_policy()
        p.activate()
        p.disable()
        assert p.status == PolicyStatus.DISABLED

    def test_disable_twice_raises(self) -> None:
        p = make_ready_policy()
        p.activate()
        p.disable()
        with pytest.raises(InvalidTransitionError):
            p.disable()

    def test_disable_from_archived_raises(self) -> None:
        p = Policy()
        p.archive()
        with pytest.raises(InvalidTransitionError):
            p.disable()


class TestPolicyArchive:
    def test_archive_from_draft(self) -> None:
        p = Policy()
        p.archive()
        assert p.status == PolicyStatus.ARCHIVED

    def test_archive_from_active(self) -> None:
        p = make_ready_policy()
        p.activate()
        p.archive()
        assert p.status == PolicyStatus.ARCHIVED

    def test_archive_from_disabled(self) -> None:
        p = make_ready_policy()
        p.activate()
        p.disable()
        p.archive()
        assert p.status == PolicyStatus.ARCHIVED

    def test_archive_emits_event(self) -> None:
        p = Policy()
        p.archive()
        assert any(isinstance(e, PolicyArchived) for e in p.events)

    def test_archive_twice_raises(self) -> None:
        p = Policy()
        p.archive()
        with pytest.raises(InvalidTransitionError):
            p.archive()

    def test_archived_immutable_no_add_rule(self) -> None:
        p = Policy()
        p.archive()
        rule = PolicyRule(
            condition=PolicyCondition(value="test"),
            action=PolicyAction(value="allow"),
        )
        with pytest.raises(PolicyNotModifiableError):
            p.add_rule(rule)

    def test_archived_immutable_no_remove_rule(self) -> None:
        p = Policy()
        p.archive()
        with pytest.raises(PolicyNotModifiableError):
            p.remove_rule(PolicyRuleId())


class TestPolicyAddRule:
    def test_add_rule(self) -> None:
        p = make_valid_policy()
        rule = PolicyRule(
            condition=PolicyCondition(value="user.role == admin"),
            action=PolicyAction(value="allow"),
        )
        p.add_rule(rule)
        assert len(p.rules) == 1
        assert p.rules[0] == rule

    def test_add_rule_emits_event(self) -> None:
        p = make_valid_policy()
        rule = PolicyRule(
            condition=PolicyCondition(value="c"),
            action=PolicyAction(value="a"),
        )
        p.add_rule(rule)
        assert any(isinstance(e, PolicyRuleAdded) for e in p.events)

    def test_add_rule_duplicate_id_raises(self) -> None:
        p = make_valid_policy()
        rule_id = PolicyRuleId()
        rule1 = PolicyRule(
            rule_id=rule_id,
            condition=PolicyCondition(value="c1"),
            action=PolicyAction(value="a1"),
        )
        rule2 = PolicyRule(
            rule_id=rule_id,
            condition=PolicyCondition(value="c2"),
            action=PolicyAction(value="a2"),
        )
        p.add_rule(rule1)
        with pytest.raises(DuplicateRuleIdError):
            p.add_rule(rule2)

    def test_add_rule_duplicate_condition_raises(self) -> None:
        p = make_valid_policy()
        rule1 = PolicyRule(
            condition=PolicyCondition(value="user.role == admin"),
            action=PolicyAction(value="allow"),
        )
        rule2 = PolicyRule(
            condition=PolicyCondition(value="user.role == admin"),
            action=PolicyAction(value="deny"),
        )
        p.add_rule(rule1)
        with pytest.raises(DuplicateRuleConditionError):
            p.add_rule(rule2)

    def test_add_rule_to_active_raises(self) -> None:
        p = make_ready_policy()
        p.activate()
        rule = PolicyRule(
            condition=PolicyCondition(value="c"),
            action=PolicyAction(value="a"),
        )
        with pytest.raises(PolicyNotModifiableError):
            p.add_rule(rule)

    def test_add_rule_sets_updated_at(self) -> None:
        p = make_valid_policy()
        rule = PolicyRule(
            condition=PolicyCondition(value="c"),
            action=PolicyAction(value="a"),
        )
        p.add_rule(rule)
        assert p.updated_at is not None

    def test_add_multiple_rules(self) -> None:
        p = make_valid_policy()
        for i in range(3):
            rule = PolicyRule(
                condition=PolicyCondition(value=f"cond{i}"),
                action=PolicyAction(value=f"act{i}"),
            )
            p.add_rule(rule)
        assert len(p.rules) == 3

    def test_rule_with_matching_condition_after_removal(self) -> None:
        p = make_valid_policy()
        rule1 = PolicyRule(
            condition=PolicyCondition(value="cond1"),
            action=PolicyAction(value="act1"),
        )
        p.add_rule(rule1)
        p.remove_rule(rule1.rule_id)
        rule2 = PolicyRule(
            condition=PolicyCondition(value="cond1"),
            action=PolicyAction(value="act2"),
        )
        p.add_rule(rule2)
        assert len(p.rules) == 1


class TestPolicyRemoveRule:
    def test_remove_rule(self) -> None:
        p = make_valid_policy()
        rule = PolicyRule(
            condition=PolicyCondition(value="c"),
            action=PolicyAction(value="a"),
        )
        p.add_rule(rule)
        p.remove_rule(rule.rule_id)
        assert len(p.rules) == 0

    def test_remove_rule_emits_event(self) -> None:
        p = make_valid_policy()
        rule = PolicyRule(
            condition=PolicyCondition(value="c"),
            action=PolicyAction(value="a"),
        )
        p.add_rule(rule)
        p.remove_rule(rule.rule_id)
        assert any(isinstance(e, PolicyRuleRemoved) for e in p.events)

    def test_remove_nonexistent_rule_raises(self) -> None:
        p = make_valid_policy()
        with pytest.raises(RuleNotFoundError):
            p.remove_rule(PolicyRuleId())

    def test_remove_rule_from_active_raises(self) -> None:
        p = make_ready_policy()
        rule = PolicyRule(
            condition=PolicyCondition(value="c"),
            action=PolicyAction(value="a"),
        )
        p.add_rule(rule)
        p.activate()
        with pytest.raises(PolicyNotModifiableError):
            p.remove_rule(rule.rule_id)

    def test_remove_from_disabled(self) -> None:
        p = make_ready_policy()
        rule = p.rules[0]
        p.activate()
        p.disable()
        p.remove_rule(rule.rule_id)
        assert len(p.rules) == 0


class TestPolicyStartEvaluation:
    def test_start_evaluation(self) -> None:
        p = make_ready_policy()
        e = p.start_evaluation()
        assert isinstance(e.evaluation_id, EvaluationId)
        assert e.status == PolicyEvaluationStatus.EVALUATING
        assert e.started_at is not None

    def test_start_evaluation_emits_event(self) -> None:
        p = make_ready_policy()
        p.start_evaluation()
        assert any(isinstance(e, PolicyEvaluationStarted) for e in p.events)

    def test_start_evaluation_on_disabled_raises(self) -> None:
        p = make_ready_policy()
        p.activate()
        p.disable()
        with pytest.raises(PolicyDisabledError):
            p.start_evaluation()

    def test_start_evaluation_on_archived(self) -> None:
        p = make_ready_policy()
        p.archive()
        e = p.start_evaluation()
        assert e.status == PolicyEvaluationStatus.EVALUATING

    def test_multiple_evaluations(self) -> None:
        p = make_ready_policy()
        p.start_evaluation()
        p.start_evaluation()
        assert len(p.evaluations) == 2

    def test_start_evaluation_on_active_policy(self) -> None:
        p = make_ready_policy()
        p.activate()
        e = p.start_evaluation()
        assert e.status == PolicyEvaluationStatus.EVALUATING


class TestPolicyCompleteEvaluation:
    def test_complete_evaluation(self) -> None:
        p = make_ready_policy()
        e = p.start_evaluation()
        p.complete_evaluation(
            evaluation_id=e.evaluation_id,
            decision=PolicyDecision.ALLOW,
            result=EvaluationResult(value="approved"),
        )
        assert e.status == PolicyEvaluationStatus.COMPLETED

    def test_complete_emits_event(self) -> None:
        p = make_ready_policy()
        e = p.start_evaluation()
        p.complete_evaluation(e.evaluation_id, PolicyDecision.ALLOW, EvaluationResult(value="ok"))
        assert any(isinstance(ev, PolicyEvaluationCompleted) for ev in p.events)

    def test_complete_nonexistent_raises(self) -> None:
        p = make_ready_policy()
        with pytest.raises(EvaluationNotFoundError):
            p.complete_evaluation(EvaluationId(), PolicyDecision.ALLOW, EvaluationResult(value="ok"))


class TestPolicyFailEvaluation:
    def test_fail_evaluation(self) -> None:
        p = make_ready_policy()
        e = p.start_evaluation()
        p.fail_evaluation(
            evaluation_id=e.evaluation_id,
            reason=FailureReason(value="timeout"),
        )
        assert e.status == PolicyEvaluationStatus.FAILED

    def test_fail_emits_event(self) -> None:
        p = make_ready_policy()
        e = p.start_evaluation()
        p.fail_evaluation(e.evaluation_id, FailureReason(value="error"))
        assert any(isinstance(ev, PolicyEvaluationFailed) for ev in p.events)

    def test_fail_nonexistent_raises(self) -> None:
        p = make_ready_policy()
        with pytest.raises(EvaluationNotFoundError):
            p.fail_evaluation(EvaluationId(), FailureReason(value="err"))


# =============================================================================
# 7. Rules Tests
# =============================================================================


class TestRules:
    def test_name_required_empty(self) -> None:
        with pytest.raises(InvalidPolicyNameError):
            assert_policy_name_required("")

    def test_name_required_none(self) -> None:
        with pytest.raises(InvalidPolicyNameError):
            assert_policy_name_required(None)

    def test_name_required_valid(self) -> None:
        assert assert_policy_name_required("Valid") is None

    def test_description_required_empty(self) -> None:
        with pytest.raises(InvalidPolicyDescriptionError):
            assert_policy_description_required("")

    def test_description_required_none(self) -> None:
        with pytest.raises(InvalidPolicyDescriptionError):
            assert_policy_description_required(None)

    def test_description_required_valid(self) -> None:
        assert assert_policy_description_required("Desc") is None

    def test_version_required_empty(self) -> None:
        with pytest.raises(InvalidPolicyVersionError):
            assert_policy_version_required("")

    def test_version_required_none(self) -> None:
        with pytest.raises(InvalidPolicyVersionError):
            assert_policy_version_required(None)

    def test_version_required_valid(self) -> None:
        assert assert_policy_version_required("1.0.0") is None

    def test_rule_condition_required_empty(self) -> None:
        with pytest.raises(InvalidPolicyConditionError):
            assert_rule_condition_required("")

    def test_rule_condition_required_none(self) -> None:
        with pytest.raises(InvalidPolicyConditionError):
            assert_rule_condition_required(None)

    def test_rule_condition_required_valid(self) -> None:
        assert assert_rule_condition_required("cond") is None

    def test_rule_action_required_empty(self) -> None:
        with pytest.raises(InvalidPolicyActionError):
            assert_rule_action_required("")

    def test_rule_action_required_none(self) -> None:
        with pytest.raises(InvalidPolicyActionError):
            assert_rule_action_required(None)

    def test_rule_action_required_valid(self) -> None:
        assert assert_rule_action_required("allow") is None

    def test_policy_has_no_rules(self) -> None:
        p = make_valid_policy()
        with pytest.raises(PolicyHasNoRulesError):
            assert_policy_has_rules(p)

    def test_policy_has_rules(self) -> None:
        p = make_ready_policy()
        assert assert_policy_has_rules(p) is None

    def test_policy_not_disabled_valid(self) -> None:
        p = make_valid_policy()
        assert assert_policy_not_disabled(p) is None

    def test_policy_not_disabled_raises(self) -> None:
        p = make_ready_policy()
        p.activate()
        p.disable()
        with pytest.raises(PolicyDisabledError):
            assert_policy_not_disabled(p)

    def test_policy_modifiable(self) -> None:
        p = make_valid_policy()
        assert assert_policy_modifiable(p) is None

    def test_policy_modifiable_active_raises(self) -> None:
        p = make_ready_policy()
        p.activate()
        with pytest.raises(PolicyNotModifiableError):
            assert_policy_modifiable(p)

    def test_policy_modifiable_archived_raises(self) -> None:
        p = Policy()
        p.archive()
        with pytest.raises(PolicyNotModifiableError):
            assert_policy_modifiable(p)

    def test_policy_not_terminal_valid(self) -> None:
        p = make_valid_policy()
        assert assert_policy_not_terminal(p) is None

    def test_policy_not_terminal_archived_raises(self) -> None:
        p = Policy()
        p.archive()
        with pytest.raises(PolicyTerminalError):
            assert_policy_not_terminal(p)

    def test_can_transition_valid(self) -> None:
        assert assert_policy_can_transition(PolicyStatus.DRAFT, PolicyStatus.ACTIVE) is None

    def test_can_transition_invalid(self) -> None:
        with pytest.raises(InvalidTransitionError):
            assert_policy_can_transition(PolicyStatus.DRAFT, PolicyStatus.DISABLED)

    def test_evaluation_can_transition_valid(self) -> None:
        assert assert_evaluation_can_transition(PolicyEvaluationStatus.PENDING, PolicyEvaluationStatus.EVALUATING) is None

    def test_evaluation_can_transition_invalid(self) -> None:
        with pytest.raises(InvalidTransitionError):
            assert_evaluation_can_transition(PolicyEvaluationStatus.PENDING, PolicyEvaluationStatus.COMPLETED)

    def test_evaluation_started_before_valid(self) -> None:
        e = PolicyEvaluation()
        e.start()
        assert assert_evaluation_started_before(e, "complete") is None

    def test_evaluation_started_before_not_started(self) -> None:
        e = PolicyEvaluation()
        with pytest.raises(EvaluationNotStartedError):
            assert_evaluation_started_before(e, "complete")

    def test_decision_required_none(self) -> None:
        with pytest.raises(DecisionRequiredError):
            assert_decision_required(None)

    def test_decision_required_valid(self) -> None:
        assert assert_decision_required(PolicyDecision.ALLOW) is None

    def test_evaluation_result_required_none(self) -> None:
        with pytest.raises(InvalidEvaluationResultError):
            assert_evaluation_result_required(None)

    def test_evaluation_result_required_valid(self) -> None:
        assert assert_evaluation_result_required(EvaluationResult(value="ok")) is None

    def test_failure_reason_required_none(self) -> None:
        with pytest.raises(InvalidFailureReasonError):
            assert_failure_reason_required(None)

    def test_failure_reason_required_valid(self) -> None:
        assert assert_failure_reason_required(FailureReason(value="err")) is None

    def test_rule_not_enabled_twice_valid(self) -> None:
        rule = PolicyRule()
        rule.disable()
        assert assert_rule_not_enabled_twice(rule) is None

    def test_rule_not_enabled_twice_raises(self) -> None:
        rule = PolicyRule()
        with pytest.raises(RuleAlreadyEnabledError):
            assert_rule_not_enabled_twice(rule)

    def test_rule_not_disabled_twice_valid(self) -> None:
        rule = PolicyRule()
        assert assert_rule_not_disabled_twice(rule) is None

    def test_rule_not_disabled_twice_raises(self) -> None:
        rule = PolicyRule()
        rule.disable()
        with pytest.raises(RuleAlreadyDisabledError):
            assert_rule_not_disabled_twice(rule)

    def test_rule_id_unique_valid(self) -> None:
        rule = PolicyRule()
        assert assert_rule_id_unique(rule.rule_id, []) is None

    def test_rule_id_unique_duplicate(self) -> None:
        rule = PolicyRule()
        with pytest.raises(DuplicateRuleIdError):
            assert_rule_id_unique(rule.rule_id, [rule])

    def test_rule_condition_unique_valid(self) -> None:
        cond = PolicyCondition(value="unique")
        assert assert_rule_condition_unique(cond, []) is None

    def test_rule_condition_unique_duplicate(self) -> None:
        cond = PolicyCondition(value="dup")
        rule = PolicyRule(condition=cond, action=PolicyAction(value="a"))
        with pytest.raises(DuplicateRuleConditionError):
            assert_rule_condition_unique(cond, [rule])

    def test_priority_valid(self) -> None:
        assert assert_priority_valid(0) is None
        assert assert_priority_valid(50) is None
        assert assert_priority_valid(100) is None

    def test_priority_invalid_negative(self) -> None:
        with pytest.raises(InvalidPriorityError):
            assert_priority_valid(-1)

    def test_priority_invalid_too_high(self) -> None:
        with pytest.raises(InvalidPriorityError):
            assert_priority_valid(101)

    def test_priority_invalid_type(self) -> None:
        with pytest.raises(InvalidPriorityError):
            assert_priority_valid("high")


# =============================================================================
# 8. Factory Tests
# =============================================================================


class TestFactoryCreatePolicy:
    def test_create_policy(self) -> None:
        policy, event = PolicyFactory.create_policy(name="Test", description="Desc")
        assert isinstance(policy, Policy)
        assert isinstance(event, PolicyCreated)
        assert event.name == "Test"
        assert event.description == "Desc"
        assert event.priority == "medium"
        assert event.scope == "global"
        assert event.version == "1.0.0"

    def test_create_policy_default_priority(self) -> None:
        policy, _ = PolicyFactory.create_policy(name="T", description="D")
        assert policy.priority == PolicyPriority.MEDIUM

    def test_create_policy_default_scope(self) -> None:
        policy, _ = PolicyFactory.create_policy(name="T", description="D")
        assert policy.scope == PolicyScope.GLOBAL

    def test_create_policy_custom_priority(self) -> None:
        policy, _ = PolicyFactory.create_policy(name="T", description="D", priority="high")
        assert policy.priority == PolicyPriority.HIGH

    def test_create_policy_custom_scope(self) -> None:
        policy, _ = PolicyFactory.create_policy(name="T", description="D", scope="user")
        assert policy.scope == PolicyScope.USER

    def test_create_policy_custom_version(self) -> None:
        policy, event = PolicyFactory.create_policy(name="T", description="D", version="2.1.0")
        assert str(policy.version) == "2.1.0"
        assert event.version == "2.1.0"

    def test_create_policy_empty_name_raises(self) -> None:
        with pytest.raises(InvalidPolicyNameError):
            PolicyFactory.create_policy(name="", description="D")

    def test_create_policy_empty_description_raises(self) -> None:
        with pytest.raises(InvalidPolicyDescriptionError):
            PolicyFactory.create_policy(name="T", description="")

    def test_create_policy_empty_version_raises(self) -> None:
        with pytest.raises(InvalidPolicyVersionError):
            PolicyFactory.create_policy(name="T", description="D", version="")

    def test_create_policy_invalid_version_raises(self) -> None:
        with pytest.raises(InvalidPolicyVersionError):
            PolicyFactory.create_policy(name="T", description="D", version="abc")

    def test_create_policy_event_occurred_at(self) -> None:
        _, event = PolicyFactory.create_policy(name="T", description="D")
        assert event.occurred_at is not None

    def test_create_policy_event_event_id(self) -> None:
        _, event = PolicyFactory.create_policy(name="T", description="D")
        assert isinstance(event.event_id, UUID)

    def test_create_policy_priority_enum(self) -> None:
        policy, _ = PolicyFactory.create_policy(name="T", description="D", priority=PolicyPriority.HIGH)
        assert policy.priority == PolicyPriority.HIGH

    def test_create_policy_scope_enum(self) -> None:
        policy, _ = PolicyFactory.create_policy(name="T", description="D", scope=PolicyScope.AGENT)
        assert policy.scope == PolicyScope.AGENT


class TestFactoryAddRule:
    def test_add_rule(self) -> None:
        p = make_valid_policy()
        rule, event = PolicyFactory.add_rule(policy=p, condition="c", action="a")
        assert isinstance(rule, PolicyRule)
        assert isinstance(event, PolicyRuleAdded)
        assert event.condition == "c"
        assert event.action == "a"

    def test_add_rule_empty_condition_raises(self) -> None:
        p = make_valid_policy()
        with pytest.raises(InvalidPolicyConditionError):
            PolicyFactory.add_rule(policy=p, condition="", action="a")

    def test_add_rule_empty_action_raises(self) -> None:
        p = make_valid_policy()
        with pytest.raises(InvalidPolicyActionError):
            PolicyFactory.add_rule(policy=p, condition="c", action="")

    def test_add_rule_with_priority(self) -> None:
        p = make_valid_policy()
        rule, _ = PolicyFactory.add_rule(policy=p, condition="c", action="a", priority=5)
        assert rule.priority == 5

    def test_add_rule_invalid_priority_raises(self) -> None:
        p = make_valid_policy()
        with pytest.raises(InvalidPriorityError):
            PolicyFactory.add_rule(policy=p, condition="c", action="a", priority=-1)


class TestFactoryRemoveRule:
    def test_remove_rule(self) -> None:
        p = make_valid_policy()
        rule, _ = PolicyFactory.add_rule(policy=p, condition="c", action="a")
        PolicyFactory.remove_rule(policy=p, rule_id=rule.rule_id)
        assert len(p.rules) == 0

    def test_remove_rule_nonexistent_raises(self) -> None:
        p = make_valid_policy()
        with pytest.raises(RuleNotFoundError):
            PolicyFactory.remove_rule(policy=p, rule_id=PolicyRuleId())


class TestFactoryEnableDisableRule:
    def test_enable_rule(self) -> None:
        p = make_valid_policy()
        rule = PolicyRule(condition=PolicyCondition(value="c"), action=PolicyAction(value="a"))
        rule.disable()
        p.add_rule(rule)
        PolicyFactory.enable_rule(policy=p, rule_id=rule.rule_id)
        assert rule.enabled is True

    def test_enable_twice_raises(self) -> None:
        p = make_valid_policy()
        rule = PolicyRule(condition=PolicyCondition(value="c"), action=PolicyAction(value="a"))
        p.add_rule(rule)
        with pytest.raises(RuleAlreadyEnabledError):
            PolicyFactory.enable_rule(policy=p, rule_id=rule.rule_id)

    def test_disable_rule(self) -> None:
        p = make_valid_policy()
        rule = PolicyRule(condition=PolicyCondition(value="c"), action=PolicyAction(value="a"))
        p.add_rule(rule)
        PolicyFactory.disable_rule(policy=p, rule_id=rule.rule_id)
        assert rule.enabled is False

    def test_disable_twice_raises(self) -> None:
        p = make_valid_policy()
        rule = PolicyRule(condition=PolicyCondition(value="c"), action=PolicyAction(value="a"))
        p.add_rule(rule)
        PolicyFactory.disable_rule(policy=p, rule_id=rule.rule_id)
        with pytest.raises(RuleAlreadyDisabledError):
            PolicyFactory.disable_rule(policy=p, rule_id=rule.rule_id)


class TestFactoryActivate:
    def test_activate(self) -> None:
        p = make_ready_policy()
        PolicyFactory.activate(p)
        assert p.status == PolicyStatus.ACTIVE

    def test_activate_without_rules_raises(self) -> None:
        p = make_valid_policy()
        with pytest.raises(PolicyHasNoRulesError):
            PolicyFactory.activate(p)


class TestFactoryDisable:
    def test_disable(self) -> None:
        p = make_ready_policy()
        PolicyFactory.activate(p)
        PolicyFactory.disable(p)
        assert p.status == PolicyStatus.DISABLED


class TestFactoryArchive:
    def test_archive(self) -> None:
        p = make_valid_policy()
        PolicyFactory.archive(p)
        assert p.status == PolicyStatus.ARCHIVED


class TestFactoryStartEvaluation:
    def test_start_evaluation(self) -> None:
        p = make_ready_policy()
        evaluation, event = PolicyFactory.start_evaluation(policy=p)
        assert isinstance(evaluation, PolicyEvaluation)
        assert isinstance(event, PolicyEvaluationStarted)
        assert evaluation.status == PolicyEvaluationStatus.EVALUATING

    def test_start_evaluation_on_disabled_raises(self) -> None:
        p = make_ready_policy()
        PolicyFactory.activate(p)
        PolicyFactory.disable(p)
        with pytest.raises(PolicyDisabledError):
            PolicyFactory.start_evaluation(policy=p)


class TestFactoryCompleteEvaluation:
    def test_complete_evaluation(self) -> None:
        p = make_ready_policy()
        e, _ = PolicyFactory.start_evaluation(policy=p)
        event = PolicyFactory.complete_evaluation(
            policy=p,
            evaluation_id=e.evaluation_id,
            decision="allow",
            result="approved",
        )
        assert isinstance(event, PolicyEvaluationCompleted)
        assert event.decision == "allow"
        assert event.result == "approved"

    def test_complete_with_decision_enum(self) -> None:
        p = make_ready_policy()
        e, _ = PolicyFactory.start_evaluation(policy=p)
        event = PolicyFactory.complete_evaluation(
            policy=p,
            evaluation_id=e.evaluation_id,
            decision=PolicyDecision.DENY,
            result="denied",
        )
        assert event.decision == "deny"


class TestFactoryFailEvaluation:
    def test_fail_evaluation(self) -> None:
        p = make_ready_policy()
        e, _ = PolicyFactory.start_evaluation(policy=p)
        event = PolicyFactory.fail_evaluation(
            policy=p,
            evaluation_id=e.evaluation_id,
            reason="timeout",
        )
        assert isinstance(event, PolicyEvaluationFailed)
        assert event.failure_reason == "timeout"

    def test_fail_evaluation_empty_reason_raises(self) -> None:
        p = make_ready_policy()
        e, _ = PolicyFactory.start_evaluation(policy=p)
        with pytest.raises(InvalidFailureReasonError):
            PolicyFactory.fail_evaluation(
                policy=p,
                evaluation_id=e.evaluation_id,
                reason="",
            )


# =============================================================================
# 9. Lifecycle Tests
# =============================================================================


class TestFullLifecycle:
    def test_full_policy_lifecycle(self) -> None:
        p = make_valid_policy()
        PolicyFactory.add_rule(policy=p, condition="user.role == admin", action="allow")
        PolicyFactory.activate(p)
        assert p.status == PolicyStatus.ACTIVE

        PolicyFactory.disable(p)
        assert p.status == PolicyStatus.DISABLED

        PolicyFactory.activate(p)
        assert p.status == PolicyStatus.ACTIVE

        e, _ = PolicyFactory.start_evaluation(policy=p)
        assert e.status == PolicyEvaluationStatus.EVALUATING

        PolicyFactory.complete_evaluation(policy=p, evaluation_id=e.evaluation_id, decision="allow", result="ok")
        assert e.status == PolicyEvaluationStatus.COMPLETED

        PolicyFactory.archive(p)
        assert p.status == PolicyStatus.ARCHIVED

    def test_fail_then_recover(self) -> None:
        p = make_ready_policy()
        PolicyFactory.activate(p)
        e, _ = PolicyFactory.start_evaluation(policy=p)
        PolicyFactory.fail_evaluation(policy=p, evaluation_id=e.evaluation_id, reason="error")
        assert e.status == PolicyEvaluationStatus.FAILED

        e2, _ = PolicyFactory.start_evaluation(policy=p)
        PolicyFactory.complete_evaluation(policy=p, evaluation_id=e2.evaluation_id, decision="allow", result="ok")
        assert e2.status == PolicyEvaluationStatus.COMPLETED

    def test_events_emitted_during_lifecycle(self) -> None:
        p = make_valid_policy()
        PolicyFactory.add_rule(policy=p, condition="c", action="a")
        PolicyFactory.activate(p)
        PolicyFactory.disable(p)
        PolicyFactory.archive(p)

        event_types = {type(e).__name__ for e in p.events}
        assert "PolicyRuleAdded" in event_types
        assert "PolicyActivated" in event_types
        assert "PolicyDisabled" in event_types
        assert "PolicyArchived" in event_types

    def test_evaluation_events_emitted(self) -> None:
        p = make_ready_policy()
        e, _ = PolicyFactory.start_evaluation(policy=p)
        PolicyFactory.complete_evaluation(policy=p, evaluation_id=e.evaluation_id, decision="allow", result="ok")
        event_types = {type(ev).__name__ for ev in p.events}
        assert "PolicyEvaluationStarted" in event_types
        assert "PolicyEvaluationCompleted" in event_types


# =============================================================================
# 10. Edge Case Tests
# =============================================================================


class TestEdgeCases:
    def test_policy_with_multiple_rules_activate(self) -> None:
        p = make_valid_policy()
        for i in range(5):
            PolicyFactory.add_rule(policy=p, condition=f"cond{i}", action=f"act{i}")
        assert len(p.rules) == 5
        PolicyFactory.activate(p)
        assert p.status == PolicyStatus.ACTIVE

    def test_rule_enable_after_disable_then_enable(self) -> None:
        rule = PolicyRule()
        rule.disable()
        rule.enable()
        assert rule.enabled is True
        with pytest.raises(RuleAlreadyEnabledError):
            rule.enable()

    def test_create_evaluation_without_rules_on_draft(self) -> None:
        p = make_valid_policy()
        e = p.start_evaluation()
        assert e.status == PolicyEvaluationStatus.EVALUATING

    def test_archive_disabled_policy(self) -> None:
        p = make_ready_policy()
        PolicyFactory.activate(p)
        PolicyFactory.disable(p)
        PolicyFactory.archive(p)
        assert p.status == PolicyStatus.ARCHIVED

    def test_activate_disabled_policy(self) -> None:
        p = make_ready_policy()
        PolicyFactory.activate(p)
        PolicyFactory.disable(p)
        PolicyFactory.activate(p)
        assert p.status == PolicyStatus.ACTIVE

    def test_events_cleared_properly(self) -> None:
        p = make_valid_policy()
        PolicyFactory.add_rule(policy=p, condition="c", action="a")
        PolicyFactory.activate(p)
        p._clear_events()
        assert len(p.events) == 0

    def test_rule_events_cleared_properly(self) -> None:
        p = make_valid_policy()
        rule = PolicyRule(condition=PolicyCondition(value="c"), action=PolicyAction(value="a"))
        rule.disable()
        p.add_rule(rule)
        p._clear_events()
        assert len(p.events) == 0

    def test_evaluation_repr(self) -> None:
        e = PolicyEvaluation()
        r = repr(e)
        assert "PolicyEvaluation" in r

    def test_policy_with_no_version(self) -> None:
        p = Policy()
        assert p.version is None

    def test_policy_with_version(self) -> None:
        p = Policy(version=PolicyVersion(value="2.0.0"))
        assert str(p.version) == "2.0.0"

    def test_rule_condition_unique_with_none(self) -> None:
        assert assert_rule_condition_unique(None, []) is None

    def test_rule_id_unique_with_empty_list(self) -> None:
        rid = PolicyRuleId()
        assert assert_rule_id_unique(rid, []) is None
