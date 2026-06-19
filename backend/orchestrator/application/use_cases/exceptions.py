from __future__ import annotations


class UseCaseError(Exception):
    """Base exception for all use-case-level errors."""


class OrchestrationNotFoundError(UseCaseError):
    def __init__(self, orchestration_id: str) -> None:
        super().__init__(f"Orchestration not found: {orchestration_id}")
        self.orchestration_id = orchestration_id


class WorkflowNotFoundError(UseCaseError):
    def __init__(self, workflow_id: str) -> None:
        super().__init__(f"Workflow not found: {workflow_id}")
        self.workflow_id = workflow_id


class WorkflowStepNotFoundError(UseCaseError):
    def __init__(self, step_id: str) -> None:
        super().__init__(f"Workflow step not found: {step_id}")
        self.step_id = step_id
