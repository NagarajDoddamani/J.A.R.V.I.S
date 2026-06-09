from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import memory
from backend.core.database import get_db
from backend.memory.adapters.outbound.clock import SystemClockAdapter
from backend.memory.adapters.outbound.mapper import (
    ConsentMapperImpl,
    MemoryMapperImpl,
)
from backend.memory.adapters.outbound.models import Base
from backend.memory.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyConsentRepository,
    SqlAlchemyMemoryRepository,
)
from backend.memory.application.use_cases.dto import (
    CreateMemoryRequest,
    CreateMemoryResponse,
    DeleteMemoryResponse,
    GrantConsentRequest,
    GrantConsentResponse,
    MemoryResponse,
    RevokeConsentResponse,
    SearchMemoriesResponse,
    UpdateMemoryResponse,
)
from backend.memory.domain.model import (
    ConsentId,
    ConsentRecord,
    ConsentStatus,
    Memory,
    MemoryCategory,
    MemoryContent,
    MemoryId,
    Provenance,
    RetentionPolicy,
    RevisionNumber,
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
def client(session):
    def _override_get_db():
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    app = FastAPI()
    app.include_router(memory.router, prefix="/api/v1/memory")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def clock():
    return SystemClockAdapter()


@pytest.fixture
def consent_repo(session):
    return SqlAlchemyConsentRepository(session, mapper=ConsentMapperImpl())


@pytest.fixture
def memory_repo(session):
    return SqlAlchemyMemoryRepository(session, mapper=MemoryMapperImpl())


def create_active_consent(consent_repo, clock) -> str:
    consent = ConsentRecord(consent_id=ConsentId(), status=ConsentStatus.ACTIVE)
    consent_repo.save(consent)
    return str(consent.consent_id)


def create_memory_in_repo(consent_repo, memory_repo, clock, content="Test content") -> str:
    cid = create_active_consent(consent_repo, clock)
    memory = Memory(
        memory_id=MemoryId(),
        consent_id=ConsentId(value=__import__("uuid").UUID(cid)),
        content=MemoryContent(value=content),
        category=MemoryCategory.GENERAL,
        source_type="user_input",
        source_id=None,
        provenance=Provenance(
            source="user_input", timestamp=clock.now(), actor_id="test"
        ),
        classification="public",
        sensitivity="public",
        retention=RetentionPolicy(policy="persistent"),
        revision=RevisionNumber(value=1),
        created_at=clock.now(),
    )
    memory_repo.save(memory)
    return str(memory.memory_id), cid


class TestCreateMemory:
    URL = "/api/v1/memory/memories"

    def test_create_memory_success(self, client, session, consent_repo, clock) -> None:
        cid = create_active_consent(consent_repo, clock)
        session.commit()
        resp = client.post(
            self.URL,
            json={
                "consent_id": cid,
                "content": "Hello world",
                "category": "general",
                "source_type": "user_input",
                "provenance_source": "user_input",
                "classification": "public",
                "sensitivity": "public",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "Hello world"
        assert data["category"] == "general"

    def test_create_memory_response_shape(self, client, session, consent_repo, clock) -> None:
        cid = create_active_consent(consent_repo, clock)
        session.commit()
        resp = client.post(
            self.URL,
            json={
                "consent_id": cid,
                "content": "Shape test",
                "category": "insight",
                "source_type": "inference",
                "provenance_source": "inference",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "memory_id" in data
        assert "consent_id" in data
        assert "content" in data
        assert "category" in data
        assert "source_type" in data
        assert "classification" in data
        assert "sensitivity" in data
        assert "retention_policy" in data
        assert "retention_status" in data
        assert "revision" in data
        assert "created_at" in data

    def test_create_memory_inactive_consent_returns_400(self, client, session, clock) -> None:
        cid = str(ConsentId())
        session.commit()
        resp = client.post(
            self.URL,
            json={
                "consent_id": cid,
                "content": "test",
                "category": "general",
                "source_type": "user_input",
                "provenance_source": "user_input",
            },
        )
        assert resp.status_code == 400

    def test_create_memory_nonexistent_consent_returns_400(self, client) -> None:
        resp = client.post(
            self.URL,
            json={
                "consent_id": "00000000-0000-0000-0000-000000000000",
                "content": "test",
                "category": "general",
                "source_type": "user_input",
                "provenance_source": "user_input",
            },
        )
        assert resp.status_code == 400

    def test_create_memory_empty_content_returns_422(self, client, session, consent_repo, clock) -> None:
        cid = create_active_consent(consent_repo, clock)
        session.commit()
        resp = client.post(
            self.URL,
            json={
                "consent_id": cid,
                "content": "",
                "category": "general",
                "source_type": "user_input",
                "provenance_source": "user_input",
            },
        )
        assert resp.status_code == 422


class TestUpdateMemory:
    URL = "/api/v1/memory/memories"

    def test_update_memory_success(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock)
        session.commit()
        resp = client.patch(
            f"{self.URL}/{mid}",
            json={"content": "Updated content", "memory_id": mid},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "Updated content"

    def test_update_memory_not_found(self, client) -> None:
        resp = client.patch(
            f"{self.URL}/00000000-0000-0000-0000-000000000000",
            json={"content": "test", "memory_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 404

    def test_update_memory_deleted_returns_400(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock)
        session.commit()
        client.delete(f"{self.URL}/{mid}")
        resp = client.patch(
            f"{self.URL}/{mid}",
            json={"content": "Should fail", "memory_id": mid},
        )
        assert resp.status_code == 400

    def test_update_memory_response_shape(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock)
        session.commit()
        resp = client.patch(
            f"{self.URL}/{mid}",
            json={"content": "Shape", "memory_id": mid},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "memory_id" in data
        assert "consent_id" in data
        assert "content" in data
        assert "category" in data
        assert "revision" in data
        assert "updated_at" in data

    def test_update_memory_revoked_consent_returns_422(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock)
        consent = consent_repo.find_by_id(ConsentId(value=__import__("uuid").UUID(cid)))
        if consent:
            consent.revoke()
            consent_repo.save(consent)
        session.commit()
        resp = client.patch(
            f"{self.URL}/{mid}",
            json={"content": "Should fail", "memory_id": mid},
        )
        assert resp.status_code == 422


class TestDeleteMemory:
    URL = "/api/v1/memory/memories"

    def test_delete_memory_success(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock)
        session.commit()
        resp = client.delete(f"{self.URL}/{mid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "deleted_at" in data

    def test_delete_memory_not_found(self, client) -> None:
        resp = client.delete(
            f"{self.URL}/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_delete_memory_twice_returns_400(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock)
        session.commit()
        client.delete(f"{self.URL}/{mid}")
        resp = client.delete(f"{self.URL}/{mid}")
        assert resp.status_code == 400

    def test_delete_memory_response_shape(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock)
        session.commit()
        resp = client.delete(f"{self.URL}/{mid}")
        data = resp.json()
        assert "memory_id" in data
        assert "deleted_at" in data
        assert "revision" in data


class TestGetMemory:
    URL = "/api/v1/memory/memories"

    def test_get_memory_success(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock)
        session.commit()
        resp = client.get(f"{self.URL}/{mid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["memory_id"] == mid

    def test_get_memory_not_found(self, client) -> None:
        resp = client.get(
            f"{self.URL}/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_get_memory_response_shape(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock)
        session.commit()
        resp = client.get(f"{self.URL}/{mid}")
        data = resp.json()
        assert "memory_id" in data
        assert "consent_id" in data
        assert "content" in data
        assert "category" in data
        assert "source_type" in data
        assert "classification" in data
        assert "sensitivity" in data
        assert "retention_policy" in data
        assert "retention_status" in data
        assert "revision" in data
        assert "created_at" in data

    def test_get_deleted_memory(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock)
        session.commit()
        client.delete(f"{self.URL}/{mid}")
        resp = client.get(f"{self.URL}/{mid}")
        assert resp.status_code == 200
        assert resp.json()["deleted_at"] is not None


class TestSearchMemories:
    URL = "/api/v1/memory/memories"

    def test_search_empty(self, client) -> None:
        resp = client.get(self.URL)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_search_by_consent_id(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock)
        session.commit()
        resp = client.get(f"{self.URL}?consent_id={cid}")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_search_by_category(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock)
        session.commit()
        resp = client.get(f"{self.URL}?category=general")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_search_by_category_none_found(self, client) -> None:
        resp = client.get(f"{self.URL}?category=document")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_search_response_shape(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock)
        session.commit()
        resp = client.get(self.URL)
        data = resp.json()
        assert "memories" in data
        assert "total" in data
        assert isinstance(data["memories"], list)

    def test_search_by_source_type(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock)
        session.commit()
        resp = client.get(f"{self.URL}?source_type=user_input")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestGrantConsent:
    URL = "/api/v1/memory/consents"

    def test_grant_consent_success(self, client) -> None:
        resp = client.post(self.URL, json={})
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "active"
        assert "consent_id" in data
        assert "granted_at" in data

    def test_grant_consent_with_expiry(self, client) -> None:
        future = (datetime.now(tz=timezone.utc) + timedelta(days=30)).isoformat()
        resp = client.post(self.URL, json={"expires_at": future})
        assert resp.status_code == 201

    def test_grant_consent_response_shape(self, client) -> None:
        resp = client.post(self.URL, json={})
        data = resp.json()
        assert "consent_id" in data
        assert "status" in data
        assert "granted_at" in data
        assert "policy_version" in data

    def test_grant_consent_with_policy_version(self, client) -> None:
        resp = client.post(self.URL, json={"policy_version": "2.0"})
        assert resp.status_code == 201
        assert resp.json()["policy_version"] == "2.0"


class TestRevokeConsent:
    URL = "/api/v1/memory/consents"

    def test_revoke_consent_success(self, client, session, consent_repo, clock) -> None:
        cid = create_active_consent(consent_repo, clock)
        session.commit()
        resp = client.post(f"{self.URL}/{cid}/revoke")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "revoked"
        assert "revoked_at" in data

    def test_revoke_consent_not_found(self, client) -> None:
        resp = client.post(
            f"{self.URL}/00000000-0000-0000-0000-000000000000/revoke"
        )
        assert resp.status_code == 404

    def test_revoke_consent_response_shape(self, client, session, consent_repo, clock) -> None:
        cid = create_active_consent(consent_repo, clock)
        session.commit()
        resp = client.post(f"{self.URL}/{cid}/revoke")
        data = resp.json()
        assert "consent_id" in data
        assert "status" in data
        assert "revoked_at" in data


class TestGetConsent:
    URL = "/api/v1/memory/consents"

    def test_get_consent_success(self, client, session, consent_repo, clock) -> None:
        cid = create_active_consent(consent_repo, clock)
        session.commit()
        resp = client.get(f"{self.URL}/{cid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["consent_id"] == cid
        assert data["status"] == "active"

    def test_get_consent_not_found(self, client) -> None:
        resp = client.get(
            f"{self.URL}/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_get_consent_response_shape(self, client, session, consent_repo, clock) -> None:
        cid = create_active_consent(consent_repo, clock)
        session.commit()
        resp = client.get(f"{self.URL}/{cid}")
        data = resp.json()
        assert "consent_id" in data
        assert "status" in data
        assert "policy_version" in data

    def test_get_revoked_consent(self, client, session, consent_repo, clock) -> None:
        cid = create_active_consent(consent_repo, clock)
        session.commit()
        client.post(f"{self.URL}/{cid}/revoke")
        resp = client.get(f"{self.URL}/{cid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "revoked"


class TestIntegrationFlows:
    def test_create_then_get_memory(self, client, session, consent_repo, clock) -> None:
        cid = create_active_consent(consent_repo, clock)
        session.commit()
        create_resp = client.post(
            "/api/v1/memory/memories",
            json={
                "consent_id": cid,
                "content": "Full integration",
                "category": "general",
                "source_type": "user_input",
                "provenance_source": "user_input",
            },
        )
        assert create_resp.status_code == 201
        mid = create_resp.json()["memory_id"]

        get_resp = client.get(f"/api/v1/memory/memories/{mid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["content"] == "Full integration"

    def test_create_update_then_get_memory(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock, "Original")
        session.commit()
        client.patch(f"/api/v1/memory/memories/{mid}", json={"content": "Updated", "memory_id": mid})
        get_resp = client.get(f"/api/v1/memory/memories/{mid}")
        assert get_resp.json()["content"] == "Updated"

    def test_create_delete_then_get_memory(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock)
        session.commit()
        client.delete(f"/api/v1/memory/memories/{mid}")
        get_resp = client.get(f"/api/v1/memory/memories/{mid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["deleted_at"] is not None

    def test_consent_grant_then_memory_create(self, client, session, consent_repo, clock) -> None:
        cid = create_active_consent(consent_repo, clock)
        session.commit()
        resp = client.post(
            "/api/v1/memory/memories",
            json={
                "consent_id": cid,
                "content": "With consent",
                "category": "general",
                "source_type": "user_input",
                "provenance_source": "user_input",
            },
        )
        assert resp.status_code == 201

    def test_consent_create_then_revoke(self, client, session, consent_repo, clock) -> None:
        cid = create_active_consent(consent_repo, clock)
        session.commit()
        revoke_resp = client.post(f"/api/v1/memory/consents/{cid}/revoke")
        assert revoke_resp.status_code == 200
        get_resp = client.get(f"/api/v1/memory/consents/{cid}")
        assert get_resp.json()["status"] == "revoked"

    def test_create_memory_then_search(self, client, session, consent_repo, memory_repo, clock) -> None:
        mid, cid = create_memory_in_repo(consent_repo, memory_repo, clock, "Searchable")
        session.commit()
        resp = client.get("/api/v1/memory/memories?category=general")
        assert resp.json()["total"] >= 1


class TestErrorMapping:
    def test_patch_nonexistent_memory_404(self, client) -> None:
        resp = client.patch(
            "/api/v1/memory/memories/00000000-0000-0000-0000-000000000000",
            json={"content": "nope", "memory_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 404

    def test_get_nonexistent_consent_404(self, client) -> None:
        resp = client.get(
            "/api/v1/memory/consents/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_post_memories_with_invalid_data_422(self, client) -> None:
        resp = client.post(
            "/api/v1/memory/memories",
            json={"content": "", "category": "general", "source_type": "", "provenance_source": ""},
        )
        assert resp.status_code == 422

    def test_create_memory_with_secrets_422(self, client, session, consent_repo, clock) -> None:
        cid = create_active_consent(consent_repo, clock)
        session.commit()
        resp = client.post(
            "/api/v1/memory/memories",
            json={
                "consent_id": cid,
                "content": "my password is secret123",
                "category": "general",
                "source_type": "user_input",
                "provenance_source": "user_input",
            },
        )
        assert resp.status_code == 422
