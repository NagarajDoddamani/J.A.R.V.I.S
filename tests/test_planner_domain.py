from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.planner.domain.exceptions import (
    DuplicateExecutionStepIdError,
    DuplicateTaskIdError,
    EmptyPlanExecutionError,
    HybridStrategyRequiresMultipleTasksError,
    InvalidAgentTypeError,
    InvalidEstimatedDurationError,
    InvalidExecutionStrategyError,
    InvalidFailureReasonError,
    InvalidPlanGoalError,
    InvalidPlanPriorityError,
    InvalidStepOrderError,
    InvalidTaskDescriptionError,
    InvalidTransitionError,
    InvalidUserRequestError,
    PlanHasNoTasksError,
    PlanNotReadyError,
    PlanTerminalError,
    TaskNotAssignedError,
)
from backend.planner.domain.factory import PlannerFactory
from backend.planner.domain.model import (
    AgentType,
    EstimatedDuration,
    ExecutionStep,
    ExecutionStepId,
    ExecutionStrategy,
    FailureReason,
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
from backend.planner.domain.rules import (
    VALID_PLAN_TRANSITIONS,
    VALID_TASK_TRANSITIONS,
    assert_agent_valid,
    assert_critical_plan_task_priority,
    assert_execution_step_ids_unique,
    assert_failure_reason_provided,
    assert_goal_required,
    assert_hybrid_strategy_min_tasks,
    assert_plan_can_transition,
    assert_plan_failure_reason_provided,
    assert_plan_has_tasks,
    assert_plan_is_ready,
    assert_plan_not_empty,
    assert_plan_not_terminal,
    assert_priority_valid,
    assert_step_description_required,
    assert_step_order_non_negative,
    assert_strategy_valid,
    assert_task_can_transition,
    assert_task_description_required,
    assert_task_has_assigned_agent,
    assert_task_id_unique,
    assert_user_request_required,
    validate_plan_creation,
    validate_task_assignment,
    validate_task_creation,
)

# ===========================================================================
# Helpers
# ===========================================================================


def make_valid_plan(
    user_request: str = "Help me with research",
    goal: str = "Complete research project",
    priority: PlanPriority = PlanPriority.NORMAL,
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL,
) -> Plan:
    p, _ = PlannerFactory.create_plan(
        user_request=user_request,
        goal=goal,
        priority=priority,
        strategy=strategy,
    )
    return p


def make_valid_task(
    description: str = "Gather data",
    plan: Plan | None = None,
) -> Task:
    if plan is None:
        plan = make_valid_plan()
    t, _ = PlannerFactory.add_task(plan=plan, description=description)
    return t


# =============================================================================
# 1. Value Object Tests
# =============================================================================


class TestPlanId:
    def test_creation(self) -> None:
        pid = PlanId()
        assert isinstance(pid.value, UUID)

    def test_str_representation(self) -> None:
        pid = PlanId()
        assert str(pid) == str(pid.value)

    def test_equality(self) -> None:
        v = UUID("00000000-0000-0000-0000-000000000001")
        assert PlanId(value=v) == PlanId(value=v)

    def test_inequality(self) -> None:
        assert PlanId() != PlanId()

    def test_immutability(self) -> None:
        pid = PlanId()
        with pytest.raises(AttributeError):
            pid.value = UUID(int=0)  # type: ignore

    def test_default_factory(self) -> None:
        pid = PlanId()
        assert pid.value is not None


class TestTaskId:
    def test_creation(self) -> None:
        tid = TaskId()
        assert isinstance(tid.value, UUID)

    def test_str_representation(self) -> None:
        tid = TaskId()
        assert str(tid) == str(tid.value)

    def test_equality(self) -> None:
        v = UUID("00000000-0000-0000-0000-000000000002")
        assert TaskId(value=v) == TaskId(value=v)

    def test_inequality(self) -> None:
        assert TaskId() != TaskId()

    def test_immutability(self) -> None:
        tid = TaskId()
        with pytest.raises(AttributeError):
            tid.value = UUID(int=0)  # type: ignore

    def test_default_factory(self) -> None:
        tid = TaskId()
        assert tid.value is not None


class TestExecutionStepId:
    def test_creation(self) -> None:
        eid = ExecutionStepId()
        assert isinstance(eid.value, UUID)

    def test_str_representation(self) -> None:
        eid = ExecutionStepId()
        assert str(eid) == str(eid.value)

    def test_equality(self) -> None:
        v = UUID("00000000-0000-0000-0000-000000000003")
        assert ExecutionStepId(value=v) == ExecutionStepId(value=v)

    def test_inequality(self) -> None:
        assert ExecutionStepId() != ExecutionStepId()

    def test_immutability(self) -> None:
        eid = ExecutionStepId()
        with pytest.raises(AttributeError):
            eid.value = UUID(int=0)  # type: ignore


class TestUserRequest:
    def test_creation(self) -> None:
        ur = UserRequest(value="Help me with AI research")
        assert ur.value == "Help me with AI research"

    def test_str_conversion(self) -> None:
        ur = UserRequest(value="Hello")
        assert str(ur) == "Hello"

    def test_length(self) -> None:
        ur = UserRequest(value="abcd")
        assert len(ur) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidUserRequestError, match="not be empty"):
            UserRequest(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidUserRequestError, match="not be empty"):
            UserRequest(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            UserRequest(value=123)  # type: ignore

    def test_equality(self) -> None:
        assert UserRequest(value="a") == UserRequest(value="a")

    def test_frozen(self) -> None:
        ur = UserRequest(value="a")
        with pytest.raises(AttributeError):
            ur.value = "b"  # type: ignore


class TestPlanGoal:
    def test_creation(self) -> None:
        g = PlanGoal(value="Complete research")
        assert g.value == "Complete research"

    def test_str_conversion(self) -> None:
        g = PlanGoal(value="Goal")
        assert str(g) == "Goal"

    def test_length(self) -> None:
        g = PlanGoal(value="abcd")
        assert len(g) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidPlanGoalError, match="not be empty"):
            PlanGoal(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidPlanGoalError, match="not be empty"):
            PlanGoal(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            PlanGoal(value=123)  # type: ignore

    def test_equality(self) -> None:
        assert PlanGoal(value="a") == PlanGoal(value="a")

    def test_frozen(self) -> None:
        g = PlanGoal(value="a")
        with pytest.raises(AttributeError):
            g.value = "b"  # type: ignore


class TestTaskDescription:
    def test_creation(self) -> None:
        td = TaskDescription(value="Gather data")
        assert td.value == "Gather data"

    def test_str_conversion(self) -> None:
        td = TaskDescription(value="Task")
        assert str(td) == "Task"

    def test_length(self) -> None:
        td = TaskDescription(value="abcd")
        assert len(td) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidTaskDescriptionError, match="not be empty"):
            TaskDescription(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidTaskDescriptionError, match="not be empty"):
            TaskDescription(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            TaskDescription(value=123)  # type: ignore

    def test_equality(self) -> None:
        assert TaskDescription(value="a") == TaskDescription(value="a")

    def test_frozen(self) -> None:
        td = TaskDescription(value="a")
        with pytest.raises(AttributeError):
            td.value = "b"  # type: ignore


class TestFailureReason:
    def test_creation(self) -> None:
        fr = FailureReason(value="Timeout exceeded")
        assert fr.value == "Timeout exceeded"

    def test_str_conversion(self) -> None:
        fr = FailureReason(value="Error")
        assert str(fr) == "Error"

    def test_length(self) -> None:
        fr = FailureReason(value="abcd")
        assert len(fr) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidFailureReasonError, match="not be empty"):
            FailureReason(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidFailureReasonError, match="not be empty"):
            FailureReason(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            FailureReason(value=123)  # type: ignore

    def test_equality(self) -> None:
        assert FailureReason(value="a") == FailureReason(value="a")

    def test_frozen(self) -> None:
        fr = FailureReason(value="a")
        with pytest.raises(AttributeError):
            fr.value = "b"  # type: ignore


class TestEstimatedDuration:
    def test_creation(self) -> None:
        ed = EstimatedDuration(value=60.0)
        assert ed.value == 60.0

    def test_positive_integer(self) -> None:
        ed = EstimatedDuration(value=120)
        assert ed.value == 120

    def test_float_conversion(self) -> None:
        ed = EstimatedDuration(value=30.5)
        assert float(ed) == 30.5

    def test_zero_raises(self) -> None:
        with pytest.raises(InvalidEstimatedDurationError, match="positive"):
            EstimatedDuration(value=0)

    def test_negative_raises(self) -> None:
        with pytest.raises(InvalidEstimatedDurationError, match="positive"):
            EstimatedDuration(value=-10)

    def test_non_numeric_raises(self) -> None:
        with pytest.raises(TypeError):
            EstimatedDuration(value="abc")  # type: ignore

    def test_equality(self) -> None:
        assert EstimatedDuration(value=5.0) == EstimatedDuration(value=5.0)

    def test_frozen(self) -> None:
        ed = EstimatedDuration(value=5.0)
        with pytest.raises(AttributeError):
            ed.value = 10.0  # type: ignore

    def test_large_value(self) -> None:
        ed = EstimatedDuration(value=999999.0)
        assert ed.value == 999999.0


# =============================================================================
# 2. Enum Tests
# =============================================================================


class TestPlanStatus:
    def test_members(self) -> None:
        assert PlanStatus.DRAFT.value == "draft"
        assert PlanStatus.APPROVED.value == "approved"
        assert PlanStatus.PLANNING.value == "planning"
        assert PlanStatus.READY.value == "ready"
        assert PlanStatus.EXECUTING.value == "executing"
        assert PlanStatus.COMPLETED.value == "completed"
        assert PlanStatus.FAILED.value == "failed"
        assert PlanStatus.CANCELLED.value == "cancelled"

    def test_order(self) -> None:
        members = list(PlanStatus)
        assert members == [
            PlanStatus.DRAFT,
            PlanStatus.APPROVED,
            PlanStatus.PLANNING,
            PlanStatus.READY,
            PlanStatus.EXECUTING,
            PlanStatus.COMPLETED,
            PlanStatus.FAILED,
            PlanStatus.CANCELLED,
        ]

    def test_from_string(self) -> None:
        assert PlanStatus("draft") == PlanStatus.DRAFT
        assert PlanStatus("executing") == PlanStatus.EXECUTING

    def test_unique_values(self) -> None:
        values = [s.value for s in PlanStatus]
        assert len(values) == len(set(values))


class TestTaskStatus:
    def test_members(self) -> None:
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.ASSIGNED.value == "assigned"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_from_string(self) -> None:
        assert TaskStatus("running") == TaskStatus.RUNNING

    def test_unique_values(self) -> None:
        values = [s.value for s in TaskStatus]
        assert len(values) == len(set(values))


class TestPlanPriority:
    def test_members(self) -> None:
        assert PlanPriority.LOW.value == "low"
        assert PlanPriority.NORMAL.value == "normal"
        assert PlanPriority.HIGH.value == "high"
        assert PlanPriority.CRITICAL.value == "critical"

    def test_from_string(self) -> None:
        assert PlanPriority("high") == PlanPriority.HIGH

    def test_unique_values(self) -> None:
        values = [p.value for p in PlanPriority]
        assert len(values) == len(set(values))


class TestExecutionStrategy:
    def test_members(self) -> None:
        assert ExecutionStrategy.SEQUENTIAL.value == "sequential"
        assert ExecutionStrategy.PARALLEL.value == "parallel"
        assert ExecutionStrategy.HYBRID.value == "hybrid"

    def test_from_string(self) -> None:
        assert ExecutionStrategy("hybrid") == ExecutionStrategy.HYBRID

    def test_unique_values(self) -> None:
        values = [s.value for s in ExecutionStrategy]
        assert len(values) == len(set(values))


class TestAgentType:
    def test_members(self) -> None:
        assert AgentType.PLANNER.value == "planner"
        assert AgentType.RESEARCH.value == "research"
        assert AgentType.AUTOMATION.value == "automation"
        assert AgentType.MEMORY.value == "memory"
        assert AgentType.KNOWLEDGE.value == "knowledge"
        assert AgentType.NOTIFICATION.value == "notification"
        assert AgentType.POLICY.value == "policy"

    def test_from_string(self) -> None:
        assert AgentType("research") == AgentType.RESEARCH

    def test_unique_values(self) -> None:
        values = [a.value for a in AgentType]
        assert len(values) == len(set(values))


# =============================================================================
# 3. Domain Event Tests
# =============================================================================


class TestPlanCreatedEvent:
    def test_creation(self) -> None:
        pid = PlanId()
        now = datetime.now(tz=timezone.utc)
        ev = PlanCreated(
            plan_id=pid,
            user_request="Research",
            goal="Complete",
            priority="normal",
            strategy="sequential",
            occurred_at=now,
        )
        assert ev.plan_id == pid
        assert ev.user_request == "Research"
        assert ev.goal == "Complete"
        assert ev.priority == "normal"
        assert ev.strategy == "sequential"
        assert ev.occurred_at == now
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        pid = PlanId()
        ev = PlanCreated(
            plan_id=pid, user_request="R", goal="G",
            priority="low", strategy="sequential",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.user_request = "changed"  # type: ignore

    def test_unique_event_ids(self) -> None:
        pid = PlanId()
        now = datetime.now(tz=timezone.utc)
        ev1 = PlanCreated(
            plan_id=pid, user_request="A", goal="B",
            priority="low", strategy="sequential", occurred_at=now,
        )
        ev2 = PlanCreated(
            plan_id=pid, user_request="A", goal="B",
            priority="low", strategy="sequential", occurred_at=now,
        )
        assert ev1.event_id != ev2.event_id


class TestPlanApprovedEvent:
    def test_creation(self) -> None:
        pid = PlanId()
        now = datetime.now(tz=timezone.utc)
        ev = PlanApproved(plan_id=pid, occurred_at=now)
        assert ev.plan_id == pid
        assert ev.occurred_at == now
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = PlanApproved(
            plan_id=PlanId(), occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.plan_id = PlanId()  # type: ignore


class TestPlanReadyEvent:
    def test_creation(self) -> None:
        pid = PlanId()
        now = datetime.now(tz=timezone.utc)
        ev = PlanReady(plan_id=pid, occurred_at=now)
        assert ev.plan_id == pid
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = PlanReady(
            plan_id=PlanId(), occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.occurred_at = datetime.now(tz=timezone.utc)  # type: ignore


class TestPlanExecutionStartedEvent:
    def test_creation(self) -> None:
        pid = PlanId()
        now = datetime.now(tz=timezone.utc)
        ev = PlanExecutionStarted(plan_id=pid, occurred_at=now)
        assert ev.plan_id == pid
        assert isinstance(ev.event_id, UUID)


class TestPlanCompletedEvent:
    def test_creation(self) -> None:
        pid = PlanId()
        now = datetime.now(tz=timezone.utc)
        ev = PlanCompleted(plan_id=pid, occurred_at=now)
        assert ev.plan_id == pid
        assert isinstance(ev.event_id, UUID)


class TestPlanFailedEvent:
    def test_creation(self) -> None:
        pid = PlanId()
        now = datetime.now(tz=timezone.utc)
        ev = PlanFailed(plan_id=pid, failure_reason="Error", occurred_at=now)
        assert ev.plan_id == pid
        assert ev.failure_reason == "Error"
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = PlanFailed(
            plan_id=PlanId(), failure_reason="Err",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.failure_reason = "changed"  # type: ignore


class TestPlanCancelledEvent:
    def test_creation(self) -> None:
        pid = PlanId()
        now = datetime.now(tz=timezone.utc)
        ev = PlanCancelled(plan_id=pid, occurred_at=now)
        assert ev.plan_id == pid
        assert isinstance(ev.event_id, UUID)


class TestTaskCreatedEvent:
    def test_creation(self) -> None:
        tid = TaskId()
        now = datetime.now(tz=timezone.utc)
        ev = TaskCreated(task_id=tid, description="Do work", occurred_at=now)
        assert ev.task_id == tid
        assert ev.description == "Do work"
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = TaskCreated(
            task_id=TaskId(), description="Work",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.description = "changed"  # type: ignore


class TestTaskAssignedEvent:
    def test_creation(self) -> None:
        tid = TaskId()
        now = datetime.now(tz=timezone.utc)
        ev = TaskAssigned(
            task_id=tid, assigned_agent=AgentType.RESEARCH, occurred_at=now,
        )
        assert ev.task_id == tid
        assert ev.assigned_agent == AgentType.RESEARCH
        assert isinstance(ev.event_id, UUID)


class TestTaskCompletedEvent:
    def test_creation(self) -> None:
        tid = TaskId()
        now = datetime.now(tz=timezone.utc)
        ev = TaskCompleted(task_id=tid, occurred_at=now)
        assert ev.task_id == tid
        assert isinstance(ev.event_id, UUID)


class TestTaskFailedEvent:
    def test_creation(self) -> None:
        tid = TaskId()
        now = datetime.now(tz=timezone.utc)
        ev = TaskFailed(task_id=tid, failure_reason="Error", occurred_at=now)
        assert ev.task_id == tid
        assert ev.failure_reason == "Error"
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = TaskFailed(
            task_id=TaskId(), failure_reason="Err",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.failure_reason = "changed"  # type: ignore


# =============================================================================
# 4. ExecutionStep Entity Tests
# =============================================================================


class TestExecutionStepCreation:
    def test_creation(self) -> None:
        step = ExecutionStep(step_order=1, description="Process data")
        assert isinstance(step.step_id, ExecutionStepId)
        assert step.step_order == 1
        assert step.description == "Process data"
        assert step.status == TaskStatus.PENDING

    def test_default_id_generated(self) -> None:
        step = ExecutionStep()
        assert isinstance(step.step_id, ExecutionStepId)

    def test_default_order_zero(self) -> None:
        step = ExecutionStep()
        assert step.step_order == 0

    def test_default_status_pending(self) -> None:
        step = ExecutionStep()
        assert step.status == TaskStatus.PENDING

    def test_with_task_id(self) -> None:
        tid = TaskId()
        step = ExecutionStep(task_id=tid)
        assert step.task_id == tid

    def test_repr(self) -> None:
        step = ExecutionStep(step_order=1, description="Test")
        r = repr(step)
        assert "ExecutionStep" in r
        assert "order=1" in r

    def test_immutable_fields(self) -> None:
        step = ExecutionStep()
        assert step.step_id is not None


# =============================================================================
# 5. Task Entity Tests
# =============================================================================


class TestTaskCreation:
    def test_default_status_pending(self) -> None:
        t = Task()
        assert t.status == TaskStatus.PENDING

    def test_default_id_generated(self) -> None:
        t = Task()
        assert isinstance(t.task_id, TaskId)

    def test_initial_events_empty(self) -> None:
        t = Task()
        assert t.events == []

    def test_not_terminal_initially(self) -> None:
        t = Task()
        assert t.is_terminal is False

    def test_with_description(self) -> None:
        td = TaskDescription(value="Do work")
        t = Task(description=td)
        assert t.description is not None
        assert t.description.value == "Do work"

    def test_repr(self) -> None:
        t = Task()
        r = repr(t)
        assert "Task" in r
        assert str(t.task_id) in r

    def test_empty_execution_steps(self) -> None:
        t = Task()
        assert t.execution_steps == []


class TestTaskAssign:
    def test_assign_sets_agent(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        assert t.assigned_agent == AgentType.RESEARCH

    def test_assign_sets_assigned_status(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        assert t.status == TaskStatus.ASSIGNED

    def test_assign_emits_event(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        assert len(t.events) == 1
        assert isinstance(t.events[0], TaskAssigned)
        assert t.events[0].assigned_agent == AgentType.RESEARCH

    def test_assign_twice_raises(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        with pytest.raises(InvalidTransitionError):
            t.assign(AgentType.AUTOMATION)

    def test_assign_completed_task_raises(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        t.complete()
        with pytest.raises(InvalidTransitionError):
            t.assign(AgentType.AUTOMATION)

    def test_assign_cancelled_task_raises(self) -> None:
        t = make_valid_task()
        t.cancel()
        with pytest.raises(InvalidTransitionError):
            t.assign(AgentType.RESEARCH)

    def test_assign_invalid_agent_raises(self) -> None:
        t = make_valid_task()
        with pytest.raises(InvalidAgentTypeError):
            t.assign("invalid_agent")  # type: ignore


class TestTaskStart:
    def test_start_requires_assigned(self) -> None:
        t = make_valid_task()
        with pytest.raises(TaskNotAssignedError):
            t.start()

    def test_start_sets_running(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        assert t.status == TaskStatus.RUNNING

    def test_start_no_event_emitted(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        assert len(t.events) == 1  # Only the assign event

    def test_double_start_raises(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        with pytest.raises(InvalidTransitionError):
            t.start()

    def test_start_from_completed_raises(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        t.complete()
        with pytest.raises(InvalidTransitionError):
            t.start()


class TestTaskComplete:
    def test_complete_sets_completed(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        t.complete()
        assert t.status == TaskStatus.COMPLETED

    def test_complete_emits_event(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        t.complete()
        assert len(t.events) == 2
        assert isinstance(t.events[1], TaskCompleted)

    def test_complete_from_pending_raises(self) -> None:
        t = make_valid_task()
        with pytest.raises(InvalidTransitionError):
            t.complete()

    def test_double_complete_raises(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        t.complete()
        with pytest.raises(InvalidTransitionError):
            t.complete()

    def test_complete_cancelled_raises(self) -> None:
        t = make_valid_task()
        t.cancel()
        with pytest.raises(InvalidTransitionError):
            t.complete()


class TestTaskFail:
    def test_fail_sets_failed(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        t.fail(FailureReason(value="Error occurred"))
        assert t.status == TaskStatus.FAILED

    def test_fail_requires_reason(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        with pytest.raises(InvalidFailureReasonError):
            t.fail(None)  # type: ignore

    def test_fail_emits_event(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        t.fail(FailureReason(value="Error"))
        assert len(t.events) == 2
        assert isinstance(t.events[1], TaskFailed)
        assert t.events[1].failure_reason == "Error"

    def test_fail_sets_failure_reason(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        t.fail(FailureReason(value="Timeout"))
        assert t.failure_reason is not None
        assert t.failure_reason.value == "Timeout"

    def test_fail_from_pending_raises(self) -> None:
        t = make_valid_task()
        with pytest.raises(InvalidTransitionError):
            t.fail(FailureReason(value="Error"))

    def test_double_fail_raises(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        t.fail(FailureReason(value="Error"))
        with pytest.raises(InvalidTransitionError):
            t.fail(FailureReason(value="Another error"))


class TestTaskCancel:
    def test_cancel_from_pending(self) -> None:
        t = make_valid_task()
        t.cancel()
        assert t.status == TaskStatus.CANCELLED

    def test_cancel_from_assigned(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.cancel()
        assert t.status == TaskStatus.CANCELLED

    def test_cancel_from_running(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        t.cancel()
        assert t.status == TaskStatus.CANCELLED

    def test_cancel_from_completed_raises(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        t.complete()
        with pytest.raises(InvalidTransitionError):
            t.cancel()

    def test_cancel_from_failed_raises(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        t.fail(FailureReason(value="Error"))
        with pytest.raises(InvalidTransitionError):
            t.cancel()

    def test_double_cancel_raises(self) -> None:
        t = make_valid_task()
        t.cancel()
        with pytest.raises(InvalidTransitionError):
            t.cancel()


class TestTaskTerminal:
    def test_completed_is_terminal(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        t.complete()
        assert t.is_terminal is True

    def test_failed_is_terminal(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        t.start()
        t.fail(FailureReason(value="Error"))
        assert t.is_terminal is True

    def test_cancelled_is_terminal(self) -> None:
        t = make_valid_task()
        t.cancel()
        assert t.is_terminal is True

    def test_pending_not_terminal(self) -> None:
        t = make_valid_task()
        assert t.is_terminal is False

    def test_clear_events(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        assert len(t.events) == 1
        t._clear_events()
        assert t.events == []


# =============================================================================
# 6. Plan Entity Tests
# =============================================================================


class TestPlanCreation:
    def test_default_status_draft(self) -> None:
        p = make_valid_plan()
        assert p.status == PlanStatus.DRAFT

    def test_default_id_generated(self) -> None:
        p = make_valid_plan()
        assert isinstance(p.plan_id, PlanId)

    def test_default_priority_normal(self) -> None:
        p = make_valid_plan()
        assert p.priority == PlanPriority.NORMAL

    def test_default_strategy_sequential(self) -> None:
        p = make_valid_plan()
        assert p.strategy == ExecutionStrategy.SEQUENTIAL

    def test_initial_events_empty(self) -> None:
        p = make_valid_plan()
        assert p.events == []

    def test_not_terminal_initially(self) -> None:
        p = make_valid_plan()
        assert p.is_terminal is False

    def test_initial_tasks_empty(self) -> None:
        p = make_valid_plan()
        assert p.tasks == []

    def test_created_at_set(self) -> None:
        p = make_valid_plan()
        assert p.created_at is not None
        assert p.created_at.tzinfo is not None

    def test_repr(self) -> None:
        p = make_valid_plan()
        r = repr(p)
        assert "Plan" in r
        assert str(p.plan_id) in r


class TestPlanApprove:
    def test_approve_sets_approved(self) -> None:
        p = make_valid_plan()
        p.approve()
        assert p.status == PlanStatus.APPROVED

    def test_approve_emits_event(self) -> None:
        p = make_valid_plan()
        p.approve()
        assert len(p.events) == 1
        assert isinstance(p.events[0], PlanApproved)

    def test_double_approve_raises(self) -> None:
        p = make_valid_plan()
        p.approve()
        with pytest.raises(InvalidTransitionError):
            p.approve()

    def test_approve_from_planning_raises(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        with pytest.raises(InvalidTransitionError):
            p.approve()

    def test_approve_terminal_raises(self) -> None:
        p = make_valid_plan()
        p.cancel()
        with pytest.raises(InvalidTransitionError):
            p.approve()


class TestPlanStartPlanning:
    def test_start_planning_sets_planning(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        assert p.status == PlanStatus.PLANNING

    def test_start_planning_from_draft_raises(self) -> None:
        p = make_valid_plan()
        with pytest.raises(InvalidTransitionError):
            p.start_planning()

    def test_start_planning_no_event(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        assert len(p.events) == 1  # Only the approve event

    def test_start_planning_from_ready_raises(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        with pytest.raises(InvalidTransitionError):
            p.start_planning()


class TestPlanMarkReady:
    def test_mark_ready_sets_ready(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        assert p.status == PlanStatus.READY

    def test_mark_ready_requires_tasks(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        with pytest.raises(PlanHasNoTasksError):
            p.mark_ready()

    def test_mark_ready_emits_event(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        assert len(p.events) == 2
        assert isinstance(p.events[1], PlanReady)

    def test_mark_ready_from_draft_raises(self) -> None:
        p = make_valid_plan()
        with pytest.raises(PlanHasNoTasksError):
            p.mark_ready()


class TestPlanStartExecution:
    def test_start_execution_sets_executing(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        assert p.status == PlanStatus.EXECUTING

    def test_start_execution_requires_ready(self) -> None:
        p = make_valid_plan()
        with pytest.raises(PlanNotReadyError):
            p.start_execution()

    def test_start_execution_requires_tasks(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        p._status = PlanStatus.READY  # Force ready
        with pytest.raises(PlanHasNoTasksError):
            p.start_execution()

    def test_start_execution_emits_event(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        assert len(p.events) == 3
        assert isinstance(p.events[2], PlanExecutionStarted)

    def test_double_execute_raises(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        with pytest.raises(PlanNotReadyError):
            p.start_execution()


class TestPlanComplete:
    def test_complete_sets_completed(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        p.complete()
        assert p.status == PlanStatus.COMPLETED

    def test_complete_emits_event(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        p.complete()
        assert isinstance(p.events[-1], PlanCompleted)

    def test_complete_from_draft_raises(self) -> None:
        p = make_valid_plan()
        with pytest.raises(InvalidTransitionError):
            p.complete()

    def test_double_complete_raises(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        p.complete()
        with pytest.raises(InvalidTransitionError):
            p.complete()


class TestPlanFail:
    def test_fail_sets_failed(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        p.fail(FailureReason(value="Execution error"))
        assert p.status == PlanStatus.FAILED

    def test_fail_requires_reason(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        with pytest.raises(InvalidFailureReasonError):
            p.fail(None)  # type: ignore

    def test_fail_emits_event(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        p.fail(FailureReason(value="Error"))
        assert isinstance(p.events[-1], PlanFailed)
        assert p.events[-1].failure_reason == "Error"

    def test_fail_from_draft_raises(self) -> None:
        p = make_valid_plan()
        with pytest.raises(InvalidTransitionError):
            p.fail(FailureReason(value="Error"))

    def test_fail_from_completed_raises(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        p.complete()
        with pytest.raises(InvalidTransitionError):
            p.fail(FailureReason(value="Error"))


class TestPlanCancel:
    def test_cancel_from_draft(self) -> None:
        p = make_valid_plan()
        p.cancel()
        assert p.status == PlanStatus.CANCELLED

    def test_cancel_from_approved(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.cancel()
        assert p.status == PlanStatus.CANCELLED

    def test_cancel_emits_event(self) -> None:
        p = make_valid_plan()
        p.cancel()
        assert len(p.events) == 1
        assert isinstance(p.events[0], PlanCancelled)

    def test_cancel_from_completed_raises(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        p.complete()
        with pytest.raises(InvalidTransitionError):
            p.cancel()

    def test_cancel_from_failed_raises(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        p.fail(FailureReason(value="Error"))
        with pytest.raises(InvalidTransitionError):
            p.cancel()

    def test_double_cancel_raises(self) -> None:
        p = make_valid_plan()
        p.cancel()
        with pytest.raises(InvalidTransitionError):
            p.cancel()


class TestPlanAddTask:
    def test_add_task_increases_count(self) -> None:
        p = make_valid_plan()
        t = make_valid_task(plan=p)
        assert len(p.tasks) == 1
        assert p.tasks[0].task_id == t.task_id

    def test_add_task_sets_updated_at(self) -> None:
        p = make_valid_plan()
        assert p.updated_at is None
        make_valid_task(plan=p)
        assert p.updated_at is not None

    def test_add_duplicate_task_id_raises(self) -> None:
        p = make_valid_plan()
        t1 = make_valid_task(plan=p)
        with pytest.raises(DuplicateTaskIdError):
            p.add_task(t1)

    def test_add_task_to_completed_plan_raises(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        p.complete()
        t = Task(description=TaskDescription(value="New task"))
        with pytest.raises(PlanTerminalError):
            p.add_task(t)

    def test_add_task_to_cancelled_plan_raises(self) -> None:
        p = make_valid_plan()
        p.cancel()
        t = Task(description=TaskDescription(value="New task"))
        with pytest.raises(PlanTerminalError):
            p.add_task(t)

    def test_add_task_to_failed_plan_raises(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        p.fail(FailureReason(value="Error"))
        t = Task(description=TaskDescription(value="New task"))
        with pytest.raises(PlanTerminalError):
            p.add_task(t)


# =============================================================================
# 7. Rules Tests
# =============================================================================


class TestRuleUserRequestRequired:
    def test_valid(self) -> None:
        assert_user_request_required("Help")

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidUserRequestError):
            assert_user_request_required("")

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidUserRequestError):
            assert_user_request_required(None)

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidUserRequestError):
            assert_user_request_required("   ")


class TestRuleGoalRequired:
    def test_valid(self) -> None:
        assert_goal_required("Goal")

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidPlanGoalError):
            assert_goal_required("")

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidPlanGoalError):
            assert_goal_required(None)

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidPlanGoalError):
            assert_goal_required("   ")


class TestRulePlanHasTasks:
    def test_with_tasks_passes(self) -> None:
        p = make_valid_plan()
        make_valid_task(plan=p)
        assert_plan_has_tasks(p)

    def test_empty_plan_raises(self) -> None:
        p = make_valid_plan()
        with pytest.raises(PlanHasNoTasksError):
            assert_plan_has_tasks(p)


class TestRuleTaskDescriptionRequired:
    def test_valid(self) -> None:
        assert_task_description_required("Do work")

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidTaskDescriptionError):
            assert_task_description_required("")

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidTaskDescriptionError):
            assert_task_description_required(None)

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidTaskDescriptionError):
            assert_task_description_required("   ")


class TestRuleTaskAssignedAgent:
    def test_assigned_passes(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        assert_task_has_assigned_agent(t)

    def test_unassigned_raises(self) -> None:
        t = make_valid_task()
        with pytest.raises(TaskNotAssignedError):
            assert_task_has_assigned_agent(t)


class TestRuleFailureReasonProvided:
    def test_with_reason_passes(self) -> None:
        assert_failure_reason_provided(FailureReason(value="Error"))

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidFailureReasonError, match="required"):
            assert_failure_reason_provided(None)


class TestRuleStepDescriptionRequired:
    def test_valid(self) -> None:
        assert_step_description_required("Process")

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidTaskDescriptionError):
            assert_step_description_required("")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidTaskDescriptionError):
            assert_step_description_required("   ")


class TestRuleStepOrderNonNegative:
    def test_zero_passes(self) -> None:
        assert_step_order_non_negative(0)

    def test_positive_passes(self) -> None:
        assert_step_order_non_negative(1)

    def test_negative_raises(self) -> None:
        with pytest.raises(InvalidStepOrderError):
            assert_step_order_non_negative(-1)


class TestRulePriorityValid:
    def test_valid_strings(self) -> None:
        assert_priority_valid("low")
        assert_priority_valid("normal")
        assert_priority_valid("high")
        assert_priority_valid("critical")

    def test_enum_accepted(self) -> None:
        assert_priority_valid(PlanPriority.HIGH)

    def test_invalid_raises(self) -> None:
        with pytest.raises(InvalidPlanPriorityError):
            assert_priority_valid("urgent")


class TestRuleStrategyValid:
    def test_valid_strings(self) -> None:
        assert_strategy_valid("sequential")
        assert_strategy_valid("parallel")
        assert_strategy_valid("hybrid")

    def test_enum_accepted(self) -> None:
        assert_strategy_valid(ExecutionStrategy.PARALLEL)

    def test_invalid_raises(self) -> None:
        with pytest.raises(InvalidExecutionStrategyError):
            assert_strategy_valid("invalid")


class TestRuleAgentValid:
    def test_valid_strings(self) -> None:
        for agent in ("planner", "research", "automation", "memory", "knowledge", "notification", "policy"):
            assert_agent_valid(agent)

    def test_enum_accepted(self) -> None:
        assert_agent_valid(AgentType.RESEARCH)

    def test_invalid_raises(self) -> None:
        with pytest.raises(InvalidAgentTypeError):
            assert_agent_valid("unknown")


class TestRuleEstimatedDurationPositive:
    def test_positive_passes(self) -> None:
        ed = EstimatedDuration(value=10)
        assert ed.value == 10

    def test_zero_raises(self) -> None:
        with pytest.raises(InvalidEstimatedDurationError):
            EstimatedDuration(value=0)


class TestRulePlanReadyBeforeExecuting:
    def test_ready_passes(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        assert_plan_is_ready(p)

    def test_not_ready_raises(self) -> None:
        p = make_valid_plan()
        with pytest.raises(PlanNotReadyError):
            assert_plan_is_ready(p)


class TestRuleUniqueTaskIds:
    def test_unique_passes(self) -> None:
        p = make_valid_plan()
        make_valid_task(plan=p)
        different_id = TaskId()
        assert_task_id_unique(different_id, p.tasks)  # Should pass since it's different

    def test_duplicate_raises(self) -> None:
        p = make_valid_plan()
        t1 = make_valid_task(plan=p)
        with pytest.raises(DuplicateTaskIdError):
            assert_task_id_unique(t1.task_id, p.tasks)


class TestRuleUniqueStepIds:
    def test_unique_passes(self) -> None:
        s1 = ExecutionStep()
        assert_execution_step_ids_unique(s1.step_id, [])

    def test_duplicate_raises(self) -> None:
        s1 = ExecutionStep()
        with pytest.raises(DuplicateExecutionStepIdError):
            assert_execution_step_ids_unique(s1.step_id, [s1])


class TestRuleEmptyPlanCannotExecute:
    def test_non_empty_passes(self) -> None:
        p = make_valid_plan()
        make_valid_task(plan=p)
        assert_plan_not_empty(p)

    def test_empty_raises(self) -> None:
        p = make_valid_plan()
        with pytest.raises(EmptyPlanExecutionError):
            assert_plan_not_empty(p)


class TestRuleHybridStrategyMinTasks:
    def test_hybrid_with_two_passes(self) -> None:
        assert_hybrid_strategy_min_tasks(ExecutionStrategy.HYBRID, 2)

    def test_hybrid_with_many_passes(self) -> None:
        assert_hybrid_strategy_min_tasks(ExecutionStrategy.HYBRID, 5)

    def test_hybrid_with_one_raises(self) -> None:
        with pytest.raises(HybridStrategyRequiresMultipleTasksError):
            assert_hybrid_strategy_min_tasks(ExecutionStrategy.HYBRID, 1)

    def test_sequential_with_one_passes(self) -> None:
        assert_hybrid_strategy_min_tasks(ExecutionStrategy.SEQUENTIAL, 1)

    def test_parallel_with_one_passes(self) -> None:
        assert_hybrid_strategy_min_tasks(ExecutionStrategy.PARALLEL, 1)


class TestRuleCriticalPlanTaskPriority:
    def test_critical_no_task_priority(self) -> None:
        assert_critical_plan_task_priority(PlanPriority.CRITICAL)
        assert_critical_plan_task_priority(PlanPriority.CRITICAL, None)

    def test_non_critical(self) -> None:
        assert_critical_plan_task_priority(PlanPriority.LOW)
        assert_critical_plan_task_priority(PlanPriority.NORMAL)
        assert_critical_plan_task_priority(PlanPriority.HIGH)


class TestRulePlanTransitions:
    def test_draft_to_approved(self) -> None:
        assert_plan_can_transition(PlanStatus.DRAFT, PlanStatus.APPROVED)

    def test_draft_to_cancelled(self) -> None:
        assert_plan_can_transition(PlanStatus.DRAFT, PlanStatus.CANCELLED)

    def test_approved_to_planning(self) -> None:
        assert_plan_can_transition(PlanStatus.APPROVED, PlanStatus.PLANNING)

    def test_planning_to_ready(self) -> None:
        assert_plan_can_transition(PlanStatus.PLANNING, PlanStatus.READY)

    def test_ready_to_executing(self) -> None:
        assert_plan_can_transition(PlanStatus.READY, PlanStatus.EXECUTING)

    def test_executing_to_completed(self) -> None:
        assert_plan_can_transition(PlanStatus.EXECUTING, PlanStatus.COMPLETED)

    def test_executing_to_failed(self) -> None:
        assert_plan_can_transition(PlanStatus.EXECUTING, PlanStatus.FAILED)

    def test_completed_no_transitions(self) -> None:
        for s in PlanStatus:
            if s == PlanStatus.COMPLETED:
                continue
            with pytest.raises(InvalidTransitionError):
                assert_plan_can_transition(PlanStatus.COMPLETED, s)

    def test_failed_no_transitions(self) -> None:
        for s in PlanStatus:
            if s == PlanStatus.FAILED:
                continue
            with pytest.raises(InvalidTransitionError):
                assert_plan_can_transition(PlanStatus.FAILED, s)

    def test_cancelled_no_transitions(self) -> None:
        for s in PlanStatus:
            if s == PlanStatus.CANCELLED:
                continue
            with pytest.raises(InvalidTransitionError):
                assert_plan_can_transition(PlanStatus.CANCELLED, s)

    def test_valid_transitions_dict(self) -> None:
        for status in PlanStatus:
            assert status in VALID_PLAN_TRANSITIONS


class TestRuleTaskTransitions:
    def test_pending_to_assigned(self) -> None:
        assert_task_can_transition(TaskStatus.PENDING, TaskStatus.ASSIGNED)

    def test_pending_to_cancelled(self) -> None:
        assert_task_can_transition(TaskStatus.PENDING, TaskStatus.CANCELLED)

    def test_assigned_to_running(self) -> None:
        assert_task_can_transition(TaskStatus.ASSIGNED, TaskStatus.RUNNING)

    def test_running_to_completed(self) -> None:
        assert_task_can_transition(TaskStatus.RUNNING, TaskStatus.COMPLETED)

    def test_running_to_failed(self) -> None:
        assert_task_can_transition(TaskStatus.RUNNING, TaskStatus.FAILED)

    def test_completed_no_transitions(self) -> None:
        for s in TaskStatus:
            if s == TaskStatus.COMPLETED:
                continue
            with pytest.raises(InvalidTransitionError):
                assert_task_can_transition(TaskStatus.COMPLETED, s)

    def test_failed_no_transitions(self) -> None:
        for s in TaskStatus:
            if s == TaskStatus.FAILED:
                continue
            with pytest.raises(InvalidTransitionError):
                assert_task_can_transition(TaskStatus.FAILED, s)

    def test_cancelled_no_transitions(self) -> None:
        for s in TaskStatus:
            if s == TaskStatus.CANCELLED:
                continue
            with pytest.raises(InvalidTransitionError):
                assert_task_can_transition(TaskStatus.CANCELLED, s)

    def test_valid_transitions_dict(self) -> None:
        for status in TaskStatus:
            assert status in VALID_TASK_TRANSITIONS


class TestRulePlanNotTerminal:
    def test_active_plan_passes(self) -> None:
        p = make_valid_plan()
        assert_plan_not_terminal(p)

    def test_completed_raises(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        p.complete()
        with pytest.raises(PlanTerminalError):
            assert_plan_not_terminal(p)

    def test_failed_raises(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        p.fail(FailureReason(value="Error"))
        with pytest.raises(PlanTerminalError):
            assert_plan_not_terminal(p)

    def test_cancelled_raises(self) -> None:
        p = make_valid_plan()
        p.cancel()
        with pytest.raises(PlanTerminalError):
            assert_plan_not_terminal(p)


class TestRulePlanFailureReasonProvided:
    def test_with_reason_passes(self) -> None:
        assert_plan_failure_reason_provided(FailureReason(value="Error"))

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidFailureReasonError, match="required"):
            assert_plan_failure_reason_provided(None)


class TestRulePlanEstimatesDurationPositive:
    def test_positive_passes(self) -> None:
        assert EstimatedDuration(value=1.0)


# =============================================================================
# 8. Composite Validator Tests
# =============================================================================


class TestValidatePlanCreation:
    def test_valid_creation(self) -> None:
        priority, strategy = validate_plan_creation(
            user_request="Help", goal="Complete",
            priority="normal", strategy="sequential",
        )
        assert priority == PlanPriority.NORMAL
        assert strategy == ExecutionStrategy.SEQUENTIAL

    def test_empty_user_request_raises(self) -> None:
        with pytest.raises(InvalidUserRequestError):
            validate_plan_creation(
                user_request="", goal="Goal",
                priority="normal", strategy="sequential",
            )

    def test_empty_goal_raises(self) -> None:
        with pytest.raises(InvalidPlanGoalError):
            validate_plan_creation(
                user_request="Help", goal="",
                priority="normal", strategy="sequential",
            )

    def test_invalid_priority_raises(self) -> None:
        with pytest.raises(InvalidPlanPriorityError):
            validate_plan_creation(
                user_request="Help", goal="Goal",
                priority="invalid", strategy="sequential",
            )

    def test_invalid_strategy_raises(self) -> None:
        with pytest.raises(InvalidExecutionStrategyError):
            validate_plan_creation(
                user_request="Help", goal="Goal",
                priority="normal", strategy="invalid",
            )

    def test_priority_enum_accepted(self) -> None:
        priority, strategy = validate_plan_creation(
            user_request="Help", goal="Goal",
            priority=PlanPriority.HIGH,
            strategy=ExecutionStrategy.PARALLEL,
        )
        assert priority == PlanPriority.HIGH
        assert strategy == ExecutionStrategy.PARALLEL


class TestValidateTaskCreation:
    def test_valid_creation(self) -> None:
        validate_task_creation(description="Do work")

    def test_empty_description_raises(self) -> None:
        with pytest.raises(InvalidTaskDescriptionError):
            validate_task_creation(description="")

    def test_with_plan_not_terminal(self) -> None:
        p = make_valid_plan()
        validate_task_creation(description="Do work", plan=p)

    def test_with_completed_plan_raises(self) -> None:
        p = make_valid_plan()
        p.approve()
        p.start_planning()
        make_valid_task(plan=p)
        p.mark_ready()
        p.start_execution()
        p.complete()
        with pytest.raises(PlanTerminalError):
            validate_task_creation(description="Do work", plan=p)


class TestValidateTaskAssignment:
    def test_valid_assignment(self) -> None:
        t = make_valid_task()
        validate_task_assignment(task=t, agent="research")

    def test_assigned_task_raises(self) -> None:
        t = make_valid_task()
        t.assign(AgentType.RESEARCH)
        with pytest.raises(InvalidTransitionError):
            validate_task_assignment(task=t, agent="research")


# =============================================================================
# 9. Factory Tests
# =============================================================================


class TestFactoryCreatePlan:
    def test_happy_path(self) -> None:
        p, ev = PlannerFactory.create_plan(
            user_request="Research AI",
            goal="Complete research paper",
            priority="high",
            strategy="parallel",
        )
        assert isinstance(p, Plan)
        assert isinstance(ev, PlanCreated)
        assert p.user_request is not None
        assert p.user_request.value == "Research AI"
        assert p.goal is not None
        assert p.goal.value == "Complete research paper"
        assert p.priority == PlanPriority.HIGH
        assert p.strategy == ExecutionStrategy.PARALLEL
        assert p.status == PlanStatus.DRAFT

    def test_event_payload(self) -> None:
        p, ev = PlannerFactory.create_plan(
            user_request="Help",
            goal="Goal",
            priority="critical",
            strategy="hybrid",
        )
        assert ev.plan_id == p.plan_id
        assert ev.user_request == "Help"
        assert ev.goal == "Goal"
        assert ev.priority == "critical"
        assert ev.strategy == "hybrid"

    def test_priority_enum_accepted(self) -> None:
        p, ev = PlannerFactory.create_plan(
            user_request="Help", goal="Goal",
            priority=PlanPriority.LOW,
            strategy=ExecutionStrategy.SEQUENTIAL,
        )
        assert p.priority == PlanPriority.LOW

    def test_empty_request_raises(self) -> None:
        with pytest.raises(InvalidUserRequestError):
            PlannerFactory.create_plan(
                user_request="", goal="Goal",
                priority="normal", strategy="sequential",
            )

    def test_invalid_priority_raises(self) -> None:
        with pytest.raises(InvalidPlanPriorityError):
            PlannerFactory.create_plan(
                user_request="Help", goal="Goal",
                priority="invalid", strategy="sequential",
            )

    def test_invalid_strategy_raises(self) -> None:
        with pytest.raises(InvalidExecutionStrategyError):
            PlannerFactory.create_plan(
                user_request="Help", goal="Goal",
                priority="normal", strategy="invalid",
            )

    def test_default_created_at(self) -> None:
        p, ev = PlannerFactory.create_plan(
            user_request="Help", goal="Goal",
            priority="normal", strategy="sequential",
        )
        assert isinstance(p.created_at, datetime)


class TestFactoryAddTask:
    def test_happy_path(self) -> None:
        p = make_valid_plan()
        t, ev = PlannerFactory.add_task(plan=p, description="Gather data")
        assert isinstance(t, Task)
        assert isinstance(ev, TaskCreated)
        assert t.description is not None
        assert t.description.value == "Gather data"
        assert t.status == TaskStatus.PENDING
        assert len(p.tasks) == 1

    def test_event_payload(self) -> None:
        p = make_valid_plan()
        t, ev = PlannerFactory.add_task(plan=p, description="Analyze")
        assert ev.task_id == t.task_id
        assert ev.description == "Analyze"

    def test_empty_description_raises(self) -> None:
        p = make_valid_plan()
        with pytest.raises(InvalidTaskDescriptionError):
            PlannerFactory.add_task(plan=p, description="")

    def test_add_to_cancelled_plan_raises(self) -> None:
        p = make_valid_plan()
        p.cancel()
        with pytest.raises(PlanTerminalError):
            PlannerFactory.add_task(plan=p, description="New task")


class TestFactoryAssignTask:
    def test_happy_path(self) -> None:
        t = make_valid_task()
        ev = PlannerFactory.assign_task(task=t, agent="research")
        assert isinstance(ev, TaskAssigned)
        assert ev.assigned_agent == AgentType.RESEARCH
        assert t.assigned_agent == AgentType.RESEARCH
        assert t.status == TaskStatus.ASSIGNED

    def test_agent_enum_accepted(self) -> None:
        t = make_valid_task()
        ev = PlannerFactory.assign_task(task=t, agent=AgentType.AUTOMATION)
        assert ev.assigned_agent == AgentType.AUTOMATION

    def test_invalid_agent_raises(self) -> None:
        t = make_valid_task()
        with pytest.raises(InvalidAgentTypeError):
            PlannerFactory.assign_task(task=t, agent="unknown")

    def test_double_assign_raises(self) -> None:
        t = make_valid_task()
        PlannerFactory.assign_task(task=t, agent="research")
        with pytest.raises(InvalidTransitionError):
            PlannerFactory.assign_task(task=t, agent="automation")


class TestFactoryCompleteTask:
    def test_happy_path(self) -> None:
        t = make_valid_task()
        PlannerFactory.assign_task(task=t, agent="research")
        t.start()
        ev = PlannerFactory.complete_task(task=t)
        assert isinstance(ev, TaskCompleted)
        assert t.status == TaskStatus.COMPLETED

    def test_unassigned_task_raises(self) -> None:
        t = make_valid_task()
        with pytest.raises(InvalidTransitionError):
            PlannerFactory.complete_task(task=t)


class TestFactoryFailTask:
    def test_happy_path(self) -> None:
        t = make_valid_task()
        PlannerFactory.assign_task(task=t, agent="research")
        t.start()
        ev = PlannerFactory.fail_task(task=t, reason="Timeout")
        assert isinstance(ev, TaskFailed)
        assert ev.failure_reason == "Timeout"
        assert t.status == TaskStatus.FAILED

    def test_empty_reason_raises(self) -> None:
        t = make_valid_task()
        PlannerFactory.assign_task(task=t, agent="research")
        t.start()
        with pytest.raises(InvalidFailureReasonError):
            PlannerFactory.fail_task(task=t, reason="")

    def test_unassigned_task_raises(self) -> None:
        t = make_valid_task()
        with pytest.raises(InvalidTransitionError):
            PlannerFactory.fail_task(task=t, reason="Error")


# =============================================================================
# 10. Cross-Entity Tests
# =============================================================================


class TestPlanTaskRelationship:
    def test_plan_contains_added_task(self) -> None:
        p = make_valid_plan()
        t = make_valid_task(plan=p)
        assert t in p.tasks

    def test_multiple_tasks_in_plan(self) -> None:
        p = make_valid_plan()
        t1, _ = PlannerFactory.add_task(plan=p, description="Task 1")
        t2, _ = PlannerFactory.add_task(plan=p, description="Task 2")
        assert len(p.tasks) == 2
        assert t1 in p.tasks
        assert t2 in p.tasks

    def test_plan_tasks_immutable_via_property(self) -> None:
        p = make_valid_plan()
        make_valid_task(plan=p)
        tasks = p.tasks
        assert len(p.tasks) == 1
        assert tasks is not p.tasks


class TestTaskExecutionStepRelationship:
    def test_task_holds_steps(self) -> None:
        t = make_valid_task()
        step = ExecutionStep(task_id=t.task_id, step_order=1, description="Step 1")
        t._execution_steps.append(step)
        assert len(t.execution_steps) == 1
        assert t.execution_steps[0].task_id == t.task_id


class TestPlanLifecycleThroughFactory:
    def test_full_happy_path(self) -> None:
        p, ev1 = PlannerFactory.create_plan(
            user_request="Research AI",
            goal="Paper",
            priority="normal",
            strategy="sequential",
        )
        assert isinstance(ev1, PlanCreated)

        t1, ev2 = PlannerFactory.add_task(plan=p, description="Gather data")
        assert isinstance(ev2, TaskCreated)

        t2, ev3 = PlannerFactory.add_task(plan=p, description="Analyze")
        assert isinstance(ev3, TaskCreated)

        p.approve()
        p.start_planning()
        p.mark_ready()

        ev4 = PlannerFactory.assign_task(task=t1, agent="research")
        assert isinstance(ev4, TaskAssigned)
        t1.start()
        ev5 = PlannerFactory.complete_task(task=t1)
        assert isinstance(ev5, TaskCompleted)

        ev6 = PlannerFactory.assign_task(task=t2, agent="automation")
        assert isinstance(ev6, TaskAssigned)
        t2.start()
        ev7 = PlannerFactory.fail_task(task=t2, reason="Error")
        assert isinstance(ev7, TaskFailed)

        p.start_execution()
        p.complete()
        assert p.status == PlanStatus.COMPLETED
