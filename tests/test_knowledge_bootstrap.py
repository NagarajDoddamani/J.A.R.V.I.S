from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import knowledge
from backend.core.database import get_db
from backend.knowledge.adapters.outbound.models import Base
from backend.knowledge.bootstrap import (
    complete_ingestion_use_case,
    create_chunk_use_case,
    delete_source_use_case,
    fail_ingestion_use_case,
    get_chunks_by_document_use_case,
    get_document_use_case,
    get_ingestion_job_use_case,
    get_source_use_case,
    ingest_document_use_case,
    list_sources_use_case,
    register_source_use_case,
    request_reindex_use_case,
    start_ingestion_use_case,
)
from backend.knowledge.application.use_cases.complete_ingestion import (
    CompleteIngestionUseCase,
)
from backend.knowledge.application.use_cases.create_chunk import (
    CreateChunkUseCase,
)
from backend.knowledge.application.use_cases.delete_source import (
    DeleteSourceUseCase,
)
from backend.knowledge.application.use_cases.fail_ingestion import (
    FailIngestionUseCase,
)
from backend.knowledge.application.use_cases.get_chunks_by_document import (
    GetChunksByDocumentUseCase,
)
from backend.knowledge.application.use_cases.get_document import (
    GetDocumentUseCase,
)
from backend.knowledge.application.use_cases.get_ingestion_job import (
    GetIngestionJobUseCase,
)
from backend.knowledge.application.use_cases.get_source import (
    GetSourceUseCase,
)
from backend.knowledge.application.use_cases.ingest_document import (
    IngestDocumentUseCase,
)
from backend.knowledge.application.use_cases.list_sources import (
    ListSourcesUseCase,
)
from backend.knowledge.application.use_cases.register_source import (
    RegisterSourceUseCase,
)
from backend.knowledge.application.use_cases.request_reindex import (
    RequestReindexUseCase,
)
from backend.knowledge.application.use_cases.start_ingestion import (
    StartIngestionUseCase,
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


class TestBootstrapUseCases:
    def test_register_source_use_case(self, session) -> None:
        with patch("backend.knowledge.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = register_source_use_case()
            assert isinstance(uc, RegisterSourceUseCase)

    def test_delete_source_use_case(self, session) -> None:
        with patch("backend.knowledge.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = delete_source_use_case()
            assert isinstance(uc, DeleteSourceUseCase)

    def test_get_source_use_case(self, session) -> None:
        with patch("backend.knowledge.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = get_source_use_case()
            assert isinstance(uc, GetSourceUseCase)

    def test_list_sources_use_case(self, session) -> None:
        with patch("backend.knowledge.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = list_sources_use_case()
            assert isinstance(uc, ListSourcesUseCase)

    def test_ingest_document_use_case(self, session) -> None:
        with patch("backend.knowledge.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = ingest_document_use_case()
            assert isinstance(uc, IngestDocumentUseCase)

    def test_get_document_use_case(self, session) -> None:
        with patch("backend.knowledge.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = get_document_use_case()
            assert isinstance(uc, GetDocumentUseCase)

    def test_create_chunk_use_case(self, session) -> None:
        with patch("backend.knowledge.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = create_chunk_use_case()
            assert isinstance(uc, CreateChunkUseCase)

    def test_get_chunks_by_document_use_case(self, session) -> None:
        with patch("backend.knowledge.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = get_chunks_by_document_use_case()
            assert isinstance(uc, GetChunksByDocumentUseCase)

    def test_start_ingestion_use_case(self, session) -> None:
        with patch("backend.knowledge.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = start_ingestion_use_case()
            assert isinstance(uc, StartIngestionUseCase)

    def test_complete_ingestion_use_case(self, session) -> None:
        with patch("backend.knowledge.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = complete_ingestion_use_case()
            assert isinstance(uc, CompleteIngestionUseCase)

    def test_fail_ingestion_use_case(self, session) -> None:
        with patch("backend.knowledge.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = fail_ingestion_use_case()
            assert isinstance(uc, FailIngestionUseCase)

    def test_get_ingestion_job_use_case(self, session) -> None:
        with patch("backend.knowledge.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = get_ingestion_job_use_case()
            assert isinstance(uc, GetIngestionJobUseCase)

    def test_request_reindex_use_case(self, session) -> None:
        with patch("backend.knowledge.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = request_reindex_use_case()
            assert isinstance(uc, RequestReindexUseCase)

    def test_register_source_use_case_has_clock(self) -> None:
        with patch("backend.knowledge.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = MagicMock()
            uc = register_source_use_case()
            assert hasattr(uc, "_clock")

    def test_start_ingestion_use_case_has_id_generator(self) -> None:
        with patch("backend.knowledge.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = MagicMock()
            uc = start_ingestion_use_case()
            assert hasattr(uc, "_id_generator")


class TestBootstrapThroughApi:
    def test_list_sources_empty(self, client) -> None:
        resp = client.get("/api/v1/knowledge/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sources"]) == 0

    def test_get_source_not_found(self, client) -> None:
        resp = client.get(
            "/api/v1/knowledge/sources/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_delete_source_not_found(self, client) -> None:
        resp = client.delete(
            "/api/v1/knowledge/sources/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_get_document_not_found(self, client) -> None:
        resp = client.get(
            "/api/v1/knowledge/documents/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_get_ingestion_job_not_found(self, client) -> None:
        resp = client.get(
            "/api/v1/knowledge/ingestions/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_create_chunk_no_document_returns_404(self, client) -> None:
        resp = client.post(
            "/api/v1/knowledge/chunks",
            json={"document_id": "00000000-0000-0000-0000-000000000000", "chunk_index": 0, "content": "test"},
        )
        assert resp.status_code == 404

    def test_complete_ingestion_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/knowledge/ingestions/00000000-0000-0000-0000-000000000000/complete"
        )
        assert resp.status_code == 404

    def test_fail_ingestion_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/knowledge/ingestions/00000000-0000-0000-0000-000000000000/fail",
            json={"error_message": "test error"},
        )
        assert resp.status_code == 404
