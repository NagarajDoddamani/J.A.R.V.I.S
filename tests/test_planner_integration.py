from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.api.endpoints import planner as planner_router
from backend.core.database import get_db
from backend.planner.adapters.outbound.clock import SystemClockAdapter
from backend.planner.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.planner.adapters.outbound.mapper import (
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
from backend.planner.application.use_cases.add_task import AddTaskUseCase
from backend.planner.application.use_cases.approve_plan import ApprovePlanUseCase
from backend.planner.application.use_cases.assign_task import AssignTaskUseCase
from backend.planner.application.use_cases.cancel_plan import CancelPlanUseCase
from backend.planner.application.use_cases.complete_plan import CompletePlanUseCase
from backend.planner.application.use_cases.complete_task import CompleteTaskUseCase
from backend.planner.application.use_cases.create_plan import CreatePlanUseCase
from backend.planner.application.use_cases.dto import (
    AddTaskRequest,
    AssignTaskRequest,
    CreatePlanRequest,
    FailPlanRequest,
    FailTaskRequest,
    GetPlanRequest,
    GetTaskRequest,
    ListPlansRequest,
    ListTasksRequest,
    PlanLifecycleRequest,
    TaskLifecycleRequest,
)
from backend.planner.application.use_cases.exceptions import (
    PlanNotFoundError,
    TaskNotFoundError,
)
from backend.planner.application.use_cases.fail_plan import FailPlanUseCase
from backend.planner.application.use_cases.fail_task import FailTaskUseCase
from backend.planner.application.use_cases.get_plan import GetPlanUseCase
from backend.planner.application.use_cases.get_task import GetTaskUseCase
from backend.planner.application.use_cases.list_plans import ListPlansUseCase
from backend.planner.application.use_cases.list_tasks import ListTasksUseCase
from backend.planner.application.use_cases.mark_plan_ready import (
    MarkPlanReadyUseCase,
)
from backend.planner.application.use_cases.start_execution import (
    StartExecutionUseCase,
)
from backend.planner.application.use_cases.start_planning import (
    StartPlanningUseCase,
)
from backend.planner.application.use_cases.start_task import StartTaskUseCase
from backend.planner.domain.exceptions import (
    PlanHasNoTasksError,
    PlannerDomainError,
)
from backend.planner.domain.model import (
    AgentType,
    ExecutionStrategy,
    PlanCreated,
    PlanGoal,
    PlanId,
    PlanPriority,
    PlanStatus,
    TaskId,
    TaskStatus,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.engine import Engine

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)

for _table in Base.metadata.tables.values():
    _table.schema = None

# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def engine() -> Iterator[Engine]:
    e = create_engine("sqlite://", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    yield e
    e.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    conn = engine.connect()
    s = Session(bind=conn)
    yield s
    s.close()
    conn.close()


@pytest.fixture
def clock() -> SystemClockAdapter:
    return SystemClockAdapter()


@pytest.fixture
def id_gen() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


@pytest.fixture
def plan_mapper() -> PlanMapperImpl:
    return PlanMapperImpl()


@pytest.fixture
def task_mapper() -> TaskMapperImpl:
    return TaskMapperImpl()


@pytest.fixture
def outbox_mapper() -> PlannerOutboxMapperImpl:
    return PlannerOutboxMapperImpl()


@pytest.fixture
def plan_repo(session: Session, plan_mapper: PlanMapperImpl) -> SqlAlchemyPlanRepository:
    return SqlAlchemyPlanRepository(session, mapper=plan_mapper)


@pytest.fixture
def task_repo(session: Session, task_mapper: TaskMapperImpl) -> SqlAlchemyTaskRepository:
    return SqlAlchemyTaskRepository(session, mapper=task_mapper)


@pytest.fixture
def outbox(session: Session) -> SqlAlchemyPlannerOutboxAdapter:
    return SqlAlchemyPlannerOutboxAdapter(session)


@pytest.fixture
def client(session: Session):
    def _override_get_db():
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    app = FastAPI()
    app.include_router(planner_router.router, prefix="/api/v1/planner")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


# ===================================================================
# Helpers
# ===================================================================


def _create_plan_id(plan_repo, outbox) -> str:
    uc = CreatePlanUseCase(plan_repo, outbox)
    resp = uc.execute(
        CreatePlanRequest(
            user_request="integration test",
            goal="verify lifecycle",
            priority="normal",
            strategy="sequential",
        )
    )
    return resp.plan_id


def _create_approved_plan(plan_repo, outbox) -> str:
    pid = _create_plan_id(plan_repo, outbox)
    ApprovePlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
    return pid


def _create_planning_plan(plan_repo, outbox) -> str:
    pid = _create_approved_plan(plan_repo, outbox)
    StartPlanningUseCase(plan_repo).execute(PlanLifecycleRequest(plan_id=pid))
    return pid


def _add_task(plan_repo, task_repo, outbox, plan_id: str) -> str:
    uc = AddTaskUseCase(plan_repo, task_repo, outbox)
    resp = uc.execute(AddTaskRequest(plan_id=plan_id, description="integration task"))
    return resp.task_id


def _create_ready_plan(plan_repo, task_repo, outbox) -> str:
    pid = _create_planning_plan(plan_repo, outbox)
    _add_task(plan_repo, task_repo, outbox, pid)
    MarkPlanReadyUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
    return pid


def _create_executing_plan(plan_repo, task_repo, outbox) -> str:
    pid = _create_ready_plan(plan_repo, task_repo, outbox)
    StartExecutionUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
    return pid


# ===================================================================
# Plan lifecycle
# ===================================================================


class TestPlanLifecycle:
    def test_full_lifecycle(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_plan_id(plan_repo, outbox)
        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan is not None
        assert plan.status == PlanStatus.DRAFT

        ApprovePlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan.status == PlanStatus.APPROVED

        StartPlanningUseCase(plan_repo).execute(PlanLifecycleRequest(plan_id=pid))
        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan.status == PlanStatus.PLANNING

        _add_task(plan_repo, task_repo, outbox, pid)

        MarkPlanReadyUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan.status == PlanStatus.READY

        StartExecutionUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan.status == PlanStatus.EXECUTING

        CompletePlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan.status == PlanStatus.COMPLETED

    def test_full_lifecycle_emits_events(self, plan_repo, outbox) -> None:
        pid = _create_plan_id(plan_repo, outbox)
        ApprovePlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
        events = outbox.fetch_unpublished()
        assert len(events) >= 2

    def test_approve_from_draft(self, plan_repo, outbox) -> None:
        pid = _create_plan_id(plan_repo, outbox)
        ApprovePlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan.status == PlanStatus.APPROVED

    def test_approve_twice_raises_error(self, plan_repo, outbox) -> None:
        pid = _create_approved_plan(plan_repo, outbox)
        with pytest.raises(PlannerDomainError):
            ApprovePlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))

    def test_planning_from_draft_raises_error(self, plan_repo, outbox) -> None:
        pid = _create_plan_id(plan_repo, outbox)
        with pytest.raises(PlannerDomainError):
            StartPlanningUseCase(plan_repo).execute(PlanLifecycleRequest(plan_id=pid))

    def test_mark_ready_without_tasks_raises_error(self, plan_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        with pytest.raises(PlanHasNoTasksError):
            MarkPlanReadyUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))

    def test_execute_from_ready(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_ready_plan(plan_repo, task_repo, outbox)
        StartExecutionUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan.status == PlanStatus.EXECUTING

    def test_execute_not_ready_raises_error(self, plan_repo, outbox) -> None:
        pid = _create_approved_plan(plan_repo, outbox)
        with pytest.raises(PlannerDomainError):
            StartExecutionUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))

    def test_complete_from_executing(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_executing_plan(plan_repo, task_repo, outbox)
        CompletePlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan.status == PlanStatus.COMPLETED

    def test_complete_not_executing_raises_error(self, plan_repo, outbox) -> None:
        pid = _create_approved_plan(plan_repo, outbox)
        with pytest.raises(PlannerDomainError):
            CompletePlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))

    def test_cancel_from_draft(self, plan_repo, outbox) -> None:
        pid = _create_plan_id(plan_repo, outbox)
        CancelPlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan.status == PlanStatus.CANCELLED

    def test_cancel_from_approved(self, plan_repo, outbox) -> None:
        pid = _create_approved_plan(plan_repo, outbox)
        CancelPlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan.status == PlanStatus.CANCELLED

    def test_cancel_from_planning(self, plan_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        CancelPlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan.status == PlanStatus.CANCELLED

    def test_cant_cancel_completed_plan(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_executing_plan(plan_repo, task_repo, outbox)
        CompletePlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
        with pytest.raises(PlannerDomainError):
            CancelPlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))

    def test_cant_cancel_failed_plan(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_executing_plan(plan_repo, task_repo, outbox)
        FailPlanUseCase(plan_repo, outbox).execute(
            FailPlanRequest(plan_id=pid, failure_reason="test failure")
        )
        with pytest.raises(PlannerDomainError):
            CancelPlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))

    def test_cant_approve_nonexistent_plan(self, plan_repo, outbox) -> None:
        with pytest.raises(PlanNotFoundError):
            ApprovePlanUseCase(plan_repo, outbox).execute(
                PlanLifecycleRequest(plan_id="00000000-0000-0000-0000-000000000000")
            )


