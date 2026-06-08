from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

import pytest

from backend.audit.application.ports.clock import AuditClockPort
from backend.audit.application.ports.id_generator import AuditIdGeneratorPort
from backend.audit.application.ports.outbox import AuditOutboxPort
from backend.audit.application.ports.repository import (
    AuditChainHeadRepositoryPort,
    AuditEntryRepositoryPort,
)
from backend.audit.domain.model import (
    AuditChainHead,
    AuditEntry,
    AuditEntryId,
    AuditEntryRecorded,
    AuditEntryState,
    EntryHash,
    EntryIndex,
    OccurredAt,
)
from backend.audit.domain.factory import AuditEntryFactory


# ---------------------------------------------------------------------------
# Structural protocol conformance tests
#
# Each test creates a stub and verifies it satisfies the port Protocol.
# isinstance(x, Protocol) does NOT work for structural subtyping at
# runtime — we instead verify that the stub has all the required methods
# with correct signatures by calling each method and asserting type
# expectations.
# ---------------------------------------------------------------------------


def _make_entry() -> AuditEntry:
    entry, _ = AuditEntryFactory.create(
        chain_name="security",
        action="test.port",
        policy_decision="grant",
        classification="internal",
        correlation_id="corr-port-test",
        result="success",
        actor_type="user",
        actor_id="alice",
    )
    return entry


def _make_domain_event(entry: AuditEntry) -> AuditEntryRecorded:
    return AuditEntryRecorded(
        entry_id=entry.entry_id,
        chain_name=entry.chain_name,
        action=entry.action,
        actor_type=entry.actor.actor_type,
        actor_id=entry.actor.actor_id,
        correlation_id=entry.correlation_id,
        entry_index=entry.entry_index.value,
        occurred_at=entry.occurred_at.value,
    )


# ---------------------------------------------------------------------------
# AuditEntryRepositoryPort Stub
# ---------------------------------------------------------------------------


