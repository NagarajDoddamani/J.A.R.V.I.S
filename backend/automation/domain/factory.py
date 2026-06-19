from __future__ import annotations

from datetime import datetime, timezone

from backend.automation.domain.model import (
    ActionType,
    Automation,
    AutomationCreated,
    AutomationExecution,
    AutomationExecutionCompleted,
    AutomationExecutionFailed,
    AutomationExecutionStarted,
    AutomationDescription,
    AutomationId,
    AutomationName,
    AutomationStatus,
    ExecutionMode,
    ExecutionResult,
    FailureReason,
    Trigger,
    TriggerAdded,
    TriggerExpression,
    TriggerId,
    TriggerType,
    WorkflowExecutionId,
)

from backend.automation.domain.rules import (
    assert_action_type_valid,
    assert_description_required,
    assert_execution_result_required,
    assert_failure_reason_required,
    assert_name_required,
    assert_trigger_type_valid,
)


class AutomationFactory:
    """Factory for creating validated automation domain aggregates."""

    @staticmethod
    def create_automation(
        *,
        name: str,
        description: str,
        execution_mode: str | ExecutionMode = ExecutionMode.ONCE,
    ) -> tuple[Automation, AutomationCreated]:
        assert_name_required(name)
        assert_description_required(description)

        if isinstance(execution_mode, str):
            execution_mode = ExecutionMode(execution_mode)

        name_vo = AutomationName(value=name)
        description_vo = AutomationDescription(value=description)
        now = datetime.now(tz=timezone.utc)

        automation = Automation(
            automation_id=AutomationId(),
            name=name_vo,
            description=description_vo,
            status=AutomationStatus.DRAFT,
            execution_mode=execution_mode,
            created_at=now,
        )

        event = AutomationCreated(
            automation_id=automation.automation_id,
            name=name,
            description=description,
            execution_mode=execution_mode.value,
            occurred_at=now,
        )

        return automation, event

    @staticmethod
    def add_trigger(
        *,
        automation: Automation,
        trigger_type: str | TriggerType,
        expression: str | None = None,
    ) -> tuple[Trigger, TriggerAdded]:
        if isinstance(trigger_type, str):
            assert_trigger_type_valid(trigger_type)
            trigger_type = TriggerType(trigger_type)

        expression_vo: TriggerExpression | None = None
        if expression is not None:
            expression_vo = TriggerExpression(value=expression)

        if trigger_type == TriggerType.SCHEDULED and expression is None:
            from backend.automation.domain.exceptions import (
                InvalidScheduleExpressionError,
            )

            raise InvalidScheduleExpressionError(
                "Schedule expression is required for scheduled triggers"
            )

        trigger = Trigger(
            trigger_id=TriggerId(),
            trigger_type=trigger_type,
            expression=expression_vo,
        )

        automation.add_trigger(trigger)
        event = automation.events[-1]

        return trigger, event

    @staticmethod
    def add_action(
        *,
        automation: Automation,
        action_type: str | ActionType,
    ) -> None:
        if isinstance(action_type, str):
            assert_action_type_valid(action_type)
            action_type = ActionType(action_type)

        automation.add_action(action_type)

    @staticmethod
    def enable_trigger(
        *,
        automation: Automation,
        trigger_id: TriggerId,
    ) -> None:
        automation.enable_trigger(trigger_id)

    @staticmethod
    def disable_trigger(
        *,
        automation: Automation,
        trigger_id: TriggerId,
    ) -> None:
        automation.disable_trigger(trigger_id)

    @staticmethod
    def start_execution(
        *,
        automation: Automation,
    ) -> tuple[AutomationExecution, AutomationExecutionStarted]:
        execution = automation.start_execution()
        event = automation.events[-1]
        return execution, event

    @staticmethod
    def complete_execution(
        *,
        automation: Automation,
        execution_id: WorkflowExecutionId,
        result: str,
    ) -> AutomationExecutionCompleted:
        result_vo = ExecutionResult(value=result)
        automation.complete_execution(execution_id, result_vo)
        return automation.events[-1]

    @staticmethod
    def fail_execution(
        *,
        automation: Automation,
        execution_id: WorkflowExecutionId,
        reason: str,
    ) -> AutomationExecutionFailed:
        reason_vo = FailureReason(value=reason)
        automation.fail_execution(execution_id, reason_vo)
        return automation.events[-1]

    @staticmethod
    def activate(automation: Automation) -> None:
        automation.activate()

    @staticmethod
    def pause(automation: Automation) -> None:
        automation.pause()

    @staticmethod
    def disable(automation: Automation) -> None:
        automation.disable()
