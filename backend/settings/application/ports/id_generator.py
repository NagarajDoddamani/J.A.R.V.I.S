from __future__ import annotations

from typing import Protocol


class SettingsIdGeneratorPort(Protocol):
    """Identifier generator for the settings domain.

    Produces unique identifiers, typically UUID v7 strings.
    Swappable implementations allow database-native generation
    (e.g. PostgreSQL ``gen_random_uuid()``) or deterministic
    sequences in tests.
    """

    def generate(self) -> str:
        """Generate a unique identifier.

        The returned string MUST be globally unique and suitable
        for use as a ``SettingId`` or outbox message identifier.

        Returns
        -------
        A unique identifier string (typically a UUID v7).
        """
        ...