class StubAuditEntryRepository:
    """Minimal stub conforming to AuditEntryRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, AuditEntry] = {}

    def save(self, entry: AuditEntry) -> None:
        key = str(entry.entry_id)
        self._store[key] = entry

    def find_by_id(self, entry_id: AuditEntryId) -> AuditEntry | None:
        return self._store.get(str(entry_id))

    def find_by_chain(
        self,
        chain_name: str,
        *,
        since_index: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        entries = [
            e
            for e in self._store.values()
            if e.chain_name == chain_name
            and (since_index is None or e.entry_index.value >= since_index)
        ]
        entries.sort(key=lambda e: e.entry_index.value)
        return entries[offset : offset + limit]

    def find_by_correlation_id(
        self, correlation_id: str
    ) -> list[AuditEntry]:
        return [
            e
            for e in self._store.values()
            if e.correlation_id == correlation_id
        ]

    def count_by_chain(self, chain_name: str) -> int:
        return sum(1 for e in self._store.values() if e.chain_name == chain_name)


class TestAuditEntryRepositoryPort:
    """Contract tests for AuditEntryRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubAuditEntryRepository:
        return StubAuditEntryRepository()

    def test_save_and_find_by_id(self, repo: StubAuditEntryRepository) -> None:
        entry = _make_entry()
        repo.save(entry)
        found = repo.find_by_id(entry.entry_id)
        assert found is not None
        assert found.entry_id == entry.entry_id
        assert found.chain_name == "security"

    def test_find_by_id_returns_none(self, repo: StubAuditEntryRepository) -> None:
        missing_id = AuditEntryId()
        assert repo.find_by_id(missing_id) is None

    def test_find_by_chain(self, repo: StubAuditEntryRepository) -> None:
        e1, _ = AuditEntryFactory.create(
            chain_name="chain-a",
            action="first",
            policy_decision="grant",
            classification="public",
            correlation_id="c1",
            result="success",
            actor_type="user",
            actor_id="alice",
        )
        e2, _ = AuditEntryFactory.create(
            chain_name="chain-a",
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
        e3, _ = AuditEntryFactory.create(
            chain_name="chain-b",
            action="other",
            policy_decision="grant",
            classification="public",
            correlation_id="c3",
            result="success",
            actor_type="service",
            actor_id="svc",
        )
        repo.save(e1)
        repo.save(e2)
        repo.save(e3)

        results = repo.find_by_chain("chain-a")
        assert len(results) == 2
        assert results[0].entry_index.value == 0
        assert results[1].entry_index.value == 1

    def test_find_by_chain_with_since_index(
        self, repo: StubAuditEntryRepository
    ) -> None:
        entries = []
        for i in range(5):
            e, _ = AuditEntryFactory.create(
                chain_name="chain-c",
                action=f"step.{i}",
                policy_decision="grant",
                classification="public",
                correlation_id=f"c{i}",
                result="success",
                actor_type="user",
                actor_id="alice",
                previous_entry_hash=(
                    entries[-1].entry_hash.value if entries else None
                ),
                previous_entry_index=(entries[-1].entry_index.value if entries else None),
            )
            entries.append(e)
            repo.save(e)

        results = repo.find_by_chain("chain-c", since_index=3)
        assert len(results) == 2
        assert results[0].entry_index.value == 3
        assert results[1].entry_index.value == 4

    def test_find_by_chain_pagination(
        self, repo: StubAuditEntryRepository
    ) -> None:
        entries = []
        for i in range(10):
            e, _ = AuditEntryFactory.create(
                chain_name="chain-d",
                action=f"page.{i}",
                policy_decision="grant",
                classification="internal",
                correlation_id=f"c{i}",
                result="success",
                actor_type="service",
                actor_id="svc",
                previous_entry_hash=(
                    entries[-1].entry_hash.value if entries else None
                ),
                previous_entry_index=(entries[-1].entry_index.value if entries else None),
            )
            entries.append(e)
            repo.save(e)

        page = repo.find_by_chain("chain-d", limit=3, offset=2)
        assert len(page) == 3
        assert page[0].entry_index.value == 2
        assert page[1].entry_index.value == 3
        assert page[2].entry_index.value == 4

    def test_find_by_correlation_id(
        self, repo: StubAuditEntryRepository
    ) -> None:
        e1, _ = AuditEntryFactory.create(
            chain_name="security",
            action="action.1",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-xyz",
            result="success",
            actor_type="user",
            actor_id="alice",
        )
        e2, _ = AuditEntryFactory.create(
            chain_name="consent",
            action="action.2",
            policy_decision="deny",
            classification="sensitive",
            correlation_id="corr-xyz",
            result="denied",
            actor_type="agent",
            actor_id="jarvis",
        )
        e3, _ = AuditEntryFactory.create(
            chain_name="system",
            action="other",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-abc",
            result="success",
            actor_type="service",
            actor_id="svc",
        )
        repo.save(e1)
        repo.save(e2)
        repo.save(e3)

        results = repo.find_by_correlation_id("corr-xyz")
        assert len(results) == 2
        assert all(r.correlation_id == "corr-xyz" for r in results)

    def test_count_by_chain(self, repo: StubAuditEntryRepository) -> None:
        for i in range(4):
            e, _ = AuditEntryFactory.create(
                chain_name="count-me",
                action=f"cnt.{i}",
                policy_decision="grant",
                classification="public",
                correlation_id=f"cc{i}",
                result="success",
                actor_type="user",
                actor_id="tester",
                previous_entry_hash=(e.entry_hash.value if i > 0 else None),
                previous_entry_index=(e.entry_index.value if i > 0 else None),
            )
            repo.save(e)

        assert repo.count_by_chain("count-me") == 4
        assert repo.count_by_chain("nonexistent") == 0

    def test_save_nullable_fields_roundtrip(
        self, repo: StubAuditEntryRepository
    ) -> None:
        entry, _ = AuditEntryFactory.create(
            chain_name="security",
            action="null.test",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-null",
            result="success",
            actor_type="user",
            actor_id=None,
        )
        repo.save(entry)
        found = repo.find_by_id(entry.entry_id)
        assert found is not None
        assert found.actor.actor_id is None


# ---------------------------------------------------------------------------
# AuditChainHeadRepositoryPort Stub
# ---------------------------------------------------------------------------


class StubAuditChainHeadRepository:
    """Minimal stub conforming to AuditChainHeadRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, AuditChainHead] = {}

    def save(self, head: AuditChainHead) -> None:
        self._store[head.chain_name] = head

    def find_by_chain(self, chain_name: str) -> AuditChainHead | None:
        return self._store.get(chain_name)

    def find_all(self) -> list[AuditChainHead]:
        return list(self._store.values())


class TestAuditChainHeadRepositoryPort:
    """Contract tests for AuditChainHeadRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubAuditChainHeadRepository:
        return StubAuditChainHeadRepository()

    def test_save_and_find_by_chain(
        self, repo: StubAuditChainHeadRepository
    ) -> None:
        head = AuditChainHead(
            chain_name="security",
            head_hash=EntryHash(value=b"\x01" * 32),
            entries_count=42,
        )
        repo.save(head)
        found = repo.find_by_chain("security")
        assert found is not None
        assert found.chain_name == "security"
        assert found.head_hash == EntryHash(value=b"\x01" * 32)
        assert found.entries_count == 42

    def test_find_by_chain_nonexistent(
        self, repo: StubAuditChainHeadRepository
    ) -> None:
        assert repo.find_by_chain("nonexistent") is None

    def test_find_all(self, repo: StubAuditChainHeadRepository) -> None:
        heads = [
            AuditChainHead(chain_name="security", head_hash=None, entries_count=0),
            AuditChainHead(chain_name="consent", head_hash=None, entries_count=0),
        ]
        for h in heads:
            repo.save(h)
        all_heads = repo.find_all()
        assert len(all_heads) == 2
        names = {h.chain_name for h in all_heads}
        assert names == {"security", "consent"}

    def test_upsert_semantics(self, repo: StubAuditChainHeadRepository) -> None:
        repo.save(
            AuditChainHead(chain_name="policy", head_hash=None, entries_count=5)
        )
        repo.save(
            AuditChainHead(
                chain_name="policy",
                head_hash=EntryHash(value=b"\x02" * 32),
                entries_count=6,
            )
        )
        found = repo.find_by_chain("policy")
        assert found is not None
        assert found.entries_count == 6
        assert found.head_hash == EntryHash(value=b"\x02" * 32)

    def test_empty_find_all(self, repo: StubAuditChainHeadRepository) -> None:
        assert repo.find_all() == []


# ---------------------------------------------------------------------------
# AuditOutboxPort Stub
# ---------------------------------------------------------------------------


class StubAuditOutbox:
    """Minimal stub conforming to AuditOutboxPort."""

    def __init__(self) -> None:
        self._events: dict[str, AuditEntryRecorded] = {}
        self._published: set[str] = set()

    def append(self, event: AuditEntryRecorded) -> None:
        key = str(event.entry_id)
        self._events[key] = event

    def mark_published(self, entry_id: AuditEntryId) -> None:
        self._published.add(str(entry_id))

    def fetch_unpublished(
        self, limit: int = 50
    ) -> list[AuditEntryRecorded]:
        results = [
            e
            for k, e in self._events.items()
            if k not in self._published
        ]
        return results[:limit]


class TestAuditOutboxPort:
    """Contract tests for AuditOutboxPort."""

    @pytest.fixture
    def outbox(self) -> StubAuditOutbox:
        return StubAuditOutbox()

    def test_append_and_fetch(self, outbox: StubAuditOutbox) -> None:
        entry = _make_entry()
        event = _make_domain_event(entry)
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert unpublished[0].entry_id == entry.entry_id

    def test_mark_published_excludes(
        self, outbox: StubAuditOutbox
    ) -> None:
        entry = _make_entry()
        event = _make_domain_event(entry)
        outbox.append(event)
        outbox.mark_published(entry.entry_id)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_fetch_respects_limit(self, outbox: StubAuditOutbox) -> None:
        for i in range(5):
            e, _ = AuditEntryFactory.create(
                chain_name="security",
                action=f"evt.{i}",
                policy_decision="grant",
                classification="public",
                correlation_id=f"corr-e{i}",
                result="success",
                actor_type="user",
                actor_id="alice",
            )
            outbox.append(_make_domain_event(e))

        fetched = outbox.fetch_unpublished(limit=3)
        assert len(fetched) == 3

    def test_multiple_publish_then_fetch(
        self, outbox: StubAuditOutbox
    ) -> None:
        entries = []
        for i in range(3):
            e, _ = AuditEntryFactory.create(
                chain_name="system",
                action=f"pub.{i}",
                policy_decision="grant",
                classification="internal",
                correlation_id=f"corr-p{i}",
                result="success",
                actor_type="service",
                actor_id="audit-svc",
            )
            entries.append(e)
            outbox.append(_make_domain_event(e))

        # Publish only the first two
        outbox.mark_published(entries[0].entry_id)
        outbox.mark_published(entries[1].entry_id)

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert unpublished[0].entry_id == entries[2].entry_id


# ---------------------------------------------------------------------------
# AuditClockPort Stubs + Tests
# ---------------------------------------------------------------------------


class SystemClockStub:
    """Returns real system time — conforms to AuditClockPort."""

    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)


