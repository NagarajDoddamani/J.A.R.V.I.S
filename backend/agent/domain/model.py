from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import auto, StrEnum
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================


class AgentType(StrEnum):
    COORDINATOR = auto()
    RESEARCH = auto()
    KNOWLEDGE = auto()
    AUTOMATION = auto()


class AgentStatus(StrEnum):
    IDLE = auto()
    ACTIVE = auto()
    PAUSED = auto()
    DISABLED = auto()


class AgentTaskStatus(StrEnum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class AgentExecutionStatus(StrEnum):
    PENDING = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    FAILED = auto()


# =============================================================================
# Value Objects
# =============================================================================


@dataclass(frozen=True)
class AgentId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class AgentTaskId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class AgentExecutionId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class AgentName:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"AgentName value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.agent.domain.exceptions import InvalidAgentNameError
            raise InvalidAgentNameError("Agent name must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class AgentGoal:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"AgentGoal value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.agent.domain.exceptions import InvalidAgentGoalError
            raise InvalidAgentGoalError("Agent goal must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class AgentInstruction:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"AgentInstruction value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.agent.domain.exceptions import InvalidAgentInstructionError
            raise InvalidAgentInstructionError("Agent instruction must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class AgentResult:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"AgentResult value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.agent.domain.exceptions import InvalidAgentResultError
            raise InvalidAgentResultError("Agent result must not be empty")

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
            from backend.agent.domain.exceptions import InvalidFailureReasonError
            raise InvalidFailureReasonError("Failure reason must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


# =============================================================================
# Domain Events
# =============================================================================


@dataclass(frozen=True)
class AgentCreated:
    agent_id: AgentId
    agent_type: str
    name: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AgentActivated:
    agent_id: AgentId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AgentPaused:
    agent_id: AgentId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AgentDisabled:
    agent_id: AgentId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AgentTaskCreated:
    task_id: AgentTaskId
    agent_id: AgentId
    goal: str
    instruction: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AgentTaskStarted:
    task_id: AgentTaskId
    agent_id: AgentId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AgentTaskCompleted:
    task_id: AgentTaskId
    agent_id: AgentId
    result: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AgentTaskFailed:
    task_id: AgentTaskId
    agent_id: AgentId
    failure_reason: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AgentTaskCancelled:
    task_id: AgentTaskId
    agent_id: AgentId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AgentExecutionStarted:
    execution_id: AgentExecutionId
    agent_id: AgentId
    task_id: AgentTaskId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AgentExecutionCompleted:
    execution_id: AgentExecutionId
    agent_id: AgentId
    task_id: AgentTaskId
    result: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AgentExecutionFailed:
    execution_id: AgentExecutionId
    agent_id: AgentId
    task_id: AgentTaskId
    failure_reason: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


# =============================================================================
# Agent Task Status Transitions
# =============================================================================

VALID_AGENT_TASK_TRANSITIONS: dict[AgentTaskStatus, set[AgentTaskStatus]] = {
    AgentTaskStatus.PENDING: {AgentTaskStatus.RUNNING, AgentTaskStatus.CANCELLED},
    AgentTaskStatus.RUNNING: {AgentTaskStatus.COMPLETED, AgentTaskStatus.FAILED, AgentTaskStatus.CANCELLED},
    AgentTaskStatus.COMPLETED: set(),
    AgentTaskStatus.FAILED: set(),
    AgentTaskStatus.CANCELLED: set(),
}

VALID_AGENT_EXECUTION_TRANSITIONS: dict[AgentExecutionStatus, set[AgentExecutionStatus]] = {
    AgentExecutionStatus.PENDING: {AgentExecutionStatus.EXECUTING},
    AgentExecutionStatus.EXECUTING: {AgentExecutionStatus.COMPLETED, AgentExecutionStatus.FAILED},
    AgentExecutionStatus.COMPLETED: set(),
    AgentExecutionStatus.FAILED: set(),
}

VALID_AGENT_STATUS_TRANSITIONS: dict[AgentStatus, set[AgentStatus]] = {
    AgentStatus.IDLE: {AgentStatus.ACTIVE, AgentStatus.DISABLED},
    AgentStatus.ACTIVE: {AgentStatus.PAUSED, AgentStatus.DISABLED},
    AgentStatus.PAUSED: {AgentStatus.ACTIVE, AgentStatus.DISABLED},
    AgentStatus.DISABLED: set(),
}


# =============================================================================
# Entities
# =============================================================================


class AgentTask:
    """A task assigned to an agent."""

    def __init__(
        self,
        task_id: AgentTaskId | None = None,
        goal: AgentGoal | None = None,
        instruction: AgentInstruction | None = None,
        status: AgentTaskStatus = AgentTaskStatus.PENDING,
        result: AgentResult | None = None,
        failure_reason: FailureReason | None = None,
        agent_id: AgentId | None = None,
    ) -> None:
        self._task_id = task_id or AgentTaskId()
        self._goal = goal
        self._instruction = instruction
        self._status = status
        self._result = result
        self._failure_reason = failure_reason
        self._agent_id = agent_id
        self._events: list[
            AgentTaskCreated
            | AgentTaskStarted
            | AgentTaskCompleted
            | AgentTaskFailed
            | AgentTaskCancelled
        ] = []

    @property
    def task_id(self) -> AgentTaskId:
        return self._task_id

    @property
    def goal(self) -> AgentGoal | None:
        return self._goal

    @property
    def instruction(self) -> AgentInstruction | None:
        return self._instruction

    @property
    def status(self) -> AgentTaskStatus:
        return self._status

    @property
    def result(self) -> AgentResult | None:
        return self._result

    @property
    def failure_reason(self) -> FailureReason | None:
        return self._failure_reason

    @property
    def agent_id(self) -> AgentId | None:
        return self._agent_id

    @property
    def events(
        self,
    ) -> list[
        AgentTaskCreated
        | AgentTaskStarted
        | AgentTaskCompleted
        | AgentTaskFailed
        | AgentTaskCancelled
    ]:
        return list(self._events)

    @property
    def is_terminal(self) -> bool:
        return self._status in (
            AgentTaskStatus.COMPLETED,
            AgentTaskStatus.FAILED,
            AgentTaskStatus.CANCELLED,
        )

    def start(self) -> None:
        from backend.agent.domain.rules import (
            assert_agent_task_can_transition,
        )

        assert_agent_task_can_transition(self._status, AgentTaskStatus.RUNNING)
        self._status = AgentTaskStatus.RUNNING

    def complete(self, result: AgentResult) -> None:
        from backend.agent.domain.rules import (
            assert_agent_task_can_transition,
            assert_agent_task_started_before,
            assert_agent_result_required,
        )

        assert_agent_task_can_transition(self._status, AgentTaskStatus.COMPLETED)
        assert_agent_task_started_before(self, "complete")
        assert_agent_result_required(result)
        self._result = result
        self._status = AgentTaskStatus.COMPLETED

    def fail(self, reason: FailureReason) -> None:
        from backend.agent.domain.rules import (
            assert_agent_task_can_transition,
            assert_agent_task_started_before,
            assert_failure_reason_required,
        )

        assert_agent_task_can_transition(self._status, AgentTaskStatus.FAILED)
        assert_agent_task_started_before(self, "fail")
        assert_failure_reason_required(reason)
        self._failure_reason = reason
        self._status = AgentTaskStatus.FAILED

    def cancel(self) -> None:
        from backend.agent.domain.rules import (
            assert_agent_task_can_transition,
        )

        assert_agent_task_can_transition(self._status, AgentTaskStatus.CANCELLED)
        self._status = AgentTaskStatus.CANCELLED

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"AgentTask(id={self._task_id}, "
            f"status={self._status.value})"
        )


class AgentExecution:
    """A single execution of an agent task."""

    def __init__(
        self,
        execution_id: AgentExecutionId | None = None,
        task_id: AgentTaskId | None = None,
        status: AgentExecutionStatus = AgentExecutionStatus.PENDING,
        result: AgentResult | None = None,
        failure_reason: FailureReason | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        agent_id: AgentId | None = None,
    ) -> None:
        self._execution_id = execution_id or AgentExecutionId()
        self._task_id = task_id or AgentTaskId()
        self._status = status
        self._result = result
        self._failure_reason = failure_reason
        self._started_at = started_at
        self._completed_at = completed_at
        self._agent_id = agent_id

    @property
    def execution_id(self) -> AgentExecutionId:
        return self._execution_id

    @property
    def task_id(self) -> AgentTaskId:
        return self._task_id

    @property
    def status(self) -> AgentExecutionStatus:
        return self._status

    @property
    def result(self) -> AgentResult | None:
        return self._result

    @property
    def failure_reason(self) -> FailureReason | None:
        return self._failure_reason

    @property
    def started_at(self) -> datetime | None:
        return self._started_at

    @property
    def completed_at(self) -> datetime | None:
        return self._completed_at

    @property
    def agent_id(self) -> AgentId | None:
        return self._agent_id

    @property
    def is_terminal(self) -> bool:
        return self._status in (
            AgentExecutionStatus.COMPLETED,
            AgentExecutionStatus.FAILED,
        )

    def start(self) -> None:
        from backend.agent.domain.rules import (
            assert_agent_execution_can_transition,
        )

        assert_agent_execution_can_transition(self._status, AgentExecutionStatus.EXECUTING)
        self._status = AgentExecutionStatus.EXECUTING
        self._started_at = datetime.now(tz=timezone.utc)

    def complete(self, result: AgentResult) -> None:
        from backend.agent.domain.rules import (
            assert_agent_execution_can_transition,
            assert_agent_execution_started_before,
            assert_agent_result_required,
        )

        assert_agent_execution_can_transition(self._status, AgentExecutionStatus.COMPLETED)
        assert_agent_execution_started_before(self, "complete")
        assert_agent_result_required(result)
        self._result = result
        self._status = AgentExecutionStatus.COMPLETED
        self._completed_at = datetime.now(tz=timezone.utc)

    def fail(self, reason: FailureReason) -> None:
        from backend.agent.domain.rules import (
            assert_agent_execution_can_transition,
            assert_agent_execution_started_before,
            assert_failure_reason_required,
        )

        assert_agent_execution_can_transition(self._status, AgentExecutionStatus.FAILED)
        assert_agent_execution_started_before(self, "fail")
        assert_failure_reason_required(reason)
        self._failure_reason = reason
        self._status = AgentExecutionStatus.FAILED
        self._completed_at = datetime.now(tz=timezone.utc)

    def __repr__(self) -> str:
        return (
            f"AgentExecution(id={self._execution_id}, "
            f"status={self._status.value})"
        )


class Agent:
    """Aggregate root for the agent domain."""

    def __init__(
        self,
        agent_id: AgentId | None = None,
        agent_type: AgentType = AgentType.COORDINATOR,
        name: AgentName | None = None,
        status: AgentStatus = AgentStatus.IDLE,
        tasks: list[AgentTask] | None = None,
        executions: list[AgentExecution] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._agent_id = agent_id or AgentId()
        self._agent_type = agent_type
        self._name = name
        self._status = status
        self._tasks = tasks or []
        self._executions = executions or []
        self._created_at = created_at or datetime.now(tz=timezone.utc)
        self._updated_at = updated_at
        self._events: list[
            AgentCreated
            | AgentActivated
            | AgentPaused
            | AgentDisabled
            | AgentTaskCreated
            | AgentTaskStarted
            | AgentTaskCompleted
            | AgentTaskFailed
            | AgentTaskCancelled
            | AgentExecutionStarted
            | AgentExecutionCompleted
            | AgentExecutionFailed
        ] = []

    # -- properties ---------------------------------------------------------

    @property
    def agent_id(self) -> AgentId:
        return self._agent_id

    @property
    def agent_type(self) -> AgentType:
        return self._agent_type

    @property
    def name(self) -> AgentName | None:
        return self._name

    @property
    def status(self) -> AgentStatus:
        return self._status

    @property
    def tasks(self) -> list[AgentTask]:
        return list(self._tasks)

    @property
    def executions(self) -> list[AgentExecution]:
        return list(self._executions)

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @property
    def events(
        self,
    ) -> list[
        AgentCreated
        | AgentActivated
        | AgentPaused
        | AgentDisabled
        | AgentTaskCreated
        | AgentTaskStarted
        | AgentTaskCompleted
        | AgentTaskFailed
        | AgentTaskCancelled
        | AgentExecutionStarted
        | AgentExecutionCompleted
        | AgentExecutionFailed
    ]:
        return list(self._events)

    @property
    def is_disabled(self) -> bool:
        return self._status == AgentStatus.DISABLED

    @property
    def is_paused(self) -> bool:
        return self._status == AgentStatus.PAUSED

    @property
    def is_terminal(self) -> bool:
        return self._status == AgentStatus.DISABLED

    # -- commands -----------------------------------------------------------

    def activate(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.agent.domain.rules import (
            assert_agent_status_can_transition,
        )

        assert_agent_status_can_transition(self._status, AgentStatus.ACTIVE)
        self._status = AgentStatus.ACTIVE
        self._updated_at = now
        self._events.append(
            AgentActivated(
                agent_id=self._agent_id, occurred_at=now
            )
        )

    def pause(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.agent.domain.rules import (
            assert_agent_status_can_transition,
        )

        assert_agent_status_can_transition(self._status, AgentStatus.PAUSED)
        self._status = AgentStatus.PAUSED
        self._updated_at = now
        self._events.append(
            AgentPaused(
                agent_id=self._agent_id, occurred_at=now
            )
        )

    def disable(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.agent.domain.rules import (
            assert_agent_status_can_transition,
        )

        assert_agent_status_can_transition(self._status, AgentStatus.DISABLED)
        self._status = AgentStatus.DISABLED
        self._updated_at = now
        self._events.append(
            AgentDisabled(
                agent_id=self._agent_id, occurred_at=now
            )
        )

    def add_task(self, task: AgentTask) -> None:
        from backend.agent.domain.rules import (
            assert_agent_not_disabled_or_paused,
            assert_agent_task_id_unique,
        )

        assert_agent_not_disabled_or_paused(self)
        assert_agent_task_id_unique(task.task_id, self._tasks)
        task._agent_id = self._agent_id
        self._tasks.append(task)
        self._updated_at = datetime.now(tz=timezone.utc)
        self._events.append(
            AgentTaskCreated(
                task_id=task.task_id,
                agent_id=self._agent_id,
                goal=str(task.goal) if task.goal else "",
                instruction=str(task.instruction) if task.instruction else "",
                occurred_at=datetime.now(tz=timezone.utc),
            )
        )

    def start_task(self, task_id: AgentTaskId) -> None:
        from backend.agent.domain.rules import (
            assert_agent_not_disabled_or_paused,
        )

        assert_agent_not_disabled_or_paused(self)
        task = self._find_task(task_id)
        task.start()
        self._updated_at = datetime.now(tz=timezone.utc)
        self._events.append(
            AgentTaskStarted(
                task_id=task_id,
                agent_id=self._agent_id,
                occurred_at=datetime.now(tz=timezone.utc),
            )
        )

    def complete_task(self, task_id: AgentTaskId, result: AgentResult) -> None:
        task = self._find_task(task_id)
        task.complete(result)
        self._updated_at = datetime.now(tz=timezone.utc)
        self._events.append(
            AgentTaskCompleted(
                task_id=task_id,
                agent_id=self._agent_id,
                result=result.value,
                occurred_at=datetime.now(tz=timezone.utc),
            )
        )

    def fail_task(self, task_id: AgentTaskId, reason: FailureReason) -> None:
        task = self._find_task(task_id)
        task.fail(reason)
        self._updated_at = datetime.now(tz=timezone.utc)
        self._events.append(
            AgentTaskFailed(
                task_id=task_id,
                agent_id=self._agent_id,
                failure_reason=reason.value,
                occurred_at=datetime.now(tz=timezone.utc),
            )
        )

    def cancel_task(self, task_id: AgentTaskId) -> None:
        task = self._find_task(task_id)
        task.cancel()
        self._updated_at = datetime.now(tz=timezone.utc)
        self._events.append(
            AgentTaskCancelled(
                task_id=task_id,
                agent_id=self._agent_id,
                occurred_at=datetime.now(tz=timezone.utc),
            )
        )

    def start_execution(self, task_id: AgentTaskId) -> AgentExecution:
        now = datetime.now(tz=timezone.utc)
        from backend.agent.domain.rules import (
            assert_agent_not_disabled,
            assert_agent_not_paused,
            assert_agent_execution_id_unique,
        )

        assert_agent_not_disabled(self)
        assert_agent_not_paused(self)
        task = self._find_task(task_id)
        execution = AgentExecution(
            task_id=task_id,
            agent_id=self._agent_id,
        )
        assert_agent_execution_id_unique(execution.execution_id, self._executions)
        execution.start()
        self._executions.append(execution)
        self._updated_at = now
        self._events.append(
            AgentExecutionStarted(
                execution_id=execution.execution_id,
                agent_id=self._agent_id,
                task_id=task_id,
                occurred_at=now,
            )
        )
        return execution

    def complete_execution(self, execution_id: AgentExecutionId, result: AgentResult) -> None:
        now = datetime.now(tz=timezone.utc)
        execution = self._find_execution(execution_id)
        execution.complete(result)
        self._updated_at = now
        self._events.append(
            AgentExecutionCompleted(
                execution_id=execution_id,
                agent_id=self._agent_id,
                task_id=execution.task_id,
                result=result.value,
                occurred_at=now,
            )
        )

    def fail_execution(self, execution_id: AgentExecutionId, reason: FailureReason) -> None:
        now = datetime.now(tz=timezone.utc)
        execution = self._find_execution(execution_id)
        execution.fail(reason)
        self._updated_at = now
        self._events.append(
            AgentExecutionFailed(
                execution_id=execution_id,
                agent_id=self._agent_id,
                task_id=execution.task_id,
                failure_reason=reason.value,
                occurred_at=now,
            )
        )

    # -- internal -----------------------------------------------------------

    def _find_task(self, task_id: AgentTaskId) -> AgentTask:
        for task in self._tasks:
            if task.task_id == task_id:
                return task
        from backend.agent.domain.exceptions import AgentTaskNotFoundError
        raise AgentTaskNotFoundError(str(task_id))

    def _find_execution(self, execution_id: AgentExecutionId) -> AgentExecution:
        for execution in self._executions:
            if execution.execution_id == execution_id:
                return execution
        from backend.agent.domain.exceptions import AgentExecutionNotFoundError
        raise AgentExecutionNotFoundError(str(execution_id))

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"Agent(id={self._agent_id}, "
            f"name={self._name}, "
            f"type={self._agent_type.value}, "
            f"status={self._status.value})"
        )
