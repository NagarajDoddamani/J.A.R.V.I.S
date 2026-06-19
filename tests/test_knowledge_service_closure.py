from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from backend.knowledge.domain.factory import KnowledgeFactory
from backend.knowledge.domain.model import (
    DocumentStatus,
    IngestionJob,
    IngestionJobId,
    IngestionStatus,
    KnowledgeSource,
    KnowledgeSourceId,
    SourceStatus,
    SourceType,
)
from backend.knowledge.domain.rules import (
    MAX_CHUNK_CONTENT_LENGTH,
    VALID_CLASSIFICATIONS,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


# ===================================================================
# Enum audit
# ===================================================================


class TestEnumAudit:
    def test_source_status_values(self) -> None:
        expected = {"registered", "active", "disabled", "deleted"}
        actual = {e.value for e in SourceStatus}
        assert actual == expected

    def test_source_status_count(self) -> None:
        assert len(SourceStatus) == 4

    def test_document_status_values(self) -> None:
        expected = {"pending", "ingested", "indexed", "deleted"}
        actual = {e.value for e in DocumentStatus}
        assert actual == expected

    def test_document_status_count(self) -> None:
        assert len(DocumentStatus) == 4

    def test_ingestion_status_values(self) -> None:
        expected = {"queued", "running", "completed", "failed"}
        actual = {e.value for e in IngestionStatus}
        assert actual == expected

    def test_ingestion_status_count(self) -> None:
        assert len(IngestionStatus) == 4

    def test_source_type_values(self) -> None:
        expected = {"file", "directory", "url", "manual", "memory_export"}
        actual = {e.value for e in SourceType}
        assert actual == expected

    def test_source_type_count(self) -> None:
        assert len(SourceType) == 5

    def test_valid_classifications(self) -> None:
        expected = {"public", "internal", "sensitive", "restricted"}
        assert VALID_CLASSIFICATIONS == expected

    def test_chunk_max_length(self) -> None:
        assert MAX_CHUNK_CONTENT_LENGTH > 0


# ===================================================================
# Architecture import verification
# ===================================================================


class TestArchitectureImports:
    DOMAIN_DIR = REPO_ROOT / "backend" / "knowledge" / "domain"
    PORTS_DIR = REPO_ROOT / "backend" / "knowledge" / "application" / "ports"
    PERSISTENCE_DIR = REPO_ROOT / "backend" / "knowledge" / "application" / "persistence"
    USE_CASES_DIR = REPO_ROOT / "backend" / "knowledge" / "application" / "use_cases"
    ADAPTERS_DIR = REPO_ROOT / "backend" / "knowledge" / "adapters"
    BOOTSTRAP_FILE = REPO_ROOT / "backend" / "knowledge" / "bootstrap.py"
    NATS_FILE = REPO_ROOT / "backend" / "knowledge" / "nats.py"
    API_FILE = REPO_ROOT / "backend" / "api" / "endpoints" / "knowledge.py"

    INFRASTRUCTURE = {"sqlalchemy", "nats", "fastapi", "starlette", "httpx", "alembic", "redis", "qdrant_client"}

    def _read_py_files(self, directory: Path) -> list[Path]:
        return list(directory.rglob("*.py"))

    def _get_imports(self, path: Path) -> set[str]:
        text = path.read_text(encoding="utf-8")
        imports: set[str] = set()
        for line in text.splitlines():
            if line.startswith("import ") or line.startswith("from "):
                for infra in self.INFRASTRUCTURE:
                    if infra in line:
                        imports.add(infra)
        return imports

    def test_domain_imports_no_infrastructure(self) -> None:
        for py_file in self._read_py_files(self.DOMAIN_DIR):
            imports = self._get_imports(py_file)
            violations = imports & self.INFRASTRUCTURE
            assert not violations, f"{py_file.relative_to(REPO_ROOT)} imports {violations}"

    def test_ports_import_no_infrastructure(self) -> None:
        for py_file in self._read_py_files(self.PORTS_DIR):
            imports = self._get_imports(py_file)
            violations = imports & self.INFRASTRUCTURE
            assert not violations, f"{py_file.relative_to(REPO_ROOT)} imports {violations}"

    def test_persistence_imports_no_infrastructure(self) -> None:
        for py_file in self._read_py_files(self.PERSISTENCE_DIR):
            imports = self._get_imports(py_file)
            violations = imports & self.INFRASTRUCTURE
            assert not violations, f"{py_file.relative_to(REPO_ROOT)} imports {violations}"

    def test_use_cases_import_only_ports_and_domain(self) -> None:
        use_case_files = [f for f in self._read_py_files(self.USE_CASES_DIR) if f.name != "__init__.py"]
        for py_file in use_case_files:
            text = py_file.read_text(encoding="utf-8")
            for line in text.splitlines():
                if line.startswith("from backend.knowledge."):
                    rest = line.split("import")[0] if "import" in line else ""
                    if "ports" not in rest and "domain" not in rest and "use_cases" not in rest:
                        if "application" in rest:
                            pytest.fail(
                                f"{py_file.relative_to(REPO_ROOT)} imports from non-ports/domain: {line}"
                            )


# ===================================================================
# Layer isolation audit
# ===================================================================


class TestLayerIsolation:
    LAYER_PATHS: dict[str, Path] = {
        "domain": REPO_ROOT / "backend" / "knowledge" / "domain",
        "ports": REPO_ROOT / "backend" / "knowledge" / "application" / "ports",
        "persistence": REPO_ROOT / "backend" / "knowledge" / "application" / "persistence",
        "use_cases": REPO_ROOT / "backend" / "knowledge" / "application" / "use_cases",
        "adapters": REPO_ROOT / "backend" / "knowledge" / "adapters",
        "bootstrap": REPO_ROOT / "backend" / "knowledge" / "bootstrap.py",
        "nats": REPO_ROOT / "backend" / "knowledge" / "nats.py",
        "api": REPO_ROOT / "backend" / "api" / "endpoints" / "knowledge.py",
    }

    FORBIDDEN_UPWARD: dict[str, set[str]] = {
        "ports": {"adapters", "bootstrap", "nats", "api"},
        "persistence": {"adapters", "bootstrap", "nats", "api"},
        "use_cases": {"adapters", "bootstrap", "nats", "api"},
    }

    def test_no_upward_dependencies_from_lower_layers(self) -> None:
        for layer_name, upper_layers in self.FORBIDDEN_UPWARD.items():
            layer_path = self.LAYER_PATHS[layer_name]
            if layer_path.is_dir():
                py_files = list(layer_path.rglob("*.py"))
            else:
                py_files = [layer_path] if layer_path.exists() else []
            for py_file in py_files:
                text = py_file.read_text(encoding="utf-8")
                rel = py_file.relative_to(REPO_ROOT)
                for line in text.splitlines():
                    if line.startswith("from backend.knowledge."):
                        parts = line.split(".")[2:4] if "from backend.knowledge." in line else []
                        if len(parts) >= 2:
                            module = parts[1]
                            if module in upper_layers:
                                pytest.fail(
                                    f"{rel} imports from upper layer '{module}': {line}"
                                )


# ===================================================================
# Provider audit
# ===================================================================


class TestProviderAudit:
    def test_all_13_providers_exist(self) -> None:
        from backend.knowledge import bootstrap
        providers = [
            name for name in dir(bootstrap)
            if name.endswith("_use_case") and not name.startswith("_")
        ]
        assert len(providers) == 13, f"Expected 13 providers, got {len(providers)}: {providers}"


# ===================================================================
# Route audit
# ===================================================================


class TestRouteAudit:
    def test_all_13_routes_registered(self) -> None:
        from backend.api.endpoints.knowledge import router
        routes = [r.path for r in router.routes]
        assert len(routes) == 13, f"Expected 13 routes, got {len(routes)}: {routes}"
        expected_paths = {
            "/sources",
            "/sources/{source_id}",
            "/sources/{source_id}",
            "/sources/{source_id}/reindex",
            "/documents",
            "/documents/{document_id}",
            "/chunks",
            "/documents/{document_id}/chunks",
            "/ingestions",
            "/ingestions/{job_id}/complete",
            "/ingestions/{job_id}/fail",
            "/ingestions/{job_id}",
        }
        for path in expected_paths:
            assert path in routes, f"Missing route: {path}"


# ===================================================================
# Event audit
# ===================================================================


class TestEventAudit:
    def test_all_10_event_types_supported(self) -> None:
        from backend.knowledge.nats import _EVENT_TYPE_MAP
        assert len(_EVENT_TYPE_MAP) == 10, f"Expected 10 event types, got {len(_EVENT_TYPE_MAP)}"

    def test_all_event_types_have_nats_subjects(self) -> None:
        from backend.knowledge.nats import _EVENT_TYPE_MAP, _NATS_SUBJECT_MAP
        for event_type in _EVENT_TYPE_MAP:
            assert event_type in _NATS_SUBJECT_MAP, f"Missing NATS subject for {event_type}"

    def test_event_subjects_follow_convention(self) -> None:
        from backend.knowledge.nats import _NATS_SUBJECT_MAP
        for subject in _NATS_SUBJECT_MAP.values():
            assert subject.startswith("jarvis.event.knowledge.")
            assert subject.endswith(".v1")


# ===================================================================
# Repository audit
# ===================================================================


class TestRepositoryAudit:
    def test_four_repositories_exist(self) -> None:
        from backend.knowledge.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyKnowledgeSourceRepository,
            SqlAlchemyKnowledgeDocumentRepository,
            SqlAlchemyKnowledgeChunkRepository,
            SqlAlchemyIngestionJobRepository,
            SqlAlchemyKnowledgeOutboxAdapter,
        )
        assert SqlAlchemyKnowledgeSourceRepository is not None
        assert SqlAlchemyKnowledgeDocumentRepository is not None
        assert SqlAlchemyKnowledgeChunkRepository is not None
        assert SqlAlchemyIngestionJobRepository is not None
        assert SqlAlchemyKnowledgeOutboxAdapter is not None


