from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.memory.adapters.outbound.clock import SystemClockAdapter
from backend.memory.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.memory.adapters.outbound.mapper import (
    ConsentMapperImpl,
    MemoryMapperImpl,
    MemoryOutboxMapperImpl,
)
from backend.memory.adapters.outbound.models import Base
from backend.memory.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyConsentRepository,
    SqlAlchemyMemoryOutboxAdapter,
    SqlAlchemyMemoryRepository,
)
from backend.memory.application.ports.outbox import MemoryOutboxPort
from backend.memory.application.ports.repository import (
    ConsentRepositoryPort,
    MemoryRepositoryPort,
)
from backend.memory.domain.model import (
    ConsentId,
    ConsentRecord,
    ConsentStatus,
    Memory,
    MemoryCategory,
    MemoryContent,
    MemoryId,
    MemoryState,
    Provenance,
    RetentionPolicy,
    RetentionStatus,
    RevisionNumber,
)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def engine() -> Iterator[Engine]:
    e = create_engine("sqlite://", echo=False)
    for t in Base.metadata.tables.values():
        t.schema = None
    Base.metadata.create_all(bind=e)
    yield e
    e.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    S = sessionmaker(bind=engine)
    s = S()
    yield s
    s.close()


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
def clock() -> SystemClockAdapter:
    return SystemClockAdapter()


@pytest.fixture
def id_gen() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


@pytest.fixture
def memory_repo(
    session: Session, memory_mapper: MemoryMapperImpl
) -> MemoryRepositoryPort:
    return SqlAlchemyMemoryRepository(session=session, mapper=memory_mapper)


@pytest.fixture
def consent_repo(
    session: Session, consent_mapper: ConsentMapperImpl
) -> ConsentRepositoryPort:
    return SqlAlchemyConsentRepository(session=session, mapper=consent_mapper)


@pytest.fixture
def outbox_adapter(
    session: Session, outbox_mapper: MemoryOutboxMapperImpl
) -> MemoryOutboxPort:
    return SqlAlchemyMemoryOutboxAdapter(session=session, mapper=outbox_mapper)


@pytest.fixture
def a_memory(clock: SystemClockAdapter) -> Memory:
    return Memory(
        memory_id=MemoryId(),
        consent_id=ConsentId(),
        content=MemoryContent(value="Integration test memory"),
        category=MemoryCategory.GENERAL,
        source_type="user_input",
        source_id=None,
        provenance=Provenance(
            source="user_input",
            timestamp=clock.now(),
            actor_id="test-user",
        ),
        classification="test",
        sensitivity="test",
        retention=RetentionPolicy(policy="persistent"),
        revision=RevisionNumber(value=1),
        created_at=clock.now(),
    )


@pytest.fixture
def a_consent(clock: SystemClockAdapter) -> ConsentRecord:
    return ConsentRecord(
        consent_id=ConsentId(),
        status=ConsentStatus.ACTIVE,
        policy_version="1.0",
        granted_at=clock.now(),
    )


# ===================================================================
# Memory repository integration tests
# ===================================================================


