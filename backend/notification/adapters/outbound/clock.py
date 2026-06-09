from __future__ import annotations

from datetime import datetime, timezone


class SystemClockAdapter:
    """Production clock adapter returning the real system UTC time."""

    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)
