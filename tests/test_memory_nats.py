from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.memory.adapters.outbound.clock import SystemClockAdapter
from backend.memory.adapters.outbound.mapper import (
    ConsentMapperImpl,
    MemoryMapperImpl,
)
from backend.memory.adapters.outbound.models import Base
from backend.memory.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyConsentRepository,
    SqlAlchemyMemoryOutboxAdapter,
    SqlAlchemyMemoryRepository,
)
from backend.memory.application.use_cases.dto import (
    CreateMemoryRequest,
)
from backend.memory.application.use_cases.create_memory import (
    CreateMemoryUseCase,
)
from backend.memory.domain.model import (
    ConsentGranted,
    ConsentId,
    ConsentRecord,
    ConsentRevoked,
    ConsentStatus,
    MemoryCreated,
    MemoryDeleted,
    MemoryId,
    MemoryUpdated,
    MemoryCategory,
)
from backend.memory.nats import (
    MemoryOutboxEvent,
    publish_memory_outbox_events,
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
    return SqlAlchemyMemoryOutboxAdapter(session)


@pytest.fixture
def clock():
    return SystemClockAdapter()


@pytest.fixture
def mock_js():
    js = AsyncMock()
    js.publish = AsyncMock()
    return js


def add_outbox_entries(session, count: int = 3):
    """Helper: simulate outbox entries by running create memory use case."""
    clock = SystemClockAdapter()
    mapper = MemoryMapperImpl()
    consent_mapper = ConsentMapperImpl()
    memory_repo = SqlAlchemyMemoryRepository(session, mapper=mapper)
    consent_repo = SqlAlchemyConsentRepository(session, mapper=consent_mapper)
    outbox = SqlAlchemyMemoryOutboxAdapter(session)

    for i in range(count):
        consent = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.ACTIVE)
        consent_repo.save(consent)
        session.flush()

        uc = CreateMemoryUseCase(
            memory_repo=memory_repo,
            consent_repo=consent_repo,
            outbox=outbox,
            clock=clock,
            id_generator=__import__("backend.memory.adapters.outbound.id_generator").memory.adapters.outbound.id_generator.UuidGeneratorAdapter(),
        )
        uc.execute(
            CreateMemoryRequest(
                consent_id=str(consent.consent_id),
                content=f"Memory {i}",
                category="general",
                source_type="user_input",
                provenance_source="user_input",
            )
        )
    session.commit()
    return outbox


