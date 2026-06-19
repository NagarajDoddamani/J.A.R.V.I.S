from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID, uuid4

import pytest

from backend.agent.application.ports.clock import AgentClockPort
from backend.agent.application.ports.id_generator import AgentIdGeneratorPort
from backend.agent.application.ports.outbox import (
    AgentOutboxEvent,
    AgentOutboxPort,
)
from backend.agent.application.ports.repository import (
    AgentExecutionRepositoryPort,
    AgentRepositoryPort,
    AgentTaskRepositoryPort,
)
from backend.agent.domain.model import (
    Agent,
    AgentActivated,
    AgentCreated,
    AgentDisabled,
    AgentExecution,
    AgentExecutionCompleted,
    AgentExecutionFailed,
    AgentExecutionId,
    AgentExecutionStarted,
    AgentExecutionStatus,
    AgentId,
    AgentPaused,
    AgentStatus,
    AgentTask,
    AgentTaskCancelled,
    AgentTaskCompleted,
    AgentTaskCreated,
    AgentTaskFailed,
    AgentTaskId,
    AgentTaskStarted,
    AgentTaskStatus,
    AgentType,
)

# =========================================================================
# Constants
# =========================================================================

_NOW = datetime(2026, 6, 16, 12, 0, 0, tzinfo=timezone.utc)


# =========================================================================
# Helpers
# =========================================================================


def _make_agent(
    *,
    agent_id: AgentId | None = None,
    status: AgentStatus = AgentStatus.IDLE,
    agent_type: AgentType = AgentType.COORDINATOR,
) -> Agent:
    agent = Agent(
        agent_id=agent_id or AgentId(),
        agent_type=agent_type,
        status=status,
    )
    return agent


def _make_task(
    *,
    task_id: AgentTaskId | None = None,
    status: AgentTaskStatus = AgentTaskStatus.PENDING,
) -> AgentTask:
    task = AgentTask(
        task_id=task_id or AgentTaskId(),
        status=status,
    )
    return task


def _make_execution(
    *,
    execution_id: AgentExecutionId | None = None,
    status: AgentExecutionStatus = AgentExecutionStatus.PENDING,
) -> AgentExecution:
    return AgentExecution(
        execution_id=execution_id or AgentExecutionId(),
        status=status,
    )


def _make_created_event() -> AgentCreated:
    return AgentCreated(
        agent_id=AgentId(),
        agent_type="research",
        name="test",
        occurred_at=_NOW,
    )


# =========================================================================
# Stub: AgentRepositoryPort
# =========================================================================


