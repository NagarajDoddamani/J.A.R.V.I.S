from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.audit.adapters.outbound.clock import SystemClockAdapter
from backend.audit.adapters.outbound.id_generator import (
    UuidV7GeneratorAdapter,
)
from backend.audit.adapters.outbound.mappers import (
    AuditChainHeadMapperImpl,
    AuditEntryMapperImpl,
    AuditOutboxMapperImpl,
)
from backend.audit.adapters.outbound.repositories import (
    SqlAlchemyAuditChainHeadRepository,
    SqlAlchemyAuditEntryRepository,
    SqlAlchemyAuditOutboxRepository,
)
from backend.audit.domain.factory import AuditEntryFactory
from backend.audit.domain.model import (
    AuditChainHead,
    AuditEntry,
    AuditEntryId,
    AuditEntryRecorded,
    EntryHash,
)

# ===================================================================
# SQLite compatibility: strip schema qualifiers from ORM metadata
# ===================================================================

from backend.audit.adapters.outbound.models import (
    AuditChainHeadModel,
    AuditEntryModel,
    AuditOutboxModel,
    Base,
)

# SQLite does not support schema-qualified table names. Remove the
# schema from each table's metadata so ``create_all`` works.
for _table in Base.metadata.tables.values():
    _table.schema = None


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite://", echo=False)
    Base.metadata.create_all(e)
    return e


@pytest.fixture
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    s = Session(bind=connection)
    yield s
    s.close()
    transaction.rollback()
    connection.close()


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


class TestUuidV7GeneratorAdapter:
    def test_generate_returns_string(self) -> None:
        gen = UuidV7GeneratorAdapter()
        result = gen.generate()
        assert isinstance(result, str)

    def test_generates_valid_uuid(self) -> None:
        gen = UuidV7GeneratorAdapter()
        uid = UUID(gen.generate())
        assert uid.version in (4,)  # uuid4

    def test_unique(self) -> None:
        gen = UuidV7GeneratorAdapter()
        ids = {gen.generate() for _ in range(100)}
        assert len(ids) == 100


# ===================================================================
# Mapper implementation tests
# ===================================================================


class TestAuditEntryMapperImpl:
    @pytest.fixture
    def mapper(self) -> AuditEntryMapperImpl:
        return AuditEntryMapperImpl()

    def test_domain_to_dto(self, mapper: AuditEntryMapperImpl) -> None:
        entry, _ = AuditEntryFactory.create(
            chain_name="security",
            action="test.mapper",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-map-impl",
            result="success",
            actor_type="user",
            actor_id="alice",
            target_type="memory",
            target_ref="mem-001",
        )
        dto = mapper.domain_to_dto(entry)
        assert dto.entry_id == str(entry.entry_id)
        assert dto.chain_name == "security"
        assert dto.actor_type == "user"
        assert dto.actor_id == "alice"
        assert dto.target_type == "memory"
        assert dto.target_ref == "mem-001"
        assert dto.entry_hash == entry.entry_hash.value

    def test_dto_to_domain(self, mapper: AuditEntryMapperImpl) -> None:
        entry, _ = AuditEntryFactory.create(
            chain_name="roundtrip",
            action="verify.dto",
            policy_decision="deny",
            classification="sensitive",
            correlation_id="corr-dto",
            causation_id="cause-dto",
            result="denied",
            actor_type="agent",
            actor_id="jarvis",
            target_type="consent",
            target_ref="cons-001",
            redacted_reason="User revoked",
        )
        dto = mapper.domain_to_dto(entry)
        reconstructed = mapper.dto_to_domain(dto)
        assert str(reconstructed.entry_id) == str(entry.entry_id)
        assert reconstructed.chain_name == entry.chain_name
        assert reconstructed.actor.actor_type == entry.actor.actor_type
        assert reconstructed.actor.actor_id == entry.actor.actor_id
        assert reconstructed.action == entry.action
        assert reconstructed.target is not None
        assert reconstructed.target.target_type == entry.target.target_type
        assert reconstructed.target.target_ref == entry.target.target_ref
        assert reconstructed.policy_decision == entry.policy_decision
        assert reconstructed.classification == entry.classification
        assert reconstructed.correlation_id == entry.correlation_id
        assert reconstructed.causation_id == entry.causation_id
        assert reconstructed.result == entry.result
        assert reconstructed.redacted_reason == entry.redacted_reason
        assert reconstructed.entry_hash == entry.entry_hash
        assert reconstructed.entry_index == entry.entry_index
        assert reconstructed.state == entry.state

    def test_null_fields_roundtrip(
        self, mapper: AuditEntryMapperImpl
    ) -> None:
        entry, _ = AuditEntryFactory.create(
            chain_name="nulls",
            action="test.nulls",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-n",
            result="success",
            actor_type="service",
            actor_id=None,
        )
        dto = mapper.domain_to_dto(entry)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.actor.actor_id is None
        assert reconstructed.target is None
        assert reconstructed.previous_hash is None


