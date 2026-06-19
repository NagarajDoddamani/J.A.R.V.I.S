"""In-memory workflow state storage.

This is the initial implementation; a persistent backend (e.g. SQLite,
PostgreSQL) can be swapped in later without changing the engine interface.
"""

from __future__ import annotations

from backend.runtime.workflows.errors import WorkflowInstanceNotFoundError
from backend.runtime.workflows.models import WorkflowInstance


class WorkflowState:
    """Abstract interface for workflow state persistence."""

    def save(self, instance: WorkflowInstance) -> None:
        ...

    def load(self, instance_id: str) -> WorkflowInstance:
        ...

    def delete(self, instance_id: str) -> None:
        ...

    def list_all(self) -> list[WorkflowInstance]:
        ...


class InMemoryWorkflowState(WorkflowState):
    """Thread-safe (for async) in-memory workflow state store."""

    def __init__(self) -> None:
        self._instances: dict[str, WorkflowInstance] = {}

    def save(self, instance: WorkflowInstance) -> None:
        self._instances[instance.instance_id] = instance

    def load(self, instance_id: str) -> WorkflowInstance:
        instance = self._instances.get(instance_id)
        if instance is None:
            raise WorkflowInstanceNotFoundError(f"Workflow instance not found: {instance_id}")
        return instance

    def delete(self, instance_id: str) -> None:
        self._instances.pop(instance_id, None)

    def list_all(self) -> list[WorkflowInstance]:
        return list(self._instances.values())

    def clear(self) -> None:
        self._instances.clear()
