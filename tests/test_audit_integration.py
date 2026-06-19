from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.audit.adapters.outbound.clock import SystemClockAdapter
from backend.audit.adapters.outbound.id_generator import UuidV7GeneratorAdapter
from backend.audit.adapters.outbound.mappers import AuditEntryMapperImpl
from backend.audit.adapters.outbound.models import (
    AuditChainHeadModel,
    AuditEntryModel,
    AuditOutboxModel,
    Base,
)
from backend.audit.adapters.outbound.repositories import (
    SqlAlchemyAuditChainHeadRepository,
    SqlAlchemyAuditEntryRepository,
    SqlAlchemyAuditOutboxRepository,
)
from backend.audit.application.use_cases.dto import (
    GetAuditChainHeadRequest,
    GetAuditChainRequest,
    GetAuditEntriesByCorrelationRequest,
    GetAuditEntryRequest,
    RecordAuditEntryRequest,
)
from backend.audit.application.use_cases.get_by_correlation import (
    GetAuditEntriesByCorrelationUseCase,
)
from backend.audit.application.use_cases.get_chain import GetAuditChainUseCase
from backend.audit.application.use_cases.get_chain_head import (
    GetAuditChainHeadUseCase,
)
from backend.audit.application.use_cases.get_entry import GetAuditEntryUseCase
from backend.audit.application.use_cases.record_entry import (
    RecordAuditEntryUseCase,
)
from backend.audit.domain.exceptions import AuditDomainError
from backend.audit.domain.factory import AuditEntryFactory
from backend.audit.domain.model import AuditChainHead, AuditEntryId, EntryHash
from backend.audit.nats import publish_outbox_events

# Strip schema for SQLite compatibility
for _table in Base.metadata.tables.values():
    _table.schema = None


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite://", echo=False)
    Base.metadata.create_all(bind=e)
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


@pytest.fixture
def entry_repo(session: Session) -> SqlAlchemyAuditEntryRepository:
    return SqlAlchemyAuditEntryRepository(session)


@pytest.fixture
def chain_head_repo(session: Session) -> SqlAlchemyAuditChainHeadRepository:
    return SqlAlchemyAuditChainHeadRepository(session)


@pytest.fixture
def outbox_repo(session: Session) -> SqlAlchemyAuditOutboxRepository:
    return SqlAlchemyAuditOutboxRepository(session)


@pytest.fixture
def clock() -> SystemClockAdapter:
    return SystemClockAdapter()


@pytest.fixture
def id_generator() -> UuidV7GeneratorAdapter:
    return UuidV7GeneratorAdapter()


# ===================================================================
# Use case → repository → SQLite round-trip
# ===================================================================