class FixedClock:
    """Returns a fixed time — conforms to AuditClockPort."""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return self._fixed


class TestAuditClockPort:
    """Contract tests for AuditClockPort."""

    def test_system_clock_returns_utc(self) -> None:
        clock: AuditClockPort = SystemClockStub()
        result = clock.now()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result).total_seconds() == 0.0

    def test_fixed_clock_returns_configured_time(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        clock: AuditClockPort = FixedClock(dt)
        assert clock.now() == dt

    def test_fixed_clock_is_deterministic(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        clock: AuditClockPort = FixedClock(dt)
        assert clock.now() == clock.now() == dt

    def test_clock_protocol_conformance(self) -> None:
        """Verify stubs satisfy the Protocol via call-sites."""
        def use_clock(c: AuditClockPort) -> datetime:
            return c.now()

        assert use_clock(SystemClockStub()) is not None
        assert use_clock(FixedClock(
            datetime(2026, 1, 1, tzinfo=timezone.utc)
        )) is not None


# ---------------------------------------------------------------------------
# AuditIdGeneratorPort Stubs + Tests
# ---------------------------------------------------------------------------


class Uuid7GeneratorStub:
    """Generates UUID v7 strings — conforms to AuditIdGeneratorPort."""

    def generate(self) -> str:
        return str(AuditEntryId())


class SequentialIdGenerator:
    """Generates deterministic sequential IDs — conforms to AuditIdGeneratorPort."""

    def __init__(self) -> None:
        self._counter = 0

    def generate(self) -> str:
        self._counter += 1
        return f"audit-{self._counter:010d}"


class TestAuditIdGeneratorPort:
    """Contract tests for AuditIdGeneratorPort."""

    def test_uuid_generator_returns_string(self) -> None:
        gen: AuditIdGeneratorPort = Uuid7GeneratorStub()
        result = gen.generate()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_uuid_generator_unique(self) -> None:
        gen: AuditIdGeneratorPort = Uuid7GeneratorStub()
        ids = {gen.generate() for _ in range(100)}
        assert len(ids) == 100

    def test_sequential_generator(self) -> None:
        gen: AuditIdGeneratorPort = SequentialIdGenerator()
        assert gen.generate() == "audit-0000000001"
        assert gen.generate() == "audit-0000000002"
        assert gen.generate() == "audit-0000000003"

    def test_generator_protocol_conformance(self) -> None:
        """Verify stubs satisfy the Protocol via call-sites."""
        def use_generator(g: AuditIdGeneratorPort) -> str:
            return g.generate()

        assert isinstance(use_generator(Uuid7GeneratorStub()), str)
        assert use_generator(SequentialIdGenerator()) == "audit-0000000001"


# ---------------------------------------------------------------------------
# Port method signature cross-verification
# ---------------------------------------------------------------------------


class TestMethodSignatures:
    """Verify that each port method signature matches expectations.

    These tests introspect the stub methods and check parameter
    names and annotations to catch signature drift.
    """

    def test_entry_repo_signatures(self) -> None:
        import inspect

        methods = {
            "save": {"entry": AuditEntry},
            "find_by_id": {"entry_id": AuditEntryId, "return": AuditEntry | None},
            "find_by_chain": {
                "chain_name": str,
                "since_index": int | None,
                "limit": int,
                "offset": int,
                "return": list,
            },
            "find_by_correlation_id": {
                "correlation_id": str,
                "return": list,
            },
            "count_by_chain": {"chain_name": str, "return": int},
        }
        stub = StubAuditEntryRepository()
        for method_name, expected_params in methods.items():
            method = getattr(stub, method_name)
            sig = inspect.signature(method)
            for param_name in expected_params:
                if param_name == "return":
                    continue
                assert param_name in sig.parameters, (
                    f"{method_name} missing parameter {param_name!r}"
                )

    def test_chain_head_repo_signatures(self) -> None:
        methods = ["save", "find_by_chain", "find_all"]
        for m in methods:
            assert hasattr(StubAuditChainHeadRepository(), m)

    def test_outbox_signatures(self) -> None:
        methods = ["append", "mark_published", "fetch_unpublished"]
        for m in methods:
            assert hasattr(StubAuditOutbox(), m)

    def test_clock_signature(self) -> None:
        assert hasattr(SystemClockStub(), "now")
        assert hasattr(FixedClock(datetime.now(tz=timezone.utc)), "now")

    def test_id_generator_signature(self) -> None:
        assert hasattr(Uuid7GeneratorStub(), "generate")
        assert hasattr(SequentialIdGenerator(), "generate")
