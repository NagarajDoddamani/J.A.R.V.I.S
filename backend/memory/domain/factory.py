from __future__ import annotations

from datetime import datetime, timezone

from backend.memory.domain.exceptions import MemoryDomainError
from backend.memory.domain.model import (
    ConsentRecord,
    Memory,
    MemoryCategory,
    MemoryContent,
    MemoryCreated,
    MemoryId,
    Provenance,
    RetentionPolicy,
    RetentionStatus,
    RevisionNumber,
)
from backend.memory.domain.rules import validate_memory_creation


class MemoryFactory:
    """Factory for creating validated Memory aggregate instances."""

    @staticmethod
    def create(
        *,
        consent: ConsentRecord,
        content: str,
        category: str | MemoryCategory,
        source_type: str,
        source_id: str | None = None,
        provenance: Provenance | None,
        retention: RetentionPolicy | None,
        classification: str,
        sensitivity: str,
        redaction_metadata: str | None = None,
    ) -> tuple[Memory, MemoryCreated]:
        if isinstance(category, str):
            category = MemoryCategory(category)

        content_vo = MemoryContent(value=content)

        validate_memory_creation(
            content=content_vo,
            consent=consent,
            source_type=source_type,
            provenance=provenance,
            classification=classification,
            sensitivity=sensitivity,
            retention=retention,
            redaction_metadata=redaction_metadata,
        )

        memory = Memory(
            memory_id=MemoryId(),
            consent_id=consent.consent_id,
            content=content_vo,
            category=category,
            source_type=source_type,
            source_id=source_id,
            provenance=provenance,  # type: ignore[arg-type]
            classification=classification,
            sensitivity=sensitivity,
            retention=retention,  # type: ignore[arg-type]
            revision=RevisionNumber(value=1),
            created_at=datetime.now(tz=timezone.utc),
            retention_status=RetentionStatus.ACTIVE,
            redaction_metadata=redaction_metadata,
        )

        event = MemoryCreated(
            memory_id=memory.memory_id,
            consent_id=memory.consent_id,
            category=memory.category,
            source_type=memory.source_type,
            source_id=memory.source_id,
            sensitivity=memory.sensitivity,
            occurred_at=memory.created_at,
        )

        return memory, event
