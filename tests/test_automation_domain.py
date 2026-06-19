from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.automation.domain.exceptions import (
    AutomationHasNoActionsError,
    AutomationHasNoTriggersError,
    AutomationNotPausedError,
    AutomationTerminalError,
    DuplicateActionTypeError,
    DuplicateTriggerIdError,
    ExecutionNotFoundError,
    ExecutionNotStartedError,
    InvalidActionTypeError,
    InvalidAutomationDescriptionError,
    InvalidAutomationNameError,
    InvalidExecutionResultError,
    InvalidFailureReasonError,
    InvalidScheduleExpressionError,
    InvalidTransitionError,
    InvalidTriggerExpressionError,
    TriggerAlreadyDisabledError,
    TriggerAlreadyEnabledError,
)
from backend.automation.domain.factory import AutomationFactory
from backend.automation.domain.model import (
    ActionAdded,
    ActionType,
    Automation,
    AutomationActivated,
    AutomationCreated,
    AutomationDescription,
    AutomationDisabled,
    AutomationExecution,
    AutomationExecutionCompleted,
    AutomationExecutionFailed,
    AutomationExecutionStarted,
    AutomationId,
    AutomationName,
    AutomationPaused,
    AutomationStatus,
    ExecutionMode,
    ExecutionResult,
    ExecutionStatus,
    FailureReason,
    ScheduleExpression,
    Trigger,
    TriggerAdded,
    TriggerDisabled,
    TriggerEnabled,
    TriggerExpression,
    TriggerId,
    TriggerType,
    WorkflowExecutionId,
    VALID_AUTOMATION_TRANSITIONS,
    VALID_EXECUTION_TRANSITIONS,
)
from backend.automation.domain.rules import (
    assert_action_definition_unique,
    assert_action_type_valid,
    assert_automation_can_transition,
    assert_automation_has_actions,
    assert_automation_has_triggers,
    assert_automation_not_paused,
    assert_automation_not_terminal,
    assert_description_required,
    assert_execution_can_transition,
    assert_execution_result_required,
    assert_execution_started_before,
    assert_failure_reason_required,
    assert_name_required,
    assert_schedule_expression_required,
    assert_trigger_expression_required,
    assert_trigger_id_unique,
    assert_trigger_not_disabled_twice,
    assert_trigger_not_enabled_twice,
    assert_trigger_type_valid,
)


# ===========================================================================
# Helpers
# ===========================================================================


def make_valid_automation(
    name: str = "Daily Report",
    description: str = "Generates daily report",
    execution_mode: ExecutionMode = ExecutionMode.ONCE,
) -> Automation:
    a, _ = AutomationFactory.create_automation(
        name=name,
        description=description,
        execution_mode=execution_mode,
    )
    return a


def make_ready_automation() -> Automation:
    a = make_valid_automation()
    trigger = Trigger(trigger_type=TriggerType.SCHEDULED, expression=TriggerExpression(value="0 8 * * *"))
    a.add_trigger(trigger)
    a.add_action(ActionType.NOTIFICATION)
    return a


# =============================================================================
# 1. Value Object Tests
# =============================================================================


class TestAutomationId:
    def test_creation(self) -> None:
        aid = AutomationId()
        assert isinstance(aid.value, UUID)

    def test_str_representation(self) -> None:
        aid = AutomationId()
        assert str(aid) == str(aid.value)

    def test_equality(self) -> None:
        v = UUID("00000000-0000-0000-0000-000000000001")
        assert AutomationId(value=v) == AutomationId(value=v)

    def test_inequality(self) -> None:
        assert AutomationId() != AutomationId()

    def test_immutability(self) -> None:
        aid = AutomationId()
        with pytest.raises(AttributeError):
            aid.value = UUID(int=0)

    def test_default_factory(self) -> None:
        aid = AutomationId()
        assert aid.value is not None


class TestWorkflowExecutionId:
    def test_creation(self) -> None:
        eid = WorkflowExecutionId()
        assert isinstance(eid.value, UUID)

    def test_str_representation(self) -> None:
        eid = WorkflowExecutionId()
        assert str(eid) == str(eid.value)

    def test_equality(self) -> None:
        v = UUID("00000000-0000-0000-0000-000000000002")
        assert WorkflowExecutionId(value=v) == WorkflowExecutionId(value=v)

    def test_inequality(self) -> None:
        assert WorkflowExecutionId() != WorkflowExecutionId()

    def test_immutability(self) -> None:
        eid = WorkflowExecutionId()
        with pytest.raises(AttributeError):
            eid.value = UUID(int=0)


class TestTriggerId:
    def test_creation(self) -> None:
        tid = TriggerId()
        assert isinstance(tid.value, UUID)

    def test_str_representation(self) -> None:
        tid = TriggerId()
        assert str(tid) == str(tid.value)

    def test_equality(self) -> None:
        v = UUID("00000000-0000-0000-0000-000000000003")
        assert TriggerId(value=v) == TriggerId(value=v)

    def test_inequality(self) -> None:
        assert TriggerId() != TriggerId()

    def test_immutability(self) -> None:
        tid = TriggerId()
        with pytest.raises(AttributeError):
            tid.value = UUID(int=0)


