from __future__ import annotations

from typing import Protocol


class ResearchIdGeneratorPort(Protocol):
    """Identifier generator for the research domain.

    Produces unique string identifiers for research requests, jobs,
    and sources. Swappable implementations allow UUID-based
    generation in production or deterministic sequences in tests.
    """

    def generate_request_id(self) -> str:
        """Generate a unique research request identifier.

        The returned string MUST be globally unique and suitable
        for use as a ``ResearchRequestId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...

    def generate_job_id(self) -> str:
        """Generate a unique research job identifier.

        The returned string MUST be globally unique and suitable
        for use as a ``ResearchJobId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...

    def generate_source_id(self) -> str:
        """Generate a unique research source identifier.

        The returned string MUST be globally unique and suitable
        for use as a ``ResearchSource`` source_id value.

        Returns
        -------
        A unique identifier string.
        """
        ...
