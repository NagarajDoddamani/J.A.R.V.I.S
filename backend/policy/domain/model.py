from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import auto, StrEnum
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================


class PolicyStatus(StrEnum):
    DRAFT = auto()
    ACTIVE = auto()
    DISABLED = auto()
    ARCHIVED = auto()


class PolicyPriority(StrEnum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


class PolicyDecision(StrEnum):
    ALLOW = auto()
    DENY = auto()
    REVIEW = auto()


class PolicyEvaluationStatus(StrEnum):
    PENDING = auto()
    EVALUATING = auto()
    COMPLETED = auto()
    FAILED = auto()


class PolicyScope(StrEnum):
    GLOBAL = auto()
    USER = auto()
    AGENT = auto()
    AUTOMATION = auto()
    WORKFLOW = auto()


# =============================================================================
# Value Objects
# =============================================================================


@dataclass(frozen=True)
class PolicyId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class PolicyRuleId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class EvaluationId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class PolicyName:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"PolicyName value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.policy.domain.exceptions import InvalidPolicyNameError
            raise InvalidPolicyNameError("Policy name must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class PolicyDescription:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"PolicyDescription value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.policy.domain.exceptions import InvalidPolicyDescriptionError
            raise InvalidPolicyDescriptionError("Policy description must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class PolicyCondition:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"PolicyCondition value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.policy.domain.exceptions import InvalidPolicyConditionError
            raise InvalidPolicyConditionError("Policy condition must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class PolicyAction:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"PolicyAction value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.policy.domain.exceptions import InvalidPolicyActionError
            raise InvalidPolicyActionError("Policy action must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class PolicyVersion:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"PolicyVersion value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.policy.domain.exceptions import InvalidPolicyVersionError
            raise InvalidPolicyVersionError("Policy version must not be empty")
        import re
        if not re.match(r"^\d+\.\d+\.\d+$", self.value.strip()):
            from backend.policy.domain.exceptions import InvalidPolicyVersionError
            raise InvalidPolicyVersionError("Policy version must follow semver format (e.g. 1.0.0)")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class FailureReason:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"FailureReason value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.policy.domain.exceptions import InvalidFailureReasonError
            raise InvalidFailureReasonError("Failure reason must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class EvaluationResult:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"EvaluationResult value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.policy.domain.exceptions import InvalidEvaluationResultError
            raise InvalidEvaluationResultError("Evaluation result must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


# =============================================================================
# Domain Events
# =============================================================================


@dataclass(frozen=True)
class PolicyCreated:
    policy_id: PolicyId
    name: str
    description: str
    priority: str
    scope: str
    version: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PolicyActivated:
    policy_id: PolicyId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PolicyDisabled:
    policy_id: PolicyId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PolicyArchived:
    policy_id: PolicyId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PolicyRuleAdded:
    rule_id: PolicyRuleId
    policy_id: PolicyId
    condition: str
    action: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PolicyRuleRemoved:
    rule_id: PolicyRuleId
    policy_id: PolicyId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PolicyRuleEnabled:
    rule_id: PolicyRuleId
    policy_id: PolicyId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PolicyRuleDisabled:
    rule_id: PolicyRuleId
    policy_id: PolicyId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PolicyEvaluationStarted:
    policy_id: PolicyId
    evaluation_id: EvaluationId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PolicyEvaluationCompleted:
    policy_id: PolicyId
    evaluation_id: EvaluationId
    decision: str
    result: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PolicyEvaluationFailed:
    policy_id: PolicyId
    evaluation_id: EvaluationId
    failure_reason: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


# =============================================================================
# Entities
# =============================================================================


class PolicyRule:
    """A rule within a policy that defines a condition-action pair."""

    def __init__(
        self,
        rule_id: PolicyRuleId | None = None,
        condition: PolicyCondition | None = None,
        action: PolicyAction | None = None,
        priority: int = 0,
        enabled: bool = True,
        policy_id: PolicyId | None = None,
    ) -> None:
        self._rule_id = rule_id or PolicyRuleId()
        self._condition = condition
        self._action = action
        self._priority = priority
        self._enabled = enabled
        self._policy_id = policy_id

    @property
    def rule_id(self) -> PolicyRuleId:
        return self._rule_id

    @property
    def condition(self) -> PolicyCondition | None:
        return self._condition

    @property
    def action(self) -> PolicyAction | None:
        return self._action

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def policy_id(self) -> PolicyId | None:
        return self._policy_id

    def enable(self) -> None:
        from backend.policy.domain.rules import assert_rule_not_enabled_twice

        assert_rule_not_enabled_twice(self)
        self._enabled = True

    def disable(self) -> None:
        from backend.policy.domain.rules import assert_rule_not_disabled_twice

        assert_rule_not_disabled_twice(self)
        self._enabled = False

    def __repr__(self) -> str:
        return (
            f"PolicyRule(id={self._rule_id}, "
            f"condition={self._condition}, "
            f"enabled={self._enabled})"
        )


class PolicyEvaluation:
    """A single evaluation of a policy against a request."""

    def __init__(
        self,
        evaluation_id: EvaluationId | None = None,
        policy_id: PolicyId | None = None,
        status: PolicyEvaluationStatus = PolicyEvaluationStatus.PENDING,
        decision: PolicyDecision | None = None,
        result: EvaluationResult | None = None,
        failure_reason: FailureReason | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        self._evaluation_id = evaluation_id or EvaluationId()
        self._policy_id = policy_id or PolicyId()
        self._status = status
        self._decision = decision
        self._result = result
        self._failure_reason = failure_reason
        self._started_at = started_at
        self._completed_at = completed_at

    @property
    def evaluation_id(self) -> EvaluationId:
        return self._evaluation_id

    @property
    def policy_id(self) -> PolicyId:
        return self._policy_id

    @property
    def status(self) -> PolicyEvaluationStatus:
        return self._status

    @property
    def decision(self) -> PolicyDecision | None:
        return self._decision

    @property
    def result(self) -> EvaluationResult | None:
        return self._result

    @property
    def failure_reason(self) -> FailureReason | None:
        return self._failure_reason

    @property
    def started_at(self) -> datetime | None:
        return self._started_at

    @property
    def completed_at(self) -> datetime | None:
        return self._completed_at

    @property
    def is_terminal(self) -> bool:
        return self._status in (
            PolicyEvaluationStatus.COMPLETED,
            PolicyEvaluationStatus.FAILED,
        )

    def start(self) -> None:
        from backend.policy.domain.rules import (
            assert_evaluation_can_transition,
        )

        assert_evaluation_can_transition(self._status, PolicyEvaluationStatus.EVALUATING)
        self._status = PolicyEvaluationStatus.EVALUATING
        self._started_at = datetime.now(tz=timezone.utc)

    def complete(self, decision: PolicyDecision, result: EvaluationResult) -> None:
        from backend.policy.domain.rules import (
            assert_evaluation_can_transition,
            assert_evaluation_started_before,
            assert_decision_required,
            assert_evaluation_result_required,
        )

        assert_evaluation_started_before(self, "complete")
        assert_decision_required(decision)
        assert_evaluation_result_required(result)
        assert_evaluation_can_transition(self._status, PolicyEvaluationStatus.COMPLETED)
        self._decision = decision
        self._result = result
        self._status = PolicyEvaluationStatus.COMPLETED
        self._completed_at = datetime.now(tz=timezone.utc)

    def fail(self, reason: FailureReason) -> None:
        from backend.policy.domain.rules import (
            assert_evaluation_can_transition,
            assert_evaluation_started_before,
            assert_failure_reason_required,
        )

        assert_evaluation_started_before(self, "fail")
        assert_failure_reason_required(reason)
        assert_evaluation_can_transition(self._status, PolicyEvaluationStatus.FAILED)
        self._failure_reason = reason
        self._status = PolicyEvaluationStatus.FAILED
        self._completed_at = datetime.now(tz=timezone.utc)

    def __repr__(self) -> str:
        return (
            f"PolicyEvaluation(id={self._evaluation_id}, "
            f"status={self._status.value})"
        )


# =============================================================================
# Policy Status Transitions
# =============================================================================

VALID_POLICY_TRANSITIONS: dict[PolicyStatus, set[PolicyStatus]] = {
    PolicyStatus.DRAFT: {PolicyStatus.ACTIVE, PolicyStatus.ARCHIVED},
    PolicyStatus.ACTIVE: {PolicyStatus.DISABLED, PolicyStatus.ARCHIVED},
    PolicyStatus.DISABLED: {PolicyStatus.ACTIVE, PolicyStatus.ARCHIVED},
    PolicyStatus.ARCHIVED: set(),
}

VALID_EVALUATION_TRANSITIONS: dict[PolicyEvaluationStatus, set[PolicyEvaluationStatus]] = {
    PolicyEvaluationStatus.PENDING: {PolicyEvaluationStatus.EVALUATING},
    PolicyEvaluationStatus.EVALUATING: {PolicyEvaluationStatus.COMPLETED, PolicyEvaluationStatus.FAILED},
    PolicyEvaluationStatus.COMPLETED: set(),
    PolicyEvaluationStatus.FAILED: set(),
}


class Policy:
    """Aggregate root for the policy domain."""

    def __init__(
        self,
        policy_id: PolicyId | None = None,
        name: PolicyName | None = None,
        description: PolicyDescription | None = None,
        status: PolicyStatus = PolicyStatus.DRAFT,
        priority: PolicyPriority = PolicyPriority.MEDIUM,
        scope: PolicyScope = PolicyScope.GLOBAL,
        version: PolicyVersion | None = None,
        rules: list[PolicyRule] | None = None,
        evaluations: list[PolicyEvaluation] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._policy_id = policy_id or PolicyId()
        self._name = name
        self._description = description
        self._status = status
        self._priority = priority
        self._scope = scope
        self._version = version
        self._rules = rules or []
        self._evaluations = evaluations or []
        self._created_at = created_at or datetime.now(tz=timezone.utc)
        self._updated_at = updated_at
        self._events: list[
            PolicyCreated
            | PolicyActivated
            | PolicyDisabled
            | PolicyArchived
            | PolicyRuleAdded
            | PolicyRuleRemoved
            | PolicyRuleEnabled
            | PolicyRuleDisabled
            | PolicyEvaluationStarted
            | PolicyEvaluationCompleted
            | PolicyEvaluationFailed
        ] = []

    # -- properties ---------------------------------------------------------

    @property
    def policy_id(self) -> PolicyId:
        return self._policy_id

    @property
    def name(self) -> PolicyName | None:
        return self._name

    @property
    def description(self) -> PolicyDescription | None:
        return self._description

    @property
    def status(self) -> PolicyStatus:
        return self._status

    @property
    def priority(self) -> PolicyPriority:
        return self._priority

    @property
    def scope(self) -> PolicyScope:
        return self._scope

    @property
    def version(self) -> PolicyVersion | None:
        return self._version

    @property
    def rules(self) -> list[PolicyRule]:
        return list(self._rules)

    @property
    def evaluations(self) -> list[PolicyEvaluation]:
        return list(self._evaluations)

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @property
    def events(
        self,
    ) -> list[
        PolicyCreated
        | PolicyActivated
        | PolicyDisabled
        | PolicyArchived
        | PolicyRuleAdded
        | PolicyRuleRemoved
        | PolicyRuleEnabled
        | PolicyRuleDisabled
        | PolicyEvaluationStarted
        | PolicyEvaluationCompleted
        | PolicyEvaluationFailed
    ]:
        return list(self._events)

    @property
    def is_terminal(self) -> bool:
        return self._status == PolicyStatus.ARCHIVED

    @property
    def is_modifiable(self) -> bool:
        return self._status not in (PolicyStatus.ACTIVE, PolicyStatus.ARCHIVED)

    # -- commands -----------------------------------------------------------

    def activate(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.policy.domain.rules import (
            assert_policy_can_transition,
            assert_policy_has_rules,
        )

        assert_policy_has_rules(self)
        assert_policy_can_transition(self._status, PolicyStatus.ACTIVE)
        self._status = PolicyStatus.ACTIVE
        self._updated_at = now
        self._events.append(
            PolicyActivated(
                policy_id=self._policy_id, occurred_at=now
            )
        )

    def disable(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.policy.domain.rules import (
            assert_policy_can_transition,
        )

        assert_policy_can_transition(self._status, PolicyStatus.DISABLED)
        self._status = PolicyStatus.DISABLED
        self._updated_at = now
        self._events.append(
            PolicyDisabled(
                policy_id=self._policy_id, occurred_at=now
            )
        )

    def archive(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.policy.domain.rules import (
            assert_policy_can_transition,
        )

        assert_policy_can_transition(self._status, PolicyStatus.ARCHIVED)
        self._status = PolicyStatus.ARCHIVED
        self._updated_at = now
        self._events.append(
            PolicyArchived(
                policy_id=self._policy_id, occurred_at=now
            )
        )

    def add_rule(self, rule: PolicyRule) -> None:
        from backend.policy.domain.rules import (
            assert_policy_modifiable,
            assert_rule_id_unique,
            assert_rule_condition_unique,
        )

        assert_policy_modifiable(self)
        assert_rule_id_unique(rule.rule_id, self._rules)
        assert_rule_condition_unique(rule.condition, self._rules)
        rule._policy_id = self._policy_id
        self._rules.append(rule)
        self._updated_at = datetime.now(tz=timezone.utc)
        self._events.append(
            PolicyRuleAdded(
                rule_id=rule.rule_id,
                policy_id=self._policy_id,
                condition=str(rule.condition) if rule.condition else "",
                action=str(rule.action) if rule.action else "",
                occurred_at=datetime.now(tz=timezone.utc),
            )
        )

    def enable_rule(self, rule_id: PolicyRuleId) -> None:
        rule = self._find_rule(rule_id)
        rule.enable()
        now = datetime.now(tz=timezone.utc)
        self._updated_at = now
        self._events.append(
            PolicyRuleEnabled(
                rule_id=rule_id,
                policy_id=self._policy_id,
                occurred_at=now,
            )
        )

    def disable_rule(self, rule_id: PolicyRuleId) -> None:
        rule = self._find_rule(rule_id)
        rule.disable()
        now = datetime.now(tz=timezone.utc)
        self._updated_at = now
        self._events.append(
            PolicyRuleDisabled(
                rule_id=rule_id,
                policy_id=self._policy_id,
                occurred_at=now,
            )
        )

    def remove_rule(self, rule_id: PolicyRuleId) -> None:
        from backend.policy.domain.rules import (
            assert_policy_modifiable,
        )

        assert_policy_modifiable(self)
        rule = self._find_rule(rule_id)
        self._rules.remove(rule)
        self._updated_at = datetime.now(tz=timezone.utc)
        self._events.append(
            PolicyRuleRemoved(
                rule_id=rule_id,
                policy_id=self._policy_id,
                occurred_at=datetime.now(tz=timezone.utc),
            )
        )

    def start_evaluation(self) -> PolicyEvaluation:
        now = datetime.now(tz=timezone.utc)
        from backend.policy.domain.rules import (
            assert_policy_not_disabled,
        )

        assert_policy_not_disabled(self)
        evaluation = PolicyEvaluation(policy_id=self._policy_id)
        evaluation.start()
        self._evaluations.append(evaluation)
        self._updated_at = now
        self._events.append(
            PolicyEvaluationStarted(
                policy_id=self._policy_id,
                evaluation_id=evaluation.evaluation_id,
                occurred_at=now,
            )
        )
        return evaluation

    def complete_evaluation(self, evaluation_id: EvaluationId, decision: PolicyDecision, result: EvaluationResult) -> None:
        now = datetime.now(tz=timezone.utc)
        evaluation = self._find_evaluation(evaluation_id)
        evaluation.complete(decision, result)
        self._updated_at = now
        self._events.append(
            PolicyEvaluationCompleted(
                policy_id=self._policy_id,
                evaluation_id=evaluation_id,
                decision=decision.value,
                result=result.value,
                occurred_at=now,
            )
        )

    def fail_evaluation(self, evaluation_id: EvaluationId, reason: FailureReason) -> None:
        now = datetime.now(tz=timezone.utc)
        evaluation = self._find_evaluation(evaluation_id)
        evaluation.fail(reason)
        self._updated_at = now
        self._events.append(
            PolicyEvaluationFailed(
                policy_id=self._policy_id,
                evaluation_id=evaluation_id,
                failure_reason=reason.value,
                occurred_at=now,
            )
        )

    # -- internal -----------------------------------------------------------

    def _find_rule(self, rule_id: PolicyRuleId) -> PolicyRule:
        for rule in self._rules:
            if rule.rule_id == rule_id:
                return rule
        from backend.policy.domain.exceptions import RuleNotFoundError
        raise RuleNotFoundError(str(rule_id))

    def _find_evaluation(self, evaluation_id: EvaluationId) -> PolicyEvaluation:
        for evaluation in self._evaluations:
            if evaluation.evaluation_id == evaluation_id:
                return evaluation
        from backend.policy.domain.exceptions import EvaluationNotFoundError
        raise EvaluationNotFoundError(str(evaluation_id))

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"Policy(id={self._policy_id}, "
            f"name={self._name}, "
            f"status={self._status.value})"
        )
