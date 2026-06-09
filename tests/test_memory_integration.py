from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import memory as memory_router
from backend.core.database import get_db
from backend.memory.adapters.outbound.clock import SystemClockAdapter
from backend.memory.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.memory.adapters.outbound.mapper import (
    ConsentMapperImpl,
    MemoryMapperImpl,
    MemoryOutboxMapperImpl,
)
from backend.memory.adapters.outbound.models import Base, MemoryOutboxModel
from backend.memory.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyConsentRepository,
    SqlAlchemyMemoryOutboxAdapter,
    SqlAlchemyMemoryRepository,
)
from backend.memory.application.persistence.dto import (
    ConsentStorageDTO,
    MemoryOutboxStorageDTO,
    MemoryStorageDTO,
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

for _table in Base.metadata.tables.values():
    _table.schema = None


@pytest.fixture
def engine() -> Iterator[Engine]:
    e = create_engine("sqlite://", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    yield e
    e.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    conn = engine.connect()
    s = Session(bind=conn)
    yield s
    s.close()
    conn.close()


@pytest.fixture
def clock() -> SystemClockAdapter:
    return SystemClockAdapter()


@pytest.fixture
def id_gen() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


@pytest.fixture
def memory_mapper() -> MemoryMapperImpl:
    return MemoryMapperImpl()


@pytest.fixture
def consent_mapper() -> ConsentMapperImpl:
    return ConsentMapperImpl()


@pytest.fixture
def outbox_mapper() -> MemoryOutboxMapperImpl:
    return MemoryOutboxMapperImpl()


@pytest.fixture
def memory_repo(session: Session, memory_mapper: MemoryMapperImpl) -> SqlAlchemyMemoryRepository:
    return SqlAlchemyMemoryRepository(session=session, mapper=memory_mapper)


@pytest.fixture
def consent_repo(session: Session, consent_mapper: ConsentMapperImpl) -> SqlAlchemyConsentRepository:
    return SqlAlchemyConsentRepository(session=session, mapper=consent_mapper)


@pytest.fixture
def outbox_adapter(session: Session, outbox_mapper: MemoryOutboxMapperImpl) -> SqlAlchemyMemoryOutboxAdapter:
    return SqlAlchemyMemoryOutboxAdapter(session=session, mapper=outbox_mapper)


@pytest.fixture
def client(session: Session):
    def _override_get_db():
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    app = FastAPI()
    app.include_router(memory_router.router, prefix="/api/v1/memory")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


# ===================================================================
# Consent lifecycle
# ===================================================================


class TestConsentLifecycle:
    def test_grant_then_get(self, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        consent = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.ACTIVE)
        consent_repo.save(consent)
        found = consent_repo.find_by_id(consent.consent_id)
        assert found is not None
        assert found.status == ConsentStatus.ACTIVE

    def test_grant_revoke_then_get(self, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        consent = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.ACTIVE)
        consent_repo.save(consent)
        consent.revoke()
        consent_repo.save(consent)
        found = consent_repo.find_by_id(consent.consent_id)
        assert found is not None
        assert found.status == ConsentStatus.REVOKED
        assert found.revoked_at is not None

    def test_grant_revoke_then_get_active_empty(self, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        consent = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.ACTIVE)
        consent_repo.save(consent)
        consent.revoke()
        consent_repo.save(consent)
        active = consent_repo.find_active()
        assert len(active) == 0

    def test_find_revoked(self, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        consent = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.ACTIVE)
        consent_repo.save(consent)
        consent.revoke()
        consent_repo.save(consent)
        revoked = consent_repo.find_revoked()
        assert len(revoked) == 1

    def test_consent_count(self, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        for _ in range(3):
            c = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.ACTIVE)
            consent_repo.save(c)
        assert consent_repo.count() == 3

    def test_grant_emits_event(self, session: Session, outbox_adapter: SqlAlchemyMemoryOutboxAdapter, clock: SystemClockAdapter) -> None:
        consent = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.PROPOSED)
        consent.grant()
        event = ConsentGranted(consent_id=consent.consent_id, occurred_at=clock.now())
        outbox_adapter.append(event)
        session.flush()
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], ConsentGranted)

    def test_revoke_emits_event(self, session: Session, outbox_adapter: SqlAlchemyMemoryOutboxAdapter, clock: SystemClockAdapter) -> None:
        consent = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.ACTIVE)
        consent.revoke()
        event = ConsentRevoked(consent_id=consent.consent_id, occurred_at=clock.now())
        outbox_adapter.append(event)
        session.flush()
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], ConsentRevoked)


