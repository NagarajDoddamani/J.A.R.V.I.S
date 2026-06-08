from __future__ import annotations

from uuid import uuid4


class UuidV7GeneratorAdapter:
    """Production ID generator using UUID v4 (Python uuid4).

    Note: The production database uses ``platform.uuidv7()`` for
    time-ordered UUIDs. This adapter provides a Python-side UUID
    suitable for testing and non-DB-generated identifiers.
    """

    def generate(self) -> str:
        return str(uuid4())
