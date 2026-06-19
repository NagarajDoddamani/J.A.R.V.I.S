from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

import pytest

from backend.automation.application.ports.clock import AutomationClockPort
from backend.automation.application.ports.id_generator import (
    AutomationIdGeneratorPort,
)
from backend.automation.application.ports.outbox import (
    AutomationOutboxEvent,
    AutomationOutboxPort,
)
from backend.automation.application.ports.repository import (
    AutomationExecutionRepositoryPort,
    AutomationRepositoryPort,
    TriggerRepositoryPort,
)
from backend.automation.domain.model import (
    ActionAdded,
    ActionType,
    Automation,
    AutomationActivated,
    AutomationCreated,
    AutomationDisabled,
    AutomationExecution,
    AutomationExecutionCompleted,
    AutomationExecutionFailed,
    AutomationExecutionStarted,
    AutomationId,
    AutomationPaused,
    AutomationStatus,
    ExecutionMode,
    ExecutionResult,
    ExecutionStatus,
    FailureReason,
    Trigger,
    TriggerAdded,
    TriggerDisabled,
    TriggerEnabled,
    TriggerExpression,
    TriggerId,
    TriggerType,
    WorkflowExecutionId,
)

# =========================================================================
# Constants
# =========================================================================

_NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)


# =========================================================================
# Helpers
# =========================================================================


def _make_automation(
    *,
    automation_id: AutomationId | None = None,
    status: AutomationStatus = AutomationStatus.DRAFT,
    execution_mode: ExecutionMode = ExecutionMode.ONCE,
) -> Automation:
    a = Automation(execution_mode=execution_mode)
    if automation_id is not None:
        object.__setattr__(a, "_automation_id", automation_id)
    if status != AutomationStatus.DRAFT:
        object.__setattr__(a, "_status", status)
    return a


def _make_trigger(
    *,
    trigger_id: TriggerId | None = None,
    trigger_type: TriggerType = TriggerType.MANUAL,
    expression: TriggerExpression | None = None,
    enabled: bool = True,
) -> Trigger:
    return Trigger(
        trigger_id=trigger_id or TriggerId(),
        trigger_type=trigger_type,
        expression=expression,
        enabled=enabled,
    )


def _make_execution(
    *,
    execution_id: WorkflowExecutionId | None = None,
    status: ExecutionStatus = ExecutionStatus.PENDING,
    automation_id: AutomationId | None = None,
) -> AutomationExecution:
    return AutomationExecution(
        execution_id=execution_id or WorkflowExecutionId(),
        automation_id=automation_id or AutomationId(),
        status=status,
    )


def _make_event() -> AutomationCreated:
    return AutomationCreated(
        automation_id=AutomationId(),
        name="test",
        description="test",
        execution_mode="once",
        occurred_at=_NOW,
    )


# =========================================================================
# Stub: AutomationRepositoryPort
# =========================================================================


