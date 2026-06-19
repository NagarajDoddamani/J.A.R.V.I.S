from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import auto, StrEnum
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================


class OrchestrationStatus(StrEnum):
    CREATED = auto()
    PLANNING = auto()
    RESEARCHING = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class WorkflowStepStatus(StrEnum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()


class AgentRole(StrEnum):
    PLANNER = auto()
    RESEARCH = auto()
    AUTOMATION = auto()
    MEMORY = auto()
    KNOWLEDGE = auto()
    POLICY = auto()


class ExecutionMode(StrEnum):
    SEQUENTIAL = auto()
    PARALLEL = auto()
    HYBRID = auto()


# =============================================================================
# Value Objects
# =============================================================================


@dataclass(frozen=True)
class OrchestrationId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class WorkflowId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class UserIntent:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"UserIntent value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.orchestrator.domain.exceptions import InvalidUserIntentError

            raise InvalidUserIntentError("User intent must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class WorkflowGoal:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"WorkflowGoal value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.orchestrator.domain.exceptions import InvalidWorkflowGoalError

            raise InvalidWorkflowGoalError("Workflow goal must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class ExecutionResult:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"ExecutionResult value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.orchestrator.domain.exceptions import InvalidExecutionResultError

            raise InvalidExecutionResultError("Execution result must not be empty")

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
            from backend.orchestrator.domain.exceptions import InvalidFailureReasonError

            raise InvalidFailureReasonError("Failure reason must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class AgentReference:
    role: AgentRole

    def __post_init__(self) -> None:
        if not isinstance(self.role, AgentRole):
            from backend.orchestrator.domain.exceptions import InvalidAgentRoleError

            raise InvalidAgentRoleError(str(self.role))

    def __str__(self) -> str:
        return self.role.value


@dataclass(frozen=True)
class ExecutionOrder:
    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int):
            msg = f"ExecutionOrder value must be an int, got {type(self.value).__name__}"
            raise TypeError(msg)
        if self.value < 0:
            from backend.orchestrator.domain.exceptions import InvalidExecutionOrderError

            raise InvalidExecutionOrderError(self.value)

    def __int__(self) -> int:
        return self.value


# =============================================================================
# Domain Events
# =============================================================================


@dataclass(frozen=True)
class OrchestrationCreated:
    orchestration_id: OrchestrationId
    intent: str
    goal: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class OrchestrationPlanningStarted:
    orchestration_id: OrchestrationId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class OrchestrationResearchStarted:
    orchestration_id: OrchestrationId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class OrchestrationExecutionStarted:
    orchestration_id: OrchestrationId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class OrchestrationCompleted:
    orchestration_id: OrchestrationId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class OrchestrationFailed:
    orchestration_id: OrchestrationId
    failure_reason: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class OrchestrationCancelled:
    orchestration_id: OrchestrationId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class WorkflowCreated:
    workflow_id: WorkflowId
    orchestration_id: OrchestrationId
    goal: str
    mode: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class WorkflowCompleted:
    workflow_id: WorkflowId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class WorkflowFailed:
    workflow_id: WorkflowId
    failure_reason: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class WorkflowStepStarted:
    step_id: WorkflowId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class WorkflowStepCompleted:
    step_id: WorkflowId
    result: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class WorkflowStepFailed:
    step_id: WorkflowId
    failure_reason: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


# =============================================================================
# WorkflowStep Status Transitions
# =============================================================================

VALID_WORKFLOW_STEP_TRANSITIONS: dict[WorkflowStepStatus, set[WorkflowStepStatus]] = {
    WorkflowStepStatus.PENDING: {WorkflowStepStatus.RUNNING, WorkflowStepStatus.SKIPPED},
    WorkflowStepStatus.RUNNING: {WorkflowStepStatus.COMPLETED, WorkflowStepStatus.FAILED},
    WorkflowStepStatus.COMPLETED: set(),
    WorkflowStepStatus.FAILED: set(),
    WorkflowStepStatus.SKIPPED: set(),
}


# =============================================================================
# Entities
# =============================================================================


class WorkflowStep:
    """A single step within a workflow, assigned to a specific agent role."""

    def __init__(
        self,
        step_id: WorkflowId | None = None,
        agent_role: AgentRole = AgentRole.RESEARCH,
        execution_order: ExecutionOrder | None = None,
        status: WorkflowStepStatus = WorkflowStepStatus.PENDING,
        result: ExecutionResult | None = None,
        failure_reason: FailureReason | None = None,
    ) -> None:
        self._step_id = step_id or WorkflowId()
        self._agent_role = agent_role
        self._execution_order = execution_order or ExecutionOrder(value=0)
        self._status = status
        self._result = result
        self._failure_reason = failure_reason
        self._events: list[WorkflowStepStarted | WorkflowStepCompleted | WorkflowStepFailed] = []

    # -- properties ---------------------------------------------------------

    @property
    def step_id(self) -> WorkflowId:
        return self._step_id

    @property
    def agent_role(self) -> AgentRole:
        return self._agent_role

    @property
    def execution_order(self) -> ExecutionOrder:
        return self._execution_order

    @property
    def status(self) -> WorkflowStepStatus:
        return self._status

    @property
    def result(self) -> ExecutionResult | None:
        return self._result

    @property
    def failure_reason(self) -> FailureReason | None:
        return self._failure_reason

    @property
    def events(self) -> list[WorkflowStepStarted | WorkflowStepCompleted | WorkflowStepFailed]:
        return list(self._events)

    @property
    def is_terminal(self) -> bool:
        return self._status in (
            WorkflowStepStatus.COMPLETED,
            WorkflowStepStatus.FAILED,
            WorkflowStepStatus.SKIPPED,
        )

    # -- commands -----------------------------------------------------------

    def start(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.orchestrator.domain.rules import assert_step_can_transition

        assert_step_can_transition(self._status, WorkflowStepStatus.RUNNING)
        self._status = WorkflowStepStatus.RUNNING
        self._events.append(
            WorkflowStepStarted(step_id=self._step_id, occurred_at=now)
        )

    def complete(self, result: ExecutionResult) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.orchestrator.domain.rules import (
            assert_execution_result_required,
            assert_step_can_transition,
        )

        assert_execution_result_required(result)
        assert_step_can_transition(self._status, WorkflowStepStatus.COMPLETED)
        self._result = result
        self._status = WorkflowStepStatus.COMPLETED
        self._events.append(
            WorkflowStepCompleted(
                step_id=self._step_id,
                result=result.value,
                occurred_at=now,
            )
        )

    def fail(self, reason: FailureReason) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.orchestrator.domain.rules import (
            assert_failure_reason_required,
            assert_step_can_transition,
        )

        assert_failure_reason_required(reason)
        assert_step_can_transition(self._status, WorkflowStepStatus.FAILED)
        self._failure_reason = reason
        self._status = WorkflowStepStatus.FAILED
        self._events.append(
            WorkflowStepFailed(
                step_id=self._step_id,
                failure_reason=reason.value,
                occurred_at=now,
            )
        )

    def skip(self) -> None:
        from backend.orchestrator.domain.rules import assert_step_can_transition

        assert_step_can_transition(self._status, WorkflowStepStatus.SKIPPED)
        self._status = WorkflowStepStatus.SKIPPED

    # -- internal -----------------------------------------------------------

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"WorkflowStep(id={self._step_id}, "
            f"role={self._agent_role.value}, "
            f"order={self._execution_order.value}, "
            f"status={self._status.value})"
        )


# =============================================================================
# Workflow Status Transitions
# =============================================================================


class WorkflowStatus(StrEnum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()


VALID_WORKFLOW_TRANSITIONS: dict[WorkflowStatus, set[WorkflowStatus]] = {
    WorkflowStatus.PENDING: {WorkflowStatus.RUNNING},
    WorkflowStatus.RUNNING: {WorkflowStatus.COMPLETED, WorkflowStatus.FAILED},
    WorkflowStatus.COMPLETED: set(),
    WorkflowStatus.FAILED: set(),
}


class Workflow:
    """A workflow containing multiple steps with an execution mode."""

    def __init__(
        self,
        workflow_id: WorkflowId | None = None,
        goal: WorkflowGoal | None = None,
        mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
        steps: list[WorkflowStep] | None = None,
    ) -> None:
        self._workflow_id = workflow_id or WorkflowId()
        self._goal = goal
        self._mode = mode
        self._status = WorkflowStatus.PENDING
        self._steps = steps or []
        self._events: list[WorkflowCreated | WorkflowCompleted | WorkflowFailed] = []

    # -- properties ---------------------------------------------------------

    @property
    def workflow_id(self) -> WorkflowId:
        return self._workflow_id

    @property
    def goal(self) -> WorkflowGoal | None:
        return self._goal

    @property
    def mode(self) -> ExecutionMode:
        return self._mode

    @property
    def status(self) -> WorkflowStatus:
        return self._status

    @property
    def steps(self) -> list[WorkflowStep]:
        return list(self._steps)

    @property
    def events(self) -> list[WorkflowCreated | WorkflowCompleted | WorkflowFailed]:
        return list(self._events)

    @property
    def is_terminal(self) -> bool:
        return self._status in (
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
        )

    # -- commands -----------------------------------------------------------

    def add_step(self, step: WorkflowStep) -> None:
        from backend.orchestrator.domain.rules import (
            assert_step_execution_order_unique,
            assert_workflow_not_terminal,
        )

        assert_workflow_not_terminal(self)
        assert_step_execution_order_unique(step.execution_order, self._steps, self._mode)
        self._steps.append(step)

    def start(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.orchestrator.domain.rules import (
            assert_hybrid_mode_min_steps,
            assert_workflow_can_transition,
            assert_workflow_has_steps,
        )

        assert_workflow_has_steps(self)
        assert_hybrid_mode_min_steps(self._mode, len(self._steps))
        assert_workflow_can_transition(self._status, WorkflowStatus.RUNNING)
        self._status = WorkflowStatus.RUNNING
        self._events.append(
            WorkflowCreated(
                workflow_id=self._workflow_id,
                orchestration_id=OrchestrationId(),
                goal=str(self._goal) if self._goal else "",
                mode=self._mode.value,
                occurred_at=now,
            )
        )

    def complete(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.orchestrator.domain.rules import (
            assert_workflow_can_transition,
            assert_workflow_started_before,
        )

        assert_workflow_started_before(self, "complete")
        assert_workflow_can_transition(self._status, WorkflowStatus.COMPLETED)
        self._status = WorkflowStatus.COMPLETED
        self._events.append(
            WorkflowCompleted(workflow_id=self._workflow_id, occurred_at=now)
        )

    def fail(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.orchestrator.domain.rules import (
            assert_workflow_can_transition,
            assert_workflow_started_before,
        )

        assert_workflow_started_before(self, "fail")
        assert_workflow_can_transition(self._status, WorkflowStatus.FAILED)
        self._status = WorkflowStatus.FAILED
        self._events.append(
            WorkflowFailed(
                workflow_id=self._workflow_id,
                failure_reason="Workflow execution failed",
                occurred_at=now,
            )
        )

    # -- internal -----------------------------------------------------------

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"Workflow(id={self._workflow_id}, "
            f"mode={self._mode.value}, "
            f"status={self._status.value})"
        )


# =============================================================================
# Orchestration Status Transitions
# =============================================================================

VALID_ORCHESTRATION_TRANSITIONS: dict[OrchestrationStatus, set[OrchestrationStatus]] = {
    OrchestrationStatus.CREATED: {OrchestrationStatus.PLANNING, OrchestrationStatus.CANCELLED},
    OrchestrationStatus.PLANNING: {OrchestrationStatus.RESEARCHING, OrchestrationStatus.FAILED, OrchestrationStatus.CANCELLED},
    OrchestrationStatus.RESEARCHING: {OrchestrationStatus.EXECUTING, OrchestrationStatus.FAILED, OrchestrationStatus.CANCELLED},
    OrchestrationStatus.EXECUTING: {OrchestrationStatus.COMPLETED, OrchestrationStatus.FAILED, OrchestrationStatus.CANCELLED},
    OrchestrationStatus.COMPLETED: set(),
    OrchestrationStatus.FAILED: set(),
    OrchestrationStatus.CANCELLED: set(),
}


class Orchestration:
    """Aggregate root for the orchestrator domain."""

    def __init__(
        self,
        orchestration_id: OrchestrationId | None = None,
        intent: UserIntent | None = None,
        goal: WorkflowGoal | None = None,
        status: OrchestrationStatus = OrchestrationStatus.CREATED,
        workflows: list[Workflow] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._orchestration_id = orchestration_id or OrchestrationId()
        self._intent = intent
        self._goal = goal
        self._status = status
        self._workflows = workflows or []
        self._created_at = created_at or datetime.now(tz=timezone.utc)
        self._updated_at = updated_at
        self._events: list[
            OrchestrationCreated
            | OrchestrationPlanningStarted
            | OrchestrationResearchStarted
            | OrchestrationExecutionStarted
            | OrchestrationCompleted
            | OrchestrationFailed
            | OrchestrationCancelled
        ] = []

    # -- properties ---------------------------------------------------------

    @property
    def orchestration_id(self) -> OrchestrationId:
        return self._orchestration_id

    @property
    def intent(self) -> UserIntent | None:
        return self._intent

    @property
    def goal(self) -> WorkflowGoal | None:
        return self._goal

    @property
    def status(self) -> OrchestrationStatus:
        return self._status

    @property
    def workflows(self) -> list[Workflow]:
        return list(self._workflows)

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
        OrchestrationCreated
        | OrchestrationPlanningStarted
        | OrchestrationResearchStarted
        | OrchestrationExecutionStarted
        | OrchestrationCompleted
        | OrchestrationFailed
        | OrchestrationCancelled
    ]:
        return list(self._events)

    @property
    def is_terminal(self) -> bool:
        return self._status in (
            OrchestrationStatus.COMPLETED,
            OrchestrationStatus.FAILED,
            OrchestrationStatus.CANCELLED,
        )

    # -- commands -----------------------------------------------------------

    def start_planning(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.orchestrator.domain.rules import (
            assert_orchestration_can_transition,
        )

        assert_orchestration_can_transition(self._status, OrchestrationStatus.PLANNING)
        self._status = OrchestrationStatus.PLANNING
        self._updated_at = now
        self._events.append(
            OrchestrationPlanningStarted(
                orchestration_id=self._orchestration_id, occurred_at=now
            )
        )

    def start_research(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.orchestrator.domain.rules import (
            assert_orchestration_can_transition,
        )

        assert_orchestration_can_transition(self._status, OrchestrationStatus.RESEARCHING)
        self._status = OrchestrationStatus.RESEARCHING
        self._updated_at = now
        self._events.append(
            OrchestrationResearchStarted(
                orchestration_id=self._orchestration_id, occurred_at=now
            )
        )

    def start_execution(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.orchestrator.domain.rules import (
            assert_orchestration_can_transition,
        )

        assert_orchestration_can_transition(self._status, OrchestrationStatus.EXECUTING)
        self._status = OrchestrationStatus.EXECUTING
        self._updated_at = now
        self._events.append(
            OrchestrationExecutionStarted(
                orchestration_id=self._orchestration_id, occurred_at=now
            )
        )

    def complete(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.orchestrator.domain.rules import (
            assert_all_workflows_completed,
            assert_orchestration_can_transition,
        )

        assert_all_workflows_completed(self)
        assert_orchestration_can_transition(self._status, OrchestrationStatus.COMPLETED)
        self._status = OrchestrationStatus.COMPLETED
        self._updated_at = now
        self._events.append(
            OrchestrationCompleted(
                orchestration_id=self._orchestration_id, occurred_at=now
            )
        )

    def fail(self, reason: FailureReason) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.orchestrator.domain.rules import (
            assert_failure_reason_required,
            assert_orchestration_can_transition,
        )

        assert_failure_reason_required(reason)
        assert_orchestration_can_transition(self._status, OrchestrationStatus.FAILED)
        self._status = OrchestrationStatus.FAILED
        self._updated_at = now
        self._events.append(
            OrchestrationFailed(
                orchestration_id=self._orchestration_id,
                failure_reason=reason.value,
                occurred_at=now,
            )
        )

    def cancel(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.orchestrator.domain.rules import (
            assert_orchestration_can_transition,
        )

        assert_orchestration_can_transition(self._status, OrchestrationStatus.CANCELLED)
        self._status = OrchestrationStatus.CANCELLED
        self._updated_at = now
        self._events.append(
            OrchestrationCancelled(
                orchestration_id=self._orchestration_id, occurred_at=now
            )
        )

    def add_workflow(self, workflow: Workflow) -> None:
        from backend.orchestrator.domain.rules import (
            assert_orchestration_not_terminal,
            assert_workflow_id_unique,
        )

        assert_orchestration_not_terminal(self)
        assert_workflow_id_unique(workflow.workflow_id, self._workflows)
        self._workflows.append(workflow)
        self._updated_at = datetime.now(tz=timezone.utc)

    # -- internal -----------------------------------------------------------

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"Orchestration(id={self._orchestration_id}, "
            f"status={self._status.value})"
        )