class TestAutomationName:
    def test_creation(self) -> None:
        n = AutomationName(value="Daily Report")
        assert n.value == "Daily Report"

    def test_str_conversion(self) -> None:
        n = AutomationName(value="Report")
        assert str(n) == "Report"

    def test_length(self) -> None:
        n = AutomationName(value="abcd")
        assert len(n) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidAutomationNameError, match="not be empty"):
            AutomationName(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidAutomationNameError, match="not be empty"):
            AutomationName(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            AutomationName(value=123)

    def test_equality(self) -> None:
        assert AutomationName(value="a") == AutomationName(value="a")

    def test_frozen(self) -> None:
        n = AutomationName(value="a")
        with pytest.raises(AttributeError):
            n.value = "b"


class TestAutomationDescription:
    def test_creation(self) -> None:
        d = AutomationDescription(value="Generates report")
        assert d.value == "Generates report"

    def test_str_conversion(self) -> None:
        d = AutomationDescription(value="Desc")
        assert str(d) == "Desc"

    def test_length(self) -> None:
        d = AutomationDescription(value="abcd")
        assert len(d) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidAutomationDescriptionError, match="not be empty"):
            AutomationDescription(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidAutomationDescriptionError, match="not be empty"):
            AutomationDescription(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            AutomationDescription(value=123)

    def test_equality(self) -> None:
        assert AutomationDescription(value="a") == AutomationDescription(value="a")

    def test_frozen(self) -> None:
        d = AutomationDescription(value="a")
        with pytest.raises(AttributeError):
            d.value = "b"


class TestTriggerExpression:
    def test_creation(self) -> None:
        e = TriggerExpression(value="0 8 * * *")
        assert e.value == "0 8 * * *"

    def test_str_conversion(self) -> None:
        e = TriggerExpression(value="cron")
        assert str(e) == "cron"

    def test_length(self) -> None:
        e = TriggerExpression(value="abcd")
        assert len(e) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidTriggerExpressionError, match="not be empty"):
            TriggerExpression(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidTriggerExpressionError, match="not be empty"):
            TriggerExpression(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            TriggerExpression(value=123)

    def test_equality(self) -> None:
        assert TriggerExpression(value="a") == TriggerExpression(value="a")

    def test_frozen(self) -> None:
        e = TriggerExpression(value="a")
        with pytest.raises(AttributeError):
            e.value = "b"


class TestScheduleExpression:
    def test_creation(self) -> None:
        e = ScheduleExpression(value="0 8 * * *")
        assert e.value == "0 8 * * *"

    def test_str_conversion(self) -> None:
        e = ScheduleExpression(value="cron")
        assert str(e) == "cron"

    def test_length(self) -> None:
        e = ScheduleExpression(value="abcd")
        assert len(e) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidScheduleExpressionError, match="not be empty"):
            ScheduleExpression(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidScheduleExpressionError, match="not be empty"):
            ScheduleExpression(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            ScheduleExpression(value=123)

    def test_equality(self) -> None:
        assert ScheduleExpression(value="a") == ScheduleExpression(value="a")

    def test_frozen(self) -> None:
        e = ScheduleExpression(value="a")
        with pytest.raises(AttributeError):
            e.value = "b"


class TestExecutionResult:
    def test_creation(self) -> None:
        r = ExecutionResult(value="Success")
        assert r.value == "Success"

    def test_str_conversion(self) -> None:
        r = ExecutionResult(value="OK")
        assert str(r) == "OK"

    def test_length(self) -> None:
        r = ExecutionResult(value="abcd")
        assert len(r) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidExecutionResultError, match="not be empty"):
            ExecutionResult(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidExecutionResultError, match="not be empty"):
            ExecutionResult(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            ExecutionResult(value=123)

    def test_equality(self) -> None:
        assert ExecutionResult(value="a") == ExecutionResult(value="a")

    def test_frozen(self) -> None:
        r = ExecutionResult(value="a")
        with pytest.raises(AttributeError):
            r.value = "b"


class TestFailureReason:
    def test_creation(self) -> None:
        r = FailureReason(value="Timeout")
        assert r.value == "Timeout"

    def test_str_conversion(self) -> None:
        r = FailureReason(value="Error")
        assert str(r) == "Error"

    def test_length(self) -> None:
        r = FailureReason(value="abcd")
        assert len(r) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidFailureReasonError, match="not be empty"):
            FailureReason(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidFailureReasonError, match="not be empty"):
            FailureReason(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            FailureReason(value=123)

    def test_equality(self) -> None:
        assert FailureReason(value="a") == FailureReason(value="a")

    def test_frozen(self) -> None:
        r = FailureReason(value="a")
        with pytest.raises(AttributeError):
            r.value = "b"


# =============================================================================
# 2. Enum Tests
# =============================================================================


class TestAutomationStatus:
    def test_members(self) -> None:
        assert AutomationStatus.DRAFT.value == "draft"
        assert AutomationStatus.ACTIVE.value == "active"
        assert AutomationStatus.PAUSED.value == "paused"
        assert AutomationStatus.RUNNING.value == "running"
        assert AutomationStatus.COMPLETED.value == "completed"
        assert AutomationStatus.FAILED.value == "failed"
        assert AutomationStatus.DISABLED.value == "disabled"

    def test_order(self) -> None:
        members = list(AutomationStatus)
        assert members == [
            AutomationStatus.DRAFT,
            AutomationStatus.ACTIVE,
            AutomationStatus.PAUSED,
            AutomationStatus.RUNNING,
            AutomationStatus.COMPLETED,
            AutomationStatus.FAILED,
            AutomationStatus.DISABLED,
        ]

    def test_from_string(self) -> None:
        assert AutomationStatus("draft") == AutomationStatus.DRAFT
        assert AutomationStatus("active") == AutomationStatus.ACTIVE

    def test_unique_values(self) -> None:
        values = [s.value for s in AutomationStatus]
        assert len(values) == len(set(values))


class TestTriggerType:
    def test_members(self) -> None:
        assert TriggerType.MANUAL.value == "manual"
        assert TriggerType.SCHEDULED.value == "scheduled"
        assert TriggerType.EVENT.value == "event"
        assert TriggerType.WEBHOOK.value == "webhook"

    def test_from_string(self) -> None:
        assert TriggerType("scheduled") == TriggerType.SCHEDULED

    def test_unique_values(self) -> None:
        values = [t.value for t in TriggerType]
        assert len(values) == len(set(values))


class TestExecutionStatus:
    def test_members(self) -> None:
        assert ExecutionStatus.PENDING.value == "pending"
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.COMPLETED.value == "completed"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.CANCELLED.value == "cancelled"

    def test_from_string(self) -> None:
        assert ExecutionStatus("running") == ExecutionStatus.RUNNING

    def test_unique_values(self) -> None:
        values = [s.value for s in ExecutionStatus]
        assert len(values) == len(set(values))


class TestExecutionMode:
    def test_members(self) -> None:
        assert ExecutionMode.ONCE.value == "once"
        assert ExecutionMode.RECURRING.value == "recurring"
        assert ExecutionMode.CONTINUOUS.value == "continuous"

    def test_from_string(self) -> None:
        assert ExecutionMode("recurring") == ExecutionMode.RECURRING

    def test_unique_values(self) -> None:
        values = [m.value for m in ExecutionMode]
        assert len(values) == len(set(values))


class TestActionType:
    def test_members(self) -> None:
        assert ActionType.NOTIFICATION.value == "notification"
        assert ActionType.MEMORY.value == "memory"
        assert ActionType.KNOWLEDGE.value == "knowledge"
        assert ActionType.RESEARCH.value == "research"
        assert ActionType.ORCHESTRATION.value == "orchestration"
        assert ActionType.CUSTOM.value == "custom"

    def test_from_string(self) -> None:
        assert ActionType("research") == ActionType.RESEARCH

    def test_unique_values(self) -> None:
        values = [a.value for a in ActionType]
        assert len(values) == len(set(values))


# =============================================================================
# 3. Domain Event Tests
# =============================================================================


class TestAutomationCreatedEvent:
    def test_creation(self) -> None:
        aid = AutomationId()
        now = datetime.now(tz=timezone.utc)
        ev = AutomationCreated(
            automation_id=aid,
            name="Report",
            description="Daily report",
            execution_mode="once",
            occurred_at=now,
        )
        assert ev.automation_id == aid
        assert ev.name == "Report"
        assert ev.description == "Daily report"
        assert ev.execution_mode == "once"
        assert ev.occurred_at == now
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = AutomationCreated(
            automation_id=AutomationId(),
            name="R", description="D",
            execution_mode="once",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.name = "changed"

    def test_unique_event_ids(self) -> None:
        aid = AutomationId()
        now = datetime.now(tz=timezone.utc)
        ev1 = AutomationCreated(
            automation_id=aid, name="A", description="B",
            execution_mode="once", occurred_at=now,
        )
        ev2 = AutomationCreated(
            automation_id=aid, name="A", description="B",
            execution_mode="once", occurred_at=now,
        )
        assert ev1.event_id != ev2.event_id


class TestAutomationActivatedEvent:
    def test_creation(self) -> None:
        aid = AutomationId()
        now = datetime.now(tz=timezone.utc)
        ev = AutomationActivated(automation_id=aid, occurred_at=now)
        assert ev.automation_id == aid
        assert ev.occurred_at == now
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = AutomationActivated(
            automation_id=AutomationId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.automation_id = AutomationId()


class TestAutomationPausedEvent:
    def test_creation(self) -> None:
        aid = AutomationId()
        now = datetime.now(tz=timezone.utc)
        ev = AutomationPaused(automation_id=aid, occurred_at=now)
        assert ev.automation_id == aid
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = AutomationPaused(
            automation_id=AutomationId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.occurred_at = datetime.now(tz=timezone.utc)


class TestAutomationDisabledEvent:
    def test_creation(self) -> None:
        aid = AutomationId()
        now = datetime.now(tz=timezone.utc)
        ev = AutomationDisabled(automation_id=aid, occurred_at=now)
        assert ev.automation_id == aid
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = AutomationDisabled(
            automation_id=AutomationId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.automation_id = AutomationId()


class TestAutomationExecutionStartedEvent:
    def test_creation(self) -> None:
        aid = AutomationId()
        eid = WorkflowExecutionId()
        now = datetime.now(tz=timezone.utc)
        ev = AutomationExecutionStarted(
            automation_id=aid, execution_id=eid, occurred_at=now,
        )
        assert ev.automation_id == aid
        assert ev.execution_id == eid
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = AutomationExecutionStarted(
            automation_id=AutomationId(),
            execution_id=WorkflowExecutionId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.execution_id = WorkflowExecutionId()


class TestAutomationExecutionCompletedEvent:
    def test_creation(self) -> None:
        aid = AutomationId()
        eid = WorkflowExecutionId()
        now = datetime.now(tz=timezone.utc)
        ev = AutomationExecutionCompleted(
            automation_id=aid, execution_id=eid,
            result="Success", occurred_at=now,
        )
        assert ev.automation_id == aid
        assert ev.execution_id == eid
        assert ev.result == "Success"
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = AutomationExecutionCompleted(
            automation_id=AutomationId(),
            execution_id=WorkflowExecutionId(),
            result="OK", occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.result = "changed"


class TestAutomationExecutionFailedEvent:
    def test_creation(self) -> None:
        aid = AutomationId()
        eid = WorkflowExecutionId()
        now = datetime.now(tz=timezone.utc)
        ev = AutomationExecutionFailed(
            automation_id=aid, execution_id=eid,
            failure_reason="Timeout", occurred_at=now,
        )
        assert ev.automation_id == aid
        assert ev.execution_id == eid
        assert ev.failure_reason == "Timeout"
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = AutomationExecutionFailed(
            automation_id=AutomationId(),
            execution_id=WorkflowExecutionId(),
            failure_reason="Err", occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.failure_reason = "changed"


class TestTriggerAddedEvent:
    def test_creation(self) -> None:
        tid = TriggerId()
        aid = AutomationId()
        now = datetime.now(tz=timezone.utc)
        ev = TriggerAdded(
            trigger_id=tid, automation_id=aid,
            trigger_type="scheduled", expression="0 8 * * *",
            occurred_at=now,
        )
        assert ev.trigger_id == tid
        assert ev.automation_id == aid
        assert ev.trigger_type == "scheduled"
        assert ev.expression == "0 8 * * *"
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = TriggerAdded(
            trigger_id=TriggerId(), automation_id=AutomationId(),
            trigger_type="manual", expression="",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.trigger_type = "changed"


class TestTriggerEnabledEvent:
    def test_creation(self) -> None:
        tid = TriggerId()
        aid = AutomationId()
        now = datetime.now(tz=timezone.utc)
        ev = TriggerEnabled(trigger_id=tid, automation_id=aid, occurred_at=now)
        assert ev.trigger_id == tid
        assert ev.automation_id == aid
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = TriggerEnabled(
            trigger_id=TriggerId(), automation_id=AutomationId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.trigger_id = TriggerId()


class TestTriggerDisabledEvent:
    def test_creation(self) -> None:
        tid = TriggerId()
        aid = AutomationId()
        now = datetime.now(tz=timezone.utc)
        ev = TriggerDisabled(trigger_id=tid, automation_id=aid, occurred_at=now)
        assert ev.trigger_id == tid
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = TriggerDisabled(
            trigger_id=TriggerId(), automation_id=AutomationId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.trigger_id = TriggerId()


class TestActionAddedEvent:
    def test_creation(self) -> None:
        aid = AutomationId()
        now = datetime.now(tz=timezone.utc)
        ev = ActionAdded(
            automation_id=aid, action_type="notification", occurred_at=now,
        )
        assert ev.automation_id == aid
        assert ev.action_type == "notification"
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        ev = ActionAdded(
            automation_id=AutomationId(), action_type="research",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.action_type = "changed"


# =============================================================================
# 4. Trigger Entity Tests
# =============================================================================


class TestTriggerCreation:
    def test_default_id_generated(self) -> None:
        t = Trigger()
        assert isinstance(t.trigger_id, TriggerId)

    def test_default_trigger_type(self) -> None:
        t = Trigger()
        assert t.trigger_type == TriggerType.MANUAL

    def test_default_enabled(self) -> None:
        t = Trigger()
        assert t.enabled is True

    def test_default_expression_none(self) -> None:
        t = Trigger()
        assert t.expression is None

    def test_custom_trigger_type(self) -> None:
        t = Trigger(trigger_type=TriggerType.SCHEDULED)
        assert t.trigger_type == TriggerType.SCHEDULED

    def test_with_expression(self) -> None:
        expr = TriggerExpression(value="0 8 * * *")
        t = Trigger(trigger_type=TriggerType.SCHEDULED, expression=expr)
        assert t.expression == expr

    def test_disabled_initially(self) -> None:
        t = Trigger(enabled=False)
        assert t.enabled is False

    def test_repr(self) -> None:
        t = Trigger()
        r = repr(t)
        assert "Trigger" in r
        assert str(t.trigger_id) in r
        assert t.trigger_type.value in r


class TestTriggerEnable:
    def test_enable_sets_enabled(self) -> None:
        t = Trigger(enabled=False)
        t.enable()
        assert t.enabled is True

    def test_enable_already_enabled_raises(self) -> None:
        t = Trigger(enabled=True)
        with pytest.raises(TriggerAlreadyEnabledError):
            t.enable()


class TestTriggerDisable:
    def test_disable_sets_disabled(self) -> None:
        t = Trigger(enabled=True)
        t.disable()
        assert t.enabled is False

    def test_disable_already_disabled_raises(self) -> None:
        t = Trigger(enabled=False)
        with pytest.raises(TriggerAlreadyDisabledError):
            t.disable()


class TestTriggerEnableDisableCycle:
    def test_enable_then_disable(self) -> None:
        t = Trigger(enabled=False)
        t.enable()
        assert t.enabled is True
        t.disable()
        assert t.enabled is False

    def test_disable_then_enable(self) -> None:
        t = Trigger(enabled=True)
        t.disable()
        assert t.enabled is False
        t.enable()
        assert t.enabled is True


# =============================================================================
# 5. AutomationExecution Entity Tests
# =============================================================================


class TestAutomationExecutionCreation:
    def test_default_id_generated(self) -> None:
        e = AutomationExecution()
        assert isinstance(e.execution_id, WorkflowExecutionId)

    def test_default_status_pending(self) -> None:
        e = AutomationExecution()
        assert e.status == ExecutionStatus.PENDING

    def test_default_result_none(self) -> None:
        e = AutomationExecution()
        assert e.result is None

    def test_default_failure_reason_none(self) -> None:
        e = AutomationExecution()
        assert e.failure_reason is None

    def test_default_started_at_none(self) -> None:
        e = AutomationExecution()
        assert e.started_at is None

    def test_default_completed_at_none(self) -> None:
        e = AutomationExecution()
        assert e.completed_at is None

    def test_not_terminal_initially(self) -> None:
        e = AutomationExecution()
        assert e.is_terminal is False

    def test_repr(self) -> None:
        e = AutomationExecution()
        r = repr(e)
        assert "AutomationExecution" in r
        assert str(e.execution_id) in r
        assert e.status.value in r

    def test_custom_automation_id(self) -> None:
        aid = AutomationId()
        e = AutomationExecution(automation_id=aid)
        assert e.automation_id == aid


class TestAutomationExecutionStart:
    def test_start_sets_running(self) -> None:
        e = AutomationExecution()
        e.start()
        assert e.status == ExecutionStatus.RUNNING

    def test_start_sets_started_at(self) -> None:
        e = AutomationExecution()
        e.start()
        assert e.started_at is not None
        assert e.started_at.tzinfo is not None

    def test_start_from_running_raises(self) -> None:
        e = AutomationExecution()
        e.start()
        with pytest.raises(InvalidTransitionError):
            e.start()

    def test_start_from_completed_raises(self) -> None:
        e = AutomationExecution()
        e.start()
        e.complete(ExecutionResult(value="Done"))
        with pytest.raises(InvalidTransitionError):
            e.start()


class TestAutomationExecutionComplete:
    def test_complete_sets_completed(self) -> None:
        e = AutomationExecution()
        e.start()
        e.complete(ExecutionResult(value="Success"))
        assert e.status == ExecutionStatus.COMPLETED

    def test_complete_sets_result(self) -> None:
        e = AutomationExecution()
        e.start()
        result = ExecutionResult(value="Success")
        e.complete(result)
        assert e.result == result

    def test_complete_sets_completed_at(self) -> None:
        e = AutomationExecution()
        e.start()
        e.complete(ExecutionResult(value="Done"))
        assert e.completed_at is not None
        assert e.completed_at.tzinfo is not None

    def test_complete_is_terminal(self) -> None:
        e = AutomationExecution()
        e.start()
        e.complete(ExecutionResult(value="Done"))
        assert e.is_terminal is True

    def test_complete_without_start_raises(self) -> None:
        e = AutomationExecution()
        with pytest.raises(ExecutionNotStartedError):
            e.complete(ExecutionResult(value="Done"))

    def test_complete_without_result_raises(self) -> None:
        e = AutomationExecution()
        e.start()
        with pytest.raises(InvalidExecutionResultError):
            e.complete(None)

    def test_double_complete_raises(self) -> None:
        e = AutomationExecution()
        e.start()
        e.complete(ExecutionResult(value="Done"))
        with pytest.raises(ExecutionNotStartedError):
            e.complete(ExecutionResult(value="Done"))


class TestAutomationExecutionFail:
    def test_fail_sets_failed(self) -> None:
        e = AutomationExecution()
        e.start()
        e.fail(FailureReason(value="Error"))
        assert e.status == ExecutionStatus.FAILED

    def test_fail_sets_failure_reason(self) -> None:
        e = AutomationExecution()
        e.start()
        reason = FailureReason(value="Timeout")
        e.fail(reason)
        assert e.failure_reason == reason

    def test_fail_sets_completed_at(self) -> None:
        e = AutomationExecution()
        e.start()
        e.fail(FailureReason(value="Err"))
        assert e.completed_at is not None

    def test_fail_is_terminal(self) -> None:
        e = AutomationExecution()
        e.start()
        e.fail(FailureReason(value="Err"))
        assert e.is_terminal is True

    def test_fail_without_start_raises(self) -> None:
        e = AutomationExecution()
        with pytest.raises(ExecutionNotStartedError):
            e.fail(FailureReason(value="Err"))

    def test_fail_without_reason_raises(self) -> None:
        e = AutomationExecution()
        e.start()
        with pytest.raises(InvalidFailureReasonError):
            e.fail(None)

    def test_double_fail_raises(self) -> None:
        e = AutomationExecution()
        e.start()
        e.fail(FailureReason(value="Err"))
        with pytest.raises(ExecutionNotStartedError):
            e.fail(FailureReason(value="Err"))


class TestAutomationExecutionCancel:
    def test_cancel_sets_cancelled(self) -> None:
        e = AutomationExecution()
        e.cancel()
        assert e.status == ExecutionStatus.CANCELLED

    def test_cancel_sets_completed_at(self) -> None:
        e = AutomationExecution()
        e.cancel()
        assert e.completed_at is not None

    def test_cancel_from_pending(self) -> None:
        e = AutomationExecution()
        e.cancel()
        assert e.is_terminal is True

    def test_cancel_from_running(self) -> None:
        e = AutomationExecution()
        e.start()
        e.cancel()
        assert e.status == ExecutionStatus.CANCELLED

    def test_double_cancel_raises(self) -> None:
        e = AutomationExecution()
        e.cancel()
        with pytest.raises(InvalidTransitionError):
            e.cancel()

    def test_cancel_completed_raises(self) -> None:
        e = AutomationExecution()
        e.start()
        e.complete(ExecutionResult(value="Done"))
        with pytest.raises(InvalidTransitionError):
            e.cancel()


class TestAutomationExecutionTerminal:
    def test_completed_is_terminal(self) -> None:
        e = AutomationExecution()
        e.start()
        e.complete(ExecutionResult(value="Done"))
        assert e.is_terminal is True

    def test_failed_is_terminal(self) -> None:
        e = AutomationExecution()
        e.start()
        e.fail(FailureReason(value="Err"))
        assert e.is_terminal is True

    def test_cancelled_is_terminal(self) -> None:
        e = AutomationExecution()
        e.cancel()
        assert e.is_terminal is True

    def test_pending_not_terminal(self) -> None:
        e = AutomationExecution()
        assert e.is_terminal is False


# =============================================================================
# 6. Automation Aggregate Tests
# =============================================================================


class TestAutomationCreation:
    def test_default_id_generated(self) -> None:
        a = make_valid_automation()
        assert isinstance(a.automation_id, AutomationId)

    def test_default_status_draft(self) -> None:
        a = make_valid_automation()
        assert a.status == AutomationStatus.DRAFT

    def test_default_execution_mode_once(self) -> None:
        a = make_valid_automation()
        assert a.execution_mode == ExecutionMode.ONCE

    def test_default_triggers_empty(self) -> None:
        a = make_valid_automation()
        assert a.triggers == []

    def test_default_actions_empty(self) -> None:
        a = make_valid_automation()
        assert a.actions == []

    def test_default_executions_empty(self) -> None:
        a = make_valid_automation()
        assert a.executions == []

    def test_initial_events_empty(self) -> None:
        a = make_valid_automation()
        assert a.events == []

    def test_not_terminal_initially(self) -> None:
        a = make_valid_automation()
        assert a.is_terminal is False

    def test_created_at_set(self) -> None:
        a = make_valid_automation()
        assert a.created_at is not None
        assert a.created_at.tzinfo is not None

    def test_updated_at_none_initially(self) -> None:
        a = make_valid_automation()
        assert a.updated_at is None

    def test_repr(self) -> None:
        a = make_valid_automation()
        r = repr(a)
        assert "Automation" in r
        assert str(a.automation_id) in r

    def test_custom_automation_id(self) -> None:
        aid = AutomationId()
        a = Automation(automation_id=aid)
        assert a.automation_id == aid

    def test_custom_execution_mode(self) -> None:
        a = Automation(execution_mode=ExecutionMode.RECURRING)
        assert a.execution_mode == ExecutionMode.RECURRING


class TestAutomationActivate:
    def test_activate_sets_active(self) -> None:
        a = make_ready_automation()
        a.activate()
        assert a.status == AutomationStatus.ACTIVE

    def test_activate_emits_event(self) -> None:
        a = make_ready_automation()
        a._clear_events()
        a.activate()
        assert len(a.events) == 1
        assert isinstance(a.events[0], AutomationActivated)

    def test_activate_sets_updated_at(self) -> None:
        a = make_ready_automation()
        a.activate()
        assert a.updated_at is not None

    def test_activate_without_triggers_raises(self) -> None:
        a = make_valid_automation()
        a.add_action(ActionType.NOTIFICATION)
        with pytest.raises(AutomationHasNoTriggersError):
            a.activate()

    def test_activate_without_actions_raises(self) -> None:
        a = make_valid_automation()
        trigger = Trigger(trigger_type=TriggerType.SCHEDULED, expression=TriggerExpression(value="0 8 * * *"))
        a.add_trigger(trigger)
        with pytest.raises(AutomationHasNoActionsError):
            a.activate()

    def test_double_activate_raises(self) -> None:
        a = make_ready_automation()
        a.activate()
        with pytest.raises(InvalidTransitionError):
            a.activate()

    def test_activate_from_paused(self) -> None:
        a = make_ready_automation()
        a.activate()
        a.pause()
        a.activate()
        assert a.status == AutomationStatus.ACTIVE


class TestAutomationPause:
    def test_pause_sets_paused(self) -> None:
        a = make_ready_automation()
        a.activate()
        a.pause()
        assert a.status == AutomationStatus.PAUSED

    def test_pause_emits_event(self) -> None:
        a = make_ready_automation()
        a.activate()
        a.pause()
        assert isinstance(a.events[-1], AutomationPaused)

    def test_pause_from_draft_raises(self) -> None:
        a = make_valid_automation()
        with pytest.raises(InvalidTransitionError):
            a.pause()

    def test_double_pause_raises(self) -> None:
        a = make_ready_automation()
        a.activate()
        a.pause()
        with pytest.raises(InvalidTransitionError):
            a.pause()

    def test_pause_from_running(self) -> None:
        a = make_ready_automation()
        a.activate()
        a.start_execution()
        a.pause()
        assert a.status == AutomationStatus.PAUSED


class TestAutomationDisable:
    def test_disable_sets_disabled(self) -> None:
        a = make_valid_automation()
        a.disable()
        assert a.status == AutomationStatus.DISABLED

    def test_disable_emits_event(self) -> None:
        a = make_valid_automation()
        a.disable()
        assert isinstance(a.events[-1], AutomationDisabled)

    def test_disable_from_active(self) -> None:
        a = make_ready_automation()
        a.activate()
        a.disable()
        assert a.status == AutomationStatus.DISABLED

    def test_disable_from_paused(self) -> None:
        a = make_ready_automation()
        a.activate()
        a.pause()
        a.disable()
        assert a.status == AutomationStatus.DISABLED

    def test_disabled_is_terminal(self) -> None:
        a = make_valid_automation()
        a.disable()
        assert a.is_terminal is True


class TestAutomationStartExecution:
    def test_start_execution_returns_execution(self) -> None:
        a = make_ready_automation()
        a.activate()
        e = a.start_execution()
        assert isinstance(e, AutomationExecution)
        assert e.status == ExecutionStatus.RUNNING

    def test_start_execution_sets_automation_running(self) -> None:
        a = make_ready_automation()
        a.activate()
        a.start_execution()
        assert a.status == AutomationStatus.RUNNING

    def test_start_execution_emits_event(self) -> None:
        a = make_ready_automation()
        a.activate()
        a.start_execution()
        assert isinstance(a.events[-1], AutomationExecutionStarted)

    def test_start_execution_adds_to_executions(self) -> None:
        a = make_ready_automation()
        a.activate()
        a.start_execution()
        assert len(a.executions) == 1

    def test_start_execution_from_paused_raises(self) -> None:
        a = make_ready_automation()
        a.activate()
        a.pause()
        with pytest.raises(AutomationNotPausedError):
            a.start_execution()

    def test_start_execution_from_draft_raises(self) -> None:
        a = make_valid_automation()
        with pytest.raises(InvalidTransitionError):
            a.start_execution()

    def test_start_execution_from_completed_raises(self) -> None:
        a = make_ready_automation()
        a.activate()
        e = a.start_execution()
        a.complete_execution(e.execution_id, ExecutionResult(value="Done"))
        with pytest.raises(InvalidTransitionError):
            a.start_execution()


class TestAutomationCompleteExecution:
    def test_complete_execution_sets_completed(self) -> None:
        a = make_ready_automation()
        a.activate()
        e = a.start_execution()
        a.complete_execution(e.execution_id, ExecutionResult(value="Success"))
        assert e.status == ExecutionStatus.COMPLETED

    def test_complete_execution_sets_automation_completed(self) -> None:
        a = make_ready_automation()
        a.activate()
        e = a.start_execution()
        a.complete_execution(e.execution_id, ExecutionResult(value="Success"))
        assert a.status == AutomationStatus.COMPLETED

    def test_complete_execution_automation_terminal(self) -> None:
        a = make_ready_automation()
        a.activate()
        e = a.start_execution()
        a.complete_execution(e.execution_id, ExecutionResult(value="Done"))
        assert a.is_terminal is True

    def test_complete_execution_emits_event(self) -> None:
        a = make_ready_automation()
        a.activate()
        e = a.start_execution()
        a.complete_execution(e.execution_id, ExecutionResult(value="OK"))
        assert isinstance(a.events[-1], AutomationExecutionCompleted)

    def test_complete_nonexistent_execution_raises(self) -> None:
        a = make_ready_automation()
        a.activate()
        with pytest.raises(ExecutionNotFoundError):
            a.complete_execution(WorkflowExecutionId(), ExecutionResult(value="OK"))


class TestAutomationFailExecution:
    def test_fail_execution_sets_failed(self) -> None:
        a = make_ready_automation()
        a.activate()
        e = a.start_execution()
        a.fail_execution(e.execution_id, FailureReason(value="Error"))
        assert e.status == ExecutionStatus.FAILED

    def test_fail_execution_sets_automation_failed(self) -> None:
        a = make_ready_automation()
        a.activate()
        e = a.start_execution()
        a.fail_execution(e.execution_id, FailureReason(value="Error"))
        assert a.status == AutomationStatus.FAILED

    def test_fail_execution_emits_event(self) -> None:
        a = make_ready_automation()
        a.activate()
        e = a.start_execution()
        a.fail_execution(e.execution_id, FailureReason(value="Err"))
        assert isinstance(a.events[-1], AutomationExecutionFailed)

    def test_fail_nonexistent_execution_raises(self) -> None:
        a = make_ready_automation()
        a.activate()
        with pytest.raises(ExecutionNotFoundError):
            a.fail_execution(WorkflowExecutionId(), FailureReason(value="Err"))


class TestAutomationAddTrigger:
    def test_add_trigger_appends(self) -> None:
        a = make_valid_automation()
        t = Trigger(trigger_type=TriggerType.SCHEDULED, expression=TriggerExpression(value="0 8 * * *"))
        a.add_trigger(t)
        assert len(a.triggers) == 1
        assert a.triggers[0] == t

    def test_add_trigger_emits_event(self) -> None:
        a = make_valid_automation()
        t = Trigger(trigger_type=TriggerType.SCHEDULED, expression=TriggerExpression(value="0 8 * * *"))
        a.add_trigger(t)
        assert isinstance(a.events[-1], TriggerAdded)

    def test_add_duplicate_trigger_raises(self) -> None:
        a = make_valid_automation()
        t = Trigger(trigger_type=TriggerType.SCHEDULED, expression=TriggerExpression(value="0 8 * * *"))
        a.add_trigger(t)
        with pytest.raises(DuplicateTriggerIdError):
            a.add_trigger(t)

    def test_add_trigger_to_completed_raises(self) -> None:
        a = make_ready_automation()
        a.activate()
        e = a.start_execution()
        a.complete_execution(e.execution_id, ExecutionResult(value="Done"))
        with pytest.raises(AutomationTerminalError):
            a.add_trigger(Trigger(trigger_type=TriggerType.MANUAL))

    def test_add_trigger_to_disabled_raises(self) -> None:
        a = make_valid_automation()
        a.disable()
        with pytest.raises(AutomationTerminalError):
            a.add_trigger(Trigger(trigger_type=TriggerType.MANUAL))

    def test_multiple_triggers(self) -> None:
        a = make_valid_automation()
        a.add_trigger(Trigger(trigger_type=TriggerType.MANUAL))
        a.add_trigger(Trigger(trigger_type=TriggerType.SCHEDULED, expression=TriggerExpression(value="0 9 * * *")))
        assert len(a.triggers) == 2


class TestAutomationAddAction:
    def test_add_action_appends(self) -> None:
        a = make_valid_automation()
        a.add_action(ActionType.NOTIFICATION)
        assert len(a.actions) == 1
        assert a.actions[0] == ActionType.NOTIFICATION

    def test_add_action_emits_event(self) -> None:
        a = make_valid_automation()
        a.add_action(ActionType.NOTIFICATION)
        assert isinstance(a.events[-1], ActionAdded)

    def test_add_duplicate_action_raises(self) -> None:
        a = make_valid_automation()
        a.add_action(ActionType.NOTIFICATION)
        with pytest.raises(DuplicateActionTypeError):
            a.add_action(ActionType.NOTIFICATION)

    def test_add_multiple_actions(self) -> None:
        a = make_valid_automation()
        a.add_action(ActionType.NOTIFICATION)
        a.add_action(ActionType.MEMORY)
        assert len(a.actions) == 2

    def test_add_action_to_completed_raises(self) -> None:
        a = make_ready_automation()
        a.activate()
        e = a.start_execution()
        a.complete_execution(e.execution_id, ExecutionResult(value="Done"))
        with pytest.raises(AutomationTerminalError):
            a.add_action(ActionType.NOTIFICATION)


class TestAutomationLifecycle:
    def test_full_lifecycle(self) -> None:
        a = make_ready_automation()
        a.activate()
        assert a.status == AutomationStatus.ACTIVE
        e = a.start_execution()
        assert a.status == AutomationStatus.RUNNING
        a.complete_execution(e.execution_id, ExecutionResult(value="Success"))
        assert a.status == AutomationStatus.COMPLETED
        assert a.is_terminal is True

    def test_fail_then_recover(self) -> None:
        a = make_ready_automation()
        a.activate()
        e = a.start_execution()
        a.fail_execution(e.execution_id, FailureReason(value="Error"))
        assert a.status == AutomationStatus.FAILED
        assert a.is_terminal is False
        trigger = Trigger(trigger_type=TriggerType.MANUAL)
        a.add_trigger(trigger)
        assert len(a.triggers) == 2

    def test_draft_to_disabled_terminal(self) -> None:
        a = make_valid_automation()
        a.disable()
        assert a.status == AutomationStatus.DISABLED
        assert a.is_terminal is True
        with pytest.raises(AutomationTerminalError):
            a.add_trigger(Trigger(trigger_type=TriggerType.MANUAL))

    def test_clear_events(self) -> None:
        a = make_valid_automation()
        a._clear_events()
        assert a.events == []

    def test_events_after_multiple_operations(self) -> None:
        a = make_ready_automation()
        a._clear_events()
        a.activate()
        a.pause()
        a.activate()
        assert len(a.events) == 3


# =============================================================================
# 7. Rule Tests
# =============================================================================


class TestRuleNameRequired:
    def test_valid_name_passes(self) -> None:
        assert_name_required("Report")

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidAutomationNameError, match="required"):
            assert_name_required(None)

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidAutomationNameError, match="required"):
            assert_name_required("")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidAutomationNameError, match="required"):
            assert_name_required("   ")


class TestRuleDescriptionRequired:
    def test_valid_description_passes(self) -> None:
        assert_description_required("Generates report")

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidAutomationDescriptionError, match="required"):
            assert_description_required(None)

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidAutomationDescriptionError, match="required"):
            assert_description_required("")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidAutomationDescriptionError, match="required"):
            assert_description_required("   ")


class TestRuleTriggerExpression:
    def test_with_expression_passes(self) -> None:
        assert_trigger_expression_required(TriggerExpression(value="0 8 * * *"))

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidTriggerExpressionError, match="required"):
            assert_trigger_expression_required(None)


class TestRuleScheduleExpression:
    def test_scheduled_with_expression_passes(self) -> None:
        assert_schedule_expression_required(
            TriggerType.SCHEDULED, ScheduleExpression(value="0 8 * * *"),
        )

    def test_scheduled_without_expression_raises(self) -> None:
        with pytest.raises(InvalidScheduleExpressionError, match="required"):
            assert_schedule_expression_required(TriggerType.SCHEDULED, None)

    def test_manual_without_expression_passes(self) -> None:
        assert_schedule_expression_required(TriggerType.MANUAL, None)


class TestRuleActionTypeValid:
    def test_valid_action_type_passes(self) -> None:
        assert_action_type_valid("notification")

    def test_invalid_action_type_raises(self) -> None:
        with pytest.raises(InvalidActionTypeError):
            assert_action_type_valid("invalid")


class TestRuleTriggerTypeValid:
    def test_valid_trigger_type_passes(self) -> None:
        assert_trigger_type_valid("scheduled")

    def test_invalid_trigger_type_raises(self) -> None:
        with pytest.raises(InvalidActionTypeError):
            assert_trigger_type_valid("invalid")


class TestRuleAutomationHasTriggers:
    def test_with_triggers_passes(self) -> None:
        a = make_valid_automation()
        a.add_trigger(Trigger(trigger_type=TriggerType.MANUAL))
        assert_automation_has_triggers(a)

    def test_without_triggers_raises(self) -> None:
        a = make_valid_automation()
        with pytest.raises(AutomationHasNoTriggersError):
            assert_automation_has_triggers(a)


class TestRuleAutomationHasActions:
    def test_with_actions_passes(self) -> None:
        a = make_valid_automation()
        a.add_action(ActionType.NOTIFICATION)
        assert_automation_has_actions(a)

    def test_without_actions_raises(self) -> None:
        a = make_valid_automation()
        with pytest.raises(AutomationHasNoActionsError):
            assert_automation_has_actions(a)


class TestRuleAutomationNotPaused:
    def test_active_passes(self) -> None:
        a = make_ready_automation()
        a.activate()
        assert_automation_not_paused(a)

    def test_paused_raises(self) -> None:
        a = make_ready_automation()
        a.activate()
        a.pause()
        with pytest.raises(AutomationNotPausedError):
            assert_automation_not_paused(a)

    def test_draft_passes(self) -> None:
        a = make_valid_automation()
        assert_automation_not_paused(a)


class TestRuleAutomationNotTerminal:
    def test_draft_passes(self) -> None:
        a = make_valid_automation()
        assert_automation_not_terminal(a)

    def test_completed_raises(self) -> None:
        a = make_ready_automation()
        a.activate()
        e = a.start_execution()
        a.complete_execution(e.execution_id, ExecutionResult(value="Done"))
        with pytest.raises(AutomationTerminalError):
            assert_automation_not_terminal(a)

    def test_disabled_raises(self) -> None:
        a = make_valid_automation()
        a.disable()
        with pytest.raises(AutomationTerminalError):
            assert_automation_not_terminal(a)

    def test_failed_passes(self) -> None:
        a = make_ready_automation()
        a.activate()
        e = a.start_execution()
        a.fail_execution(e.execution_id, FailureReason(value="Err"))
        assert_automation_not_terminal(a)


class TestRuleExecutionStartedBefore:
    def test_running_passes(self) -> None:
        e = AutomationExecution()
        e.start()
        assert_execution_started_before(e, "complete")

    def test_pending_raises(self) -> None:
        e = AutomationExecution()
        with pytest.raises(ExecutionNotStartedError):
            assert_execution_started_before(e, "complete")

    def test_completed_raises(self) -> None:
        e = AutomationExecution()
        e.start()
        e.complete(ExecutionResult(value="Done"))
        with pytest.raises(ExecutionNotStartedError):
            assert_execution_started_before(e, "complete")


class TestRuleExecutionResultRequired:
    def test_with_result_passes(self) -> None:
        assert_execution_result_required(ExecutionResult(value="OK"))

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidExecutionResultError, match="required"):
            assert_execution_result_required(None)


class TestRuleFailureReasonRequired:
    def test_with_reason_passes(self) -> None:
        assert_failure_reason_required(FailureReason(value="Error"))

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidFailureReasonError, match="required"):
            assert_failure_reason_required(None)


class TestRuleTriggerIdUnique:
    def test_unique_passes(self) -> None:
        t1 = Trigger()
        assert_trigger_id_unique(t1.trigger_id, [Trigger()])

    def test_duplicate_raises(self) -> None:
        t = Trigger()
        with pytest.raises(DuplicateTriggerIdError):
            assert_trigger_id_unique(t.trigger_id, [t])


class TestRuleActionDefinitionUnique:
    def test_unique_passes(self) -> None:
        assert_action_definition_unique(ActionType.NOTIFICATION, [ActionType.MEMORY])

    def test_duplicate_raises(self) -> None:
        with pytest.raises(DuplicateActionTypeError):
            assert_action_definition_unique(ActionType.NOTIFICATION, [ActionType.NOTIFICATION])


class TestRuleTriggerNotEnabledTwice:
    def test_disabled_passes(self) -> None:
        t = Trigger(enabled=False)
        assert_trigger_not_enabled_twice(t)

    def test_enabled_raises(self) -> None:
        t = Trigger(enabled=True)
        with pytest.raises(TriggerAlreadyEnabledError):
            assert_trigger_not_enabled_twice(t)


class TestRuleTriggerNotDisabledTwice:
    def test_enabled_passes(self) -> None:
        t = Trigger(enabled=True)
        assert_trigger_not_disabled_twice(t)

    def test_disabled_raises(self) -> None:
        t = Trigger(enabled=False)
        with pytest.raises(TriggerAlreadyDisabledError):
            assert_trigger_not_disabled_twice(t)


# =============================================================================
# 8. Transition Rule Tests
# =============================================================================


class TestRuleAutomationTransitions:
    def test_draft_to_active(self) -> None:
        assert_automation_can_transition(AutomationStatus.DRAFT, AutomationStatus.ACTIVE)

    def test_draft_to_disabled(self) -> None:
        assert_automation_can_transition(AutomationStatus.DRAFT, AutomationStatus.DISABLED)

    def test_active_to_paused(self) -> None:
        assert_automation_can_transition(AutomationStatus.ACTIVE, AutomationStatus.PAUSED)

    def test_active_to_running(self) -> None:
        assert_automation_can_transition(AutomationStatus.ACTIVE, AutomationStatus.RUNNING)

    def test_active_to_disabled(self) -> None:
        assert_automation_can_transition(AutomationStatus.ACTIVE, AutomationStatus.DISABLED)

    def test_paused_to_active(self) -> None:
        assert_automation_can_transition(AutomationStatus.PAUSED, AutomationStatus.ACTIVE)

    def test_paused_to_disabled(self) -> None:
        assert_automation_can_transition(AutomationStatus.PAUSED, AutomationStatus.DISABLED)

    def test_running_to_completed(self) -> None:
        assert_automation_can_transition(AutomationStatus.RUNNING, AutomationStatus.COMPLETED)

    def test_running_to_failed(self) -> None:
        assert_automation_can_transition(AutomationStatus.RUNNING, AutomationStatus.FAILED)

    def test_running_to_paused(self) -> None:
        assert_automation_can_transition(AutomationStatus.RUNNING, AutomationStatus.PAUSED)

    def test_failed_to_draft(self) -> None:
        assert_automation_can_transition(AutomationStatus.FAILED, AutomationStatus.DRAFT)

    def test_disabled_to_draft(self) -> None:
        assert_automation_can_transition(AutomationStatus.DISABLED, AutomationStatus.DRAFT)

    def test_completed_no_transitions(self) -> None:
        for s in AutomationStatus:
            if s == AutomationStatus.COMPLETED:
                continue
            with pytest.raises(InvalidTransitionError):
                assert_automation_can_transition(AutomationStatus.COMPLETED, s)

    def test_disabled_no_transitions_except_draft(self) -> None:
        for s in AutomationStatus:
            if s == AutomationStatus.DRAFT:
                continue
            with pytest.raises(InvalidTransitionError):
                assert_automation_can_transition(AutomationStatus.DISABLED, s)

    def test_draft_to_running_invalid(self) -> None:
        with pytest.raises(InvalidTransitionError):
            assert_automation_can_transition(AutomationStatus.DRAFT, AutomationStatus.RUNNING)

    def test_draft_to_completed_invalid(self) -> None:
        with pytest.raises(InvalidTransitionError):
            assert_automation_can_transition(AutomationStatus.DRAFT, AutomationStatus.COMPLETED)

    def test_active_to_draft_invalid(self) -> None:
        with pytest.raises(InvalidTransitionError):
            assert_automation_can_transition(AutomationStatus.ACTIVE, AutomationStatus.DRAFT)

    def test_valid_transitions_dict(self) -> None:
        for status in AutomationStatus:
            assert status in VALID_AUTOMATION_TRANSITIONS


class TestRuleExecutionTransitions:
    def test_pending_to_running(self) -> None:
        assert_execution_can_transition(ExecutionStatus.PENDING, ExecutionStatus.RUNNING)

    def test_pending_to_cancelled(self) -> None:
        assert_execution_can_transition(ExecutionStatus.PENDING, ExecutionStatus.CANCELLED)

    def test_running_to_completed(self) -> None:
        assert_execution_can_transition(ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED)

    def test_running_to_failed(self) -> None:
        assert_execution_can_transition(ExecutionStatus.RUNNING, ExecutionStatus.FAILED)

    def test_running_to_cancelled(self) -> None:
        assert_execution_can_transition(ExecutionStatus.RUNNING, ExecutionStatus.CANCELLED)

    def test_completed_no_transitions(self) -> None:
        for s in ExecutionStatus:
            if s == ExecutionStatus.COMPLETED:
                continue
            with pytest.raises(InvalidTransitionError):
                assert_execution_can_transition(ExecutionStatus.COMPLETED, s)

    def test_failed_no_transitions(self) -> None:
        for s in ExecutionStatus:
            if s == ExecutionStatus.FAILED:
                continue
            with pytest.raises(InvalidTransitionError):
                assert_execution_can_transition(ExecutionStatus.FAILED, s)

    def test_cancelled_no_transitions(self) -> None:
        for s in ExecutionStatus:
            if s == ExecutionStatus.CANCELLED:
                continue
            with pytest.raises(InvalidTransitionError):
                assert_execution_can_transition(ExecutionStatus.CANCELLED, s)

    def test_pending_to_completed_invalid(self) -> None:
        with pytest.raises(InvalidTransitionError):
            assert_execution_can_transition(ExecutionStatus.PENDING, ExecutionStatus.COMPLETED)

    def test_valid_transitions_dict(self) -> None:
        for status in ExecutionStatus:
            assert status in VALID_EXECUTION_TRANSITIONS


# =============================================================================
# 9. Factory Tests
# =============================================================================


class TestFactoryCreateAutomation:
    def test_happy_path(self) -> None:
        a, ev = AutomationFactory.create_automation(
            name="Daily Report",
            description="Generates daily report",
        )
        assert isinstance(a, Automation)
        assert isinstance(ev, AutomationCreated)
        assert a.name is not None
        assert a.name.value == "Daily Report"
        assert a.description is not None
        assert a.description.value == "Generates daily report"
        assert a.status == AutomationStatus.DRAFT
        assert a.execution_mode == ExecutionMode.ONCE

    def test_event_payload(self) -> None:
        a, ev = AutomationFactory.create_automation(
            name="Report",
            description="Daily",
            execution_mode="recurring",
        )
        assert ev.automation_id == a.automation_id
        assert ev.name == "Report"
        assert ev.description == "Daily"
        assert ev.execution_mode == "recurring"

    def test_execution_mode_enum_accepted(self) -> None:
        a, ev = AutomationFactory.create_automation(
            name="Test",
            description="Test desc",
            execution_mode=ExecutionMode.RECURRING,
        )
        assert a.execution_mode == ExecutionMode.RECURRING

    def test_empty_name_raises(self) -> None:
        with pytest.raises(InvalidAutomationNameError):
            AutomationFactory.create_automation(name="", description="Desc")

    def test_empty_description_raises(self) -> None:
        with pytest.raises(InvalidAutomationDescriptionError):
            AutomationFactory.create_automation(name="Test", description="")

    def test_default_created_at(self) -> None:
        a, ev = AutomationFactory.create_automation(name="Test", description="Desc")
        assert isinstance(a.created_at, datetime)
        assert isinstance(ev.occurred_at, datetime)


class TestFactoryAddTrigger:
    def test_happy_path(self) -> None:
        a = make_valid_automation()
        t, ev = AutomationFactory.add_trigger(
            automation=a,
            trigger_type="manual",
            expression="run now",
        )
        assert isinstance(t, Trigger)
        assert isinstance(ev, TriggerAdded)
        assert t.trigger_type == TriggerType.MANUAL
        assert t.expression is not None
        assert len(a.triggers) == 1

    def test_trigger_type_enum_accepted(self) -> None:
        a = make_valid_automation()
        t, ev = AutomationFactory.add_trigger(
            automation=a,
            trigger_type=TriggerType.MANUAL,
        )
        assert t.trigger_type == TriggerType.MANUAL

    def test_invalid_trigger_type_raises(self) -> None:
        a = make_valid_automation()
        with pytest.raises(InvalidActionTypeError):
            AutomationFactory.add_trigger(automation=a, trigger_type="unknown")

    def test_scheduled_without_expression_raises(self) -> None:
        a = make_valid_automation()
        with pytest.raises(InvalidScheduleExpressionError):
            AutomationFactory.add_trigger(automation=a, trigger_type="scheduled")

    def test_manual_without_expression(self) -> None:
        a = make_valid_automation()
        t, ev = AutomationFactory.add_trigger(automation=a, trigger_type="manual")
        assert t.trigger_type == TriggerType.MANUAL
        assert t.expression is None

    def test_scheduled_with_expression(self) -> None:
        a = make_valid_automation()
        t, ev = AutomationFactory.add_trigger(
            automation=a,
            trigger_type="scheduled",
            expression="0 8 * * *",
        )
        assert t.trigger_type == TriggerType.SCHEDULED
        assert t.expression is not None


class TestFactoryAddAction:
    def test_happy_path(self) -> None:
        a = make_valid_automation()
        AutomationFactory.add_action(automation=a, action_type="notification")
        assert len(a.actions) == 1
        assert a.actions[0] == ActionType.NOTIFICATION

    def test_action_type_enum_accepted(self) -> None:
        a = make_valid_automation()
        AutomationFactory.add_action(automation=a, action_type=ActionType.MEMORY)
        assert a.actions[0] == ActionType.MEMORY

    def test_invalid_action_type_raises(self) -> None:
        a = make_valid_automation()
        with pytest.raises(InvalidActionTypeError):
            AutomationFactory.add_action(automation=a, action_type="invalid")


class TestFactoryEnableDisableTrigger:
    def test_enable_trigger(self) -> None:
        a = make_valid_automation()
        t = Trigger(enabled=False)
        a.add_trigger(t)
        AutomationFactory.enable_trigger(automation=a, trigger_id=t.trigger_id)
        assert t.enabled is True

    def test_disable_trigger(self) -> None:
        a = make_valid_automation()
        t = Trigger(enabled=True)
        a.add_trigger(t)
        AutomationFactory.disable_trigger(automation=a, trigger_id=t.trigger_id)
        assert t.enabled is False


class TestFactoryStartExecution:
    def test_happy_path(self) -> None:
        a = make_ready_automation()
        a.activate()
        e, ev = AutomationFactory.start_execution(automation=a)
        assert isinstance(e, AutomationExecution)
        assert isinstance(ev, AutomationExecutionStarted)
        assert e.status == ExecutionStatus.RUNNING
        assert a.status == AutomationStatus.RUNNING


class TestFactoryCompleteExecution:
    def test_happy_path(self) -> None:
        a = make_ready_automation()
        a.activate()
        e, _ = AutomationFactory.start_execution(automation=a)
        ev = AutomationFactory.complete_execution(
            automation=a,
            execution_id=e.execution_id,
            result="Success",
        )
        assert isinstance(ev, AutomationExecutionCompleted)
        assert ev.result == "Success"
        assert e.status == ExecutionStatus.COMPLETED

    def test_empty_result_raises(self) -> None:
        a = make_ready_automation()
        a.activate()
        e, _ = AutomationFactory.start_execution(automation=a)
        with pytest.raises(InvalidExecutionResultError):
            AutomationFactory.complete_execution(
                automation=a,
                execution_id=e.execution_id,
                result="",
            )


class TestFactoryFailExecution:
    def test_happy_path(self) -> None:
        a = make_ready_automation()
        a.activate()
        e, _ = AutomationFactory.start_execution(automation=a)
        ev = AutomationFactory.fail_execution(
            automation=a,
            execution_id=e.execution_id,
            reason="Timeout",
        )
        assert isinstance(ev, AutomationExecutionFailed)
        assert ev.failure_reason == "Timeout"
        assert e.status == ExecutionStatus.FAILED

    def test_empty_reason_raises(self) -> None:
        a = make_ready_automation()
        a.activate()
        e, _ = AutomationFactory.start_execution(automation=a)
        with pytest.raises(InvalidFailureReasonError):
            AutomationFactory.fail_execution(
                automation=a,
                execution_id=e.execution_id,
                reason="",
            )


class TestFactoryActivatePauseDisable:
    def test_activate(self) -> None:
        a = make_ready_automation()
        AutomationFactory.activate(a)
        assert a.status == AutomationStatus.ACTIVE

    def test_pause(self) -> None:
        a = make_ready_automation()
        AutomationFactory.activate(a)
        AutomationFactory.pause(a)
        assert a.status == AutomationStatus.PAUSED

    def test_disable(self) -> None:
        a = make_valid_automation()
        AutomationFactory.disable(a)
        assert a.status == AutomationStatus.DISABLED


# =============================================================================
# 10. Automation Lifecycle Through Factory
# =============================================================================


class TestAutomationLifecycleThroughFactory:
    def test_full_lifecycle(self) -> None:
        a, _ = AutomationFactory.create_automation(
            name="My Automation",
            description="Full lifecycle test",
        )
        AutomationFactory.add_trigger(
            automation=a,
            trigger_type="manual",
        )
        AutomationFactory.add_action(automation=a, action_type="notification")
        AutomationFactory.activate(a)
        assert a.status == AutomationStatus.ACTIVE
        e, _ = AutomationFactory.start_execution(automation=a)
        assert a.status == AutomationStatus.RUNNING
        AutomationFactory.complete_execution(
            automation=a,
            execution_id=e.execution_id,
            result="Completed",
        )
        assert a.status == AutomationStatus.COMPLETED

    def test_fail_then_recover_through_factory(self) -> None:
        a, _ = AutomationFactory.create_automation(
            name="Recoverable",
            description="Can recover from failure",
        )
        AutomationFactory.add_trigger(automation=a, trigger_type="manual")
        AutomationFactory.add_action(automation=a, action_type="memory")
        AutomationFactory.activate(a)
        e, _ = AutomationFactory.start_execution(automation=a)
        AutomationFactory.fail_execution(
            automation=a,
            execution_id=e.execution_id,
            reason="Network error",
        )
        assert a.status == AutomationStatus.FAILED
        assert a.is_terminal is False
        AutomationFactory.add_trigger(
            automation=a,
            trigger_type="manual",
        )
        assert len(a.triggers) == 2

    def test_disable_through_factory(self) -> None:
        a, _ = AutomationFactory.create_automation(
            name="DisableMe",
            description="Will be disabled",
        )
        AutomationFactory.disable(a)
        assert a.is_terminal is True