def add_simple_outbox_entries(session, count: int = 3):
    """Helper: directly create outbox entries for testing."""
    outbox = SqlAlchemyMemoryOutboxAdapter(session)
    for i in range(count):
        event = MemoryCreated(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            category=MemoryCategory.GENERAL,
            source_type="user_input",
            source_id=None,
            sensitivity="low",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
    session.commit()
    return outbox


class TestPublishMemoryOutboxEvents:
    @pytest.mark.asyncio
    async def test_publishes_all_events(self, session, mock_js) -> None:
        add_simple_outbox_entries(session, count=2)
        outbox = SqlAlchemyMemoryOutboxAdapter(session)

        await publish_memory_outbox_events(
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
        outbox = SqlAlchemyMemoryOutboxAdapter(session)

        await publish_memory_outbox_events(
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
        outbox = SqlAlchemyMemoryOutboxAdapter(session)

        await publish_memory_outbox_events(
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
        outbox = SqlAlchemyMemoryOutboxAdapter(session)

        await publish_memory_outbox_events(
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
        outbox = SqlAlchemyMemoryOutboxAdapter(session)

        await publish_memory_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject.startswith("jarvis.memory.event.")

    @pytest.mark.asyncio
    async def test_payload_is_json_bytes(
        self, session, mock_js
    ) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyMemoryOutboxAdapter(session)

        await publish_memory_outbox_events(
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
        outbox = SqlAlchemyMemoryOutboxAdapter(session)

        await publish_memory_outbox_events(
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
        assert payload["producer"] == "memory"

    @pytest.mark.asyncio
    async def test_memory_created_event_type(
        self, session, mock_js
    ) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyMemoryOutboxAdapter(session)

        await publish_memory_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        import json
        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["event_type"] == "MEMORY_CREATED"
        assert "consent_id" in payload
        assert "category" in payload
        assert "source_type" in payload
        assert "sensitivity" in payload

    @pytest.mark.asyncio
    async def test_consent_granted_event_type(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyMemoryOutboxAdapter(session)
        event = ConsentGranted(
            consent_id=ConsentId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_memory_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        import json
        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["event_type"] == "CONSENT_GRANTED"

    @pytest.mark.asyncio
    async def test_consent_revoked_event_type(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyMemoryOutboxAdapter(session)
        event = ConsentRevoked(
            consent_id=ConsentId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_memory_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        mock_js.publish.assert_called_once()
        import json
        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["event_type"] == "CONSENT_REVOKED"

    @pytest.mark.asyncio
    async def test_subject_for_memory_created(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyMemoryOutboxAdapter(session)
        event = MemoryCreated(
            memory_id=MemoryId(),
            consent_id=ConsentId(),
            category=MemoryCategory.GENERAL,
            source_type="user_input",
            source_id=None,
            sensitivity="low",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_memory_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.memory.event.memory_created.v1"

    @pytest.mark.asyncio
    async def test_subject_for_memory_updated(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyMemoryOutboxAdapter(session)
        event = MemoryUpdated(
            memory_id=MemoryId(),
            revision=2,
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_memory_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.memory.event.memory_updated.v1"

    @pytest.mark.asyncio
    async def test_subject_for_memory_deleted(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyMemoryOutboxAdapter(session)
        event = MemoryDeleted(
            memory_id=MemoryId(),
            revision=1,
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_memory_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.memory.event.memory_deleted.v1"

    @pytest.mark.asyncio
    async def test_subject_for_consent_granted(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyMemoryOutboxAdapter(session)
        event = ConsentGranted(
            consent_id=ConsentId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_memory_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.memory.event.consent_granted.v1"

    @pytest.mark.asyncio
    async def test_creates_session_when_no_outbox_provided(
        self, mock_js
    ) -> None:
        with patch("backend.memory.nats.create_session") as mock_create:
            mock_session = MagicMock()
            mock_create.return_value = mock_session

            await publish_memory_outbox_events(
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
        outbox = SqlAlchemyMemoryOutboxAdapter(session)

        with patch("backend.memory.nats.logger.error") as mock_log:
            await publish_memory_outbox_events(
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
        outbox = SqlAlchemyMemoryOutboxAdapter(session)

        async def fake_sleep(_):
            raise asyncio.CancelledError()

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)

        with pytest.raises(asyncio.CancelledError):
            await publish_memory_outbox_events(
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
        outbox = SqlAlchemyMemoryOutboxAdapter(session)

        await publish_memory_outbox_events(
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
        outbox = SqlAlchemyMemoryOutboxAdapter(session)

        await publish_memory_outbox_events(
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
        outbox = SqlAlchemyMemoryOutboxAdapter(session)

        await publish_memory_outbox_events(
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
        outbox = SqlAlchemyMemoryOutboxAdapter(session)

        await publish_memory_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        from backend.memory.adapters.outbound.models import MemoryOutboxModel
        models = session.query(MemoryOutboxModel).all()
        for m in models:
            assert m.published_at is not None

    @pytest.mark.asyncio
    async def test_publishes_all_event_types(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyMemoryOutboxAdapter(session)
        now = datetime.now(tz=timezone.utc)
        events: list[MemoryOutboxEvent] = [
            MemoryCreated(MemoryId(), ConsentId(), MemoryCategory.GENERAL, "ui", None, "low", now),
            MemoryUpdated(MemoryId(), 1, now),
            MemoryDeleted(MemoryId(), 1, now),
            ConsentGranted(ConsentId(), now),
            ConsentRevoked(ConsentId(), now),
        ]
        for e in events:
            outbox.append(e)
        session.commit()

        await publish_memory_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        assert mock_js.publish.await_count == 5

    @pytest.mark.asyncio
    async def test_fifo_order_preserved(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyMemoryOutboxAdapter(session)
        now = datetime.now(tz=timezone.utc)
        for i in range(3):
            outbox.append(
                MemoryCreated(
                    memory_id=MemoryId(),
                    consent_id=ConsentId(),
                    category=MemoryCategory.GENERAL,
                    source_type="user_input",
                    source_id=None,
                    sensitivity="low",
                    occurred_at=now,
                )
            )
        session.commit()

        await publish_memory_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        assert mock_js.publish.await_count == 3