class TestAuditChainHeadMapperImpl:
    def test_roundtrip(self) -> None:
        mapper = AuditChainHeadMapperImpl()
        head = AuditChainHead(
            chain_name="security",
            head_hash=EntryHash(value=b"\xab" * 32),
            entries_count=42,
        )
        dto = mapper.domain_to_dto(head)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.chain_name == "security"
        assert reconstructed.head_hash == head.head_hash
        assert reconstructed.entries_count == 42

    def test_null_hash_roundtrip(self) -> None:
        mapper = AuditChainHeadMapperImpl()
        head = AuditChainHead(
            chain_name="empty", head_hash=None, entries_count=0
        )
        dto = mapper.domain_to_dto(head)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.head_hash is None
        assert reconstructed.entries_count == 0


class TestAuditOutboxMapperImpl:
    def test_roundtrip(self) -> None:
        mapper = AuditOutboxMapperImpl()
        _, event = AuditEntryFactory.create(
            chain_name="outbox-map",
            action="test.event",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-ob-map",
            result="success",
            actor_type="user",
            actor_id="alice",
        )
        dto = mapper.event_to_dto(event)
        reconstructed = mapper.dto_to_event(dto)
        assert str(reconstructed.entry_id) == str(event.entry_id)
        assert reconstructed.chain_name == event.chain_name
        assert reconstructed.action == event.action
        assert reconstructed.actor_type == event.actor_type
        assert reconstructed.correlation_id == event.correlation_id
        assert reconstructed.entry_index == event.entry_index


# ===================================================================
# Repository contract compliance tests
# ===================================================================


