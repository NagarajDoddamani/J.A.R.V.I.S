from __future__ import annotations

from backend.runtime.workflows.errors import WorkflowNotFoundError
from backend.runtime.workflows.models import WorkflowDefinition


class WorkflowRegistry:
    """Maps workflow types (e.g. ``"research_plan"``) to their
    :class:`WorkflowDefinition`.
    """

    def __init__(self) -> None:
        self._definitions: dict[str, WorkflowDefinition] = {}

    def register(self, definition: WorkflowDefinition) -> None:
        """Register a workflow definition.

        Raises ``ValueError`` if the workflow type is already registered.
        """
        if definition.workflow_type in self._definitions:
            raise ValueError(
                f"Workflow type {definition.workflow_type!r} is already registered"
            )
        self._definitions[definition.workflow_type] = definition

    def register_or_replace(self, definition: WorkflowDefinition) -> None:
        """Register or replace a workflow definition."""
        self._definitions[definition.workflow_type] = definition

    def get(self, workflow_type: str) -> WorkflowDefinition:
        """Return the definition for *workflow_type* or raise."""
        definition = self._definitions.get(workflow_type)
        if definition is None:
            raise WorkflowNotFoundError(f"Workflow type not registered: {workflow_type!r}")
        return definition

    def unregister(self, workflow_type: str) -> None:
        """Remove a registered workflow definition."""
        self._definitions.pop(workflow_type, None)

    def has(self, workflow_type: str) -> bool:
        """Return ``True`` if the workflow type is registered."""
        return workflow_type in self._definitions

    @property
    def registered_types(self) -> frozenset[str]:
        return frozenset(self._definitions)

    def clear(self) -> None:
        self._definitions.clear()
