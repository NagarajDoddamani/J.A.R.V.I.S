from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.knowledge.adapters.outbound.clock import SystemClockAdapter
from backend.knowledge.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.knowledge.adapters.outbound.mapper import (
    KnowledgeSourceMapperImpl,
)
from backend.knowledge.adapters.outbound.models import Base
from backend.knowledge.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyKnowledgeOutboxAdapter,
    SqlAlchemyKnowledgeSourceRepository,
)
from backend.knowledge.application.use_cases.dto import (
    RegisterSourceRequest,
)
from backend.knowledge.application.use_cases.register_source import (
    RegisterSourceUseCase,
)
from backend.knowledge.domain.model import (
    ChunkCreated,
    ChunkId,
    ChunkIndex,
    DocumentChecksum,
    DocumentDeleted,
    DocumentId,
    DocumentIndexed,
    DocumentIngested,
    IngestionCompleted,
    IngestionFailed,
    IngestionJobId,
    IngestionStarted,
    KnowledgeSourceDeleted,
    KnowledgeSourceId,
    KnowledgeSourceRegistered,
    ReindexRequested,
    SourceLocation,
    SourceType,
)
from backend.knowledge.nats import (
    KnowledgeOutboxEvent,
    publish_knowledge_outbox_events,
)

for _table in Base.metadata.tables.values():
    _table.schema = None


