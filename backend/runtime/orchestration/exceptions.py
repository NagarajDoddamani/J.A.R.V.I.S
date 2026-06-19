from __future__ import annotations


class RuntimeOrchestrationError(Exception):
    """Base exception for runtime orchestration errors."""


class UnknownWorkflowError(RuntimeOrchestrationError):
    """Raised when an unknown workflow type is requested."""


class OrchestrationWorkflowExecutionError(RuntimeOrchestrationError):
    """Raised when a workflow execution fails."""


class WorkflowTemplateError(RuntimeOrchestrationError):
    """Raised when a workflow template is malformed or cannot be constructed."""
