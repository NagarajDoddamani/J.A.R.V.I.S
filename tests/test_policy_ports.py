from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

import pytest

from backend.policy.application.ports.clock import PolicyClockPort
from backend.policy.application.ports.id_generator import (
    PolicyIdGeneratorPort,
)
from backend.policy.application.ports.outbox import (
    PolicyOutboxEvent,
    PolicyOutboxPort,
)
from backend.policy.application.ports.repository import (
    PolicyEvaluationRepositoryPort,
    PolicyRepositoryPort,
    PolicyRuleRepositoryPort,
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

_NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)


# =============================================================================
# Stub helpers
# =============================================================================


def _make_policy(
    policy_id: PolicyId | None = None,
    name: str = "test-policy",
    description: str = "Test policy description",
    status: PolicyStatus = PolicyStatus.DRAFT,
) -> Policy:
    policy = Policy(
        policy_id=policy_id or PolicyId(),
        name=PolicyName(name),
        description=PolicyDescription(description),
        status=status,
        priority=PolicyPriority.MEDIUM,
        scope=PolicyScope.GLOBAL,
        version=PolicyVersion("1.0.0"),
        created_at=_NOW,
    )
    rule = PolicyRule(
        rule_id=PolicyRuleId(),
        condition=PolicyCondition("true"),
        action=PolicyAction("allow"),
    )
    policy._rules.append(rule)
    return policy


def _make_rule(
    rule_id: PolicyRuleId | None = None,
    condition: str = "true",
    action: str = "allow",
    enabled: bool = True,
) -> PolicyRule:
    return PolicyRule(
        rule_id=rule_id or PolicyRuleId(),
        condition=PolicyCondition(condition),
        action=PolicyAction(action),
        enabled=enabled,
    )


def _make_evaluation(
    evaluation_id: EvaluationId | None = None,
    policy_id: PolicyId | None = None,
    status: PolicyEvaluationStatus = PolicyEvaluationStatus.PENDING,
) -> PolicyEvaluation:
    return PolicyEvaluation(
        evaluation_id=evaluation_id or EvaluationId(),
        policy_id=policy_id or PolicyId(),
        status=status,
    )


def _make_event() -> PolicyOutboxEvent:
    return PolicyCreated(
        policy_id=PolicyId(),
        name="test",
        description="desc",
        priority="medium",
        scope="global",
        version="1.0.0",
        occurred_at=_NOW,
    )


# =============================================================================
# Stub implementations
# =============================================================================


class StubPolicyRepository:
    """Minimal stub conforming to PolicyRepositoryPort."""

    def __init__(self) -> None:
        self._policies: dict[str, Policy] = {}

    def save(self, policy: Policy) -> None:
        self._policies[str(policy.policy_id)] = policy

    def find_by_id(self, policy_id: PolicyId) -> Policy | None:
        return self._policies.get(str(policy_id))

    def find_by_status(self, status: PolicyStatus) -> list[Policy]:
        return [p for p in self._policies.values() if p.status == status]

    def find_by_priority(self, priority: PolicyPriority) -> list[Policy]:
        return [p for p in self._policies.values() if p.priority == priority]

    def find_by_scope(self, scope: PolicyScope) -> list[Policy]:
        return [p for p in self._policies.values() if p.scope == scope]

    def find_all(self) -> list[Policy]:
        return list(self._policies.values())

    def count(self) -> int:
        return len(self._policies)


class StubRuleRepository:
    """Minimal stub conforming to PolicyRuleRepositoryPort."""

    def __init__(self) -> None:
        self._rules: dict[str, PolicyRule] = {}

    def save(self, rule: PolicyRule) -> None:
        self._rules[str(rule.rule_id)] = rule

    def find_by_id(self, rule_id: PolicyRuleId) -> PolicyRule | None:
        return self._rules.get(str(rule_id))

    def find_by_policy_id(self, policy_id: PolicyId) -> list[PolicyRule]:
        return [r for r in self._rules.values()]

    def find_enabled(self) -> list[PolicyRule]:
        return [r for r in self._rules.values() if r.enabled]

    def find_all(self) -> list[PolicyRule]:
        return list(self._rules.values())

    def count(self) -> int:
        return len(self._rules)