class StubAutomationRepository:
    """Minimal stub conforming to AutomationRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, Automation] = {}

    def save(self, automation: Automation) -> None:
        self._store[str(automation.automation_id)] = automation

    def find_by_id(self, automation_id: AutomationId) -> Automation | None:
        return self._store.get(str(automation_id))

    def find_by_status(self, status: AutomationStatus) -> list[Automation]:
        return [a for a in self._store.values() if a.status == status]

    def find_by_execution_mode(self, mode: ExecutionMode) -> list[Automation]:
        return [a for a in self._store.values() if a.execution_mode == mode]

    def count(self) -> int:
        return len(self._store)


class TestAutomationRepositoryPort:
    """Contract tests for AutomationRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubAutomationRepository:
        return StubAutomationRepository()

    def test_save_and_find_by_id(self, repo: StubAutomationRepository) -> None:
        a = _make_automation()
        repo.save(a)
        found = repo.find_by_id(a.automation_id)
        assert found is not None
        assert found.automation_id == a.automation_id

    def test_find_by_id_returns_none(self, repo: StubAutomationRepository) -> None:
        assert repo.find_by_id(AutomationId()) is None

    def test_find_by_status(self, repo: StubAutomationRepository) -> None:
        draft = _make_automation(status=AutomationStatus.DRAFT)
        active = _make_automation(status=AutomationStatus.ACTIVE)
        repo.save(draft)
        repo.save(active)
        results = repo.find_by_status(AutomationStatus.DRAFT)
        assert len(results) == 1
        assert results[0].automation_id == draft.automation_id

    def test_find_by_status_multiple(self, repo: StubAutomationRepository) -> None:
        for _ in range(3):
            repo.save(_make_automation(status=AutomationStatus.ACTIVE))
        repo.save(_make_automation(status=AutomationStatus.DRAFT))
        assert len(repo.find_by_status(AutomationStatus.ACTIVE)) == 3

    def test_find_by_status_empty(self, repo: StubAutomationRepository) -> None:
        assert repo.find_by_status(AutomationStatus.COMPLETED) == []

    def test_find_by_status_all(self, repo: StubAutomationRepository) -> None:
        for s in AutomationStatus:
            repo.save(_make_automation(status=s))
        for s in AutomationStatus:
            assert len(repo.find_by_status(s)) == 1

    def test_find_by_execution_mode(self, repo: StubAutomationRepository) -> None:
        once = _make_automation(execution_mode=ExecutionMode.ONCE)
        recurring = _make_automation(execution_mode=ExecutionMode.RECURRING)
        repo.save(once)
        repo.save(recurring)
        results = repo.find_by_execution_mode(ExecutionMode.ONCE)
        assert len(results) == 1
        assert results[0].automation_id == once.automation_id

    def test_find_by_execution_mode_multiple(
        self, repo: StubAutomationRepository
    ) -> None:
        for _ in range(2):
            repo.save(_make_automation(execution_mode=ExecutionMode.RECURRING))
        assert len(repo.find_by_execution_mode(ExecutionMode.RECURRING)) == 2

    def test_find_by_execution_mode_empty(
        self, repo: StubAutomationRepository
    ) -> None:
        assert repo.find_by_execution_mode(ExecutionMode.CONTINUOUS) == []

    def test_save_updates_existing(self, repo: StubAutomationRepository) -> None:
        a = _make_automation()
        repo.save(a)
        object.__setattr__(a, "_status", AutomationStatus.ACTIVE)
        repo.save(a)
        found = repo.find_by_id(a.automation_id)
        assert found is not None
        assert found.status == AutomationStatus.ACTIVE

    def test_count_empty(self, repo: StubAutomationRepository) -> None:
        assert repo.count() == 0

    def test_count_multiple(self, repo: StubAutomationRepository) -> None:
        for _ in range(5):
            repo.save(_make_automation())
        assert repo.count() == 5

    def test_save_duplicate_does_not_increase_count(
        self, repo: StubAutomationRepository
    ) -> None:
        a = _make_automation()
        repo.save(a)
        repo.save(a)
        assert repo.count() == 1


# =========================================================================
# Stub: TriggerRepositoryPort
# =========================================================================


class StubTriggerRepository:
    """Minimal stub conforming to TriggerRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, Trigger] = {}

    def save(self, trigger: Trigger) -> None:
        self._store[str(trigger.trigger_id)] = trigger

    def find_by_id(self, trigger_id: TriggerId) -> Trigger | None:
        return self._store.get(str(trigger_id))

    def find_by_type(self, trigger_type: TriggerType) -> list[Trigger]:
        return [t for t in self._store.values() if t.trigger_type == trigger_type]

    def find_enabled(self) -> list[Trigger]:
        return [t for t in self._store.values() if t.enabled]

    def count(self) -> int:
        return len(self._store)


class TestTriggerRepositoryPort:
    """Contract tests for TriggerRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubTriggerRepository:
        return StubTriggerRepository()

    def test_save_and_find_by_id(self, repo: StubTriggerRepository) -> None:
        t = _make_trigger()
        repo.save(t)
        found = repo.find_by_id(t.trigger_id)
        assert found is not None
        assert found.trigger_id == t.trigger_id

    def test_find_by_id_returns_none(self, repo: StubTriggerRepository) -> None:
        assert repo.find_by_id(TriggerId()) is None

    def test_find_by_type(self, repo: StubTriggerRepository) -> None:
        manual = _make_trigger(trigger_type=TriggerType.MANUAL)
        scheduled = _make_trigger(
            trigger_type=TriggerType.SCHEDULED,
            expression=TriggerExpression(value="0 8 * * *"),
        )
        repo.save(manual)
        repo.save(scheduled)
        results = repo.find_by_type(TriggerType.MANUAL)
        assert len(results) == 1
        assert results[0].trigger_id == manual.trigger_id

    def test_find_by_type_multiple(self, repo: StubTriggerRepository) -> None:
        for _ in range(3):
            repo.save(_make_trigger(trigger_type=TriggerType.EVENT))
        assert len(repo.find_by_type(TriggerType.EVENT)) == 3

    def test_find_by_type_empty(self, repo: StubTriggerRepository) -> None:
        assert repo.find_by_type(TriggerType.WEBHOOK) == []

    def test_find_by_type_all(self, repo: StubTriggerRepository) -> None:
        for tt in TriggerType:
            expr = TriggerExpression(value="0 8 * * *") if tt == TriggerType.SCHEDULED else None
            repo.save(_make_trigger(trigger_type=tt, expression=expr))
        for tt in TriggerType:
            assert len(repo.find_by_type(tt)) == 1

    def test_find_enabled(self, repo: StubTriggerRepository) -> None:
        enabled = _make_trigger(enabled=True)
        disabled = _make_trigger(enabled=False)
        repo.save(enabled)
        repo.save(disabled)
        results = repo.find_enabled()
        assert len(results) == 1
        assert results[0].trigger_id == enabled.trigger_id

    def test_find_enabled_multiple(self, repo: StubTriggerRepository) -> None:
        for _ in range(4):
            repo.save(_make_trigger(enabled=True))
        repo.save(_make_trigger(enabled=False))
        assert len(repo.find_enabled()) == 4

    def test_find_enabled_empty(self, repo: StubTriggerRepository) -> None:
        repo.save(_make_trigger(enabled=False))
        assert repo.find_enabled() == []

    def test_save_updates_existing(self, repo: StubTriggerRepository) -> None:
        t = _make_trigger(enabled=True)
        repo.save(t)
        object.__setattr__(t, "_enabled", False)
        repo.save(t)
        found = repo.find_by_id(t.trigger_id)
        assert found is not None
        assert found.enabled is False

    def test_count_empty(self, repo: StubTriggerRepository) -> None:
        assert repo.count() == 0

    def test_count_multiple(self, repo: StubTriggerRepository) -> None:
        for _ in range(3):
            repo.save(_make_trigger())
        assert repo.count() == 3

    def test_save_duplicate_does_not_increase_count(
        self, repo: StubTriggerRepository
    ) -> None:
        t = _make_trigger()
        repo.save(t)
        repo.save(t)
        assert repo.count() == 1


