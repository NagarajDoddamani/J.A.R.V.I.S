from __future__ import annotations

from typing import Protocol


class AutomationIdGeneratorPort(Protocol):
    """Identifier generator for the automation domain.

    Produces unique string identifiers for automations, triggers,
    and executions. Swappable implementations allow UUID-based
    generation in production or deterministic sequences in tests.
    """

    def generate_automation_id(self) -> str:
        """Generate a unique automation identifier.

        The returned string MUST be globally unique and suitable for
        use as an ``AutomationId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...

    def generate_trigger_id(self) -> str:
        """Generate a unique trigger identifier.

        The returned string MUST be globally unique and suitable for
        use as a ``TriggerId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...

    def generate_execution_id(self) -> str:
        """Generate a unique execution identifier.

        The returned string MUST be globally unique and suitable for
        use as a ``WorkflowExecutionId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...
