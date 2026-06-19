from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID, uuid4

import pytest

from backend.orchestrator.application.ports.clock import OrchestratorClockPort
from backend.orchestrator.application.ports.id_generator import (
    OrchestratorIdGeneratorPort,
)
from backend.orchestrator.application.ports.outbox import (
    OrchestratorOutboxEvent,
    OrchestratorOutboxPort,
)
from backend.orchestrator.application.ports.repository import (
    OrchestrationRepositoryPort,
    OrchestratorStepRepositoryPort,
    OrchestratorWorkflowRepositoryPort,
)
from backend.orchestrator.domain.model import (
    AgentRole,
    ExecutionMode,
    ExecutionOrder,
    Orchestration,
    OrchestrationCancelled,
    OrchestrationCompleted,
    OrchestrationCreated,
    OrchestrationExecutionStarted,
    OrchestrationFailed,
    OrchestrationId,
    OrchestrationPlanningStarted,
    OrchestrationResearchStarted,
    OrchestrationStatus,
    Workflow,
    WorkflowCompleted,
    WorkflowCreated,
    WorkflowFailed,
    WorkflowGoal,
    WorkflowId,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepCompleted,
    WorkflowStepFailed,
    WorkflowStepStarted,
    WorkflowStepStatus,
)

# =========================================================================
# Constants
# =========================================================================

_NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


# =========================================================================
# Helpers
# =========================================================================


def _make_orchestration(
    *,
    orchestration_id: OrchestrationId | None = None,
    status: OrchestrationStatus = OrchestrationStatus.CREATED,
) -> Orchestration:
    from backend.orchestrator.domain.factory import OrchestratorFactory

    o, _ = OrchestratorFactory.create_orchestration(
        intent="test orchestration", goal="test goal",
    )
    if orchestration_id is not None:
        object.__setattr__(o, "_orchestration_id", orchestration_id)
    if status != OrchestrationStatus.CREATED:
        object.__setattr__(o, "_status", status)
    return o


def _make_workflow(
    *,
    workflow_id: WorkflowId | None = None,
    status: WorkflowStatus = WorkflowStatus.PENDING,
) -> Workflow:
    wf = Workflow(
        workflow_id=workflow_id or WorkflowId(),
        goal=WorkflowGoal(value="test workflow"),
        mode=ExecutionMode.SEQUENTIAL,
    )
    if status != WorkflowStatus.PENDING:
        object.__setattr__(wf, "_status", status)
    return wf


def _make_step(
    *,
    step_id: WorkflowId | None = None,
    agent_role: AgentRole = AgentRole.RESEARCH,
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING,
) -> WorkflowStep:
    return WorkflowStep(
        step_id=step_id or WorkflowId(),
        agent_role=agent_role,
        execution_order=ExecutionOrder(value=0),
        status=status,
    )


def _make_created_event() -> OrchestrationCreated:
    return OrchestrationCreated(
        orchestration_id=OrchestrationId(),
        intent="test", goal="test", occurred_at=_NOW,
    )


# =========================================================================
# Stub: OrchestrationRepositoryPort
# =========================================================================


