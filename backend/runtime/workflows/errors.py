from __future__ import annotations


class WorkflowError(Exception):
    """Base exception for workflow engine errors."""


class WorkflowNotFoundError(WorkflowError):
    """Raised when a workflow type is not registered."""


class WorkflowInstanceNotFoundError(WorkflowError):
    """Raised when a workflow instance does not exist."""


class WorkflowStepNotFoundError(WorkflowError):
    """Raised when a step is not found in a workflow instance."""


class WorkflowExecutionError(WorkflowError):
    """Raised when a step execution fails."""


class WorkflowTimeoutError(WorkflowError):
    """Raised when a workflow or step exceeds its timeout."""


class WorkflowInvalidTransitionError(WorkflowError):
    """Raised when a state transition is not allowed (e.g. completing a
    step that has already failed)."""


class WorkflowDependencyError(WorkflowError):
    """Raised when step dependencies form an invalid graph (e.g. cycle)."""
