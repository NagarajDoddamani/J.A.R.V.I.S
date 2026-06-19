from __future__ import annotations


class UseCaseError(Exception):
    """Base exception for all use-case-level errors."""


class PlanNotFoundError(UseCaseError):
    def __init__(self, plan_id: str) -> None:
        super().__init__(f"Plan not found: {plan_id}")
        self.plan_id = plan_id


class TaskNotFoundError(UseCaseError):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task not found: {task_id}")
        self.task_id = task_id