class TestSqlAlchemyAuditEntryRepository:
    @pytest.fixture
    def repo(self, session: Session) -> SqlAlchemyAuditEntryRepository:
        return SqlAlchemyAuditEntryRepository(session)

    def test_save_and_find_by_id(
        self, repo: SqlAlchemyAuditEntryRepository
    ) -> None:
        entry, _ = AuditEntryFactory.create(
            chain_name="security",
            action="save.and.find",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-sf",
            result="success",
            actor_type="user",
            actor_id="alice",
        )
        repo.save(entry)
        found = repo.find_by_id(entry.entry_id)
        assert found is not None
        assert str(found.entry_id) == str(entry.entry_id)
        assert found.chain_name == "security"
        assert found.action == "save.and.find"

    def test_find_by_id_nonexistent(
        self, repo: SqlAlchemyAuditEntryRepository
    ) -> None:
        missing = AuditEntryId()
        assert repo.find_by_id(missing) is None

    def test_find_by_chain(
        self, repo: SqlAlchemyAuditEntryRepository
    ) -> None:
        e1, _ = AuditEntryFactory.create(
            chain_name="chain-r",
            action="first",
            policy_decision="grant",
            classification="public",
            correlation_id="c1",
            result="ok",
            actor_type="user",
            actor_id="alice",
        )
        e2, _ = AuditEntryFactory.create(
            chain_name="chain-r",
            action="second",
            policy_decision="deny",
            classification="sensitive",
            correlation_id="c2",
            result="denied",
            actor_type="agent",
            actor_id="jarvis",
            previous_entry_hash=e1.entry_hash.value,
            previous_entry_index=e1.entry_index.value,
        )
        repo.save(e1)
        repo.save(e2)

        results = repo.find_by_chain("chain-r")
        assert len(results) == 2
        assert results[0].entry_index.value == 0
        assert results[1].entry_index.value == 1

    def test_find_by_chain_pagination(
        self, repo: SqlAlchemyAuditEntryRepository
    ) -> None:
        entries = []
        for i in range(10):
            e, _ = AuditEntryFactory.create(
                chain_name="chain-page",
                action=f"step.{i}",
                policy_decision="grant",
                classification="public",
                correlation_id=f"cp{i}",
                result="ok",
                actor_type="user",
                actor_id="alice",
                previous_entry_hash=(
                    entries[-1].entry_hash.value if entries else None
                ),
                previous_entry_index=(
                    entries[-1].entry_index.value if entries else None
                ),
            )
            entries.append(e)
            repo.save(e)

        page = repo.find_by_chain("chain-page", limit=3, offset=5)
        assert len(page) == 3
        assert page[0].entry_index.value == 5
        assert page[2].entry_index.value == 7

    def test_find_by_correlation_id(
        self, repo: SqlAlchemyAuditEntryRepository
    ) -> None:
        e1, _ = AuditEntryFactory.create(
            chain_name="sys",
            action="a",
            policy_decision="grant",
            classification="public",
            correlation_id="shared-id",
            result="ok",
            actor_type="user",
            actor_id="alice",
        )
        e2, _ = AuditEntryFactory.create(
            chain_name="consent",
            action="b",
            policy_decision="grant",
            classification="public",
            correlation_id="shared-id",
            result="ok",
            actor_type="user",
            actor_id="bob",
        )
        e3, _ = AuditEntryFactory.create(
            chain_name="sys",
            action="c",
            policy_decision="grant",
            classification="public",
            correlation_id="other-id",
            result="ok",
            actor_type="user",
            actor_id="alice",
        )
        repo.save(e1)
        repo.save(e2)
        repo.save(e3)

        results = repo.find_by_correlation_id("shared-id")
        assert len(results) == 2
        assert all(r.correlation_id == "shared-id" for r in results)

    def test_count_by_chain(
        self, repo: SqlAlchemyAuditEntryRepository
    ) -> None:
        entries = []
        for i in range(4):
            e, _ = AuditEntryFactory.create(
                chain_name="count-chain",
                action=f"c.{i}",
                policy_decision="grant",
                classification="public",
                correlation_id=f"cc{i}",
                result="ok",
                actor_type="user",
                actor_id="alice",
                previous_entry_hash=(
                    entries[-1].entry_hash.value if entries else None
                ),
                previous_entry_index=(
                    entries[-1].entry_index.value if entries else None
                ),
            )
            entries.append(e)
            repo.save(e)

        assert repo.count_by_chain("count-chain") == 4
        assert repo.count_by_chain("nonexistent") == 0


class TestSqlAlchemyAuditChainHeadRepository:
    @pytest.fixture
    def repo(
        self, session: Session
    ) -> SqlAlchemyAuditChainHeadRepository:
        return SqlAlchemyAuditChainHeadRepository(session)

    def test_save_and_find_by_chain(
        self, repo: SqlAlchemyAuditChainHeadRepository
    ) -> None:
        head = AuditChainHead(
            chain_name="security",
            head_hash=EntryHash(value=b"\xaa" * 32),
            entries_count=10,
        )
        repo.save(head)
        found = repo.find_by_chain("security")
        assert found is not None
        assert found.chain_name == "security"
        assert found.head_hash == EntryHash(value=b"\xaa" * 32)
        assert found.entries_count == 10

    def test_find_by_chain_nonexistent(
        self, repo: SqlAlchemyAuditChainHeadRepository
    ) -> None:
        assert repo.find_by_chain("nonexistent") is None

    def test_upsert(
        self, repo: SqlAlchemyAuditChainHeadRepository
    ) -> None:
        head = AuditChainHead(
            chain_name="policy",
            head_hash=EntryHash(value=b"\xbb" * 32),
            entries_count=5,
        )
        repo.save(head)

        updated = AuditChainHead(
            chain_name="policy",
            head_hash=EntryHash(value=b"\xcc" * 32),
            entries_count=6,
        )
        repo.save(updated)

        found = repo.find_by_chain("policy")
        assert found is not None
        assert found.entries_count == 6
        assert found.head_hash == EntryHash(value=b"\xcc" * 32)

    def test_find_all(
        self, repo: SqlAlchemyAuditChainHeadRepository
    ) -> None:
        repo.save(
            AuditChainHead(
                chain_name="a", head_hash=EntryHash(value=b"\x01" * 32), entries_count=1
            )
        )
        repo.save(
            AuditChainHead(
                chain_name="b", head_hash=EntryHash(value=b"\x02" * 32), entries_count=2
            )
        )
        all_heads = repo.find_all()
        assert len(all_heads) == 2
        names = {h.chain_name for h in all_heads}
        assert names == {"a", "b"}


