from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

import pytest

from backend.memory.application.ports.clock import MemoryClockPort
from backend.memory.application.ports.id_generator import MemoryIdGeneratorPort
from backend.memory.application.ports.outbox import MemoryOutboxEvent, MemoryOutboxPort
from backend.memory.application.ports.repository import (
    ConsentRepositoryPort,
    MemoryRepositoryPort,
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
    MemoryState,
    Provenance,
    RetentionPolicy,
    RetentionStatus,
    RevisionNumber,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_memory(
    *,
    memory_id: MemoryId | None = None,
    consent_id: ConsentId | None = None,
    content: str = "test content",
    category: MemoryCategory = MemoryCategory.GENERAL,
    source_type: str = "user_input",
    source_id: str | None = None,
    state: MemoryState = MemoryState.CREATED,
    deleted_at: datetime | None = None,
) -> Memory:
    now = datetime.now(tz=timezone.utc)
    return Memory(
        memory_id=memory_id or MemoryId(),
        consent_id=consent_id or ConsentId(),
        content=MemoryContent(value=content),
        category=category,
        source_type=source_type,
        source_id=source_id,
        provenance=Provenance(source="test", timestamp=now),
        classification="public",
        sensitivity="low",
        retention=RetentionPolicy(policy="persistent"),
        revision=RevisionNumber(value=1),
        created_at=now,
        state=state,
        retention_status=RetentionStatus.ACTIVE,
        deleted_at=deleted_at,
    )


def _make_consent(
    *,
    consent_id: ConsentId | None = None,
    status: ConsentStatus = ConsentStatus.PROPOSED,
    expires_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> ConsentRecord:
    now = datetime.now(tz=timezone.utc)
    granted_at = now if status == ConsentStatus.ACTIVE else None
    return ConsentRecord(
        consent_id=consent_id or ConsentId(),
        status=status,
        granted_at=granted_at,
        expires_at=expires_at,
        revoked_at=revoked_at,
    )


# ---------------------------------------------------------------------------
# MemoryRepositoryPort Stub
# ---------------------------------------------------------------------------


class StubMemoryRepository:
    """Minimal stub conforming to MemoryRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, Memory] = {}

    def save(self, memory: Memory) -> None:
        key = str(memory.memory_id)
        self._store[key] = memory

    def find_by_id(self, memory_id: MemoryId) -> Memory | None:
        return self._store.get(str(memory_id))

    def find_by_consent_id(self, consent_id: ConsentId) -> list[Memory]:
        return [m for m in self._store.values() if m.consent_id == consent_id]

    def find_by_category(self, category: MemoryCategory) -> list[Memory]:
        return [m for m in self._store.values() if m.category == category]

    def find_by_source(
        self, source_type: str, source_id: str | None
    ) -> list[Memory]:
        return [
            m
            for m in self._store.values()
            if m.source_type == source_type
            and (source_id is None or m.source_id == source_id)
        ]

    def find_deleted(self) -> list[Memory]:
        return [m for m in self._store.values() if m.is_deleted]

    def count(self) -> int:
        return len(self._store)


class TestMemoryRepositoryPort:
    """Contract tests for MemoryRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubMemoryRepository:
        return StubMemoryRepository()

    def test_save_and_find_by_id(self, repo: StubMemoryRepository) -> None:
        memory = _make_memory()
        repo.save(memory)
        found = repo.find_by_id(memory.memory_id)
        assert found is not None
        assert found.memory_id == memory.memory_id
        assert found.content.value == "test content"

    def test_find_by_id_returns_none(self, repo: StubMemoryRepository) -> None:
        missing_id = MemoryId()
        assert repo.find_by_id(missing_id) is None

    def test_find_by_consent_id(self, repo: StubMemoryRepository) -> None:
        consent_id = ConsentId()
        m1 = _make_memory(consent_id=consent_id, content="memory one")
        m2 = _make_memory(consent_id=consent_id, content="memory two")
        m3 = _make_memory(content="other consent")
        repo.save(m1)
        repo.save(m2)
        repo.save(m3)

        results = repo.find_by_consent_id(consent_id)
        assert len(results) == 2
        assert all(r.consent_id == consent_id for r in results)

    def test_find_by_consent_id_empty(
        self, repo: StubMemoryRepository
    ) -> None:
        results = repo.find_by_consent_id(ConsentId())
        assert results == []

    def test_find_by_category(self, repo: StubMemoryRepository) -> None:
        m1 = _make_memory(category=MemoryCategory.CONVERSATION)
        m2 = _make_memory(category=MemoryCategory.CONVERSATION)
        m3 = _make_memory(category=MemoryCategory.INSIGHT)
        repo.save(m1)
        repo.save(m2)
        repo.save(m3)

        results = repo.find_by_category(MemoryCategory.CONVERSATION)
        assert len(results) == 2
        assert all(r.category == MemoryCategory.CONVERSATION for r in results)

    def test_find_by_category_empty(self, repo: StubMemoryRepository) -> None:
        results = repo.find_by_category(MemoryCategory.EPHEMERAL)
        assert results == []

    def test_find_by_source_with_id(self, repo: StubMemoryRepository) -> None:
        m1 = _make_memory(source_type="conversation", source_id="chat-1")
        m2 = _make_memory(source_type="conversation", source_id="chat-1")
        m3 = _make_memory(source_type="conversation", source_id="chat-2")
        m4 = _make_memory(source_type="user_input", source_id="input-1")
        repo.save(m1)
        repo.save(m2)
        repo.save(m3)
        repo.save(m4)

        results = repo.find_by_source("conversation", "chat-1")
        assert len(results) == 2
        assert all(r.source_id == "chat-1" for r in results)

    def test_find_by_source_with_none_id(
        self, repo: StubMemoryRepository
    ) -> None:
        m1 = _make_memory(source_type="inference", source_id="inf-1")
        m2 = _make_memory(source_type="inference", source_id="inf-2")
        m3 = _make_memory(source_type="system", source_id="sys-1")
        repo.save(m1)
        repo.save(m2)
        repo.save(m3)

        results = repo.find_by_source("inference", None)
        assert len(results) == 2
        assert all(r.source_type == "inference" for r in results)

    def test_find_by_source_empty(self, repo: StubMemoryRepository) -> None:
        results = repo.find_by_source("nonexistent", None)
        assert results == []

    def test_find_deleted(self, repo: StubMemoryRepository) -> None:
        now = datetime.now(tz=timezone.utc)
        m1 = _make_memory(state=MemoryState.DELETED, deleted_at=now)
        m2 = _make_memory(state=MemoryState.CREATED)
        m3 = _make_memory(state=MemoryState.DELETED, deleted_at=now)
        repo.save(m1)
        repo.save(m2)
        repo.save(m3)

        results = repo.find_deleted()
        assert len(results) == 2
        assert all(r.is_deleted for r in results)

    def test_find_deleted_empty(self, repo: StubMemoryRepository) -> None:
        m = _make_memory(state=MemoryState.CREATED)
        repo.save(m)
        results = repo.find_deleted()
        assert results == []

    def test_count(self, repo: StubMemoryRepository) -> None:
        assert repo.count() == 0
        repo.save(_make_memory())
        assert repo.count() == 1
        repo.save(_make_memory())
        assert repo.count() == 2

    def test_save_update_semantics(self, repo: StubMemoryRepository) -> None:
        memory = _make_memory(content="original")
        repo.save(memory)
        found = repo.find_by_id(memory.memory_id)
        assert found is not None
        assert found.content.value == "original"

        updated = _make_memory(
            memory_id=memory.memory_id,
            consent_id=memory.consent_id,
            content="updated",
        )
        repo.save(updated)
        found = repo.find_by_id(memory.memory_id)
        assert found is not None
        assert found.content.value == "updated"

    def test_deleted_memories_excluded_from_normal_queries(
        self, repo: StubMemoryRepository
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        consent_id = ConsentId()
        m1 = _make_memory(
            consent_id=consent_id,
            state=MemoryState.DELETED,
            deleted_at=now,
        )
        m2 = _make_memory(consent_id=consent_id)
        repo.save(m1)
        repo.save(m2)

        by_consent = repo.find_by_consent_id(consent_id)
        assert len(by_consent) == 2

    def test_empty_repo_count(self, repo: StubMemoryRepository) -> None:
        assert repo.count() == 0

    def test_find_memory_by_category_multiple_categories(
        self, repo: StubMemoryRepository
    ) -> None:
        for cat in MemoryCategory:
            m = _make_memory(category=cat)
            repo.save(m)

        assert len(repo.find_by_category(MemoryCategory.GENERAL)) == 1
        assert len(repo.find_by_category(MemoryCategory.DOCUMENT)) == 1

    def test_find_by_source_none_id_includes_null_ids(
        self, repo: StubMemoryRepository
    ) -> None:
        m1 = _make_memory(source_type="external", source_id=None)
        m2 = _make_memory(source_type="external", source_id="ext-1")
        repo.save(m1)
        repo.save(m2)

        results = repo.find_by_source("external", None)
        assert len(results) == 2


# ---------------------------------------------------------------------------
# ConsentRepositoryPort Stub
# ---------------------------------------------------------------------------


class StubConsentRepository:
    """Minimal stub conforming to ConsentRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, ConsentRecord] = {}

    def save(self, consent: ConsentRecord) -> None:
        key = str(consent.consent_id)
        self._store[key] = consent

    def find_by_id(self, consent_id: ConsentId) -> ConsentRecord | None:
        return self._store.get(str(consent_id))

    def find_active(self) -> list[ConsentRecord]:
        return [
            c
            for c in self._store.values()
            if c.status == ConsentStatus.ACTIVE
        ]

    def find_expired(self) -> list[ConsentRecord]:
        now = datetime.now(tz=timezone.utc)
        return [
            c
            for c in self._store.values()
            if c.expires_at is not None and c.expires_at < now
        ]

    def find_revoked(self) -> list[ConsentRecord]:
        return [
            c
            for c in self._store.values()
            if c.status == ConsentStatus.REVOKED
        ]

    def count(self) -> int:
        return len(self._store)


class TestConsentRepositoryPort:
    """Contract tests for ConsentRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubConsentRepository:
        return StubConsentRepository()

    def test_save_and_find_by_id(self, repo: StubConsentRepository) -> None:
        consent = _make_consent()
        repo.save(consent)
        found = repo.find_by_id(consent.consent_id)
        assert found is not None
        assert found.consent_id == consent.consent_id

    def test_find_by_id_returns_none(self, repo: StubConsentRepository) -> None:
        missing_id = ConsentId()
        assert repo.find_by_id(missing_id) is None

    def test_find_active(self, repo: StubConsentRepository) -> None:
        active = _make_consent(status=ConsentStatus.ACTIVE)
        proposed = _make_consent(status=ConsentStatus.PROPOSED)
        repo.save(active)
        repo.save(proposed)

        results = repo.find_active()
        assert len(results) == 1
        assert results[0].status == ConsentStatus.ACTIVE

    def test_find_active_excludes_revoked(
        self, repo: StubConsentRepository
    ) -> None:
        active = _make_consent(status=ConsentStatus.ACTIVE)
        revoked = _make_consent(status=ConsentStatus.REVOKED)
        repo.save(active)
        repo.save(revoked)

        results = repo.find_active()
        assert len(results) == 1
        assert all(r.status == ConsentStatus.ACTIVE for r in results)

    def test_find_revoked(self, repo: StubConsentRepository) -> None:
        revoked = _make_consent(status=ConsentStatus.REVOKED)
        active = _make_consent(status=ConsentStatus.ACTIVE)
        repo.save(revoked)
        repo.save(active)

        results = repo.find_revoked()
        assert len(results) == 1
        assert results[0].status == ConsentStatus.REVOKED

    def test_find_revoked_excludes_active(
        self, repo: StubConsentRepository
    ) -> None:
        active = _make_consent(status=ConsentStatus.ACTIVE)
        revoked = _make_consent(status=ConsentStatus.REVOKED)
        repo.save(active)
        repo.save(revoked)

        results = repo.find_revoked()
        assert len(results) == 1
        assert all(r.status == ConsentStatus.REVOKED for r in results)

    def test_find_expired(self, repo: StubConsentRepository) -> None:
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        expired = _make_consent(
            status=ConsentStatus.ACTIVE, expires_at=past
        )
        not_expired = _make_consent(
            status=ConsentStatus.ACTIVE, expires_at=future
        )
        no_expiry = _make_consent(status=ConsentStatus.ACTIVE)
        repo.save(expired)
        repo.save(not_expired)
        repo.save(no_expiry)

        results = repo.find_expired()
        assert len(results) == 1
        assert results[0].expires_at == past

    def test_find_expired_excludes_future(
        self, repo: StubConsentRepository
    ) -> None:
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        consent = _make_consent(
            status=ConsentStatus.ACTIVE, expires_at=future
        )
        repo.save(consent)
        assert repo.find_expired() == []

    def test_find_expired_considers_status_independent(
        self, repo: StubConsentRepository
    ) -> None:
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        revoked_past = _make_consent(
            status=ConsentStatus.REVOKED, expires_at=past
        )
        repo.save(revoked_past)
        results = repo.find_expired()
        assert len(results) == 1

    def test_count(self, repo: StubConsentRepository) -> None:
        assert repo.count() == 0
        repo.save(_make_consent())
        assert repo.count() == 1
        repo.save(_make_consent())
        assert repo.count() == 2

    def test_count_empty(self, repo: StubConsentRepository) -> None:
        assert repo.count() == 0

    def test_find_active_no_active(self, repo: StubConsentRepository) -> None:
        repo.save(_make_consent(status=ConsentStatus.PROPOSED))
        results = repo.find_active()
        assert results == []

    def test_find_revoked_no_revoked(self, repo: StubConsentRepository) -> None:
        repo.save(_make_consent(status=ConsentStatus.ACTIVE))
        results = repo.find_revoked()
        assert results == []

    def test_find_expired_no_expiry_set(
        self, repo: StubConsentRepository
    ) -> None:
        repo.save(_make_consent(status=ConsentStatus.ACTIVE))
        results = repo.find_expired()
        assert results == []


# ---------------------------------------------------------------------------
# MemoryOutboxPort Stub
# ---------------------------------------------------------------------------


class StubMemoryOutbox:
    """Minimal stub conforming to MemoryOutboxPort."""

    def __init__(self) -> None:
        self._events: list[MemoryOutboxEvent] = []
        self._published: set[str] = set()

    def append(self, event: MemoryOutboxEvent) -> None:
        self._events.append(event)

    def fetch_unpublished(self, limit: int = 100) -> list[MemoryOutboxEvent]:
        results = [
            e
            for i, e in enumerate(self._events)
            if self._event_key(e, i) not in self._published
        ]
        return results[:limit]

    def mark_published(self, event_id: str) -> None:
        self._published.add(event_id)

    @staticmethod
    def _event_key(event: MemoryOutboxEvent, index: int) -> str:
        if hasattr(event, "memory_id"):
            return f"memory:{event.memory_id}"
        if hasattr(event, "consent_id"):
            return f"consent:{event.consent_id}"
        return f"index:{index}"


_now = datetime.now(tz=timezone.utc)


def _make_memory_created_event() -> MemoryCreated:
    return MemoryCreated(
        memory_id=MemoryId(),
        consent_id=ConsentId(),
        category=MemoryCategory.GENERAL,
        source_type="user_input",
        source_id=None,
        sensitivity="low",
        occurred_at=_now,
    )


def _make_consent_granted_event() -> ConsentGranted:
    return ConsentGranted(
        consent_id=ConsentId(),
        occurred_at=_now,
    )


class TestMemoryOutboxPort:
    """Contract tests for MemoryOutboxPort."""

    @pytest.fixture
    def outbox(self) -> StubMemoryOutbox:
        return StubMemoryOutbox()

    def test_append_and_fetch(self, outbox: StubMemoryOutbox) -> None:
        event = _make_memory_created_event()
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert unpublished[0].memory_id == event.memory_id

    def test_mark_published_excludes(self, outbox: StubMemoryOutbox) -> None:
        event = _make_memory_created_event()
        outbox.append(event)
        outbox.mark_published(f"memory:{event.memory_id}")
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_fetch_respects_limit(self, outbox: StubMemoryOutbox) -> None:
        for _ in range(10):
            outbox.append(_make_memory_created_event())
        fetched = outbox.fetch_unpublished(limit=3)
        assert len(fetched) == 3

    def test_fetch_default_limit(self, outbox: StubMemoryOutbox) -> None:
        for _ in range(200):
            outbox.append(_make_memory_created_event())
        fetched = outbox.fetch_unpublished()
        assert len(fetched) == 100

    def test_fifo_ordering(self, outbox: StubMemoryOutbox) -> None:
        ids = [MemoryId() for _ in range(5)]
        for mid in ids:
            outbox.append(
                MemoryCreated(
                    memory_id=mid,
                    consent_id=ConsentId(),
                    category=MemoryCategory.GENERAL,
                    source_type="user_input",
                    source_id=None,
                    sensitivity="low",
                    occurred_at=_now,
                )
            )
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 5
        for i, e in enumerate(unpublished):
            assert e.memory_id == ids[i]

    def test_idempotent_mark_published(
        self, outbox: StubMemoryOutbox
    ) -> None:
        event = _make_memory_created_event()
        outbox.append(event)
        key = f"memory:{event.memory_id}"
        outbox.mark_published(key)
        outbox.mark_published(key)
        outbox.mark_published(key)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_multiple_publish_then_fetch(
        self, outbox: StubMemoryOutbox
    ) -> None:
        events = [_make_memory_created_event() for _ in range(3)]
        for e in events:
            outbox.append(e)

        outbox.mark_published(f"memory:{events[0].memory_id}")
        outbox.mark_published(f"memory:{events[1].memory_id}")

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert unpublished[0].memory_id == events[2].memory_id

    def test_fetch_unpublished_empty(self, outbox: StubMemoryOutbox) -> None:
        assert outbox.fetch_unpublished() == []

    def test_consent_event_outbox(
        self, outbox: StubMemoryOutbox
    ) -> None:
        event = _make_consent_granted_event()
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], ConsentGranted)
        assert unpublished[0].consent_id == event.consent_id

    def test_mark_published_consent_event(
        self, outbox: StubMemoryOutbox
    ) -> None:
        event = _make_consent_granted_event()
        outbox.append(event)
        outbox.mark_published(f"consent:{event.consent_id}")
        assert outbox.fetch_unpublished() == []

    def test_partial_publish(self, outbox: StubMemoryOutbox) -> None:
        events = [_make_memory_created_event() for _ in range(5)]
        for e in events:
            outbox.append(e)
        outbox.mark_published(f"memory:{events[0].memory_id}")
        outbox.mark_published(f"memory:{events[2].memory_id}")

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 3


# ---------------------------------------------------------------------------
# MemoryClockPort Stubs + Tests
# ---------------------------------------------------------------------------


class SystemClockStub:
    """Returns real system time — conforms to MemoryClockPort."""

    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)


