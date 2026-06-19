from __future__ import annotations


class OrchestratorDomainError(Exception):
    """Base exception for all orchestrator domain errors."""


class InvalidUserIntentError(OrchestratorDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid user intent: {reason}")


class InvalidWorkflowGoalError(OrchestratorDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid workflow goal: {reason}")


class InvalidAgentRoleError(OrchestratorDomainError):
    def __init__(self, role: str) -> None:
        super().__init__(f"Invalid agent role: {role!r}")
        self.role = role


class InvalidExecutionOrderError(OrchestratorDomainError):
    def __init__(self, order: int) -> None:
        super().__init__(f"Execution order must be non-negative, got {order}")
        self.order = order


class InvalidFailureReasonError(OrchestratorDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid failure reason: {reason}")


class InvalidExecutionResultError(OrchestratorDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid execution result: {reason}")


class InvalidTransitionError(OrchestratorDomainError):
    def __init__(self, entity: str, current: str, target: str) -> None:
        super().__init__(
            f"Invalid {entity} transition from {current!r} to {target!r}"
        )
        self.entity = entity
        self.current = current
        self.target = target


class OrchestrationTerminalError(OrchestratorDomainError):
    def __init__(self, status: str) -> None:
        super().__init__(
            f"Orchestration is in terminal state {status!r} and cannot be modified"
        )
        self.status = status


class WorkflowTerminalError(OrchestratorDomainError):
    def __init__(self, status: str) -> None:
        super().__init__(
            f"Workflow is in terminal state {status!r} and cannot be modified"
        )
        self.status = status


class WorkflowStepTerminalError(OrchestratorDomainError):
    def __init__(self, status: str) -> None:
        super().__init__(
            f"Workflow step is in terminal state {status!r} and cannot transition"
        )
        self.status = status


class WorkflowHasNoStepsError(OrchestratorDomainError):
    def __init__(self) -> None:
        super().__init__("Workflow must have at least one step before start")


class StepNotStartedError(OrchestratorDomainError):
    def __init__(self, action: str) -> None:
        super().__init__(f"Step must be started before {action}")


class WorkflowNotStartedError(OrchestratorDomainError):
    def __init__(self, action: str) -> None:
        super().__init__(f"Workflow must be started before {action}")


class DuplicateExecutionOrderError(OrchestratorDomainError):
    def __init__(self, order: int) -> None:
        super().__init__(
            f"Duplicate execution order {order} not allowed in SEQUENTIAL mode"
        )
        self.order = order


class DuplicateWorkflowIdError(OrchestratorDomainError):
    def __init__(self) -> None:
        super().__init__("Duplicate workflow IDs not allowed within orchestration")


class HybridModeRequiresTwoStepsError(OrchestratorDomainError):
    def __init__(self) -> None:
        super().__init__("HYBRID mode requires at least two steps")


class AllWorkflowsNotCompletedError(OrchestratorDomainError):
    def __init__(self) -> None:
        super().__init__("All workflows must be completed before orchestration can complete")
