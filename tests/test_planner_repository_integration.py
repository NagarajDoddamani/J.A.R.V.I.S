from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator
from uuid import UUID

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.planner.adapters.outbound.clock import SystemClockAdapter
from backend.planner.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.planner.adapters.outbound.mapper import (
    ExecutionStepMapperImpl,
    PlanMapperImpl,
    PlannerOutboxMapperImpl,
    TaskMapperImpl,
)
from backend.planner.adapters.outbound.models import Base
from backend.planner.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyPlanRepository,
    SqlAlchemyPlannerOutboxAdapter,
    SqlAlchemyTaskRepository,
)
from backend.planner.domain.model import (
    AgentType,
    EstimatedDuration,
    ExecutionStep,
    ExecutionStepId,
    ExecutionStrategy,
    FailureReason,
    Plan,
    PlanGoal,
    PlanId,
    PlanPriority,
    PlanStatus,
    Task,
    TaskCreated,
    TaskDescription,
    TaskId,
    TaskStatus,
    UserRequest,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def engine() -> Iterator[Engine]:
    e = create_engine("sqlite://", echo=False)
    for t in Base.metadata.tables.values():
        t.schema = None
    Base.metadata.create_all(bind=e)
    yield e
    e.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    S = sessionmaker(bind=engine)
    s = S()
    yield s
    s.close()


@pytest.fixture
def plan_mapper() -> PlanMapperImpl:
    return PlanMapperImpl()


@pytest.fixture
def task_mapper() -> TaskMapperImpl:
    return TaskMapperImpl()


@pytest.fixture
def step_mapper() -> ExecutionStepMapperImpl:
    return ExecutionStepMapperImpl()


@pytest.fixture
def outbox_mapper() -> PlannerOutboxMapperImpl:
    return PlannerOutboxMapperImpl()


@pytest.fixture
def clock() -> SystemClockAdapter:
    return SystemClockAdapter()


@pytest.fixture
def id_gen() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


@pytest.fixture
def plan_repo(
    session: Session, plan_mapper: PlanMapperImpl
) -> SqlAlchemyPlanRepository:
    return SqlAlchemyPlanRepository(session=session, mapper=plan_mapper)


@pytest.fixture
def task_repo(
    session: Session, task_mapper: TaskMapperImpl
) -> SqlAlchemyTaskRepository:
    return SqlAlchemyTaskRepository(session=session, mapper=task_mapper)


@pytest.fixture
def outbox_adapter(
    session: Session, outbox_mapper: PlannerOutboxMapperImpl
) -> SqlAlchemyPlannerOutboxAdapter:
    return SqlAlchemyPlannerOutboxAdapter(session=session, mapper=outbox_mapper)


@pytest.fixture
def a_plan(clock: SystemClockAdapter) -> Plan:
    return Plan(
        plan_id=PlanId(),
        user_request=UserRequest(value="integration request"),
        goal=PlanGoal(value="integration goal"),
        priority=PlanPriority.NORMAL,
        strategy=ExecutionStrategy.SEQUENTIAL,
        status=PlanStatus.DRAFT,
        created_at=clock.now(),
        updated_at=clock.now(),
    )


@pytest.fixture
def a_task(clock: SystemClockAdapter) -> Task:
    return Task(
        task_id=TaskId(),
        description=TaskDescription(value="integration task"),
        status=TaskStatus.PENDING,
    )


# ===================================================================
# Plan repository integration tests
# ===================================================================


class TestPlanRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        plan_repo: SqlAlchemyPlanRepository,
        a_plan: Plan,
    ) -> None:
        plan_repo.save(a_plan)
        found = plan_repo.find_by_id(a_plan.plan_id)
        assert found is not None
        assert str(found.plan_id) == str(a_plan.plan_id)

    def test_save_updates_existing(
        self,
        plan_repo: SqlAlchemyPlanRepository,
        a_plan: Plan,
    ) -> None:
        plan_repo.save(a_plan)
        a_plan.approve()
        plan_repo.save(a_plan)
        found = plan_repo.find_by_id(a_plan.plan_id)
        assert found is not None
        assert found.status == PlanStatus.APPROVED

    def test_find_by_id_missing(
        self,
        plan_repo: SqlAlchemyPlanRepository,
    ) -> None:
        found = plan_repo.find_by_id(PlanId())
        assert found is None

    def test_find_by_status(
        self,
        plan_repo: SqlAlchemyPlanRepository,
        a_plan: Plan,
    ) -> None:
        plan_repo.save(a_plan)
        results = plan_repo.find_by_status(PlanStatus.DRAFT)
        assert len(results) >= 1
        assert results[0].plan_id == a_plan.plan_id

    def test_find_by_status_empty(
        self,
        plan_repo: SqlAlchemyPlanRepository,
    ) -> None:
        results = plan_repo.find_by_status(PlanStatus.COMPLETED)
        assert len(results) == 0

    def test_find_by_priority(
        self,
        plan_repo: SqlAlchemyPlanRepository,
        a_plan: Plan,
    ) -> None:
        plan_repo.save(a_plan)
        results = plan_repo.find_by_priority(PlanPriority.NORMAL)
        assert len(results) >= 1

    def test_find_by_priority_empty(
        self,
        plan_repo: SqlAlchemyPlanRepository,
    ) -> None:
        results = plan_repo.find_by_priority(PlanPriority.CRITICAL)
        assert len(results) == 0

    def test_find_active(
        self,
        plan_repo: SqlAlchemyPlanRepository,
        a_plan: Plan,
    ) -> None:
        plan_repo.save(a_plan)
        results = plan_repo.find_active()
        assert len(results) >= 1

    def test_find_active_excludes_terminal(
        self,
        plan_repo: SqlAlchemyPlanRepository,
    ) -> None:
        plan = Plan(
            plan_id=PlanId(),
            user_request=UserRequest(value="r"),
            goal=PlanGoal(value="g"),
            priority=PlanPriority.NORMAL,
            strategy=ExecutionStrategy.SEQUENTIAL,
            status=PlanStatus.COMPLETED,
            created_at=NOW,
            updated_at=NOW,
        )
        plan_repo.save(plan)
        results = plan_repo.find_active()
        for r in results:
            assert r.status not in (
                PlanStatus.COMPLETED,
                PlanStatus.FAILED,
                PlanStatus.CANCELLED,
            )

    def test_count(
        self,
        plan_repo: SqlAlchemyPlanRepository,
        a_plan: Plan,
    ) -> None:
        assert plan_repo.count() == 0
        plan_repo.save(a_plan)
        assert plan_repo.count() == 1

    def test_lifecycle_persistence(
        self,
        plan_repo: SqlAlchemyPlanRepository,
        a_plan: Plan,
    ) -> None:
        plan_repo.save(a_plan)
        a_plan.approve()
        plan_repo.save(a_plan)
        found = plan_repo.find_by_id(a_plan.plan_id)
        assert found is not None
        assert found.status == PlanStatus.APPROVED


