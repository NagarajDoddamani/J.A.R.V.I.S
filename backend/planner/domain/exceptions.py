from __future__ import annotations


class PlannerDomainError(Exception):
    """Base exception for all planner domain errors."""


class InvalidUserRequestError(PlannerDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid user request: {reason}")


class InvalidPlanGoalError(PlannerDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid plan goal: {reason}")


class InvalidPlanPriorityError(PlannerDomainError):
    def __init__(self, priority: str) -> None:
        super().__init__(f"Invalid plan priority: {priority!r}")
        self.priority = priority


class InvalidExecutionStrategyError(PlannerDomainError):
    def __init__(self, strategy: str) -> None:
        super().__init__(f"Invalid execution strategy: {strategy!r}")
        self.strategy = strategy


class InvalidAgentTypeError(PlannerDomainError):
    def __init__(self, agent: str) -> None:
        super().__init__(f"Invalid agent type: {agent!r}")
        self.agent = agent


class InvalidTaskDescriptionError(PlannerDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid task description: {reason}")


class InvalidFailureReasonError(PlannerDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid failure reason: {reason}")


class InvalidEstimatedDurationError(PlannerDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid estimated duration: {reason}")


class InvalidTransitionError(PlannerDomainError):
    def __init__(self, entity: str, current: str, target: str) -> None:
        super().__init__(
            f"Invalid {entity} transition from {current!r} to {target!r}"
        )
        self.entity = entity
        self.current = current
        self.target = target


class PlanHasNoTasksError(PlannerDomainError):
    def __init__(self) -> None:
        super().__init__("Plan must have at least one task before READY")


class PlanNotReadyError(PlannerDomainError):
    def __init__(self, status: str) -> None:
        super().__init__(f"Plan must be READY before EXECUTING, got {status!r}")
        self.status = status


class PlanTerminalError(PlannerDomainError):
    def __init__(self, status: str) -> None:
        super().__init__(f"Plan is in terminal state {status!r} and cannot be modified")
        self.status = status


class TaskNotAssignedError(PlannerDomainError):
    def __init__(self) -> None:
        super().__init__("Task must have an assigned agent before RUNNING")


class TaskTerminalError(PlannerDomainError):
    def __init__(self, status: str) -> None:
        super().__init__(f"Task is in terminal state {status!r} and cannot transition")
        self.status = status


class DuplicateTaskIdError(PlannerDomainError):
    def __init__(self) -> None:
        super().__init__("Plan must have unique task IDs")


class DuplicateExecutionStepIdError(PlannerDomainError):
    def __init__(self) -> None:
        super().__init__("Tasks must have unique execution step IDs")


class InvalidStepOrderError(PlannerDomainError):
    def __init__(self, order: int) -> None:
        super().__init__(f"Step order must be non-negative, got {order}")
        self.order = order


class EmptyPlanExecutionError(PlannerDomainError):
    def __init__(self) -> None:
        super().__init__("Empty plans cannot execute")


class HybridStrategyRequiresMultipleTasksError(PlannerDomainError):
    def __init__(self) -> None:
        super().__init__("HYBRID strategy requires at least 2 tasks")
