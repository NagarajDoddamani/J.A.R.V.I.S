from __future__ import annotations

from backend.automation.domain.model import (
    ActionType,
    Automation,
    AutomationExecution,
    AutomationStatus,
    ExecutionResult,
    ExecutionStatus,
    FailureReason,
    ScheduleExpression,
    Trigger,
    TriggerExpression,
    TriggerType,
    VALID_AUTOMATION_TRANSITIONS,
    VALID_EXECUTION_TRANSITIONS,
)


# -- Name -----------------------------------------------------------------


def assert_name_required(name: str | None) -> None:
    if not name or not name.strip():
        from backend.automation.domain.exceptions import InvalidAutomationNameError

        raise InvalidAutomationNameError("Automation name is required")


# -- Description ----------------------------------------------------------


def assert_description_required(description: str | None) -> None:
    if not description or not description.strip():
        from backend.automation.domain.exceptions import (
            InvalidAutomationDescriptionError,
        )

        raise InvalidAutomationDescriptionError("Automation description is required")


# -- Trigger expression ---------------------------------------------------


def assert_trigger_expression_required(expression: TriggerExpression | None) -> None:
    if expression is None:
        from backend.automation.domain.exceptions import (
            InvalidTriggerExpressionError,
        )

        raise InvalidTriggerExpressionError("Trigger expression is required")


# -- Schedule expression --------------------------------------------------


def assert_schedule_expression_required(
    trigger_type: TriggerType,
    expression: ScheduleExpression | None,
) -> None:
    if trigger_type == TriggerType.SCHEDULED and expression is None:
        from backend.automation.domain.exceptions import (
            InvalidScheduleExpressionError,
        )

        raise InvalidScheduleExpressionError(
            "Schedule expression is required for scheduled triggers"
        )


# -- Action type ----------------------------------------------------------


def assert_action_type_valid(action_type: str) -> None:
    try:
        ActionType(action_type)
    except ValueError:
        from backend.automation.domain.exceptions import InvalidActionTypeError

        raise InvalidActionTypeError(action_type)


# -- Trigger type ---------------------------------------------------------


def assert_trigger_type_valid(trigger_type: str) -> None:
    try:
        TriggerType(trigger_type)
    except ValueError:
        from backend.automation.domain.exceptions import InvalidActionTypeError

        raise InvalidActionTypeError(trigger_type)


# -- Has triggers/actions -------------------------------------------------


def assert_automation_has_triggers(automation: Automation) -> None:
    if not automation.triggers:
        from backend.automation.domain.exceptions import (
            AutomationHasNoTriggersError,
        )

        raise AutomationHasNoTriggersError(
            "Automation must have at least one trigger before activation"
        )


def assert_automation_has_actions(automation: Automation) -> None:
    if not automation.actions:
        from backend.automation.domain.exceptions import (
            AutomationHasNoActionsError,
        )

        raise AutomationHasNoActionsError(
            "Automation must have at least one action before activation"
        )


# -- Not paused -----------------------------------------------------------


def assert_automation_not_paused(automation: Automation) -> None:
    if automation.status == AutomationStatus.PAUSED:
        from backend.automation.domain.exceptions import (
            AutomationNotPausedError,
        )

        raise AutomationNotPausedError()


# -- Terminal states ------------------------------------------------------


def assert_automation_not_terminal(automation: Automation) -> None:
    if automation.is_terminal:
        from backend.automation.domain.exceptions import (
            AutomationTerminalError,
        )

        raise AutomationTerminalError(automation.status.value)


# -- Transition guards ----------------------------------------------------


def assert_automation_can_transition(
    current: AutomationStatus, target: AutomationStatus
) -> None:
    allowed = VALID_AUTOMATION_TRANSITIONS.get(current, set())
    if target not in allowed:
        from backend.automation.domain.exceptions import InvalidTransitionError

        raise InvalidTransitionError(current.value, target.value)


def assert_execution_can_transition(
    current: ExecutionStatus, target: ExecutionStatus
) -> None:
    allowed = VALID_EXECUTION_TRANSITIONS.get(current, set())
    if target not in allowed:
        from backend.automation.domain.exceptions import InvalidTransitionError

        raise InvalidTransitionError(current.value, target.value)


# -- Execution guards -----------------------------------------------------


def assert_execution_started_before(execution: AutomationExecution, action: str) -> None:
    if execution.status not in (ExecutionStatus.RUNNING,):
        from backend.automation.domain.exceptions import (
            ExecutionNotStartedError,
        )

        raise ExecutionNotStartedError(action)


def assert_execution_result_required(result: ExecutionResult | None) -> None:
    if result is None:
        from backend.automation.domain.exceptions import (
            InvalidExecutionResultError,
        )

        raise InvalidExecutionResultError("Execution result is required")


def assert_failure_reason_required(reason: FailureReason | None) -> None:
    if reason is None:
        from backend.automation.domain.exceptions import (
            InvalidFailureReasonError,
        )

        raise InvalidFailureReasonError("Failure reason is required")


# -- Uniqueness guards ----------------------------------------------------


def assert_trigger_id_unique(trigger_id, existing_triggers: list[Trigger]) -> None:
    for trigger in existing_triggers:
        if trigger.trigger_id == trigger_id:
            from backend.automation.domain.exceptions import (
                DuplicateTriggerIdError,
            )

            raise DuplicateTriggerIdError(str(trigger_id))


def assert_action_definition_unique(
    action_type: ActionType, existing_actions: list[ActionType]
) -> None:
    for existing in existing_actions:
        if existing == action_type:
            from backend.automation.domain.exceptions import (
                DuplicateActionTypeError,
            )

            raise DuplicateActionTypeError(action_type.value)


# -- Trigger guards -------------------------------------------------------


def assert_trigger_not_enabled_twice(trigger: Trigger) -> None:
    if trigger.enabled:
        from backend.automation.domain.exceptions import (
            TriggerAlreadyEnabledError,
        )

        raise TriggerAlreadyEnabledError()


def assert_trigger_not_disabled_twice(trigger: Trigger) -> None:
    if not trigger.enabled:
        from backend.automation.domain.exceptions import (
            TriggerAlreadyDisabledError,
        )

        raise TriggerAlreadyDisabledError()
