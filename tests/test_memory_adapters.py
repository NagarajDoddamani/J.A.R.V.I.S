from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.memory.adapters.outbound.clock import SystemClockAdapter
from backend.memory.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.memory.adapters.outbound.mapper import (
    ConsentMapperImpl,
    MemoryMapperImpl,
    MemoryOutboxMapperImpl,
)
from backend.memory.domain.model import (
    ConsentGranted,
    ConsentId,
    ConsentRecord,
    ConsentRevoked,
    ConsentStatus,
    Memory,
    MemoryCategory,
    MemoryContent,
    MemoryCreated,
    MemoryDeleted,
    MemoryId,
    MemoryPurgeScheduled,
    MemoryPurged,
    MemoryRetentionExpired,
    MemoryState,
    MemoryUpdated,
    Provenance,
    RetentionPolicy,
    RetentionStatus,
    RevisionNumber,
)


# ===================================================================
# Clock adapter tests
# ===================================================================


class TestSystemClockAdapter:
    def test_now_returns_utc(self) -> None:
        clock = SystemClockAdapter()
        result = clock.now()
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result).total_seconds() == 0.0

    def test_now_returns_datetime(self) -> None:
        clock = SystemClockAdapter()
        assert isinstance(clock.now(), datetime)


# ===================================================================
# ID generator adapter tests
# ===================================================================


class TestUuidGeneratorAdapter:
    def test_generate_memory_id(self) -> None:
        gen = UuidGeneratorAdapter()
        mid = gen.generate_memory_id()
        assert isinstance(mid, MemoryId)

    def test_generate_consent_id(self) -> None:
        gen = UuidGeneratorAdapter()
        cid = gen.generate_consent_id()
        assert isinstance(cid, ConsentId)

    def test_unique_memory_ids(self) -> None:
        gen = UuidGeneratorAdapter()
        ids = {gen.generate_memory_id() for _ in range(100)}
        assert len(ids) == 100

    def test_unique_consent_ids(self) -> None:
        gen = UuidGeneratorAdapter()
        ids = {gen.generate_consent_id() for _ in range(100)}
        assert len(ids) == 100


# ===================================================================
# MemoryMapperImpl tests
# ===================================================================


