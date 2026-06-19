from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import auto, StrEnum
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================


class PlanStatus(StrEnum):
    DRAFT = auto()
    APPROVED = auto()
    PLANNING = auto()
    READY = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class TaskStatus(StrEnum):
    PENDING = auto()
    ASSIGNED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class PlanPriority(StrEnum):
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()


class ExecutionStrategy(StrEnum):
    SEQUENTIAL = auto()
    PARALLEL = auto()
    HYBRID = auto()


class AgentType(StrEnum):
    PLANNER = auto()
    RESEARCH = auto()
    AUTOMATION = auto()
    MEMORY = auto()
    KNOWLEDGE = auto()
    NOTIFICATION = auto()
    POLICY = auto()


# =============================================================================
# Value Objects
# =============================================================================


@dataclass(frozen=True)
class PlanId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class TaskId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class ExecutionStepId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class UserRequest:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"UserRequest value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.planner.domain.exceptions import InvalidUserRequestError

            raise InvalidUserRequestError("User request must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class PlanGoal:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"PlanGoal value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.planner.domain.exceptions import InvalidPlanGoalError

            raise InvalidPlanGoalError("Plan goal must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class TaskDescription:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"TaskDescription value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.planner.domain.exceptions import InvalidTaskDescriptionError

            raise InvalidTaskDescriptionError("Task description must not be empty")

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
            from backend.planner.domain.exceptions import InvalidFailureReasonError

            raise InvalidFailureReasonError("Failure reason must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class EstimatedDuration:
    value: float

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)):
            msg = f"EstimatedDuration value must be a number, got {type(self.value).__name__}"
            raise TypeError(msg)
        if self.value <= 0:
            from backend.planner.domain.exceptions import InvalidEstimatedDurationError

            raise InvalidEstimatedDurationError(
                f"Estimated duration must be positive, got {self.value}"
            )

    def __float__(self) -> float:
        return float(self.value)


# =============================================================================
# Domain Events
# =============================================================================


@dataclass(frozen=True)
class PlanCreated:
    plan_id: PlanId
    user_request: str
    goal: str
    priority: str
    strategy: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PlanApproved:
    plan_id: PlanId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PlanReady:
    plan_id: PlanId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PlanExecutionStarted:
    plan_id: PlanId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PlanCompleted:
    plan_id: PlanId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PlanFailed:
    plan_id: PlanId
    failure_reason: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PlanCancelled:
    plan_id: PlanId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class TaskCreated:
    task_id: TaskId
    description: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class TaskAssigned:
    task_id: TaskId
    assigned_agent: AgentType
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class TaskCompleted:
    task_id: TaskId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class TaskFailed:
    task_id: TaskId
    failure_reason: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


# =============================================================================
# Entities
# =============================================================================


class ExecutionStep:
    """A single execution step within a task."""

    def __init__(
        self,
        step_id: ExecutionStepId | None = None,
        task_id: TaskId | None = None,
        step_order: int = 0,
        description: str = "",
        status: TaskStatus = TaskStatus.PENDING,
    ) -> None:
        self._step_id = step_id or ExecutionStepId()
        self._task_id = task_id
        self._step_order = step_order
        self._description = description
        self._status = status

    # -- properties ---------------------------------------------------------

    @property
    def step_id(self) -> ExecutionStepId:
        return self._step_id

    @property
    def task_id(self) -> TaskId | None:
        return self._task_id

    @property
    def step_order(self) -> int:
        return self._step_order

    @property
    def description(self) -> str:
        return self._description

    @property
    def status(self) -> TaskStatus:
        return self._status

    def __repr__(self) -> str:
        return (
            f"ExecutionStep(id={self._step_id}, "
            f"order={self._step_order}, "
            f"status={self._status.value})"
        )


class Task:
    """A task within a plan."""

    def __init__(
        self,
        task_id: TaskId | None = None,
        plan_id: PlanId | None = None,
        description: TaskDescription | None = None,
        assigned_agent: AgentType | None = None,
        status: TaskStatus = TaskStatus.PENDING,
        failure_reason: FailureReason | None = None,
        estimated_duration: EstimatedDuration | None = None,
        execution_steps: list[ExecutionStep] | None = None,
    ) -> None:
        self._task_id = task_id or TaskId()
        self._plan_id = plan_id
        self._description = description
        self._assigned_agent = assigned_agent
        self._status = status
        self._failure_reason = failure_reason
        self._estimated_duration = estimated_duration
        self._execution_steps = execution_steps or []
        self._events: list[TaskAssigned | TaskCompleted | TaskFailed] = []

    # -- properties ---------------------------------------------------------

    @property
    def task_id(self) -> TaskId:
        return self._task_id

    @property
    def plan_id(self) -> PlanId | None:
        return self._plan_id

    @property
    def description(self) -> TaskDescription | None:
        return self._description

    @property
    def assigned_agent(self) -> AgentType | None:
        return self._assigned_agent

    @property
    def status(self) -> TaskStatus:
        return self._status

    @property
    def failure_reason(self) -> FailureReason | None:
        return self._failure_reason

    @property
    def estimated_duration(self) -> EstimatedDuration | None:
        return self._estimated_duration

    @property
    def execution_steps(self) -> list[ExecutionStep]:
        return list(self._execution_steps)

    @property
    def events(self) -> list[TaskAssigned | TaskCompleted | TaskFailed]:
        return list(self._events)

    @property
    def is_terminal(self) -> bool:
        return self._status in (
            TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED,
        )

    # -- commands -----------------------------------------------------------

    def assign(self, agent: AgentType) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.planner.domain.rules import (
            assert_agent_valid,
            assert_task_can_transition,
        )

        assert_agent_valid(agent)
        assert_task_can_transition(self._status, TaskStatus.ASSIGNED)
        self._assigned_agent = agent
        self._status = TaskStatus.ASSIGNED
        self._events.append(
            TaskAssigned(task_id=self._task_id, assigned_agent=agent, occurred_at=now)
        )

    def start(self) -> None:
        from backend.planner.domain.rules import (
            assert_task_can_transition,
            assert_task_has_assigned_agent,
        )

        assert_task_has_assigned_agent(self)
        assert_task_can_transition(self._status, TaskStatus.RUNNING)
        self._status = TaskStatus.RUNNING

    def complete(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.planner.domain.rules import assert_task_can_transition

        assert_task_can_transition(self._status, TaskStatus.COMPLETED)
        self._status = TaskStatus.COMPLETED
        self._events.append(
            TaskCompleted(task_id=self._task_id, occurred_at=now)
        )

    def fail(self, reason: FailureReason) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.planner.domain.rules import (
            assert_failure_reason_provided,
            assert_task_can_transition,
        )

        assert_failure_reason_provided(reason)
        assert_task_can_transition(self._status, TaskStatus.FAILED)
        self._failure_reason = reason
        self._status = TaskStatus.FAILED
        self._events.append(
            TaskFailed(
                task_id=self._task_id,
                failure_reason=reason.value,
                occurred_at=now,
            )
        )

    def cancel(self) -> None:
        from backend.planner.domain.rules import assert_task_can_transition

        assert_task_can_transition(self._status, TaskStatus.CANCELLED)
        self._status = TaskStatus.CANCELLED

    # -- internal -----------------------------------------------------------

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"Task(id={self._task_id}, "
            f"status={self._status.value})"
        )


class Plan:
    """Aggregate root for the planner domain."""

    def __init__(
        self,
        plan_id: PlanId | None = None,
        user_request: UserRequest | None = None,
        goal: PlanGoal | None = None,
        priority: PlanPriority = PlanPriority.NORMAL,
        strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL,
        status: PlanStatus = PlanStatus.DRAFT,
        tasks: list[Task] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._plan_id = plan_id or PlanId()
        self._user_request = user_request
        self._goal = goal
        self._priority = priority
        self._strategy = strategy
        self._status = status
        self._tasks = tasks or []
        self._created_at = created_at or datetime.now(tz=timezone.utc)
        self._updated_at = updated_at
        self._events: list[PlanApproved | PlanReady | PlanExecutionStarted | PlanCompleted | PlanFailed | PlanCancelled] = []

    # -- properties ---------------------------------------------------------

    @property
    def plan_id(self) -> PlanId:
        return self._plan_id

    @property
    def user_request(self) -> UserRequest | None:
        return self._user_request

    @property
    def goal(self) -> PlanGoal | None:
        return self._goal

    @property
    def priority(self) -> PlanPriority:
        return self._priority

    @property
    def strategy(self) -> ExecutionStrategy:
        return self._strategy

    @property
    def status(self) -> PlanStatus:
        return self._status

    @property
    def tasks(self) -> list[Task]:
        return list(self._tasks)

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @property
    def events(self) -> list[PlanApproved | PlanReady | PlanExecutionStarted | PlanCompleted | PlanFailed | PlanCancelled]:
        return list(self._events)

    @property
    def is_terminal(self) -> bool:
        return self._status in (
            PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.CANCELLED,
        )

    # -- commands -----------------------------------------------------------

    def approve(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.planner.domain.rules import assert_plan_can_transition

        assert_plan_can_transition(self._status, PlanStatus.APPROVED)
        self._status = PlanStatus.APPROVED
        self._updated_at = now
        self._events.append(
            PlanApproved(plan_id=self._plan_id, occurred_at=now)
        )

    def start_planning(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.planner.domain.rules import assert_plan_can_transition

        assert_plan_can_transition(self._status, PlanStatus.PLANNING)
        self._status = PlanStatus.PLANNING
        self._updated_at = now

    def mark_ready(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.planner.domain.rules import (
            assert_plan_can_transition,
            assert_plan_has_tasks,
        )

        assert_plan_has_tasks(self)
        assert_plan_can_transition(self._status, PlanStatus.READY)
        self._status = PlanStatus.READY
        self._updated_at = now
        self._events.append(
            PlanReady(plan_id=self._plan_id, occurred_at=now)
        )

    def start_execution(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.planner.domain.rules import (
            assert_plan_can_transition,
            assert_plan_has_tasks,
            assert_plan_is_ready,
        )

        assert_plan_is_ready(self)
        assert_plan_has_tasks(self)
        assert_plan_can_transition(self._status, PlanStatus.EXECUTING)
        self._status = PlanStatus.EXECUTING
        self._updated_at = now
        self._events.append(
            PlanExecutionStarted(plan_id=self._plan_id, occurred_at=now)
        )

    def complete(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.planner.domain.rules import assert_plan_can_transition

        assert_plan_can_transition(self._status, PlanStatus.COMPLETED)
        self._status = PlanStatus.COMPLETED
        self._updated_at = now
        self._events.append(
            PlanCompleted(plan_id=self._plan_id, occurred_at=now)
        )

    def fail(self, reason: FailureReason) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.planner.domain.rules import (
            assert_plan_can_transition,
            assert_plan_failure_reason_provided,
        )

        assert_plan_failure_reason_provided(reason)
        assert_plan_can_transition(self._status, PlanStatus.FAILED)
        self._status = PlanStatus.FAILED
        self._updated_at = now
        self._events.append(
            PlanFailed(
                plan_id=self._plan_id,
                failure_reason=reason.value,
                occurred_at=now,
            )
        )

    def cancel(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.planner.domain.rules import assert_plan_can_transition

        assert_plan_can_transition(self._status, PlanStatus.CANCELLED)
        self._status = PlanStatus.CANCELLED
        self._updated_at = now
        self._events.append(
            PlanCancelled(plan_id=self._plan_id, occurred_at=now)
        )

    def add_task(self, task: Task) -> None:
        from backend.planner.domain.rules import (
            assert_plan_not_terminal,
            assert_task_id_unique,
        )

        assert_plan_not_terminal(self)
        assert_task_id_unique(task.task_id, self._tasks)
        self._tasks.append(task)
        self._updated_at = datetime.now(tz=timezone.utc)

    # -- internal -----------------------------------------------------------

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"Plan(id={self._plan_id}, "
            f"status={self._status.value}, "
            f"priority={self._priority.value})"
        )
