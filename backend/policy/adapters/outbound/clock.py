from __future__ import annotations

from datetime import datetime, timezone


class SystemClockAdapter:
    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)
