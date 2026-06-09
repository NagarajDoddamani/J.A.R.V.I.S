from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.memory.application.ports.clock import MemoryClockPort
from backend.memory.application.ports.id_generator import MemoryIdGeneratorPort
from backend.memory.application.ports.outbox import MemoryOutboxPort
from backend.memory.application.ports.repository import (
    ConsentRepositoryPort,
    MemoryRepositoryPort,
)
from backend.memory.application.use_cases.create_memory import (
    CreateMemoryUseCase,
)
from backend.memory.application.use_cases.delete_memory import (
    DeleteMemoryUseCase,
)
from backend.memory.application.use_cases.dto import (
    ConsentResponse,
    CreateMemoryRequest,
    CreateMemoryResponse,
    DeleteMemoryRequest,
    GetConsentRequest,
    GetMemoryRequest,
    GrantConsentRequest,
    GrantConsentResponse,
    MemoryResponse,
    RevokeConsentRequest,
    RevokeConsentResponse,
    SearchMemoriesRequest,
    SearchMemoriesResponse,
    UpdateMemoryRequest,
    UpdateMemoryResponse,
)
from backend.memory.application.use_cases.exceptions import (
    ConsentNotFoundError,
    ConsentNotActiveError,
    MemoryDeletedError,
    MemoryNotFoundError,
    UseCaseError,
)
from backend.memory.application.use_cases.get_consent import GetConsentUseCase
from backend.memory.application.use_cases.get_memory import GetMemoryUseCase
from backend.memory.application.use_cases.grant_consent import (
    GrantConsentUseCase,
)
from backend.memory.application.use_cases.revoke_consent import (
    RevokeConsentUseCase,
)
from backend.memory.application.use_cases.search_memories import (
    SearchMemoriesUseCase,
)
from backend.memory.application.use_cases.update_memory import (
    UpdateMemoryUseCase,
)
from backend.memory.domain.exceptions import (
    DeletedMemoryUpdateError,
    InvalidConsentTransitionError,
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
    MemoryUpdated,
    Provenance,
    RetentionPolicy,
    RetentionStatus,
    RevisionNumber,
)

# ===================================================================
# Fake port implementations (in-memory)
# ===================================================================


class FakeMemoryRepository:
    def __init__(self) -> None:
        self._store: dict[str, Memory] = {}
        self._saved: list[Memory] = []

    def save(self, memory: Memory) -> None:
        key = str(memory.memory_id)
        self._store[key] = memory
        self._saved.append(memory)

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


class FakeConsentRepository:
    def __init__(self) -> None:
        self._store: dict[str, ConsentRecord] = {}

    def save(self, consent: ConsentRecord) -> None:
        self._store[str(consent.consent_id)] = consent

    def find_by_id(self, consent_id: ConsentId) -> ConsentRecord | None:
        return self._store.get(str(consent_id))

    def find_active(self) -> list[ConsentRecord]:
        return [
            c for c in self._store.values()
            if c.status == ConsentStatus.ACTIVE
        ]

    def find_expired(self) -> list[ConsentRecord]:
        now = datetime.now(tz=timezone.utc)
        return [
            c for c in self._store.values()
            if c.expires_at is not None and c.expires_at < now
        ]

    def find_revoked(self) -> list[ConsentRecord]:
        return [
            c for c in self._store.values()
            if c.status == ConsentStatus.REVOKED
        ]

    def count(self) -> int:
        return len(self._store)


class FakeMemoryOutbox:
    def __init__(self) -> None:
        self._events: list = []
        self._published: set[str] = set()

    def append(self, event: object) -> None:
        self._events.append(event)

    def mark_published(self, event_id: str) -> None:
        self._published.add(event_id)

    def fetch_unpublished(self, limit: int = 100) -> list:
        return [
            e for e in self._events
            if str(getattr(e, "memory_id", getattr(e, "consent_id", ""))) not in self._published
        ][:limit]


class FakeClock:
    def __init__(self, fixed: datetime | None = None) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        if self._fixed is not None:
            return self._fixed
        return datetime.now(tz=timezone.utc)


class FakeMemoryIdGenerator:
    def __init__(self) -> None:
        self._mem_counter = 0
        self._con_counter = 0

    def generate_memory_id(self) -> MemoryId:
        self._mem_counter += 1
        return MemoryId()

    def generate_consent_id(self) -> ConsentId:
        self._con_counter += 1
        return ConsentId()


# ===================================================================
# Helpers
# ===================================================================


def _create_active_consent(
    consent_repo: FakeConsentRepository,
    clock: FakeClock,
    expires_at: datetime | None = None,
) -> ConsentRecord:
    consent = ConsentRecord(
        consent_id=ConsentId(),
        expires_at=expires_at,
    )
    consent.grant()
    consent_repo.save(consent)
    return consent


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def fixed_time() -> datetime:
    return datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def fake_memory_repo() -> FakeMemoryRepository:
    return FakeMemoryRepository()


@pytest.fixture
def fake_consent_repo() -> FakeConsentRepository:
    return FakeConsentRepository()