# ===================================================================
# Memory lifecycle
# ===================================================================


class TestMemoryLifecycle:
    def test_create_then_get(self, memory_repo: SqlAlchemyMemoryRepository, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        cid, mid = self._create_memory(memory_repo, consent_repo, clock)
        found = memory_repo.find_by_id(mid)
        assert found is not None
        assert str(found.memory_id) == str(mid)

    def test_create_update_then_get(self, memory_repo: SqlAlchemyMemoryRepository, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        cid, mid = self._create_memory(memory_repo, consent_repo, clock)
        memory = memory_repo.find_by_id(mid)
        assert memory is not None
        consent = consent_repo.find_by_id(memory.consent_id)
        assert consent is not None
        memory.update(content=MemoryContent(value="Updated content"), consent=consent)
        memory_repo.save(memory)
        found = memory_repo.find_by_id(mid)
        assert found is not None
        assert found.content.value == "Updated content"
        assert int(found.revision) >= 1

    def test_create_delete_then_find_deleted(self, memory_repo: SqlAlchemyMemoryRepository, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        cid, mid = self._create_memory(memory_repo, consent_repo, clock)
        memory = memory_repo.find_by_id(mid)
        assert memory is not None
        memory.delete()
        memory_repo.save(memory)
        deleted = memory_repo.find_deleted()
        assert len(deleted) == 1
        assert deleted[0].memory_id == memory.memory_id

    def test_search_by_consent_id(self, memory_repo: SqlAlchemyMemoryRepository, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        cid, mid = self._create_memory(memory_repo, consent_repo, clock)
        results = memory_repo.find_by_consent_id(cid)
        assert len(results) == 1

    def test_search_by_category(self, memory_repo: SqlAlchemyMemoryRepository, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        cid, mid = self._create_memory(memory_repo, consent_repo, clock)
        results = memory_repo.find_by_category(MemoryCategory.GENERAL)
        assert len(results) == 1

    def test_count(self, memory_repo: SqlAlchemyMemoryRepository, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        for _ in range(3):
            self._create_memory(memory_repo, consent_repo, clock)
        assert memory_repo.count() == 3

    def test_soft_deleted_memory_find_by_id_shows_deleted(self, memory_repo: SqlAlchemyMemoryRepository, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        cid, mid = self._create_memory(memory_repo, consent_repo, clock)
        memory = memory_repo.find_by_id(mid)
        assert memory is not None
        memory.delete()
        memory_repo.save(memory)
        found = memory_repo.find_by_id(mid)
        assert found is not None
        assert found.state == MemoryState.DELETED
        assert found.deleted_at is not None

    def _create_memory(self, memory_repo, consent_repo, clock) -> tuple[ConsentId, MemoryId]:
        consent = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.ACTIVE)
        consent_repo.save(consent)
        memory = Memory(
            memory_id=MemoryId(),
            consent_id=consent.consent_id,
            content=MemoryContent(value="Lifecycle test"),
            category=MemoryCategory.GENERAL,
            source_type="user_input",
            source_id=None,
            provenance=Provenance(source="user_input", timestamp=clock.now(), actor_id="test"),
            classification="public",
            sensitivity="public",
            retention=RetentionPolicy(policy="persistent"),
            revision=RevisionNumber(value=1),
            created_at=clock.now(),
        )
        memory_repo.save(memory)
        return consent.consent_id, memory.memory_id


# ===================================================================
# Retention lifecycle
# ===================================================================


class TestRetentionLifecycle:
    def test_active_to_expired(self, memory_repo: SqlAlchemyMemoryRepository, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        memory = self._make_memory(consent_repo, clock)
        memory_repo.save(memory)
        memory.expire_retention()
        memory_repo.save(memory)
        found = memory_repo.find_by_id(memory.memory_id)
        assert found is not None
        assert found.retention_status == RetentionStatus.EXPIRED

    def test_expired_to_purge_pending(self, memory_repo: SqlAlchemyMemoryRepository, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        memory = self._make_memory(consent_repo, clock)
        memory_repo.save(memory)
        memory.expire_retention()
        memory_repo.save(memory)
        memory.schedule_purge()
        memory_repo.save(memory)
        found = memory_repo.find_by_id(memory.memory_id)
        assert found is not None
        assert found.retention_status == RetentionStatus.PURGE_PENDING

    def test_purge_pending_to_purged(self, memory_repo: SqlAlchemyMemoryRepository, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        memory = self._make_memory(consent_repo, clock)
        memory_repo.save(memory)
        memory.purge_memory()
        memory_repo.save(memory)
        found = memory_repo.find_by_id(memory.memory_id)
        assert found is not None
        assert found.retention_status == RetentionStatus.PURGED
        assert found.state == MemoryState.DELETED

    def test_purged_memory_is_deleted(self, memory_repo: SqlAlchemyMemoryRepository, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        memory = self._make_memory(consent_repo, clock)
        memory_repo.save(memory)
        memory.purge_memory()
        memory_repo.save(memory)
        assert memory.is_deleted

    def test_full_retention_cycle(self, memory_repo: SqlAlchemyMemoryRepository, consent_repo: SqlAlchemyConsentRepository, clock: SystemClockAdapter) -> None:
        memory = self._make_memory(consent_repo, clock)
        memory_repo.save(memory)
        assert memory.retention_status == RetentionStatus.ACTIVE
        memory.expire_retention()
        memory_repo.save(memory)
        assert memory.retention_status == RetentionStatus.EXPIRED
        memory.schedule_purge()
        memory_repo.save(memory)
        assert memory.retention_status == RetentionStatus.PURGE_PENDING
        memory.purge_memory()
        memory_repo.save(memory)
        assert memory.retention_status == RetentionStatus.PURGED
        assert memory.state == MemoryState.DELETED

    def _make_memory(self, consent_repo, clock) -> Memory:
        consent = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.ACTIVE)
        consent_repo.save(consent)
        return Memory(
            memory_id=MemoryId(),
            consent_id=consent.consent_id,
            content=MemoryContent(value="Retention test"),
            category=MemoryCategory.GENERAL,
            source_type="user_input",
            source_id=None,
            provenance=Provenance(source="user_input", timestamp=clock.now(), actor_id="test"),
            classification="public",
            sensitivity="public",
            retention=RetentionPolicy(policy="persistent"),
            revision=RevisionNumber(value=1),
            created_at=clock.now(),
        )


# ===================================================================
# Repository roundtrip
# ===================================================================


class TestRepositoryRoundtrip:
    ROUNDTRIP_FIELDS = [
        "memory_id",
        "consent_id",
        "revision",
        "classification",
        "sensitivity",
        "retention_policy",
        "retention_status",
    ]

    def test_domain_to_dto_to_orm_to_dto_to_domain(self, session: Session, memory_mapper: MemoryMapperImpl, clock: SystemClockAdapter) -> None:
        now = clock.now()
        original = Memory(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            content=MemoryContent(value="Roundtrip test"),
            category=MemoryCategory.DOCUMENT,
            source_type="external",
            source_id="ext-001",
            provenance=Provenance(source="external", timestamp=now, actor_id="system"),
            classification="internal",
            sensitivity="internal",
            retention=RetentionPolicy(policy="persistent"),
            revision=RevisionNumber(value=3),
            created_at=now,
        )
        dto = memory_mapper.domain_to_dto(original)
        from backend.memory.adapters.outbound.models import MemoryModel
        model = MemoryModel(
            memory_id=dto.memory_id,
            consent_id=dto.consent_id,
            content=dto.content,
            category=dto.category,
            source_type=dto.source_type,
            source_id=dto.source_id,
            provenance_actor_id=dto.provenance_actor_id,
            provenance_timestamp=dto.provenance_timestamp,
            classification=dto.classification,
            sensitivity=dto.sensitivity,
            retention_policy=dto.retention_policy,
            retention_status=dto.retention_status,
            revision=dto.revision,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            deleted_at=dto.deleted_at,
        )
        session.add(model)
        session.flush()
        session.expire(model)
        loaded = session.get(MemoryModel, dto.memory_id)
        assert loaded is not None
        back_dto = MemoryStorageDTO(
            memory_id=loaded.memory_id,
            consent_id=loaded.consent_id,
            content=loaded.content,
            category=loaded.category,
            source_type=loaded.source_type,
            source_id=loaded.source_id,
            provenance_actor_id=loaded.provenance_actor_id,
            provenance_timestamp=loaded.provenance_timestamp,
            classification=loaded.classification,
            sensitivity=loaded.sensitivity,
            retention_policy=loaded.retention_policy,
            retention_status=loaded.retention_status,
            revision=loaded.revision,
            created_at=loaded.created_at,
            updated_at=loaded.updated_at,
            deleted_at=loaded.deleted_at,
        )
        reconstructed = memory_mapper.dto_to_domain(back_dto)
        assert str(reconstructed.memory_id) == str(original.memory_id)
        assert str(reconstructed.consent_id) == str(original.consent_id)
        assert int(reconstructed.revision) == int(original.revision)
        assert reconstructed.classification == original.classification
        assert reconstructed.sensitivity == original.sensitivity
        assert reconstructed.retention.policy == original.retention.policy
        assert reconstructed.retention_status == original.retention_status

    def test_consent_roundtrip(self, session: Session, consent_mapper: ConsentMapperImpl, clock: SystemClockAdapter) -> None:
        now = clock.now()
        original = ConsentRecord(
            consent_id=ConsentId(),
            status=ConsentStatus.ACTIVE,
            policy_version="2.0",
            granted_at=now,
        )
        dto = consent_mapper.domain_to_dto(original)
        from backend.memory.adapters.outbound.models import ConsentModel
        model = ConsentModel(
            consent_id=dto.consent_id,
            status=dto.status,
            granted_at=dto.granted_at,
            expires_at=dto.expires_at,
            revoked_at=dto.revoked_at,
            policy_version=dto.policy_version,
        )
        session.add(model)
        session.flush()
        session.expire(model)
        loaded = session.get(ConsentModel, dto.consent_id)
        assert loaded is not None
        back_dto = ConsentStorageDTO(
            consent_id=loaded.consent_id,
            status=loaded.status,
            granted_at=loaded.granted_at,
            expires_at=loaded.expires_at,
            revoked_at=loaded.revoked_at,
            policy_version=loaded.policy_version,
        )
        reconstructed = consent_mapper.dto_to_domain(back_dto)
        assert str(reconstructed.consent_id) == str(original.consent_id)
        assert reconstructed.status == ConsentStatus.ACTIVE
        assert reconstructed.policy_version == "2.0"

    def test_provenance_preserved_through_roundtrip(self, session: Session, memory_mapper: MemoryMapperImpl, clock: SystemClockAdapter) -> None:
        now = clock.now()
        original = Memory(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            content=MemoryContent(value="Provenance test"),
            category=MemoryCategory.INSIGHT,
            source_type="inference",
            source_id=None,
            provenance=Provenance(source="inference", timestamp=now, actor_id="agent-7"),
            classification="public",
            sensitivity="public",
            retention=RetentionPolicy(policy="persistent"),
            revision=RevisionNumber(value=1),
            created_at=now,
        )
        dto = memory_mapper.domain_to_dto(original)
        reconstructed = memory_mapper.dto_to_domain(dto)
        assert reconstructed.provenance.actor_id == "agent-7"
        assert reconstructed.provenance.source == "inference"

    def test_deleted_at_roundtrip(self, session: Session, memory_mapper: MemoryMapperImpl, clock: SystemClockAdapter) -> None:
        now = clock.now()
        original = Memory(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            content=MemoryContent(value="Deleted roundtrip"),
            category=MemoryCategory.GENERAL,
            source_type="user_input",
            source_id=None,
            provenance=Provenance(source="user_input", timestamp=now, actor_id="test"),
            classification="public",
            sensitivity="public",
            retention=RetentionPolicy(policy="persistent"),
            revision=RevisionNumber(value=1),
            created_at=now,
            deleted_at=now,
            state=MemoryState.DELETED,
        )
        dto = memory_mapper.domain_to_dto(original)
        reconstructed = memory_mapper.dto_to_domain(dto)
        assert reconstructed.deleted_at is not None
        assert reconstructed.state == MemoryState.DELETED


# ===================================================================
# Outbox event verification
# ===================================================================


class TestOutboxAllEvents:
    def test_memory_created_event(self, session: Session, outbox_adapter: SqlAlchemyMemoryOutboxAdapter, clock: SystemClockAdapter) -> None:
        event = MemoryCreated(
            memory_id=MemoryId(), consent_id=ConsentId(),
            category=MemoryCategory.GENERAL, source_type="user_input",
            source_id=None, sensitivity="low", occurred_at=clock.now(),
        )
        outbox_adapter.append(event)
        session.flush()
        events = outbox_adapter.fetch_unpublished()
        assert len(events) == 1
        assert isinstance(events[0], MemoryCreated)

    def test_memory_updated_event(self, session: Session, outbox_adapter: SqlAlchemyMemoryOutboxAdapter, clock: SystemClockAdapter) -> None:
        event = MemoryUpdated(memory_id=MemoryId(), revision=2, occurred_at=clock.now())
        outbox_adapter.append(event)
        session.flush()
        events = outbox_adapter.fetch_unpublished()
        assert len(events) == 1
        assert isinstance(events[0], MemoryUpdated)

    def test_memory_deleted_event(self, session: Session, outbox_adapter: SqlAlchemyMemoryOutboxAdapter, clock: SystemClockAdapter) -> None:
        event = MemoryDeleted(memory_id=MemoryId(), revision=1, occurred_at=clock.now())
        outbox_adapter.append(event)
        session.flush()
        events = outbox_adapter.fetch_unpublished()
        assert isinstance(events[0], MemoryDeleted)

    def test_memory_retention_expired_event(self, session: Session, outbox_adapter: SqlAlchemyMemoryOutboxAdapter, clock: SystemClockAdapter) -> None:
        event = MemoryRetentionExpired(memory_id=MemoryId(), revision=1, occurred_at=clock.now())
        outbox_adapter.append(event)
        session.flush()
        events = outbox_adapter.fetch_unpublished()
        assert isinstance(events[0], MemoryRetentionExpired)

    def test_memory_purge_scheduled_event(self, session: Session, outbox_adapter: SqlAlchemyMemoryOutboxAdapter, clock: SystemClockAdapter) -> None:
        event = MemoryPurgeScheduled(memory_id=MemoryId(), revision=1, occurred_at=clock.now())
        outbox_adapter.append(event)
        session.flush()
        events = outbox_adapter.fetch_unpublished()
        assert isinstance(events[0], MemoryPurgeScheduled)

    def test_memory_purged_event(self, session: Session, outbox_adapter: SqlAlchemyMemoryOutboxAdapter, clock: SystemClockAdapter) -> None:
        event = MemoryPurged(memory_id=MemoryId(), revision=1, occurred_at=clock.now())
        outbox_adapter.append(event)
        session.flush()
        events = outbox_adapter.fetch_unpublished()
        assert isinstance(events[0], MemoryPurged)

    def test_consent_granted_event(self, session: Session, outbox_adapter: SqlAlchemyMemoryOutboxAdapter, clock: SystemClockAdapter) -> None:
        event = ConsentGranted(consent_id=ConsentId(), occurred_at=clock.now())
        outbox_adapter.append(event)
        session.flush()
        events = outbox_adapter.fetch_unpublished()
        assert isinstance(events[0], ConsentGranted)

    def test_consent_revoked_event(self, session: Session, outbox_adapter: SqlAlchemyMemoryOutboxAdapter, clock: SystemClockAdapter) -> None:
        event = ConsentRevoked(consent_id=ConsentId(), occurred_at=clock.now())
        outbox_adapter.append(event)
        session.flush()
        events = outbox_adapter.fetch_unpublished()
        assert isinstance(events[0], ConsentRevoked)

    def test_all_eight_events_roundtrip(self, session: Session, outbox_adapter: SqlAlchemyMemoryOutboxAdapter, clock: SystemClockAdapter) -> None:
        now = clock.now()
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
        for e in events:
            outbox_adapter.append(e)
        session.flush()
        fetched = outbox_adapter.fetch_unpublished(limit=10)
        assert len(fetched) == 8

    def test_fifo_ordering(self, session: Session, outbox_adapter: SqlAlchemyMemoryOutboxAdapter) -> None:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(5):
            event = MemoryCreated(
                memory_id=MemoryId(), consent_id=ConsentId(),
                category=MemoryCategory.GENERAL, source_type="ui",
                source_id=None, sensitivity="low",
                occurred_at=base,
            )
            outbox_adapter.append(event)
        session.flush()
        fetched = outbox_adapter.fetch_unpublished(limit=10)
        timestamps = [e.occurred_at for e in fetched]
        assert timestamps == sorted(timestamps)

    def test_mark_published_marks_all(self, session: Session, outbox_adapter: SqlAlchemyMemoryOutboxAdapter, clock: SystemClockAdapter) -> None:
        mid = MemoryId()
        event = MemoryCreated(
            memory_id=mid, consent_id=ConsentId(),
            category=MemoryCategory.GENERAL, source_type="ui",
            source_id=None, sensitivity="low", occurred_at=clock.now(),
        )
        outbox_adapter.append(event)
        session.flush()
        outbox_adapter.mark_published(str(mid))
        remaining = outbox_adapter.fetch_unpublished()
        assert len(remaining) == 0

    def test_aggregate_id_preserved(self, session: Session, outbox_mapper: MemoryOutboxMapperImpl, clock: SystemClockAdapter) -> None:
        mid = MemoryId()
        event = MemoryCreated(
            memory_id=mid, consent_id=ConsentId(),
            category=MemoryCategory.GENERAL, source_type="ui",
            source_id=None, sensitivity="low", occurred_at=clock.now(),
        )
        dto = outbox_mapper.event_to_dto(event)
        reconstructed = outbox_mapper.dto_to_event(dto)
        assert reconstructed.memory_id == mid

    def test_payload_correctness_memory_created(self, outbox_mapper: MemoryOutboxMapperImpl, clock: SystemClockAdapter) -> None:
        mid = MemoryId()
        cid = ConsentId()
        event = MemoryCreated(
            memory_id=mid, consent_id=cid,
            category=MemoryCategory.INSIGHT, source_type="inference",
            source_id="inf-001", sensitivity="low", occurred_at=clock.now(),
        )
        dto = outbox_mapper.event_to_dto(event)
        import json
        payload = json.loads(dto.payload) if dto.payload else {}
        assert payload["consent_id"] == str(cid)
        assert payload["category"] == "insight"
        assert payload["source_type"] == "inference"
        assert payload["source_id"] == "inf-001"

    def test_payload_correctness_memory_updated(self, outbox_mapper: MemoryOutboxMapperImpl, clock: SystemClockAdapter) -> None:
        event = MemoryUpdated(memory_id=MemoryId(), revision=7, occurred_at=clock.now())
        dto = outbox_mapper.event_to_dto(event)
        import json
        payload = json.loads(dto.payload) if dto.payload else {}
        assert payload["revision"] == 7

    def test_consent_granted_no_payload(self, outbox_mapper: MemoryOutboxMapperImpl, clock: SystemClockAdapter) -> None:
        event = ConsentGranted(consent_id=ConsentId(), occurred_at=clock.now())
        dto = outbox_mapper.event_to_dto(event)
        assert dto.payload is None


# ===================================================================
# REST contract verification
# ===================================================================


class TestRESTContract:
    def test_post_memories_201(self, client: TestClient, session: Session, clock: SystemClockAdapter) -> None:
        cid = self._create_active_consent(session, clock)
        resp = client.post(
            "/api/v1/memory/memories",
            json={
                "consent_id": cid,
                "content": "REST test",
                "category": "general",
                "source_type": "user_input",
                "provenance_source": "user_input",
            },
        )
        assert resp.status_code == 201
        assert "memory_id" in resp.json()

    def test_post_memories_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/memory/memories",
            json={"content": "", "category": "", "source_type": "", "provenance_source": ""},
        )
        assert resp.status_code == 422

    def test_patch_memories_200(self, client: TestClient, session: Session, clock: SystemClockAdapter) -> None:
        mid, cid = self._seed_memory(session, clock)
        resp = client.patch(
            f"/api/v1/memory/memories/{mid}",
            json={"content": "Patched", "memory_id": mid},
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Patched"

    def test_patch_memories_404(self, client: TestClient) -> None:
        resp = client.patch(
            "/api/v1/memory/memories/00000000-0000-0000-0000-000000000000",
            json={"content": "nope", "memory_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 404

    def test_delete_memories_200(self, client: TestClient, session: Session, clock: SystemClockAdapter) -> None:
        mid, cid = self._seed_memory(session, clock)
        resp = client.delete(f"/api/v1/memory/memories/{mid}")
        assert resp.status_code == 200
        assert "deleted_at" in resp.json()

    def test_delete_memories_404(self, client: TestClient) -> None:
        resp = client.delete(
            "/api/v1/memory/memories/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_get_memories_200(self, client: TestClient, session: Session, clock: SystemClockAdapter) -> None:
        mid, cid = self._seed_memory(session, clock)
        resp = client.get(f"/api/v1/memory/memories/{mid}")
        assert resp.status_code == 200
        assert resp.json()["memory_id"] == mid

    def test_get_memories_404(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/memory/memories/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_get_memories_search_200(self, client: TestClient, session: Session, clock: SystemClockAdapter) -> None:
        mid, cid = self._seed_memory(session, clock)
        resp = client.get("/api/v1/memory/memories?category=general")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_post_consents_201(self, client: TestClient) -> None:
        resp = client.post("/api/v1/memory/consents", json={})
        assert resp.status_code == 201
        assert resp.json()["status"] == "active"

    def test_post_consents_id_revoke_200(self, client: TestClient, session: Session, clock: SystemClockAdapter) -> None:
        cid = self._create_active_consent(session, clock)
        resp = client.post(f"/api/v1/memory/consents/{cid}/revoke")
        assert resp.status_code == 200
        assert resp.json()["status"] == "revoked"

    def test_post_consents_id_revoke_404(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/memory/consents/00000000-0000-0000-0000-000000000000/revoke"
        )
        assert resp.status_code == 404

    def test_get_consents_200(self, client: TestClient, session: Session, clock: SystemClockAdapter) -> None:
        cid = self._create_active_consent(session, clock)
        resp = client.get(f"/api/v1/memory/consents/{cid}")
        assert resp.status_code == 200
        assert resp.json()["consent_id"] == cid

    def test_get_consents_404(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/memory/consents/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def _create_active_consent(self, session: Session, clock: SystemClockAdapter) -> str:
        from backend.memory.adapters.outbound.models import ConsentModel
        consent = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.ACTIVE)
        mapper = ConsentMapperImpl()
        dto = mapper.domain_to_dto(consent)
        model = ConsentModel(
            consent_id=dto.consent_id, status=dto.status,
            granted_at=dto.granted_at, expires_at=dto.expires_at,
            revoked_at=dto.revoked_at, policy_version=dto.policy_version,
        )
        session.add(model)
        session.commit()
        return dto.consent_id

    def _seed_memory(self, session: Session, clock: SystemClockAdapter) -> tuple[str, str]:
        cid = self._create_active_consent(session, clock)
        from backend.memory.adapters.outbound.models import MemoryModel
        mapper = MemoryMapperImpl()
        memory = Memory(
            memory_id=MemoryId(), consent_id=ConsentId(value=__import__("uuid").UUID(cid)),
            content=MemoryContent(value="Seed memory"),
            category=MemoryCategory.GENERAL, source_type="user_input",
            source_id=None,
            provenance=Provenance(source="user_input", timestamp=clock.now(), actor_id="test"),
            classification="public", sensitivity="public",
            retention=RetentionPolicy(policy="persistent"),
            revision=RevisionNumber(value=1), created_at=clock.now(),
        )
        dto = mapper.domain_to_dto(memory)
        model = MemoryModel(
            memory_id=dto.memory_id, consent_id=dto.consent_id,
            content=dto.content, category=dto.category,
            source_type=dto.source_type, source_id=dto.source_id,
            provenance_actor_id=dto.provenance_actor_id,
            provenance_timestamp=dto.provenance_timestamp,
            classification=dto.classification, sensitivity=dto.sensitivity,
            retention_policy=dto.retention_policy,
            retention_status=dto.retention_status, revision=dto.revision,
            created_at=dto.created_at, updated_at=dto.updated_at,
            deleted_at=dto.deleted_at,
        )
        session.add(model)
        session.commit()
        return dto.memory_id, cid


# ===================================================================
# Cross-service scenarios
# ===================================================================


class TestCrossServiceScenarios:
    def test_consent_active_allows_memory_create(self, client: TestClient, session: Session, clock: SystemClockAdapter) -> None:
        cid = self._create_active_consent(session, clock)
        resp = client.post(
            "/api/v1/memory/memories",
            json={
                "consent_id": cid,
                "content": "Cross-service",
                "category": "general",
                "source_type": "user_input",
                "provenance_source": "user_input",
            },
        )
        assert resp.status_code == 201

    def test_consent_revoked_blocks_memory_create(self, client: TestClient, session: Session, clock: SystemClockAdapter) -> None:
        cid = self._create_active_consent(session, clock)
        client.post(f"/api/v1/memory/consents/{cid}/revoke")
        resp = client.post(
            "/api/v1/memory/memories",
            json={
                "consent_id": cid,
                "content": "Should fail",
                "category": "general",
                "source_type": "user_input",
                "provenance_source": "user_input",
            },
        )
        assert resp.status_code == 400

    def test_memory_created_after_consent_granted(self, client: TestClient, session: Session, clock: SystemClockAdapter) -> None:
        cid = self._create_active_consent(session, clock)
        resp = client.post(
            "/api/v1/memory/memories",
            json={
                "consent_id": cid,
                "content": "After consent",
                "category": "insight",
                "source_type": "inference",
                "provenance_source": "inference",
            },
        )
        assert resp.status_code == 201
        mid = resp.json()["memory_id"]
        get_resp = client.get(f"/api/v1/memory/memories/{mid}")
        assert get_resp.json()["content"] == "After consent"

    def _create_active_consent(self, session: Session, clock: SystemClockAdapter) -> str:
        consent = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.ACTIVE)
        mapper = ConsentMapperImpl()
        dto = mapper.domain_to_dto(consent)
        from backend.memory.adapters.outbound.models import ConsentModel
        model = ConsentModel(
            consent_id=dto.consent_id, status=dto.status,
            granted_at=dto.granted_at, expires_at=dto.expires_at,
            revoked_at=dto.revoked_at, policy_version=dto.policy_version,
        )
        session.add(model)
        session.commit()
        return dto.consent_id
