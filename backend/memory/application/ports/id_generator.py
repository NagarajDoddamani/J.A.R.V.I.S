from __future__ import annotations

from typing import Protocol

from backend.memory.domain.model import ConsentId, MemoryId


class MemoryIdGeneratorPort(Protocol):
    """Identifier generator for the memory domain.

    Produces unique ``MemoryId`` and ``ConsentId`` values.
    Swappable implementations allow UUID-based generation in
    production or deterministic sequences in tests.
    """

    def generate_memory_id(self) -> MemoryId:
        """Generate a unique memory identifier.

        The returned ``MemoryId`` MUST be globally unique and
        suitable for use as an aggregate identifier.

        Returns
        -------
        A unique ``MemoryId`` value.
        """
        ...

    def generate_consent_id(self) -> ConsentId:
        """Generate a unique consent identifier.

        The returned ``ConsentId`` MUST be globally unique and
        suitable for use as an aggregate identifier.

        Returns
        -------
        A unique ``ConsentId`` value.
        """
        ...
