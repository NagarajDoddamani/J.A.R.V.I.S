from __future__ import annotations

from datetime import datetime
from typing import Protocol


class KnowledgeClockPort(Protocol):
    """Clock abstraction for the knowledge domain.

    Provides the current UTC time. Swappable implementations allow
    deterministic time in tests (e.g. a ``FrozenClock`` or
    ``OffsetClock``) while the production adapter returns the real
    system clock.
    """

    def now(self) -> datetime:
        """Return the current UTC date and time.

        The returned ``datetime`` MUST be timezone-aware with
        ``tzinfo=timezone.utc``.

        Returns
        -------
        The current instant as a UTC-aware ``datetime``.
        """
        ...