class TestSqlAlchemyAuditOutboxRepository:
    @pytest.fixture
    def repo(
        self, session: Session
    ) -> SqlAlchemyAuditOutboxRepository:
        return SqlAlchemyAuditOutboxRepository(session)

    def test_append_and_fetch_unpublished(
        self, repo: SqlAlchemyAuditOutboxRepository
    ) -> None:
        _, event = AuditEntryFactory.create(
            chain_name="outbox-test",
            action="append.test",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-ob",
            result="ok",
            actor_type="user",
            actor_id="alice",
        )
        repo.append(event)
        unpublished = repo.fetch_unpublished()
        assert len(unpublished) == 1
        assert str(unpublished[0].entry_id) == str(event.entry_id)

    def test_mark_published(
        self, repo: SqlAlchemyAuditOutboxRepository
    ) -> None:
        _, event = AuditEntryFactory.create(
            chain_name="pub-test",
            action="publish.me",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-pub",
            result="ok",
            actor_type="user",
            actor_id="alice",
        )
        repo.append(event)
        unpublished = repo.fetch_unpublished()
        repo.mark_published(str(unpublished[0].event_id))
        unpublished = repo.fetch_unpublished()
        assert len(unpublished) == 0

    def test_fetch_respects_limit(
        self, repo: SqlAlchemyAuditOutboxRepository
    ) -> None:
        for i in range(5):
            _, event = AuditEntryFactory.create(
                chain_name="limit-test",
                action=f"evt.{i}",
                policy_decision="grant",
                classification="public",
                correlation_id=f"corr-l{i}",
                result="ok",
                actor_type="user",
                actor_id="alice",
            )
            repo.append(event)

        fetched = repo.fetch_unpublished(limit=3)
        assert len(fetched) == 3

    def test_partial_publish(
        self, repo: SqlAlchemyAuditOutboxRepository
    ) -> None:
        events = []
        for i in range(3):
            _, event = AuditEntryFactory.create(
                chain_name="partial",
                action=f"evt.{i}",
                policy_decision="grant",
                classification="public",
                correlation_id=f"corr-{i}",
                result="ok",
                actor_type="user",
                actor_id="alice",
            )
            events.append(event)
            repo.append(event)

        unpublished = repo.fetch_unpublished()
        repo.mark_published(str(unpublished[0].event_id))
        repo.mark_published(str(unpublished[1].event_id))

        unpublished = repo.fetch_unpublished()
        assert len(unpublished) == 1
        assert str(unpublished[0].entry_id) == str(events[2].entry_id)


# ===================================================================
# Full-stack integration: Domain → Port → Adapter
# ===================================================================


class TestAdapterIntegration:
    """End-to-end: Use Case → Repository Adapter → SQLite."""

    def test_record_then_query(
        self, session: Session
    ) -> None:
        entry_repo = SqlAlchemyAuditEntryRepository(session)
        chain_head_repo = SqlAlchemyAuditChainHeadRepository(session)
        outbox = SqlAlchemyAuditOutboxRepository(session)

        # Use factory directly (simulating use case flow)
        entry, event = AuditEntryFactory.create(
            chain_name="integration",
            action="full.stack",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-full",
            result="success",
            actor_type="user",
            actor_id="alice",
        )

        entry_repo.save(entry)
        chain_head_repo.save(
            AuditChainHead(
                chain_name="integration",
                head_hash=entry.entry_hash,
                entries_count=1,
            )
        )
        outbox.append(event)

        # Verify persistence
        found = entry_repo.find_by_id(entry.entry_id)
        assert found is not None
        assert found.action == "full.stack"

        head = chain_head_repo.find_by_chain("integration")
        assert head is not None
        assert head.entries_count == 1

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert str(unpublished[0].entry_id) == str(entry.entry_id)