class TestMemoryRepositoryIntegration:
    def test_save_and_find_by_id(
        self, memory_repo: MemoryRepositoryPort, a_memory: Memory
    ) -> None:
        memory_repo.save(a_memory)
        found = memory_repo.find_by_id(a_memory.memory_id)
        assert found is not None
        assert str(found.memory_id) == str(a_memory.memory_id)

    def test_save_updates_existing(
        self, memory_repo: MemoryRepositoryPort, a_memory: Memory, clock: SystemClockAdapter
    ) -> None:
        memory_repo.save(a_memory)
        found = memory_repo.find_by_id(a_memory.memory_id)
        assert found is not None
        assert found.content.value == "Integration test memory"

    def test_find_by_id_missing(self, memory_repo: MemoryRepositoryPort) -> None:
        found = memory_repo.find_by_id(MemoryId())
        assert found is None

    def test_find_by_consent_id(
        self, memory_repo: MemoryRepositoryPort, a_memory: Memory
    ) -> None:
        memory_repo.save(a_memory)
        results = memory_repo.find_by_consent_id(a_memory.consent_id)
        assert len(results) == 1
        assert results[0].memory_id == a_memory.memory_id

    def test_find_by_consent_id_empty(self, memory_repo: MemoryRepositoryPort) -> None:
        results = memory_repo.find_by_consent_id(ConsentId())
        assert len(results) == 0

    def test_find_by_category(
        self, memory_repo: MemoryRepositoryPort, a_memory: Memory
    ) -> None:
        memory_repo.save(a_memory)
        results = memory_repo.find_by_category(MemoryCategory.GENERAL)
        assert len(results) >= 1

    def test_find_by_category_none(
        self, memory_repo: MemoryRepositoryPort, id_gen: UuidGeneratorAdapter, clock: SystemClockAdapter
    ) -> None:
        m = Memory(
            memory_id=id_gen.generate_memory_id(),
            consent_id=ConsentId(),
            content=MemoryContent(value="Insight"),
            category=MemoryCategory.INSIGHT,
            source_type="inference",
            source_id=None,
            provenance=Provenance(
                source="inference", timestamp=clock.now(), actor_id="test"
            ),
            classification="test",
            sensitivity="test",
            retention=RetentionPolicy(policy="persistent"),
            revision=RevisionNumber(value=1),
            created_at=clock.now(),
        )
        memory_repo.save(m)
        results = memory_repo.find_by_category(MemoryCategory.DOCUMENT)
        assert len(results) == 0

    def test_find_by_source(
        self, memory_repo: MemoryRepositoryPort, a_memory: Memory
    ) -> None:
        memory_repo.save(a_memory)
        results = memory_repo.find_by_source("user_input", None)
        assert len(results) == 1

    def test_find_by_source_with_id(
        self, memory_repo: MemoryRepositoryPort, a_memory: Memory
    ) -> None:
        memory_repo.save(a_memory)
        results = memory_repo.find_by_source("user_input", "nonexistent")
        assert len(results) == 0

    def test_save_multiple_and_count(
        self,
        memory_repo: MemoryRepositoryPort,
        id_gen: UuidGeneratorAdapter,
        clock: SystemClockAdapter,
    ) -> None:
        m1 = Memory(
            memory_id=id_gen.generate_memory_id(),
            consent_id=ConsentId(),
            content=MemoryContent(value="First"),
            category=MemoryCategory.GENERAL,
            source_type="user_input",
            source_id=None,
            provenance=Provenance(
                source="user_input", timestamp=clock.now(), actor_id="u1"
            ),
            classification="test",
            sensitivity="test",
            retention=RetentionPolicy(policy="persistent"),
            revision=RevisionNumber(value=1),
            created_at=clock.now(),
        )
        m2 = Memory(
            memory_id=id_gen.generate_memory_id(),
            consent_id=ConsentId(),
            content=MemoryContent(value="Second"),
            category=MemoryCategory.GENERAL,
            source_type="user_input",
            source_id=None,
            provenance=Provenance(
                source="user_input", timestamp=clock.now(), actor_id="u2"
            ),
            classification="test",
            sensitivity="test",
            retention=RetentionPolicy(policy="persistent"),
            revision=RevisionNumber(value=1),
            created_at=clock.now(),
        )
        memory_repo.save(m1)
        memory_repo.save(m2)
        assert memory_repo.count() == 2

    def test_find_deleted(
        self, memory_repo: MemoryRepositoryPort, a_memory: Memory
    ) -> None:
        memory_repo.save(a_memory)
        a_memory.delete()
        memory_repo.save(a_memory)
        results = memory_repo.find_deleted()
        assert len(results) == 1
        assert results[0].memory_id == a_memory.memory_id

    def test_find_deleted_excludes_active(
        self, memory_repo: MemoryRepositoryPort, a_memory: Memory
    ) -> None:
        memory_repo.save(a_memory)
        results = memory_repo.find_deleted()
        assert len(results) == 0

    def test_count_empty(self, memory_repo: MemoryRepositoryPort) -> None:
        assert memory_repo.count() == 0

    def test_find_by_consent_id_multiple(
        self,
        memory_repo: MemoryRepositoryPort,
        id_gen: UuidGeneratorAdapter,
        clock: SystemClockAdapter,
    ) -> None:
        cid = ConsentId()
        for i in range(3):
            m = Memory(
                memory_id=id_gen.generate_memory_id(),
                consent_id=cid,
                content=MemoryContent(value=f"Memory {i}"),
                category=MemoryCategory.GENERAL,
                source_type="user_input",
                source_id=None,
                provenance=Provenance(
                    source="user_input", timestamp=clock.now(), actor_id="u"
                ),
                classification="test",
                sensitivity="test",
                retention=RetentionPolicy(policy="persistent"),
                revision=RevisionNumber(value=1),
                created_at=clock.now(),
            )
            memory_repo.save(m)
        results = memory_repo.find_by_consent_id(cid)
        assert len(results) == 3

    def test_save_updates_soft_deleted_state(
        self, memory_repo: MemoryRepositoryPort, a_memory: Memory
    ) -> None:
        memory_repo.save(a_memory)
        a_memory.delete()
        memory_repo.save(a_memory)
        found = memory_repo.find_by_id(a_memory.memory_id)
        assert found is not None
        assert found.state == MemoryState.DELETED
        assert found.deleted_at is not None

    def test_provenance_preserved(
        self, memory_repo: MemoryRepositoryPort, a_memory: Memory
    ) -> None:
        memory_repo.save(a_memory)
        found = memory_repo.find_by_id(a_memory.memory_id)
        assert found is not None
        assert found.provenance.actor_id == "test-user"

    def test_revision_preserved(
        self, memory_repo: MemoryRepositoryPort, a_memory: Memory
    ) -> None:
        memory_repo.save(a_memory)
        found = memory_repo.find_by_id(a_memory.memory_id)
        assert found is not None
        assert int(found.revision) == 1


