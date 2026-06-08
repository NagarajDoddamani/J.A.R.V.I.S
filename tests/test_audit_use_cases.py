from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.audit.application.ports.clock import AuditClockPort
from backend.audit.application.ports.id_generator import AuditIdGeneratorPort
from backend.audit.application.ports.outbox import AuditOutboxPort
from backend.audit.application.ports.repository import (
    AuditChainHeadRepositoryPort,
    AuditEntryRepositoryPort,
)
from backend.audit.application.use_cases.dto import (
    AuditChainHeadResponse,
    AuditEntryResponse,
    GetAuditChainHeadRequest,
    GetAuditChainRequest,
    GetAuditChainResponse,
    GetAuditEntriesByCorrelationRequest,
    GetAuditEntriesByCorrelationResponse,
    GetAuditEntryRequest,
    RecordAuditEntryRequest,
    RecordAuditEntryResponse,
)
from backend.audit.application.use_cases.exceptions import (
    AuditEntryNotFoundError,
    ChainNotFoundError,
    UseCaseError,
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

# ===================================================================
# Fake port implementations (in-memory)
# ===================================================================


class FakeAuditEntryRepository:
    def __init__(self) -> None:
        self._store: dict[str, AuditEntry] = {}

    def save(self, entry: AuditEntry) -> None:
        self._store[str(entry.entry_id)] = entry

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


class FakeAuditChainHeadRepository:
    def __init__(self) -> None:
        self._store: dict[str, AuditChainHead] = {}

    def save(self, head: AuditChainHead) -> None:
        self._store[head.chain_name] = head

    def find_by_chain(self, chain_name: str) -> AuditChainHead | None:
        return self._store.get(chain_name)

    def find_all(self) -> list[AuditChainHead]:
        return list(self._store.values())


class FakeAuditOutbox:
    def __init__(self) -> None:
        self._events: list[AuditEntryRecorded] = []
        self._published: set[str] = set()

    def append(self, event: AuditEntryRecorded) -> None:
        self._events.append(event)

    def mark_published(self, entry_id: AuditEntryId) -> None:
        self._published.add(str(entry_id))

    def fetch_unpublished(self, limit: int = 50) -> list[AuditEntryRecorded]:
        return [
            e
            for e in self._events
            if str(e.entry_id) not in self._published
        ][:limit]


class FakeClock:
    def __init__(self, fixed: datetime | None = None) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        if self._fixed is not None:
            return self._fixed
        return datetime.now(tz=timezone.utc)


class FakeIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def generate(self) -> str:
        self._counter += 1
        return f"test-id-{self._counter:010d}"


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def fixed_time() -> datetime:
    return datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def fake_entry_repo() -> FakeAuditEntryRepository:
    return FakeAuditEntryRepository()


@pytest.fixture
def fake_chain_head_repo() -> FakeAuditChainHeadRepository:
    return FakeAuditChainHeadRepository()


@pytest.fixture
def fake_outbox() -> FakeAuditOutbox:
    return FakeAuditOutbox()


@pytest.fixture
def fake_clock(fixed_time: datetime) -> FakeClock:
    return FakeClock(fixed=fixed_time)


@pytest.fixture
def fake_id_gen() -> FakeIdGenerator:
    return FakeIdGenerator()


@pytest.fixture
def record_use_case(
    fake_entry_repo: FakeAuditEntryRepository,
    fake_chain_head_repo: FakeAuditChainHeadRepository,
    fake_outbox: FakeAuditOutbox,
    fake_clock: FakeClock,
    fake_id_gen: FakeIdGenerator,
) -> RecordAuditEntryUseCase:
    return RecordAuditEntryUseCase(
        entry_repo=fake_entry_repo,
        chain_head_repo=fake_chain_head_repo,
        outbox=fake_outbox,
        clock=fake_clock,
        id_generator=fake_id_gen,
    )


@pytest.fixture
def get_entry_use_case(
    fake_entry_repo: FakeAuditEntryRepository,
) -> GetAuditEntryUseCase:
    return GetAuditEntryUseCase(entry_repo=fake_entry_repo)


@pytest.fixture
def get_chain_use_case(
    fake_entry_repo: FakeAuditEntryRepository,
) -> GetAuditChainUseCase:
    return GetAuditChainUseCase(entry_repo=fake_entry_repo)


@pytest.fixture
def get_by_correlation_use_case(
    fake_entry_repo: FakeAuditEntryRepository,
) -> GetAuditEntriesByCorrelationUseCase:
    return GetAuditEntriesByCorrelationUseCase(entry_repo=fake_entry_repo)


@pytest.fixture
def get_chain_head_use_case(
    fake_chain_head_repo: FakeAuditChainHeadRepository,
) -> GetAuditChainHeadUseCase:
    return GetAuditChainHeadUseCase(chain_head_repo=fake_chain_head_repo)


# ===================================================================
# RecordAuditEntryUseCase Tests
# ===================================================================


class TestRecordAuditEntryUseCase:
    def test_create_first_entry(
        self,
        record_use_case: RecordAuditEntryUseCase,
        fake_entry_repo: FakeAuditEntryRepository,
        fake_chain_head_repo: FakeAuditChainHeadRepository,
        fake_outbox: FakeAuditOutbox,
    ) -> None:
        request = RecordAuditEntryRequest(
            chain_name="security",
            action="memory.create",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-001",
            result="success",
            actor_type="user",
            actor_id="alice",
        )
        response = record_use_case.execute(request)

        assert response.chain_name == "security"
        assert response.action == "memory.create"
        assert response.policy_decision == "grant"
        assert response.classification == "internal"
        assert response.correlation_id == "corr-001"
        assert response.result == "success"
        assert response.actor_type == "user"
        assert response.actor_id == "alice"
        assert response.entry_index == 0
        assert response.previous_hash_hex is None
        assert len(response.entry_hash_hex) == 64  # SHA-256 hex

        # Verify persistence
        stored_entry_id = AuditEntryId(
            value=__import__("uuid", fromlist=["UUID"]).UUID(response.entry_id)
        )
        assert fake_entry_repo.find_by_id(stored_entry_id) is not None

        # Verify chain head
        head = fake_chain_head_repo.find_by_chain("security")
        assert head is not None
        assert head.entries_count == 1
        assert head.head_hash is not None

        # Verify outbox
        unpublished = fake_outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert str(unpublished[0].entry_id) == response.entry_id

    def test_create_second_entry_chains_correctly(
        self,
        record_use_case: RecordAuditEntryUseCase,
        fake_entry_repo: FakeAuditEntryRepository,
        fake_chain_head_repo: FakeAuditChainHeadRepository,
        fake_outbox: FakeAuditOutbox,
    ) -> None:
        req1 = RecordAuditEntryRequest(
            chain_name="chain-a",
            action="first",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-a",
            result="success",
            actor_type="user",
            actor_id="alice",
        )
        resp1 = record_use_case.execute(req1)

        req2 = RecordAuditEntryRequest(
            chain_name="chain-a",
            action="second",
            policy_decision="deny",
            classification="sensitive",
            correlation_id="corr-b",
            result="denied",
            actor_type="agent",
            actor_id="jarvis",
        )
        resp2 = record_use_case.execute(req2)

        assert resp2.entry_index == 1
        assert resp2.previous_hash_hex == resp1.entry_hash_hex

        # Chain head updated
        head = fake_chain_head_repo.find_by_chain("chain-a")
        assert head is not None
        assert head.entries_count == 2

        # Two events in outbox
        assert len(fake_outbox.fetch_unpublished()) == 2

    def test_create_ten_entries_sequential(
        self,
        record_use_case: RecordAuditEntryUseCase,
    ) -> None:
        for i in range(10):
            resp = record_use_case.execute(
                RecordAuditEntryRequest(
                    chain_name="chain-seq",
                    action=f"step.{i}",
                    policy_decision="grant",
                    classification="public",
                    correlation_id=f"corr-s{i}",
                    result="success",
                    actor_type="service",
                    actor_id="tester",
                )
            )
            assert resp.entry_index == i

    def test_restricted_classification_requires_reason(
        self,
        record_use_case: RecordAuditEntryUseCase,
    ) -> None:
        request = RecordAuditEntryRequest(
            chain_name="security",
            action="restricted.access",
            policy_decision="grant",
            classification="restricted",
            correlation_id="corr-restrict",
            result="denied",
            actor_type="user",
            actor_id="alice",
            redacted_reason=None,
        )
        with pytest.raises(Exception, match="Restricted"):
            record_use_case.execute(request)

    def test_restricted_with_reason_succeeds(
        self,
        record_use_case: RecordAuditEntryUseCase,
    ) -> None:
        request = RecordAuditEntryRequest(
            chain_name="security",
            action="restricted.access",
            policy_decision="deny",
            classification="restricted",
            correlation_id="corr-restrict-ok",
            result="denied",
            actor_type="user",
            actor_id="alice",
            redacted_reason="Legal hold",
        )
        response = record_use_case.execute(request)
        assert response.classification == "restricted"

    def test_all_nullable_fields_omitted(
        self,
        record_use_case: RecordAuditEntryUseCase,
    ) -> None:
        request = RecordAuditEntryRequest(
            chain_name="minimal",
            action="test.minimal",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-min",
            result="success",
            actor_type="service",
            actor_id="svc",
        )
        response = record_use_case.execute(request)
        assert response.actor_id == "svc"
        assert response.entry_index == 0

    def test_explicit_occurred_at(
        self,
        record_use_case: RecordAuditEntryUseCase,
    ) -> None:
        dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        request = RecordAuditEntryRequest(
            chain_name="time-test",
            action="backdated",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-time",
            result="success",
            actor_type="user",
            actor_id="alice",
            occurred_at=dt,
        )
        response = record_use_case.execute(request)
        assert response.occurred_at == dt

    def test_outbox_event_fields(
        self,
        record_use_case: RecordAuditEntryUseCase,
        fake_outbox: FakeAuditOutbox,
    ) -> None:
        request = RecordAuditEntryRequest(
            chain_name="consent",
            action="consent.revoke",
            policy_decision="deny",
            classification="sensitive",
            correlation_id="corr-ob-field",
            result="denied",
            actor_type="agent",
            actor_id="jarvis",
        )
        response = record_use_case.execute(request)

        unpublished = fake_outbox.fetch_unpublished()
        event = unpublished[0]
        assert str(event.entry_id) == response.entry_id
        assert event.chain_name == "consent"
        assert event.action == "consent.revoke"
        assert event.actor_type == "agent"
        assert event.actor_id == "jarvis"
        assert event.correlation_id == "corr-ob-field"
        assert event.entry_index == 0

    def test_chain_head_isolated_per_chain(
        self,
        record_use_case: RecordAuditEntryUseCase,
        fake_chain_head_repo: FakeAuditChainHeadRepository,
    ) -> None:
        record_use_case.execute(
            RecordAuditEntryRequest(
                chain_name="alpha",
                action="a1",
                policy_decision="grant",
                classification="public",
                correlation_id="ca1",
                result="ok",
                actor_type="user",
                actor_id="u1",
            )
        )
        record_use_case.execute(
            RecordAuditEntryRequest(
                chain_name="beta",
                action="b1",
                policy_decision="grant",
                classification="public",
                correlation_id="cb1",
                result="ok",
                actor_type="user",
                actor_id="u2",
            )
        )
        record_use_case.execute(
            RecordAuditEntryRequest(
                chain_name="alpha",
                action="a2",
                policy_decision="grant",
                classification="public",
                correlation_id="ca2",
                result="ok",
                actor_type="user",
                actor_id="u1",
            )
        )

        alpha_head = fake_chain_head_repo.find_by_chain("alpha")
        beta_head = fake_chain_head_repo.find_by_chain("beta")
        assert alpha_head is not None
        assert alpha_head.entries_count == 2
        assert beta_head is not None
        assert beta_head.entries_count == 1


# ===================================================================
# GetAuditEntryUseCase Tests
# ===================================================================


class TestGetAuditEntryUseCase:
    def test_find_existing_entry(
        self,
        record_use_case: RecordAuditEntryUseCase,
        get_entry_use_case: GetAuditEntryUseCase,
    ) -> None:
        create_resp = record_use_case.execute(
            RecordAuditEntryRequest(
                chain_name="security",
                action="find.me",
                policy_decision="grant",
                classification="internal",
                correlation_id="corr-find",
                result="success",
                actor_type="user",
                actor_id="alice",
            )
        )
        response = get_entry_use_case.execute(
            GetAuditEntryRequest(entry_id=create_resp.entry_id)
        )
        assert response.entry_id == create_resp.entry_id
        assert response.chain_name == "security"
        assert response.action == "find.me"
        assert response.entry_hash_hex == create_resp.entry_hash_hex
        assert response.entry_index == 0

    def test_nonexistent_entry_raises(
        self,
        get_entry_use_case: GetAuditEntryUseCase,
    ) -> None:
        request = GetAuditEntryRequest(
            entry_id="00000000-0000-0000-0000-000000000000"
        )
        with pytest.raises(AuditEntryNotFoundError):
            get_entry_use_case.execute(request)

    def test_target_fields_present(
        self,
        record_use_case: RecordAuditEntryUseCase,
        get_entry_use_case: GetAuditEntryUseCase,
    ) -> None:
        create_resp = record_use_case.execute(
            RecordAuditEntryRequest(
                chain_name="system",
                action="service.stop",
                policy_decision="grant",
                classification="internal",
                correlation_id="corr-target",
                result="success",
                actor_type="service",
                actor_id="audit-svc",
                target_type="service",
                target_ref="notification-svc",
            )
        )
        response = get_entry_use_case.execute(
            GetAuditEntryRequest(entry_id=create_resp.entry_id)
        )
        assert response.target_type == "service"
        assert response.target_ref == "notification-svc"


# ===================================================================
# GetAuditChainUseCase Tests
# ===================================================================


class TestGetAuditChainUseCase:
    def test_get_entire_chain(
        self,
        record_use_case: RecordAuditEntryUseCase,
        get_chain_use_case: GetAuditChainUseCase,
    ) -> None:
        for i in range(5):
            record_use_case.execute(
                RecordAuditEntryRequest(
                    chain_name="chain-full",
                    action=f"step.{i}",
                    policy_decision="grant",
                    classification="public",
                    correlation_id=f"corr-{i}",
                    result="success",
                    actor_type="user",
                    actor_id="alice",
                )
            )
        response = get_chain_use_case.execute(
            GetAuditChainRequest(chain_name="chain-full")
        )
        assert len(response.entries) == 5
        assert response.total == 5
        assert response.entries[0].entry_index == 0
        assert response.entries[4].entry_index == 4

    def test_get_chain_empty(self, get_chain_use_case: GetAuditChainUseCase) -> None:
        response = get_chain_use_case.execute(
            GetAuditChainRequest(chain_name="nonexistent")
        )
        assert response.entries == []
        assert response.total == 0

    def test_get_chain_with_since_index(
        self,
        record_use_case: RecordAuditEntryUseCase,
        get_chain_use_case: GetAuditChainUseCase,
    ) -> None:
        for i in range(10):
            record_use_case.execute(
                RecordAuditEntryRequest(
                    chain_name="chain-since",
                    action=f"step.{i}",
                    policy_decision="grant",
                    classification="public",
                    correlation_id=f"corr-s{i}",
                    result="success",
                    actor_type="user",
                    actor_id="alice",
                )
            )
        response = get_chain_use_case.execute(
            GetAuditChainRequest(chain_name="chain-since", since_index=7)
        )
        assert len(response.entries) == 3
        assert response.entries[0].entry_index == 7
        assert response.entries[2].entry_index == 9

    def test_get_chain_pagination(
        self,
        record_use_case: RecordAuditEntryUseCase,
        get_chain_use_case: GetAuditChainUseCase,
    ) -> None:
        for i in range(10):
            record_use_case.execute(
                RecordAuditEntryRequest(
                    chain_name="chain-page",
                    action=f"step.{i}",
                    policy_decision="grant",
                    classification="public",
                    correlation_id=f"corr-p{i}",
                    result="success",
                    actor_type="user",
                    actor_id="alice",
                )
            )
        page = get_chain_use_case.execute(
            GetAuditChainRequest(
                chain_name="chain-page", limit=3, offset=5
            )
        )
        assert len(page.entries) == 3
        assert page.entries[0].entry_index == 5
        assert page.entries[2].entry_index == 7


# ===================================================================
# GetAuditEntriesByCorrelationUseCase Tests
# ===================================================================


class TestGetAuditEntriesByCorrelationUseCase:
    def test_find_by_correlation(
        self,
        record_use_case: RecordAuditEntryUseCase,
        get_by_correlation_use_case: GetAuditEntriesByCorrelationUseCase,
    ) -> None:
        record_use_case.execute(
            RecordAuditEntryRequest(
                chain_name="security",
                action="event.1",
                policy_decision="grant",
                classification="public",
                correlation_id="corr-shared",
                result="success",
                actor_type="user",
                actor_id="alice",
            )
        )
        record_use_case.execute(
            RecordAuditEntryRequest(
                chain_name="consent",
                action="event.2",
                policy_decision="deny",
                classification="sensitive",
                correlation_id="corr-shared",
                result="denied",
                actor_type="agent",
                actor_id="jarvis",
            )
        )
        record_use_case.execute(
            RecordAuditEntryRequest(
                chain_name="system",
                action="event.3",
                policy_decision="grant",
                classification="internal",
                correlation_id="corr-other",
                result="success",
                actor_type="service",
                actor_id="svc",
            )
        )
        response = get_by_correlation_use_case.execute(
            GetAuditEntriesByCorrelationRequest(correlation_id="corr-shared")
        )
        assert len(response.entries) == 2
        assert all(
            e.correlation_id == "corr-shared" for e in response.entries
        )

    def test_no_matches(
        self,
        get_by_correlation_use_case: GetAuditEntriesByCorrelationUseCase,
    ) -> None:
        response = get_by_correlation_use_case.execute(
            GetAuditEntriesByCorrelationRequest(
                correlation_id="nonexistent"
            )
        )
        assert response.entries == []


# ===================================================================
# GetAuditChainHeadUseCase Tests
# ===================================================================


class TestGetAuditChainHeadUseCase:
    def test_existing_chain(
        self,
        record_use_case: RecordAuditEntryUseCase,
        get_chain_head_use_case: GetAuditChainHeadUseCase,
    ) -> None:
        record_use_case.execute(
            RecordAuditEntryRequest(
                chain_name="head-test",
                action="first",
                policy_decision="grant",
                classification="public",
                correlation_id="corr-head",
                result="success",
                actor_type="user",
                actor_id="alice",
            )
        )
        response = get_chain_head_use_case.execute(
            GetAuditChainHeadRequest(chain_name="head-test")
        )
        assert response.chain_name == "head-test"
        assert response.entries_count == 1
        assert len(response.head_hash_hex) == 64

    def test_nonexistent_chain(
        self,
        get_chain_head_use_case: GetAuditChainHeadUseCase,
    ) -> None:
        with pytest.raises(ChainNotFoundError):
            get_chain_head_use_case.execute(
                GetAuditChainHeadRequest(chain_name="nonexistent")
            )

    def test_entries_count_after_multiple_entries(
        self,
        record_use_case: RecordAuditEntryUseCase,
        get_chain_head_use_case: GetAuditChainHeadUseCase,
    ) -> None:
        for i in range(7):
            record_use_case.execute(
                RecordAuditEntryRequest(
                    chain_name="multi-head",
                    action=f"step.{i}",
                    policy_decision="grant",
                    classification="public",
                    correlation_id=f"corr-m{i}",
                    result="success",
                    actor_type="user",
                    actor_id="alice",
                )
            )
        response = get_chain_head_use_case.execute(
            GetAuditChainHeadRequest(chain_name="multi-head")
        )
        assert response.entries_count == 7


# ===================================================================
# Integration: Record + Query roundtrip
# ===================================================================


class TestUseCaseIntegration:
    def test_record_then_query_all_paths(
        self,
        record_use_case: RecordAuditEntryUseCase,
        get_entry_use_case: GetAuditEntryUseCase,
        get_chain_use_case: GetAuditChainUseCase,
        get_by_correlation_use_case: GetAuditEntriesByCorrelationUseCase,
        get_chain_head_use_case: GetAuditChainHeadUseCase,
    ) -> None:
        resp = record_use_case.execute(
            RecordAuditEntryRequest(
                chain_name="integration",
                action="test.all",
                policy_decision="grant",
                classification="sensitive",
                correlation_id="corr-int",
                result="success",
                actor_type="service",
                actor_id="audit-svc",
                target_type="system",
                target_ref="integration-test",
            )
        )

        # Query by ID
        by_id = get_entry_use_case.execute(
            GetAuditEntryRequest(entry_id=resp.entry_id)
        )
        assert by_id.entry_id == resp.entry_id

        # Query by chain
        chain = get_chain_use_case.execute(
            GetAuditChainRequest(chain_name="integration")
        )
        assert len(chain.entries) == 1

        # Query by correlation
        by_corr = get_by_correlation_use_case.execute(
            GetAuditEntriesByCorrelationRequest(correlation_id="corr-int")
        )
        assert len(by_corr.entries) == 1

        # Query head
        head = get_chain_head_use_case.execute(
            GetAuditChainHeadRequest(chain_name="integration")
        )
        assert head.entries_count == 1

    def test_exception_inheritance(self) -> None:
        assert issubclass(AuditEntryNotFoundError, UseCaseError)
        assert issubclass(ChainNotFoundError, UseCaseError)
