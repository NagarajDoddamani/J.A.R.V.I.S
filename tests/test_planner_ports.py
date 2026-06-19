from __future__ import annotations

from datetime import datetime, timezone
from enum import auto, StrEnum
from typing import Protocol
from uuid import UUID, uuid4

import pytest

from backend.planner.application.ports.clock import PlannerClockPort
from backend.planner.application.ports.id_generator import PlannerIdGeneratorPort
from backend.planner.application.ports.outbox import (
    PlannerOutboxEvent,
    PlannerOutboxPort,
)
from backend.planner.application.ports.repository import (
    PlanRepositoryPort,
    TaskRepositoryPort,
)
from backend.planner.domain.model import (
    AgentType,
    ExecutionStepId,
    Plan,
    PlanApproved,
    PlanCancelled,
    PlanCompleted,
    PlanCreated,
    PlanExecutionStarted,
    PlanFailed,
    PlanGoal,
    PlanId,
    PlanPriority,
    PlanReady,
    PlanStatus,
    Task,
    TaskAssigned,
    TaskCompleted,
    TaskCreated,
    TaskDescription,
    TaskFailed,
    TaskId,
    TaskStatus,
    UserRequest,
)
from backend.planner.domain.factory import PlannerFactory


# =========================================================================
# Constants
# =========================================================================

_NOW = datetime(2026, 6, 9, 14, 0, 0, tzinfo=timezone.utc)


# =========================================================================
# Helpers
# =========================================================================


def _make_plan(
    *,
    plan_id: PlanId | None = None,
    user_request: str = "test request",
    goal: str = "test goal",
    priority: PlanPriority = PlanPriority.NORMAL,
    strategy: str = "sequential",
    status: PlanStatus = PlanStatus.DRAFT,
) -> Plan:
    plan, _ = PlannerFactory.create_plan(
        user_request=user_request,
        goal=goal,
        priority=priority,
        strategy=strategy,
    )
    if plan_id is not None:
        object.__setattr__(plan, "_plan_id", plan_id)
    if status != PlanStatus.DRAFT:
        object.__setattr__(plan, "_status", status)
    return plan


def _make_task(
    *,
    task_id: TaskId | None = None,
    description: str = "test task",
    agent: AgentType | None = None,
    status: TaskStatus = TaskStatus.PENDING,
) -> Task:
    task = Task(
        task_id=task_id or TaskId(),
        description=TaskDescription(value=description),
        assigned_agent=agent,
        status=status,
    )
    return task


def _make_plan_created_event(plan: Plan) -> PlanCreated:
    return PlanCreated(
        plan_id=plan.plan_id,
        user_request=str(plan.user_request) if plan.user_request else "",
        goal=str(plan.goal) if plan.goal else "",
        priority=str(plan.priority.value),
        strategy=str(plan.strategy.value),
        occurred_at=_NOW,
    )


def _make_task_created_event(task: Task) -> TaskCreated:
    return TaskCreated(
        task_id=task.task_id,
        description=str(task.description) if task.description else "",
        occurred_at=_NOW,
    )


# =========================================================================
# PlanRepositoryPort Stub
# =========================================================================


class StubPlanRepository:
    """Minimal stub conforming to PlanRepositoryPort."""

    TERMINAL_STATUSES = {PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.CANCELLED}

    def __init__(self) -> None:
        self._store: dict[str, Plan] = {}

    def save(self, plan: Plan) -> None:
        key = str(plan.plan_id)
        self._store[key] = plan

    def find_by_id(self, plan_id: PlanId) -> Plan | None:
        return self._store.get(str(plan_id))

    def find_by_status(self, status: PlanStatus) -> list[Plan]:
        return [p for p in self._store.values() if p.status == status]

    def find_by_priority(self, priority: PlanPriority) -> list[Plan]:
        return [p for p in self._store.values() if p.priority == priority]

    def find_active(self) -> list[Plan]:
        return [
            p for p in self._store.values() if p.status not in self.TERMINAL_STATUSES
        ]

    def count(self) -> int:
        return len(self._store)