class StubAgentRepository:
    """Minimal stub conforming to AgentRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, Agent] = {}

    def save(self, agent: Agent) -> None:
        self._store[str(agent.agent_id)] = agent

    def find_by_id(self, agent_id: AgentId) -> Agent | None:
        return self._store.get(str(agent_id))

    def find_by_status(self, status: AgentStatus) -> list[Agent]:
        return [a for a in self._store.values() if a.status == status]

    def find_by_type(self, agent_type: AgentType) -> list[Agent]:
        return [a for a in self._store.values() if a.agent_type == agent_type]

    def find_all(self) -> list[Agent]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class TestAgentRepositoryPort:
    """Contract tests for AgentRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubAgentRepository:
        return StubAgentRepository()

    def test_save_and_find_by_id(self, repo: StubAgentRepository) -> None:
        agent = _make_agent()
        repo.save(agent)
        found = repo.find_by_id(agent.agent_id)
        assert found is not None
        assert found.agent_id == agent.agent_id

    def test_find_by_id_returns_none(self, repo: StubAgentRepository) -> None:
        assert repo.find_by_id(AgentId()) is None

    def test_find_by_status(self, repo: StubAgentRepository) -> None:
        idle = _make_agent(status=AgentStatus.IDLE)
        active = _make_agent(status=AgentStatus.ACTIVE)
        repo.save(idle)
        repo.save(active)
        results = repo.find_by_status(AgentStatus.IDLE)
        assert len(results) == 1
        assert results[0].agent_id == idle.agent_id

    def test_find_by_status_multiple(self, repo: StubAgentRepository) -> None:
        for _ in range(3):
            repo.save(_make_agent(status=AgentStatus.ACTIVE))
        repo.save(_make_agent(status=AgentStatus.IDLE))
        assert len(repo.find_by_status(AgentStatus.ACTIVE)) == 3

    def test_find_by_status_empty(self, repo: StubAgentRepository) -> None:
        assert repo.find_by_status(AgentStatus.DISABLED) == []

    def test_find_by_status_all(self, repo: StubAgentRepository) -> None:
        for s in AgentStatus:
            repo.save(_make_agent(status=s))
        for s in AgentStatus:
            assert len(repo.find_by_status(s)) == 1

    def test_find_by_type(self, repo: StubAgentRepository) -> None:
        coord = _make_agent(agent_type=AgentType.COORDINATOR)
        research = _make_agent(agent_type=AgentType.RESEARCH)
        repo.save(coord)
        repo.save(research)
        results = repo.find_by_type(AgentType.COORDINATOR)
        assert len(results) == 1
        assert results[0].agent_id == coord.agent_id

    def test_find_by_type_multiple(self, repo: StubAgentRepository) -> None:
        for _ in range(2):
            repo.save(_make_agent(agent_type=AgentType.KNOWLEDGE))
        assert len(repo.find_by_type(AgentType.KNOWLEDGE)) == 2

    def test_find_by_type_empty(self, repo: StubAgentRepository) -> None:
        assert repo.find_by_type(AgentType.AUTOMATION) == []

    def test_find_by_type_all_types(self, repo: StubAgentRepository) -> None:
        for t in AgentType:
            repo.save(_make_agent(agent_type=t))
        for t in AgentType:
            assert len(repo.find_by_type(t)) == 1

    def test_save_updates_existing(self, repo: StubAgentRepository) -> None:
        agent = _make_agent()
        repo.save(agent)
        object.__setattr__(agent, "_status", AgentStatus.ACTIVE)
        repo.save(agent)
        found = repo.find_by_id(agent.agent_id)
        assert found is not None
        assert found.status == AgentStatus.ACTIVE

    def test_count_empty(self, repo: StubAgentRepository) -> None:
        assert repo.count() == 0

    def test_count_multiple(self, repo: StubAgentRepository) -> None:
        for _ in range(5):
            repo.save(_make_agent())
        assert repo.count() == 5

    def test_save_duplicate_does_not_increase_count(
        self, repo: StubAgentRepository
    ) -> None:
        agent = _make_agent()
        repo.save(agent)
        repo.save(agent)
        assert repo.count() == 1

    def test_find_all_empty(self, repo: StubAgentRepository) -> None:
        assert repo.find_all() == []

    def test_find_all_multiple(self, repo: StubAgentRepository) -> None:
        for _ in range(3):
            repo.save(_make_agent())
        assert len(repo.find_all()) == 3


# =========================================================================
# Stub: AgentTaskRepositoryPort
# =========================================================================