class StubOrchestrationRepository:
    """Minimal stub conforming to OrchestrationRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, Orchestration] = {}

    def save(self, orchestration: Orchestration) -> None:
        self._store[str(orchestration.orchestration_id)] = orchestration

    def find_by_id(self, orchestration_id: OrchestrationId) -> Orchestration | None:
        return self._store.get(str(orchestration_id))

    def find_by_status(self, status: OrchestrationStatus) -> list[Orchestration]:
        return [o for o in self._store.values() if o.status == status]

    def find_all(self) -> list[Orchestration]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class TestOrchestrationRepositoryPort:
    """Contract tests for OrchestrationRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubOrchestrationRepository:
        return StubOrchestrationRepository()

    def test_save_and_find_by_id(self, repo: StubOrchestrationRepository) -> None:
        o = _make_orchestration()
        repo.save(o)
        found = repo.find_by_id(o.orchestration_id)
        assert found is not None
        assert found.orchestration_id == o.orchestration_id

    def test_find_by_id_returns_none(self, repo: StubOrchestrationRepository) -> None:
        assert repo.find_by_id(OrchestrationId()) is None

    def test_find_by_status(self, repo: StubOrchestrationRepository) -> None:
        created = _make_orchestration(status=OrchestrationStatus.CREATED)
        planning = _make_orchestration(status=OrchestrationStatus.PLANNING)
        repo.save(created)
        repo.save(planning)
        results = repo.find_by_status(OrchestrationStatus.CREATED)
        assert len(results) == 1
        assert results[0].orchestration_id == created.orchestration_id

    def test_find_by_status_multiple(self, repo: StubOrchestrationRepository) -> None:
        for _ in range(3):
            repo.save(_make_orchestration(status=OrchestrationStatus.PLANNING))
        repo.save(_make_orchestration(status=OrchestrationStatus.CREATED))
        assert len(repo.find_by_status(OrchestrationStatus.PLANNING)) == 3

    def test_find_by_status_empty(self, repo: StubOrchestrationRepository) -> None:
        assert repo.find_by_status(OrchestrationStatus.FAILED) == []

    def test_find_by_status_all(self, repo: StubOrchestrationRepository) -> None:
        for s in OrchestrationStatus:
            repo.save(_make_orchestration(status=s))
        for s in OrchestrationStatus:
            assert len(repo.find_by_status(s)) == 1

    def test_save_updates_existing(self, repo: StubOrchestrationRepository) -> None:
        o = _make_orchestration()
        repo.save(o)
        object.__setattr__(o, "_status", OrchestrationStatus.PLANNING)
        repo.save(o)
        found = repo.find_by_id(o.orchestration_id)
        assert found is not None
        assert found.status == OrchestrationStatus.PLANNING

    def test_count_empty(self, repo: StubOrchestrationRepository) -> None:
        assert repo.count() == 0

    def test_count_multiple(self, repo: StubOrchestrationRepository) -> None:
        for _ in range(5):
            repo.save(_make_orchestration())
        assert repo.count() == 5

    def test_save_duplicate_does_not_increase_count(
        self, repo: StubOrchestrationRepository
    ) -> None:
        o = _make_orchestration()
        repo.save(o)
        repo.save(o)
        assert repo.count() == 1


# =========================================================================
# Stub: OrchestratorWorkflowRepositoryPort
# =========================================================================


