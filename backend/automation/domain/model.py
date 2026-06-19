from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import auto, StrEnum
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================


class AutomationStatus(StrEnum):
    DRAFT = auto()
    ACTIVE = auto()
    PAUSED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    DISABLED = auto()


class TriggerType(StrEnum):
    MANUAL = auto()
    SCHEDULED = auto()
    EVENT = auto()
    WEBHOOK = auto()


class ExecutionStatus(StrEnum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class ExecutionMode(StrEnum):
    ONCE = auto()
    RECURRING = auto()
    CONTINUOUS = auto()


class ActionType(StrEnum):
    NOTIFICATION = auto()
    MEMORY = auto()
    KNOWLEDGE = auto()
    RESEARCH = auto()
    ORCHESTRATION = auto()
    CUSTOM = auto()


# =============================================================================
# Value Objects
# =============================================================================


@dataclass(frozen=True)
class AutomationId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class WorkflowExecutionId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class TriggerId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class AutomationName:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"AutomationName value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.automation.domain.exceptions import InvalidAutomationNameError
            raise InvalidAutomationNameError("Automation name must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class AutomationDescription:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"AutomationDescription value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.automation.domain.exceptions import InvalidAutomationDescriptionError
            raise InvalidAutomationDescriptionError("Automation description must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class TriggerExpression:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"TriggerExpression value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.automation.domain.exceptions import InvalidTriggerExpressionError
            raise InvalidTriggerExpressionError("Trigger expression must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class ScheduleExpression:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"ScheduleExpression value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.automation.domain.exceptions import InvalidScheduleExpressionError
            raise InvalidScheduleExpressionError("Schedule expression must not be empty")

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
            from backend.automation.domain.exceptions import InvalidExecutionResultError
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
            from backend.automation.domain.exceptions import InvalidFailureReasonError
            raise InvalidFailureReasonError("Failure reason must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


# =============================================================================
# Domain Events
# =============================================================================


@dataclass(frozen=True)
class AutomationCreated:
    automation_id: AutomationId
    name: str
    description: str
    execution_mode: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AutomationActivated:
    automation_id: AutomationId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AutomationPaused:
    automation_id: AutomationId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AutomationDisabled:
    automation_id: AutomationId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AutomationExecutionStarted:
    automation_id: AutomationId
    execution_id: WorkflowExecutionId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AutomationExecutionCompleted:
    automation_id: AutomationId
    execution_id: WorkflowExecutionId
    result: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class AutomationExecutionFailed:
    automation_id: AutomationId
    execution_id: WorkflowExecutionId
    failure_reason: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class TriggerAdded:
    trigger_id: TriggerId
    automation_id: AutomationId
    trigger_type: str
    expression: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class TriggerEnabled:
    trigger_id: TriggerId
    automation_id: AutomationId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class TriggerDisabled:
    trigger_id: TriggerId
    automation_id: AutomationId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class ActionAdded:
    automation_id: AutomationId
    action_type: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


# =============================================================================
# Entities
# =============================================================================


class Trigger:
    """A trigger that starts automation execution."""

    def __init__(
        self,
        trigger_id: TriggerId | None = None,
        trigger_type: TriggerType = TriggerType.MANUAL,
        expression: TriggerExpression | None = None,
        enabled: bool = True,
        automation_id: AutomationId | None = None,
    ) -> None:
        self._trigger_id = trigger_id or TriggerId()
        self._trigger_type = trigger_type
        self._expression = expression
        self._enabled = enabled
        self._automation_id = automation_id

    @property
    def trigger_id(self) -> TriggerId:
        return self._trigger_id

    @property
    def trigger_type(self) -> TriggerType:
        return self._trigger_type

    @property
    def expression(self) -> TriggerExpression | None:
        return self._expression

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def automation_id(self) -> AutomationId | None:
        return self._automation_id

    def enable(self) -> None:
        from backend.automation.domain.rules import assert_trigger_not_enabled_twice

        assert_trigger_not_enabled_twice(self)
        self._enabled = True

    def disable(self) -> None:
        from backend.automation.domain.rules import assert_trigger_not_disabled_twice

        assert_trigger_not_disabled_twice(self)
        self._enabled = False

    def __repr__(self) -> str:
        return (
            f"Trigger(id={self._trigger_id}, "
            f"type={self._trigger_type.value}, "
            f"enabled={self._enabled})"
        )


class AutomationExecution:
    """A single execution of an automation."""

    def __init__(
        self,
        execution_id: WorkflowExecutionId | None = None,
        automation_id: AutomationId | None = None,
        status: ExecutionStatus = ExecutionStatus.PENDING,
        result: ExecutionResult | None = None,
        failure_reason: FailureReason | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        self._execution_id = execution_id or WorkflowExecutionId()
        self._automation_id = automation_id or AutomationId()
        self._status = status
        self._result = result
        self._failure_reason = failure_reason
        self._started_at = started_at
        self._completed_at = completed_at

    @property
    def execution_id(self) -> WorkflowExecutionId:
        return self._execution_id

    @property
    def automation_id(self) -> AutomationId:
        return self._automation_id

    @property
    def status(self) -> ExecutionStatus:
        return self._status

    @property
    def result(self) -> ExecutionResult | None:
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
    def is_terminal(self) -> bool:
        return self._status in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        )

    def start(self) -> None:
        from backend.automation.domain.rules import (
            assert_execution_can_transition,
        )

        assert_execution_can_transition(self._status, ExecutionStatus.RUNNING)
        self._status = ExecutionStatus.RUNNING
        self._started_at = datetime.now(tz=timezone.utc)

    def complete(self, result: ExecutionResult) -> None:
        from backend.automation.domain.rules import (
            assert_execution_can_transition,
            assert_execution_result_required,
            assert_execution_started_before,
        )

        assert_execution_started_before(self, "complete")
        assert_execution_result_required(result)
        assert_execution_can_transition(self._status, ExecutionStatus.COMPLETED)
        self._result = result
        self._status = ExecutionStatus.COMPLETED
        self._completed_at = datetime.now(tz=timezone.utc)

    def fail(self, reason: FailureReason) -> None:
        from backend.automation.domain.rules import (
            assert_execution_can_transition,
            assert_execution_started_before,
            assert_failure_reason_required,
        )

        assert_execution_started_before(self, "fail")
        assert_failure_reason_required(reason)
        assert_execution_can_transition(self._status, ExecutionStatus.FAILED)
        self._failure_reason = reason
        self._status = ExecutionStatus.FAILED
        self._completed_at = datetime.now(tz=timezone.utc)

    def cancel(self) -> None:
        from backend.automation.domain.rules import (
            assert_execution_can_transition,
        )

        assert_execution_can_transition(self._status, ExecutionStatus.CANCELLED)
        self._status = ExecutionStatus.CANCELLED
        self._completed_at = datetime.now(tz=timezone.utc)

    def __repr__(self) -> str:
        return (
            f"AutomationExecution(id={self._execution_id}, "
            f"status={self._status.value})"
        )


# =============================================================================
# Automation Status Transitions
# =============================================================================

VALID_AUTOMATION_TRANSITIONS: dict[AutomationStatus, set[AutomationStatus]] = {
    AutomationStatus.DRAFT: {AutomationStatus.ACTIVE, AutomationStatus.DISABLED},
    AutomationStatus.ACTIVE: {AutomationStatus.PAUSED, AutomationStatus.RUNNING, AutomationStatus.DISABLED},
    AutomationStatus.PAUSED: {AutomationStatus.ACTIVE, AutomationStatus.DISABLED},
    AutomationStatus.RUNNING: {AutomationStatus.COMPLETED, AutomationStatus.FAILED, AutomationStatus.PAUSED},
    AutomationStatus.COMPLETED: set(),
    AutomationStatus.FAILED: {AutomationStatus.DRAFT},
    AutomationStatus.DISABLED: {AutomationStatus.DRAFT},
}

VALID_EXECUTION_TRANSITIONS: dict[ExecutionStatus, set[ExecutionStatus]] = {
    ExecutionStatus.PENDING: {ExecutionStatus.RUNNING, ExecutionStatus.CANCELLED},
    ExecutionStatus.RUNNING: {ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED},
    ExecutionStatus.COMPLETED: set(),
    ExecutionStatus.FAILED: set(),
    ExecutionStatus.CANCELLED: set(),
}


class Automation:
    """Aggregate root for the automation domain."""

    def __init__(
        self,
        automation_id: AutomationId | None = None,
        name: AutomationName | None = None,
        description: AutomationDescription | None = None,
        status: AutomationStatus = AutomationStatus.DRAFT,
        execution_mode: ExecutionMode = ExecutionMode.ONCE,
        triggers: list[Trigger] | None = None,
        actions: list[ActionType] | None = None,
        executions: list[AutomationExecution] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._automation_id = automation_id or AutomationId()
        self._name = name
        self._description = description
        self._status = status
        self._execution_mode = execution_mode
        self._triggers = triggers or []
        self._actions = actions or []
        self._executions = executions or []
        self._created_at = created_at or datetime.now(tz=timezone.utc)
        self._updated_at = updated_at
        self._events: list[
            AutomationCreated
            | AutomationActivated
            | AutomationPaused
            | AutomationDisabled
            | AutomationExecutionStarted
            | AutomationExecutionCompleted
            | AutomationExecutionFailed
            | TriggerAdded
            | TriggerEnabled
            | TriggerDisabled
            | ActionAdded
        ] = []

    # -- properties ---------------------------------------------------------

    @property
    def automation_id(self) -> AutomationId:
        return self._automation_id

    @property
    def name(self) -> AutomationName | None:
        return self._name

    @property
    def description(self) -> AutomationDescription | None:
        return self._description

    @property
    def status(self) -> AutomationStatus:
        return self._status

    @property
    def execution_mode(self) -> ExecutionMode:
        return self._execution_mode

    @property
    def triggers(self) -> list[Trigger]:
        return list(self._triggers)

    @property
    def actions(self) -> list[ActionType]:
        return list(self._actions)

    @property
    def executions(self) -> list[AutomationExecution]:
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
        AutomationCreated
        | AutomationActivated
        | AutomationPaused
        | AutomationDisabled
        | AutomationExecutionStarted
        | AutomationExecutionCompleted
        | AutomationExecutionFailed
        | TriggerAdded
        | TriggerEnabled
        | TriggerDisabled
        | ActionAdded
    ]:
        return list(self._events)

    @property
    def is_terminal(self) -> bool:
        return self._status in (
            AutomationStatus.COMPLETED,
            AutomationStatus.DISABLED,
        )

    # -- commands -----------------------------------------------------------

    def activate(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.automation.domain.rules import (
            assert_automation_can_transition,
            assert_automation_has_actions,
            assert_automation_has_triggers,
        )

        assert_automation_has_triggers(self)
        assert_automation_has_actions(self)
        assert_automation_can_transition(self._status, AutomationStatus.ACTIVE)
        self._status = AutomationStatus.ACTIVE
        self._updated_at = now
        self._events.append(
            AutomationActivated(
                automation_id=self._automation_id, occurred_at=now
            )
        )

    def pause(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.automation.domain.rules import (
            assert_automation_can_transition,
        )

        assert_automation_can_transition(self._status, AutomationStatus.PAUSED)
        self._status = AutomationStatus.PAUSED
        self._updated_at = now
        self._events.append(
            AutomationPaused(
                automation_id=self._automation_id, occurred_at=now
            )
        )

    def disable(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.automation.domain.rules import (
            assert_automation_can_transition,
        )

        assert_automation_can_transition(self._status, AutomationStatus.DISABLED)
        self._status = AutomationStatus.DISABLED
        self._updated_at = now
        self._events.append(
            AutomationDisabled(
                automation_id=self._automation_id, occurred_at=now
            )
        )

    def start_execution(self) -> AutomationExecution:
        now = datetime.now(tz=timezone.utc)
        from backend.automation.domain.rules import (
            assert_automation_can_transition,
            assert_automation_not_paused,
        )

        assert_automation_not_paused(self)
        assert_automation_can_transition(self._status, AutomationStatus.RUNNING)
        execution = AutomationExecution(automation_id=self._automation_id)
        execution.start()
        self._executions.append(execution)
        self._status = AutomationStatus.RUNNING
        self._updated_at = now
        self._events.append(
            AutomationExecutionStarted(
                automation_id=self._automation_id,
                execution_id=execution.execution_id,
                occurred_at=now,
            )
        )
        return execution

    def complete_execution(self, execution_id: WorkflowExecutionId, result: ExecutionResult) -> None:
        now = datetime.now(tz=timezone.utc)
        execution = self._find_execution(execution_id)
        execution.complete(result)
        self._status = AutomationStatus.COMPLETED
        self._updated_at = now
        self._events.append(
            AutomationExecutionCompleted(
                automation_id=self._automation_id,
                execution_id=execution_id,
                result=result.value,
                occurred_at=now,
            )
        )

    def fail_execution(self, execution_id: WorkflowExecutionId, reason: FailureReason) -> None:
        now = datetime.now(tz=timezone.utc)
        execution = self._find_execution(execution_id)
        execution.fail(reason)
        self._status = AutomationStatus.FAILED
        self._updated_at = now
        self._events.append(
            AutomationExecutionFailed(
                automation_id=self._automation_id,
                execution_id=execution_id,
                failure_reason=reason.value,
                occurred_at=now,
            )
        )

    def add_trigger(self, trigger: Trigger) -> None:
        from backend.automation.domain.rules import (
            assert_automation_not_terminal,
            assert_trigger_id_unique,
        )

        assert_automation_not_terminal(self)
        assert_trigger_id_unique(trigger.trigger_id, self._triggers)
        trigger._automation_id = self._automation_id
        self._triggers.append(trigger)
        self._updated_at = datetime.now(tz=timezone.utc)
        self._events.append(
            TriggerAdded(
                trigger_id=trigger.trigger_id,
                automation_id=self._automation_id,
                trigger_type=trigger.trigger_type.value,
                expression=str(trigger.expression) if trigger.expression else "",
                occurred_at=datetime.now(tz=timezone.utc),
            )
        )

    def add_action(self, action_type: ActionType) -> None:
        from backend.automation.domain.rules import (
            assert_action_definition_unique,
            assert_automation_not_terminal,
        )

        assert_automation_not_terminal(self)
        assert_action_definition_unique(action_type, self._actions)
        self._actions.append(action_type)
        self._updated_at = datetime.now(tz=timezone.utc)
        self._events.append(
            ActionAdded(
                automation_id=self._automation_id,
                action_type=action_type.value,
                occurred_at=datetime.now(tz=timezone.utc),
            )
        )

    def enable_trigger(self, trigger_id: TriggerId) -> None:
        trigger = self._find_trigger(trigger_id)
        trigger.enable()
        now = datetime.now(tz=timezone.utc)
        self._updated_at = now
        self._events.append(
            TriggerEnabled(
                trigger_id=trigger_id,
                automation_id=self._automation_id,
                occurred_at=now,
            )
        )

    def disable_trigger(self, trigger_id: TriggerId) -> None:
        trigger = self._find_trigger(trigger_id)
        trigger.disable()
        now = datetime.now(tz=timezone.utc)
        self._updated_at = now
        self._events.append(
            TriggerDisabled(
                trigger_id=trigger_id,
                automation_id=self._automation_id,
                occurred_at=now,
            )
        )

    # -- internal -----------------------------------------------------------

    def _find_trigger(self, trigger_id: TriggerId) -> Trigger:
        for trigger in self._triggers:
            if trigger.trigger_id == trigger_id:
                return trigger
        from backend.automation.domain.exceptions import TriggerNotFoundError
        raise TriggerNotFoundError(str(trigger_id))

    def _find_execution(self, execution_id: WorkflowExecutionId) -> AutomationExecution:
        for execution in self._executions:
            if execution.execution_id == execution_id:
                return execution
        from backend.automation.domain.exceptions import ExecutionNotFoundError
        raise ExecutionNotFoundError(str(execution_id))

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"Automation(id={self._automation_id}, "
            f"name={self._name}, "
            f"status={self._status.value})"
        )