class TestRecordAuditEntryUseCaseIntegration:
    def test_record_and_retrieve(
        self,
        entry_repo: SqlAlchemyAuditEntryRepository,
        chain_head_repo: SqlAlchemyAuditChainHeadRepository,
        outbox_repo: SqlAlchemyAuditOutboxRepository,
        clock: SystemClockAdapter,
        id_generator: UuidV7GeneratorAdapter,
        session: Session,
    ) -> None:
        use_case = RecordAuditEntryUseCase(
            entry_repo=entry_repo,
            chain_head_repo=chain_head_repo,
            outbox=outbox_repo,
            clock=clock,
            id_generator=id_generator,
        )

        request = RecordAuditEntryRequest(
            chain_name="int-record",
            action="integration.test",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-int-record",
            result="success",
            actor_type="user",
            actor_id="alice",
        )
        response = use_case.execute(request)
        session.commit()

        get_use_case = GetAuditEntryUseCase(entry_repo=entry_repo)
        found = get_use_case.execute(
            GetAuditEntryRequest(entry_id=response.entry_id)
        )
        assert found.action == "integration.test"
        assert found.chain_name == "int-record"
        assert found.entry_index == 0

    def test_chain_linking(
        self,
        entry_repo: SqlAlchemyAuditEntryRepository,
        chain_head_repo: SqlAlchemyAuditChainHeadRepository,
        outbox_repo: SqlAlchemyAuditOutboxRepository,
        clock: SystemClockAdapter,
        id_generator: UuidV7GeneratorAdapter,
        session: Session,
    ) -> None:
        use_case = RecordAuditEntryUseCase(
            entry_repo=entry_repo,
            chain_head_repo=chain_head_repo,
            outbox=outbox_repo,
            clock=clock,
            id_generator=id_generator,
        )

        r1 = use_case.execute(
            RecordAuditEntryRequest(
                chain_name="linking",
                action="first",
                policy_decision="grant",
                classification="public",
                correlation_id="link-1",
                result="success",
                actor_type="user",
            )
        )
        session.commit()

        r2 = use_case.execute(
            RecordAuditEntryRequest(
                chain_name="linking",
                action="second",
                policy_decision="deny",
                classification="sensitive",
                correlation_id="link-2",
                result="denied",
                actor_type="agent",
                actor_id="jarvis",
            )
        )
        session.commit()

        chain_use_case = GetAuditChainUseCase(entry_repo=entry_repo)
        chain = chain_use_case.execute(
            GetAuditChainRequest(chain_name="linking")
        )
        assert len(chain.entries) == 2
        assert chain.entries[0].entry_index == 0
        assert chain.entries[1].entry_index == 1
        assert chain.entries[1].previous_hash_hex == chain.entries[0].entry_hash_hex

    def test_chain_head_tracking(
        self,
        entry_repo: SqlAlchemyAuditEntryRepository,
        chain_head_repo: SqlAlchemyAuditChainHeadRepository,
        outbox_repo: SqlAlchemyAuditOutboxRepository,
        clock: SystemClockAdapter,
        id_generator: UuidV7GeneratorAdapter,
        session: Session,
    ) -> None:
        use_case = RecordAuditEntryUseCase(
            entry_repo=entry_repo,
            chain_head_repo=chain_head_repo,
            outbox=outbox_repo,
            clock=clock,
            id_generator=id_generator,
        )

        for i in range(5):
            use_case.execute(
                RecordAuditEntryRequest(
                    chain_name="head-track",
                    action=f"step.{i}",
                    policy_decision="grant",
                    classification="public",
                    correlation_id=f"ht-{i}",
                    result="success",
                    actor_type="user",
                )
            )
            session.commit()

        head_use_case = GetAuditChainHeadUseCase(
            chain_head_repo=chain_head_repo
        )
        head = head_use_case.execute(
            GetAuditChainHeadRequest(chain_name="head-track")
        )
        assert head.entries_count == 5
        assert isinstance(head.head_hash_hex, str)
        assert len(head.head_hash_hex) == 64  # SHA-256 hex


class TestGetAuditEntryUseCaseIntegration:
    def test_nonexistent_raises(
        self,
        entry_repo: SqlAlchemyAuditEntryRepository,
    ) -> None:
        import uuid

        use_case = GetAuditEntryUseCase(entry_repo=entry_repo)
        from backend.audit.application.use_cases.exceptions import (
            AuditEntryNotFoundError,
        )

        with pytest.raises(AuditEntryNotFoundError):
            use_case.execute(
                GetAuditEntryRequest(entry_id=str(uuid.uuid4()))
            )


class TestGetChainUseCaseIntegration:
    def test_pagination(
        self,
        entry_repo: SqlAlchemyAuditEntryRepository,
        chain_head_repo: SqlAlchemyAuditChainHeadRepository,
        outbox_repo: SqlAlchemyAuditOutboxRepository,
        clock: SystemClockAdapter,
        id_generator: UuidV7GeneratorAdapter,
        session: Session,
    ) -> None:
        use_case = RecordAuditEntryUseCase(
            entry_repo=entry_repo,
            chain_head_repo=chain_head_repo,
            outbox=outbox_repo,
            clock=clock,
            id_generator=id_generator,
        )
        for i in range(10):
            use_case.execute(
                RecordAuditEntryRequest(
                    chain_name="page-chain",
                    action=f"step.{i}",
                    policy_decision="grant",
                    classification="public",
                    correlation_id=f"pg-{i}",
                    result="success",
                    actor_type="user",
                )
            )
            session.commit()

        chain_use_case = GetAuditChainUseCase(entry_repo=entry_repo)
        result = chain_use_case.execute(
            GetAuditChainRequest(
                chain_name="page-chain", limit=3, offset=7
            )
        )
        assert len(result.entries) == 3
        assert result.entries[0].entry_index == 7
        assert result.total == 10