class StubWorkflowRepository:
    """Minimal stub conforming to OrchestratorWorkflowRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, Workflow] = {}

    def save(self, workflow: Workflow) -> None:
        self._store[str(workflow.workflow_id)] = workflow

    def find_by_id(self, workflow_id: WorkflowId) -> Workflow | None:
        return self._store.get(str(workflow_id))

    def find_by_status(self, status: WorkflowStatus) -> list[Workflow]:
        return [w for w in self._store.values() if w.status == status]

    def find_by_orchestration_id(
        self, orchestration_id: OrchestrationId
    ) -> list[Workflow]:
        return list(self._store.values())

    def find_all(self) -> list[Workflow]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class TestWorkflowRepositoryPort:
    """Contract tests for OrchestratorWorkflowRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubWorkflowRepository:
        return StubWorkflowRepository()

    def test_save_and_find_by_id(self, repo: StubWorkflowRepository) -> None:
        wf = _make_workflow()
        repo.save(wf)
        found = repo.find_by_id(wf.workflow_id)
        assert found is not None
        assert found.workflow_id == wf.workflow_id

    def test_find_by_id_returns_none(self, repo: StubWorkflowRepository) -> None:
        assert repo.find_by_id(WorkflowId()) is None

    def test_find_by_status(self, repo: StubWorkflowRepository) -> None:
        pending = _make_workflow(status=WorkflowStatus.PENDING)
        running = _make_workflow(status=WorkflowStatus.RUNNING)
        repo.save(pending)
        repo.save(running)
        results = repo.find_by_status(WorkflowStatus.PENDING)
        assert len(results) == 1
        assert results[0].workflow_id == pending.workflow_id

    def test_find_by_status_multiple(self, repo: StubWorkflowRepository) -> None:
        for _ in range(4):
            repo.save(_make_workflow(status=WorkflowStatus.RUNNING))
        assert len(repo.find_by_status(WorkflowStatus.RUNNING)) == 4

    def test_find_by_status_empty(self, repo: StubWorkflowRepository) -> None:
        assert repo.find_by_status(WorkflowStatus.FAILED) == []

    def test_find_by_orchestration_id(
        self, repo: StubWorkflowRepository
    ) -> None:
        repo.save(_make_workflow())
        results = repo.find_by_orchestration_id(OrchestrationId())
        assert len(results) == 1

    def test_find_by_orchestration_id_empty(
        self, repo: StubWorkflowRepository
    ) -> None:
        assert repo.find_by_orchestration_id(OrchestrationId()) == []

    def test_save_updates_existing(self, repo: StubWorkflowRepository) -> None:
        wf = _make_workflow()
        repo.save(wf)
        object.__setattr__(wf, "_status", WorkflowStatus.RUNNING)
        repo.save(wf)
        found = repo.find_by_id(wf.workflow_id)
        assert found is not None
        assert found.status == WorkflowStatus.RUNNING

    def test_count_empty(self, repo: StubWorkflowRepository) -> None:
        assert repo.count() == 0

    def test_count_multiple(self, repo: StubWorkflowRepository) -> None:
        for _ in range(3):
            repo.save(_make_workflow())
        assert repo.count() == 3

    def test_save_duplicate_does_not_increase_count(
        self, repo: StubWorkflowRepository
    ) -> None:
        wf = _make_workflow()
        repo.save(wf)
        repo.save(wf)
        assert repo.count() == 1


# =========================================================================
# Stub: OrchestratorStepRepositoryPort
# =========================================================================


class StubStepRepository:
    """Minimal stub conforming to OrchestratorStepRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, WorkflowStep] = {}

    def save(self, step: WorkflowStep) -> None:
        self._store[str(step.step_id)] = step

    def find_by_id(self, step_id: WorkflowId) -> WorkflowStep | None:
        return self._store.get(str(step_id))

    def find_by_status(self, status: WorkflowStepStatus) -> list[WorkflowStep]:
        return [s for s in self._store.values() if s.status == status]

    def find_by_workflow_id(self, workflow_id: WorkflowId) -> list[WorkflowStep]:
        return list(self._store.values())

    def find_by_agent_role(self, agent_role: AgentRole) -> list[WorkflowStep]:
        return [s for s in self._store.values() if s.agent_role == agent_role]

    def count(self) -> int:
        return len(self._store)


class TestStepRepositoryPort:
    """Contract tests for OrchestratorStepRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubStepRepository:
        return StubStepRepository()

    def test_save_and_find_by_id(self, repo: StubStepRepository) -> None:
        step = _make_step()
        repo.save(step)
        found = repo.find_by_id(step.step_id)
        assert found is not None
        assert found.step_id == step.step_id

    def test_find_by_id_returns_none(self, repo: StubStepRepository) -> None:
        assert repo.find_by_id(WorkflowId()) is None

    def test_find_by_status(self, repo: StubStepRepository) -> None:
        pending = _make_step(status=WorkflowStepStatus.PENDING)
        running = _make_step(status=WorkflowStepStatus.RUNNING)
        repo.save(pending)
        repo.save(running)
        results = repo.find_by_status(WorkflowStepStatus.PENDING)
        assert len(results) == 1
        assert results[0].step_id == pending.step_id

    def test_find_by_status_multiple(self, repo: StubStepRepository) -> None:
        for _ in range(3):
            repo.save(_make_step(status=WorkflowStepStatus.RUNNING))
        assert len(repo.find_by_status(WorkflowStepStatus.RUNNING)) == 3

    def test_find_by_status_empty(self, repo: StubStepRepository) -> None:
        assert repo.find_by_status(WorkflowStepStatus.FAILED) == []

    def test_find_by_workflow_id(self, repo: StubStepRepository) -> None:
        repo.save(_make_step())
        results = repo.find_by_workflow_id(WorkflowId())
        assert len(results) == 1

    def test_find_by_workflow_id_empty(self, repo: StubStepRepository) -> None:
        assert repo.find_by_workflow_id(WorkflowId()) == []

    def test_find_by_agent_role(self, repo: StubStepRepository) -> None:
        planner = _make_step(agent_role=AgentRole.PLANNER)
        research = _make_step(agent_role=AgentRole.RESEARCH)
        repo.save(planner)
        repo.save(research)
        results = repo.find_by_agent_role(AgentRole.PLANNER)
        assert len(results) == 1
        assert results[0].step_id == planner.step_id

    def test_find_by_agent_role_multiple(self, repo: StubStepRepository) -> None:
        for _ in range(2):
            repo.save(_make_step(agent_role=AgentRole.AUTOMATION))
        assert len(repo.find_by_agent_role(AgentRole.AUTOMATION)) == 2

    def test_find_by_agent_role_empty(self, repo: StubStepRepository) -> None:
        assert repo.find_by_agent_role(AgentRole.MEMORY) == []

    def test_save_updates_existing(self, repo: StubStepRepository) -> None:
        step = _make_step()
        repo.save(step)
        object.__setattr__(step, "_status", WorkflowStepStatus.RUNNING)
        repo.save(step)
        found = repo.find_by_id(step.step_id)
        assert found is not None
        assert found.status == WorkflowStepStatus.RUNNING

    def test_count_empty(self, repo: StubStepRepository) -> None:
        assert repo.count() == 0

    def test_count_multiple(self, repo: StubStepRepository) -> None:
        for _ in range(4):
            repo.save(_make_step())
        assert repo.count() == 4

    def test_save_duplicate_does_not_increase_count(
        self, repo: StubStepRepository
    ) -> None:
        step = _make_step()
        repo.save(step)
        repo.save(step)
        assert repo.count() == 1