# ===================================================================
# Task repository integration tests
# ===================================================================


class TestTaskRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        task_repo: SqlAlchemyTaskRepository,
        a_task: Task,
    ) -> None:
        task_repo.save(a_task)
        found = task_repo.find_by_id(a_task.task_id)
        assert found is not None
        assert str(found.task_id) == str(a_task.task_id)

    def test_save_updates_existing(
        self,
        task_repo: SqlAlchemyTaskRepository,
        a_task: Task,
    ) -> None:
        task_repo.save(a_task)
        a_task.assign(AgentType.RESEARCH)
        task_repo.save(a_task)
        found = task_repo.find_by_id(a_task.task_id)
        assert found is not None
        assert found.status == TaskStatus.ASSIGNED
        assert found.assigned_agent == AgentType.RESEARCH

    def test_find_by_id_missing(
        self,
        task_repo: SqlAlchemyTaskRepository,
    ) -> None:
        found = task_repo.find_by_id(TaskId())
        assert found is None

    def test_find_by_status(
        self,
        task_repo: SqlAlchemyTaskRepository,
        a_task: Task,
    ) -> None:
        task_repo.save(a_task)
        results = task_repo.find_by_status(TaskStatus.PENDING)
        assert len(results) >= 1
        assert results[0].task_id == a_task.task_id

    def test_find_by_status_empty(
        self,
        task_repo: SqlAlchemyTaskRepository,
    ) -> None:
        results = task_repo.find_by_status(TaskStatus.COMPLETED)
        assert len(results) == 0

    def test_find_by_agent(
        self,
        task_repo: SqlAlchemyTaskRepository,
        a_task: Task,
    ) -> None:
        a_task.assign(AgentType.RESEARCH)
        task_repo.save(a_task)
        results = task_repo.find_by_agent(AgentType.RESEARCH)
        assert len(results) >= 1

    def test_find_by_agent_empty(
        self,
        task_repo: SqlAlchemyTaskRepository,
    ) -> None:
        results = task_repo.find_by_agent(AgentType.AUTOMATION)
        assert len(results) == 0

    def test_find_by_plan_id(
        self,
        task_repo: SqlAlchemyTaskRepository,
        a_task: Task,
    ) -> None:
        task_repo.save(a_task)
        results = task_repo.find_by_plan_id(PlanId())
        assert isinstance(results, list)

    def test_count(
        self,
        task_repo: SqlAlchemyTaskRepository,
        a_task: Task,
    ) -> None:
        assert task_repo.count() == 0
        task_repo.save(a_task)
        assert task_repo.count() == 1

    def test_failure_reason_persisted(
        self,
        task_repo: SqlAlchemyTaskRepository,
    ) -> None:
        task = Task(
            task_id=TaskId(),
            description=TaskDescription(value="failing task"),
            status=TaskStatus.FAILED,
            failure_reason=FailureReason(value="something broke"),
        )
        task_repo.save(task)
        found = task_repo.find_by_id(task.task_id)
        assert found is not None
        assert found.status == TaskStatus.FAILED
        assert str(found.failure_reason) == "something broke"

    def test_estimated_duration_persisted(
        self,
        task_repo: SqlAlchemyTaskRepository,
    ) -> None:
        task = Task(
            task_id=TaskId(),
            description=TaskDescription(value="timed task"),
            status=TaskStatus.ASSIGNED,
            assigned_agent=AgentType.AUTOMATION,
            estimated_duration=EstimatedDuration(value=45.5),
        )
        task_repo.save(task)
        found = task_repo.find_by_id(task.task_id)
        assert found is not None
        assert found.estimated_duration is not None
        assert float(found.estimated_duration) == 45.5