# =========================================================================
# Stub: AutomationExecutionRepositoryPort
# =========================================================================


class StubExecutionRepository:
    """Minimal stub conforming to AutomationExecutionRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, AutomationExecution] = {}

    def save(self, execution: AutomationExecution) -> None:
        self._store[str(execution.execution_id)] = execution

    def find_by_id(
        self, execution_id: WorkflowExecutionId
    ) -> AutomationExecution | None:
        return self._store.get(str(execution_id))

    def find_by_status(self, status: ExecutionStatus) -> list[AutomationExecution]:
        return [e for e in self._store.values() if e.status == status]

    def find_by_automation_id(
        self, automation_id: AutomationId
    ) -> list[AutomationExecution]:
        return [e for e in self._store.values() if e.automation_id == automation_id]

    def count(self) -> int:
        return len(self._store)


class TestExecutionRepositoryPort:
    """Contract tests for AutomationExecutionRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubExecutionRepository:
        return StubExecutionRepository()

    def test_save_and_find_by_id(self, repo: StubExecutionRepository) -> None:
        e = _make_execution()
        repo.save(e)
        found = repo.find_by_id(e.execution_id)
        assert found is not None
        assert found.execution_id == e.execution_id

    def test_find_by_id_returns_none(self, repo: StubExecutionRepository) -> None:
        assert repo.find_by_id(WorkflowExecutionId()) is None

    def test_find_by_status(self, repo: StubExecutionRepository) -> None:
        pending = _make_execution(status=ExecutionStatus.PENDING)
        running = _make_execution(status=ExecutionStatus.RUNNING)
        repo.save(pending)
        repo.save(running)
        results = repo.find_by_status(ExecutionStatus.PENDING)
        assert len(results) == 1
        assert results[0].execution_id == pending.execution_id

    def test_find_by_status_multiple(self, repo: StubExecutionRepository) -> None:
        for _ in range(3):
            repo.save(_make_execution(status=ExecutionStatus.RUNNING))
        assert len(repo.find_by_status(ExecutionStatus.RUNNING)) == 3

    def test_find_by_status_empty(self, repo: StubExecutionRepository) -> None:
        assert repo.find_by_status(ExecutionStatus.FAILED) == []

    def test_find_by_status_all(self, repo: StubExecutionRepository) -> None:
        for s in ExecutionStatus:
            repo.save(_make_execution(status=s))
        for s in ExecutionStatus:
            assert len(repo.find_by_status(s)) == 1

    def test_find_by_automation_id(self, repo: StubExecutionRepository) -> None:
        aid = AutomationId()
        e = _make_execution(automation_id=aid)
        repo.save(e)
        results = repo.find_by_automation_id(aid)
        assert len(results) == 1
        assert results[0].execution_id == e.execution_id

    def test_find_by_automation_id_multiple(
        self, repo: StubExecutionRepository
    ) -> None:
        aid = AutomationId()
        for _ in range(3):
            repo.save(_make_execution(automation_id=aid))
        assert len(repo.find_by_automation_id(aid)) == 3

    def test_find_by_automation_id_empty(
        self, repo: StubExecutionRepository
    ) -> None:
        assert repo.find_by_automation_id(AutomationId()) == []

    def test_save_updates_existing(self, repo: StubExecutionRepository) -> None:
        e = _make_execution()
        repo.save(e)
        object.__setattr__(e, "_status", ExecutionStatus.RUNNING)
        repo.save(e)
        found = repo.find_by_id(e.execution_id)
        assert found is not None
        assert found.status == ExecutionStatus.RUNNING

    def test_count_empty(self, repo: StubExecutionRepository) -> None:
        assert repo.count() == 0

    def test_count_multiple(self, repo: StubExecutionRepository) -> None:
        for _ in range(4):
            repo.save(_make_execution())
        assert repo.count() == 4

    def test_save_duplicate_does_not_increase_count(
        self, repo: StubExecutionRepository
    ) -> None:
        e = _make_execution()
        repo.save(e)
        repo.save(e)
        assert repo.count() == 1