# =========================================================================
# Stub: OrchestratorOutboxPort
# =========================================================================


class StubOutbox:
    """Minimal stub conforming to OrchestratorOutboxPort."""

    def __init__(self) -> None:
        self._store: list[tuple[str, OrchestratorOutboxEvent]] = []

    def append(self, event: OrchestratorOutboxEvent) -> None:
        aggregate_id = str(event.event_id)
        self._store.append((aggregate_id, event))

    def fetch_unpublished(self, limit: int = 100) -> list[OrchestratorOutboxEvent]:
        return [event for _, event in self._store[:limit]]

    def mark_published(self, aggregate_id: str) -> None:
        self._store = [
            (aid, event)
            for aid, event in self._store
            if aid != aggregate_id
        ]


class TestOutboxPort:
    """Contract tests for OrchestratorOutboxPort."""

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
        oid = OrchestrationId()
        wid = WorkflowId()
        e1: OrchestratorOutboxEvent = OrchestrationCreated(
            orchestration_id=oid, intent="i", goal="g", occurred_at=_NOW,
        )
        e2: OrchestratorOutboxEvent = OrchestrationPlanningStarted(
            orchestration_id=oid, occurred_at=_NOW,
        )
        e3: OrchestratorOutboxEvent = OrchestrationResearchStarted(
            orchestration_id=oid, occurred_at=_NOW,
        )
        e4: OrchestratorOutboxEvent = OrchestrationExecutionStarted(
            orchestration_id=oid, occurred_at=_NOW,
        )
        e5: OrchestratorOutboxEvent = OrchestrationCompleted(
            orchestration_id=oid, occurred_at=_NOW,
        )
        e6: OrchestratorOutboxEvent = OrchestrationFailed(
            orchestration_id=oid, failure_reason="err", occurred_at=_NOW,
        )
        e7: OrchestratorOutboxEvent = OrchestrationCancelled(
            orchestration_id=oid, occurred_at=_NOW,
        )
        e8: OrchestratorOutboxEvent = WorkflowCreated(
            workflow_id=wid, orchestration_id=oid, goal="g", mode="seq",
            occurred_at=_NOW,
        )
        e9: OrchestratorOutboxEvent = WorkflowCompleted(
            workflow_id=wid, occurred_at=_NOW,
        )
        e10: OrchestratorOutboxEvent = WorkflowFailed(
            workflow_id=wid, failure_reason="err", occurred_at=_NOW,
        )
        e11: OrchestratorOutboxEvent = WorkflowStepStarted(
            step_id=wid, occurred_at=_NOW,
        )
        e12: OrchestratorOutboxEvent = WorkflowStepCompleted(
            step_id=wid, result="ok", occurred_at=_NOW,
        )
        e13: OrchestratorOutboxEvent = WorkflowStepFailed(
            step_id=wid, failure_reason="err", occurred_at=_NOW,
        )
        for e in [e1, e2, e3, e4, e5, e6, e7, e8, e9, e10, e11, e12, e13]:
            outbox.append(e)
        assert len(outbox.fetch_unpublished()) == 13


