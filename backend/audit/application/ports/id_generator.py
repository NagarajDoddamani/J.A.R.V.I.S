from __future__ import annotations

from typing import Protocol


class AuditIdGeneratorPort(Protocol):
    """Identifier generator for the audit domain.

    Produces unique identifiers, typically UUID v7 strings.
    Swappable implementations allow database-native generation
    (e.g. PostgreSQL ``gen_random_uuid()``) or deterministic
    sequences in tests.
    """

    def generate(self) -> str:
        """Generate a unique identifier.

        The returned string MUST be globally unique and
        suitable for use as an ``AuditEntryId`` value.

        Returns
        -------
        A unique identifier string (typically a UUID v7).
        """
        ...