class StubEvaluationRepository:
    """Minimal stub conforming to PolicyEvaluationRepositoryPort."""

    def __init__(self) -> None:
        self._evaluations: dict[str, PolicyEvaluation] = {}

    def save(self, evaluation: PolicyEvaluation) -> None:
        self._evaluations[str(evaluation.evaluation_id)] = evaluation

    def find_by_id(self, evaluation_id: EvaluationId) -> PolicyEvaluation | None:
        return self._evaluations.get(str(evaluation_id))

    def find_by_status(
        self, status: PolicyEvaluationStatus
    ) -> list[PolicyEvaluation]:
        return [e for e in self._evaluations.values() if e.status == status]

    def find_by_policy_id(self, policy_id: PolicyId) -> list[PolicyEvaluation]:
        return [e for e in self._evaluations.values()]

    def find_all(self) -> list[PolicyEvaluation]:
        return list(self._evaluations.values())

    def count(self) -> int:
        return len(self._evaluations)


class StubOutbox:
    """Minimal stub conforming to PolicyOutboxPort."""

    def __init__(self) -> None:
        self._events: list[PolicyOutboxEvent] = []

    def append(self, event: PolicyOutboxEvent) -> None:
        self._events.append(event)

    def fetch_unpublished(self, limit: int = 100) -> list[PolicyOutboxEvent]:
        return self._events[:limit]

    def mark_published(self, aggregate_id: str) -> None:
        self._events = [
            e for e in self._events if str(e.event_id) != aggregate_id
        ]


