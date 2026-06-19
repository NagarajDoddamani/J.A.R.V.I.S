from __future__ import annotations

from typing import Protocol


class AgentIdGeneratorPort(Protocol):
    """Identifier generator for the agent domain.

    Produces unique string identifiers for agents, tasks, and
    executions. Swappable implementations allow UUID-based generation
    in production or deterministic sequences in tests.
    """

    def generate_agent_id(self) -> str:
        """Generate a unique agent identifier.

        The returned string MUST be globally unique and suitable for
        use as an ``AgentId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...

    def generate_task_id(self) -> str:
        """Generate a unique task identifier.

        The returned string MUST be globally unique and suitable for
        use as an ``AgentTaskId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...

    def generate_execution_id(self) -> str:
        """Generate a unique execution identifier.

        The returned string MUST be globally unique and suitable for
        use as an ``AgentExecutionId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...