class StubTaskRepository:
    """Minimal stub conforming to AgentTaskRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, AgentTask] = {}

    def save(self, task: AgentTask) -> None:
        self._store[str(task.task_id)] = task

    def find_by_id(self, task_id: AgentTaskId) -> AgentTask | None:
        return self._store.get(str(task_id))

    def find_by_agent_id(self, agent_id: AgentId) -> list[AgentTask]:
        return [t for t in self._store.values() if t.agent_id == agent_id]

    def find_by_status(self, status: AgentTaskStatus) -> list[AgentTask]:
        return [t for t in self._store.values() if t.status == status]

    def find_all(self) -> list[AgentTask]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class TestAgentTaskRepositoryPort:
    """Contract tests for AgentTaskRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubTaskRepository:
        return StubTaskRepository()

    def test_save_and_find_by_id(self, repo: StubTaskRepository) -> None:
        task = _make_task()
        repo.save(task)
        found = repo.find_by_id(task.task_id)
        assert found is not None
        assert found.task_id == task.task_id

    def test_find_by_id_returns_none(self, repo: StubTaskRepository) -> None:
        assert repo.find_by_id(AgentTaskId()) is None

    def test_find_by_status(self, repo: StubTaskRepository) -> None:
        pending = _make_task(status=AgentTaskStatus.PENDING)
        running = _make_task(status=AgentTaskStatus.RUNNING)
        repo.save(pending)
        repo.save(running)
        results = repo.find_by_status(AgentTaskStatus.PENDING)
        assert len(results) == 1
        assert results[0].task_id == pending.task_id

    def test_find_by_status_multiple(self, repo: StubTaskRepository) -> None:
        for _ in range(3):
            repo.save(_make_task(status=AgentTaskStatus.RUNNING))
        assert len(repo.find_by_status(AgentTaskStatus.RUNNING)) == 3

    def test_find_by_status_empty(self, repo: StubTaskRepository) -> None:
        assert repo.find_by_status(AgentTaskStatus.FAILED) == []

    def test_find_by_agent_id(self, repo: StubTaskRepository) -> None:
        agent_id = AgentId()
        task = AgentTask(agent_id=agent_id)
        repo.save(task)
        results = repo.find_by_agent_id(agent_id)
        assert len(results) == 1
        assert results[0].task_id == task.task_id

    def test_find_by_agent_id_empty(self, repo: StubTaskRepository) -> None:
        assert repo.find_by_agent_id(AgentId()) == []

    def test_save_updates_existing(self, repo: StubTaskRepository) -> None:
        task = _make_task()
        repo.save(task)
        object.__setattr__(task, "_status", AgentTaskStatus.RUNNING)
        repo.save(task)
        found = repo.find_by_id(task.task_id)
        assert found is not None
        assert found.status == AgentTaskStatus.RUNNING

    def test_count_empty(self, repo: StubTaskRepository) -> None:
        assert repo.count() == 0

    def test_count_multiple(self, repo: StubTaskRepository) -> None:
        for _ in range(4):
            repo.save(_make_task())
        assert repo.count() == 4

    def test_save_duplicate_does_not_increase_count(
        self, repo: StubTaskRepository
    ) -> None:
        task = _make_task()
        repo.save(task)
        repo.save(task)
        assert repo.count() == 1

    def test_find_all_empty(self, repo: StubTaskRepository) -> None:
        assert repo.find_all() == []

    def test_find_all_multiple(self, repo: StubTaskRepository) -> None:
        for _ in range(3):
            repo.save(_make_task())
        assert len(repo.find_all()) == 3

    def test_find_by_agent_id_multiple(
        self, repo: StubTaskRepository
    ) -> None:
        agent_id = AgentId()
        t1 = AgentTask(agent_id=agent_id)
        t2 = AgentTask(agent_id=agent_id)
        repo.save(t1)
        repo.save(t2)
        assert len(repo.find_by_agent_id(agent_id)) == 2


# =========================================================================
# Stub: AgentExecutionRepositoryPort
# =========================================================================