# ===================================================================
# Consent repository integration tests
# ===================================================================


class TestConsentRepositoryIntegration:
    def test_save_and_find_by_id(
        self, consent_repo: ConsentRepositoryPort, a_consent: ConsentRecord
    ) -> None:
        consent_repo.save(a_consent)
        found = consent_repo.find_by_id(a_consent.consent_id)
        assert found is not None
        assert found.consent_id == a_consent.consent_id

    def test_find_by_id_missing(self, consent_repo: ConsentRepositoryPort) -> None:
        found = consent_repo.find_by_id(ConsentId())
        assert found is None

    def test_find_active(
        self, consent_repo: ConsentRepositoryPort, a_consent: ConsentRecord, clock: SystemClockAdapter
    ) -> None:
        consent_repo.save(a_consent)
        revoked = ConsentRecord(
            consent_id=ConsentId(),
            status=ConsentStatus.REVOKED,
            policy_version="1.0",
            granted_at=clock.now(),
            revoked_at=clock.now(),
        )
        consent_repo.save(revoked)
        active = consent_repo.find_active()
        assert len(active) == 1
        assert active[0].consent_id == a_consent.consent_id

    def test_find_active_all_revoked(
        self, consent_repo: ConsentRepositoryPort, clock: SystemClockAdapter
    ) -> None:
        c = ConsentRecord(
            consent_id=ConsentId(),
            status=ConsentStatus.REVOKED,
            policy_version="1.0",
            granted_at=clock.now(),
            revoked_at=clock.now(),
        )
        consent_repo.save(c)
        active = consent_repo.find_active()
        assert len(active) == 0

    def test_find_expired(
        self, consent_repo: ConsentRepositoryPort, clock: SystemClockAdapter
    ) -> None:
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        expired = ConsentRecord(
            consent_id=ConsentId(),
            status=ConsentStatus.ACTIVE,
            policy_version="1.0",
            granted_at=past,
            expires_at=past,
        )
        consent_repo.save(expired)
        results = consent_repo.find_expired()
        assert len(results) == 1

    def test_find_revoked(
        self, consent_repo: ConsentRepositoryPort, clock: SystemClockAdapter
    ) -> None:
        c = ConsentRecord(
            consent_id=ConsentId(),
            status=ConsentStatus.REVOKED,
            policy_version="1.0",
            granted_at=clock.now(),
            revoked_at=clock.now(),
        )
        consent_repo.save(c)
        results = consent_repo.find_revoked()
        assert len(results) == 1

    def test_count(
        self, consent_repo: ConsentRepositoryPort, a_consent: ConsentRecord
    ) -> None:
        consent_repo.save(a_consent)
        assert consent_repo.count() == 1

    def test_count_empty(self, consent_repo: ConsentRepositoryPort) -> None:
        assert consent_repo.count() == 0

    def test_save_updates_revoked_status(
        self, consent_repo: ConsentRepositoryPort, clock: SystemClockAdapter
    ) -> None:
        c = ConsentRecord(
            consent_id=ConsentId(),
            status=ConsentStatus.ACTIVE,
            policy_version="1.0",
            granted_at=clock.now(),
        )
        consent_repo.save(c)
        c.revoke()
        consent_repo.save(c)
        found = consent_repo.find_by_id(c.consent_id)
        assert found is not None
        assert found.status == ConsentStatus.REVOKED

    def test_consent_with_expiry(
        self, consent_repo: ConsentRepositoryPort, clock: SystemClockAdapter
    ) -> None:
        future = datetime(2099, 12, 31, tzinfo=timezone.utc)
        c = ConsentRecord(
            consent_id=ConsentId(),
            status=ConsentStatus.ACTIVE,
            policy_version="1.0",
            granted_at=clock.now(),
            expires_at=future,
        )
        consent_repo.save(c)
        found = consent_repo.find_by_id(c.consent_id)
        assert found is not None
        assert found.expires_at is not None
        assert found.expires_at.year == 2099

    def test_no_expiry(
        self, consent_repo: ConsentRepositoryPort, a_consent: ConsentRecord
    ) -> None:
        consent_repo.save(a_consent)
        found = consent_repo.find_by_id(a_consent.consent_id)
        assert found is not None
        assert found.expires_at is None