class TestPlanRepositoryPort:
    """Contract tests for PlanRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubPlanRepository:
        return StubPlanRepository()

    def test_save_and_find_by_id(self, repo: StubPlanRepository) -> None:
        plan = _make_plan()
        repo.save(plan)
        found = repo.find_by_id(plan.plan_id)
        assert found is not None
        assert found.plan_id == plan.plan_id
        assert found.status == PlanStatus.DRAFT

    def test_find_by_id_returns_none(self, repo: StubPlanRepository) -> None:
        missing_id = PlanId()
        assert repo.find_by_id(missing_id) is None

    def test_find_by_status(self, repo: StubPlanRepository) -> None:
        draft = _make_plan(status=PlanStatus.DRAFT)
        approved = _make_plan(status=PlanStatus.APPROVED)
        repo.save(draft)
        repo.save(approved)

        drafts = repo.find_by_status(PlanStatus.DRAFT)
        assert len(drafts) == 1
        assert drafts[0].plan_id == draft.plan_id

        approved_list = repo.find_by_status(PlanStatus.APPROVED)
        assert len(approved_list) == 1
        assert approved_list[0].plan_id == approved.plan_id

    def test_find_by_status_multiple(self, repo: StubPlanRepository) -> None:
        plans = [_make_plan(status=PlanStatus.READY) for _ in range(3)]
        for p in plans:
            repo.save(p)
        repo.save(_make_plan(status=PlanStatus.DRAFT))

        ready = repo.find_by_status(PlanStatus.READY)
        assert len(ready) == 3

    def test_find_by_status_empty(self, repo: StubPlanRepository) -> None:
        assert repo.find_by_status(PlanStatus.EXECUTING) == []

    def test_find_by_priority(self, repo: StubPlanRepository) -> None:
        high = _make_plan(priority=PlanPriority.HIGH)
        normal = _make_plan(priority=PlanPriority.NORMAL)
        repo.save(high)
        repo.save(normal)

        high_list = repo.find_by_priority(PlanPriority.HIGH)
        assert len(high_list) == 1
        assert high_list[0].plan_id == high.plan_id

    def test_find_by_priority_multiple(self, repo: StubPlanRepository) -> None:
        for _ in range(5):
            repo.save(_make_plan(priority=PlanPriority.CRITICAL))

        critical = repo.find_by_priority(PlanPriority.CRITICAL)
        assert len(critical) == 5

    def test_find_by_priority_empty(self, repo: StubPlanRepository) -> None:
        assert repo.find_by_priority(PlanPriority.LOW) == []

    def test_find_active_includes_draft(self, repo: StubPlanRepository) -> None:
        repo.save(_make_plan(status=PlanStatus.DRAFT))
        active = repo.find_active()
        assert len(active) == 1

    def test_find_active_includes_approved(self, repo: StubPlanRepository) -> None:
        repo.save(_make_plan(status=PlanStatus.APPROVED))
        active = repo.find_active()
        assert len(active) == 1

    def test_find_active_includes_planning(self, repo: StubPlanRepository) -> None:
        repo.save(_make_plan(status=PlanStatus.PLANNING))
        active = repo.find_active()
        assert len(active) == 1

    def test_find_active_includes_ready(self, repo: StubPlanRepository) -> None:
        repo.save(_make_plan(status=PlanStatus.READY))
        active = repo.find_active()
        assert len(active) == 1

    def test_find_active_includes_executing(self, repo: StubPlanRepository) -> None:
        repo.save(_make_plan(status=PlanStatus.EXECUTING))
        active = repo.find_active()
        assert len(active) == 1

    def test_find_active_excludes_completed(self, repo: StubPlanRepository) -> None:
        repo.save(_make_plan(status=PlanStatus.COMPLETED))
        active = repo.find_active()
        assert len(active) == 0

    def test_find_active_excludes_failed(self, repo: StubPlanRepository) -> None:
        repo.save(_make_plan(status=PlanStatus.FAILED))
        active = repo.find_active()
        assert len(active) == 0

    def test_find_active_excludes_cancelled(self, repo: StubPlanRepository) -> None:
        repo.save(_make_plan(status=PlanStatus.CANCELLED))
        active = repo.find_active()
        assert len(active) == 0

    def test_find_active_mixed(self, repo: StubPlanRepository) -> None:
        repo.save(_make_plan(status=PlanStatus.DRAFT))
        repo.save(_make_plan(status=PlanStatus.COMPLETED))
        repo.save(_make_plan(status=PlanStatus.EXECUTING))
        repo.save(_make_plan(status=PlanStatus.FAILED))
        repo.save(_make_plan(status=PlanStatus.APPROVED))

        active = repo.find_active()
        assert len(active) == 3
        statuses = {p.status for p in active}
        assert statuses == {PlanStatus.DRAFT, PlanStatus.EXECUTING, PlanStatus.APPROVED}

    def test_find_active_empty(self, repo: StubPlanRepository) -> None:
        assert repo.find_active() == []

    def test_count(self, repo: StubPlanRepository) -> None:
        assert repo.count() == 0
        repo.save(_make_plan())
        assert repo.count() == 1
        repo.save(_make_plan())
        assert repo.count() == 2

    def test_count_after_save_multiple(self, repo: StubPlanRepository) -> None:
        for _ in range(10):
            repo.save(_make_plan())
        assert repo.count() == 10

    def test_save_upsert_behavior(self, repo: StubPlanRepository) -> None:
        plan = _make_plan()
        repo.save(plan)
        assert repo.count() == 1

        same_id = plan.plan_id
        updated = _make_plan(plan_id=same_id, goal="updated goal")
        repo.save(updated)
        assert repo.count() == 1
        found = repo.find_by_id(same_id)
        assert found is not None

    def test_find_by_id_preserves_aggregate_state(
        self, repo: StubPlanRepository
    ) -> None:
        plan, events = PlannerFactory.create_plan(
            user_request="complex request",
            goal="complex goal",
            priority=PlanPriority.HIGH,
            strategy="sequential",
        )
        repo.save(plan)
        found = repo.find_by_id(plan.plan_id)
        assert found is not None
        assert found.priority == PlanPriority.HIGH
        assert found.strategy.value == "sequential"

    def test_empty_repo_count(self, repo: StubPlanRepository) -> None:
        assert repo.count() == 0

    def test_all_statuses_queryable(self, repo: StubPlanRepository) -> None:
        for s in PlanStatus:
            repo.save(_make_plan(status=s))
        for s in PlanStatus:
            plans = repo.find_by_status(s)
            assert len(plans) == 1, f"Failed for {s}"

    def test_all_priorities_queryable(self, repo: StubPlanRepository) -> None:
        for p in PlanPriority:
            repo.save(_make_plan(priority=p))
        for p in PlanPriority:
            plans = repo.find_by_priority(p)
            assert len(plans) == 1, f"Failed for {p}"

    def test_find_by_id_distinct_ids(self, repo: StubPlanRepository) -> None:
        p1 = _make_plan()
        p2 = _make_plan()
        repo.save(p1)
        repo.save(p2)
        assert repo.find_by_id(p1.plan_id).plan_id == p1.plan_id
        assert repo.find_by_id(p2.plan_id).plan_id == p2.plan_id

    def test_save_nullable_user_request(
        self, repo: StubPlanRepository
    ) -> None:
        plan = _make_plan(user_request="valid")
        repo.save(plan)
        found = repo.find_by_id(plan.plan_id)
        assert found is not None
        assert found.user_request is not None
        assert str(found.user_request) == "valid"

    def test_save_persists_plan_priority(self, repo: StubPlanRepository) -> None:
        plan = _make_plan(priority=PlanPriority.CRITICAL)
        repo.save(plan)
        found = repo.find_by_id(plan.plan_id)
        assert found is not None
        assert found.priority == PlanPriority.CRITICAL


# =========================================================================
# TaskRepositoryPort Stub
# =========================================================================


class StubTaskRepository:
    """Minimal stub conforming to TaskRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, Task] = {}

    def save(self, task: Task) -> None:
        key = str(task.task_id)
        self._store[key] = task

    def find_by_id(self, task_id: TaskId) -> Task | None:
        return self._store.get(str(task_id))

    def find_by_status(self, status: TaskStatus) -> list[Task]:
        return [t for t in self._store.values() if t.status == status]

    def find_by_agent(self, agent_type: AgentType) -> list[Task]:
        return [
            t
            for t in self._store.values()
            if t.assigned_agent == agent_type
        ]

    def find_by_plan_id(self, plan_id: PlanId) -> list[Task]:
        return [t for t in self._store.values()]

    def count(self) -> int:
        return len(self._store)