class StubExecutionRepository:
    """Minimal stub conforming to AgentExecutionRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, AgentExecution] = {}

    def save(self, execution: AgentExecution) -> None:
        self._store[str(execution.execution_id)] = execution

    def find_by_id(
        self, execution_id: AgentExecutionId
    ) -> AgentExecution | None:
        return self._store.get(str(execution_id))

    def find_by_agent_id(self, agent_id: AgentId) -> list[AgentExecution]:
        return [e for e in self._store.values() if e.agent_id == agent_id]

    def find_by_task_id(self, task_id: AgentTaskId) -> list[AgentExecution]:
        return [e for e in self._store.values() if e.task_id == task_id]

    def find_by_status(
        self, status: AgentExecutionStatus
    ) -> list[AgentExecution]:
        return [e for e in self._store.values() if e.status == status]

    def find_all(self) -> list[AgentExecution]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class TestAgentExecutionRepositoryPort:
    """Contract tests for AgentExecutionRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubExecutionRepository:
        return StubExecutionRepository()

    def test_save_and_find_by_id(self, repo: StubExecutionRepository) -> None:
        execution = _make_execution()
        repo.save(execution)
        found = repo.find_by_id(execution.execution_id)
        assert found is not None
        assert found.execution_id == execution.execution_id

    def test_find_by_id_returns_none(
        self, repo: StubExecutionRepository
    ) -> None:
        assert repo.find_by_id(AgentExecutionId()) is None

    def test_find_by_status(self, repo: StubExecutionRepository) -> None:
        pending = _make_execution(status=AgentExecutionStatus.PENDING)
        executing = _make_execution(status=AgentExecutionStatus.EXECUTING)
        repo.save(pending)
        repo.save(executing)
        results = repo.find_by_status(AgentExecutionStatus.PENDING)
        assert len(results) == 1
        assert results[0].execution_id == pending.execution_id

    def test_find_by_status_multiple(
        self, repo: StubExecutionRepository
    ) -> None:
        for _ in range(3):
            repo.save(_make_execution(status=AgentExecutionStatus.EXECUTING))
        assert len(repo.find_by_status(AgentExecutionStatus.EXECUTING)) == 3

    def test_find_by_status_empty(
        self, repo: StubExecutionRepository
    ) -> None:
        assert repo.find_by_status(AgentExecutionStatus.FAILED) == []

    def test_find_by_agent_id(self, repo: StubExecutionRepository) -> None:
        agent_id = AgentId()
        execution = AgentExecution(agent_id=agent_id)
        repo.save(execution)
        results = repo.find_by_agent_id(agent_id)
        assert len(results) == 1
        assert results[0].execution_id == execution.execution_id

    def test_find_by_agent_id_empty(
        self, repo: StubExecutionRepository
    ) -> None:
        assert repo.find_by_agent_id(AgentId()) == []

    def test_find_by_task_id(self, repo: StubExecutionRepository) -> None:
        task_id = AgentTaskId()
        execution = AgentExecution(task_id=task_id)
        repo.save(execution)
        results = repo.find_by_task_id(task_id)
        assert len(results) == 1
        assert results[0].execution_id == execution.execution_id

    def test_find_by_task_id_empty(
        self, repo: StubExecutionRepository
    ) -> None:
        assert repo.find_by_task_id(AgentTaskId()) == []

    def test_save_updates_existing(
        self, repo: StubExecutionRepository
    ) -> None:
        execution = _make_execution()
        repo.save(execution)
        object.__setattr__(execution, "_status", AgentExecutionStatus.EXECUTING)
        repo.save(execution)
        found = repo.find_by_id(execution.execution_id)
        assert found is not None
        assert found.status == AgentExecutionStatus.EXECUTING

    def test_count_empty(self, repo: StubExecutionRepository) -> None:
        assert repo.count() == 0

    def test_count_multiple(self, repo: StubExecutionRepository) -> None:
        for _ in range(4):
            repo.save(_make_execution())
        assert repo.count() == 4

    def test_save_duplicate_does_not_increase_count(
        self, repo: StubExecutionRepository
    ) -> None:
        execution = _make_execution()
        repo.save(execution)
        repo.save(execution)
        assert repo.count() == 1

    def test_find_all_empty(self, repo: StubExecutionRepository) -> None:
        assert repo.find_all() == []

    def test_find_all_multiple(self, repo: StubExecutionRepository) -> None:
        for _ in range(3):
            repo.save(_make_execution())
        assert len(repo.find_all()) == 3

    def test_find_by_agent_id_multiple(
        self, repo: StubExecutionRepository
    ) -> None:
        agent_id = AgentId()
        e1 = AgentExecution(agent_id=agent_id)
        e2 = AgentExecution(agent_id=agent_id)
        repo.save(e1)
        repo.save(e2)
        assert len(repo.find_by_agent_id(agent_id)) == 2

    def test_find_by_task_id_multiple(
        self, repo: StubExecutionRepository
    ) -> None:
        task_id = AgentTaskId()
        e1 = AgentExecution(task_id=task_id)
        e2 = AgentExecution(task_id=task_id)
        repo.save(e1)
        repo.save(e2)
        assert len(repo.find_by_task_id(task_id)) == 2


# =========================================================================
# Stub: AgentOutboxPort
# =========================================================================