# ===================================================================
# Outbox adapter integration tests
# ===================================================================


class TestMemoryOutboxAdapterIntegration:
    def test_append_and_fetch(
        self,
        outbox_adapter: MemoryOutboxPort,
        clock: SystemClockAdapter,
        id_gen: UuidGeneratorAdapter,
    ) -> None:
        from backend.memory.domain.model import MemoryCreated

        event = MemoryCreated(
            memory_id=id_gen.generate_memory_id(),
            consent_id=ConsentId(),
            category=MemoryCategory.GENERAL,
            source_type="user_input",
            source_id=None,
            sensitivity="low",
            occurred_at=clock.now(),
        )
        outbox_adapter.append(event)
        fetched = outbox_adapter.fetch_unpublished(limit=10)
        assert len(fetched) == 1
        assert isinstance(fetched[0], MemoryCreated)

    def test_fetch_unpublished_respects_limit(
        self,
        outbox_adapter: MemoryOutboxPort,
        clock: SystemClockAdapter,
        id_gen: UuidGeneratorAdapter,
    ) -> None:
        from backend.memory.domain.model import MemoryCreated

        for _ in range(5):
            outbox_adapter.append(
                MemoryCreated(
                    memory_id=id_gen.generate_memory_id(),
                    consent_id=ConsentId(),
                    category=MemoryCategory.GENERAL,
                    source_type="user_input",
                    source_id=None,
                    sensitivity="low",
                    occurred_at=clock.now(),
                )
            )
        fetched = outbox_adapter.fetch_unpublished(limit=3)
        assert len(fetched) == 3

    def test_mark_published(
        self,
        outbox_adapter: MemoryOutboxPort,
        clock: SystemClockAdapter,
        id_gen: UuidGeneratorAdapter,
    ) -> None:
        from backend.memory.domain.model import MemoryCreated

        mid = id_gen.generate_memory_id()
        outbox_adapter.append(
            MemoryCreated(
                memory_id=mid,
                consent_id=ConsentId(),
                category=MemoryCategory.GENERAL,
                source_type="user_input",
                source_id=None,
                sensitivity="low",
                occurred_at=clock.now(),
            )
        )
        fetched = outbox_adapter.fetch_unpublished(limit=10)
        assert len(fetched) == 1
        outbox_adapter.mark_published(str(fetched[0].event_id))
        remaining = outbox_adapter.fetch_unpublished(limit=10)
        assert len(remaining) == 0

    def test_mark_published_partial(
        self,
        outbox_adapter: MemoryOutboxPort,
        clock: SystemClockAdapter,
        id_gen: UuidGeneratorAdapter,
    ) -> None:
        from backend.memory.domain.model import MemoryCreated

        mids = []
        for _ in range(4):
            mid = id_gen.generate_memory_id()
            mids.append(mid)
            outbox_adapter.append(
                MemoryCreated(
                    memory_id=mid,
                    consent_id=ConsentId(),
                    category=MemoryCategory.GENERAL,
                    source_type="user_input",
                    source_id=None,
                    sensitivity="low",
                    occurred_at=clock.now(),
                )
            )
        all_fetched = outbox_adapter.fetch_unpublished(limit=10)
        assert len(all_fetched) == 4

        outbox_adapter.mark_published(str(all_fetched[0].event_id))
        outbox_adapter.mark_published(str(all_fetched[1].event_id))
        remaining = outbox_adapter.fetch_unpublished(limit=10)
        assert len(remaining) == 2

    def test_idempotent_mark_published(
        self,
        outbox_adapter: MemoryOutboxPort,
        clock: SystemClockAdapter,
        id_gen: UuidGeneratorAdapter,
    ) -> None:
        from backend.memory.domain.model import MemoryCreated

        mid = id_gen.generate_memory_id()
        outbox_adapter.append(
            MemoryCreated(
                memory_id=mid,
                consent_id=ConsentId(),
                category=MemoryCategory.GENERAL,
                source_type="user_input",
                source_id=None,
                sensitivity="low",
                occurred_at=clock.now(),
            )
        )
        fetched = outbox_adapter.fetch_unpublished(limit=10)
        outbox_adapter.mark_published(str(fetched[0].event_id))
        outbox_adapter.mark_published(str(fetched[0].event_id))
        remaining = outbox_adapter.fetch_unpublished(limit=10)
        assert len(remaining) == 0

    def test_fetch_fifo_order(
        self,
        outbox_adapter: MemoryOutboxPort,
        clock: SystemClockAdapter,
        id_gen: UuidGeneratorAdapter,
    ) -> None:
        from backend.memory.domain.model import MemoryCreated

        for _ in range(5):
            outbox_adapter.append(
                MemoryCreated(
                    memory_id=id_gen.generate_memory_id(),
                    consent_id=ConsentId(),
                    category=MemoryCategory.GENERAL,
                    source_type="user_input",
                    source_id=None,
                    sensitivity="low",
                    occurred_at=clock.now(),
                )
            )
        fetched = outbox_adapter.fetch_unpublished(limit=10)
        timestamps = [e.occurred_at for e in fetched]
        assert timestamps == sorted(timestamps)

    def test_append_consent_granted(
        self, outbox_adapter: MemoryOutboxPort, clock: SystemClockAdapter
    ) -> None:
        from backend.memory.domain.model import ConsentGranted

        event = ConsentGranted(consent_id=ConsentId(), occurred_at=clock.now())
        outbox_adapter.append(event)
        fetched = outbox_adapter.fetch_unpublished(limit=10)
        assert len(fetched) == 1
        assert isinstance(fetched[0], ConsentGranted)

    def test_append_consent_revoked(
        self, outbox_adapter: MemoryOutboxPort, clock: SystemClockAdapter
    ) -> None:
        from backend.memory.domain.model import ConsentRevoked

        event = ConsentRevoked(consent_id=ConsentId(), occurred_at=clock.now())
        outbox_adapter.append(event)
        fetched = outbox_adapter.fetch_unpublished(limit=10)
        assert len(fetched) == 1
        assert isinstance(fetched[0], ConsentRevoked)

    def test_append_multiple_event_types(
        self,
        outbox_adapter: MemoryOutboxPort,
        clock: SystemClockAdapter,
        id_gen: UuidGeneratorAdapter,
    ) -> None:
        from backend.memory.domain.model import (
            MemoryCreated,
            MemoryDeleted,
            MemoryUpdated,
        )

        mid = id_gen.generate_memory_id()
        cid = ConsentId()
        outbox_adapter.append(
            MemoryCreated(mid, cid, MemoryCategory.GENERAL, "ui", None, "low", clock.now())
        )
        outbox_adapter.append(MemoryUpdated(mid, 1, clock.now()))
        outbox_adapter.append(MemoryDeleted(mid, 1, clock.now()))
        fetched = outbox_adapter.fetch_unpublished(limit=10)
        types = {type(e).__name__ for e in fetched}
        assert types == {"MemoryCreated", "MemoryUpdated", "MemoryDeleted"}


