from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import audit
from backend.audit.adapters.outbound.models import Base, AuditEntryModel, AuditChainHeadModel, AuditOutboxModel
from backend.core.database import get_db

# Strip schema for SQLite compatibility
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
    app.include_router(audit.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


RECORD_BODY = {
    "chain_name": "api-test",
    "action": "test.action",
    "policy_decision": "grant",
    "classification": "public",
    "correlation_id": "corr-api",
    "result": "success",
    "actor_type": "user",
    "actor_id": "alice",
}


class TestRecordAuditEntry:
    URL = "/api/v1/audit/entries"

    def test_create_entry_returns_201(self, client: TestClient) -> None:
        resp = client.post(self.URL, json=RECORD_BODY)
        assert resp.status_code == 201

    def test_create_entry_response_shape(self, client: TestClient) -> None:
        resp = client.post(self.URL, json=RECORD_BODY)
        data = resp.json()
        assert "entry_id" in data
        assert isinstance(data["entry_id"], str)
        assert data["chain_name"] == "api-test"
        assert data["action"] == "test.action"
        assert data["policy_decision"] == "grant"
        assert data["classification"] == "public"
        assert data["correlation_id"] == "corr-api"
        assert data["result"] == "success"
        assert data["actor_type"] == "user"
        assert data["actor_id"] == "alice"
        assert data["entry_index"] == 0
        assert isinstance(data["entry_hash_hex"], str)
        assert data["previous_hash_hex"] is None
        assert isinstance(data["occurred_at"], str)

    def test_create_entry_missing_required_field_returns_422(self, client: TestClient) -> None:
        resp = client.post(self.URL, json={"chain_name": "bad", "action": "missing"})
        assert resp.status_code == 422

    def test_create_entry_invalid_classification_returns_422(self, client: TestClient) -> None:
        body = {**RECORD_BODY, "classification": "ultra-secret"}
        resp = client.post(self.URL, json=body)
        assert resp.status_code == 422

    def test_create_entry_auto_index_increments(self, client: TestClient) -> None:
        body0 = {**RECORD_BODY, "correlation_id": "idx-0", "action": "first"}
        r0 = client.post(self.URL, json=body0)
        assert r0.status_code == 201
        assert r0.json()["entry_index"] == 0

        body1 = {**RECORD_BODY, "correlation_id": "idx-1", "action": "second"}
        r1 = client.post(self.URL, json=body1)
        assert r1.status_code == 201
        assert r1.json()["entry_index"] == 1

    def test_create_entry_linking(self, client: TestClient) -> None:
        body0 = {**RECORD_BODY, "correlation_id": "link-0", "action": "first"}
        r0 = client.post(self.URL, json=body0)
        assert r0.status_code == 201
        hash0 = r0.json()["entry_hash_hex"]

        body1 = {**RECORD_BODY, "correlation_id": "link-1", "action": "second"}
        r1 = client.post(self.URL, json=body1)
        assert r1.status_code == 201
        assert r1.json()["previous_hash_hex"] == hash0

    def test_create_entry_with_all_optional_fields(self, client: TestClient) -> None:
        body = {
            **RECORD_BODY,
            "correlation_id": "corr-all",
            "causation_id": "cause-001",
            "actor_id": "jarvis",
            "target_type": "consent",
            "target_ref": "cons-001",
            "redacted_reason": "User revoked",
            "occurred_at": "2026-06-08T12:00:00+00:00",
        }
        resp = client.post(self.URL, json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["causation_id"] == "cause-001"
        assert data["actor_id"] == "jarvis"

    def test_create_entry_then_get_by_id(self, client: TestClient) -> None:
        body = {**RECORD_BODY, "correlation_id": "rt-1", "action": "roundtrip"}
        post_resp = client.post(self.URL, json=body)
        assert post_resp.status_code == 201
        entry_id = post_resp.json()["entry_id"]

        get_resp = client.get(f"{self.URL}/{entry_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["entry_id"] == entry_id
        assert data["action"] == "roundtrip"
        assert data["chain_name"] == "api-test"


class TestGetAuditEntry:
    URL = "/api/v1/audit/entries"

    def test_get_nonexistent_returns_404(self, client: TestClient) -> None:
        resp = client.get(f"{self.URL}/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_get_entry_response_shape(self, client: TestClient) -> None:
        body = {**RECORD_BODY, "correlation_id": "shape", "action": "get.shape"}
        post_resp = client.post(self.URL, json=body)
        entry_id = post_resp.json()["entry_id"]

        resp = client.get(f"{self.URL}/{entry_id}")
        data = resp.json()
        assert "entry_id" in data
        assert "chain_name" in data
        assert "actor_type" in data
        assert "action" in data
        assert "policy_decision" in data
        assert "classification" in data
        assert "correlation_id" in data
        assert "result" in data
        assert "occurred_at" in data
        assert "previous_hash_hex" in data
        assert "entry_hash_hex" in data
        assert "entry_index" in data


class TestListAuditEntries:
    URL = "/api/v1/audit/entries"

    def test_requires_correlation_id(self, client: TestClient) -> None:
        resp = client.get(self.URL)
        assert resp.status_code == 422

    def test_list_by_correlation(self, client: TestClient) -> None:
        cid = "list-by-corr"
        for i in range(3):
            body = {**RECORD_BODY, "correlation_id": cid, "action": f"evt.{i}"}
            client.post(self.URL, json=body)

        resp = client.get(self.URL, params={"correlation_id": cid})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 3

    def test_list_by_correlation_empty(self, client: TestClient) -> None:
        resp = client.get(self.URL, params={"correlation_id": "nonexistent"})
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetAuditChain:
    URL = "/api/v1/audit/chains"

    def test_get_chain_returns_entries(self, client: TestClient) -> None:
        chain = "test-get-chain"
        for i in range(3):
            body = {**RECORD_BODY, "chain_name": chain, "correlation_id": f"gc-{i}", "action": f"step.{i}"}
            client.post("/api/v1/audit/entries", json=body)

        resp = client.get(f"{self.URL}/{chain}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["entry_index"] == 0
        assert data[2]["entry_index"] == 2

    def test_get_chain_pagination(self, client: TestClient) -> None:
        chain = "test-pagination"
        for i in range(10):
            body = {**RECORD_BODY, "chain_name": chain, "correlation_id": f"pg-{i}", "action": f"step.{i}"}
            client.post("/api/v1/audit/entries", json=body)

        resp = client.get(f"{self.URL}/{chain}", params={"limit": 3, "offset": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert data[0]["entry_index"] == 5

    def test_get_chain_since_index(self, client: TestClient) -> None:
        chain = "test-since"
        for i in range(5):
            body = {**RECORD_BODY, "chain_name": chain, "correlation_id": f"si-{i}", "action": f"step.{i}"}
            client.post("/api/v1/audit/entries", json=body)

        resp = client.get(f"{self.URL}/{chain}", params={"since_index": 3})
        data = resp.json()
        assert len(data) == 2
        assert data[0]["entry_index"] == 3

    def test_get_chain_empty(self, client: TestClient) -> None:
        resp = client.get(f"{self.URL}/nonexistent-chain")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetAuditChainHead:
    URL = "/api/v1/audit/chains"

    def test_get_head(self, client: TestClient) -> None:
        chain = "head-chain"
        for i in range(4):
            body = {**RECORD_BODY, "chain_name": chain, "correlation_id": f"head-{i}", "action": f"step.{i}"}
            client.post("/api/v1/audit/entries", json=body)

        resp = client.get(f"{self.URL}/{chain}/head")
        assert resp.status_code == 200
        data = resp.json()
        assert data["chain_name"] == chain
        assert data["entries_count"] == 4
        assert isinstance(data["head_hash_hex"], str)

    def test_get_head_nonexistent(self, client: TestClient) -> None:
        resp = client.get(f"{self.URL}/no-such-chain/head")
        assert resp.status_code == 404