# ===================================================================
# Failure lifecycle
# ===================================================================


class TestFailureLifecycle:
    def test_fail_from_executing(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_executing_plan(plan_repo, task_repo, outbox)
        FailPlanUseCase(plan_repo, outbox).execute(
            FailPlanRequest(plan_id=pid, failure_reason="failure")
        )
        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan.status == PlanStatus.FAILED

    def test_fail_twice_raises_error(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_executing_plan(plan_repo, task_repo, outbox)
        FailPlanUseCase(plan_repo, outbox).execute(
            FailPlanRequest(plan_id=pid, failure_reason="failure")
        )
        with pytest.raises(PlannerDomainError):
            FailPlanUseCase(plan_repo, outbox).execute(
                FailPlanRequest(plan_id=pid, failure_reason="again")
            )

    def test_fail_empty_reason_raises_error(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_executing_plan(plan_repo, task_repo, outbox)
        with pytest.raises(PlannerDomainError):
            FailPlanUseCase(plan_repo, outbox).execute(
                FailPlanRequest(plan_id=pid, failure_reason="")
            )

    def test_fail_nonexistent_plan_raises_error(self, plan_repo, outbox) -> None:
        with pytest.raises(PlanNotFoundError):
            FailPlanUseCase(plan_repo, outbox).execute(
                FailPlanRequest(
                    plan_id="00000000-0000-0000-0000-000000000000",
                    failure_reason="failure",
                )
            )

    def test_fail_emits_event(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_executing_plan(plan_repo, task_repo, outbox)
        from backend.planner.domain.model import PlanFailed
        FailPlanUseCase(plan_repo, outbox).execute(
            FailPlanRequest(plan_id=pid, failure_reason="critical error")
        )
        events = outbox.fetch_unpublished()
        failed = next(e for e in events if isinstance(e, PlanFailed))
        assert failed.failure_reason == "critical error"


# ===================================================================
# Task lifecycle
# ===================================================================


class TestTaskLifecycle:
    def test_task_full_lifecycle(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)

        task = task_repo.find_by_id(TaskId(value=tid))
        assert task is not None
        assert task.status == TaskStatus.PENDING
        assert str(task.plan_id) == pid

        AssignTaskUseCase(task_repo, outbox).execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        task = task_repo.find_by_id(TaskId(value=tid))
        assert task.status == TaskStatus.ASSIGNED

        StartTaskUseCase(task_repo).execute(TaskLifecycleRequest(task_id=tid))
        task = task_repo.find_by_id(TaskId(value=tid))
        assert task.status == TaskStatus.RUNNING

        CompleteTaskUseCase(task_repo, outbox).execute(TaskLifecycleRequest(task_id=tid))
        task = task_repo.find_by_id(TaskId(value=tid))
        assert task.status == TaskStatus.COMPLETED

    def test_task_failure_lifecycle(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)

        AssignTaskUseCase(task_repo, outbox).execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        StartTaskUseCase(task_repo).execute(TaskLifecycleRequest(task_id=tid))
        FailTaskUseCase(task_repo, outbox).execute(
            FailTaskRequest(task_id=tid, failure_reason="task failed")
        )
        task = task_repo.find_by_id(TaskId(value=tid))
        assert task.status == TaskStatus.FAILED

    def test_assign_emits_event(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)
        AssignTaskUseCase(task_repo, outbox).execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        events = outbox.fetch_unpublished()
        assert len(events) >= 1

    def test_assign_invalid_agent_raises_error(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)
        with pytest.raises(PlannerDomainError):
            AssignTaskUseCase(task_repo, outbox).execute(
                AssignTaskRequest(task_id=tid, agent="invalid_agent")
            )

    def test_assign_twice_raises_error(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)
        AssignTaskUseCase(task_repo, outbox).execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        with pytest.raises(PlannerDomainError):
            AssignTaskUseCase(task_repo, outbox).execute(
                AssignTaskRequest(task_id=tid, agent="coder")
            )

    def test_start_without_assign_raises_error(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)
        with pytest.raises(PlannerDomainError):
            StartTaskUseCase(task_repo).execute(TaskLifecycleRequest(task_id=tid))

    def test_complete_without_start_raises_error(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)
        AssignTaskUseCase(task_repo, outbox).execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        with pytest.raises(PlannerDomainError):
            CompleteTaskUseCase(task_repo, outbox).execute(TaskLifecycleRequest(task_id=tid))

    def test_fail_without_start_raises_error(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)
        AssignTaskUseCase(task_repo, outbox).execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        with pytest.raises(PlannerDomainError):
            FailTaskUseCase(task_repo, outbox).execute(
                FailTaskRequest(task_id=tid, failure_reason="fail")
            )

    def test_cant_complete_after_fail(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)
        AssignTaskUseCase(task_repo, outbox).execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        StartTaskUseCase(task_repo).execute(TaskLifecycleRequest(task_id=tid))
        FailTaskUseCase(task_repo, outbox).execute(
            FailTaskRequest(task_id=tid, failure_reason="fail")
        )
        with pytest.raises(PlannerDomainError):
            CompleteTaskUseCase(task_repo, outbox).execute(TaskLifecycleRequest(task_id=tid))

    def test_task_not_found_raises_error(self, plan_repo, task_repo, outbox) -> None:
        with pytest.raises(TaskNotFoundError):
            StartTaskUseCase(task_repo).execute(
                TaskLifecycleRequest(task_id="00000000-0000-0000-0000-000000000000")
            )


# ===================================================================
# Repository roundtrip
# ===================================================================


class TestRepositoryRoundtrip:
    def test_plan_roundtrip_preserves_all_fields(self, plan_repo, outbox) -> None:
        from backend.planner.domain.factory import PlannerFactory

        plan, _ = PlannerFactory.create_plan(
            user_request="roundtrip test",
            goal="verify fields",
            priority="high",
            strategy="parallel",
        )
        plan_repo.save(plan)
        loaded = plan_repo.find_by_id(plan.plan_id)
        assert loaded is not None
        assert str(loaded.plan_id) == str(plan.plan_id)
        assert str(loaded.user_request) == "roundtrip test"
        assert str(loaded.goal) == "verify fields"
        assert loaded.priority == PlanPriority.HIGH
        assert loaded.strategy == ExecutionStrategy.PARALLEL
        assert loaded.status == PlanStatus.DRAFT

    def test_plan_with_tasks_roundtrip(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)

        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan is not None
        assert len(plan.tasks) >= 1
        task_ids = [str(t.task_id) for t in plan.tasks]
        assert tid in task_ids

    def test_plan_task_status_sync(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)
        AssignTaskUseCase(task_repo, outbox).execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        StartTaskUseCase(task_repo).execute(TaskLifecycleRequest(task_id=tid))
        CompleteTaskUseCase(task_repo, outbox).execute(TaskLifecycleRequest(task_id=tid))

        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan is not None
        assert plan.tasks[0].status == TaskStatus.COMPLETED

    def test_task_roundtrip_preserves_all_fields(self, task_repo, outbox, plan_repo) -> None:
        from backend.planner.domain.factory import PlannerFactory
        from backend.planner.domain.model import Plan

        plan = Plan(plan_id=PlanId())
        task, _ = PlannerFactory.add_task(plan=plan, description="full field roundtrip")
        task_repo.save(task)

        loaded = task_repo.find_by_id(task.task_id)
        assert loaded is not None
        assert str(loaded.task_id) == str(task.task_id)
        assert str(loaded.description) == "full field roundtrip"
        assert loaded.status == TaskStatus.PENDING

    def test_task_find_by_plan_id(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        _add_task(plan_repo, task_repo, outbox, pid)

        tasks = task_repo.find_by_plan_id(PlanId(value=pid))
        assert len(tasks) >= 1
        assert all(str(t.plan_id) == pid for t in tasks)

    def test_multiple_tasks_on_plan(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        for _ in range(3):
            _add_task(plan_repo, task_repo, outbox, pid)
        plan = plan_repo.find_by_id(PlanId(value=pid))
        assert plan is not None
        assert len(plan.tasks) == 3

    def test_plan_find_by_status(self, plan_repo, outbox) -> None:
        _create_approved_plan(plan_repo, outbox)
        plans = plan_repo.find_by_status(PlanStatus.APPROVED)
        assert len(plans) >= 1

    def test_plan_find_active(self, plan_repo, outbox) -> None:
        _create_plan_id(plan_repo, outbox)
        active = plan_repo.find_active()
        assert len(active) >= 1
        for p in active:
            assert p.status not in (PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.CANCELLED)

    def test_plan_count(self, plan_repo, outbox) -> None:
        _create_plan_id(plan_repo, outbox)
        assert plan_repo.count() >= 1


# ===================================================================
# Outbox lifecycle
# ===================================================================


class TestOutboxLifecycle:
    def test_append_then_fetch(self, outbox) -> None:
        now = datetime.now(timezone.utc)
        event = PlanCreated(
            plan_id=PlanId(),
            user_request="test",
            goal="test",
            priority="normal",
            strategy="sequential",
            occurred_at=now,
        )
        outbox.append(event)
        events = outbox.fetch_unpublished()
        assert len(events) >= 1

    def test_fetch_unpublished_only(self, outbox) -> None:
        now = datetime.now(timezone.utc)
        event = PlanCreated(
            plan_id=PlanId(),
            user_request="test",
            goal="test",
            priority="normal",
            strategy="sequential",
            occurred_at=now,
        )
        outbox.append(event)
        events = outbox.fetch_unpublished()
        assert len(events) >= 1
        events = outbox.fetch_unpublished()
        outbox.mark_published(str(events[0].event_id))
        remaining = outbox.fetch_unpublished()
        remaining_matching = [e for e in remaining if str(e.plan_id) == str(event.plan_id)]
        assert len(remaining_matching) == 0

    def test_mark_published_idempotent(self, outbox) -> None:
        now = datetime.now(timezone.utc)
        event = PlanCreated(
            plan_id=PlanId(),
            user_request="test",
            goal="test",
            priority="normal",
            strategy="sequential",
            occurred_at=now,
        )
        outbox.append(event)
        fetched = outbox.fetch_unpublished()
        outbox.mark_published(str(fetched[0].event_id))
        outbox.mark_published(str(fetched[0].event_id))

    def test_fetch_respects_limit(self, outbox) -> None:
        now = datetime.now(timezone.utc)
        for _ in range(5):
            outbox.append(
                PlanCreated(
                    plan_id=PlanId(),
                    user_request="test",
                    goal="test",
                    priority="normal",
                    strategy="sequential",
                    occurred_at=now,
                )
            )
        events = outbox.fetch_unpublished(limit=3)
        assert len(events) <= 3

    def test_event_has_aggregate_id(self, outbox) -> None:
        now = datetime.now(timezone.utc)
        pid = PlanId()
        event = PlanCreated(
            plan_id=pid,
            user_request="test",
            goal="test",
            priority="normal",
            strategy="sequential",
            occurred_at=now,
        )
        outbox.append(event)
        events = outbox.fetch_unpublished()
        matching = [e for e in events if e.plan_id == pid]
        assert len(matching) >= 1

    def test_outbox_append_mark_flow(self, outbox, plan_repo, outbox_mapper) -> None:
        now = datetime.now(timezone.utc)
        event = PlanCreated(
            plan_id=PlanId(),
            user_request="test",
            goal="test",
            priority="normal",
            strategy="sequential",
            occurred_at=now,
        )
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) > 0
        outbox.mark_published(str(unpublished[0].event_id))
        remaining = outbox.fetch_unpublished()
        matching = [e for e in remaining if e.plan_id == event.plan_id]
        assert len(matching) == 0


# ===================================================================
# FIFO ordering
# ===================================================================


class TestFifoOrdering:
    def test_plan_events_fifo(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        _add_task(plan_repo, task_repo, outbox, pid)
        MarkPlanReadyUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))

        events = outbox.fetch_unpublished()
        timestamps = [e.occurred_at for e in events]
        assert timestamps == sorted(timestamps)

    def test_task_events_fifo(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)
        AssignTaskUseCase(task_repo, outbox).execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        StartTaskUseCase(task_repo).execute(TaskLifecycleRequest(task_id=tid))

        events = outbox.fetch_unpublished()
        timestamps = [e.occurred_at for e in events]
        assert timestamps == sorted(timestamps)

    def test_mixed_plan_and_task_events_fifo(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        _add_task(plan_repo, task_repo, outbox, pid)
        MarkPlanReadyUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))
        tid = _add_task(plan_repo, task_repo, outbox, pid)
        AssignTaskUseCase(task_repo, outbox).execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )

        events = outbox.fetch_unpublished()
        timestamps = [e.occurred_at for e in events]
        assert timestamps == sorted(timestamps)

    def test_multiple_plans_fifo(self, plan_repo, outbox, task_repo) -> None:
        p1 = _create_plan_id(plan_repo, outbox)
        p2 = _create_plan_id(plan_repo, outbox)
        CancelPlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=p1))
        ApprovePlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=p2))

        events = outbox.fetch_unpublished()
        timestamps = [e.occurred_at for e in events]
        assert timestamps == sorted(timestamps)


