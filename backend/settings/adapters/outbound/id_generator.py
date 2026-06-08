from __future__ import annotations

from uuid import uuid4


class UuidGeneratorAdapter:
    """Production ID generator using UUID v4."""

    def generate(self) -> str:
        return str(uuid4())
