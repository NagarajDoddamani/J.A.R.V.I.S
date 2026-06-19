from __future__ import annotations


class UseCaseError(Exception):
    """Base exception for all use-case-level errors."""


class AutomationNotFoundError(UseCaseError):
    def __init__(self, automation_id: str) -> None:
        super().__init__(f"Automation not found: {automation_id}")
        self.automation_id = automation_id


class TriggerNotFoundError(UseCaseError):
    def __init__(self, trigger_id: str) -> None:
        super().__init__(f"Trigger not found: {trigger_id}")
        self.trigger_id = trigger_id


class AutomationExecutionNotFoundError(UseCaseError):
    def __init__(self, execution_id: str) -> None:
        super().__init__(f"Automation execution not found: {execution_id}")
        self.execution_id = execution_id