@pytest.fixture
def fake_outbox() -> FakeMemoryOutbox:
    return FakeMemoryOutbox()


@pytest.fixture
def fake_clock(fixed_time: datetime) -> FakeClock:
    return FakeClock(fixed=fixed_time)


@pytest.fixture
def fake_id_gen() -> FakeMemoryIdGenerator:
    return FakeMemoryIdGenerator()


@pytest.fixture
def active_consent(
    fake_consent_repo: FakeConsentRepository,
    fake_clock: FakeClock,
) -> ConsentRecord:
    return _create_active_consent(fake_consent_repo, fake_clock)


@pytest.fixture
def create_use_case(
    fake_memory_repo: FakeMemoryRepository,
    fake_consent_repo: FakeConsentRepository,
    fake_outbox: FakeMemoryOutbox,
    fake_clock: FakeClock,
    fake_id_gen: FakeMemoryIdGenerator,
) -> CreateMemoryUseCase:
    return CreateMemoryUseCase(
        memory_repo=fake_memory_repo,
        consent_repo=fake_consent_repo,
        outbox=fake_outbox,
        clock=fake_clock,
        id_generator=fake_id_gen,
    )


@pytest.fixture
def update_use_case(
    fake_memory_repo: FakeMemoryRepository,
    fake_consent_repo: FakeConsentRepository,
    fake_outbox: FakeMemoryOutbox,
) -> UpdateMemoryUseCase:
    return UpdateMemoryUseCase(
        memory_repo=fake_memory_repo,
        consent_repo=fake_consent_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def delete_use_case(
    fake_memory_repo: FakeMemoryRepository,
    fake_outbox: FakeMemoryOutbox,
) -> DeleteMemoryUseCase:
    return DeleteMemoryUseCase(
        memory_repo=fake_memory_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def get_memory_use_case(
    fake_memory_repo: FakeMemoryRepository,
) -> GetMemoryUseCase:
    return GetMemoryUseCase(memory_repo=fake_memory_repo)


@pytest.fixture
def search_use_case(
    fake_memory_repo: FakeMemoryRepository,
) -> SearchMemoriesUseCase:
    return SearchMemoriesUseCase(memory_repo=fake_memory_repo)


@pytest.fixture
def grant_consent_use_case(
    fake_consent_repo: FakeConsentRepository,
    fake_outbox: FakeMemoryOutbox,
    fake_clock: FakeClock,
    fake_id_gen: FakeMemoryIdGenerator,
) -> GrantConsentUseCase:
    return GrantConsentUseCase(
        consent_repo=fake_consent_repo,
        outbox=fake_outbox,
        clock=fake_clock,
        id_generator=fake_id_gen,
    )


@pytest.fixture
def revoke_consent_use_case(
    fake_consent_repo: FakeConsentRepository,
    fake_outbox: FakeMemoryOutbox,
) -> RevokeConsentUseCase:
    return RevokeConsentUseCase(
        consent_repo=fake_consent_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def get_consent_use_case(
    fake_consent_repo: FakeConsentRepository,
) -> GetConsentUseCase:
    return GetConsentUseCase(consent_repo=fake_consent_repo)


# ===================================================================
# CreateMemoryUseCase Tests
# ===================================================================


class TestCreateMemoryUseCase:
    def test_happy_path(
        self,
        create_use_case: CreateMemoryUseCase,
        active_consent: ConsentRecord,
        fake_memory_repo: FakeMemoryRepository,
        fake_outbox: FakeMemoryOutbox,
    ) -> None:
        request = CreateMemoryRequest(
            consent_id=str(active_consent.consent_id),
            content="User prefers dark mode",
            category="preference",
            source_type="user_input",
            provenance_source="user_input",
        )
        response = create_use_case.execute(request)

        assert response.content == "User prefers dark mode"
        assert response.category == "preference"
        assert response.source_type == "user_input"
        assert response.revision == 1
        assert response.created_at is not None

        stored_id = UUID(response.memory_id)
        assert fake_memory_repo.find_by_id(stored_id) is not None

        unpublished = fake_outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], MemoryCreated)

    def test_inactive_consent_raises_error(
        self,
        create_use_case: CreateMemoryUseCase,
        fake_consent_repo: FakeConsentRepository,
        fake_clock: FakeClock,
    ) -> None:
        consent = ConsentRecord(consent_id=ConsentId())
        fake_consent_repo.save(consent)

        request = CreateMemoryRequest(
            consent_id=str(consent.consent_id),
            content="test",
            category="general",
            source_type="user_input",
            provenance_source="user_input",
        )
        with pytest.raises(ConsentNotActiveError):
            create_use_case.execute(request)

    def test_missing_consent_raises_error(
        self,
        create_use_case: CreateMemoryUseCase,
    ) -> None:
        request = CreateMemoryRequest(
            consent_id=str(ConsentId()),
            content="test",
            category="general",
            source_type="user_input",
            provenance_source="user_input",
        )
        with pytest.raises(ConsentNotFoundError):
            create_use_case.execute(request)

    def test_with_all_optional_fields(
        self,
        create_use_case: CreateMemoryUseCase,
        active_consent: ConsentRecord,
    ) -> None:
        request = CreateMemoryRequest(
            consent_id=str(active_consent.consent_id),
            content="Sensitive insight",
            category="insight",
            source_type="inference",
            source_id="inf-001",
            provenance_source="inference",
            provenance_actor_id="jarvis",
            classification="sensitive",
            sensitivity="sensitive",
            retention_policy="time_bound",
            retention_ttl_days=90,
            redaction_metadata="redact-field-1",
        )
        response = create_use_case.execute(request)
        assert response.source_id == "inf-001"
        assert response.classification == "sensitive"
        assert response.sensitivity == "sensitive"
        assert response.retention_policy == "time_bound"

    def test_event_in_outbox(
        self,
        create_use_case: CreateMemoryUseCase,
        active_consent: ConsentRecord,
        fake_outbox: FakeMemoryOutbox,
    ) -> None:
        request = CreateMemoryRequest(
            consent_id=str(active_consent.consent_id),
            content="Event test",
            category="general",
            source_type="system",
            provenance_source="system",
        )
        response = create_use_case.execute(request)
        unpublished = fake_outbox.fetch_unpublished()
        event = unpublished[0]
        assert isinstance(event, MemoryCreated)
        assert str(event.memory_id) == response.memory_id
        assert str(event.consent_id) == response.consent_id
        assert event.category.value == "general"

    def test_response_has_correct_fields(
        self,
        create_use_case: CreateMemoryUseCase,
        active_consent: ConsentRecord,
    ) -> None:
        request = CreateMemoryRequest(
            consent_id=str(active_consent.consent_id),
            content="Response test",
            category="document",
            source_type="external",
            provenance_source="external",
        )
        response = create_use_case.execute(request)
        assert isinstance(response, CreateMemoryResponse)
        assert response.memory_id is not None
        assert response.consent_id is not None
        assert response.revision == 1
        assert response.retention_status == "active"

    def test_revoked_consent_raises_error(
        self,
        create_use_case: CreateMemoryUseCase,
        fake_consent_repo: FakeConsentRepository,
        fake_clock: FakeClock,
    ) -> None:
        consent = ConsentRecord(consent_id=ConsentId())
        consent.grant()
        consent.revoke()
        fake_consent_repo.save(consent)

        request = CreateMemoryRequest(
            consent_id=str(consent.consent_id),
            content="test",
            category="general",
            source_type="user_input",
            provenance_source="user_input",
        )
        with pytest.raises(ConsentNotActiveError):
            create_use_case.execute(request)

    def test_memory_persisted_in_repo(
        self,
        create_use_case: CreateMemoryUseCase,
        active_consent: ConsentRecord,
        fake_memory_repo: FakeMemoryRepository,
    ) -> None:
        request = CreateMemoryRequest(
            consent_id=str(active_consent.consent_id),
            content="Persist test",
            category="conversation",
            source_type="conversation",
            provenance_source="conversation",
        )
        response = create_use_case.execute(request)
        assert fake_memory_repo.count() == 1
        stored = fake_memory_repo.find_by_id(UUID(response.memory_id))
        assert stored is not None
        assert stored.content.value == "Persist test"


# ===================================================================
# UpdateMemoryUseCase Tests
# ===================================================================


class TestUpdateMemoryUseCase:
    @pytest.fixture
    def existing_memory(
        self,
        create_use_case: CreateMemoryUseCase,
        active_consent: ConsentRecord,
    ) -> str:
        request = CreateMemoryRequest(
            consent_id=str(active_consent.consent_id),
            content="Original content",
            category="general",
            source_type="user_input",
            provenance_source="user_input",
        )
        response = create_use_case.execute(request)
        return response.memory_id

    def test_happy_path(
        self,
        update_use_case: UpdateMemoryUseCase,
        existing_memory: str,
        fake_outbox: FakeMemoryOutbox,
    ) -> None:
        request = UpdateMemoryRequest(
            memory_id=existing_memory,
            content="Updated content",
        )
        response = update_use_case.execute(request)
        assert response.content == "Updated content"
        assert response.revision == 2
        assert response.updated_at is not None

        unpublished = fake_outbox.fetch_unpublished()
        events = [e for e in unpublished if isinstance(e, MemoryUpdated)]
        assert len(events) == 1

    def test_missing_memory_raises_error(
        self,
        update_use_case: UpdateMemoryUseCase,
    ) -> None:
        request = UpdateMemoryRequest(
            memory_id=str(MemoryId()),
            content="test",
        )
        with pytest.raises(MemoryNotFoundError):
            update_use_case.execute(request)

    def test_deleted_memory_raises_error(
        self,
        update_use_case: UpdateMemoryUseCase,
        existing_memory: str,
        fake_memory_repo: FakeMemoryRepository,
    ) -> None:
        memory = fake_memory_repo.find_by_id(UUID(existing_memory))
        assert memory is not None
        memory.delete()

        request = UpdateMemoryRequest(
            memory_id=existing_memory,
            content="test",
        )
        with pytest.raises(MemoryDeletedError):
            update_use_case.execute(request)

    def test_revoked_consent_blocks_update(
        self,
        update_use_case: UpdateMemoryUseCase,
        existing_memory: str,
        fake_consent_repo: FakeConsentRepository,
        fake_memory_repo: FakeMemoryRepository,
    ) -> None:
        memory = fake_memory_repo.find_by_id(UUID(existing_memory))
        assert memory is not None
        consent = fake_consent_repo.find_by_id(memory.consent_id)
        assert consent is not None
        consent.revoke()
        fake_consent_repo.save(consent)

        request = UpdateMemoryRequest(
            memory_id=existing_memory,
            content="test",
        )
        with pytest.raises(Exception):
            update_use_case.execute(request)

    def test_event_emitted(
        self,
        update_use_case: UpdateMemoryUseCase,
        existing_memory: str,
        fake_outbox: FakeMemoryOutbox,
    ) -> None:
        request = UpdateMemoryRequest(
            memory_id=existing_memory,
            content="Event check",
        )
        update_use_case.execute(request)
        events = fake_outbox.fetch_unpublished()
        updated = [e for e in events if isinstance(e, MemoryUpdated)]
        assert len(updated) == 1
        assert updated[0].revision == 2

    def test_revision_increments(
        self,
        update_use_case: UpdateMemoryUseCase,
        existing_memory: str,
    ) -> None:
        for i in range(3):
            resp = update_use_case.execute(
                UpdateMemoryRequest(
                    memory_id=existing_memory,
                    content=f"Update {i + 1}",
                )
            )
            assert resp.revision == 2 + i

    def test_persists_update(
        self,
        update_use_case: UpdateMemoryUseCase,
        existing_memory: str,
        fake_memory_repo: FakeMemoryRepository,
    ) -> None:
        update_use_case.execute(
            UpdateMemoryRequest(
                memory_id=existing_memory,
                content="Persisted update",
            )
        )
        memory = fake_memory_repo.find_by_id(UUID(existing_memory))
        assert memory is not None
        assert memory.content.value == "Persisted update"
        assert int(memory.revision) == 2


# ===================================================================
# DeleteMemoryUseCase Tests
# ===================================================================


class TestDeleteMemoryUseCase:
    @pytest.fixture
    def existing_memory(
        self,
        create_use_case: CreateMemoryUseCase,
        active_consent: ConsentRecord,
    ) -> str:
        request = CreateMemoryRequest(
            consent_id=str(active_consent.consent_id),
            content="Delete me",
            category="general",
            source_type="user_input",
            provenance_source="user_input",
        )
        return create_use_case.execute(request).memory_id

    def test_soft_delete(
        self,
        delete_use_case: DeleteMemoryUseCase,
        existing_memory: str,
        fake_memory_repo: FakeMemoryRepository,
    ) -> None:
        request = DeleteMemoryRequest(memory_id=existing_memory)
        response = delete_use_case.execute(request)
        assert response.deleted_at is not None
        assert response.revision == 1

        memory = fake_memory_repo.find_by_id(UUID(existing_memory))
        assert memory is not None
        assert memory.is_deleted
        assert memory.deleted_at is not None

    def test_missing_memory_raises_error(
        self,
        delete_use_case: DeleteMemoryUseCase,
    ) -> None:
        request = DeleteMemoryRequest(memory_id=str(MemoryId()))
        with pytest.raises(MemoryNotFoundError):
            delete_use_case.execute(request)

    def test_event_emitted(
        self,
        delete_use_case: DeleteMemoryUseCase,
        existing_memory: str,
        fake_outbox: FakeMemoryOutbox,
    ) -> None:
        request = DeleteMemoryRequest(memory_id=existing_memory)
        delete_use_case.execute(request)
        events = fake_outbox.fetch_unpublished()
        deleted = [e for e in events if isinstance(e, MemoryDeleted)]
        assert len(deleted) == 1
        assert str(deleted[0].memory_id) == existing_memory

    def test_already_deleted_raises_error(
        self,
        delete_use_case: DeleteMemoryUseCase,
        existing_memory: str,
    ) -> None:
        delete_use_case.execute(DeleteMemoryRequest(memory_id=existing_memory))
        with pytest.raises(DeletedMemoryUpdateError):
            delete_use_case.execute(
                DeleteMemoryRequest(memory_id=existing_memory)
            )

    def test_deleted_memory_still_queryable(
        self,
        delete_use_case: DeleteMemoryUseCase,
        existing_memory: str,
        fake_memory_repo: FakeMemoryRepository,
    ) -> None:
        delete_use_case.execute(DeleteMemoryRequest(memory_id=existing_memory))
        deleted_list = fake_memory_repo.find_deleted()
        assert len(deleted_list) == 1
        assert str(deleted_list[0].memory_id) == existing_memory


# ===================================================================
# GetMemoryUseCase Tests
# ===================================================================


class TestGetMemoryUseCase:
    @pytest.fixture
    def existing_memory(
        self,
        create_use_case: CreateMemoryUseCase,
        active_consent: ConsentRecord,
    ) -> str:
        request = CreateMemoryRequest(
            consent_id=str(active_consent.consent_id),
            content="Find me",
            category="document",
            source_type="external",
            source_id="doc-001",
            provenance_source="external",
        )
        return create_use_case.execute(request).memory_id

    def test_returns_memory_response(
        self,
        get_memory_use_case: GetMemoryUseCase,
        existing_memory: str,
    ) -> None:
        request = GetMemoryRequest(memory_id=existing_memory)
        response = get_memory_use_case.execute(request)
        assert isinstance(response, MemoryResponse)
        assert response.memory_id == existing_memory
        assert response.content == "Find me"
        assert response.category == "document"
        assert response.source_type == "external"
        assert response.source_id == "doc-001"

    def test_missing_raises_error(
        self,
        get_memory_use_case: GetMemoryUseCase,
    ) -> None:
        request = GetMemoryRequest(memory_id=str(MemoryId()))
        with pytest.raises(MemoryNotFoundError):
            get_memory_use_case.execute(request)

    def test_response_has_all_fields(
        self,
        get_memory_use_case: GetMemoryUseCase,
        existing_memory: str,
    ) -> None:
        response = get_memory_use_case.execute(
            GetMemoryRequest(memory_id=existing_memory)
        )
        assert response.memory_id is not None
        assert response.consent_id is not None
        assert response.classification is not None
        assert response.sensitivity is not None
        assert response.retention_policy is not None
        assert response.retention_status is not None
        assert response.revision > 0
        assert response.created_at is not None

    def test_error_is_use_case_error(
        self,
        get_memory_use_case: GetMemoryUseCase,
    ) -> None:
        with pytest.raises(UseCaseError):
            get_memory_use_case.execute(
                GetMemoryRequest(memory_id=str(MemoryId()))
            )


# ===================================================================
# SearchMemoriesUseCase Tests
# ===================================================================


class TestSearchMemoriesUseCase:
    @pytest.fixture
    def setup_memories(
        self,
        create_use_case: CreateMemoryUseCase,
        active_consent: ConsentRecord,
        fake_consent_repo: FakeConsentRepository,
        fake_clock: FakeClock,
    ) -> dict[str, str]:
        consent2 = _create_active_consent(fake_consent_repo, fake_clock)

        id1 = create_use_case.execute(CreateMemoryRequest(
            consent_id=str(active_consent.consent_id),
            content="Memory A",
            category="conversation",
            source_type="user_input",
            source_id="chat-1",
            provenance_source="user_input",
        )).memory_id

        id2 = create_use_case.execute(CreateMemoryRequest(
            consent_id=str(active_consent.consent_id),
            content="Memory B",
            category="document",
            source_type="external",
            source_id="doc-1",
            provenance_source="external",
        )).memory_id

        id3 = create_use_case.execute(CreateMemoryRequest(
            consent_id=str(consent2.consent_id),
            content="Memory C",
            category="conversation",
            source_type="user_input",
            source_id="chat-2",
            provenance_source="user_input",
        )).memory_id

        return {
            "mem_a": id1,
            "mem_b": id2,
            "mem_c": id3,
            "consent1": str(active_consent.consent_id),
            "consent2": str(consent2.consent_id),
        }

    def test_search_by_category(
        self,
        search_use_case: SearchMemoriesUseCase,
        setup_memories: dict[str, str],
    ) -> None:
        request = SearchMemoriesRequest(category="conversation")
        response = search_use_case.execute(request)
        assert response.total == 2
        assert all(m.category == "conversation" for m in response.memories)

    def test_search_by_consent_id(
        self,
        search_use_case: SearchMemoriesUseCase,
        setup_memories: dict[str, str],
    ) -> None:
        request = SearchMemoriesRequest(
            consent_id=setup_memories["consent1"]
        )
        response = search_use_case.execute(request)
        assert response.total == 2

    def test_search_by_source_type(
        self,
        search_use_case: SearchMemoriesUseCase,
        setup_memories: dict[str, str],
    ) -> None:
        request = SearchMemoriesRequest(source_type="external")
        response = search_use_case.execute(request)
        assert response.total == 1

    def test_search_by_source_with_id(
        self,
        search_use_case: SearchMemoriesUseCase,
        setup_memories: dict[str, str],
    ) -> None:
        request = SearchMemoriesRequest(
            source_type="user_input", source_id="chat-1"
        )
        response = search_use_case.execute(request)
        assert response.total == 1
        assert response.memories[0].content == "Memory A"

    def test_empty_results(
        self,
        search_use_case: SearchMemoriesUseCase,
    ) -> None:
        request = SearchMemoriesRequest(category="ephemeral")
        response = search_use_case.execute(request)
        assert response.total == 0
        assert response.memories == []

    def test_no_filters_returns_empty(
        self,
        search_use_case: SearchMemoriesUseCase,
    ) -> None:
        request = SearchMemoriesRequest()
        response = search_use_case.execute(request)
        assert response.total == 0

    def test_combined_category_and_consent(
        self,
        search_use_case: SearchMemoriesUseCase,
        setup_memories: dict[str, str],
    ) -> None:
        request = SearchMemoriesRequest(
            category="conversation",
            consent_id=setup_memories["consent1"],
        )
        response = search_use_case.execute(request)
        assert response.total == 1
        assert response.memories[0].content == "Memory A"

    def test_combined_source_and_category(
        self,
        search_use_case: SearchMemoriesUseCase,
        setup_memories: dict[str, str],
    ) -> None:
        request = SearchMemoriesRequest(
            source_type="user_input",
            category="conversation",
        )
        response = search_use_case.execute(request)
        assert response.total == 2


# ===================================================================
# GrantConsentUseCase Tests
# ===================================================================


class TestGrantConsentUseCase:
    def test_happy_path(
        self,
        grant_consent_use_case: GrantConsentUseCase,
        fake_consent_repo: FakeConsentRepository,
    ) -> None:
        request = GrantConsentRequest()
        response = grant_consent_use_case.execute(request)
        assert response.status == "active"
        assert response.granted_at is not None
        assert response.consent_id is not None

        stored = fake_consent_repo.find_by_id(
            ConsentId(value=UUID(response.consent_id))
        )
        assert stored is not None
        assert stored.status == ConsentStatus.ACTIVE

    def test_event_emitted(
        self,
        grant_consent_use_case: GrantConsentUseCase,
        fake_outbox: FakeMemoryOutbox,
    ) -> None:
        request = GrantConsentRequest()
        response = grant_consent_use_case.execute(request)
        unpublished = fake_outbox.fetch_unpublished()
        assert len(unpublished) == 1
        event = unpublished[0]
        assert isinstance(event, ConsentGranted)
        assert str(event.consent_id) == response.consent_id

    def test_with_expiry(
        self,
        grant_consent_use_case: GrantConsentUseCase,
        fake_clock: FakeClock,
    ) -> None:
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        request = GrantConsentRequest(
            expires_at=future,
            policy_version="2.0",
        )
        response = grant_consent_use_case.execute(request)
        assert response.expires_at == future
        assert response.policy_version == "2.0"

    def test_consent_persisted(
        self,
        grant_consent_use_case: GrantConsentUseCase,
        fake_consent_repo: FakeConsentRepository,
    ) -> None:
        request = GrantConsentRequest()
        response = grant_consent_use_case.execute(request)
        assert fake_consent_repo.count() == 1
        active = fake_consent_repo.find_active()
        assert len(active) == 1

    def test_response_type(
        self,
        grant_consent_use_case: GrantConsentUseCase,
    ) -> None:
        request = GrantConsentRequest()
        response = grant_consent_use_case.execute(request)
        assert isinstance(response, GrantConsentResponse)

    def test_granted_at_is_clock_now(
        self,
        grant_consent_use_case: GrantConsentUseCase,
        fixed_time: datetime,
    ) -> None:
        request = GrantConsentRequest()
        response = grant_consent_use_case.execute(request)
        assert response.granted_at == fixed_time


# ===================================================================
# RevokeConsentUseCase Tests
# ===================================================================


class TestRevokeConsentUseCase:
    @pytest.fixture
    def active_consent(
        self,
        grant_consent_use_case: GrantConsentUseCase,
    ) -> str:
        return grant_consent_use_case.execute(GrantConsentRequest()).consent_id

    def test_revoke_active_consent(
        self,
        revoke_consent_use_case: RevokeConsentUseCase,
        active_consent: str,
        fake_consent_repo: FakeConsentRepository,
    ) -> None:
        request = RevokeConsentRequest(consent_id=active_consent)
        response = revoke_consent_use_case.execute(request)
        assert response.status == "revoked"
        assert response.revoked_at is not None

        stored = fake_consent_repo.find_by_id(
            ConsentId(value=UUID(active_consent))
        )
        assert stored is not None
        assert stored.status == ConsentStatus.REVOKED

    def test_missing_consent_raises_error(
        self,
        revoke_consent_use_case: RevokeConsentUseCase,
    ) -> None:
        request = RevokeConsentRequest(consent_id=str(ConsentId()))
        with pytest.raises(ConsentNotFoundError):
            revoke_consent_use_case.execute(request)

    def test_already_revoked_raises_error(
        self,
        revoke_consent_use_case: RevokeConsentUseCase,
        active_consent: str,
    ) -> None:
        revoke_consent_use_case.execute(
            RevokeConsentRequest(consent_id=active_consent)
        )
        with pytest.raises(InvalidConsentTransitionError):
            revoke_consent_use_case.execute(
                RevokeConsentRequest(consent_id=active_consent)
            )

    def test_event_emitted(
        self,
        revoke_consent_use_case: RevokeConsentUseCase,
        active_consent: str,
        fake_outbox: FakeMemoryOutbox,
    ) -> None:
        revoke_consent_use_case.execute(
            RevokeConsentRequest(consent_id=active_consent)
        )
        events = fake_outbox.fetch_unpublished()
        revoked = [e for e in events if isinstance(e, ConsentRevoked)]
        assert len(revoked) == 1

    def test_response_type(
        self,
        revoke_consent_use_case: RevokeConsentUseCase,
        active_consent: str,
    ) -> None:
        response = revoke_consent_use_case.execute(
            RevokeConsentRequest(consent_id=active_consent)
        )
        assert isinstance(response, RevokeConsentResponse)

    def test_revoked_consent_not_active(
        self,
        revoke_consent_use_case: RevokeConsentUseCase,
        active_consent: str,
        fake_consent_repo: FakeConsentRepository,
    ) -> None:
        revoke_consent_use_case.execute(
            RevokeConsentRequest(consent_id=active_consent)
        )
        active = fake_consent_repo.find_active()
        assert len(active) == 0
        revoked = fake_consent_repo.find_revoked()
        assert len(revoked) == 1


# ===================================================================
# GetConsentUseCase Tests
# ===================================================================


class TestGetConsentUseCase:
    @pytest.fixture
    def existing_consent(
        self,
        grant_consent_use_case: GrantConsentUseCase,
    ) -> str:
        return grant_consent_use_case.execute(GrantConsentRequest()).consent_id

    def test_returns_consent_response(
        self,
        get_consent_use_case: GetConsentUseCase,
        existing_consent: str,
    ) -> None:
        request = GetConsentRequest(consent_id=existing_consent)
        response = get_consent_use_case.execute(request)
        assert isinstance(response, ConsentResponse)
        assert response.consent_id == existing_consent
        assert response.status == "active"

    def test_missing_raises_error(
        self,
        get_consent_use_case: GetConsentUseCase,
    ) -> None:
        request = GetConsentRequest(consent_id=str(ConsentId()))
        with pytest.raises(ConsentNotFoundError):
            get_consent_use_case.execute(request)

    def test_response_has_all_fields(
        self,
        get_consent_use_case: GetConsentUseCase,
        existing_consent: str,
    ) -> None:
        response = get_consent_use_case.execute(
            GetConsentRequest(consent_id=existing_consent)
        )
        assert response.consent_id is not None
        assert response.status is not None
        assert response.granted_at is not None
        assert response.policy_version is not None

    def test_error_is_use_case_error(
        self,
        get_consent_use_case: GetConsentUseCase,
    ) -> None:
        with pytest.raises(UseCaseError):
            get_consent_use_case.execute(
                GetConsentRequest(consent_id=str(ConsentId()))
            )


# ===================================================================
# Integration Tests
# ===================================================================


class TestIntegration:
    def test_full_lifecycle(
        self,
        fake_memory_repo: FakeMemoryRepository,
        fake_consent_repo: FakeConsentRepository,
        fake_outbox: FakeMemoryOutbox,
        fake_clock: FakeClock,
        fake_id_gen: FakeMemoryIdGenerator,
    ) -> None:
        create = CreateMemoryUseCase(
            memory_repo=fake_memory_repo,
            consent_repo=fake_consent_repo,
            outbox=fake_outbox,
            clock=fake_clock,
            id_generator=fake_id_gen,
        )
        grant = GrantConsentUseCase(
            consent_repo=fake_consent_repo,
            outbox=fake_outbox,
            clock=fake_clock,
            id_generator=fake_id_gen,
        )
        update = UpdateMemoryUseCase(
            memory_repo=fake_memory_repo,
            consent_repo=fake_consent_repo,
            outbox=fake_outbox,
        )
        delete = DeleteMemoryUseCase(
            memory_repo=fake_memory_repo,
            outbox=fake_outbox,
        )
        get_mem = GetMemoryUseCase(memory_repo=fake_memory_repo)
        search = SearchMemoriesUseCase(memory_repo=fake_memory_repo)
        revoke = RevokeConsentUseCase(
            consent_repo=fake_consent_repo,
            outbox=fake_outbox,
        )
        get_con = GetConsentUseCase(consent_repo=fake_consent_repo)

        # Step 1: Grant consent
        consent_resp = grant.execute(GrantConsentRequest())
        assert consent_resp.status == "active"

        # Step 2: Create memory
        create_resp = create.execute(CreateMemoryRequest(
            consent_id=consent_resp.consent_id,
            content="Integration memory",
            category="general",
            source_type="user_input",
            provenance_source="user_input",
        ))
        assert create_resp.revision == 1

        # Step 3: Get memory
        get_resp = get_mem.execute(
            GetMemoryRequest(memory_id=create_resp.memory_id)
        )
        assert get_resp.content == "Integration memory"

        # Step 4: Update memory
        update_resp = update.execute(UpdateMemoryRequest(
            memory_id=create_resp.memory_id,
            content="Updated integration memory",
        ))
        assert update_resp.revision == 2

        # Step 5: Search
        search_resp = search.execute(
            SearchMemoriesRequest(consent_id=consent_resp.consent_id)
        )
        assert search_resp.total == 1
        assert search_resp.memories[0].revision == 2

        # Step 6: Revoke consent
        revoke_resp = revoke.execute(
            RevokeConsentRequest(consent_id=consent_resp.consent_id)
        )
        assert revoke_resp.status == "revoked"

        # Step 7: Get consent
        get_con_resp = get_con.execute(
            GetConsentRequest(consent_id=consent_resp.consent_id)
        )
        assert get_con_resp.status == "revoked"

        # Step 8: Delete memory
        delete_resp = delete.execute(
            DeleteMemoryRequest(memory_id=create_resp.memory_id)
        )
        assert delete_resp.deleted_at is not None

    def test_outbox_event_sequence(
        self,
        create_use_case: CreateMemoryUseCase,
        active_consent: ConsentRecord,
        update_use_case: UpdateMemoryUseCase,
        delete_use_case: DeleteMemoryUseCase,
        fake_outbox: FakeMemoryOutbox,
    ) -> None:
        create_resp = create_use_case.execute(CreateMemoryRequest(
            consent_id=str(active_consent.consent_id),
            content="Event sequence",
            category="general",
            source_type="user_input",
            provenance_source="user_input",
        ))

        update_use_case.execute(UpdateMemoryRequest(
            memory_id=create_resp.memory_id,
            content="Updated",
        ))

        delete_use_case.execute(DeleteMemoryRequest(
            memory_id=create_resp.memory_id,
        ))

        events = fake_outbox.fetch_unpublished()
        types = [type(e).__name__ for e in events]
        assert types == ["MemoryCreated", "MemoryUpdated", "MemoryDeleted"]

    def test_revision_monotonicity(
        self,
        create_use_case: CreateMemoryUseCase,
        active_consent: ConsentRecord,
        update_use_case: UpdateMemoryUseCase,
    ) -> None:
        create_resp = create_use_case.execute(CreateMemoryRequest(
            consent_id=str(active_consent.consent_id),
            content="Rev test",
            category="general",
            source_type="user_input",
            provenance_source="user_input",
        ))
        assert create_resp.revision == 1

        for expected in range(2, 6):
            resp = update_use_case.execute(UpdateMemoryRequest(
                memory_id=create_resp.memory_id,
                content=f"Revision {expected}",
            ))
            assert resp.revision == expected

    def test_consent_grant_then_create_then_revoke(
        self,
        grant_consent_use_case: GrantConsentUseCase,
        create_use_case: CreateMemoryUseCase,
        revoke_consent_use_case: RevokeConsentUseCase,
        fake_consent_repo: FakeConsentRepository,
    ) -> None:
        consent_resp = grant_consent_use_case.execute(GrantConsentRequest())

        create_use_case.execute(CreateMemoryRequest(
            consent_id=consent_resp.consent_id,
            content="Memory under consent",
            category="general",
            source_type="user_input",
            provenance_source="user_input",
        ))

        revoke_consent_use_case.execute(
            RevokeConsentRequest(consent_id=consent_resp.consent_id)
        )

        stored = fake_consent_repo.find_by_id(
            ConsentId(value=UUID(consent_resp.consent_id))
        )
        assert stored is not None
        assert stored.status == ConsentStatus.REVOKED

    def test_search_after_delete(
        self,
        create_use_case: CreateMemoryUseCase,
        active_consent: ConsentRecord,
        delete_use_case: DeleteMemoryUseCase,
        search_use_case: SearchMemoriesUseCase,
    ) -> None:
        create_resp = create_use_case.execute(CreateMemoryRequest(
            consent_id=str(active_consent.consent_id),
            content="Search after delete",
            category="document",
            source_type="external",
            provenance_source="external",
        ))

        search_before = search_use_case.execute(
            SearchMemoriesRequest(category="document")
        )
        assert search_before.total == 1

        delete_use_case.execute(
            DeleteMemoryRequest(memory_id=create_resp.memory_id)
        )

        search_after = search_use_case.execute(
            SearchMemoriesRequest(category="document")
        )
        assert search_after.total == 1


# ===================================================================
# Exception hierarchy tests
# ===================================================================


class TestExceptions:
    def test_use_case_error_base(self) -> None:
        assert issubclass(MemoryNotFoundError, UseCaseError)
        assert issubclass(ConsentNotFoundError, UseCaseError)
        assert issubclass(ConsentNotActiveError, UseCaseError)
        assert issubclass(MemoryDeletedError, UseCaseError)

    def test_memory_not_found_error_message(self) -> None:
        err = MemoryNotFoundError("mem-001")
        assert "mem-001" in str(err)
        assert err.memory_id == "mem-001"

    def test_consent_not_found_error_message(self) -> None:
        err = ConsentNotFoundError("con-001")
        assert "con-001" in str(err)
        assert err.consent_id == "con-001"

    def test_consent_not_active_error_message(self) -> None:
        err = ConsentNotActiveError("con-001")
        assert "con-001" in str(err)
        assert err.consent_id == "con-001"

    def test_memory_deleted_error_message(self) -> None:
        err = MemoryDeletedError("mem-001")
        assert "mem-001" in str(err)
        assert err.memory_id == "mem-001"