# ===================================================================
# Outbox adapter integration tests
# ===================================================================


class TestPlannerOutboxAdapterIntegration:
    def test_append_and_fetch(
        self,
        outbox_adapter: SqlAlchemyPlannerOutboxAdapter,
    ) -> None:
        event = TaskCreated(
            task_id=TaskId(),
            description="test event",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], TaskCreated)

    def test_fifo_ordering(
        self,
        outbox_adapter: SqlAlchemyPlannerOutboxAdapter,
    ) -> None:
        t1 = TaskCreated(TaskId(), "first", NOW)
        t2 = TaskCreated(TaskId(), "second", NOW)
        outbox_adapter.append(t1)
        outbox_adapter.append(t2)
        unpublished = outbox_adapter.fetch_unpublished(limit=10)
        assert len(unpublished) == 2
        assert unpublished[0].description == "first"
        assert unpublished[1].description == "second"

    def test_mark_published(
        self,
        outbox_adapter: SqlAlchemyPlannerOutboxAdapter,
        session: Session,
    ) -> None:
        event = TaskCreated(
            task_id=TaskId(),
            description="publish me",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        unpublished_before = outbox_adapter.fetch_unpublished()
        assert len(unpublished_before) == 1

        unpublished_before = outbox_adapter.fetch_unpublished()
        outbox_adapter.mark_published(str(unpublished_before[0].event_id))
        session.flush()
        unpublished_after = outbox_adapter.fetch_unpublished()
        assert len(unpublished_after) == 0

    def test_mark_published_idempotent(
        self,
        outbox_adapter: SqlAlchemyPlannerOutboxAdapter,
    ) -> None:
        event = TaskCreated(
            task_id=TaskId(),
            description="idempotent",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        fetched = outbox_adapter.fetch_unpublished()
        outbox_adapter.mark_published(str(fetched[0].event_id))
        outbox_adapter.mark_published(str(fetched[0].event_id))

    def test_fetch_limit(
        self,
        outbox_adapter: SqlAlchemyPlannerOutboxAdapter,
    ) -> None:
        for i in range(5):
            event = TaskCreated(
                task_id=TaskId(),
                description=f"event-{i}",
                occurred_at=NOW,
            )
            outbox_adapter.append(event)
        results = outbox_adapter.fetch_unpublished(limit=3)
        assert len(results) == 3

    def test_empty_outbox(
        self,
        outbox_adapter: SqlAlchemyPlannerOutboxAdapter,
    ) -> None:
        results = outbox_adapter.fetch_unpublished()
        assert len(results) == 0


# ===================================================================
# Plan-task relationship integration tests
# ===================================================================


class TestPlanTaskRelationship:
    def test_plan_and_task_independent_storage(
        self,
        plan_repo: SqlAlchemyPlanRepository,
        task_repo: SqlAlchemyTaskRepository,
        a_plan: Plan,
        a_task: Task,
    ) -> None:
        plan_repo.save(a_plan)
        task_repo.save(a_task)
        found_plan = plan_repo.find_by_id(a_plan.plan_id)
        found_task = task_repo.find_by_id(a_task.task_id)
        assert found_plan is not None
        assert found_task is not None

    def test_multiple_plans(
        self,
        plan_repo: SqlAlchemyPlanRepository,
    ) -> None:
        p1 = Plan(
            plan_id=PlanId(),
            user_request=UserRequest(value="r1"),
            goal=PlanGoal(value="g1"),
            priority=PlanPriority.HIGH,
            strategy=ExecutionStrategy.PARALLEL,
            status=PlanStatus.DRAFT,
            created_at=NOW,
        )
        p2 = Plan(
            plan_id=PlanId(),
            user_request=UserRequest(value="r2"),
            goal=PlanGoal(value="g2"),
            priority=PlanPriority.LOW,
            strategy=ExecutionStrategy.SEQUENTIAL,
            status=PlanStatus.APPROVED,
            created_at=NOW,
        )
        plan_repo.save(p1)
        plan_repo.save(p2)
        assert plan_repo.count() == 2

    def test_multiple_tasks(
        self,
        task_repo: SqlAlchemyTaskRepository,
    ) -> None:
        t1 = Task(
            task_id=TaskId(),
            description=TaskDescription(value="task A"),
            status=TaskStatus.PENDING,
        )
        t2 = Task(
            task_id=TaskId(),
            description=TaskDescription(value="task B"),
            status=TaskStatus.ASSIGNED,
            assigned_agent=AgentType.MEMORY,
        )
        task_repo.save(t1)
        task_repo.save(t2)
        assert task_repo.count() == 2

    def test_sqlite_roundtrip(
        self,
        session: Session,
        plan_repo: SqlAlchemyPlanRepository,
        a_plan: Plan,
    ) -> None:
        plan_repo.save(a_plan)
        session.commit()
        session.expire_all()
        found = plan_repo.find_by_id(a_plan.plan_id)
        assert found is not None
        assert str(found.plan_id) == str(a_plan.plan_id)
        assert str(found.user_request) == "integration request"
        assert found.priority == PlanPriority.NORMAL
        assert found.strategy == ExecutionStrategy.SEQUENTIAL
        assert found.status == PlanStatus.DRAFT