class StubClock:
    """Minimal stub conforming to PolicyClockPort."""

    def __init__(self, now: datetime = _NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class StubIdGenerator:
    """Minimal stub conforming to PolicyIdGeneratorPort."""

    def __init__(self) -> None:
        self._counter = 0

    def generate_policy_id(self) -> str:
        self._counter += 1
        return f"policy-{self._counter}"

    def generate_rule_id(self) -> str:
        self._counter += 1
        return f"rule-{self._counter}"

    def generate_evaluation_id(self) -> str:
        self._counter += 1
        return f"eval-{self._counter}"


# =============================================================================
# PolicyRepositoryPort contract tests
# =============================================================================


class TestPolicyRepositoryPort:
    """Contract tests for PolicyRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubPolicyRepository:
        return StubPolicyRepository()

    def test_save_and_find_by_id(self, repo: StubPolicyRepository) -> None:
        policy = _make_policy()
        repo.save(policy)
        found = repo.find_by_id(policy.policy_id)
        assert found is not None
        assert found.policy_id == policy.policy_id

    def test_find_by_id_returns_none(self, repo: StubPolicyRepository) -> None:
        assert repo.find_by_id(PolicyId()) is None

    def test_find_by_status(self, repo: StubPolicyRepository) -> None:
        policy = _make_policy(status=PolicyStatus.DRAFT)
        repo.save(policy)
        results = repo.find_by_status(PolicyStatus.DRAFT)
        assert len(results) == 1
        assert results[0].policy_id == policy.policy_id

    def test_find_by_status_multiple(self, repo: StubPolicyRepository) -> None:
        p1 = _make_policy(status=PolicyStatus.DRAFT)
        p2 = _make_policy(status=PolicyStatus.DRAFT)
        p3 = _make_policy(status=PolicyStatus.ACTIVE)
        repo.save(p1)
        repo.save(p2)
        repo.save(p3)
        results = repo.find_by_status(PolicyStatus.DRAFT)
        assert len(results) == 2

    def test_find_by_status_empty(self, repo: StubPolicyRepository) -> None:
        assert repo.find_by_status(PolicyStatus.ACTIVE) == []

    def test_find_by_status_all(self, repo: StubPolicyRepository) -> None:
        p1 = _make_policy(status=PolicyStatus.DRAFT)
        p2 = _make_policy(status=PolicyStatus.ACTIVE)
        repo.save(p1)
        repo.save(p2)
        assert len(repo.find_by_status(PolicyStatus.DRAFT)) == 1
        assert len(repo.find_by_status(PolicyStatus.ACTIVE)) == 1

    def test_find_by_priority(self, repo: StubPolicyRepository) -> None:
        policy = _make_policy()
        repo.save(policy)
        results = repo.find_by_priority(PolicyPriority.MEDIUM)
        assert len(results) == 1
        assert results[0].policy_id == policy.policy_id

    def test_find_by_priority_multiple(self, repo: StubPolicyRepository) -> None:
        p1 = _make_policy()
        p2 = _make_policy()
        p3 = _make_policy()
        repo.save(p1)
        repo.save(p2)
        repo.save(p3)
        results = repo.find_by_priority(PolicyPriority.MEDIUM)
        assert len(results) == 3

    def test_find_by_priority_empty(self, repo: StubPolicyRepository) -> None:
        assert repo.find_by_priority(PolicyPriority.HIGH) == []

    def test_find_by_scope(self, repo: StubPolicyRepository) -> None:
        policy = _make_policy()
        repo.save(policy)
        results = repo.find_by_scope(PolicyScope.GLOBAL)
        assert len(results) == 1

    def test_find_by_scope_multiple(self, repo: StubPolicyRepository) -> None:
        p1 = _make_policy()
        p2 = _make_policy()
        repo.save(p1)
        repo.save(p2)
        results = repo.find_by_scope(PolicyScope.GLOBAL)
        assert len(results) == 2

    def test_find_by_scope_empty(self, repo: StubPolicyRepository) -> None:
        assert repo.find_by_scope(PolicyScope.AGENT) == []

    def test_find_all(self, repo: StubPolicyRepository) -> None:
        p1 = _make_policy()
        p2 = _make_policy()
        repo.save(p1)
        repo.save(p2)
        assert len(repo.find_all()) == 2

    def test_find_all_empty(self, repo: StubPolicyRepository) -> None:
        assert repo.find_all() == []

    def test_save_updates_existing(self, repo: StubPolicyRepository) -> None:
        policy = _make_policy(status=PolicyStatus.DRAFT)
        repo.save(policy)
        policy._status = PolicyStatus.ACTIVE
        repo.save(policy)
        found = repo.find_by_id(policy.policy_id)
        assert found is not None
        assert found.status == PolicyStatus.ACTIVE

    def test_count_empty(self, repo: StubPolicyRepository) -> None:
        assert repo.count() == 0

    def test_count_multiple(self, repo: StubPolicyRepository) -> None:
        repo.save(_make_policy())
        repo.save(_make_policy())
        assert repo.count() == 2

    def test_save_duplicate_does_not_increase_count(
        self, repo: StubPolicyRepository
    ) -> None:
        policy = _make_policy()
        repo.save(policy)
        repo.save(policy)
        assert repo.count() == 1


# =============================================================================
# PolicyRuleRepositoryPort contract tests
# =============================================================================


class TestRuleRepositoryPort:
    """Contract tests for PolicyRuleRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubRuleRepository:
        return StubRuleRepository()

    def test_save_and_find_by_id(self, repo: StubRuleRepository) -> None:
        rule = _make_rule()
        repo.save(rule)
        found = repo.find_by_id(rule.rule_id)
        assert found is not None
        assert found.rule_id == rule.rule_id

    def test_find_by_id_returns_none(self, repo: StubRuleRepository) -> None:
        assert repo.find_by_id(PolicyRuleId()) is None

    def test_find_by_policy_id(self, repo: StubRuleRepository) -> None:
        rule = _make_rule()
        repo.save(rule)
        results = repo.find_by_policy_id(PolicyId())
        assert len(results) == 1

    def test_find_by_policy_id_multiple(self, repo: StubRuleRepository) -> None:
        repo.save(_make_rule())
        repo.save(_make_rule())
        results = repo.find_by_policy_id(PolicyId())
        assert len(results) == 2

    def test_find_by_policy_id_empty(self, repo: StubRuleRepository) -> None:
        assert repo.find_by_policy_id(PolicyId()) == []

    def test_find_enabled(self, repo: StubRuleRepository) -> None:
        rule = _make_rule(enabled=True)
        repo.save(rule)
        results = repo.find_enabled()
        assert len(results) == 1
        assert results[0].enabled is True

    def test_find_enabled_multiple(self, repo: StubRuleRepository) -> None:
        repo.save(_make_rule(enabled=True))
        repo.save(_make_rule(enabled=True))
        results = repo.find_enabled()
        assert len(results) == 2

    def test_find_enabled_empty(self, repo: StubRuleRepository) -> None:
        assert repo.find_enabled() == []

    def test_find_all(self, repo: StubRuleRepository) -> None:
        repo.save(_make_rule())
        repo.save(_make_rule())
        assert len(repo.find_all()) == 2

    def test_find_all_empty(self, repo: StubRuleRepository) -> None:
        assert repo.find_all() == []

    def test_save_updates_existing(self, repo: StubRuleRepository) -> None:
        rule = _make_rule(enabled=True)
        repo.save(rule)
        new_rule = PolicyRule(
            rule_id=rule.rule_id,
            condition=PolicyCondition("false"),
            action=PolicyAction("deny"),
            enabled=False,
        )
        repo.save(new_rule)
        found = repo.find_by_id(rule.rule_id)
        assert found is not None
        assert found.enabled is False

    def test_count_empty(self, repo: StubRuleRepository) -> None:
        assert repo.count() == 0

    def test_count_multiple(self, repo: StubRuleRepository) -> None:
        repo.save(_make_rule())
        repo.save(_make_rule())
        assert repo.count() == 2

    def test_save_duplicate_does_not_increase_count(
        self, repo: StubRuleRepository
    ) -> None:
        rule = _make_rule()
        repo.save(rule)
        repo.save(rule)
        assert repo.count() == 1


# =============================================================================
# PolicyEvaluationRepositoryPort contract tests
# =============================================================================


class TestEvaluationRepositoryPort:
    """Contract tests for PolicyEvaluationRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubEvaluationRepository:
        return StubEvaluationRepository()

    def test_save_and_find_by_id(self, repo: StubEvaluationRepository) -> None:
        evaluation = _make_evaluation()
        repo.save(evaluation)
        found = repo.find_by_id(evaluation.evaluation_id)
        assert found is not None
        assert found.evaluation_id == evaluation.evaluation_id

    def test_find_by_id_returns_none(
        self, repo: StubEvaluationRepository
    ) -> None:
        assert repo.find_by_id(EvaluationId()) is None

    def test_find_by_status(self, repo: StubEvaluationRepository) -> None:
        evaluation = _make_evaluation(status=PolicyEvaluationStatus.PENDING)
        repo.save(evaluation)
        results = repo.find_by_status(PolicyEvaluationStatus.PENDING)
        assert len(results) == 1
        assert results[0].evaluation_id == evaluation.evaluation_id

    def test_find_by_status_multiple(
        self, repo: StubEvaluationRepository
    ) -> None:
        e1 = _make_evaluation(status=PolicyEvaluationStatus.PENDING)
        e2 = _make_evaluation(status=PolicyEvaluationStatus.PENDING)
        e3 = _make_evaluation(status=PolicyEvaluationStatus.COMPLETED)
        repo.save(e1)
        repo.save(e2)
        repo.save(e3)
        results = repo.find_by_status(PolicyEvaluationStatus.PENDING)
        assert len(results) == 2

    def test_find_by_status_empty(
        self, repo: StubEvaluationRepository
    ) -> None:
        assert repo.find_by_status(PolicyEvaluationStatus.FAILED) == []

    def test_find_by_status_all(
        self, repo: StubEvaluationRepository
    ) -> None:
        e1 = _make_evaluation(status=PolicyEvaluationStatus.PENDING)
        e2 = _make_evaluation(status=PolicyEvaluationStatus.COMPLETED)
        repo.save(e1)
        repo.save(e2)
        assert len(repo.find_by_status(PolicyEvaluationStatus.PENDING)) == 1
        assert len(repo.find_by_status(PolicyEvaluationStatus.COMPLETED)) == 1

    def test_find_by_policy_id(self, repo: StubEvaluationRepository) -> None:
        evaluation = _make_evaluation()
        repo.save(evaluation)
        results = repo.find_by_policy_id(PolicyId())
        assert len(results) == 1

    def test_find_by_policy_id_multiple(
        self, repo: StubEvaluationRepository
    ) -> None:
        repo.save(_make_evaluation())
        repo.save(_make_evaluation())
        results = repo.find_by_policy_id(PolicyId())
        assert len(results) == 2

    def test_find_by_policy_id_empty(
        self, repo: StubEvaluationRepository
    ) -> None:
        assert repo.find_by_policy_id(PolicyId()) == []

    def test_find_all(self, repo: StubEvaluationRepository) -> None:
        repo.save(_make_evaluation())
        repo.save(_make_evaluation())
        assert len(repo.find_all()) == 2

    def test_find_all_empty(self, repo: StubEvaluationRepository) -> None:
        assert repo.find_all() == []

    def test_save_updates_existing(
        self, repo: StubEvaluationRepository
    ) -> None:
        evaluation = _make_evaluation(status=PolicyEvaluationStatus.PENDING)
        repo.save(evaluation)
        evaluation._status = PolicyEvaluationStatus.EVALUATING
        repo.save(evaluation)
        found = repo.find_by_id(evaluation.evaluation_id)
        assert found is not None
        assert found.status == PolicyEvaluationStatus.EVALUATING

    def test_count_empty(self, repo: StubEvaluationRepository) -> None:
        assert repo.count() == 0

    def test_count_multiple(self, repo: StubEvaluationRepository) -> None:
        repo.save(_make_evaluation())
        repo.save(_make_evaluation())
        assert repo.count() == 2

    def test_save_duplicate_does_not_increase_count(
        self, repo: StubEvaluationRepository
    ) -> None:
        evaluation = _make_evaluation()
        repo.save(evaluation)
        repo.save(evaluation)
        assert repo.count() == 1


# =============================================================================
# PolicyOutboxPort contract tests
# =============================================================================


class TestOutboxPort:
    """Contract tests for PolicyOutboxPort."""

    @pytest.fixture
    def outbox(self) -> StubOutbox:
        return StubOutbox()

    def test_append_and_fetch(self, outbox: StubOutbox) -> None:
        event = _make_event()
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert unpublished[0] == event

    def test_fetch_empty(self, outbox: StubOutbox) -> None:
        assert outbox.fetch_unpublished() == []

    def test_fifo_order(self, outbox: StubOutbox) -> None:
        e1 = _make_event()
        e2 = _make_event()
        e3 = _make_event()
        outbox.append(e1)
        outbox.append(e2)
        outbox.append(e3)
        unpublished = outbox.fetch_unpublished()
        assert unpublished[0] == e1
        assert unpublished[1] == e2
        assert unpublished[2] == e3

    def test_fetch_respects_limit(self, outbox: StubOutbox) -> None:
        for _ in range(10):
            outbox.append(_make_event())
        assert len(outbox.fetch_unpublished(limit=3)) == 3
        assert len(outbox.fetch_unpublished(limit=0)) == 0

    def test_fetch_default_limit(self, outbox: StubOutbox) -> None:
        for _ in range(200):
            outbox.append(_make_event())
        assert len(outbox.fetch_unpublished()) == 100

    def test_mark_published_removes_event(self, outbox: StubOutbox) -> None:
        event = _make_event()
        outbox.append(event)
        aid = str(event.event_id)
        outbox.mark_published(aid)
        assert outbox.fetch_unpublished() == []

    def test_mark_published_idempotent(self, outbox: StubOutbox) -> None:
        event = _make_event()
        outbox.append(event)
        aid = str(event.event_id)
        outbox.mark_published(aid)
        outbox.mark_published(aid)
        assert outbox.fetch_unpublished() == []

    def test_mark_published_partial(self, outbox: StubOutbox) -> None:
        e1 = _make_event()
        e2 = _make_event()
        e3 = _make_event()
        outbox.append(e1)
        outbox.append(e2)
        outbox.append(e3)
        outbox.mark_published(str(e2.event_id))
        unpublished = outbox.fetch_unpublished()
        assert e1 in unpublished
        assert e2 not in unpublished
        assert e3 in unpublished

    def test_mark_published_nonexistent(self, outbox: StubOutbox) -> None:
        event = _make_event()
        outbox.append(event)
        outbox.mark_published("nonexistent-id")
        assert len(outbox.fetch_unpublished()) == 1

    def test_append_after_mark_published(self, outbox: StubOutbox) -> None:
        e1 = _make_event()
        e2 = _make_event()
        outbox.append(e1)
        outbox.mark_published(str(e1.event_id))
        outbox.append(e2)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert unpublished[0] == e2

    def test_fetch_limit_exceeds_events(self, outbox: StubOutbox) -> None:
        for _ in range(5):
            outbox.append(_make_event())
        assert len(outbox.fetch_unpublished(limit=100)) == 5

    def test_fetch_fifo_across_many_events(self, outbox: StubOutbox) -> None:
        events = [_make_event() for _ in range(50)]
        for e in events:
            outbox.append(e)
        unpublished = outbox.fetch_unpublished(limit=50)
        for i in range(50):
            assert unpublished[i] == events[i]

    def test_mark_published_keeps_others(self, outbox: StubOutbox) -> None:
        events = [_make_event() for _ in range(5)]
        for e in events:
            outbox.append(e)
        outbox.mark_published(str(events[0].event_id))
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 4
        assert events[0] not in unpublished


# =============================================================================
# PolicyClockPort contract tests
# =============================================================================


class TestClockPort:
    """Contract tests for PolicyClockPort."""

    def test_now_returns_datetime(self) -> None:
        clock = StubClock()
        result = clock.now()
        assert isinstance(result, datetime)

    def test_now_is_utc(self) -> None:
        clock = StubClock()
        result = clock.now()
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result) == timezone.utc.utcoffset(result)

    def test_now_frozen_value(self) -> None:
        expected = datetime(2025, 1, 1, tzinfo=timezone.utc)
        clock = StubClock(now=expected)
        assert clock.now() == expected

    def test_now_consistent(self) -> None:
        clock = StubClock()
        assert clock.now() == clock.now()

    def test_now_timezone_aware(self) -> None:
        clock = StubClock()
        assert clock.now().tzinfo is not None


# =============================================================================
# PolicyIdGeneratorPort contract tests
# =============================================================================


class TestIdGeneratorPort:
    """Contract tests for PolicyIdGeneratorPort."""

    def test_generate_policy_id_returns_string(self) -> None:
        gen = StubIdGenerator()
        result = gen.generate_policy_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_rule_id_returns_string(self) -> None:
        gen = StubIdGenerator()
        result = gen.generate_rule_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_evaluation_id_returns_string(self) -> None:
        gen = StubIdGenerator()
        result = gen.generate_evaluation_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_uniqueness(self) -> None:
        gen = StubIdGenerator()
        ids = {
            gen.generate_policy_id(),
            gen.generate_rule_id(),
            gen.generate_evaluation_id(),
        }
        assert len(ids) == 3

    def test_incrementing_sequence(self) -> None:
        gen = StubIdGenerator()
        a = gen.generate_policy_id()
        b = gen.generate_policy_id()
        assert a != b

    def test_ids_are_different_prefixes(self) -> None:
        gen = StubIdGenerator()
        aid = gen.generate_policy_id()
        tid = gen.generate_rule_id()
        eid = gen.generate_evaluation_id()
        assert aid != tid != eid


# =============================================================================
# Protocol structural conformance
# =============================================================================


class TestPolicyPortProtocolConformance:
    """Verify stub classes structurally conform to their protocols."""

    def test_policy_repository_has_all_methods(self) -> None:
        methods = {
            "save", "find_by_id", "find_by_status", "find_by_priority",
            "find_by_scope", "find_all", "count",
        }
        stub_methods = {
            m for m in dir(StubPolicyRepository) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_rule_repository_has_all_methods(self) -> None:
        methods = {
            "save", "find_by_id", "find_by_policy_id", "find_enabled",
            "find_all", "count",
        }
        stub_methods = {
            m for m in dir(StubRuleRepository) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_evaluation_repository_has_all_methods(self) -> None:
        methods = {
            "save", "find_by_id", "find_by_status", "find_by_policy_id",
            "find_all", "count",
        }
        stub_methods = {
            m for m in dir(StubEvaluationRepository) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_outbox_has_all_methods(self) -> None:
        methods = {"append", "fetch_unpublished", "mark_published"}
        stub_methods = {
            m for m in dir(StubOutbox) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_clock_has_now_method(self) -> None:
        assert hasattr(StubClock, "now")

    def test_id_generator_has_all_methods(self) -> None:
        methods = {
            "generate_policy_id", "generate_rule_id",
            "generate_evaluation_id",
        }
        stub_methods = {
            m for m in dir(StubIdGenerator) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_port_modules_importable(self) -> None:
        from backend.policy.application.ports import (
            PolicyClockPort,
            PolicyEvaluationRepositoryPort,
            PolicyIdGeneratorPort,
            PolicyOutboxEvent,
            PolicyOutboxPort,
            PolicyRepositoryPort,
            PolicyRuleRepositoryPort,
        )
        assert PolicyClockPort is not None
        assert PolicyEvaluationRepositoryPort is not None
        assert PolicyIdGeneratorPort is not None
        assert PolicyOutboxEvent is not None
        assert PolicyOutboxPort is not None
        assert PolicyRepositoryPort is not None
        assert PolicyRuleRepositoryPort is not None

    def test_protocols_are_abstract(self) -> None:
        with pytest.raises(TypeError):
            PolicyRepositoryPort()
        with pytest.raises(TypeError):
            PolicyRuleRepositoryPort()
        with pytest.raises(TypeError):
            PolicyEvaluationRepositoryPort()
        with pytest.raises(TypeError):
            PolicyOutboxPort()
        with pytest.raises(TypeError):
            PolicyClockPort()
        with pytest.raises(TypeError):
            PolicyIdGeneratorPort()


# =============================================================================
# Outbox event union conformance
# =============================================================================


class TestPolicyOutboxEventUnion:
    """Verify that all domain events satisfy the outbox event union."""

    def test_policy_created_is_event(self) -> None:
        event: PolicyOutboxEvent = PolicyCreated(
            policy_id=PolicyId(),
            name="n", description="d", priority="medium",
            scope="global", version="1.0.0",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_activated_is_event(self) -> None:
        event: PolicyOutboxEvent = PolicyActivated(
            policy_id=PolicyId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_disabled_is_event(self) -> None:
        event: PolicyOutboxEvent = PolicyDisabled(
            policy_id=PolicyId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_archived_is_event(self) -> None:
        event: PolicyOutboxEvent = PolicyArchived(
            policy_id=PolicyId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_rule_added_is_event(self) -> None:
        event: PolicyOutboxEvent = PolicyRuleAdded(
            rule_id=PolicyRuleId(), policy_id=PolicyId(),
            condition="true", action="allow",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_rule_removed_is_event(self) -> None:
        event: PolicyOutboxEvent = PolicyRuleRemoved(
            rule_id=PolicyRuleId(), policy_id=PolicyId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_rule_enabled_is_event(self) -> None:
        event: PolicyOutboxEvent = PolicyRuleEnabled(
            rule_id=PolicyRuleId(), policy_id=PolicyId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_rule_disabled_is_event(self) -> None:
        event: PolicyOutboxEvent = PolicyRuleDisabled(
            rule_id=PolicyRuleId(), policy_id=PolicyId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_evaluation_started_is_event(self) -> None:
        event: PolicyOutboxEvent = PolicyEvaluationStarted(
            policy_id=PolicyId(),
            evaluation_id=EvaluationId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_evaluation_completed_is_event(self) -> None:
        event: PolicyOutboxEvent = PolicyEvaluationCompleted(
            policy_id=PolicyId(),
            evaluation_id=EvaluationId(),
            decision="allow", result="ok",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_policy_evaluation_failed_is_event(self) -> None:
        event: PolicyOutboxEvent = PolicyEvaluationFailed(
            policy_id=PolicyId(),
            evaluation_id=EvaluationId(),
            failure_reason="err",
            occurred_at=_NOW,
        )
        assert event is not None