@pytest.fixture
def session():
    e = create_engine("sqlite://", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    conn = e.connect()
    transaction = conn.begin()
    s = Session(bind=conn)
    yield s
    s.close()
    transaction.rollback()
    conn.close()
    e.dispose()


@pytest.fixture
def outbox(session):
    return SqlAlchemyKnowledgeOutboxAdapter(session)


@pytest.fixture
def clock():
    return SystemClockAdapter()


@pytest.fixture
def mock_js():
    js = AsyncMock()
    js.publish = AsyncMock()
    return js


def _add_source_outbox_entries(session, count: int = 3):
    outbox = SqlAlchemyKnowledgeOutboxAdapter(session)
    clock = SystemClockAdapter()
    mapper = KnowledgeSourceMapperImpl()
    source_repo = SqlAlchemyKnowledgeSourceRepository(session, mapper=mapper)
    id_gen = UuidGeneratorAdapter()

    uc = RegisterSourceUseCase(
        source_repo=source_repo,
        outbox=outbox,
        clock=clock,
        id_generator=id_gen,
    )
    for i in range(count):
        uc.execute(
            RegisterSourceRequest(
                name=f"Source {i}",
                source_type="file",
                location=f"/tmp/{i}",
                classification="public",
            )
        )
    session.commit()
    return outbox


def add_simple_outbox_entries(session, count: int = 3):
    outbox = SqlAlchemyKnowledgeOutboxAdapter(session)
    for i in range(count):
        event = KnowledgeSourceRegistered(
            source_id=KnowledgeSourceId(),
            name=f"Source {i}",
            source_type=SourceType.FILE,
            location=SourceLocation(value=f"/tmp/{i}"),
            classification="public",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
    session.commit()
    return outbox


class TestPublishKnowledgeOutboxEvents:
    @pytest.mark.asyncio
    async def test_publishes_all_events(self, session, mock_js) -> None:
        add_simple_outbox_entries(session, count=2)
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        assert mock_js.publish.await_count == 2

    @pytest.mark.asyncio
    async def test_marks_events_published(self, session, mock_js) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_no_events_no_publish(self, session, mock_js) -> None:
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        mock_js.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_respects_limit(self, session, mock_js) -> None:
        add_simple_outbox_entries(session, count=5)
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=2,
            interval_seconds=0.01,
            max_iterations=1,
        )

        assert mock_js.publish.await_count == 2

    @pytest.mark.asyncio
    async def test_publish_called_with_correct_subject(
        self, session, mock_js
    ) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject.startswith("jarvis.event.knowledge.")

    @pytest.mark.asyncio
    async def test_payload_is_json_bytes(
        self, session, mock_js
    ) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        payload = mock_js.publish.await_args[0][1]
        assert isinstance(payload, bytes)

    @pytest.mark.asyncio
    async def test_payload_contains_envelope_fields(
        self, session, mock_js
    ) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        import json
        payload = json.loads(mock_js.publish.await_args[0][1])
        assert "event_id" in payload
        assert "event_type" in payload
        assert "kind" in payload
        assert payload["kind"] == "event"
        assert "producer" in payload
        assert payload["producer"] == "knowledge"

    @pytest.mark.asyncio
    async def test_source_registered_event_type(
        self, session, mock_js
    ) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        import json
        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["event_type"] == "KNOWLEDGE_SOURCE_REGISTERED"
        assert "name" in payload
        assert "source_type" in payload
        assert "location" in payload
        assert "classification" in payload

    @pytest.mark.asyncio
    async def test_subject_for_source_registered(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)
        event = KnowledgeSourceRegistered(
            source_id=KnowledgeSourceId(),
            name="Test",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"),
            classification="public",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.knowledge.source_registered.v1"

    @pytest.mark.asyncio
    async def test_subject_for_source_deleted(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)
        event = KnowledgeSourceDeleted(
            source_id=KnowledgeSourceId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.knowledge.source_deleted.v1"

    @pytest.mark.asyncio
    async def test_subject_for_document_ingested(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)
        event = DocumentIngested(
            document_id=DocumentId(),
            source_id=KnowledgeSourceId(),
            title="Test",
            checksum=DocumentChecksum(value="abc"),
            classification="public",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.knowledge.document_ingested.v1"

    @pytest.mark.asyncio
    async def test_subject_for_document_indexed(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)
        event = DocumentIndexed(
            document_id=DocumentId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.knowledge.document_indexed.v1"

    @pytest.mark.asyncio
    async def test_subject_for_document_deleted(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)
        event = DocumentDeleted(
            document_id=DocumentId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.knowledge.document_deleted.v1"

    @pytest.mark.asyncio
    async def test_subject_for_chunk_created(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)
        event = ChunkCreated(
            chunk_id=ChunkId(),
            document_id=DocumentId(),
            chunk_index=ChunkIndex(value=0),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.knowledge.chunk_created.v1"

    @pytest.mark.asyncio
    async def test_subject_for_ingestion_started(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)
        event = IngestionStarted(
            job_id=IngestionJobId(),
            source_id=KnowledgeSourceId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.knowledge.ingestion_started.v1"

    @pytest.mark.asyncio
    async def test_subject_for_ingestion_completed(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)
        event = IngestionCompleted(
            job_id=IngestionJobId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.knowledge.ingestion_completed.v1"

    @pytest.mark.asyncio
    async def test_subject_for_ingestion_failed(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)
        event = IngestionFailed(
            job_id=IngestionJobId(),
            error_message="Failed",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.knowledge.ingestion_failed.v1"

    @pytest.mark.asyncio
    async def test_subject_for_reindex_requested(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)
        event = ReindexRequested(
            source_id=KnowledgeSourceId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.knowledge.reindex_requested.v1"

    @pytest.mark.asyncio
    async def test_ingestion_failed_has_error_message(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)
        event = IngestionFailed(
            job_id=IngestionJobId(),
            error_message="Something broke",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        import json
        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["error_message"] == "Something broke"

    @pytest.mark.asyncio
    async def test_creates_session_when_no_outbox_provided(
        self, mock_js
    ) -> None:
        with patch("backend.knowledge.nats.create_session") as mock_create:
            mock_session = MagicMock()
            mock_create.return_value = mock_session

            await publish_knowledge_outbox_events(
                mock_js,
                batch=10,
                interval_seconds=0.01,
                max_iterations=1,
            )

            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_logs_error_on_exception(self, session, mock_js) -> None:
        mock_js.publish.side_effect = Exception("NATS down")
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)

        with patch("backend.knowledge.nats.logger.error") as mock_log:
            await publish_knowledge_outbox_events(
                mock_js,
                outbox=outbox,
                batch=10,
                interval_seconds=0.01,
                max_iterations=1,
            )
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_iterations_zero_runs_indefinitely(
        self, session, mock_js, monkeypatch
    ) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)

        async def fake_sleep(_):
            raise asyncio.CancelledError()

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)

        with pytest.raises(asyncio.CancelledError):
            await publish_knowledge_outbox_events(
                mock_js,
                outbox=outbox,
                batch=10,
                interval_seconds=0.01,
                max_iterations=0,
            )

    @pytest.mark.asyncio
    async def test_iteration_count_limits(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=2,
        )

        mock_js.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_envelope_has_aggregate_id(
        self, session, mock_js
    ) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        import json
        payload = json.loads(mock_js.publish.await_args[0][1])
        assert "aggregate_id" in payload

    @pytest.mark.asyncio
    async def test_envelope_has_occurred_at(
        self, session, mock_js
    ) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        import json
        payload = json.loads(mock_js.publish.await_args[0][1])
        assert "occurred_at" in payload

    @pytest.mark.asyncio
    async def test_mark_published_after_publish(
        self, session, mock_js
    ) -> None:
        add_simple_outbox_entries(session, count=2)
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        from backend.knowledge.adapters.outbound.models import KnowledgeOutboxModel
        models = session.query(KnowledgeOutboxModel).all()
        for m in models:
            assert m.published_at is not None

    @pytest.mark.asyncio
    async def test_publishes_all_event_types(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)
        now = datetime.now(tz=timezone.utc)
        events: list[KnowledgeOutboxEvent] = [
            KnowledgeSourceRegistered(
                KnowledgeSourceId(), "n", SourceType.FILE,
                SourceLocation(value="/t"), "pub", now
            ),
            KnowledgeSourceDeleted(KnowledgeSourceId(), now),
            DocumentIngested(DocumentId(), KnowledgeSourceId(), "t",
                             DocumentChecksum(value="c"),
                             "pub", now),
            DocumentIndexed(DocumentId(), now),
            DocumentDeleted(DocumentId(), now),
            ChunkCreated(ChunkId(), DocumentId(), ChunkIndex(value=0), now),
            ReindexRequested(KnowledgeSourceId(), now),
            IngestionStarted(IngestionJobId(), KnowledgeSourceId(), now),
            IngestionCompleted(IngestionJobId(), now),
            IngestionFailed(IngestionJobId(), "err", now),
        ]
        for e in events:
            outbox.append(e)
        session.commit()

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        assert mock_js.publish.await_count == 10

    @pytest.mark.asyncio
    async def test_fifo_order_preserved(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyKnowledgeOutboxAdapter(session)
        now = datetime.now(tz=timezone.utc)
        for i in range(3):
            outbox.append(
                KnowledgeSourceRegistered(
                    source_id=KnowledgeSourceId(),
                    name=f"S{i}",
                    source_type=SourceType.FILE,
                    location=SourceLocation(value=f"/t{i}"),
                    classification="public",
                    occurred_at=now,
                )
            )
        session.commit()

        await publish_knowledge_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        assert mock_js.publish.await_count == 3