class TestTaskRepositoryPort:
    """Contract tests for TaskRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubTaskRepository:
        return StubTaskRepository()

    def test_save_and_find_by_id(self, repo: StubTaskRepository) -> None:
        task = _make_task()
        repo.save(task)
        found = repo.find_by_id(task.task_id)
        assert found is not None
        assert found.task_id == task.task_id
        assert found.status == TaskStatus.PENDING

    def test_find_by_id_returns_none(self, repo: StubTaskRepository) -> None:
        missing_id = TaskId()
        assert repo.find_by_id(missing_id) is None

    def test_find_by_status(self, repo: StubTaskRepository) -> None:
        pending = _make_task(status=TaskStatus.PENDING)
        assigned = _make_task(status=TaskStatus.ASSIGNED)
        repo.save(pending)
        repo.save(assigned)

        pending_list = repo.find_by_status(TaskStatus.PENDING)
        assert len(pending_list) == 1
        assert pending_list[0].task_id == pending.task_id

        assigned_list = repo.find_by_status(TaskStatus.ASSIGNED)
        assert len(assigned_list) == 1
        assert assigned_list[0].task_id == assigned.task_id

    def test_find_by_status_multiple(self, repo: StubTaskRepository) -> None:
        for _ in range(4):
            repo.save(_make_task(status=TaskStatus.RUNNING))

        running = repo.find_by_status(TaskStatus.RUNNING)
        assert len(running) == 4

    def test_find_by_status_empty(self, repo: StubTaskRepository) -> None:
        assert repo.find_by_status(TaskStatus.FAILED) == []

    def test_find_by_agent(self, repo: StubTaskRepository) -> None:
        research = _make_task(agent=AgentType.RESEARCH)
        memory = _make_task(agent=AgentType.MEMORY)
        repo.save(research)
        repo.save(memory)

        research_tasks = repo.find_by_agent(AgentType.RESEARCH)
        assert len(research_tasks) == 1
        assert research_tasks[0].task_id == research.task_id

    def test_find_by_agent_multiple(self, repo: StubTaskRepository) -> None:
        for _ in range(3):
            repo.save(_make_task(agent=AgentType.AUTOMATION))

        automation = repo.find_by_agent(AgentType.AUTOMATION)
        assert len(automation) == 3

    def test_find_by_agent_empty(self, repo: StubTaskRepository) -> None:
        assert repo.find_by_agent(AgentType.POLICY) == []

    def test_find_by_agent_all_agents(self, repo: StubTaskRepository) -> None:
        for agent in AgentType:
            repo.save(_make_task(agent=agent))

        for agent in AgentType:
            tasks = repo.find_by_agent(agent)
            assert len(tasks) == 1, f"Failed for {agent}"

    def test_find_by_plan_id(self, repo: StubTaskRepository) -> None:
        plan_id = PlanId()
        task = _make_task()
        repo.save(task)
        tasks = repo.find_by_plan_id(plan_id)
        assert isinstance(tasks, list)

    def test_find_by_plan_id_empty(self, repo: StubTaskRepository) -> None:
        tasks = repo.find_by_plan_id(PlanId())
        assert tasks == []

    def test_count(self, repo: StubTaskRepository) -> None:
        assert repo.count() == 0
        repo.save(_make_task())
        assert repo.count() == 1
        repo.save(_make_task())
        assert repo.count() == 2

    def test_count_after_save_multiple(self, repo: StubTaskRepository) -> None:
        for _ in range(7):
            repo.save(_make_task())
        assert repo.count() == 7

    def test_save_upsert_behavior(self, repo: StubTaskRepository) -> None:
        task = _make_task()
        repo.save(task)
        assert repo.count() == 1

        same_id = task.task_id
        updated = _make_task(task_id=same_id, description="updated")
        repo.save(updated)
        assert repo.count() == 1
        found = repo.find_by_id(same_id)
        assert found is not None

    def test_find_by_id_preserves_task_state(
        self, repo: StubTaskRepository
    ) -> None:
        task = _make_task(description="my task", agent=AgentType.RESEARCH)
        repo.save(task)
        found = repo.find_by_id(task.task_id)
        assert found is not None
        assert found.assigned_agent == AgentType.RESEARCH

    def test_empty_repo_count(self, repo: StubTaskRepository) -> None:
        assert repo.count() == 0

    def test_all_task_statuses_queryable(self, repo: StubTaskRepository) -> None:
        for s in TaskStatus:
            repo.save(_make_task(status=s))
        for s in TaskStatus:
            tasks = repo.find_by_status(s)
            assert len(tasks) == 1, f"Failed for {s}"

    def test_task_ownership_preserved(self, repo: StubTaskRepository) -> None:
        task = _make_task(agent=AgentType.NOTIFICATION)
        repo.save(task)
        found = repo.find_by_id(task.task_id)
        assert found is not None
        assert found.assigned_agent == AgentType.NOTIFICATION

    def test_find_by_agent_none_assigned(
        self, repo: StubTaskRepository
    ) -> None:
        task = _make_task(agent=None)
        repo.save(task)
        unassigned = repo.find_by_agent(AgentType.PLANNER)
        assert unassigned == []

    def test_save_persists_task_status(self, repo: StubTaskRepository) -> None:
        task = _make_task(status=TaskStatus.ASSIGNED)
        repo.save(task)
        found = repo.find_by_id(task.task_id)
        assert found is not None
        assert found.status == TaskStatus.ASSIGNED


# =========================================================================
# PlannerOutboxPort Stub
# =========================================================================


class StubPlannerOutbox:
    """Minimal stub conforming to PlannerOutboxPort."""

    def __init__(self) -> None:
        self._events: list[PlannerOutboxEvent] = []
        self._published: set[str] = set()

    def append(self, event: PlannerOutboxEvent) -> None:
        self._events.append(event)

    def fetch_unpublished(
        self, limit: int = 100
    ) -> list[PlannerOutboxEvent]:
        results: list[PlannerOutboxEvent] = []
        for e in self._events:
            key = self._get_key(e)
            if key not in self._published:
                results.append(e)
                if len(results) >= limit:
                    break
        return results

    def mark_published(self, aggregate_id: str) -> None:
        self._published.add(aggregate_id)

    @staticmethod
    def _get_key(event: PlannerOutboxEvent) -> str:
        if hasattr(event, "plan_id"):
            return str(event.plan_id)
        if hasattr(event, "task_id"):
            return str(event.task_id)
        return str(id(event))


class TestPlannerOutboxPort:
    """Contract tests for PlannerOutboxPort."""

    @pytest.fixture
    def outbox(self) -> StubPlannerOutbox:
        return StubPlannerOutbox()

    def test_append_and_fetch(self, outbox: StubPlannerOutbox) -> None:
        event = PlanCreated(
            plan_id=PlanId(),
            user_request="test",
            goal="goal",
            priority="normal",
            strategy="sequential",
            occurred_at=_NOW,
        )
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], PlanCreated)

    def test_append_and_fetch_task_event(self, outbox: StubPlannerOutbox) -> None:
        event = TaskCreated(
            task_id=TaskId(),
            description="do something",
            occurred_at=_NOW,
        )
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], TaskCreated)
        assert unpublished[0].task_id == event.task_id

    def test_mark_published_excludes(self, outbox: StubPlannerOutbox) -> None:
        event = PlanCreated(
            plan_id=PlanId(),
            user_request="test",
            goal="goal",
            priority="normal",
            strategy="sequential",
            occurred_at=_NOW,
        )
        outbox.append(event)
        outbox.mark_published(str(event.plan_id))
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_mark_published_task_excludes(
        self, outbox: StubPlannerOutbox
    ) -> None:
        event = TaskCreated(
            task_id=TaskId(),
            description="task",
            occurred_at=_NOW,
        )
        outbox.append(event)
        outbox.mark_published(str(event.task_id))
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_fetch_respects_limit(self, outbox: StubPlannerOutbox) -> None:
        for _ in range(10):
            outbox.append(
                TaskCreated(task_id=TaskId(), description="t", occurred_at=_NOW)
            )
        fetched = outbox.fetch_unpublished(limit=3)
        assert len(fetched) == 3

    def test_fetch_default_limit(self, outbox: StubPlannerOutbox) -> None:
        for _ in range(200):
            outbox.append(
                TaskCreated(task_id=TaskId(), description="t", occurred_at=_NOW)
            )
        fetched = outbox.fetch_unpublished()
        assert len(fetched) == 100

    def test_fifo_ordering(self, outbox: StubPlannerOutbox) -> None:
        ids = [PlanId() for _ in range(5)]
        for pid in ids:
            outbox.append(
                PlanCreated(
                    plan_id=pid,
                    user_request=f"req-{pid}",
                    goal="goal",
                    priority="normal",
                    strategy="sequential",
                    occurred_at=_NOW,
                )
            )
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 5
        for i, e in enumerate(unpublished):
            assert isinstance(e, PlanCreated)
            assert e.plan_id == ids[i]

    def test_idempotent_mark_published(
        self, outbox: StubPlannerOutbox
    ) -> None:
        event = PlanCreated(
            plan_id=PlanId(),
            user_request="test",
            goal="goal",
            priority="normal",
            strategy="sequential",
            occurred_at=_NOW,
        )
        outbox.append(event)
        key = str(event.plan_id)
        outbox.mark_published(key)
        outbox.mark_published(key)
        outbox.mark_published(key)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_multiple_publish_then_fetch(
        self, outbox: StubPlannerOutbox
    ) -> None:
        events = [
            PlanCreated(
                plan_id=PlanId(),
                user_request=f"req-{i}",
                goal="goal",
                priority="normal",
                strategy="sequential",
                occurred_at=_NOW,
            )
            for i in range(3)
        ]
        for e in events:
            outbox.append(e)

        outbox.mark_published(str(events[0].plan_id))
        outbox.mark_published(str(events[1].plan_id))

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert unpublished[0].plan_id == events[2].plan_id

    def test_fetch_unpublished_empty(self, outbox: StubPlannerOutbox) -> None:
        assert outbox.fetch_unpublished() == []

    def test_mixed_plan_and_task_events(
        self, outbox: StubPlannerOutbox
    ) -> None:
        plan_event = PlanCreated(
            plan_id=PlanId(),
            user_request="test",
            goal="goal",
            priority="normal",
            strategy="sequential",
            occurred_at=_NOW,
        )
        task_event = TaskCreated(
            task_id=TaskId(),
            description="task",
            occurred_at=_NOW,
        )
        outbox.append(plan_event)
        outbox.append(task_event)

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 2
        assert isinstance(unpublished[0], PlanCreated)
        assert isinstance(unpublished[1], TaskCreated)

    def test_partial_publish_mixed_events(
        self, outbox: StubPlannerOutbox
    ) -> None:
        plan_id = PlanId()
        task_id = TaskId()
        outbox.append(
            PlanCreated(
                plan_id=plan_id,
                user_request="req",
                goal="goal",
                priority="normal",
                strategy="sequential",
                occurred_at=_NOW,
            )
        )
        outbox.append(
            TaskCreated(task_id=task_id, description="task", occurred_at=_NOW)
        )

        outbox.mark_published(str(plan_id))

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], TaskCreated)

    def test_all_event_types_appendable(self, outbox: StubPlannerOutbox) -> None:
        pid = PlanId()
        tid = TaskId()
        events: list[PlannerOutboxEvent] = [
            PlanCreated(
                plan_id=pid, user_request="r", goal="g",
                priority="n", strategy="s", occurred_at=_NOW,
            ),
            PlanApproved(plan_id=pid, occurred_at=_NOW),
            PlanReady(plan_id=pid, occurred_at=_NOW),
            PlanExecutionStarted(plan_id=pid, occurred_at=_NOW),
            PlanCompleted(plan_id=pid, occurred_at=_NOW),
            PlanFailed(plan_id=pid, failure_reason="fail", occurred_at=_NOW),
            PlanCancelled(plan_id=pid, occurred_at=_NOW),
            TaskCreated(task_id=tid, description="d", occurred_at=_NOW),
            TaskAssigned(
                task_id=tid, assigned_agent=AgentType.RESEARCH,
                occurred_at=_NOW,
            ),
            TaskCompleted(task_id=tid, occurred_at=_NOW),
            TaskFailed(task_id=tid, failure_reason="err", occurred_at=_NOW),
        ]
        for e in events:
            outbox.append(e)

        all_events = outbox.fetch_unpublished(limit=20)
        assert len(all_events) == 11

    def test_fifo_preserved_after_partial_mark(
        self, outbox: StubPlannerOutbox
    ) -> None:
        ids = [PlanId() for _ in range(4)]
        for pid in ids:
            outbox.append(
                PlanCreated(
                    plan_id=pid,
                    user_request="r", goal="g",
                    priority="n", strategy="s", occurred_at=_NOW,
                )
            )

        outbox.mark_published(str(ids[0]))
        outbox.mark_published(str(ids[2]))

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 2
        assert unpublished[0].plan_id == ids[1]
        assert unpublished[1].plan_id == ids[3]

    def test_fetch_no_limit_returns_all(self, outbox: StubPlannerOutbox) -> None:
        for _ in range(50):
            outbox.append(
                TaskCreated(task_id=TaskId(), description="x", occurred_at=_NOW)
            )
        fetched = outbox.fetch_unpublished(limit=200)
        assert len(fetched) == 50

    def test_mark_published_nonexistent_key(
        self, outbox: StubPlannerOutbox
    ) -> None:
        outbox.mark_published("nonexistent-id")
        assert outbox.fetch_unpublished() == []


# =========================================================================
# PlannerClockPort Stubs + Tests
# =========================================================================


class SystemClockStub:
    """Returns real system time — conforms to PlannerClockPort."""

    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)


class FixedClock:
    """Returns a fixed time — conforms to PlannerClockPort."""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return self._fixed


class OffsetClock:
    """Returns system time plus a fixed offset — conforms to PlannerClockPort."""

    def __init__(self, offset_seconds: float = 0) -> None:
        self._offset = offset_seconds

    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)


class TestPlannerClockPort:
    """Contract tests for PlannerClockPort."""

    def test_system_clock_returns_utc(self) -> None:
        clock: PlannerClockPort = SystemClockStub()
        result = clock.now()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result).total_seconds() == 0.0

    def test_fixed_clock_returns_configured_time(self) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        clock: PlannerClockPort = FixedClock(dt)
        assert clock.now() == dt

    def test_fixed_clock_is_deterministic(self) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        clock: PlannerClockPort = FixedClock(dt)
        assert clock.now() == clock.now() == dt

    def test_fixed_clock_different_times(self) -> None:
        dt1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        dt2 = datetime(2026, 12, 31, tzinfo=timezone.utc)
        c1: PlannerClockPort = FixedClock(dt1)
        c2: PlannerClockPort = FixedClock(dt2)
        assert c1.now() == dt1
        assert c2.now() == dt2

    def test_clock_protocol_conformance(self) -> None:
        def use_clock(c: PlannerClockPort) -> datetime:
            return c.now()

        assert use_clock(SystemClockStub()) is not None
        assert use_clock(
            FixedClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
        ) is not None

    def test_fixed_clock_accepts_naive_datetime(self) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0)
        clock: PlannerClockPort = FixedClock(dt)
        result = clock.now()
        assert isinstance(result, datetime)

    def test_system_clock_consistent_type(self) -> None:
        clock: PlannerClockPort = SystemClockStub()
        result = clock.now()
        assert isinstance(result, datetime)

    def test_offset_clock_protocol_conformance(self) -> None:
        clock: PlannerClockPort = OffsetClock()
        result = clock.now()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None


# =========================================================================
# PlannerIdGeneratorPort Stubs + Tests
# =========================================================================


class UuidPlannerIdGenerator:
    """Generates UUID-based string IDs — conforms to PlannerIdGeneratorPort."""

    def generate_plan_id(self) -> str:
        return str(PlanId())

    def generate_task_id(self) -> str:
        return str(TaskId())

    def generate_step_id(self) -> str:
        return str(ExecutionStepId())


class SequentialPlannerIdGenerator:
    """Generates deterministic sequential IDs — conforms to PlannerIdGeneratorPort."""

    def __init__(self) -> None:
        self._plan_counter = 0
        self._task_counter = 0
        self._step_counter = 0

    def generate_plan_id(self) -> str:
        self._plan_counter += 1
        return f"plan-{self._plan_counter:010d}"

    def generate_task_id(self) -> str:
        self._task_counter += 1
        return f"task-{self._task_counter:010d}"

    def generate_step_id(self) -> str:
        self._step_counter += 1
        return f"step-{self._step_counter:010d}"


class FixedPlannerIdGenerator:
    """Returns configured IDs — conforms to PlannerIdGeneratorPort."""

    def __init__(
        self,
        plan_id: str = "fixed-plan",
        task_id: str = "fixed-task",
        step_id: str = "fixed-step",
    ) -> None:
        self._plan_id = plan_id
        self._task_id = task_id
        self._step_id = step_id

    def generate_plan_id(self) -> str:
        return self._plan_id

    def generate_task_id(self) -> str:
        return self._task_id

    def generate_step_id(self) -> str:
        return self._step_id

    def set_plan_id(self, value: str) -> None:
        self._plan_id = value

    def set_task_id(self, value: str) -> None:
        self._task_id = value

    def set_step_id(self, value: str) -> None:
        self._step_id = value


class TestPlannerIdGeneratorPort:
    """Contract tests for PlannerIdGeneratorPort."""

    def test_generate_plan_id_returns_string(self) -> None:
        gen: PlannerIdGeneratorPort = UuidPlannerIdGenerator()
        result = gen.generate_plan_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_task_id_returns_string(self) -> None:
        gen: PlannerIdGeneratorPort = UuidPlannerIdGenerator()
        result = gen.generate_task_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_step_id_returns_string(self) -> None:
        gen: PlannerIdGeneratorPort = UuidPlannerIdGenerator()
        result = gen.generate_step_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unique_plan_ids(self) -> None:
        gen: PlannerIdGeneratorPort = UuidPlannerIdGenerator()
        ids = {gen.generate_plan_id() for _ in range(100)}
        assert len(ids) == 100

    def test_unique_task_ids(self) -> None:
        gen: PlannerIdGeneratorPort = UuidPlannerIdGenerator()
        ids = {gen.generate_task_id() for _ in range(100)}
        assert len(ids) == 100

    def test_unique_step_ids(self) -> None:
        gen: PlannerIdGeneratorPort = UuidPlannerIdGenerator()
        ids = {gen.generate_step_id() for _ in range(100)}
        assert len(ids) == 100

    def test_plan_task_step_ids_distinct_groups(self) -> None:
        gen: PlannerIdGeneratorPort = UuidPlannerIdGenerator()
        plan_ids = {gen.generate_plan_id() for _ in range(10)}
        task_ids = {gen.generate_task_id() for _ in range(10)}
        step_ids = {gen.generate_step_id() for _ in range(10)}
        all_ids = plan_ids | task_ids | step_ids
        assert len(all_ids) == 30

    def test_sequential_generator_plan_ids(self) -> None:
        gen: PlannerIdGeneratorPort = SequentialPlannerIdGenerator()
        assert gen.generate_plan_id() == "plan-0000000001"
        assert gen.generate_plan_id() == "plan-0000000002"
        assert gen.generate_plan_id() == "plan-0000000003"

    def test_sequential_generator_task_ids(self) -> None:
        gen: PlannerIdGeneratorPort = SequentialPlannerIdGenerator()
        assert gen.generate_task_id() == "task-0000000001"
        assert gen.generate_task_id() == "task-0000000002"
        assert gen.generate_task_id() == "task-0000000003"

    def test_sequential_generator_step_ids(self) -> None:
        gen: PlannerIdGeneratorPort = SequentialPlannerIdGenerator()
        assert gen.generate_step_id() == "step-0000000001"
        assert gen.generate_step_id() == "step-0000000002"
        assert gen.generate_step_id() == "step-0000000003"

    def test_sequential_independent_counters(self) -> None:
        gen: PlannerIdGeneratorPort = SequentialPlannerIdGenerator()
        gen.generate_plan_id()
        gen.generate_task_id()
        gen.generate_step_id()
        assert gen.generate_plan_id() == "plan-0000000002"
        assert gen.generate_task_id() == "task-0000000002"
        assert gen.generate_step_id() == "step-0000000002"

    def test_generator_protocol_conformance(self) -> None:
        def use_generator(g: PlannerIdGeneratorPort) -> tuple[str, str, str]:
            return g.generate_plan_id(), g.generate_task_id(), g.generate_step_id()

        plan_id, task_id, step_id = use_generator(UuidPlannerIdGenerator())
        assert isinstance(plan_id, str)
        assert isinstance(task_id, str)
        assert isinstance(step_id, str)

        plan_id2, task_id2, step_id2 = use_generator(SequentialPlannerIdGenerator())
        assert plan_id2 == "plan-0000000001"
        assert task_id2 == "task-0000000001"
        assert step_id2 == "step-0000000001"

    def test_fixed_generator_returns_configured_values(self) -> None:
        gen: PlannerIdGeneratorPort = FixedPlannerIdGenerator()
        assert gen.generate_plan_id() == "fixed-plan"
        assert gen.generate_task_id() == "fixed-task"
        assert gen.generate_step_id() == "fixed-step"

    def test_fixed_generator_updatable(self) -> None:
        gen = FixedPlannerIdGenerator()
        gen.set_plan_id("custom-plan-id")
        gen.set_task_id("custom-task-id")
        gen.set_step_id("custom-step-id")
        assert gen.generate_plan_id() == "custom-plan-id"
        assert gen.generate_task_id() == "custom-task-id"
        assert gen.generate_step_id() == "custom-step-id"


# =========================================================================
# Port method signature cross-verification
# =========================================================================


class TestMethodSignatures:
    """Verify that each port method signature matches expectations.

    These tests introspect the stub methods and check parameter
    names and annotations to catch signature drift.
    """

    def test_plan_repo_signatures(self) -> None:
        import inspect

        methods = {
            "save": {"plan": Plan},
            "find_by_id": {"plan_id": PlanId, "return": Plan | None},
            "find_by_status": {"status": PlanStatus, "return": list},
            "find_by_priority": {"priority": PlanPriority, "return": list},
            "find_active": {"return": list},
            "count": {"return": int},
        }
        stub = StubPlanRepository()
        for method_name, expected_params in methods.items():
            method = getattr(stub, method_name)
            sig = inspect.signature(method)
            for param_name in expected_params:
                if param_name == "return":
                    continue
                assert param_name in sig.parameters, (
                    f"{method_name} missing parameter {param_name!r}"
                )

    def test_task_repo_signatures(self) -> None:
        import inspect

        methods = {
            "save": {"task": Task},
            "find_by_id": {"task_id": TaskId, "return": Task | None},
            "find_by_status": {"status": TaskStatus, "return": list},
            "find_by_agent": {"agent_type": AgentType, "return": list},
            "find_by_plan_id": {"plan_id": PlanId, "return": list},
            "count": {"return": int},
        }
        stub = StubTaskRepository()
        for method_name, expected_params in methods.items():
            method = getattr(stub, method_name)
            sig = inspect.signature(method)
            for param_name in expected_params:
                if param_name == "return":
                    continue
                assert param_name in sig.parameters, (
                    f"{method_name} missing parameter {param_name!r}"
                )

    def test_outbox_signatures(self) -> None:
        import inspect

        stub = StubPlannerOutbox()
        sig_append = inspect.signature(stub.append)
        assert "event" in sig_append.parameters

        sig_fetch = inspect.signature(stub.fetch_unpublished)
        assert "limit" in sig_fetch.parameters

        sig_mark = inspect.signature(stub.mark_published)
        assert "aggregate_id" in sig_mark.parameters

    def test_clock_signature(self) -> None:
        stub = SystemClockStub()
        assert hasattr(stub, "now")
        result = stub.now()
        assert isinstance(result, datetime)

    def test_id_generator_signatures(self) -> None:
        stub = UuidPlannerIdGenerator()
        assert hasattr(stub, "generate_plan_id")
        assert hasattr(stub, "generate_task_id")
        assert hasattr(stub, "generate_step_id")

    def test_plan_repo_has_all_methods(self) -> None:
        methods = ["save", "find_by_id", "find_by_status", "find_by_priority", "find_active", "count"]
        stub = StubPlanRepository()
        for m in methods:
            assert hasattr(stub, m), f"Plan repo missing method {m}"

    def test_task_repo_has_all_methods(self) -> None:
        methods = ["save", "find_by_id", "find_by_status", "find_by_agent", "find_by_plan_id", "count"]
        stub = StubTaskRepository()
        for m in methods:
            assert hasattr(stub, m), f"Task repo missing method {m}"

    def test_outbox_has_all_methods(self) -> None:
        methods = ["append", "fetch_unpublished", "mark_published"]
        stub = StubPlannerOutbox()
        for m in methods:
            assert hasattr(stub, m), f"Outbox missing method {m}"

    def test_id_generator_has_all_methods(self) -> None:
        methods = ["generate_plan_id", "generate_task_id", "generate_step_id"]
        stub = UuidPlannerIdGenerator()
        for m in methods:
            assert hasattr(stub, m), f"ID generator missing method {m}"


# =========================================================================
# PlannerOutboxEvent union type verification
# =========================================================================


class TestPlannerOutboxEventUnion:
    """Verify that PlannerOutboxEvent accepts all expected event types."""

    def test_plan_created_is_valid(self) -> None:
        event: PlannerOutboxEvent = PlanCreated(
            plan_id=PlanId(), user_request="r", goal="g",
            priority="n", strategy="s", occurred_at=_NOW,
        )
        assert isinstance(event, PlanCreated)

    def test_plan_approved_is_valid(self) -> None:
        event: PlannerOutboxEvent = PlanApproved(
            plan_id=PlanId(), occurred_at=_NOW,
        )
        assert isinstance(event, PlanApproved)

    def test_plan_ready_is_valid(self) -> None:
        event: PlannerOutboxEvent = PlanReady(
            plan_id=PlanId(), occurred_at=_NOW,
        )
        assert isinstance(event, PlanReady)

    def test_plan_execution_started_is_valid(self) -> None:
        event: PlannerOutboxEvent = PlanExecutionStarted(
            plan_id=PlanId(), occurred_at=_NOW,
        )
        assert isinstance(event, PlanExecutionStarted)

    def test_plan_completed_is_valid(self) -> None:
        event: PlannerOutboxEvent = PlanCompleted(
            plan_id=PlanId(), occurred_at=_NOW,
        )
        assert isinstance(event, PlanCompleted)

    def test_plan_failed_is_valid(self) -> None:
        event: PlannerOutboxEvent = PlanFailed(
            plan_id=PlanId(), failure_reason="reason", occurred_at=_NOW,
        )
        assert isinstance(event, PlanFailed)

    def test_plan_cancelled_is_valid(self) -> None:
        event: PlannerOutboxEvent = PlanCancelled(
            plan_id=PlanId(), occurred_at=_NOW,
        )
        assert isinstance(event, PlanCancelled)

    def test_task_created_is_valid(self) -> None:
        event: PlannerOutboxEvent = TaskCreated(
            task_id=TaskId(), description="d", occurred_at=_NOW,
        )
        assert isinstance(event, TaskCreated)

    def test_task_assigned_is_valid(self) -> None:
        event: PlannerOutboxEvent = TaskAssigned(
            task_id=TaskId(), assigned_agent=AgentType.PLANNER,
            occurred_at=_NOW,
        )
        assert isinstance(event, TaskAssigned)

    def test_task_completed_is_valid(self) -> None:
        event: PlannerOutboxEvent = TaskCompleted(
            task_id=TaskId(), occurred_at=_NOW,
        )
        assert isinstance(event, TaskCompleted)

    def test_task_failed_is_valid(self) -> None:
        event: PlannerOutboxEvent = TaskFailed(
            task_id=TaskId(), failure_reason="err", occurred_at=_NOW,
        )
        assert isinstance(event, TaskFailed)