# ===================================================================
# Combined lifecycle integration tests
# ===================================================================


class TestFullLifecycleIntegration:
    def test_memory_save_and_retrieve(
        self, memory_repo: MemoryRepositoryPort, a_memory: Memory
    ) -> None:
        memory_repo.save(a_memory)
        found = memory_repo.find_by_id(a_memory.memory_id)
        assert found is not None
        assert found.content.value == "Integration test memory"

    def test_memory_soft_delete_workflow(
        self, memory_repo: MemoryRepositoryPort, a_memory: Memory
    ) -> None:
        memory_repo.save(a_memory)
        a_memory.delete()
        memory_repo.save(a_memory)
        found = memory_repo.find_by_id(a_memory.memory_id)
        assert found is not None
        assert found.is_deleted

    def test_consent_then_memory_then_outbox(
        self,
        memory_repo: MemoryRepositoryPort,
        consent_repo: ConsentRepositoryPort,
        outbox_adapter: MemoryOutboxPort,
        a_memory: Memory,
        a_consent: ConsentRecord,
        clock: SystemClockAdapter,
    ) -> None:
        from backend.memory.domain.model import MemoryCreated

        consent_repo.save(a_consent)
        memory_repo.save(a_memory)

        event = MemoryCreated(
            memory_id=a_memory.memory_id,
            consent_id=a_memory.consent_id,
            category=a_memory.category,
            source_type=a_memory.source_type,
            source_id=a_memory.source_id,
            sensitivity=a_memory.sensitivity,
            occurred_at=clock.now(),
        )
        outbox_adapter.append(event)

        stored_consent = consent_repo.find_by_id(a_consent.consent_id)
        assert stored_consent is not None

        stored_memory = memory_repo.find_by_id(a_memory.memory_id)
        assert stored_memory is not None

        unpublished = outbox_adapter.fetch_unpublished(limit=10)
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], MemoryCreated)

    def test_consent_grant_and_revoke(
        self, consent_repo: ConsentRepositoryPort, clock: SystemClockAdapter
    ) -> None:
        c = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.PROPOSED)
        c.grant()
        consent_repo.save(c)
        assert len(consent_repo.find_active()) == 1

        c.revoke()
        consent_repo.save(c)
        assert len(consent_repo.find_active()) == 0
        assert len(consent_repo.find_revoked()) == 1

    def test_empty_counts(
        self,
        memory_repo: MemoryRepositoryPort,
        consent_repo: ConsentRepositoryPort,
    ) -> None:
        assert memory_repo.count() == 0
        assert consent_repo.count() == 0

    def test_memory_deleted_visible_in_find_deleted(
        self, memory_repo: MemoryRepositoryPort, a_memory: Memory
    ) -> None:
        memory_repo.save(a_memory)
        a_memory.delete()
        memory_repo.save(a_memory)
        deleted = memory_repo.find_deleted()
        assert len(deleted) == 1
        assert deleted[0].memory_id == a_memory.memory_id

    def test_outbox_events_have_event_ids(
        self,
        outbox_adapter: MemoryOutboxPort,
        clock: SystemClockAdapter,
        id_gen: UuidGeneratorAdapter,
    ) -> None:
        from backend.memory.domain.model import MemoryCreated

        mid = id_gen.generate_memory_id()
        outbox_adapter.append(
            MemoryCreated(
                memory_id=mid,
                consent_id=ConsentId(),
                category=MemoryCategory.GENERAL,
                source_type="user_input",
                source_id=None,
                sensitivity="low",
                occurred_at=clock.now(),
            )
        )
        fetched = outbox_adapter.fetch_unpublished(limit=10)
        assert len(fetched) == 1
        assert hasattr(fetched[0], "memory_id")

    def test_mark_published_idempotent_multiple_calls(
        self,
        outbox_adapter: MemoryOutboxPort,
        clock: SystemClockAdapter,
        id_gen: UuidGeneratorAdapter,
    ) -> None:
        from backend.memory.domain.model import MemoryCreated

        mid = id_gen.generate_memory_id()
        outbox_adapter.append(
            MemoryCreated(
                memory_id=mid,
                consent_id=ConsentId(),
                category=MemoryCategory.GENERAL,
                source_type="user_input",
                source_id=None,
                sensitivity="low",
                occurred_at=clock.now(),
            )
        )
        fetched = outbox_adapter.fetch_unpublished(limit=10)
        outbox_adapter.mark_published(str(fetched[0].event_id))
        outbox_adapter.mark_published(str(fetched[0].event_id))
        outbox_adapter.mark_published(str(fetched[0].event_id))
        remaining = outbox_adapter.fetch_unpublished(limit=10)
        assert len(remaining) == 0

    def test_multiple_consents_independent(
        self, consent_repo: ConsentRepositoryPort, clock: SystemClockAdapter
    ) -> None:
        c1 = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.ACTIVE)
        c2 = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.ACTIVE)
        c3 = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.REVOKED)
        consent_repo.save(c1)
        consent_repo.save(c2)
        consent_repo.save(c3)
        assert consent_repo.count() == 3
        assert len(consent_repo.find_active()) == 2
        assert len(consent_repo.find_revoked()) == 1
