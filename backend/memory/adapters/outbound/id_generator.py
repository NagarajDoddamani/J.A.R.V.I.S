from __future__ import annotations

from uuid import uuid4

from backend.memory.domain.model import ConsentId, MemoryId


class UuidGeneratorAdapter:
    """Production ID generator using UUID v4.

    Conforms to ``MemoryIdGeneratorPort`` by providing
    ``generate_memory_id`` and ``generate_consent_id`` methods.
    """

    def generate_memory_id(self) -> MemoryId:
        return MemoryId()

    def generate_consent_id(self) -> ConsentId:
        return ConsentId()