# ===================================================================
# Mapper audit
# ===================================================================


class TestMapperAudit:
    def test_five_mappers_exist(self) -> None:
        from backend.knowledge.adapters.outbound.mapper import (
            KnowledgeSourceMapperImpl,
            KnowledgeDocumentMapperImpl,
            KnowledgeChunkMapperImpl,
            IngestionJobMapperImpl,
            KnowledgeOutboxMapperImpl,
        )
        assert KnowledgeSourceMapperImpl is not None
        assert KnowledgeDocumentMapperImpl is not None
        assert KnowledgeChunkMapperImpl is not None
        assert IngestionJobMapperImpl is not None
        assert KnowledgeOutboxMapperImpl is not None


# ===================================================================
# DTO audit
# ===================================================================


class TestDTOAudit:
    def test_persistence_dtos_exist(self) -> None:
        from backend.knowledge.application.persistence.dto import (
            IngestionJobStorageDTO,
            KnowledgeChunkStorageDTO,
            KnowledgeDocumentStorageDTO,
            KnowledgeOutboxStorageDTO,
            KnowledgeSourceStorageDTO,
        )
        assert KnowledgeSourceStorageDTO is not None
        assert KnowledgeDocumentStorageDTO is not None
        assert KnowledgeChunkStorageDTO is not None
        assert IngestionJobStorageDTO is not None
        assert KnowledgeOutboxStorageDTO is not None

    def test_request_dtos_exist(self) -> None:
        from backend.knowledge.application.use_cases.dto import (
            RegisterSourceRequest,
            DeleteSourceRequest,
            GetSourceRequest,
            ListSourcesRequest,
            IngestDocumentRequest,
            GetDocumentRequest,
            CreateChunkRequest,
            GetChunksByDocumentRequest,
            StartIngestionRequest,
            CompleteIngestionRequest,
            FailIngestionRequest,
            GetIngestionJobRequest,
            RequestReindexRequest,
        )
        assert RegisterSourceRequest is not None
        assert DeleteSourceRequest is not None
        assert GetSourceRequest is not None
        assert ListSourcesRequest is not None
        assert IngestDocumentRequest is not None
        assert GetDocumentRequest is not None
        assert CreateChunkRequest is not None
        assert GetChunksByDocumentRequest is not None
        assert StartIngestionRequest is not None
        assert CompleteIngestionRequest is not None
        assert FailIngestionRequest is not None
        assert GetIngestionJobRequest is not None
        assert RequestReindexRequest is not None

    def test_response_dtos_exist(self) -> None:
        from backend.knowledge.application.use_cases.dto import (
            RegisterSourceResponse,
            DeleteSourceResponse,
            SourceResponse,
            ListSourcesResponse,
            IngestDocumentResponse,
            DocumentResponse,
            CreateChunkResponse,
            ChunkResponse,
            GetChunksByDocumentResponse,
            StartIngestionResponse,
            CompleteIngestionResponse,
            FailIngestionResponse,
            IngestionJobResponse,
            ReindexResponse,
        )
        assert RegisterSourceResponse is not None
        assert DeleteSourceResponse is not None
        assert SourceResponse is not None
        assert ListSourcesResponse is not None
        assert IngestDocumentResponse is not None
        assert DocumentResponse is not None
        assert CreateChunkResponse is not None
        assert ChunkResponse is not None
        assert GetChunksByDocumentResponse is not None
        assert StartIngestionResponse is not None
        assert CompleteIngestionResponse is not None
        assert FailIngestionResponse is not None
        assert IngestionJobResponse is not None
        assert ReindexResponse is not None

    def test_all_dto_types_have_unique_names(self) -> None:
        from backend.knowledge.application.use_cases.dto import (
            RegisterSourceRequest,
            RegisterSourceResponse,
            DeleteSourceRequest,
            DeleteSourceResponse,
            GetSourceRequest,
            SourceResponse,
            ListSourcesRequest,
            ListSourcesResponse,
            IngestDocumentRequest,
            IngestDocumentResponse,
            GetDocumentRequest,
            DocumentResponse,
            CreateChunkRequest,
            CreateChunkResponse,
            ChunkResponse,
            GetChunksByDocumentRequest,
            GetChunksByDocumentResponse,
            StartIngestionRequest,
            StartIngestionResponse,
            CompleteIngestionRequest,
            CompleteIngestionResponse,
            FailIngestionRequest,
            FailIngestionResponse,
            GetIngestionJobRequest,
            IngestionJobResponse,
            RequestReindexRequest,
            ReindexResponse,
        )
        dto_names = [
            "RegisterSourceRequest", "RegisterSourceResponse",
            "DeleteSourceRequest", "DeleteSourceResponse",
            "GetSourceRequest", "SourceResponse",
            "ListSourcesRequest", "ListSourcesResponse",
            "IngestDocumentRequest", "IngestDocumentResponse",
            "GetDocumentRequest", "DocumentResponse",
            "CreateChunkRequest", "CreateChunkResponse",
            "ChunkResponse",
            "GetChunksByDocumentRequest", "GetChunksByDocumentResponse",
            "StartIngestionRequest", "StartIngestionResponse",
            "CompleteIngestionRequest", "CompleteIngestionResponse",
            "FailIngestionRequest", "FailIngestionResponse",
            "GetIngestionJobRequest", "IngestionJobResponse",
            "RequestReindexRequest", "ReindexResponse",
        ]
        assert len(dto_names) == 27