class StubOutbox:
    """Minimal stub conforming to AgentOutboxPort."""

    def __init__(self) -> None:
        self._store: list[tuple[str, AgentOutboxEvent]] = []

    def append(self, event: AgentOutboxEvent) -> None:
        aggregate_id = str(event.event_id)
        self._store.append((aggregate_id, event))

    def fetch_unpublished(
        self, limit: int = 100
    ) -> list[AgentOutboxEvent]:
        return [event for _, event in self._store[:limit]]

    def mark_published(self, aggregate_id: str) -> None:
        self._store = [
            (aid, event)
            for aid, event in self._store
            if aid != aggregate_id
        ]


class TestOutboxPort:
    """Contract tests for AgentOutboxPort."""

    @pytest.fixture
    def outbox(self) -> StubOutbox:
        return StubOutbox()

    def test_append_and_fetch(self, outbox: StubOutbox) -> None:
        event = _make_created_event()
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert unpublished[0] == event

    def test_fetch_empty(self, outbox: StubOutbox) -> None:
        assert outbox.fetch_unpublished() == []

    def test_fifo_order(self, outbox: StubOutbox) -> None:
        e1 = _make_created_event()
        e2 = _make_created_event()
        e3 = _make_created_event()
        outbox.append(e1)
        outbox.append(e2)
        outbox.append(e3)
        unpublished = outbox.fetch_unpublished()
        assert unpublished[0] == e1
        assert unpublished[1] == e2
        assert unpublished[2] == e3

    def test_fetch_respects_limit(self, outbox: StubOutbox) -> None:
        for _ in range(10):
            outbox.append(_make_created_event())
        assert len(outbox.fetch_unpublished(limit=3)) == 3
        assert len(outbox.fetch_unpublished(limit=0)) == 0

    def test_fetch_default_limit(self, outbox: StubOutbox) -> None:
        for _ in range(200):
            outbox.append(_make_created_event())
        assert len(outbox.fetch_unpublished()) == 100

    def test_mark_published_removes_event(self, outbox: StubOutbox) -> None:
        event = _make_created_event()
        outbox.append(event)
        outbox.mark_published(str(event.event_id))
        assert outbox.fetch_unpublished() == []

    def test_mark_published_idempotent(self, outbox: StubOutbox) -> None:
        event = _make_created_event()
        outbox.append(event)
        aid = str(event.event_id)
        outbox.mark_published(aid)
        outbox.mark_published(aid)
        assert outbox.fetch_unpublished() == []

    def test_mark_published_partial(self, outbox: StubOutbox) -> None:
        e1 = _make_created_event()
        e2 = _make_created_event()
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
        e1 = _make_created_event()
        e2 = _make_created_event()
        outbox.append(e1)
        outbox.mark_published(str(e1.event_id))
        outbox.append(e2)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert unpublished[0] == e2

    def test_fetch_limit_exceeds_events(self, outbox: StubOutbox) -> None:
        for _ in range(5):
            outbox.append(_make_created_event())
        assert len(outbox.fetch_unpublished(limit=100)) == 5

    def test_fetch_fifo_across_many_events(self, outbox: StubOutbox) -> None:
        events = [_make_created_event() for _ in range(50)]
        for e in events:
            outbox.append(e)
        unpublished = outbox.fetch_unpublished(limit=50)
        for i in range(50):
            assert unpublished[i] == events[i]

    def test_mark_published_keeps_others(self, outbox: StubOutbox) -> None:
        events = [_make_created_event() for _ in range(5)]
        for e in events:
            outbox.append(e)
        for i in range(2):
            outbox.mark_published(str(events[i].event_id))
        assert len(outbox.fetch_unpublished()) == 3

    def test_multiple_event_types(self, outbox: StubOutbox) -> None:
        aid = AgentId()
        tid = AgentTaskId()
        eid = AgentExecutionId()
        e1: AgentOutboxEvent = AgentCreated(
            agent_id=aid, agent_type="research", name="n", occurred_at=_NOW,
        )
        e2: AgentOutboxEvent = AgentActivated(
            agent_id=aid, occurred_at=_NOW,
        )
        e3: AgentOutboxEvent = AgentPaused(
            agent_id=aid, occurred_at=_NOW,
        )
        e4: AgentOutboxEvent = AgentDisabled(
            agent_id=aid, occurred_at=_NOW,
        )
        e5: AgentOutboxEvent = AgentTaskCreated(
            task_id=tid, agent_id=aid, goal="g", instruction="i",
            occurred_at=_NOW,
        )
        e6: AgentOutboxEvent = AgentTaskStarted(
            task_id=tid, agent_id=aid, occurred_at=_NOW,
        )
        e7: AgentOutboxEvent = AgentTaskCompleted(
            task_id=tid, agent_id=aid, result="ok", occurred_at=_NOW,
        )
        e8: AgentOutboxEvent = AgentTaskFailed(
            task_id=tid, agent_id=aid, failure_reason="err",
            occurred_at=_NOW,
        )
        e9: AgentOutboxEvent = AgentTaskCancelled(
            task_id=tid, agent_id=aid, occurred_at=_NOW,
        )
        e10: AgentOutboxEvent = AgentExecutionStarted(
            execution_id=eid, agent_id=aid, task_id=tid,
            occurred_at=_NOW,
        )
        e11: AgentOutboxEvent = AgentExecutionCompleted(
            execution_id=eid, agent_id=aid, task_id=tid, result="ok",
            occurred_at=_NOW,
        )
        e12: AgentOutboxEvent = AgentExecutionFailed(
            execution_id=eid, agent_id=aid, task_id=tid,
            failure_reason="err", occurred_at=_NOW,
        )
        for e in [e1, e2, e3, e4, e5, e6, e7, e8, e9, e10, e11, e12]:
            outbox.append(e)
        assert len(outbox.fetch_unpublished()) == 12


