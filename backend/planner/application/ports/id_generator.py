from __future__ import annotations

from typing import Protocol


class PlannerIdGeneratorPort(Protocol):
    """Identifier generator for the planner domain.

    Produces unique string identifiers for plans, tasks, and
    execution steps. Swappable implementations allow UUID-based
    generation in production or deterministic sequences in tests.
    """

    def generate_plan_id(self) -> str:
        """Generate a unique plan identifier.

        The returned string MUST be globally unique and suitable
        for use as a ``PlanId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...

    def generate_task_id(self) -> str:
        """Generate a unique task identifier.

        The returned string MUST be globally unique and suitable
        for use as a ``TaskId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...

    def generate_step_id(self) -> str:
        """Generate a unique execution step identifier.

        The returned string MUST be globally unique and suitable
        for use as an ``ExecutionStepId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...