# ===================================================================
# Security audit
# ===================================================================


class TestSecurityAudit:
    def test_classification_enforced(self) -> None:
        from backend.knowledge.domain.rules import assert_classification_valid
        assert_classification_valid("public")
        assert_classification_valid("internal")
        assert_classification_valid("sensitive")
        assert_classification_valid("restricted")
        with pytest.raises(Exception):
            assert_classification_valid("invalid")

    def test_invalid_type_rejected(self) -> None:
        from backend.knowledge.domain.exceptions import InvalidSourceTypeError
        with pytest.raises(InvalidSourceTypeError):
            KnowledgeFactory.register_source(
                name="Test", source_type="nonexistent",
                location="/tmp", classification="public",
            )

    def test_deleted_source_blocks_activation(self) -> None:
        from datetime import datetime, timezone
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(), name="Test",
            source_type=SourceType.FILE,
            status=SourceStatus.DELETED,
            created_at=datetime.now(tz=timezone.utc),
            deleted_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(Exception):
            source.activate()

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(Exception):
            KnowledgeFactory.register_source(
                name="", source_type="file",
                location="/tmp", classification="public",
            )

    def test_empty_title_rejected(self) -> None:
        from datetime import datetime, timezone
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Src", source_type=SourceType.FILE,
            status=SourceStatus.ACTIVE,
            created_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(Exception):
            KnowledgeFactory.ingest_document(
                source=source, title="", checksum="abc", classification="public",
            )

    def test_invalid_transition_blocked(self) -> None:
        from datetime import datetime, timezone
        from backend.knowledge.domain.exceptions import InvalidIngestionTransitionError
        job = IngestionJob(
            job_id=IngestionJobId(),
            status=IngestionStatus.COMPLETED,
            started_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(InvalidIngestionTransitionError):
            job.complete()


# ===================================================================
# Coverage audit
# ===================================================================


class TestCoverageAudit:
    def test_domain_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_knowledge_domain.py").exists()

    def test_ports_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_knowledge_ports.py").exists()

    def test_persistence_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_knowledge_persistence_contracts.py").exists()

    def test_use_cases_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_knowledge_use_cases.py").exists()

    def test_adapter_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_knowledge_adapters.py").exists()

    def test_repository_integration_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_knowledge_repository_integration.py").exists()

    def test_bootstrap_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_knowledge_bootstrap.py").exists()

    def test_api_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_knowledge_api.py").exists()

    def test_nats_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_knowledge_nats.py").exists()

    def test_integration_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_knowledge_integration.py").exists()

    def test_service_closure_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_knowledge_service_closure.py").exists()

    def test_all_knowledge_test_files(self) -> None:
        knowledge_tests = sorted((REPO_ROOT / "tests").glob("test_knowledge_*.py"))
        expected = {
            "test_knowledge_adapters.py",
            "test_knowledge_api.py",
            "test_knowledge_bootstrap.py",
            "test_knowledge_domain.py",
            "test_knowledge_integration.py",
            "test_knowledge_nats.py",
            "test_knowledge_persistence_contracts.py",
            "test_knowledge_ports.py",
            "test_knowledge_repository_integration.py",
            "test_knowledge_service_closure.py",
            "test_knowledge_use_cases.py",
        }
        actual = {f.name for f in knowledge_tests}
        missing = expected - actual
        assert not missing, f"Missing test files: {missing}"
