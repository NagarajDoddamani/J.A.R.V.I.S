from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import knowledge
from backend.core.database import get_db
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
    RegisterSourceResponse,
    SourceResponse,
    DocumentResponse,
)
from backend.knowledge.domain.model import (
    KnowledgeSource,
    KnowledgeSourceId,
    SourceLocation,
    SourceStatus,
    SourceType,
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
    app.include_router(knowledge.router, prefix="/api/v1/knowledge")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def clock():
    return SystemClockAdapter()


@pytest.fixture
def source_repo(session):
    return SqlAlchemyKnowledgeSourceRepository(session, mapper=KnowledgeSourceMapperImpl())


@pytest.fixture
def outbox(session):
    return SqlAlchemyKnowledgeOutboxAdapter(session)


def create_active_source(source_repo, clock) -> str:
    now = clock.now()
    source = KnowledgeSource(
        source_id=KnowledgeSourceId(),
        name="Test Source",
        source_type=SourceType.FILE,
        location=SourceLocation(value="/tmp/test"),
        classification="public",
        status=SourceStatus.ACTIVE,
        created_at=now,
    )
    source_repo.save(source)
    return str(source.source_id)


def create_source_in_repo(source_repo, clock, status=SourceStatus.REGISTERED) -> str:
    now = clock.now()
    source = KnowledgeSource(
        source_id=KnowledgeSourceId(),
        name="Test Source",
        source_type=SourceType.FILE,
        location=SourceLocation(value="/tmp/test"),
        classification="public",
        status=status,
        created_at=now,
    )
    source_repo.save(source)
    return str(source.source_id)


class TestRegisterSource:
    URL = "/api/v1/knowledge/sources"

    def test_register_source_success(self, client) -> None:
        resp = client.post(
            self.URL,
            json={
                "name": "My Source",
                "source_type": "file",
                "location": "/data/source",
                "classification": "public",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Source"
        assert data["source_type"] == "file"
        assert data["status"] == "registered"

    def test_register_source_response_shape(self, client) -> None:
        resp = client.post(
            self.URL,
            json={
                "name": "Shape Test",
                "source_type": "url",
                "location": "https://example.com",
                "classification": "internal",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "source_id" in data
        assert "name" in data
        assert "source_type" in data
        assert "location" in data
        assert "classification" in data
        assert "status" in data
        assert "created_at" in data

    def test_register_source_empty_name_returns_422(self, client) -> None:
        resp = client.post(
            self.URL,
            json={
                "name": "",
                "source_type": "file",
                "location": "/data",
                "classification": "public",
            },
        )
        assert resp.status_code == 422

    def test_register_source_invalid_type_returns_422(self, client) -> None:
        resp = client.post(
            self.URL,
            json={
                "name": "Test",
                "source_type": "invalid_type",
                "location": "/data",
                "classification": "public",
            },
        )
        assert resp.status_code == 422


class TestListSources:
    URL = "/api/v1/knowledge/sources"

    def test_list_sources_empty(self, client) -> None:
        resp = client.get(self.URL)
        assert resp.status_code == 200
        assert resp.json()["sources"] == []

    def test_list_sources_with_data(self, client, session, source_repo, clock) -> None:
        create_active_source(source_repo, clock)
        session.commit()
        resp = client.get(self.URL)
        assert resp.status_code == 200
        assert len(resp.json()["sources"]) >= 1

    def test_list_sources_response_shape(self, client, session, source_repo, clock) -> None:
        create_active_source(source_repo, clock)
        session.commit()
        resp = client.get(self.URL)
        data = resp.json()
        assert "sources" in data
        assert isinstance(data["sources"], list)
        if data["sources"]:
            item = data["sources"][0]
            assert "source_id" in item
            assert "name" in item
            assert "status" in item


class TestGetSource:
    URL = "/api/v1/knowledge/sources"

    def test_get_source_success(self, client, session, source_repo, clock) -> None:
        sid = create_source_in_repo(source_repo, clock)
        session.commit()
        resp = client.get(f"{self.URL}/{sid}")
        assert resp.status_code == 200
        assert resp.json()["source_id"] == sid

    def test_get_source_not_found(self, client) -> None:
        resp = client.get(
            f"{self.URL}/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_get_source_response_shape(self, client, session, source_repo, clock) -> None:
        sid = create_source_in_repo(source_repo, clock)
        session.commit()
        resp = client.get(f"{self.URL}/{sid}")
        data = resp.json()
        assert "source_id" in data
        assert "name" in data
        assert "source_type" in data
        assert "location" in data
        assert "classification" in data
        assert "status" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "deleted_at" in data


class TestDeleteSource:
    URL = "/api/v1/knowledge/sources"

    def test_delete_source_success(self, client, session, source_repo, clock) -> None:
        sid = create_source_in_repo(source_repo, clock)
        session.commit()
        resp = client.delete(f"{self.URL}/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "deleted_at" in data

    def test_delete_source_not_found(self, client) -> None:
        resp = client.delete(
            f"{self.URL}/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_delete_source_response_shape(self, client, session, source_repo, clock) -> None:
        sid = create_source_in_repo(source_repo, clock)
        session.commit()
        resp = client.delete(f"{self.URL}/{sid}")
        data = resp.json()
        assert "source_id" in data
        assert "deleted_at" in data


class TestIngestDocument:
    URL = "/api/v1/knowledge/documents"

    def test_ingest_document_success(self, client, session, source_repo, clock) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        resp = client.post(
            self.URL,
            json={
                "source_id": sid,
                "title": "Test Document",
                "checksum": "abc123",
                "classification": "public",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Document"
        assert data["status"] == "pending"

    def test_ingest_document_response_shape(self, client, session, source_repo, clock) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        resp = client.post(
            self.URL,
            json={
                "source_id": sid,
                "title": "Shape Test",
                "checksum": "def456",
                "classification": "internal",
            },
        )
        data = resp.json()
        assert "document_id" in data
        assert "source_id" in data
        assert "title" in data
        assert "checksum" in data
        assert "classification" in data
        assert "status" in data
        assert "revision" in data
        assert "created_at" in data

    def test_ingest_document_inactive_source_returns_400(self, client) -> None:
        resp = client.post(
            self.URL,
            json={
                "source_id": "00000000-0000-0000-0000-000000000000",
                "title": "Test",
                "checksum": "abc",
                "classification": "public",
            },
        )
        assert resp.status_code == 404

    def test_ingest_document_empty_title_returns_422(
        self, client, session, source_repo, clock
    ) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        resp = client.post(
            self.URL,
            json={
                "source_id": sid,
                "title": "",
                "checksum": "abc",
                "classification": "public",
            },
        )
        assert resp.status_code == 400


class TestGetDocument:
    URL = "/api/v1/knowledge/documents"

    def test_get_document_success(self, client, session, source_repo, clock) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        doc_resp = client.post(
            "/api/v1/knowledge/documents",
            json={
                "source_id": sid,
                "title": "Get Test",
                "checksum": "xyz789",
                "classification": "public",
            },
        )
        doc_id = doc_resp.json()["document_id"]
        resp = client.get(f"{self.URL}/{doc_id}")
        assert resp.status_code == 200
        assert resp.json()["document_id"] == doc_id

    def test_get_document_not_found(self, client) -> None:
        resp = client.get(
            f"{self.URL}/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_get_document_response_shape(self, client, session, source_repo, clock) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        doc_resp = client.post(
            "/api/v1/knowledge/documents",
            json={
                "source_id": sid,
                "title": "Shape",
                "checksum": "abc",
                "classification": "public",
            },
        )
        doc_id = doc_resp.json()["document_id"]
        resp = client.get(f"{self.URL}/{doc_id}")
        data = resp.json()
        assert "document_id" in data
        assert "source_id" in data
        assert "title" in data
        assert "checksum" in data
        assert "classification" in data
        assert "status" in data
        assert "revision" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "deleted_at" in data


class TestCreateChunk:
    URL = "/api/v1/knowledge/chunks"

    def test_create_chunk_success(self, client, session, source_repo, clock) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        doc_resp = client.post(
            "/api/v1/knowledge/documents",
            json={"source_id": sid, "title": "Doc", "checksum": "abc", "classification": "public"},
        )
        doc_id = doc_resp.json()["document_id"]
        resp = client.post(
            self.URL,
            json={"document_id": doc_id, "chunk_index": 0, "content": "Hello world"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["chunk_index"] == 0
        assert data["content"] == "Hello world"

    def test_create_chunk_response_shape(self, client, session, source_repo, clock) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        doc_resp = client.post(
            "/api/v1/knowledge/documents",
            json={"source_id": sid, "title": "Doc", "checksum": "abc", "classification": "public"},
        )
        doc_id = doc_resp.json()["document_id"]
        resp = client.post(
            self.URL,
            json={"document_id": doc_id, "chunk_index": 0, "content": "Shape"},
        )
        data = resp.json()
        assert "chunk_id" in data
        assert "document_id" in data
        assert "chunk_index" in data
        assert "content" in data
        assert "classification" in data
        assert "created_at" in data

    def test_create_chunk_nonexistent_document_returns_404(self, client) -> None:
        resp = client.post(
            self.URL,
            json={
                "document_id": "00000000-0000-0000-0000-000000000000",
                "chunk_index": 0,
                "content": "test",
            },
        )
        assert resp.status_code == 404

    def test_create_chunk_empty_content_returns_400(
        self, client, session, source_repo, clock
    ) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        doc_resp = client.post(
            "/api/v1/knowledge/documents",
            json={"source_id": sid, "title": "Doc", "checksum": "abc", "classification": "public"},
        )
        doc_id = doc_resp.json()["document_id"]
        resp = client.post(
            self.URL,
            json={"document_id": doc_id, "chunk_index": 0, "content": ""},
        )
        assert resp.status_code == 400


class TestGetChunksByDocument:
    def test_get_chunks_by_document_empty(
        self, client, session, source_repo, clock
    ) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        doc_resp = client.post(
            "/api/v1/knowledge/documents",
            json={"source_id": sid, "title": "Doc", "checksum": "abc", "classification": "public"},
        )
        doc_id = doc_resp.json()["document_id"]
        resp = client.get(f"/api/v1/knowledge/documents/{doc_id}/chunks")
        assert resp.status_code == 200
        assert resp.json()["chunks"] == []

    def test_get_chunks_by_document_with_data(
        self, client, session, source_repo, clock
    ) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        doc_resp = client.post(
            "/api/v1/knowledge/documents",
            json={"source_id": sid, "title": "Doc", "checksum": "abc", "classification": "public"},
        )
        doc_id = doc_resp.json()["document_id"]
        client.post(
            "/api/v1/knowledge/chunks",
            json={"document_id": doc_id, "chunk_index": 0, "content": "First"},
        )
        client.post(
            "/api/v1/knowledge/chunks",
            json={"document_id": doc_id, "chunk_index": 1, "content": "Second"},
        )
        resp = client.get(f"/api/v1/knowledge/documents/{doc_id}/chunks")
        assert resp.status_code == 200
        assert len(resp.json()["chunks"]) == 2


class TestStartIngestion:
    URL = "/api/v1/knowledge/ingestions"

    def test_start_ingestion_success(self, client, session, source_repo, clock) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        resp = client.post(
            self.URL,
            json={"source_id": sid},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "running"
        assert "job_id" in data

    def test_start_ingestion_inactive_source_returns_400(self, client) -> None:
        resp = client.post(
            self.URL,
            json={"source_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 404

    def test_start_ingestion_response_shape(
        self, client, session, source_repo, clock
    ) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        resp = client.post(self.URL, json={"source_id": sid})
        data = resp.json()
        assert "job_id" in data
        assert "source_id" in data
        assert "status" in data
        assert "started_at" in data


class TestCompleteIngestion:
    def test_complete_ingestion_success(
        self, client, session, source_repo, clock
    ) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        job_resp = client.post(
            "/api/v1/knowledge/ingestions",
            json={"source_id": sid},
        )
        job_id = job_resp.json()["job_id"]
        resp = client.post(f"/api/v1/knowledge/ingestions/{job_id}/complete")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "completed_at" in data

    def test_complete_ingestion_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/knowledge/ingestions/00000000-0000-0000-0000-000000000000/complete"
        )
        assert resp.status_code == 404


class TestFailIngestion:
    def test_fail_ingestion_success(
        self, client, session, source_repo, clock
    ) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        job_resp = client.post(
            "/api/v1/knowledge/ingestions",
            json={"source_id": sid},
        )
        job_id = job_resp.json()["job_id"]
        resp = client.post(
            f"/api/v1/knowledge/ingestions/{job_id}/fail",
            json={"error_message": "Something went wrong"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "Something went wrong"

    def test_fail_ingestion_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/knowledge/ingestions/00000000-0000-0000-0000-000000000000/fail",
            json={"error_message": "error"},
        )
        assert resp.status_code == 404


class TestGetIngestionJob:
    def test_get_ingestion_job_success(
        self, client, session, source_repo, clock
    ) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        job_resp = client.post(
            "/api/v1/knowledge/ingestions",
            json={"source_id": sid},
        )
        job_id = job_resp.json()["job_id"]
        resp = client.get(f"/api/v1/knowledge/ingestions/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == job_id

    def test_get_ingestion_job_not_found(self, client) -> None:
        resp = client.get(
            "/api/v1/knowledge/ingestions/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404


class TestRequestReindex:
    def test_request_reindex_success(
        self, client, session, source_repo, clock
    ) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        resp = client.post(f"/api/v1/knowledge/sources/{sid}/reindex")
        assert resp.status_code == 200
        data = resp.json()
        assert data["source_id"] == sid

    def test_request_reindex_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/knowledge/sources/00000000-0000-0000-0000-000000000000/reindex"
        )
        assert resp.status_code == 404

    def test_request_reindex_inactive_source_returns_400(
        self, client, session, source_repo, clock
    ) -> None:
        sid = create_source_in_repo(source_repo, clock, status=SourceStatus.REGISTERED)
        session.commit()
        resp = client.post(f"/api/v1/knowledge/sources/{sid}/reindex")
        assert resp.status_code == 400


class TestIntegrationFlows:
    def test_register_then_get_source(self, client, session, source_repo, clock) -> None:
        create_resp = client.post(
            "/api/v1/knowledge/sources",
            json={
                "name": "Integration Source",
                "source_type": "file",
                "location": "/tmp/int",
                "classification": "public",
            },
        )
        assert create_resp.status_code == 201
        sid = create_resp.json()["source_id"]
        get_resp = client.get(f"/api/v1/knowledge/sources/{sid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "Integration Source"

    def test_register_activate_then_ingest_document(
        self, client, session, source_repo, clock
    ) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()

        doc_resp = client.post(
            "/api/v1/knowledge/documents",
            json={
                "source_id": sid,
                "title": "Flow Doc",
                "checksum": "flow123",
                "classification": "public",
            },
        )
        assert doc_resp.status_code == 201
        assert doc_resp.json()["title"] == "Flow Doc"

    def test_source_document_chunk_flow(
        self, client, session, source_repo, clock
    ) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        doc_resp = client.post(
            "/api/v1/knowledge/documents",
            json={"source_id": sid, "title": "Flow", "checksum": "abc", "classification": "public"},
        )
        doc_id = doc_resp.json()["document_id"]
        chunk_resp = client.post(
            "/api/v1/knowledge/chunks",
            json={"document_id": doc_id, "chunk_index": 0, "content": "Flow content"},
        )
        assert chunk_resp.status_code == 201
        chunks_resp = client.get(f"/api/v1/knowledge/documents/{doc_id}/chunks")
        assert len(chunks_resp.json()["chunks"]) == 1

    def test_ingestion_lifecycle(
        self, client, session, source_repo, clock
    ) -> None:
        sid = create_active_source(source_repo, clock)
        session.commit()
        start_resp = client.post(
            "/api/v1/knowledge/ingestions",
            json={"source_id": sid},
        )
        assert start_resp.status_code == 201
        job_id = start_resp.json()["job_id"]
        complete_resp = client.post(
            f"/api/v1/knowledge/ingestions/{job_id}/complete"
        )
        assert complete_resp.status_code == 200
        assert complete_resp.json()["status"] == "completed"


class TestErrorMapping:
    def test_get_nonexistent_source_404(self, client) -> None:
        resp = client.get(
            "/api/v1/knowledge/sources/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_get_nonexistent_document_404(self, client) -> None:
        resp = client.get(
            "/api/v1/knowledge/documents/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_get_nonexistent_ingestion_job_404(self, client) -> None:
        resp = client.get(
            "/api/v1/knowledge/ingestions/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_register_source_invalid_type_422(self, client) -> None:
        resp = client.post(
            "/api/v1/knowledge/sources",
            json={
                "name": "Test",
                "source_type": "nope",
                "location": "/tmp",
                "classification": "public",
            },
        )
        assert resp.status_code == 422

    def test_register_source_empty_name_422(self, client) -> None:
        resp = client.post(
            "/api/v1/knowledge/sources",
            json={
                "name": "",
                "source_type": "file",
                "location": "/tmp",
                "classification": "public",
            },
        )
        assert resp.status_code == 422