# =========================================================================
# Stub: AutomationOutboxPort
# =========================================================================


class StubOutbox:
    """Minimal stub conforming to AutomationOutboxPort."""

    def __init__(self) -> None:
        self._store: list[tuple[str, AutomationOutboxEvent]] = []

    def append(self, event: AutomationOutboxEvent) -> None:
        aggregate_id = str(event.event_id)
        self._store.append((aggregate_id, event))

    def fetch_unpublished(self, limit: int = 100) -> list[AutomationOutboxEvent]:
        return [event for _, event in self._store[:limit]]

    def mark_published(self, aggregate_id: str) -> None:
        self._store = [
            (aid, event)
            for aid, event in self._store
            if aid != aggregate_id
        ]


class TestOutboxPort:
    """Contract tests for AutomationOutboxPort."""

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
        outbox.mark_published(str(event.event_id))
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
        outbox.append(e1)
        outbox.append(e2)
        outbox.mark_published(str(e1.event_id))
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert unpublished[0] == e2

    def test_mark_published_nonexistent(self, outbox: StubOutbox) -> None:
        outbox.mark_published("nonexistent-id")
        assert outbox.fetch_unpublished() == []

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
        for i in range(2):
            outbox.mark_published(str(events[i].event_id))
        assert len(outbox.fetch_unpublished()) == 3


# =========================================================================
# Stub: AutomationClockPort
# =========================================================================