class FixedClock:
    """Returns a fixed time — conforms to MemoryClockPort."""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return self._fixed


class TestMemoryClockPort:
    """Contract tests for MemoryClockPort."""

    def test_system_clock_returns_utc(self) -> None:
        clock: MemoryClockPort = SystemClockStub()
        result = clock.now()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result).total_seconds() == 0.0

    def test_fixed_clock_returns_configured_time(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        clock: MemoryClockPort = FixedClock(dt)
        assert clock.now() == dt

    def test_fixed_clock_is_deterministic(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        clock: MemoryClockPort = FixedClock(dt)
        assert clock.now() == clock.now() == dt

    def test_clock_protocol_conformance(self) -> None:
        def use_clock(c: MemoryClockPort) -> datetime:
            return c.now()

        assert use_clock(SystemClockStub()) is not None
        assert use_clock(
            FixedClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
        ) is not None

    def test_fixed_clock_rejects_naive_datetime(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0)
        clock: MemoryClockPort = FixedClock(dt)
        result = clock.now()
        assert result.tzinfo is None

    def test_system_clock_consistent_type(self) -> None:
        clock: MemoryClockPort = SystemClockStub()
        result = clock.now()
        assert isinstance(result, datetime)


# ---------------------------------------------------------------------------
# MemoryIdGeneratorPort Stubs + Tests
# ---------------------------------------------------------------------------


class UuidMemoryIdGeneratorStub:
    """Generates UUID-based IDs — conforms to MemoryIdGeneratorPort."""

    def generate_memory_id(self) -> MemoryId:
        return MemoryId()

    def generate_consent_id(self) -> ConsentId:
        return ConsentId()


class SequentialMemoryIdGenerator:
    """Generates deterministic sequential IDs — conforms to MemoryIdGeneratorPort."""

    def __init__(self) -> None:
        self._mem_counter = 0
        self._con_counter = 0

    def generate_memory_id(self) -> MemoryId:
        self._mem_counter += 1
        return MemoryId()

    def generate_consent_id(self) -> ConsentId:
        self._con_counter += 1
        return ConsentId()


class FixedMemoryIdGenerator:
    """Generates IDs with deterministic counter — conforms to MemoryIdGeneratorPort."""

    def __init__(self) -> None:
        self._calls: list[str] = []

    def generate_memory_id(self) -> MemoryId:
        self._calls.append("memory")
        return MemoryId()

    def generate_consent_id(self) -> ConsentId:
        self._calls.append("consent")
        return ConsentId()

    @property
    def call_count(self) -> int:
        return len(self._calls)

    @property
    def last_call(self) -> str | None:
        return self._calls[-1] if self._calls else None


class TestMemoryIdGeneratorPort:
    """Contract tests for MemoryIdGeneratorPort."""

    def test_memory_id_generator_returns_memory_id(self) -> None:
        gen: MemoryIdGeneratorPort = UuidMemoryIdGeneratorStub()
        result = gen.generate_memory_id()
        assert isinstance(result, MemoryId)
        assert isinstance(result.value, type(MemoryId().value))

    def test_consent_id_generator_returns_consent_id(self) -> None:
        gen: MemoryIdGeneratorPort = UuidMemoryIdGeneratorStub()
        result = gen.generate_consent_id()
        assert isinstance(result, ConsentId)
        assert isinstance(result.value, type(ConsentId().value))

    def test_uuid_generator_unique_memory_ids(self) -> None:
        gen: MemoryIdGeneratorPort = UuidMemoryIdGeneratorStub()
        ids = {gen.generate_memory_id() for _ in range(100)}
        assert len(ids) == 100

    def test_uuid_generator_unique_consent_ids(self) -> None:
        gen: MemoryIdGeneratorPort = UuidMemoryIdGeneratorStub()
        ids = {gen.generate_consent_id() for _ in range(100)}
        assert len(ids) == 100

    def test_fixed_generator_tracks_calls(self) -> None:
        gen: MemoryIdGeneratorPort = FixedMemoryIdGenerator()
        assert gen.call_count == 0

        gen.generate_memory_id()
        assert gen.call_count == 1
        assert gen.last_call == "memory"

        gen.generate_consent_id()
        assert gen.call_count == 2
        assert gen.last_call == "consent"

    def test_generator_protocol_conformance(self) -> None:
        def use_generator(g: MemoryIdGeneratorPort) -> tuple[MemoryId, ConsentId]:
            return g.generate_memory_id(), g.generate_consent_id()

        mid, cid = use_generator(UuidMemoryIdGeneratorStub())
        assert isinstance(mid, MemoryId)
        assert isinstance(cid, ConsentId)

        mid2, cid2 = use_generator(FixedMemoryIdGenerator())
        assert isinstance(mid2, MemoryId)
        assert isinstance(cid2, ConsentId)

    def test_memory_and_consent_ids_distinct(self) -> None:
        gen: MemoryIdGeneratorPort = UuidMemoryIdGeneratorStub()
        mid = gen.generate_memory_id()
        cid = gen.generate_consent_id()
        assert isinstance(mid, MemoryId)
        assert isinstance(cid, ConsentId)


# ---------------------------------------------------------------------------
# Port method signature cross-verification
# ---------------------------------------------------------------------------


class TestMethodSignatures:
    """Verify that each port method signature matches expectations.

    These tests introspect the stub methods and check parameter
    names and annotations to catch signature drift.
    """

    def test_memory_repo_signatures(self) -> None:
        import inspect

        methods = {
            "save": {"memory": Memory},
            "find_by_id": {"memory_id": MemoryId, "return": Memory | None},
            "find_by_consent_id": {"consent_id": ConsentId, "return": list},
            "find_by_category": {"category": MemoryCategory, "return": list},
            "find_by_source": {
                "source_type": str,
                "source_id": str | None,
                "return": list,
            },
            "find_deleted": {"return": list},
            "count": {"return": int},
        }
        stub = StubMemoryRepository()
        for method_name, expected_params in methods.items():
            method = getattr(stub, method_name)
            sig = inspect.signature(method)
            for param_name in expected_params:
                if param_name == "return":
                    continue
                assert param_name in sig.parameters, (
                    f"{method_name} missing parameter {param_name!r}"
                )

    def test_consent_repo_signatures(self) -> None:
        methods = ["save", "find_by_id", "find_active", "find_expired", "find_revoked", "count"]
        for m in methods:
            assert hasattr(StubConsentRepository(), m)

    def test_outbox_signatures(self) -> None:
        methods = ["append", "fetch_unpublished", "mark_published"]
        for m in methods:
            assert hasattr(StubMemoryOutbox(), m)

    def test_clock_signature(self) -> None:
        assert hasattr(SystemClockStub(), "now")
        assert hasattr(FixedClock(datetime.now(tz=timezone.utc)), "now")

    def test_id_generator_signatures(self) -> None:
        assert hasattr(UuidMemoryIdGeneratorStub(), "generate_memory_id")
        assert hasattr(UuidMemoryIdGeneratorStub(), "generate_consent_id")
        assert hasattr(FixedMemoryIdGenerator(), "generate_memory_id")
        assert hasattr(FixedMemoryIdGenerator(), "generate_consent_id")

    def test_memory_repo_method_count(self) -> None:
        port_methods = {
            m for m in dir(MemoryRepositoryPort) if not m.startswith("_")
        }
        assert port_methods == {
            "save",
            "find_by_id",
            "find_by_consent_id",
            "find_by_category",
            "find_by_source",
            "find_deleted",
            "count",
        }

    def test_consent_repo_method_count(self) -> None:
        port_methods = {
            m for m in dir(ConsentRepositoryPort) if not m.startswith("_")
        }
        assert port_methods == {
            "save",
            "find_by_id",
            "find_active",
            "find_expired",
            "find_revoked",
            "count",
        }

    def test_outbox_method_count(self) -> None:
        port_methods = {
            m for m in dir(MemoryOutboxPort) if not m.startswith("_")
        }
        assert port_methods == {"append", "fetch_unpublished", "mark_published"}

    def test_clock_method_count(self) -> None:
        port_methods = {
            m for m in dir(MemoryClockPort) if not m.startswith("_")
        }
        assert port_methods == {"now"}

    def test_id_generator_method_count(self) -> None:
        port_methods = {
            m for m in dir(MemoryIdGeneratorPort) if not m.startswith("_")
        }
        assert port_methods == {"generate_memory_id", "generate_consent_id"}

    def test_memory_repo_nullable_return(self) -> None:
        stub = StubMemoryRepository()
        result = stub.find_by_id(MemoryId())
        assert result is None

    def test_consent_repo_nullable_return(self) -> None:
        stub = StubConsentRepository()
        result = stub.find_by_id(ConsentId())
        assert result is None