# =========================================================================
# Stub: AgentClockPort
# =========================================================================


class StubClock:
    """Minimal stub conforming to AgentClockPort."""

    def __init__(self, now: datetime = _NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class TestClockPort:
    """Contract tests for AgentClockPort."""

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
# Stub: AgentIdGeneratorPort
# =========================================================================


class StubIdGenerator:
    """Minimal stub conforming to AgentIdGeneratorPort."""

    def __init__(self) -> None:
        self._counter = 0

    def generate_agent_id(self) -> str:
        self._counter += 1
        return f"agent-{self._counter}"

    def generate_task_id(self) -> str:
        self._counter += 1
        return f"task-{self._counter}"

    def generate_execution_id(self) -> str:
        self._counter += 1
        return f"exec-{self._counter}"


class TestIdGeneratorPort:
    """Contract tests for AgentIdGeneratorPort."""

    def test_generate_agent_id_returns_string(self) -> None:
        gen = StubIdGenerator()
        result = gen.generate_agent_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_task_id_returns_string(self) -> None:
        gen = StubIdGenerator()
        result = gen.generate_task_id()
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
            gen.generate_agent_id(),
            gen.generate_task_id(),
            gen.generate_execution_id(),
        }
        assert len(ids) == 3

    def test_incrementing_sequence(self) -> None:
        gen = StubIdGenerator()
        a = gen.generate_agent_id()
        b = gen.generate_agent_id()
        assert a != b

    def test_ids_are_different_prefixes(self) -> None:
        gen = StubIdGenerator()
        aid = gen.generate_agent_id()
        tid = gen.generate_task_id()
        eid = gen.generate_execution_id()
        assert aid.startswith("agent-")
        assert tid.startswith("task-")
        assert eid.startswith("exec-")
        assert aid != tid != eid


# =========================================================================
# Outbox Event Union Conformance
# =========================================================================


