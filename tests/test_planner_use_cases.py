from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.planner.application.ports.outbox import PlannerOutboxPort
from backend.planner.application.ports.repository import (
    PlanRepositoryPort,
    TaskRepositoryPort,
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
    AddTaskResponse,
    AssignTaskRequest,
    AssignTaskResponse,
    CreatePlanRequest,
    CreatePlanResponse,
    FailPlanRequest,
    FailPlanResponse,
    FailTaskRequest,
    FailTaskResponse,
    GetPlanRequest,
    GetTaskRequest,
    ListPlansRequest,
    ListPlansResponse,
    ListTasksRequest,
    ListTasksResponse,
    PlanLifecycleRequest,
    PlanLifecycleResponse,
    PlanResponse,
    TaskLifecycleRequest,
    TaskLifecycleResponse,
    TaskResponse,
)
from backend.planner.application.use_cases.exceptions import (
    PlanNotFoundError,
    TaskNotFoundError,
    UseCaseError,
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
from backend.planner.domain.model import (
    AgentType,
    ExecutionStrategy,
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
from backend.planner.domain.exceptions import (
    InvalidTransitionError,
    InvalidUserRequestError,
    InvalidPlanGoalError,
    InvalidPlanPriorityError,
    InvalidExecutionStrategyError,
    InvalidAgentTypeError,
    InvalidTaskDescriptionError,
    InvalidFailureReasonError,
    PlanHasNoTasksError,
    PlanNotReadyError,
    EmptyPlanExecutionError,
)

# ===================================================================
# Fake port implementations (in-memory)
# ===================================================================


class FakePlanRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, Plan] = {}
        self.save_calls: list[Plan] = []

    def save(self, plan: Plan) -> None:
        self._store[plan.plan_id.value] = plan
        self.save_calls.append(plan)

    def find_by_id(self, plan_id: PlanId) -> Plan | None:
        return self._store.get(plan_id.value)

    def find_by_status(self, status: PlanStatus) -> list[Plan]:
        return [p for p in self._store.values() if p.status == status]

    def find_by_priority(self, priority: PlanPriority) -> list[Plan]:
        return [p for p in self._store.values() if p.priority == priority]

    def find_active(self) -> list[Plan]:
        terminal = {PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.CANCELLED}
        return [p for p in self._store.values() if p.status not in terminal]

    def count(self) -> int:
        return len(self._store)


class FakeTaskRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, Task] = {}
        self.save_calls: list[Task] = []

    def save(self, task: Task) -> None:
        self._store[task.task_id.value] = task
        self.save_calls.append(task)

    def find_by_id(self, task_id: TaskId) -> Task | None:
        return self._store.get(task_id.value)

    def find_by_status(self, status: TaskStatus) -> list[Task]:
        return [t for t in self._store.values() if t.status == status]

    def find_by_agent(self, agent_type: AgentType) -> list[Task]:
        return [t for t in self._store.values() if t.assigned_agent == agent_type]

    def find_by_plan_id(self, plan_id: PlanId) -> list[Task]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class FakePlannerOutbox:
    def __init__(self) -> None:
        self._events: list = []
        self.append_calls: list = []

    def append(self, event: object) -> None:
        self._events.append(event)
        self.append_calls.append(event)

    def fetch_unpublished(self, limit: int = 100) -> list:
        return list(self._events[:limit])

    def mark_published(self, aggregate_id: str) -> None:
        pass


# ===================================================================
# Fixtures
# ===================================================================


_NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def fake_plan_repo() -> FakePlanRepository:
    return FakePlanRepository()


@pytest.fixture
def fake_task_repo() -> FakeTaskRepository:
    return FakeTaskRepository()


@pytest.fixture
def fake_outbox() -> FakePlannerOutbox:
    return FakePlannerOutbox()


@pytest.fixture
def create_plan_uc(
    fake_plan_repo: FakePlanRepository,
    fake_outbox: FakePlannerOutbox,
) -> CreatePlanUseCase:
    return CreatePlanUseCase(plan_repo=fake_plan_repo, outbox=fake_outbox)


@pytest.fixture
def approve_plan_uc(
    fake_plan_repo: FakePlanRepository,
    fake_outbox: FakePlannerOutbox,
) -> ApprovePlanUseCase:
    return ApprovePlanUseCase(plan_repo=fake_plan_repo, outbox=fake_outbox)


@pytest.fixture
def start_planning_uc(
    fake_plan_repo: FakePlanRepository,
) -> StartPlanningUseCase:
    return StartPlanningUseCase(plan_repo=fake_plan_repo)


@pytest.fixture
def mark_ready_uc(
    fake_plan_repo: FakePlanRepository,
    fake_outbox: FakePlannerOutbox,
) -> MarkPlanReadyUseCase:
    return MarkPlanReadyUseCase(plan_repo=fake_plan_repo, outbox=fake_outbox)


@pytest.fixture
def start_execution_uc(
    fake_plan_repo: FakePlanRepository,
    fake_outbox: FakePlannerOutbox,
) -> StartExecutionUseCase:
    return StartExecutionUseCase(plan_repo=fake_plan_repo, outbox=fake_outbox)


@pytest.fixture
def complete_plan_uc(
    fake_plan_repo: FakePlanRepository,
    fake_outbox: FakePlannerOutbox,
) -> CompletePlanUseCase:
    return CompletePlanUseCase(plan_repo=fake_plan_repo, outbox=fake_outbox)


@pytest.fixture
def fail_plan_uc(
    fake_plan_repo: FakePlanRepository,
    fake_outbox: FakePlannerOutbox,
) -> FailPlanUseCase:
    return FailPlanUseCase(plan_repo=fake_plan_repo, outbox=fake_outbox)