class StubClock:
    """Minimal stub conforming to AutomationClockPort."""

    def __init__(self, now: datetime = _NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class TestClockPort:
    """Contract tests for AutomationClockPort."""

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


# =========================================================================
# Stub: AutomationIdGeneratorPort
# =========================================================================


class StubIdGenerator:
    """Minimal stub conforming to AutomationIdGeneratorPort."""

    def __init__(self) -> None:
        self._counter = 0

    def generate_automation_id(self) -> str:
        self._counter += 1
        return f"auto-{self._counter}"

    def generate_trigger_id(self) -> str:
        self._counter += 1
        return f"trig-{self._counter}"

    def generate_execution_id(self) -> str:
        self._counter += 1
        return f"exec-{self._counter}"


class TestIdGeneratorPort:
    """Contract tests for AutomationIdGeneratorPort."""

    def test_generate_automation_id_returns_string(self) -> None:
        gen = StubIdGenerator()
        result = gen.generate_automation_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_trigger_id_returns_string(self) -> None:
        gen = StubIdGenerator()
        result = gen.generate_trigger_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_execution_id_returns_string(self) -> None:
        gen = StubIdGenerator()
        result = gen.generate_execution_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_uniqueness(self) -> None:
        gen = StubIdGenerator()
        ids = {
            gen.generate_automation_id(),
            gen.generate_trigger_id(),
            gen.generate_execution_id(),
        }
        assert len(ids) == 3

    def test_incrementing_sequence(self) -> None:
        gen = StubIdGenerator()
        a = gen.generate_automation_id()
        b = gen.generate_automation_id()
        assert a != b

    def test_ids_are_different_prefixes(self) -> None:
        gen = StubIdGenerator()
        aid = gen.generate_automation_id()
        tid = gen.generate_trigger_id()
        eid = gen.generate_execution_id()
        assert aid != tid != eid


# =========================================================================
# Outbox Event Union Conformance
# =========================================================================


class TestAutomationOutboxEventUnion:
    """Verify that all domain events satisfy the outbox event union."""

    def test_automation_created_is_event(self) -> None:
        event: AutomationOutboxEvent = AutomationCreated(
            automation_id=AutomationId(),
            name="n", description="d", execution_mode="once",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_automation_activated_is_event(self) -> None:
        event: AutomationOutboxEvent = AutomationActivated(
            automation_id=AutomationId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_automation_paused_is_event(self) -> None:
        event: AutomationOutboxEvent = AutomationPaused(
            automation_id=AutomationId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_automation_disabled_is_event(self) -> None:
        event: AutomationOutboxEvent = AutomationDisabled(
            automation_id=AutomationId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_execution_started_is_event(self) -> None:
        event: AutomationOutboxEvent = AutomationExecutionStarted(
            automation_id=AutomationId(),
            execution_id=WorkflowExecutionId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_execution_completed_is_event(self) -> None:
        event: AutomationOutboxEvent = AutomationExecutionCompleted(
            automation_id=AutomationId(),
            execution_id=WorkflowExecutionId(),
            result="ok", occurred_at=_NOW,
        )
        assert event is not None

    def test_execution_failed_is_event(self) -> None:
        event: AutomationOutboxEvent = AutomationExecutionFailed(
            automation_id=AutomationId(),
            execution_id=WorkflowExecutionId(),
            failure_reason="err", occurred_at=_NOW,
        )
        assert event is not None

    def test_trigger_added_is_event(self) -> None:
        event: AutomationOutboxEvent = TriggerAdded(
            trigger_id=TriggerId(), automation_id=AutomationId(),
            trigger_type="manual", expression="",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_trigger_enabled_is_event(self) -> None:
        event: AutomationOutboxEvent = TriggerEnabled(
            trigger_id=TriggerId(), automation_id=AutomationId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_trigger_disabled_is_event(self) -> None:
        event: AutomationOutboxEvent = TriggerDisabled(
            trigger_id=TriggerId(), automation_id=AutomationId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_action_added_is_event(self) -> None:
        event: AutomationOutboxEvent = ActionAdded(
            automation_id=AutomationId(), action_type="notification",
            occurred_at=_NOW,
        )
        assert event is not None


# =========================================================================
# Protocol Structural Conformance
# =========================================================================


class TestAutomationPortProtocolConformance:
    """Verify stub classes structurally conform to their protocols."""

    def test_automation_repository_has_all_methods(self) -> None:
        methods = {"save", "find_by_id", "find_by_status",
                   "find_by_execution_mode", "count"}
        stub_methods = {
            m for m in dir(StubAutomationRepository) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_trigger_repository_has_all_methods(self) -> None:
        methods = {"save", "find_by_id", "find_by_type",
                   "find_enabled", "count"}
        stub_methods = {
            m for m in dir(StubTriggerRepository) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_execution_repository_has_all_methods(self) -> None:
        methods = {"save", "find_by_id", "find_by_status",
                   "find_by_automation_id", "count"}
        stub_methods = {
            m for m in dir(StubExecutionRepository) if not m.startswith("_")
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
        methods = {"generate_automation_id", "generate_trigger_id",
                   "generate_execution_id"}
        stub_methods = {
            m for m in dir(StubIdGenerator) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_port_modules_importable(self) -> None:
        from backend.automation.application.ports import (
            AutomationClockPort,
            AutomationExecutionRepositoryPort,
            AutomationIdGeneratorPort,
            AutomationOutboxEvent,
            AutomationOutboxPort,
            AutomationRepositoryPort,
            TriggerRepositoryPort,
        )
        assert AutomationClockPort is not None
        assert AutomationExecutionRepositoryPort is not None
        assert AutomationIdGeneratorPort is not None
        assert AutomationOutboxEvent is not None
        assert AutomationOutboxPort is not None
        assert AutomationRepositoryPort is not None
        assert TriggerRepositoryPort is not None

    def test_protocols_are_abstract(self) -> None:
        with pytest.raises(TypeError):
            AutomationRepositoryPort()
        with pytest.raises(TypeError):
            TriggerRepositoryPort()
        with pytest.raises(TypeError):
            AutomationExecutionRepositoryPort()
        with pytest.raises(TypeError):
            AutomationOutboxPort()
        with pytest.raises(TypeError):
            AutomationClockPort()
        with pytest.raises(TypeError):
            AutomationIdGeneratorPort()
