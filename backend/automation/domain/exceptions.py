from __future__ import annotations


class AutomationDomainError(Exception):
    """Base exception for automation domain errors."""

    def __init__(self, message: str = "") -> None:
        self.message = message
        super().__init__(message)


class InvalidAutomationNameError(AutomationDomainError):
    pass


class InvalidAutomationDescriptionError(AutomationDomainError):
    pass


class InvalidTriggerExpressionError(AutomationDomainError):
    pass


class InvalidScheduleExpressionError(AutomationDomainError):
    pass


class InvalidExecutionResultError(AutomationDomainError):
    pass


class InvalidFailureReasonError(AutomationDomainError):
    pass


class InvalidTransitionError(AutomationDomainError):
    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition from {current} to {target}")


class AutomationTerminalError(AutomationDomainError):
    def __init__(self, status: str) -> None:
        self.status = status
        super().__init__(f"Automation is terminal in status {status}")


class AutomationHasNoTriggersError(AutomationDomainError):
    pass


class AutomationHasNoActionsError(AutomationDomainError):
    pass


class AutomationNotPausedError(AutomationDomainError):
    def __init__(self) -> None:
        super().__init__("Automation is paused and cannot execute")


class ExecutionNotStartedError(AutomationDomainError):
    def __init__(self, action: str) -> None:
        self.action = action
        super().__init__(f"Execution must start before {action}")


class ExecutionNotFoundError(AutomationDomainError):
    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id
        super().__init__(f"Execution not found: {execution_id}")


class DuplicateTriggerIdError(AutomationDomainError):
    def __init__(self, trigger_id: str) -> None:
        self.trigger_id = trigger_id
        super().__init__(f"Duplicate trigger ID: {trigger_id}")


class DuplicateActionTypeError(AutomationDomainError):
    def __init__(self, action_type: str) -> None:
        self.action_type = action_type
        super().__init__(f"Duplicate action type: {action_type}")


class TriggerAlreadyEnabledError(AutomationDomainError):
    def __init__(self) -> None:
        super().__init__("Trigger is already enabled")


class TriggerAlreadyDisabledError(AutomationDomainError):
    def __init__(self) -> None:
        super().__init__("Trigger is already disabled")


class InvalidActionTypeError(AutomationDomainError):
    def __init__(self, action_type: str) -> None:
        self.action_type = action_type
        super().__init__(f"Invalid action type: {action_type}")


class TriggerNotFoundError(AutomationDomainError):
    def __init__(self, trigger_id: str) -> None:
        self.trigger_id = trigger_id
        super().__init__(f"Trigger not found: {trigger_id}")