class TestGetByCorrelationUseCaseIntegration:
    def test_cross_chain_correlation(
        self,
        entry_repo: SqlAlchemyAuditEntryRepository,
        chain_head_repo: SqlAlchemyAuditChainHeadRepository,
        outbox_repo: SqlAlchemyAuditOutboxRepository,
        clock: SystemClockAdapter,
        id_generator: UuidV7GeneratorAdapter,
        session: Session,
    ) -> None:
        use_case = RecordAuditEntryUseCase(
            entry_repo=entry_repo,
            chain_head_repo=chain_head_repo,
            outbox=outbox_repo,
            clock=clock,
            id_generator=id_generator,
        )
        cid = "shared-correlation"
        for chain in ("chain-a", "chain-b", "chain-c"):
            use_case.execute(
                RecordAuditEntryRequest(
                    chain_name=chain,
                    action=f"evt.{chain}",
                    policy_decision="grant",
                    classification="public",
                    correlation_id=cid,
                    result="success",
                    actor_type="user",
                )
            )
            session.commit()

        corr_use_case = GetAuditEntriesByCorrelationUseCase(
            entry_repo=entry_repo
        )
        result = corr_use_case.execute(
            GetAuditEntriesByCorrelationRequest(correlation_id=cid)
        )
        assert len(result.entries) == 3
        chains = {e.chain_name for e in result.entries}
        assert chains == {"chain-a", "chain-b", "chain-c"}


# ===================================================================
# Outbox persistence
# ===================================================================


class TestOutboxPersistence:
    def test_append_and_fetch_unpublished(
        self,
        entry_repo: SqlAlchemyAuditEntryRepository,
        chain_head_repo: SqlAlchemyAuditChainHeadRepository,
        outbox_repo: SqlAlchemyAuditOutboxRepository,
        clock: SystemClockAdapter,
        id_generator: UuidV7GeneratorAdapter,
        session: Session,
    ) -> None:
        use_case = RecordAuditEntryUseCase(
            entry_repo=entry_repo,
            chain_head_repo=chain_head_repo,
            outbox=outbox_repo,
            clock=clock,
            id_generator=id_generator,
        )
        use_case.execute(
            RecordAuditEntryRequest(
                chain_name="ob-test",
                action="ob.action",
                policy_decision="grant",
                classification="public",
                correlation_id="ob-1",
                result="success",
                actor_type="user",
            )
        )
        session.commit()

        unpublished = outbox_repo.fetch_unpublished()
        assert len(unpublished) == 1

    def test_mark_published(
        self,
        entry_repo: SqlAlchemyAuditEntryRepository,
        chain_head_repo: SqlAlchemyAuditChainHeadRepository,
        outbox_repo: SqlAlchemyAuditOutboxRepository,
        clock: SystemClockAdapter,
        id_generator: UuidV7GeneratorAdapter,
        session: Session,
    ) -> None:
        use_case = RecordAuditEntryUseCase(
            entry_repo=entry_repo,
            chain_head_repo=chain_head_repo,
            outbox=outbox_repo,
            clock=clock,
            id_generator=id_generator,
        )
        response = use_case.execute(
            RecordAuditEntryRequest(
                chain_name="ob-pub",
                action="ob.publish",
                policy_decision="grant",
                classification="public",
                correlation_id="ob-pub-1",
                result="success",
                actor_type="user",
            )
        )
        session.commit()

        unpublished_before = outbox_repo.fetch_unpublished()
        outbox_repo.mark_published(str(unpublished_before[0].event_id))
        unpublished = outbox_repo.fetch_unpublished()
        assert len(unpublished) == 0

    def test_multiple_events_fifo(
        self,
        entry_repo: SqlAlchemyAuditEntryRepository,
        chain_head_repo: SqlAlchemyAuditChainHeadRepository,
        outbox_repo: SqlAlchemyAuditOutboxRepository,
        clock: SystemClockAdapter,
        id_generator: UuidV7GeneratorAdapter,
        session: Session,
    ) -> None:
        use_case = RecordAuditEntryUseCase(
            entry_repo=entry_repo,
            chain_head_repo=chain_head_repo,
            outbox=outbox_repo,
            clock=clock,
            id_generator=id_generator,
        )
        for i in range(3):
            use_case.execute(
                RecordAuditEntryRequest(
                    chain_name="ob-fifo",
                    action=f"evt.{i}",
                    policy_decision="grant",
                    classification="public",
                    correlation_id=f"ob-fifo-{i}",
                    result="success",
                    actor_type="user",
                )
            )
            session.commit()

        unpublished = outbox_repo.fetch_unpublished(limit=2)
        assert len(unpublished) == 2

        outbox_repo.mark_published(str(unpublished[0].event_id))
        remaining = outbox_repo.fetch_unpublished()
        assert len(remaining) == 2  # only one was published