class TestMemoryMapperImpl:
    @pytest.fixture
    def mapper(self) -> MemoryMapperImpl:
        return MemoryMapperImpl()

    def test_domain_to_dto(self, mapper: MemoryMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        memory = Memory(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            content=MemoryContent(value="Test content"),
            category=MemoryCategory.INSIGHT,
            source_type="inference",
            source_id="inf-001",
            provenance=Provenance(
                source="inference", timestamp=now, actor_id="jarvis"
            ),
            classification="sensitive",
            sensitivity="sensitive",
            retention=RetentionPolicy(policy="time_bound", ttl_days=30),
            revision=RevisionNumber(value=2),
            created_at=now,
            retention_status=RetentionStatus.ACTIVE,
        )
        dto = mapper.domain_to_dto(memory)
        assert dto.memory_id == str(memory.memory_id)
        assert dto.consent_id == str(memory.consent_id)
        assert dto.content == "Test content"
        assert dto.category == "insight"
        assert dto.source_type == "inference"
        assert dto.source_id == "inf-001"
        assert dto.provenance_actor_id == "jarvis"
        assert dto.provenance_timestamp == now
        assert dto.classification == "sensitive"
        assert dto.sensitivity == "sensitive"
        assert dto.retention_policy == "time_bound"
        assert dto.retention_status == "active"
        assert dto.revision == 2

    def test_dto_to_domain(self, mapper: MemoryMapperImpl) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = mapper.domain_to_dto(
            Memory(
                memory_id=MemoryId(),
                consent_id=ConsentId(),
                content=MemoryContent(value="DTO to domain"),
                category=MemoryCategory.CONVERSATION,
                source_type="conversation",
                source_id="conv-001",
                provenance=Provenance(
                    source="conversation", timestamp=dt, actor_id="alice"
                ),
                classification="internal",
                sensitivity="internal",
                retention=RetentionPolicy(policy="persistent"),
                revision=RevisionNumber(value=1),
                created_at=dt,
            )
        )
        memory = mapper.dto_to_domain(dto)
        assert str(memory.memory_id) == dto.memory_id
        assert memory.content.value == "DTO to domain"
        assert memory.category == MemoryCategory.CONVERSATION
        assert memory.source_id == "conv-001"
        assert memory.provenance.actor_id == "alice"
        assert memory.retention.policy == "persistent"
        assert int(memory.revision) == 1

    def test_roundtrip(self, mapper: MemoryMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = Memory(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            content=MemoryContent(value="Roundtrip"),
            category=MemoryCategory.DOCUMENT,
            source_type="external",
            source_id="doc-99",
            provenance=Provenance(
                source="external", timestamp=now, actor_id="system"
            ),
            classification="restricted",
            sensitivity="restricted",
            retention=RetentionPolicy(policy="ephemeral"),
            revision=RevisionNumber(value=5),
            created_at=now,
            updated_at=now,
            state=MemoryState.UPDATED,
            retention_status=RetentionStatus.ACTIVE,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert str(reconstructed.memory_id) == str(original.memory_id)
        assert reconstructed.content.value == "Roundtrip"
        assert reconstructed.category == MemoryCategory.DOCUMENT
        assert reconstructed.source_type == "external"
        assert reconstructed.classification == "restricted"
        assert reconstructed.retention.policy == "ephemeral"
        assert int(reconstructed.revision) == 5

    def test_null_fields_roundtrip(self, mapper: MemoryMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = Memory(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            content=MemoryContent(value="Nulls"),
            category=MemoryCategory.GENERAL,
            source_type="system",
            source_id=None,
            provenance=Provenance(
                source="system", timestamp=now, actor_id=None
            ),
            classification="public",
            sensitivity="public",
            retention=RetentionPolicy(policy="persistent"),
            revision=RevisionNumber(value=1),
            created_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.source_id is None
        assert reconstructed.provenance.actor_id is None
        assert reconstructed.updated_at is None
        assert reconstructed.deleted_at is None
        assert reconstructed.state == MemoryState.CREATED

    def test_deleted_state_preserved(self, mapper: MemoryMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = Memory(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            content=MemoryContent(value="Delete me"),
            category=MemoryCategory.GENERAL,
            source_type="user_input",
            source_id=None,
            provenance=Provenance(
                source="user_input", timestamp=now, actor_id=None
            ),
            classification="public",
            sensitivity="public",
            retention=RetentionPolicy(policy="persistent"),
            revision=RevisionNumber(value=1),
            created_at=now,
            deleted_at=now,
            state=MemoryState.DELETED,
            retention_status=RetentionStatus.ACTIVE,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.deleted_at is not None
        assert reconstructed.state == MemoryState.DELETED

    def test_time_bound_retention(self, mapper: MemoryMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = Memory(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            content=MemoryContent(value="Time bound"),
            category=MemoryCategory.GENERAL,
            source_type="user_input",
            source_id=None,
            provenance=Provenance(
                source="user_input", timestamp=now, actor_id=None
            ),
            classification="public",
            sensitivity="public",
            retention=RetentionPolicy(policy="time_bound", ttl_days=90),
            revision=RevisionNumber(value=1),
            created_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.retention.policy == "time_bound"

    def test_expired_retention_status(self, mapper: MemoryMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = Memory(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            content=MemoryContent(value="Expired"),
            category=MemoryCategory.GENERAL,
            source_type="user_input",
            source_id=None,
            provenance=Provenance(
                source="user_input", timestamp=now, actor_id=None
            ),
            classification="public",
            sensitivity="public",
            retention=RetentionPolicy(policy="persistent"),
            revision=RevisionNumber(value=1),
            created_at=now,
            retention_status=RetentionStatus.EXPIRED,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.retention_status == RetentionStatus.EXPIRED


# ===================================================================
# ConsentMapperImpl tests
# ===================================================================


class TestConsentMapperImpl:
    @pytest.fixture
    def mapper(self) -> ConsentMapperImpl:
        return ConsentMapperImpl()

    def test_domain_to_dto(self, mapper: ConsentMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        consent = ConsentRecord(
            consent_id=ConsentId(),
            status=ConsentStatus.ACTIVE,
            policy_version="2.1",
            granted_at=now,
            expires_at=None,
        )
        dto = mapper.domain_to_dto(consent)
        assert dto.consent_id == str(consent.consent_id)
        assert dto.status == "active"
        assert dto.policy_version == "2.1"
        assert dto.granted_at == now
        assert dto.expires_at is None
        assert dto.revoked_at is None

    def test_dto_to_domain(self, mapper: ConsentMapperImpl) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = mapper.domain_to_dto(
            ConsentRecord(
                consent_id=ConsentId(),
                status=ConsentStatus.REVOKED,
                policy_version="1.0",
                granted_at=dt,
                revoked_at=dt,
            )
        )
        consent = mapper.dto_to_domain(dto)
        assert str(consent.consent_id) == dto.consent_id
        assert consent.status == ConsentStatus.REVOKED
        assert consent.revoked_at == dt

    def test_roundtrip(self, mapper: ConsentMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = ConsentRecord(
            consent_id=ConsentId(),
            status=ConsentStatus.ACTIVE,
            policy_version="1.5",
            granted_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert str(reconstructed.consent_id) == str(original.consent_id)
        assert reconstructed.status == ConsentStatus.ACTIVE
        assert reconstructed.policy_version == "1.5"
        assert reconstructed.granted_at == now

    def test_null_fields(self, mapper: ConsentMapperImpl) -> None:
        original = ConsentRecord(
            consent_id=ConsentId(),
            status=ConsentStatus.PROPOSED,
            policy_version="1.0",
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.granted_at is None
        assert reconstructed.expires_at is None
        assert reconstructed.revoked_at is None

    def test_revoked_state(self, mapper: ConsentMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = ConsentRecord(
            consent_id=ConsentId(),
            status=ConsentStatus.REVOKED,
            policy_version="1.0",
            revoked_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == ConsentStatus.REVOKED
        assert reconstructed.revoked_at == now

    def test_expiry_preserved(self, mapper: ConsentMapperImpl) -> None:
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        original = ConsentRecord(
            consent_id=ConsentId(),
            status=ConsentStatus.ACTIVE,
            policy_version="1.0",
            granted_at=datetime.now(tz=timezone.utc),
            expires_at=future,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.expires_at == future


# ===================================================================
# MemoryOutboxMapperImpl tests
# ===================================================================


class TestMemoryOutboxMapperImpl:
    @pytest.fixture
    def mapper(self) -> MemoryOutboxMapperImpl:
        return MemoryOutboxMapperImpl()

    def test_memory_created_event_to_dto(self, mapper: MemoryOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        event = MemoryCreated(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            category=MemoryCategory.GENERAL,
            source_type="user_input",
            source_id=None,
            sensitivity="low",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "memory.created"
        assert dto.aggregate_id == str(event.memory_id)
        assert dto.occurred_at == now
        assert dto.published is False
        assert dto.payload is not None

    def test_consent_granted_event_to_dto(self, mapper: MemoryOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        event = ConsentGranted(
            consent_id=ConsentId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "consent.granted"
        assert dto.aggregate_id == str(event.consent_id)

    def test_consent_revoked_event_to_dto(self, mapper: MemoryOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        event = ConsentRevoked(
            consent_id=ConsentId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "consent.revoked"

    def test_memory_updated_event_to_dto(self, mapper: MemoryOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        event = MemoryUpdated(
            memory_id=MemoryId(),
            revision=3,
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "memory.updated"
        assert "revision" in dto.payload  # type: ignore[operator]

    def test_memory_deleted_event_to_dto(self, mapper: MemoryOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        event = MemoryDeleted(
            memory_id=MemoryId(),
            revision=1,
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "memory.deleted"

    def test_all_eight_event_types(self, mapper: MemoryOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        mid = MemoryId()
        cid = ConsentId()
        events = [
            MemoryCreated(mid, cid, MemoryCategory.GENERAL, "ui", None, "low", now),
            MemoryUpdated(mid, 1, now),
            MemoryDeleted(mid, 1, now),
            MemoryRetentionExpired(mid, 1, now),
            MemoryPurgeScheduled(mid, 1, now),
            MemoryPurged(mid, 1, now),
            ConsentGranted(cid, now),
            ConsentRevoked(cid, now),
        ]
        for event in events:
            dto = mapper.event_to_dto(event)
            assert dto.event_id is not None
            assert dto.event_type is not None
            assert dto.aggregate_id is not None

    def test_dto_to_event_memory_created(self, mapper: MemoryOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = MemoryCreated(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            category=MemoryCategory.INSIGHT,
            source_type="inference",
            source_id="inf-001",
            sensitivity="low",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(original)
        event = mapper.dto_to_event(dto)
        assert isinstance(event, MemoryCreated)
        assert str(event.memory_id) == str(original.memory_id)
        assert event.category == MemoryCategory.INSIGHT
        assert event.source_type == "inference"

    def test_dto_to_event_consent_granted(self, mapper: MemoryOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = ConsentGranted(consent_id=ConsentId(), occurred_at=now)
        dto = mapper.event_to_dto(original)
        event = mapper.dto_to_event(dto)
        assert isinstance(event, ConsentGranted)
        assert str(event.consent_id) == str(original.consent_id)

    def test_dto_to_event_consent_revoked(self, mapper: MemoryOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = ConsentRevoked(consent_id=ConsentId(), occurred_at=now)
        dto = mapper.event_to_dto(original)
        event = mapper.dto_to_event(dto)
        assert isinstance(event, ConsentRevoked)

    def test_roundtrip_memory_created(self, mapper: MemoryOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = MemoryCreated(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            category=MemoryCategory.PREFERENCE,
            source_type="user_input",
            source_id="chat-42",
            sensitivity="low",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert type(reconstructed) is type(original)
        assert str(reconstructed.memory_id) == str(original.memory_id)

    def test_roundtrip_memory_updated(self, mapper: MemoryOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = MemoryUpdated(memory_id=MemoryId(), revision=7, occurred_at=now)
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, MemoryUpdated)
        assert reconstructed.revision == 7

    def test_roundtrip_consent_granted(self, mapper: MemoryOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = ConsentGranted(consent_id=ConsentId(), occurred_at=now)
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, ConsentGranted)
        assert str(reconstructed.consent_id) == str(original.consent_id)

    def test_unknown_event_type_raises(self, mapper: MemoryOutboxMapperImpl) -> None:
        from backend.memory.adapters.outbound.mapper import _EVENT_TYPE_REVERSE
        from backend.memory.application.persistence.dto import (
            MemoryOutboxStorageDTO,
        )
        dto = MemoryOutboxStorageDTO(
            event_id="id-1",
            event_type="nonexistent.type",
            aggregate_id="agg-1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(ValueError, match="Unknown event_type"):
            mapper.dto_to_event(dto)