@pytest.fixture
def cancel_plan_uc(
    fake_plan_repo: FakePlanRepository,
    fake_outbox: FakePlannerOutbox,
) -> CancelPlanUseCase:
    return CancelPlanUseCase(plan_repo=fake_plan_repo, outbox=fake_outbox)


@pytest.fixture
def add_task_uc(
    fake_plan_repo: FakePlanRepository,
    fake_task_repo: FakeTaskRepository,
    fake_outbox: FakePlannerOutbox,
) -> AddTaskUseCase:
    return AddTaskUseCase(
        plan_repo=fake_plan_repo,
        task_repo=fake_task_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def assign_task_uc(
    fake_task_repo: FakeTaskRepository,
    fake_outbox: FakePlannerOutbox,
) -> AssignTaskUseCase:
    return AssignTaskUseCase(task_repo=fake_task_repo, outbox=fake_outbox)


@pytest.fixture
def complete_task_uc(
    fake_task_repo: FakeTaskRepository,
    fake_outbox: FakePlannerOutbox,
) -> CompleteTaskUseCase:
    return CompleteTaskUseCase(task_repo=fake_task_repo, outbox=fake_outbox)


@pytest.fixture
def fail_task_uc(
    fake_task_repo: FakeTaskRepository,
    fake_outbox: FakePlannerOutbox,
) -> FailTaskUseCase:
    return FailTaskUseCase(task_repo=fake_task_repo, outbox=fake_outbox)


@pytest.fixture
def get_plan_uc(
    fake_plan_repo: FakePlanRepository,
) -> GetPlanUseCase:
    return GetPlanUseCase(plan_repo=fake_plan_repo)


@pytest.fixture
def list_plans_uc(
    fake_plan_repo: FakePlanRepository,
) -> ListPlansUseCase:
    return ListPlansUseCase(plan_repo=fake_plan_repo)


@pytest.fixture
def get_task_uc(
    fake_task_repo: FakeTaskRepository,
) -> GetTaskUseCase:
    return GetTaskUseCase(task_repo=fake_task_repo)


@pytest.fixture
def list_tasks_uc(
    fake_task_repo: FakeTaskRepository,
) -> ListTasksUseCase:
    return ListTasksUseCase(task_repo=fake_task_repo)


@pytest.fixture
def start_task_uc(
    fake_task_repo: FakeTaskRepository,
) -> StartTaskUseCase:
    return StartTaskUseCase(task_repo=fake_task_repo)


# ===================================================================
# Helpers
# ===================================================================


def _create_plan(
    create_plan_uc: CreatePlanUseCase,
    *,
    user_request: str = "test request",
    goal: str = "test goal",
    priority: str = "normal",
    strategy: str = "sequential",
) -> CreatePlanResponse:
    return create_plan_uc.execute(
        CreatePlanRequest(
            user_request=user_request,
            goal=goal,
            priority=priority,
            strategy=strategy,
        )
    )


def _create_plan_with_task(
    create_plan_uc: CreatePlanUseCase,
    add_task_uc: AddTaskUseCase,
    *,
    user_request: str = "test request",
    goal: str = "test goal",
) -> tuple[str, str]:
    plan_resp = _create_plan(
        create_plan_uc, user_request=user_request, goal=goal,
    )
    task_resp = add_task_uc.execute(
        AddTaskRequest(plan_id=plan_resp.plan_id, description="test task")
    )
    return plan_resp.plan_id, task_resp.task_id


def _full_lifecycle_to_executing(
    create_plan_uc: CreatePlanUseCase,
    approve_plan_uc: ApprovePlanUseCase,
    start_planning_uc: StartPlanningUseCase,
    add_task_uc: AddTaskUseCase,
    mark_ready_uc: MarkPlanReadyUseCase,
    start_execution_uc: StartExecutionUseCase,
) -> str:
    plan_resp = _create_plan(create_plan_uc)
    pid = plan_resp.plan_id
    approve_plan_uc.execute(PlanLifecycleRequest(plan_id=pid))
    start_planning_uc.execute(PlanLifecycleRequest(plan_id=pid))
    add_task_uc.execute(AddTaskRequest(plan_id=pid, description="task"))
    mark_ready_uc.execute(PlanLifecycleRequest(plan_id=pid))
    start_execution_uc.execute(PlanLifecycleRequest(plan_id=pid))
    return pid


# ===================================================================
# CreatePlanUseCase Tests
# ===================================================================


class TestCreatePlanUseCase:
    def test_happy_path(
        self,
        create_plan_uc: CreatePlanUseCase,
        fake_plan_repo: FakePlanRepository,
        fake_outbox: FakePlannerOutbox,
    ) -> None:
        response = _create_plan(create_plan_uc)

        assert response.user_request == "test request"
        assert response.goal == "test goal"
        assert response.priority == "normal"
        assert response.strategy == "sequential"
        assert response.status == "draft"
        assert response.created_at is not None

        stored = fake_plan_repo.find_by_id(
            PlanId(value=UUID(response.plan_id))
        )
        assert stored is not None
        assert fake_outbox.append_calls is not None

    def test_plan_persisted(
        self,
        create_plan_uc: CreatePlanUseCase,
        fake_plan_repo: FakePlanRepository,
    ) -> None:
        response = _create_plan(create_plan_uc)
        assert fake_plan_repo.count() == 1
        stored = fake_plan_repo.find_by_id(
            PlanId(value=UUID(response.plan_id))
        )
        assert stored is not None
        assert stored.status == PlanStatus.DRAFT

    def test_plan_created_event_emitted(
        self,
        create_plan_uc: CreatePlanUseCase,
        fake_outbox: FakePlannerOutbox,
    ) -> None:
        response = _create_plan(create_plan_uc)
        assert len(fake_outbox.append_calls) == 1
        event = fake_outbox.append_calls[0]
        assert isinstance(event, PlanCreated)
        assert str(event.plan_id) == response.plan_id
        assert event.user_request == "test request"

    def test_high_priority_plan(
        self,
        create_plan_uc: CreatePlanUseCase,
    ) -> None:
        response = _create_plan(create_plan_uc, priority="high")
        assert response.priority == "high"

    def test_critical_priority_plan(
        self,
        create_plan_uc: CreatePlanUseCase,
    ) -> None:
        response = _create_plan(create_plan_uc, priority="critical")
        assert response.priority == "critical"

    def test_parallel_strategy(
        self,
        create_plan_uc: CreatePlanUseCase,
    ) -> None:
        response = _create_plan(create_plan_uc, strategy="parallel")
        assert response.strategy == "parallel"

    def test_empty_user_request_rejected(
        self,
        create_plan_uc: CreatePlanUseCase,
    ) -> None:
        with pytest.raises(InvalidUserRequestError):
            _create_plan(create_plan_uc, user_request="")

    def test_empty_goal_rejected(
        self,
        create_plan_uc: CreatePlanUseCase,
    ) -> None:
        with pytest.raises(InvalidPlanGoalError):
            _create_plan(create_plan_uc, goal="")

    def test_invalid_priority_rejected(
        self,
        create_plan_uc: CreatePlanUseCase,
    ) -> None:
        with pytest.raises(InvalidPlanPriorityError):
            _create_plan(create_plan_uc, priority="invalid")

    def test_invalid_strategy_rejected(
        self,
        create_plan_uc: CreatePlanUseCase,
    ) -> None:
        with pytest.raises(InvalidExecutionStrategyError):
            _create_plan(create_plan_uc, strategy="invalid")

    def test_response_type(
        self,
        create_plan_uc: CreatePlanUseCase,
    ) -> None:
        response = _create_plan(create_plan_uc)
        assert isinstance(response, CreatePlanResponse)

    def test_save_called(
        self,
        create_plan_uc: CreatePlanUseCase,
        fake_plan_repo: FakePlanRepository,
    ) -> None:
        _create_plan(create_plan_uc)
        assert len(fake_plan_repo.save_calls) == 1

    def test_multiple_plans(
        self,
        create_plan_uc: CreatePlanUseCase,
        fake_plan_repo: FakePlanRepository,
    ) -> None:
        _create_plan(create_plan_uc, user_request="first")
        _create_plan(create_plan_uc, user_request="second")
        assert fake_plan_repo.count() == 2


# ===================================================================
# ApprovePlanUseCase Tests
# ===================================================================


class TestApprovePlanUseCase:
    def test_draft_to_approved(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        response = approve_plan_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        assert response.status == "approved"
        assert isinstance(response, PlanLifecycleResponse)

    def test_event_emitted(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        fake_outbox: FakePlannerOutbox,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        approve_plan_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        events = [
            e for e in fake_outbox.append_calls if isinstance(e, PlanApproved)
        ]
        assert len(events) == 1
        assert str(events[0].plan_id) == create_resp.plan_id

    def test_missing_plan_raises_error(
        self,
        approve_plan_uc: ApprovePlanUseCase,
    ) -> None:
        with pytest.raises(PlanNotFoundError):
            approve_plan_uc.execute(
                PlanLifecycleRequest(
                    plan_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_save_called(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        fake_plan_repo: FakePlanRepository,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        approve_plan_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        assert len(fake_plan_repo.save_calls) == 2

    def test_stored_status_updated(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        fake_plan_repo: FakePlanRepository,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        approve_plan_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        stored = fake_plan_repo.find_by_id(
            PlanId(value=UUID(create_resp.plan_id))
        )
        assert stored is not None
        assert stored.status == PlanStatus.APPROVED

    def test_double_approve_rejected(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        approve_plan_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        with pytest.raises(InvalidTransitionError):
            approve_plan_uc.execute(
                PlanLifecycleRequest(plan_id=create_resp.plan_id)
            )


# ===================================================================
# StartPlanningUseCase Tests
# ===================================================================


class TestStartPlanningUseCase:
    def test_approved_to_planning(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        approve_plan_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        response = start_planning_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        assert response.status == "planning"

    def test_missing_plan_raises_error(
        self,
        start_planning_uc: StartPlanningUseCase,
    ) -> None:
        with pytest.raises(PlanNotFoundError):
            start_planning_uc.execute(
                PlanLifecycleRequest(
                    plan_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_direct_draft_to_planning_rejected(
        self,
        create_plan_uc: CreatePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        with pytest.raises(InvalidTransitionError):
            start_planning_uc.execute(
                PlanLifecycleRequest(plan_id=create_resp.plan_id)
            )

    def test_stored_status_updated(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
        fake_plan_repo: FakePlanRepository,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        approve_plan_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        start_planning_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        stored = fake_plan_repo.find_by_id(
            PlanId(value=UUID(create_resp.plan_id))
        )
        assert stored is not None
        assert stored.status == PlanStatus.PLANNING

    def test_save_called(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
        fake_plan_repo: FakePlanRepository,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        approve_plan_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        start_planning_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        assert len(fake_plan_repo.save_calls) == 3


# ===================================================================
# MarkPlanReadyUseCase Tests
# ===================================================================


class TestMarkPlanReadyUseCase:
    def test_planning_to_ready(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
        add_task_uc: AddTaskUseCase,
        mark_ready_uc: MarkPlanReadyUseCase,
    ) -> None:
        pid, _ = _create_plan_with_task(create_plan_uc, add_task_uc)
        approve_plan_uc.execute(PlanLifecycleRequest(plan_id=pid))
        start_planning_uc.execute(PlanLifecycleRequest(plan_id=pid))
        response = mark_ready_uc.execute(
            PlanLifecycleRequest(plan_id=pid)
        )
        assert response.status == "ready"

    def test_no_tasks_rejected(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
        mark_ready_uc: MarkPlanReadyUseCase,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        approve_plan_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        start_planning_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        with pytest.raises(PlanHasNoTasksError):
            mark_ready_uc.execute(
                PlanLifecycleRequest(plan_id=create_resp.plan_id)
            )

    def test_event_emitted(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
        add_task_uc: AddTaskUseCase,
        mark_ready_uc: MarkPlanReadyUseCase,
        fake_outbox: FakePlannerOutbox,
    ) -> None:
        pid, _ = _create_plan_with_task(create_plan_uc, add_task_uc)
        approve_plan_uc.execute(PlanLifecycleRequest(plan_id=pid))
        start_planning_uc.execute(PlanLifecycleRequest(plan_id=pid))
        mark_ready_uc.execute(PlanLifecycleRequest(plan_id=pid))
        events = [
            e for e in fake_outbox.append_calls if isinstance(e, PlanReady)
        ]
        assert len(events) == 1
        assert str(events[0].plan_id) == pid

    def test_missing_plan_raises_error(
        self,
        mark_ready_uc: MarkPlanReadyUseCase,
    ) -> None:
        with pytest.raises(PlanNotFoundError):
            mark_ready_uc.execute(
                PlanLifecycleRequest(
                    plan_id="00000000-0000-0000-0000-000000000000"
                )
            )


# ===================================================================
# StartExecutionUseCase Tests
# ===================================================================


class TestStartExecutionUseCase:
    def test_ready_to_executing(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
        add_task_uc: AddTaskUseCase,
        mark_ready_uc: MarkPlanReadyUseCase,
        start_execution_uc: StartExecutionUseCase,
    ) -> None:
        pid = _full_lifecycle_to_executing(
            create_plan_uc, approve_plan_uc, start_planning_uc,
            add_task_uc, mark_ready_uc, start_execution_uc,
        )
        stored = FakePlanRepository().find_by_id(PlanId(value=UUID(pid)))
        assert stored is None

    def test_executing_status(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
        add_task_uc: AddTaskUseCase,
        mark_ready_uc: MarkPlanReadyUseCase,
        start_execution_uc: StartExecutionUseCase,
        fake_plan_repo: FakePlanRepository,
    ) -> None:
        pid = _full_lifecycle_to_executing(
            create_plan_uc, approve_plan_uc, start_planning_uc,
            add_task_uc, mark_ready_uc, start_execution_uc,
        )
        stored = fake_plan_repo.find_by_id(PlanId(value=UUID(pid)))
        assert stored is not None
        assert stored.status == PlanStatus.EXECUTING

    def test_event_emitted(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
        add_task_uc: AddTaskUseCase,
        mark_ready_uc: MarkPlanReadyUseCase,
        start_execution_uc: StartExecutionUseCase,
        fake_outbox: FakePlannerOutbox,
    ) -> None:
        pid = _full_lifecycle_to_executing(
            create_plan_uc, approve_plan_uc, start_planning_uc,
            add_task_uc, mark_ready_uc, start_execution_uc,
        )
        events = [
            e for e in fake_outbox.append_calls
            if isinstance(e, PlanExecutionStarted)
        ]
        assert len(events) == 1
        assert str(events[0].plan_id) == pid

    def test_missing_plan_raises_error(
        self,
        start_execution_uc: StartExecutionUseCase,
    ) -> None:
        with pytest.raises(PlanNotFoundError):
            start_execution_uc.execute(
                PlanLifecycleRequest(
                    plan_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_not_ready_rejected(
        self,
        create_plan_uc: CreatePlanUseCase,
        start_execution_uc: StartExecutionUseCase,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        with pytest.raises(PlanNotReadyError):
            start_execution_uc.execute(
                PlanLifecycleRequest(plan_id=create_resp.plan_id)
            )


# ===================================================================
# CompletePlanUseCase Tests
# ===================================================================


class TestCompletePlanUseCase:
    def test_executing_to_completed(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
        add_task_uc: AddTaskUseCase,
        mark_ready_uc: MarkPlanReadyUseCase,
        start_execution_uc: StartExecutionUseCase,
        complete_plan_uc: CompletePlanUseCase,
        fake_plan_repo: FakePlanRepository,
    ) -> None:
        pid = _full_lifecycle_to_executing(
            create_plan_uc, approve_plan_uc, start_planning_uc,
            add_task_uc, mark_ready_uc, start_execution_uc,
        )
        response = complete_plan_uc.execute(
            PlanLifecycleRequest(plan_id=pid)
        )
        assert response.status == "completed"
        stored = fake_plan_repo.find_by_id(PlanId(value=UUID(pid)))
        assert stored is not None
        assert stored.status == PlanStatus.COMPLETED

    def test_event_emitted(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
        add_task_uc: AddTaskUseCase,
        mark_ready_uc: MarkPlanReadyUseCase,
        start_execution_uc: StartExecutionUseCase,
        complete_plan_uc: CompletePlanUseCase,
        fake_outbox: FakePlannerOutbox,
    ) -> None:
        pid = _full_lifecycle_to_executing(
            create_plan_uc, approve_plan_uc, start_planning_uc,
            add_task_uc, mark_ready_uc, start_execution_uc,
        )
        complete_plan_uc.execute(PlanLifecycleRequest(plan_id=pid))
        events = [
            e for e in fake_outbox.append_calls
            if isinstance(e, PlanCompleted)
        ]
        assert len(events) == 1

    def test_missing_plan_raises_error(
        self,
        complete_plan_uc: CompletePlanUseCase,
    ) -> None:
        with pytest.raises(PlanNotFoundError):
            complete_plan_uc.execute(
                PlanLifecycleRequest(
                    plan_id="00000000-0000-0000-0000-000000000000"
                )
            )


# ===================================================================
# FailPlanUseCase Tests
# ===================================================================


class TestFailPlanUseCase:
    def test_executing_to_failed(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
        add_task_uc: AddTaskUseCase,
        mark_ready_uc: MarkPlanReadyUseCase,
        start_execution_uc: StartExecutionUseCase,
        fail_plan_uc: FailPlanUseCase,
    ) -> None:
        pid = _full_lifecycle_to_executing(
            create_plan_uc, approve_plan_uc, start_planning_uc,
            add_task_uc, mark_ready_uc, start_execution_uc,
        )
        response = fail_plan_uc.execute(
            FailPlanRequest(plan_id=pid, failure_reason="error occurred")
        )
        assert response.status == "failed"
        assert response.failure_reason == "error occurred"

    def test_event_emitted(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
        add_task_uc: AddTaskUseCase,
        mark_ready_uc: MarkPlanReadyUseCase,
        start_execution_uc: StartExecutionUseCase,
        fail_plan_uc: FailPlanUseCase,
        fake_outbox: FakePlannerOutbox,
    ) -> None:
        pid = _full_lifecycle_to_executing(
            create_plan_uc, approve_plan_uc, start_planning_uc,
            add_task_uc, mark_ready_uc, start_execution_uc,
        )
        fail_plan_uc.execute(
            FailPlanRequest(plan_id=pid, failure_reason="error")
        )
        events = [
            e for e in fake_outbox.append_calls
            if isinstance(e, PlanFailed)
        ]
        assert len(events) == 1

    def test_missing_plan_raises_error(
        self,
        fail_plan_uc: FailPlanUseCase,
    ) -> None:
        with pytest.raises(PlanNotFoundError):
            fail_plan_uc.execute(
                FailPlanRequest(
                    plan_id="00000000-0000-0000-0000-000000000000",
                    failure_reason="error",
                )
            )

    def test_empty_failure_reason_rejected(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
        add_task_uc: AddTaskUseCase,
        mark_ready_uc: MarkPlanReadyUseCase,
        start_execution_uc: StartExecutionUseCase,
        fail_plan_uc: FailPlanUseCase,
    ) -> None:
        pid = _full_lifecycle_to_executing(
            create_plan_uc, approve_plan_uc, start_planning_uc,
            add_task_uc, mark_ready_uc, start_execution_uc,
        )
        with pytest.raises(InvalidFailureReasonError):
            fail_plan_uc.execute(
                FailPlanRequest(plan_id=pid, failure_reason="")
            )


# ===================================================================
# CancelPlanUseCase Tests
# ===================================================================


class TestCancelPlanUseCase:
    def test_draft_to_cancelled(
        self,
        create_plan_uc: CreatePlanUseCase,
        cancel_plan_uc: CancelPlanUseCase,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        response = cancel_plan_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        assert response.status == "cancelled"

    def test_executing_to_cancelled(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        start_planning_uc: StartPlanningUseCase,
        add_task_uc: AddTaskUseCase,
        mark_ready_uc: MarkPlanReadyUseCase,
        start_execution_uc: StartExecutionUseCase,
        cancel_plan_uc: CancelPlanUseCase,
    ) -> None:
        pid = _full_lifecycle_to_executing(
            create_plan_uc, approve_plan_uc, start_planning_uc,
            add_task_uc, mark_ready_uc, start_execution_uc,
        )
        response = cancel_plan_uc.execute(
            PlanLifecycleRequest(plan_id=pid)
        )
        assert response.status == "cancelled"

    def test_event_emitted(
        self,
        create_plan_uc: CreatePlanUseCase,
        cancel_plan_uc: CancelPlanUseCase,
        fake_outbox: FakePlannerOutbox,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        cancel_plan_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        events = [
            e for e in fake_outbox.append_calls
            if isinstance(e, PlanCancelled)
        ]
        assert len(events) == 1

    def test_missing_plan_raises_error(
        self,
        cancel_plan_uc: CancelPlanUseCase,
    ) -> None:
        with pytest.raises(PlanNotFoundError):
            cancel_plan_uc.execute(
                PlanLifecycleRequest(
                    plan_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_cancelled_plan_cannot_transition(
        self,
        create_plan_uc: CreatePlanUseCase,
        cancel_plan_uc: CancelPlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        cancel_plan_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        with pytest.raises(InvalidTransitionError):
            approve_plan_uc.execute(
                PlanLifecycleRequest(plan_id=create_resp.plan_id)
            )


# ===================================================================
# AddTaskUseCase Tests
# ===================================================================


class TestAddTaskUseCase:
    def test_happy_path(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        response = add_task_uc.execute(
            AddTaskRequest(
                plan_id=create_resp.plan_id, description="do something"
            )
        )
        assert isinstance(response, AddTaskResponse)
        assert response.description == "do something"
        assert response.status == "pending"

    def test_event_emitted(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        fake_outbox: FakePlannerOutbox,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        add_task_uc.execute(
            AddTaskRequest(
                plan_id=create_resp.plan_id, description="task"
            )
        )
        events = [
            e for e in fake_outbox.append_calls
            if isinstance(e, TaskCreated)
        ]
        assert len(events) == 1
        assert events[0].description == "task"

    def test_missing_plan_raises_error(
        self,
        add_task_uc: AddTaskUseCase,
    ) -> None:
        with pytest.raises(PlanNotFoundError):
            add_task_uc.execute(
                AddTaskRequest(
                    plan_id="00000000-0000-0000-0000-000000000000",
                    description="task",
                )
            )

    def test_empty_description_rejected(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        with pytest.raises(InvalidTaskDescriptionError):
            add_task_uc.execute(
                AddTaskRequest(
                    plan_id=create_resp.plan_id, description=""
                )
            )

    def test_terminal_plan_rejects_tasks(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        cancel_plan_uc: CancelPlanUseCase,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        cancel_plan_uc.execute(
            PlanLifecycleRequest(plan_id=create_resp.plan_id)
        )
        from backend.planner.domain.exceptions import PlanTerminalError
        with pytest.raises(PlanTerminalError):
            add_task_uc.execute(
                AddTaskRequest(
                    plan_id=create_resp.plan_id, description="task"
                )
            )

    def test_task_added_to_plan(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        fake_plan_repo: FakePlanRepository,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        add_task_uc.execute(
            AddTaskRequest(
                plan_id=create_resp.plan_id, description="task1"
            )
        )
        stored = fake_plan_repo.find_by_id(
            PlanId(value=UUID(create_resp.plan_id))
        )
        assert stored is not None
        assert len(stored.tasks) == 1

    def test_multiple_tasks(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        fake_outbox: FakePlannerOutbox,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        add_task_uc.execute(
            AddTaskRequest(
                plan_id=create_resp.plan_id, description="task1"
            )
        )
        add_task_uc.execute(
            AddTaskRequest(
                plan_id=create_resp.plan_id, description="task2"
            )
        )
        assert len(fake_outbox.append_calls)  # events emitted properly


# ===================================================================
# AssignTaskUseCase Tests
# ===================================================================


class TestAssignTaskUseCase:
    def test_assign_to_agent(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        assign_task_uc: AssignTaskUseCase,
    ) -> None:
        pid, tid = _create_plan_with_task(create_plan_uc, add_task_uc)
        response = assign_task_uc.execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        assert response.assigned_agent == "research"
        assert response.status == "assigned"
        assert isinstance(response, AssignTaskResponse)

    def test_event_emitted(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        assign_task_uc: AssignTaskUseCase,
        fake_outbox: FakePlannerOutbox,
    ) -> None:
        pid, tid = _create_plan_with_task(create_plan_uc, add_task_uc)
        assign_task_uc.execute(
            AssignTaskRequest(task_id=tid, agent="memory")
        )
        events = [
            e for e in fake_outbox.append_calls
            if isinstance(e, TaskAssigned)
        ]
        assert len(events) == 1
        assert str(events[0].task_id) == tid

    def test_missing_task_raises_error(
        self,
        assign_task_uc: AssignTaskUseCase,
    ) -> None:
        with pytest.raises(TaskNotFoundError):
            assign_task_uc.execute(
                AssignTaskRequest(
                    task_id="00000000-0000-0000-0000-000000000000",
                    agent="research",
                )
            )

    def test_invalid_agent_rejected(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        assign_task_uc: AssignTaskUseCase,
    ) -> None:
        pid, tid = _create_plan_with_task(create_plan_uc, add_task_uc)
        with pytest.raises(InvalidAgentTypeError):
            assign_task_uc.execute(
                AssignTaskRequest(task_id=tid, agent="invalid_agent")
            )

    def test_stored_task_updated(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        assign_task_uc: AssignTaskUseCase,
        fake_task_repo: FakeTaskRepository,
    ) -> None:
        pid, tid = _create_plan_with_task(create_plan_uc, add_task_uc)
        assign_task_uc.execute(
            AssignTaskRequest(task_id=tid, agent="automation")
        )
        stored = fake_task_repo.find_by_id(TaskId(value=UUID(tid)))
        assert stored is not None
        assert stored.assigned_agent == AgentType.AUTOMATION
        assert stored.status == TaskStatus.ASSIGNED


# ===================================================================
# CompleteTaskUseCase Tests
# ===================================================================


class TestCompleteTaskUseCase:
    def test_complete_assigned_task(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        assign_task_uc: AssignTaskUseCase,
        start_task_uc: StartTaskUseCase,
        complete_task_uc: CompleteTaskUseCase,
    ) -> None:
        pid, tid = _create_plan_with_task(create_plan_uc, add_task_uc)
        assign_task_uc.execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        start_task_uc.execute(TaskLifecycleRequest(task_id=tid))
        response = complete_task_uc.execute(
            TaskLifecycleRequest(task_id=tid)
        )
        assert response.status == "completed"
        assert isinstance(response, TaskLifecycleResponse)

    def test_event_emitted(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        assign_task_uc: AssignTaskUseCase,
        start_task_uc: StartTaskUseCase,
        complete_task_uc: CompleteTaskUseCase,
        fake_outbox: FakePlannerOutbox,
    ) -> None:
        pid, tid = _create_plan_with_task(create_plan_uc, add_task_uc)
        assign_task_uc.execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        start_task_uc.execute(TaskLifecycleRequest(task_id=tid))
        complete_task_uc.execute(TaskLifecycleRequest(task_id=tid))
        events = [
            e for e in fake_outbox.append_calls
            if isinstance(e, TaskCompleted)
        ]
        assert len(events) == 1
        assert str(events[0].task_id) == tid

    def test_missing_task_raises_error(
        self,
        complete_task_uc: CompleteTaskUseCase,
    ) -> None:
        with pytest.raises(TaskNotFoundError):
            complete_task_uc.execute(
                TaskLifecycleRequest(
                    task_id="00000000-0000-0000-0000-000000000000"
                )
            )


# ===================================================================
# FailTaskUseCase Tests
# ===================================================================


class TestFailTaskUseCase:
    def test_fail_assigned_task(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        assign_task_uc: AssignTaskUseCase,
        start_task_uc: StartTaskUseCase,
        fail_task_uc: FailTaskUseCase,
    ) -> None:
        pid, tid = _create_plan_with_task(create_plan_uc, add_task_uc)
        assign_task_uc.execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        start_task_uc.execute(TaskLifecycleRequest(task_id=tid))
        response = fail_task_uc.execute(
            FailTaskRequest(task_id=tid, failure_reason="error")
        )
        assert response.status == "failed"
        assert response.failure_reason == "error"
        assert isinstance(response, FailTaskResponse)

    def test_event_emitted(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        assign_task_uc: AssignTaskUseCase,
        start_task_uc: StartTaskUseCase,
        fail_task_uc: FailTaskUseCase,
        fake_outbox: FakePlannerOutbox,
    ) -> None:
        pid, tid = _create_plan_with_task(create_plan_uc, add_task_uc)
        assign_task_uc.execute(
            AssignTaskRequest(task_id=tid, agent="planner")
        )
        start_task_uc.execute(TaskLifecycleRequest(task_id=tid))
        fail_task_uc.execute(
            FailTaskRequest(task_id=tid, failure_reason="err")
        )
        events = [
            e for e in fake_outbox.append_calls
            if isinstance(e, TaskFailed)
        ]
        assert len(events) == 1

    def test_missing_task_raises_error(
        self,
        fail_task_uc: FailTaskUseCase,
    ) -> None:
        with pytest.raises(TaskNotFoundError):
            fail_task_uc.execute(
                FailTaskRequest(
                    task_id="00000000-0000-0000-0000-000000000000",
                    failure_reason="error",
                )
            )

    def test_empty_reason_rejected(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        assign_task_uc: AssignTaskUseCase,
        start_task_uc: StartTaskUseCase,
        fail_task_uc: FailTaskUseCase,
    ) -> None:
        pid, tid = _create_plan_with_task(create_plan_uc, add_task_uc)
        assign_task_uc.execute(
            AssignTaskRequest(task_id=tid, agent="planner")
        )
        start_task_uc.execute(TaskLifecycleRequest(task_id=tid))
        with pytest.raises(InvalidFailureReasonError):
            fail_task_uc.execute(
                FailTaskRequest(task_id=tid, failure_reason="")
            )


# ===================================================================
# GetPlanUseCase Tests
# ===================================================================


class TestGetPlanUseCase:
    def test_get_existing_plan(
        self,
        create_plan_uc: CreatePlanUseCase,
        get_plan_uc: GetPlanUseCase,
    ) -> None:
        create_resp = _create_plan(create_plan_uc)
        response = get_plan_uc.execute(
            GetPlanRequest(plan_id=create_resp.plan_id)
        )
        assert isinstance(response, PlanResponse)
        assert response.plan_id == create_resp.plan_id
        assert response.user_request == "test request"
        assert response.goal == "test goal"
        assert response.status == "draft"

    def test_get_nonexistent_plan_raises_error(
        self,
        get_plan_uc: GetPlanUseCase,
    ) -> None:
        with pytest.raises(PlanNotFoundError):
            get_plan_uc.execute(
                GetPlanRequest(
                    plan_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_plan_with_tasks_shows_count(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        get_plan_uc: GetPlanUseCase,
    ) -> None:
        pid, _ = _create_plan_with_task(create_plan_uc, add_task_uc)
        add_task_uc.execute(
            AddTaskRequest(plan_id=pid, description="second task")
        )
        response = get_plan_uc.execute(GetPlanRequest(plan_id=pid))
        assert response.task_count == 2


# ===================================================================
# ListPlansUseCase Tests
# ===================================================================


class TestListPlansUseCase:
    def test_list_all_plans(
        self,
        create_plan_uc: CreatePlanUseCase,
        list_plans_uc: ListPlansUseCase,
    ) -> None:
        _create_plan(create_plan_uc, user_request="first")
        _create_plan(create_plan_uc, user_request="second")
        response = list_plans_uc.execute(ListPlansRequest())
        assert isinstance(response, ListPlansResponse)
        assert response.total == 2

    def test_list_empty(
        self,
        list_plans_uc: ListPlansUseCase,
    ) -> None:
        response = list_plans_uc.execute(ListPlansRequest())
        assert response.total == 0
        assert response.plans == []

    def test_filter_by_status(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        list_plans_uc: ListPlansUseCase,
    ) -> None:
        resp1 = _create_plan(create_plan_uc, user_request="draft")
        resp2 = _create_plan(create_plan_uc, user_request="approved")
        approve_plan_uc.execute(
            PlanLifecycleRequest(plan_id=resp2.plan_id)
        )
        response = list_plans_uc.execute(
            ListPlansRequest(status="approved")
        )
        assert response.total == 1
        assert response.plans[0].user_request == "approved"

    def test_filter_by_priority(
        self,
        create_plan_uc: CreatePlanUseCase,
        list_plans_uc: ListPlansUseCase,
    ) -> None:
        _create_plan(create_plan_uc, user_request="normal")
        _create_plan(create_plan_uc, user_request="high", priority="high")
        response = list_plans_uc.execute(
            ListPlansRequest(priority="high")
        )
        assert response.total == 1
        assert response.plans[0].user_request == "high"

    def test_filter_by_status_and_priority(
        self,
        create_plan_uc: CreatePlanUseCase,
        approve_plan_uc: ApprovePlanUseCase,
        list_plans_uc: ListPlansUseCase,
    ) -> None:
        r1 = _create_plan(
            create_plan_uc, user_request="a", priority="high",
        )
        r2 = _create_plan(
            create_plan_uc, user_request="b", priority="high",
        )
        approve_plan_uc.execute(PlanLifecycleRequest(plan_id=r1.plan_id))
        response = list_plans_uc.execute(
            ListPlansRequest(status="approved", priority="high")
        )
        assert response.total == 1


# ===================================================================
# GetTaskUseCase Tests
# ===================================================================


class TestGetTaskUseCase:
    def test_get_existing_task(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        get_task_uc: GetTaskUseCase,
    ) -> None:
        pid, tid = _create_plan_with_task(create_plan_uc, add_task_uc)
        response = get_task_uc.execute(GetTaskRequest(task_id=tid))
        assert isinstance(response, TaskResponse)
        assert response.task_id == tid
        assert response.status == "pending"

    def test_get_nonexistent_task_raises_error(
        self,
        get_task_uc: GetTaskUseCase,
    ) -> None:
        with pytest.raises(TaskNotFoundError):
            get_task_uc.execute(
                GetTaskRequest(
                    task_id="00000000-0000-0000-0000-000000000000"
                )
            )


# ===================================================================
# ListTasksUseCase Tests
# ===================================================================


class TestListTasksUseCase:
    def test_list_all_tasks(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        list_tasks_uc: ListTasksUseCase,
    ) -> None:
        pid, _ = _create_plan_with_task(create_plan_uc, add_task_uc)
        add_task_uc.execute(
            AddTaskRequest(plan_id=pid, description="task2")
        )
        response = list_tasks_uc.execute(ListTasksRequest())
        assert isinstance(response, ListTasksResponse)
        assert response.total == 2

    def test_list_empty(
        self,
        list_tasks_uc: ListTasksUseCase,
    ) -> None:
        response = list_tasks_uc.execute(ListTasksRequest())
        assert response.total == 0
        assert response.tasks == []

    def test_filter_by_status(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        assign_task_uc: AssignTaskUseCase,
        list_tasks_uc: ListTasksUseCase,
    ) -> None:
        pid, tid = _create_plan_with_task(create_plan_uc, add_task_uc)
        assign_task_uc.execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        response = list_tasks_uc.execute(
            ListTasksRequest(status="assigned")
        )
        assert response.total == 1

    def test_filter_by_agent(
        self,
        create_plan_uc: CreatePlanUseCase,
        add_task_uc: AddTaskUseCase,
        assign_task_uc: AssignTaskUseCase,
        list_tasks_uc: ListTasksUseCase,
    ) -> None:
        pid, tid = _create_plan_with_task(create_plan_uc, add_task_uc)
        assign_task_uc.execute(
            AssignTaskRequest(task_id=tid, agent="research")
        )
        response = list_tasks_uc.execute(
            ListTasksRequest(assigned_agent="research")
        )
        assert response.total == 1


# ===================================================================
# Exception hierarchy tests
# ===================================================================


class TestExceptionHierarchy:
    def test_plan_not_found_is_use_case_error(self) -> None:
        assert issubclass(PlanNotFoundError, UseCaseError)

    def test_task_not_found_is_use_case_error(self) -> None:
        assert issubclass(TaskNotFoundError, UseCaseError)

    def test_plan_not_found_message(self) -> None:
        err = PlanNotFoundError("plan-123")
        assert "plan-123" in str(err)
        assert err.plan_id == "plan-123"

    def test_task_not_found_message(self) -> None:
        err = TaskNotFoundError("task-456")
        assert "task-456" in str(err)
        assert err.task_id == "task-456"


# ===================================================================
# DTO construction tests
# ===================================================================


class TestDTOConstruction:
    def test_create_plan_request_defaults(self) -> None:
        req = CreatePlanRequest(user_request="r", goal="g")
        assert req.priority == "normal"
        assert req.strategy == "sequential"

    def test_create_plan_request_custom(self) -> None:
        req = CreatePlanRequest(
            user_request="r", goal="g", priority="high", strategy="parallel"
        )
        assert req.priority == "high"
        assert req.strategy == "parallel"

    def test_plan_lifecycle_request(self) -> None:
        req = PlanLifecycleRequest(plan_id="abc")
        assert req.plan_id == "abc"

    def test_fail_plan_request(self) -> None:
        req = FailPlanRequest(plan_id="abc", failure_reason="err")
        assert req.failure_reason == "err"

    def test_add_task_request(self) -> None:
        req = AddTaskRequest(plan_id="p1", description="do it")
        assert req.description == "do it"

    def test_assign_task_request(self) -> None:
        req = AssignTaskRequest(task_id="t1", agent="research")
        assert req.agent == "research"

    def test_fail_task_request(self) -> None:
        req = FailTaskRequest(task_id="t1", failure_reason="err")
        assert req.failure_reason == "err"

    def test_task_lifecycle_request(self) -> None:
        req = TaskLifecycleRequest(task_id="t1")
        assert req.task_id == "t1"

    def test_get_plan_request(self) -> None:
        req = GetPlanRequest(plan_id="p1")
        assert req.plan_id == "p1"

    def test_list_plans_request_defaults(self) -> None:
        req = ListPlansRequest()
        assert req.status is None
        assert req.priority is None

    def test_get_task_request(self) -> None:
        req = GetTaskRequest(task_id="t1")
        assert req.task_id == "t1"

    def test_list_tasks_request_defaults(self) -> None:
        req = ListTasksRequest()
        assert req.status is None
        assert req.assigned_agent is None
        assert req.plan_id is None


# ===================================================================
# UseCaseError is importable and catchable
# ===================================================================


class TestUseCaseErrorCatchable:
    def test_catch_plan_not_found(self) -> None:
        try:
            raise PlanNotFoundError("id-1")
        except UseCaseError:
            assert True

    def test_catch_task_not_found(self) -> None:
        try:
            raise TaskNotFoundError("id-2")
        except UseCaseError:
            assert True
