from __future__ import annotations

from typing import Protocol


class OrchestratorIdGeneratorPort(Protocol):
    """Identifier generator for the orchestrator domain.

    Produces unique string identifiers for orchestrations, workflows,
    and steps. Swappable implementations allow UUID-based generation
    in production or deterministic sequences in tests.
    """

    def generate_orchestration_id(self) -> str:
        """Generate a unique orchestration identifier.

        The returned string MUST be globally unique and suitable for
        use as an ``OrchestrationId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...

    def generate_workflow_id(self) -> str:
        """Generate a unique workflow identifier.

        The returned string MUST be globally unique and suitable for
        use as a ``WorkflowId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...

    def generate_step_id(self) -> str:
        """Generate a unique workflow step identifier.

        The returned string MUST be globally unique and suitable for
        use as a ``WorkflowStep`` step_id value.

        Returns
        -------
        A unique identifier string.
        """
        ...