# ===================================================================
# Rollback behavior
# ===================================================================


class TestRollbackBehavior:
    def test_domain_rule_violation_does_not_persist(
        self,
        session: Session,
    ) -> None:
        with pytest.raises(AuditDomainError):
            AuditEntryFactory.create(
                chain_name="rollback",
                action="test.bad",
                policy_decision="grant",
                classification="invalid-bad-value",
                correlation_id="rb-1",
                result="success",
                actor_type="user",
                actor_id="alice",
            )

        remaining = session.query(AuditEntryModel).count()
        assert remaining == 0

    def test_domain_rule_violation_no_side_effects(
        self,
        entry_repo: SqlAlchemyAuditEntryRepository,
        chain_head_repo: SqlAlchemyAuditChainHeadRepository,
        outbox_repo: SqlAlchemyAuditOutboxRepository,
        clock: SystemClockAdapter,
        id_generator: UuidV7GeneratorAdapter,
        session: Session,
    ) -> None:
        use_case = RecordAuditEntryUseCase(
            entry_repo=entry_repo,
            chain_head_repo=chain_head_repo,
            outbox=outbox_repo,
            clock=clock,
            id_generator=id_generator,
        )

        with pytest.raises(AuditDomainError):
            use_case.execute(
                RecordAuditEntryRequest(
                    chain_name="rollback-2",
                    action="test.bad2",
                    policy_decision="invalid-decision",
                    classification="public",
                    correlation_id="rb-2",
                    result="success",
                    actor_type="user",
                    actor_id="alice",
                )
            )

        assert session.query(AuditEntryModel).count() == 0
        assert session.query(AuditChainHeadModel).count() == 0
        assert session.query(AuditOutboxModel).count() == 0


# ===================================================================
# NATS outbox publisher
# ===================================================================