class TestAgentOutboxEventUnion:
    """Verify that all domain events satisfy the outbox event union."""

    def test_agent_created_is_event(self) -> None:
        event: AgentOutboxEvent = AgentCreated(
            agent_id=AgentId(), agent_type="research", name="n",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_agent_activated_is_event(self) -> None:
        event: AgentOutboxEvent = AgentActivated(
            agent_id=AgentId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_agent_paused_is_event(self) -> None:
        event: AgentOutboxEvent = AgentPaused(
            agent_id=AgentId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_agent_disabled_is_event(self) -> None:
        event: AgentOutboxEvent = AgentDisabled(
            agent_id=AgentId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_agent_task_created_is_event(self) -> None:
        event: AgentOutboxEvent = AgentTaskCreated(
            task_id=AgentTaskId(), agent_id=AgentId(), goal="g",
            instruction="i", occurred_at=_NOW,
        )
        assert event is not None

    def test_agent_task_started_is_event(self) -> None:
        event: AgentOutboxEvent = AgentTaskStarted(
            task_id=AgentTaskId(), agent_id=AgentId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_agent_task_completed_is_event(self) -> None:
        event: AgentOutboxEvent = AgentTaskCompleted(
            task_id=AgentTaskId(), agent_id=AgentId(), result="ok",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_agent_task_failed_is_event(self) -> None:
        event: AgentOutboxEvent = AgentTaskFailed(
            task_id=AgentTaskId(), agent_id=AgentId(),
            failure_reason="err", occurred_at=_NOW,
        )
        assert event is not None

    def test_agent_task_cancelled_is_event(self) -> None:
        event: AgentOutboxEvent = AgentTaskCancelled(
            task_id=AgentTaskId(), agent_id=AgentId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_agent_execution_started_is_event(self) -> None:
        event: AgentOutboxEvent = AgentExecutionStarted(
            execution_id=AgentExecutionId(), agent_id=AgentId(),
            task_id=AgentTaskId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_agent_execution_completed_is_event(self) -> None:
        event: AgentOutboxEvent = AgentExecutionCompleted(
            execution_id=AgentExecutionId(), agent_id=AgentId(),
            task_id=AgentTaskId(), result="ok", occurred_at=_NOW,
        )
        assert event is not None

    def test_agent_execution_failed_is_event(self) -> None:
        event: AgentOutboxEvent = AgentExecutionFailed(
            execution_id=AgentExecutionId(), agent_id=AgentId(),
            task_id=AgentTaskId(), failure_reason="err",
            occurred_at=_NOW,
        )
        assert event is not None


# =========================================================================
# Protocol Structural Conformance
# =========================================================================


class TestAgentPortProtocolConformance:
    """Verify stub classes structurally conform to their protocols."""

    def test_agent_repository_has_all_methods(self) -> None:
        methods = {"save", "find_by_id", "find_by_status", "find_by_type",
                   "find_all", "count"}
        stub_methods = {
            m for m in dir(StubAgentRepository) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_task_repository_has_all_methods(self) -> None:
        methods = {"save", "find_by_id", "find_by_agent_id", "find_by_status",
                   "find_all", "count"}
        stub_methods = {
            m for m in dir(StubTaskRepository) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_execution_repository_has_all_methods(self) -> None:
        methods = {"save", "find_by_id", "find_by_agent_id", "find_by_task_id",
                   "find_by_status", "find_all", "count"}
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
        methods = {"generate_agent_id", "generate_task_id",
                   "generate_execution_id"}
        stub_methods = {
            m for m in dir(StubIdGenerator) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_port_modules_importable(self) -> None:
        from backend.agent.application.ports import (
            AgentClockPort,
            AgentExecutionRepositoryPort,
            AgentIdGeneratorPort,
            AgentOutboxEvent,
            AgentOutboxPort,
            AgentRepositoryPort,
            AgentTaskRepositoryPort,
        )
        assert AgentClockPort is not None
        assert AgentExecutionRepositoryPort is not None
        assert AgentIdGeneratorPort is not None
        assert AgentOutboxEvent is not None
        assert AgentOutboxPort is not None
        assert AgentRepositoryPort is not None
        assert AgentTaskRepositoryPort is not None

    def test_protocols_are_abstract(self) -> None:
        with pytest.raises(TypeError):
            AgentRepositoryPort()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            AgentTaskRepositoryPort()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            AgentExecutionRepositoryPort()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            AgentOutboxPort()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            AgentClockPort()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            AgentIdGeneratorPort()  # type: ignore[abstract]