# ===================================================================
# Query filtering via use cases
# ===================================================================


class TestQueryFiltering:
    def test_list_plans_by_status(self, plan_repo, outbox) -> None:
        _create_plan_id(plan_repo, outbox)
        uc = ListPlansUseCase(plan_repo)
        result = uc.execute(ListPlansRequest(status="draft"))
        assert result.total >= 1

    def test_list_plans_by_priority(self, plan_repo, outbox) -> None:
        _create_plan_id(plan_repo, outbox)
        uc = ListPlansUseCase(plan_repo)
        result = uc.execute(ListPlansRequest(priority="normal"))
        assert result.total >= 1

    def test_list_plans_no_match(self, plan_repo, outbox) -> None:
        _create_plan_id(plan_repo, outbox)
        uc = ListPlansUseCase(plan_repo)
        result = uc.execute(ListPlansRequest(status="executing"))
        assert result.total == 0

    def test_get_plan_by_id(self, plan_repo, outbox) -> None:
        pid = _create_plan_id(plan_repo, outbox)
        uc = GetPlanUseCase(plan_repo)
        result = uc.execute(GetPlanRequest(plan_id=pid))
        assert result.plan_id == pid
        assert result.status == "draft"

    def test_get_plan_not_found(self, plan_repo, outbox) -> None:
        uc = GetPlanUseCase(plan_repo)
        with pytest.raises(PlanNotFoundError):
            uc.execute(GetPlanRequest(plan_id="00000000-0000-0000-0000-000000000000"))

    def test_list_tasks_by_status(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        _add_task(plan_repo, task_repo, outbox, pid)
        uc = ListTasksUseCase(task_repo)
        result = uc.execute(ListTasksRequest(status="pending"))
        assert result.total >= 1

    def test_list_tasks_by_agent(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)
        AssignTaskUseCase(task_repo, outbox).execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        uc = ListTasksUseCase(task_repo)
        result = uc.execute(ListTasksRequest(assigned_agent="research"))
        assert result.total >= 1

    def test_list_tasks_by_plan_id(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        _add_task(plan_repo, task_repo, outbox, pid)
        uc = ListTasksUseCase(task_repo)
        result = uc.execute(ListTasksRequest(plan_id=pid))
        assert result.total >= 1

    def test_list_tasks_no_match(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        _add_task(plan_repo, task_repo, outbox, pid)
        uc = ListTasksUseCase(task_repo)
        result = uc.execute(ListTasksRequest(status="assigned"))
        assert result.total == 0

    def test_get_task_by_id(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)
        uc = GetTaskUseCase(task_repo)
        result = uc.execute(GetTaskRequest(task_id=tid))
        assert result.task_id == tid
        assert result.status == "pending"

    def test_get_task_not_found(self, plan_repo, task_repo, outbox) -> None:
        uc = GetTaskUseCase(task_repo)
        with pytest.raises(TaskNotFoundError):
            uc.execute(GetTaskRequest(task_id="00000000-0000-0000-0000-000000000000"))


# ===================================================================
# Event coverage
# ===================================================================


class TestEventCoverage:
    def test_all_events_roundtrip_through_outbox(self, outbox) -> None:
        from backend.planner.domain.model import (
            PlanApproved,
            PlanCancelled,
            PlanCompleted,
            PlanExecutionStarted,
            PlanFailed,
            PlanReady,
            TaskAssigned,
            TaskCompleted,
            TaskCreated,
            TaskFailed,
            TaskId,
        )

        now = datetime.now(timezone.utc)
        pid = PlanId()
        tid = TaskId()

        events = [
            PlanCreated(plan_id=pid, user_request="test", goal="g", priority="normal", strategy="sequential", occurred_at=now),
            PlanApproved(plan_id=pid, occurred_at=now),
            PlanReady(plan_id=pid, occurred_at=now),
            PlanExecutionStarted(plan_id=pid, occurred_at=now),
            PlanFailed(plan_id=pid, failure_reason="fail", occurred_at=now),
            PlanCompleted(plan_id=pid, occurred_at=now),
            PlanCancelled(plan_id=pid, occurred_at=now),
            TaskCreated(task_id=tid, description="task", occurred_at=now),
            TaskAssigned(task_id=tid, assigned_agent=AgentType.RESEARCH, occurred_at=now),
            TaskCompleted(task_id=tid, occurred_at=now),
            TaskFailed(task_id=tid, failure_reason="fail", occurred_at=now),
        ]

        for event in events:
            outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 11

    def test_plan_created_event_fields(self, outbox) -> None:
        now = datetime.now(timezone.utc)
        pid = PlanId()
        event = PlanCreated(plan_id=pid, user_request="test", goal="g", priority="normal", strategy="sequential", occurred_at=now)
        outbox.append(event)
        events = outbox.fetch_unpublished()
        created = next(e for e in events if isinstance(e, PlanCreated))
        assert created.plan_id == pid
        assert created.user_request == "test"

    def test_task_created_event_fields(self, outbox) -> None:
        from backend.planner.domain.model import TaskCreated, TaskId

        tid = TaskId()
        event = TaskCreated(task_id=tid, description="test", occurred_at=datetime.now(timezone.utc))
        outbox.append(event)
        events = outbox.fetch_unpublished()
        created = next(e for e in events if isinstance(e, TaskCreated))
        assert created.task_id == tid
        assert created.description == "test"

    def test_plan_events_during_lifecycle(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_executing_plan(plan_repo, task_repo, outbox)
        CompletePlanUseCase(plan_repo, outbox).execute(PlanLifecycleRequest(plan_id=pid))

        events = outbox.fetch_unpublished()
        event_type_names = {type(e).__name__ for e in events}
        assert "PlanCreated" in event_type_names
        assert "PlanApproved" in event_type_names
        assert "PlanReady" in event_type_names
        assert "PlanExecutionStarted" in event_type_names
        assert "PlanCompleted" in event_type_names

    def test_task_events_during_lifecycle(self, plan_repo, task_repo, outbox) -> None:
        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)
        AssignTaskUseCase(task_repo, outbox).execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        StartTaskUseCase(task_repo).execute(TaskLifecycleRequest(task_id=tid))
        CompleteTaskUseCase(task_repo, outbox).execute(TaskLifecycleRequest(task_id=tid))

        events = outbox.fetch_unpublished()
        event_type_names = {type(e).__name__ for e in events}
        assert "TaskCreated" in event_type_names
        assert "TaskAssigned" in event_type_names
        assert "TaskCompleted" in event_type_names

    def test_plan_failed_event_has_reason(self, plan_repo, task_repo, outbox) -> None:
        from backend.planner.domain.model import PlanFailed

        pid = _create_executing_plan(plan_repo, task_repo, outbox)
        FailPlanUseCase(plan_repo, outbox).execute(
            FailPlanRequest(plan_id=pid, failure_reason="integration failure")
        )
        events = outbox.fetch_unpublished()
        failed = next(e for e in events if isinstance(e, PlanFailed))
        assert failed.failure_reason == "integration failure"

    def test_task_failed_event_has_reason(self, plan_repo, task_repo, outbox) -> None:
        from backend.planner.domain.model import TaskFailed

        pid = _create_planning_plan(plan_repo, outbox)
        tid = _add_task(plan_repo, task_repo, outbox, pid)
        AssignTaskUseCase(task_repo, outbox).execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        StartTaskUseCase(task_repo).execute(TaskLifecycleRequest(task_id=tid))
        FailTaskUseCase(task_repo, outbox).execute(
            FailTaskRequest(task_id=tid, failure_reason="task integration failure")
        )
        events = outbox.fetch_unpublished()
        failed = next(e for e in events if isinstance(e, TaskFailed))
        assert failed.failure_reason == "task integration failure"


# ===================================================================
# REST contract verification via HTTP
# ===================================================================


class TestRESTContract:
    def test_create_plan_201(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/plans",
            json={
                "user_request": "rest test",
                "goal": "verify",
                "priority": "normal",
                "strategy": "sequential",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "plan_id" in data
        assert data["status"] == "draft"

    def test_create_plan_422_invalid(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/plans",
            json={"user_request": "test", "priority": "invalid"},
        )
        assert resp.status_code == 422

    def test_get_plan_200(self, client) -> None:
        pid = _create_plan_http(client)
        resp = client.get(f"/api/v1/planner/plans/{pid}")
        assert resp.status_code == 200
        assert resp.json()["plan_id"] == pid

    def test_get_plan_404(self, client) -> None:
        resp = client.get("/api/v1/planner/plans/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_full_plan_lifecycle_via_http(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/plans",
            json={"user_request": "http lifecycle", "goal": "test"},
        )
        assert resp.status_code == 201
        pid = resp.json()["plan_id"]

        assert client.post(f"/api/v1/planner/plans/{pid}/approve").status_code == 200
        assert client.post(f"/api/v1/planner/plans/{pid}/planning").status_code == 200
        assert client.post(
            f"/api/v1/planner/plans/{pid}/tasks",
            json={"description": "task"},
        ).status_code == 201
        assert client.post(f"/api/v1/planner/plans/{pid}/ready").status_code == 200
        assert client.post(f"/api/v1/planner/plans/{pid}/execute").status_code == 200
        assert client.post(f"/api/v1/planner/plans/{pid}/complete").status_code == 200
        assert client.get(f"/api/v1/planner/plans/{pid}").json()["status"] == "completed"

    def test_full_task_lifecycle_via_http(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/plans",
            json={"user_request": "http task lifecycle", "goal": "test"},
        )
        assert resp.status_code == 201
        pid = resp.json()["plan_id"]
        client.post(f"/api/v1/planner/plans/{pid}/approve")
        client.post(f"/api/v1/planner/plans/{pid}/planning")
        resp = client.post(
            f"/api/v1/planner/plans/{pid}/tasks",
            json={"description": "task"},
        )
        assert resp.status_code == 201
        tid = resp.json()["task_id"]

        assert client.post(
            f"/api/v1/planner/tasks/{tid}/assign",
            json={"agent": "research"},
        ).status_code == 200
        assert client.post(f"/api/v1/planner/tasks/{tid}/start").status_code == 200
        assert client.post(f"/api/v1/planner/tasks/{tid}/complete").status_code == 200

    def test_plan_fail_via_http(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/plans",
            json={"user_request": "fail test", "goal": "test"},
        )
        assert resp.status_code == 201
        pid = resp.json()["plan_id"]
        client.post(f"/api/v1/planner/plans/{pid}/approve")
        client.post(f"/api/v1/planner/plans/{pid}/planning")
        client.post(f"/api/v1/planner/plans/{pid}/tasks", json={"description": "t"})
        client.post(f"/api/v1/planner/plans/{pid}/ready")
        client.post(f"/api/v1/planner/plans/{pid}/execute")
        resp = client.post(
            f"/api/v1/planner/plans/{pid}/fail",
            json={"failure_reason": "http failure"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_plans_list_200(self, client) -> None:
        resp = client.get("/api/v1/planner/plans")
        assert resp.status_code == 200
        assert "plans" in resp.json()
        assert "total" in resp.json()

    def test_tasks_list_200(self, client) -> None:
        resp = client.get("/api/v1/planner/tasks")
        assert resp.status_code == 200
        assert "tasks" in resp.json()
        assert "total" in resp.json()


def _create_plan_http(client) -> str:
    resp = client.post(
        "/api/v1/planner/plans",
        json={"user_request": "rest helper", "goal": "test"},
    )
    assert resp.status_code == 201
    return resp.json()["plan_id"]