class TestNatsOutboxPublisher:
    @pytest.fixture
    def nats_session(self, engine):
        connection = engine.connect()
        transaction = connection.begin()
        s = Session(bind=connection)
        yield s
        s.close()
        transaction.rollback()
        connection.close()

    @pytest.fixture
    def nats_entry_repo(self, nats_session: Session) -> SqlAlchemyAuditEntryRepository:
        return SqlAlchemyAuditEntryRepository(nats_session)

    @pytest.fixture
    def nats_chain_head_repo(self, nats_session: Session) -> SqlAlchemyAuditChainHeadRepository:
        return SqlAlchemyAuditChainHeadRepository(nats_session)

    @pytest.fixture
    def nats_outbox_repo(self, nats_session: Session) -> SqlAlchemyAuditOutboxRepository:
        return SqlAlchemyAuditOutboxRepository(nats_session)

    @pytest.mark.asyncio
    async def test_publishes_events_and_marks_published(
        self,
        nats_entry_repo: SqlAlchemyAuditEntryRepository,
        nats_chain_head_repo: SqlAlchemyAuditChainHeadRepository,
        nats_outbox_repo: SqlAlchemyAuditOutboxRepository,
        nats_session: Session,
    ) -> None:
        clock = SystemClockAdapter()
        id_generator = UuidV7GeneratorAdapter()
        use_case = RecordAuditEntryUseCase(
            entry_repo=nats_entry_repo,
            chain_head_repo=nats_chain_head_repo,
            outbox=nats_outbox_repo,
            clock=clock,
            id_generator=id_generator,
        )
        use_case.execute(
            RecordAuditEntryRequest(
                chain_name="nats-pub",
                action="nats.test",
                policy_decision="grant",
                classification="public",
                correlation_id="nats-1",
                result="success",
                actor_type="user",
            )
        )
        nats_session.commit()

        mock_js = MagicMock(spec_set=["publish"])
        mock_js.publish = AsyncMock()

        await publish_outbox_events(
            mock_js,
            outbox=nats_outbox_repo,
            batch=10,
            interval_seconds=9999,
            max_iterations=1,
        )

        mock_js.publish.assert_awaited_once()
        call_args = mock_js.publish.await_args
        assert call_args is not None
        subject = call_args.args[0]
        payload = call_args.args[1]
        assert subject == "jarvis.audit.signal.nats-pub.v1"
        assert b"AUDIT_ENTRY_RECORDED" in payload

        remaining = nats_outbox_repo.fetch_unpublished()
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_empty_outbox_no_publish(
        self,
        nats_outbox_repo: SqlAlchemyAuditOutboxRepository,
    ) -> None:
        mock_js = MagicMock(spec_set=["publish"])
        mock_js.publish = AsyncMock()

        await publish_outbox_events(
            mock_js,
            outbox=nats_outbox_repo,
            batch=10,
            interval_seconds=9999,
            max_iterations=1,
        )

        mock_js.publish.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_nats_failure_does_not_mark_published(
        self,
        nats_entry_repo: SqlAlchemyAuditEntryRepository,
        nats_chain_head_repo: SqlAlchemyAuditChainHeadRepository,
        nats_outbox_repo: SqlAlchemyAuditOutboxRepository,
        nats_session: Session,
    ) -> None:
        clock = SystemClockAdapter()
        id_generator = UuidV7GeneratorAdapter()
        use_case = RecordAuditEntryUseCase(
            entry_repo=nats_entry_repo,
            chain_head_repo=nats_chain_head_repo,
            outbox=nats_outbox_repo,
            clock=clock,
            id_generator=id_generator,
        )
        use_case.execute(
            RecordAuditEntryRequest(
                chain_name="nats-fail",
                action="nats.fail",
                policy_decision="grant",
                classification="public",
                correlation_id="nats-fail-1",
                result="success",
                actor_type="user",
            )
        )
        nats_session.commit()

        mock_js = MagicMock(spec_set=["publish"])
        mock_js.publish = AsyncMock(side_effect=RuntimeError("NATS down"))

        await publish_outbox_events(
            mock_js,
            outbox=nats_outbox_repo,
            batch=10,
            interval_seconds=9999,
            max_iterations=1,
        )

        remaining = nats_outbox_repo.fetch_unpublished()
        assert len(remaining) == 1


# ===================================================================
# Clock and ID generator
# ===================================================================


class TestSystemClockAdapter:
    def test_now_returns_utc(self) -> None:
        clock = SystemClockAdapter()
        now = clock.now()
        assert now.tzinfo is not None
        assert now.tzinfo.utcoffset(now).total_seconds() == 0.0

    def test_now_returns_datetime(self) -> None:
        clock = SystemClockAdapter()
        assert isinstance(clock.now(), datetime)


class TestUuidV7GeneratorAdapter:
    def test_generates_string(self) -> None:
        gen = UuidV7GeneratorAdapter()
        assert isinstance(gen.generate(), str)

    def test_generates_valid_uuid(self) -> None:
        gen = UuidV7GeneratorAdapter()
        uid = UUID(gen.generate())
        assert uid.version in (4,)

    def test_unique(self) -> None:
        gen = UuidV7GeneratorAdapter()
        ids = {gen.generate() for _ in range(100)}
        assert len(ids) == 100