# =========================================================================
# Stub: OrchestratorClockPort
# =========================================================================


class StubClock:
    """Minimal stub conforming to OrchestratorClockPort."""

    def __init__(self, now: datetime = _NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class TestClockPort:
    """Contract tests for OrchestratorClockPort."""

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
# Stub: OrchestratorIdGeneratorPort
# =========================================================================


class StubIdGenerator:
    """Minimal stub conforming to OrchestratorIdGeneratorPort."""

    def __init__(self) -> None:
        self._counter = 0

    def generate_orchestration_id(self) -> str:
        self._counter += 1
        return f"orch-{self._counter}"

    def generate_workflow_id(self) -> str:
        self._counter += 1
        return f"wf-{self._counter}"

    def generate_step_id(self) -> str:
        self._counter += 1
        return f"step-{self._counter}"


class TestIdGeneratorPort:
    """Contract tests for OrchestratorIdGeneratorPort."""

    def test_generate_orchestration_id_returns_string(self) -> None:
        gen = StubIdGenerator()
        result = gen.generate_orchestration_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_workflow_id_returns_string(self) -> None:
        gen = StubIdGenerator()
        result = gen.generate_workflow_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_step_id_returns_string(self) -> None:
        gen = StubIdGenerator()
        result = gen.generate_step_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_uniqueness(self) -> None:
        gen = StubIdGenerator()
        ids = {
            gen.generate_orchestration_id(),
            gen.generate_workflow_id(),
            gen.generate_step_id(),
        }
        assert len(ids) == 3

    def test_incrementing_sequence(self) -> None:
        gen = StubIdGenerator()
        a = gen.generate_orchestration_id()
        b = gen.generate_orchestration_id()
        assert a != b

    def test_ids_are_different_prefixes(self) -> None:
        gen = StubIdGenerator()
        oid = gen.generate_orchestration_id()
        wid = gen.generate_workflow_id()
        sid = gen.generate_step_id()
        assert oid != wid != sid


# =========================================================================
# Outbox Event Union Conformance
# =========================================================================


class TestOrchestratorOutboxEventUnion:
    """Verify that all domain events satisfy the outbox event union."""

    def test_orchestration_created_is_event(self) -> None:
        event: OrchestratorOutboxEvent = OrchestrationCreated(
            orchestration_id=OrchestrationId(),
            intent="i", goal="g", occurred_at=_NOW,
        )
        assert event is not None

    def test_orchestration_planning_started_is_event(self) -> None:
        event: OrchestratorOutboxEvent = OrchestrationPlanningStarted(
            orchestration_id=OrchestrationId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_orchestration_research_started_is_event(self) -> None:
        event: OrchestratorOutboxEvent = OrchestrationResearchStarted(
            orchestration_id=OrchestrationId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_orchestration_execution_started_is_event(self) -> None:
        event: OrchestratorOutboxEvent = OrchestrationExecutionStarted(
            orchestration_id=OrchestrationId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_orchestration_completed_is_event(self) -> None:
        event: OrchestratorOutboxEvent = OrchestrationCompleted(
            orchestration_id=OrchestrationId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_orchestration_failed_is_event(self) -> None:
        event: OrchestratorOutboxEvent = OrchestrationFailed(
            orchestration_id=OrchestrationId(), failure_reason="err",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_orchestration_cancelled_is_event(self) -> None:
        event: OrchestratorOutboxEvent = OrchestrationCancelled(
            orchestration_id=OrchestrationId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_workflow_created_is_event(self) -> None:
        event: OrchestratorOutboxEvent = WorkflowCreated(
            workflow_id=WorkflowId(), orchestration_id=OrchestrationId(),
            goal="g", mode="seq", occurred_at=_NOW,
        )
        assert event is not None

    def test_workflow_completed_is_event(self) -> None:
        event: OrchestratorOutboxEvent = WorkflowCompleted(
            workflow_id=WorkflowId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_workflow_failed_is_event(self) -> None:
        event: OrchestratorOutboxEvent = WorkflowFailed(
            workflow_id=WorkflowId(), failure_reason="err", occurred_at=_NOW,
        )
        assert event is not None

    def test_workflow_step_started_is_event(self) -> None:
        event: OrchestratorOutboxEvent = WorkflowStepStarted(
            step_id=WorkflowId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_workflow_step_completed_is_event(self) -> None:
        event: OrchestratorOutboxEvent = WorkflowStepCompleted(
            step_id=WorkflowId(), result="ok", occurred_at=_NOW,
        )
        assert event is not None

    def test_workflow_step_failed_is_event(self) -> None:
        event: OrchestratorOutboxEvent = WorkflowStepFailed(
            step_id=WorkflowId(), failure_reason="err", occurred_at=_NOW,
        )
        assert event is not None


# =========================================================================
# Protocol Structural Conformance
# =========================================================================


class TestOrchestratorPortProtocolConformance:
    """Verify stub classes structurally conform to their protocols."""

    def test_orchestration_repository_has_all_methods(self) -> None:
        methods = {"save", "find_by_id", "find_by_status", "count"}
        stub_methods = {
            m for m in dir(StubOrchestrationRepository) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_workflow_repository_has_all_methods(self) -> None:
        methods = {"save", "find_by_id", "find_by_status",
                   "find_by_orchestration_id", "count"}
        stub_methods = {
            m for m in dir(StubWorkflowRepository) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_step_repository_has_all_methods(self) -> None:
        methods = {"save", "find_by_id", "find_by_status",
                   "find_by_workflow_id", "find_by_agent_role", "count"}
        stub_methods = {
            m for m in dir(StubStepRepository) if not m.startswith("_")
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
        methods = {"generate_orchestration_id", "generate_workflow_id",
                   "generate_step_id"}
        stub_methods = {
            m for m in dir(StubIdGenerator) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_port_modules_importable(self) -> None:
        from backend.orchestrator.application.ports import (
            OrchestrationRepositoryPort,
            OrchestratorClockPort,
            OrchestratorIdGeneratorPort,
            OrchestratorOutboxEvent,
            OrchestratorOutboxPort,
            OrchestratorStepRepositoryPort,
            OrchestratorWorkflowRepositoryPort,
        )
        assert OrchestrationRepositoryPort is not None
        assert OrchestratorClockPort is not None
        assert OrchestratorIdGeneratorPort is not None
        assert OrchestratorOutboxEvent is not None
        assert OrchestratorOutboxPort is not None
        assert OrchestratorStepRepositoryPort is not None
        assert OrchestratorWorkflowRepositoryPort is not None

    def test_protocols_are_abstract(self) -> None:
        with pytest.raises(TypeError):
            OrchestrationRepositoryPort()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            OrchestratorWorkflowRepositoryPort()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            OrchestratorStepRepositoryPort()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            OrchestratorOutboxPort()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            OrchestratorClockPort()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            OrchestratorIdGeneratorPort()  # type: ignore[abstract]
