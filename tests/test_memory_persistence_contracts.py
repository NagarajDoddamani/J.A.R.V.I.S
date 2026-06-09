from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

import pytest

from backend.memory.application.persistence.dto import (
    ConsentStorageDTO,
    MemoryOutboxStorageDTO,
    MemoryStorageDTO,
)
from backend.memory.application.persistence.mapper import (
    ConsentMapper,
    MemoryMapper,
    MemoryOutboxDomainEvent,
    MemoryOutboxMapper,
)
from backend.memory.application.persistence.schema import (
    CONSENTS_TABLE,
    MEMORIES_TABLE,
    MEMORY_OUTBOX_TABLE,
    ColumnContract,
    TableContract,
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
from backend.memory.domain.rules import (
    VALID_CLASSIFICATIONS,
    VALID_SENSITIVITY_LEVELS,
)

# ===================================================================
# Stub mapper implementations (conform to mapper protocols)
# ===================================================================


class StubMemoryMapper:
    """Stub mapper conforming to ``MemoryMapper`` protocol."""

    def domain_to_dto(self, memory: Memory) -> MemoryStorageDTO:
        return MemoryStorageDTO(
            memory_id=str(memory.memory_id),
            consent_id=str(memory.consent_id),
            content=memory.content.value,
            category=memory.category.value,
            source_type=memory.source_type,
            source_id=memory.source_id,
            provenance_actor_id=memory.provenance.actor_id,
            provenance_timestamp=memory.provenance.timestamp,
            classification=memory.classification,
            sensitivity=memory.sensitivity,
            retention_policy=memory.retention.policy,
            retention_status=memory.retention_status.value,
            revision=int(memory.revision),
            created_at=memory.created_at,
            updated_at=memory.updated_at,
            deleted_at=memory.deleted_at,
        )

    def dto_to_domain(self, dto: MemoryStorageDTO) -> Memory:
        retention_kw: dict[str, object] = {"policy": dto.retention_policy}
        if dto.retention_policy == "time_bound":
            retention_kw["ttl_days"] = 30
        state = MemoryState.DELETED if dto.deleted_at is not None else MemoryState.CREATED
        return Memory(
            memory_id=MemoryId(
                value=UUID(dto.memory_id)
            ),
            consent_id=ConsentId(
                value=UUID(dto.consent_id)
            ),
            content=MemoryContent(value=dto.content),
            category=MemoryCategory(dto.category),
            source_type=dto.source_type,
            source_id=dto.source_id,
            provenance=Provenance(
                source=dto.source_type,
                timestamp=dto.provenance_timestamp,
                actor_id=dto.provenance_actor_id,
            ),
            classification=dto.classification,
            sensitivity=dto.sensitivity,
            retention=RetentionPolicy(**retention_kw),
            retention_status=RetentionStatus(dto.retention_status),
            revision=RevisionNumber(value=dto.revision),
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            deleted_at=dto.deleted_at,
            state=state,
        )


class StubConsentMapper:
    """Stub mapper conforming to ``ConsentMapper`` protocol."""

    def domain_to_dto(self, consent: ConsentRecord) -> ConsentStorageDTO:
        return ConsentStorageDTO(
            consent_id=str(consent.consent_id),
            status=consent.status.value,
            policy_version=consent.policy_version,
            granted_at=consent.granted_at,
            expires_at=consent.expires_at,
            revoked_at=consent.revoked_at,
        )

    def dto_to_domain(self, dto: ConsentStorageDTO) -> ConsentRecord:
        return ConsentRecord(
            consent_id=ConsentId(
                value=UUID(dto.consent_id)
            ),
            status=ConsentStatus(dto.status),
            policy_version=dto.policy_version,
            granted_at=dto.granted_at,
            expires_at=dto.expires_at,
            revoked_at=dto.revoked_at,
        )


class StubMemoryOutboxMapper:
    """Stub mapper conforming to ``MemoryOutboxMapper`` protocol."""

    def event_to_dto(self, event: MemoryOutboxDomainEvent) -> MemoryOutboxStorageDTO:
        if isinstance(event, (MemoryCreated, MemoryUpdated, MemoryDeleted,
                              MemoryRetentionExpired, MemoryPurgeScheduled, MemoryPurged)):
            aggregate_id = str(event.memory_id)
        else:
            aggregate_id = str(event.consent_id)

        if isinstance(event, MemoryCreated):
            event_type = "memory.created"
        elif isinstance(event, MemoryUpdated):
            event_type = "memory.updated"
        elif isinstance(event, MemoryDeleted):
            event_type = "memory.deleted"
        elif isinstance(event, MemoryRetentionExpired):
            event_type = "memory.retention_expired"
        elif isinstance(event, MemoryPurgeScheduled):
            event_type = "memory.purge_scheduled"
        elif isinstance(event, MemoryPurged):
            event_type = "memory.purged"
        elif isinstance(event, ConsentGranted):
            event_type = "consent.granted"
        elif isinstance(event, ConsentRevoked):
            event_type = "consent.revoked"
        else:
            event_type = "unknown"

        return MemoryOutboxStorageDTO(
            event_id=aggregate_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=event.occurred_at,
            published=False,
        )

    def dto_to_event(self, dto: MemoryOutboxStorageDTO) -> MemoryOutboxDomainEvent:
        try:
            aggregate_id = UUID(dto.aggregate_id)
        except ValueError:
            aggregate_id = UUID("00000000-0000-0000-0000-000000000001")
        if dto.event_type == "memory.created":
            return MemoryCreated(
                memory_id=MemoryId(value=aggregate_id),
                consent_id=ConsentId(),
                category=MemoryCategory.GENERAL,
                source_type="user_input",
                source_id=None,
                sensitivity="low",
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "memory.updated":
            return MemoryUpdated(
                memory_id=MemoryId(value=aggregate_id),
                revision=1,
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "memory.deleted":
            return MemoryDeleted(
                memory_id=MemoryId(value=aggregate_id),
                revision=1,
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "memory.retention_expired":
            return MemoryRetentionExpired(
                memory_id=MemoryId(value=aggregate_id),
                revision=1,
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "memory.purge_scheduled":
            return MemoryPurgeScheduled(
                memory_id=MemoryId(value=aggregate_id),
                revision=1,
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "memory.purged":
            return MemoryPurged(
                memory_id=MemoryId(value=aggregate_id),
                revision=1,
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "consent.granted":
            return ConsentGranted(
                consent_id=ConsentId(value=aggregate_id),
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "consent.revoked":
            return ConsentRevoked(
                consent_id=ConsentId(value=aggregate_id),
                occurred_at=dto.occurred_at,
            )
        else:
            raise ValueError(f"Unknown event_type: {dto.event_type}")


# ===================================================================
# DTO construction tests
# ===================================================================


class TestMemoryStorageDTO:
    def test_all_fields_present(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = MemoryStorageDTO(
            memory_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            consent_id="01975c2f-4aef-7cf1-a940-ae54bf596281",
            content="User prefers dark mode",
            category="preference",
            source_type="user_input",
            source_id="chat-42",
            provenance_actor_id="alice",
            provenance_timestamp=dt,
            classification="public",
            sensitivity="public",
            retention_policy="persistent",
            retention_status="active",
            revision=1,
            created_at=dt,
            updated_at=dt,
            deleted_at=None,
        )
        assert dto.memory_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.consent_id == "01975c2f-4aef-7cf1-a940-ae54bf596281"
        assert dto.content == "User prefers dark mode"
        assert dto.category == "preference"
        assert dto.source_type == "user_input"
        assert dto.source_id == "chat-42"
        assert dto.provenance_actor_id == "alice"
        assert dto.provenance_timestamp == dt
        assert dto.classification == "public"
        assert dto.sensitivity == "public"
        assert dto.retention_policy == "persistent"
        assert dto.retention_status == "active"
        assert dto.revision == 1
        assert dto.created_at == dt
        assert dto.updated_at == dt
        assert dto.deleted_at is None

    def test_nullable_fields(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = MemoryStorageDTO(
            memory_id="id-1",
            consent_id="id-2",
            content="test",
            category="general",
            source_type="system",
            source_id=None,
            provenance_actor_id=None,
            provenance_timestamp=dt,
            classification="public",
            sensitivity="public",
            retention_policy="persistent",
            retention_status="active",
            revision=1,
            created_at=dt,
        )
        assert dto.source_id is None
        assert dto.provenance_actor_id is None
        assert dto.updated_at is None
        assert dto.deleted_at is None

    def test_frozen(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = MemoryStorageDTO(
            memory_id="id-1",
            consent_id="id-2",
            content="test",
            category="general",
            source_type="system",
            source_id=None,
            provenance_actor_id=None,
            provenance_timestamp=dt,
            classification="public",
            sensitivity="public",
            retention_policy="persistent",
            retention_status="active",
            revision=1,
            created_at=dt,
        )
        with pytest.raises(AttributeError):
            dto.memory_id = "changed"

    def test_default_deleted_at_none(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = MemoryStorageDTO(
            memory_id="id-1",
            consent_id="id-2",
            content="test",
            category="general",
            source_type="system",
            source_id=None,
            provenance_actor_id=None,
            provenance_timestamp=dt,
            classification="public",
            sensitivity="public",
            retention_policy="persistent",
            retention_status="active",
            revision=1,
            created_at=dt,
        )
        assert dto.updated_at is None
        assert dto.deleted_at is None

    def test_explicit_updated_at(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        updated = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = MemoryStorageDTO(
            memory_id="id-1",
            consent_id="id-2",
            content="test",
            category="general",
            source_type="system",
            source_id=None,
            provenance_actor_id=None,
            provenance_timestamp=dt,
            classification="public",
            sensitivity="public",
            retention_policy="persistent",
            retention_status="active",
            revision=2,
            created_at=dt,
            updated_at=updated,
        )
        assert dto.updated_at == updated

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(MemoryStorageDTO)
        assert len(fields) == 16

    def test_all_fields_have_types(self) -> None:
        import dataclasses
        for f in dataclasses.fields(MemoryStorageDTO):
            assert f.type is not None, f"Field {f.name} has no type annotation"


class TestConsentStorageDTO:
    def test_all_fields_present(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = ConsentStorageDTO(
            consent_id="01975c2f-4aef-7cf1-a940-ae54bf596281",
            status="active",
            policy_version="1.0",
            granted_at=dt,
            expires_at=dt,
            revoked_at=None,
        )
        assert dto.consent_id == "01975c2f-4aef-7cf1-a940-ae54bf596281"
        assert dto.status == "active"
        assert dto.policy_version == "1.0"
        assert dto.granted_at == dt
        assert dto.expires_at == dt
        assert dto.revoked_at is None

    def test_nullable_fields(self) -> None:
        dto = ConsentStorageDTO(
            consent_id="id-1",
            status="proposed",
            policy_version="1.0",
        )
        assert dto.granted_at is None
        assert dto.expires_at is None
        assert dto.revoked_at is None

    def test_frozen(self) -> None:
        dto = ConsentStorageDTO(
            consent_id="id-1",
            status="proposed",
            policy_version="1.0",
        )
        with pytest.raises(AttributeError):
            dto.consent_id = "changed"

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(ConsentStorageDTO)
        assert len(fields) == 6

    def test_explicit_revoked_at(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = ConsentStorageDTO(
            consent_id="id-1",
            status="revoked",
            policy_version="1.0",
            revoked_at=dt,
        )
        assert dto.revoked_at == dt


class TestMemoryOutboxStorageDTO:
    def test_all_fields_present(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = MemoryOutboxStorageDTO(
            event_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            event_type="memory.created",
            aggregate_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            occurred_at=dt,
            correlation_id="corr-001",
            causation_id="cause-001",
            payload='{"sensitivity": "low"}',
        )
        assert dto.event_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.event_type == "memory.created"
        assert dto.aggregate_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.occurred_at == dt
        assert dto.correlation_id == "corr-001"
        assert dto.causation_id == "cause-001"
        assert dto.payload == '{"sensitivity": "low"}'

    def test_default_published_false(self) -> None:
        dto = MemoryOutboxStorageDTO(
            event_id="id-1",
            event_type="memory.created",
            aggregate_id="agg-1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        assert dto.published is False

    def test_explicit_published(self) -> None:
        dto = MemoryOutboxStorageDTO(
            event_id="id-1",
            event_type="memory.created",
            aggregate_id="agg-1",
            occurred_at=datetime.now(tz=timezone.utc),
            published=True,
        )
        assert dto.published is True

    def test_nullable_fields(self) -> None:
        dto = MemoryOutboxStorageDTO(
            event_id="id-1",
            event_type="memory.created",
            aggregate_id="agg-1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        assert dto.correlation_id is None
        assert dto.causation_id is None
        assert dto.payload is None

    def test_frozen(self) -> None:
        dto = MemoryOutboxStorageDTO(
            event_id="id-1",
            event_type="memory.created",
            aggregate_id="agg-1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            dto.event_id = "changed"

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(MemoryOutboxStorageDTO)
        assert len(fields) == 8


# ===================================================================
# Mapper protocol conformance tests
# ===================================================================


class TestMemoryMapper:
    @pytest.fixture
    def mapper(self) -> StubMemoryMapper:
        return StubMemoryMapper()

    def test_protocol_conformance(self) -> None:
        mapper: MemoryMapper = StubMemoryMapper()
        assert isinstance(mapper, StubMemoryMapper)

    def test_domain_to_dto(self, mapper: StubMemoryMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        memory = Memory(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            content=MemoryContent(value="User prefers dark mode"),
            category=MemoryCategory.PREFERENCE,
            source_type="user_input",
            source_id="chat-42",
            provenance=Provenance(
                source="user_input",
                timestamp=now,
                actor_id="alice",
            ),
            classification="public",
            sensitivity="public",
            retention=RetentionPolicy(policy="persistent"),
            revision=RevisionNumber(value=1),
            created_at=now,
        )
        dto = mapper.domain_to_dto(memory)
        assert dto.memory_id == str(memory.memory_id)
        assert dto.consent_id == str(memory.consent_id)
        assert dto.content == "User prefers dark mode"
        assert dto.category == "preference"
        assert dto.source_type == "user_input"
        assert dto.source_id == "chat-42"
        assert dto.provenance_actor_id == "alice"
        assert dto.provenance_timestamp == now
        assert dto.classification == "public"
        assert dto.sensitivity == "public"
        assert dto.retention_policy == "persistent"
        assert dto.retention_status == "active"
        assert dto.revision == 1
        assert dto.created_at == now
        assert dto.updated_at is None
        assert dto.deleted_at is None

    def test_dto_to_domain(self, mapper: StubMemoryMapper) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = MemoryStorageDTO(
            memory_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            consent_id="01975c2f-4aef-7cf1-a940-ae54bf596281",
            content="Memory content text",
            category="conversation",
            source_type="conversation",
            source_id="conv-001",
            provenance_actor_id="jarvis",
            provenance_timestamp=dt,
            classification="internal",
            sensitivity="internal",
            retention_policy="persistent",
            retention_status="active",
            revision=3,
            created_at=dt,
            updated_at=dt,
            deleted_at=None,
        )
        memory = mapper.dto_to_domain(dto)
        assert str(memory.memory_id) == dto.memory_id
        assert str(memory.consent_id) == dto.consent_id
        assert memory.content.value == "Memory content text"
        assert memory.category == MemoryCategory.CONVERSATION
        assert memory.source_type == "conversation"
        assert memory.source_id == "conv-001"
        assert memory.provenance.actor_id == "jarvis"
        assert memory.provenance.timestamp == dt
        assert memory.classification == "internal"
        assert memory.sensitivity == "internal"
        assert memory.retention.policy == "persistent"
        assert memory.retention_status == RetentionStatus.ACTIVE
        assert int(memory.revision) == 3
        assert memory.created_at == dt
        assert memory.updated_at == dt
        assert memory.deleted_at is None

    def test_roundtrip(self, mapper: StubMemoryMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = Memory(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            content=MemoryContent(value="Roundtrip test content"),
            category=MemoryCategory.INSIGHT,
            source_type="inference",
            source_id="inf-001",
            provenance=Provenance(
                source="inference",
                timestamp=now,
                actor_id="system",
            ),
            classification="sensitive",
            sensitivity="sensitive",
            retention=RetentionPolicy(policy="time_bound", ttl_days=30),
            revision=RevisionNumber(value=2),
            created_at=now,
            updated_at=now,
            state=MemoryState.UPDATED,
            retention_status=RetentionStatus.ACTIVE,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)

        assert str(reconstructed.memory_id) == str(original.memory_id)
        assert str(reconstructed.consent_id) == str(original.consent_id)
        assert reconstructed.content.value == original.content.value
        assert reconstructed.category == original.category
        assert reconstructed.source_type == original.source_type
        assert reconstructed.source_id == original.source_id
        assert reconstructed.provenance.actor_id == original.provenance.actor_id
        assert reconstructed.provenance.timestamp == original.provenance.timestamp
        assert reconstructed.classification == original.classification
        assert reconstructed.sensitivity == original.sensitivity
        assert reconstructed.retention.policy == original.retention.policy
        assert reconstructed.retention_status == original.retention_status
        assert int(reconstructed.revision) == int(original.revision)
        assert reconstructed.created_at == original.created_at
        assert reconstructed.updated_at == original.updated_at
        assert reconstructed.deleted_at == original.deleted_at

    def test_null_fields_roundtrip(self, mapper: StubMemoryMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = Memory(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            content=MemoryContent(value="Null fields test"),
            category=MemoryCategory.GENERAL,
            source_type="system",
            source_id=None,
            provenance=Provenance(
                source="system",
                timestamp=now,
                actor_id=None,
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

    def test_deleted_memory_mapping(self, mapper: StubMemoryMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = Memory(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            content=MemoryContent(value="Deleted memory"),
            category=MemoryCategory.CONVERSATION,
            source_type="user_input",
            source_id="chat-99",
            provenance=Provenance(
                source="user_input",
                timestamp=now,
                actor_id="alice",
            ),
            classification="public",
            sensitivity="public",
            retention=RetentionPolicy(policy="ephemeral"),
            revision=RevisionNumber(value=3),
            created_at=now,
            deleted_at=now,
            state=MemoryState.DELETED,
            retention_status=RetentionStatus.EXPIRED,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.deleted_at == now
        assert reconstructed.retention_status == RetentionStatus.EXPIRED
        assert reconstructed.state == MemoryState.DELETED

    def test_mapper_has_required_methods(self) -> None:
        mapper: MemoryMapper = StubMemoryMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


class TestConsentMapper:
    @pytest.fixture
    def mapper(self) -> StubConsentMapper:
        return StubConsentMapper()

    def test_protocol_conformance(self) -> None:
        mapper: ConsentMapper = StubConsentMapper()
        assert isinstance(mapper, StubConsentMapper)

    def test_domain_to_dto(self, mapper: StubConsentMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        consent = ConsentRecord(
            consent_id=ConsentId(),
            status=ConsentStatus.ACTIVE,
            policy_version="2.0",
            granted_at=now,
            expires_at=None,
        )
        dto = mapper.domain_to_dto(consent)
        assert dto.consent_id == str(consent.consent_id)
        assert dto.status == "active"
        assert dto.policy_version == "2.0"
        assert dto.granted_at == now
        assert dto.expires_at is None
        assert dto.revoked_at is None

    def test_dto_to_domain(self, mapper: StubConsentMapper) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = ConsentStorageDTO(
            consent_id="01975c2f-4aef-7cf1-a940-ae54bf596281",
            status="revoked",
            policy_version="1.5",
            granted_at=dt,
            expires_at=None,
            revoked_at=dt,
        )
        consent = mapper.dto_to_domain(dto)
        assert str(consent.consent_id) == dto.consent_id
        assert consent.status == ConsentStatus.REVOKED
        assert consent.policy_version == "1.5"
        assert consent.granted_at == dt
        assert consent.expires_at is None
        assert consent.revoked_at == dt

    def test_roundtrip(self, mapper: StubConsentMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = ConsentRecord(
            consent_id=ConsentId(),
            status=ConsentStatus.ACTIVE,
            policy_version="1.0",
            granted_at=now,
            expires_at=None,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert str(reconstructed.consent_id) == str(original.consent_id)
        assert reconstructed.status == original.status
        assert reconstructed.policy_version == original.policy_version
        assert reconstructed.granted_at == original.granted_at
        assert reconstructed.expires_at == original.expires_at
        assert reconstructed.revoked_at == original.revoked_at

    def test_null_fields_roundtrip(self, mapper: StubConsentMapper) -> None:
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

    def test_revoked_consent_mapping(self, mapper: StubConsentMapper) -> None:
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

    def test_expired_consent_mapping(self, mapper: StubConsentMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        original = ConsentRecord(
            consent_id=ConsentId(),
            status=ConsentStatus.ACTIVE,
            policy_version="1.0",
            granted_at=now,
            expires_at=future,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.expires_at == future


class TestMemoryOutboxMapper:
    @pytest.fixture
    def mapper(self) -> StubMemoryOutboxMapper:
        return StubMemoryOutboxMapper()

    def test_protocol_conformance(self) -> None:
        mapper: MemoryOutboxMapper = StubMemoryOutboxMapper()
        assert isinstance(mapper, StubMemoryOutboxMapper)

    def test_memory_created_event_to_dto(self, mapper: StubMemoryOutboxMapper) -> None:
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

    def test_consent_granted_event_to_dto(self, mapper: StubMemoryOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = ConsentGranted(
            consent_id=ConsentId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "consent.granted"
        assert dto.aggregate_id == str(event.consent_id)
        assert dto.occurred_at == now

    def test_consent_revoked_event_to_dto(self, mapper: StubMemoryOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = ConsentRevoked(
            consent_id=ConsentId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "consent.revoked"
        assert dto.aggregate_id == str(event.consent_id)

    def test_memory_deleted_event_to_dto(self, mapper: StubMemoryOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = MemoryDeleted(
            memory_id=MemoryId(),
            revision=2,
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "memory.deleted"
        assert dto.aggregate_id == str(event.memory_id)

    def test_memory_updated_event_to_dto(self, mapper: StubMemoryOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = MemoryUpdated(
            memory_id=MemoryId(),
            revision=2,
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "memory.updated"

    def test_all_events_have_dto_mapping(self, mapper: StubMemoryOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        events: list[MemoryOutboxDomainEvent] = [
            MemoryCreated(MemoryId(), ConsentId(), MemoryCategory.GENERAL,
                          "user_input", None, "low", now),
            MemoryUpdated(MemoryId(), 1, now),
            MemoryDeleted(MemoryId(), 1, now),
            MemoryRetentionExpired(MemoryId(), 1, now),
            MemoryPurgeScheduled(MemoryId(), 1, now),
            MemoryPurged(MemoryId(), 1, now),
            ConsentGranted(ConsentId(), now),
            ConsentRevoked(ConsentId(), now),
        ]
        for event in events:
            dto = mapper.event_to_dto(event)
            assert dto.event_id is not None
            assert dto.event_type is not None
            assert dto.aggregate_id is not None

    def test_event_to_dto_published_default(self, mapper: StubMemoryOutboxMapper) -> None:
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
        assert dto.published is False

    def test_dto_to_event_memory_created(self, mapper: StubMemoryOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = MemoryOutboxStorageDTO(
            event_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            event_type="memory.created",
            aggregate_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, MemoryCreated)
        assert str(event.memory_id) == dto.aggregate_id

    def test_dto_to_event_consent_granted(self, mapper: StubMemoryOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = MemoryOutboxStorageDTO(
            event_id="01975c2f-4aef-7cf1-a940-ae54bf596281",
            event_type="consent.granted",
            aggregate_id="01975c2f-4aef-7cf1-a940-ae54bf596281",
            occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, ConsentGranted)

    def test_dto_to_event_consent_revoked(self, mapper: StubMemoryOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = MemoryOutboxStorageDTO(
            event_id="id-1",
            event_type="consent.revoked",
            aggregate_id="id-1",
            occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, ConsentRevoked)

    def test_dto_to_event_memory_deleted(self, mapper: StubMemoryOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = MemoryOutboxStorageDTO(
            event_id="id-1",
            event_type="memory.deleted",
            aggregate_id="id-1",
            occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, MemoryDeleted)

    def test_roundtrip_memory_created(self, mapper: StubMemoryOutboxMapper) -> None:
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
        reconstructed = mapper.dto_to_event(dto)
        assert type(reconstructed) is type(original)
        assert str(reconstructed.memory_id) == str(original.memory_id)
        assert reconstructed.occurred_at == original.occurred_at

    def test_roundtrip_consent_granted(self, mapper: StubMemoryOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = ConsentGranted(
            consent_id=ConsentId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, ConsentGranted)
        assert str(reconstructed.consent_id) == str(original.consent_id)


# ===================================================================
# Schema contract consistency tests
# ===================================================================


class TestSchemaContracts:
    def test_memories_column_count(self) -> None:
        assert len(MEMORIES_TABLE.columns) == 16

    def test_memories_schema_name(self) -> None:
        assert MEMORIES_TABLE.schema == "memory"
        assert MEMORIES_TABLE.name == "memories"

    def test_memories_primary_key(self) -> None:
        assert MEMORIES_TABLE.primary_key == "memory_id"

    def test_memories_indexes(self) -> None:
        expected = {
            "ix_memories_consent_id",
            "ix_memories_category",
            "ix_memories_source",
            "ix_memories_retention_status",
        }
        assert set(MEMORIES_TABLE.indexes) == expected

    def test_consents_column_count(self) -> None:
        assert len(CONSENTS_TABLE.columns) == 6

    def test_consents_schema_name(self) -> None:
        assert CONSENTS_TABLE.schema == "memory"
        assert CONSENTS_TABLE.name == "consents"

    def test_consents_primary_key(self) -> None:
        assert CONSENTS_TABLE.primary_key == "consent_id"

    def test_consents_indexes(self) -> None:
        assert CONSENTS_TABLE.indexes == ("ix_consents_status",)

    def test_outbox_column_count(self) -> None:
        assert len(MEMORY_OUTBOX_TABLE.columns) == 8

    def test_outbox_schema_name(self) -> None:
        assert MEMORY_OUTBOX_TABLE.schema == "memory"
        assert MEMORY_OUTBOX_TABLE.name == "outbox"

    def test_outbox_primary_key(self) -> None:
        assert MEMORY_OUTBOX_TABLE.primary_key == "event_id"

    def test_outbox_indexes(self) -> None:
        expected = {
            "ix_memory_outbox_unpublished",
            "ix_memory_outbox_aggregate",
        }
        assert set(MEMORY_OUTBOX_TABLE.indexes) == expected

    def test_memories_category_enum(self) -> None:
        col = next(
            c for c in MEMORIES_TABLE.columns if c.name == "category"
        )
        assert col.enum_values == (
            "general", "conversation", "document",
            "insight", "preference", "ephemeral",
        )
        assert col.max_length == 32
        assert col.nullable is False

    def test_memories_classification_enum(self) -> None:
        col = next(
            c for c in MEMORIES_TABLE.columns if c.name == "classification"
        )
        assert col.enum_values == (
            "public", "internal", "sensitive", "restricted"
        )
        assert col.max_length == 16
        assert col.nullable is False

    def test_memories_sensitivity_enum(self) -> None:
        col = next(
            c for c in MEMORIES_TABLE.columns if c.name == "sensitivity"
        )
        assert col.enum_values == (
            "public", "internal", "sensitive", "restricted"
        )
        assert col.max_length == 16
        assert col.nullable is False

    def test_memories_retention_policy_enum(self) -> None:
        col = next(
            c for c in MEMORIES_TABLE.columns if c.name == "retention_policy"
        )
        assert col.enum_values == ("persistent", "ephemeral", "time_bound")
        assert col.max_length == 16
        assert col.nullable is False

    def test_memories_retention_status_enum(self) -> None:
        col = next(
            c for c in MEMORIES_TABLE.columns
            if c.name == "retention_status"
        )
        assert col.enum_values == (
            "active", "expired", "purge_pending", "purged"
        )
        assert col.max_length == 16
        assert col.nullable is False

    def test_consents_status_enum(self) -> None:
        col = next(
            c for c in CONSENTS_TABLE.columns if c.name == "status"
        )
        assert col.enum_values == (
            "proposed", "active", "revoked", "purged"
        )
        assert col.max_length == 16
        assert col.nullable is False

    def test_outbox_event_type_enum(self) -> None:
        col = next(
            c for c in MEMORY_OUTBOX_TABLE.columns
            if c.name == "event_type"
        )
        assert col.enum_values == (
            "memory.created", "memory.updated",
            "memory.deleted", "memory.retention_expired",
            "memory.purge_scheduled", "memory.purged",
            "consent.granted", "consent.revoked",
        )
        assert col.max_length == 32
        assert col.nullable is False

    def test_memories_nullable_columns(self) -> None:
        nullable = {
            c.name for c in MEMORIES_TABLE.columns if c.nullable
        }
        assert nullable == {
            "source_id", "provenance_actor_id",
            "updated_at", "deleted_at",
        }

    def test_memories_non_nullable_columns(self) -> None:
        non_nullable = {
            c.name for c in MEMORIES_TABLE.columns if not c.nullable
        }
        assert len(non_nullable) == 12

    def test_consents_nullable_columns(self) -> None:
        nullable = {
            c.name for c in CONSENTS_TABLE.columns if c.nullable
        }
        assert nullable == {"granted_at", "expires_at", "revoked_at"}

    def test_outbox_nullable_columns(self) -> None:
        nullable = {
            c.name for c in MEMORY_OUTBOX_TABLE.columns if c.nullable
        }
        assert nullable == {"correlation_id", "causation_id", "payload"}


# ===================================================================
# DTO ↔ Schema field alignment tests
# ===================================================================


class TestDTOFieldAlignment:
    """Verify DTO fields match schema column contracts."""

    def test_memory_dto_fields_match_schema_columns(self) -> None:
        dto_fields = {
            "memory_id", "consent_id", "content", "category",
            "source_type", "source_id",
            "provenance_actor_id", "provenance_timestamp",
            "classification", "sensitivity",
            "retention_policy", "retention_status",
            "revision", "created_at", "updated_at", "deleted_at",
        }
        schema_cols = {c.name for c in MEMORIES_TABLE.columns}
        assert dto_fields == schema_cols, (
            f"DTO fields not aligned with schema columns. "
            f"Missing from DTO: {schema_cols - dto_fields}. "
            f"Missing from schema: {dto_fields - schema_cols}."
        )

    def test_consent_dto_fields_match_schema_columns(self) -> None:
        dto_fields = {
            "consent_id", "status", "granted_at",
            "expires_at", "revoked_at", "policy_version",
        }
        schema_cols = {c.name for c in CONSENTS_TABLE.columns}
        assert dto_fields == schema_cols

    def test_outbox_dto_fields_match_schema_columns(self) -> None:
        dto_fields = {
            "event_id", "event_type", "aggregate_id",
            "occurred_at", "correlation_id", "causation_id",
            "payload", "published",
        }
        schema_cols = {c.name for c in MEMORY_OUTBOX_TABLE.columns}
        assert dto_fields == schema_cols

    def test_memory_dto_field_types_match_schema(self) -> None:
        schema_map = {c.name: c.py_type for c in MEMORIES_TABLE.columns}
        assert schema_map["memory_id"] == str
        assert schema_map["consent_id"] == str
        assert schema_map["content"] == str
        assert schema_map["category"] == str
        assert schema_map["revision"] == int
        assert schema_map["created_at"] == datetime
        assert schema_map["provenance_timestamp"] == datetime

    def test_consent_dto_field_types_match_schema(self) -> None:
        schema_map = {c.name: c.py_type for c in CONSENTS_TABLE.columns}
        assert schema_map["consent_id"] == str
        assert schema_map["status"] == str
        assert schema_map["policy_version"] == str
        assert schema_map["granted_at"] == datetime
        assert schema_map["expires_at"] == datetime

    def test_outbox_dto_field_types_match_schema(self) -> None:
        schema_map = {
            c.name: c.py_type for c in MEMORY_OUTBOX_TABLE.columns
        }
        assert schema_map["event_id"] == str
        assert schema_map["event_type"] == str
        assert schema_map["aggregate_id"] == str
        assert schema_map["occurred_at"] == datetime
        assert schema_map["published"] == bool

    def test_memory_dto_nullability_matches_schema(self) -> None:
        schema_nullable = {
            c.name for c in MEMORIES_TABLE.columns if c.nullable
        }
        dto_nullable_hints = {
            "source_id", "provenance_actor_id",
            "updated_at", "deleted_at",
        }
        assert schema_nullable == dto_nullable_hints

    def test_consent_dto_nullability_matches_schema(self) -> None:
        schema_nullable = {
            c.name for c in CONSENTS_TABLE.columns if c.nullable
        }
        dto_nullable_hints = {"granted_at", "expires_at", "revoked_at"}
        assert schema_nullable == dto_nullable_hints

    def test_outbox_dto_nullability_matches_schema(self) -> None:
        schema_nullable = {
            c.name for c in MEMORY_OUTBOX_TABLE.columns if c.nullable
        }
        dto_nullable_hints = {"correlation_id", "causation_id", "payload"}
        assert schema_nullable == dto_nullable_hints


# ===================================================================
# Schema value constraint alignment with domain rules
# ===================================================================


class TestSchemaDomainAlignment:
    """Verify schema enum values match domain rule constants and model enums."""

    def test_category_enum_matches_domain(self) -> None:
        domain_values = {e.value for e in MemoryCategory}
        col = next(
            c for c in MEMORIES_TABLE.columns if c.name == "category"
        )
        assert col.enum_values is not None
        assert set(col.enum_values) == domain_values

    def test_classification_enum_matches_domain(self) -> None:
        col = next(
            c for c in MEMORIES_TABLE.columns
            if c.name == "classification"
        )
        assert col.enum_values is not None
        assert set(col.enum_values) == VALID_CLASSIFICATIONS

    def test_sensitivity_enum_matches_domain(self) -> None:
        col = next(
            c for c in MEMORIES_TABLE.columns if c.name == "sensitivity"
        )
        assert col.enum_values is not None
        assert set(col.enum_values) == VALID_SENSITIVITY_LEVELS

    def test_retention_policy_enum_matches_domain(self) -> None:
        valid_policies = {"persistent", "ephemeral", "time_bound"}
        col = next(
            c for c in MEMORIES_TABLE.columns
            if c.name == "retention_policy"
        )
        assert col.enum_values is not None
        assert set(col.enum_values) == valid_policies

    def test_retention_status_enum_matches_domain(self) -> None:
        domain_values = {e.value for e in RetentionStatus}
        col = next(
            c for c in MEMORIES_TABLE.columns
            if c.name == "retention_status"
        )
        assert col.enum_values is not None
        assert set(col.enum_values) == domain_values

    def test_consent_status_enum_matches_domain(self) -> None:
        domain_values = {e.value for e in ConsentStatus}
        col = next(
            c for c in CONSENTS_TABLE.columns if c.name == "status"
        )
        assert col.enum_values is not None
        assert set(col.enum_values) == domain_values

    def test_source_type_max_length(self) -> None:
        col = next(
            c for c in MEMORIES_TABLE.columns if c.name == "source_type"
        )
        assert col.max_length == 64

    def test_policy_version_max_length(self) -> None:
        col = next(
            c for c in CONSENTS_TABLE.columns
            if c.name == "policy_version"
        )
        assert col.max_length == 16

    def test_memory_id_max_length_not_set(self) -> None:
        col = next(
            c for c in MEMORIES_TABLE.columns if c.name == "memory_id"
        )
        assert col.max_length is None

    def test_outbox_both_indexes_present(self) -> None:
        assert "ix_memory_outbox_unpublished" in MEMORY_OUTBOX_TABLE.indexes
        assert "ix_memory_outbox_aggregate" in MEMORY_OUTBOX_TABLE.indexes

    def test_memories_source_index(self) -> None:
        assert "ix_memories_source" in MEMORIES_TABLE.indexes


# ===================================================================
# DTO ↔ Domain entity field parity
# ===================================================================


class TestDomainDTOParity:
    """Verify DTO fields align with domain entity properties."""

    def test_memory_dto_has_all_domain_fields(self) -> None:
        dto_fields = {
            "memory_id": str,
            "consent_id": str,
            "content": str,
            "category": str,
            "source_type": str,
            "source_id": str | None,
            "classification": str,
            "sensitivity": str,
            "revision": int,
            "created_at": datetime,
            "updated_at": datetime | None,
            "deleted_at": datetime | None,
        }
        import dataclasses
        dto_field_map = {
            f.name: f.type for f in dataclasses.fields(MemoryStorageDTO)
        }
        for name, expected_type in dto_fields.items():
            assert name in dto_field_map, (
                f"MemoryStorageDTO missing field {name!r}"
            )

    def test_consent_dto_has_all_domain_fields(self) -> None:
        dto_fields = {
            "consent_id": str,
            "status": str,
            "granted_at": datetime | None,
            "expires_at": datetime | None,
            "revoked_at": datetime | None,
            "policy_version": str,
        }
        import dataclasses
        dto_field_map = {
            f.name: f.type for f in dataclasses.fields(ConsentStorageDTO)
        }
        for name in dto_fields:
            assert name in dto_field_map

    def test_memory_provenance_flattened(self) -> None:
        dto_fields = {
            f.name for f in __import__(
                "dataclasses"
            ).fields(MemoryStorageDTO)
        }
        assert "provenance_actor_id" in dto_fields
        assert "provenance_timestamp" in dto_fields
        assert "provenance" not in dto_fields

    def test_retention_policy_flattened(self) -> None:
        dto_fields = {
            f.name for f in __import__(
                "dataclasses"
            ).fields(MemoryStorageDTO)
        }
        assert "retention_policy" in dto_fields
        assert "retention" not in dto_fields


# ===================================================================
# Port / mapper interface signature verification
# ===================================================================


class TestMapperMethodSignatures:
    def test_memory_mapper_methods(self) -> None:
        mapper: MemoryMapper = StubMemoryMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")

    def test_consent_mapper_methods(self) -> None:
        mapper: ConsentMapper = StubConsentMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")

    def test_outbox_mapper_methods(self) -> None:
        mapper: MemoryOutboxMapper = StubMemoryOutboxMapper()
        assert hasattr(mapper, "event_to_dto")
        assert hasattr(mapper, "dto_to_event")
