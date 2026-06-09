from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import memory
from backend.core.database import get_db
from backend.memory.adapters.outbound.models import Base
from backend.memory.bootstrap import (
    create_memory_use_case,
    delete_memory_use_case,
    get_consent_use_case,
    get_memory_use_case,
    grant_consent_use_case,
    revoke_consent_use_case,
    search_memories_use_case,
    update_memory_use_case,
)
from backend.memory.application.use_cases.create_memory import (
    CreateMemoryUseCase,
)
from backend.memory.application.use_cases.delete_memory import (
    DeleteMemoryUseCase,
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


class TestBootstrapUseCases:
    def test_create_memory_use_case(self, session) -> None:
        with patch("backend.memory.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = create_memory_use_case()
            assert isinstance(uc, CreateMemoryUseCase)

    def test_update_memory_use_case(self, session) -> None:
        with patch("backend.memory.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = update_memory_use_case()
            assert isinstance(uc, UpdateMemoryUseCase)

    def test_delete_memory_use_case(self, session) -> None:
        with patch("backend.memory.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = delete_memory_use_case()
            assert isinstance(uc, DeleteMemoryUseCase)

    def test_get_memory_use_case(self, session) -> None:
        with patch("backend.memory.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = get_memory_use_case()
            assert isinstance(uc, GetMemoryUseCase)

    def test_search_memories_use_case(self, session) -> None:
        with patch("backend.memory.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = search_memories_use_case()
            assert isinstance(uc, SearchMemoriesUseCase)

    def test_grant_consent_use_case(self, session) -> None:
        with patch("backend.memory.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = grant_consent_use_case()
            assert isinstance(uc, GrantConsentUseCase)

    def test_revoke_consent_use_case(self, session) -> None:
        with patch("backend.memory.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = revoke_consent_use_case()
            assert isinstance(uc, RevokeConsentUseCase)

    def test_get_consent_use_case(self, session) -> None:
        with patch("backend.memory.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = get_consent_use_case()
            assert isinstance(uc, GetConsentUseCase)

    def test_create_use_case_has_clock(self) -> None:
        with patch("backend.memory.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = MagicMock()
            uc = create_memory_use_case()
            assert hasattr(uc, "_clock")

    def test_grant_consent_use_case_has_id_generator(self) -> None:
        with patch("backend.memory.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = MagicMock()
            uc = grant_consent_use_case()
            assert hasattr(uc, "_id_generator")


class TestBootstrapThroughApi:
    def test_create_memory_no_consent_returns_400(self, client) -> None:
        resp = client.post(
            "/api/v1/memory/memories",
            json={
                "consent_id": "00000000-0000-0000-0000-000000000000",
                "content": "test",
                "category": "general",
                "source_type": "user_input",
                "provenance_source": "user_input",
            },
        )
        assert resp.status_code == 400

    def test_search_memories_empty(self, client) -> None:
        resp = client.get("/api/v1/memory/memories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_get_memory_not_found(self, client) -> None:
        resp = client.get(
            "/api/v1/memory/memories/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_delete_memory_not_found(self, client) -> None:
        resp = client.delete(
            "/api/v1/memory/memories/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_get_consent_not_found(self, client) -> None:
        resp = client.get(
            "/api/v1/memory/consents/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_revoke_consent_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/memory/consents/00000000-0000-0000-0000-000000000000/revoke"
        )
        assert resp.status_code == 404
