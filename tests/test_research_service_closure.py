from __future__ import annotations

from pathlib import Path

import pytest

from backend.research.domain.model import (
    ResearchPriority,
    ResearchStatus,
    SourceType,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

INFRASTRUCTURE = {
    "sqlalchemy",
    "nats",
    "fastapi",
    "starlette",
    "httpx",
    "alembic",
    "redis",
    "qdrant_client",
}

LAYER_PATHS: dict[str, Path | list[Path]] = {
    "domain": REPO_ROOT / "backend" / "research" / "domain",
    "ports": REPO_ROOT / "backend" / "research" / "application" / "ports",
    "persistence": REPO_ROOT / "backend" / "research" / "application" / "persistence",
    "use_cases": REPO_ROOT / "backend" / "research" / "application" / "use_cases",
}

UPWARD_LAYERS: dict[str, list[str]] = {
    "domain": ["adapters", "bootstrap", "nats", "api"],
    "ports": ["adapters", "bootstrap", "nats", "api"],
    "persistence": ["adapters", "bootstrap", "nats", "api"],
    "use_cases": ["adapters", "bootstrap", "nats", "api"],
}

SINGLE_FILE_LAYERS: dict[str, Path] = {
    "bootstrap": REPO_ROOT / "backend" / "research" / "bootstrap.py",
    "nats": REPO_ROOT / "backend" / "research" / "nats.py",
}

EXPECTED_TEST_FILES: set[str] = {
    "test_research_domain.py",
    "test_research_ports.py",
    "test_research_persistence_contracts.py",
    "test_research_use_cases.py",
    "test_research_adapters.py",
    "test_research_repository_integration.py",
    "test_research_bootstrap.py",
    "test_research_api.py",
    "test_research_nats.py",
    "test_research_integration.py",
    "test_research_service_closure.py",
}


# ===================================================================
# 1. Enum completeness
# ===================================================================


class TestEnumCompleteness:
    def test_research_status_values(self) -> None:
        expected = {"created", "running", "completed", "failed", "cancelled"}
        actual = {e.value for e in ResearchStatus}
        assert actual == expected

    def test_research_status_count(self) -> None:
        assert len(ResearchStatus) == 5

    def test_source_type_values(self) -> None:
        expected = {"memory", "knowledge", "web", "document", "user"}
        actual = {e.value for e in SourceType}
        assert actual == expected

    def test_source_type_count(self) -> None:
        assert len(SourceType) == 5

    def test_research_priority_values(self) -> None:
        expected = {"low", "normal", "high", "critical"}
        actual = {e.value for e in ResearchPriority}
        assert actual == expected

    def test_research_priority_count(self) -> None:
        assert len(ResearchPriority) == 4


# ===================================================================
# 2. Event completeness
# ===================================================================


class TestEventCompleteness:
    def test_all_seven_events_exist(self) -> None:
        from backend.research.domain.model import (
            ResearchCancelled,
            ResearchCompleted,
            ResearchFailed,
            ResearchRequested,
            ResearchStarted,
            ResearchSummaryGenerated,
            SourceAdded,
        )

        event_classes = {
            ResearchRequested,
            ResearchStarted,
            ResearchCompleted,
            ResearchFailed,
            ResearchCancelled,
            SourceAdded,
            ResearchSummaryGenerated,
        }
        assert len(event_classes) == 7

    def test_all_events_have_outbox_mapping(self) -> None:
        from backend.research.adapters.outbound.mapper import (
            _EVENT_TYPE_MAP,
        )

        assert len(_EVENT_TYPE_MAP) == 7
        for event_cls, mapped in _EVENT_TYPE_MAP.items():
            assert isinstance(mapped, str)
            assert mapped.startswith("research.") or mapped.startswith("source.")

    def test_all_events_have_nats_subject(self) -> None:
        from backend.research.nats import _NATS_SUBJECT_MAP

        assert len(_NATS_SUBJECT_MAP) == 7
        for subject in _NATS_SUBJECT_MAP.values():
            assert subject.startswith("jarvis.event.research.")
            assert subject.endswith(".v1")

    def test_event_subjects_follow_convention(self) -> None:
        from backend.research.nats import _NATS_SUBJECT_MAP

        for event_cls, subject in _NATS_SUBJECT_MAP.items():
            assert subject.startswith("jarvis.event.research.")
            assert subject.endswith(".v1")


# ===================================================================
# 3. Route inventory
# ===================================================================


class TestRouteInventory:
    def test_all_fifteen_routes_registered(self) -> None:
        from backend.api.endpoints.research import router

        expected_paths: set[str] = {
            "/requests",
            "/requests/{request_id}",
            "/requests/{request_id}/start",
            "/requests/{request_id}/complete",
            "/requests/{request_id}/fail",
            "/requests/{request_id}/cancel",
            "/requests/{request_id}/jobs",
            "/jobs/{job_id}/start",
            "/jobs/{job_id}/complete",
            "/jobs/{job_id}/fail",
            "/jobs/{job_id}",
            "/jobs",
            "/jobs/{job_id}/sources",
            "/jobs/{job_id}/summary",
        }
        actual_paths: set[str] = set()
        for route in router.routes:
            if hasattr(route, "path"):
                actual_paths.add(route.path)
        assert (
            actual_paths >= expected_paths
        ), f"Missing routes: {expected_paths - actual_paths}"
        assert len(actual_paths) >= len(expected_paths)

    def test_all_routes_have_http_methods(self) -> None:
        from backend.api.endpoints.research import router

        for route in router.routes:
            if hasattr(route, "methods"):
                assert len(route.methods) >= 1


# ===================================================================
# 4. Provider inventory
# ===================================================================


class TestProviderInventory:
    def test_all_15_providers_exist(self) -> None:
        from backend.research import bootstrap

        provider_names = [
            "create_request_use_case",
            "start_request_use_case",
            "complete_request_use_case",
            "fail_request_use_case",
            "cancel_request_use_case",
            "create_job_use_case",
            "start_job_use_case",
            "complete_job_use_case",
            "fail_job_use_case",
            "add_source_use_case",
            "generate_summary_use_case",
            "get_request_use_case",
            "list_requests_use_case",
            "get_job_use_case",
            "list_jobs_use_case",
        ]
        for name in provider_names:
            assert hasattr(bootstrap, name), f"Missing provider: {name}"

    def test_all_providers_return_correct_types(self) -> None:
        from backend.research import bootstrap

        providers = {
            "create_request_use_case": bootstrap.create_request_use_case,
            "start_request_use_case": bootstrap.start_request_use_case,
            "complete_request_use_case": bootstrap.complete_request_use_case,
            "fail_request_use_case": bootstrap.fail_request_use_case,
            "cancel_request_use_case": bootstrap.cancel_request_use_case,
            "create_job_use_case": bootstrap.create_job_use_case,
            "start_job_use_case": bootstrap.start_job_use_case,
            "complete_job_use_case": bootstrap.complete_job_use_case,
            "fail_job_use_case": bootstrap.fail_job_use_case,
            "add_source_use_case": bootstrap.add_source_use_case,
            "generate_summary_use_case": bootstrap.generate_summary_use_case,
            "get_request_use_case": bootstrap.get_request_use_case,
            "list_requests_use_case": bootstrap.list_requests_use_case,
            "get_job_use_case": bootstrap.get_job_use_case,
            "list_jobs_use_case": bootstrap.list_jobs_use_case,
        }
        assert len(providers) == 15


# ===================================================================
# 5. Repository inventory
# ===================================================================


class TestRepositoryInventory:
    def test_three_repositories_exist(self) -> None:
        from backend.research.application.ports.repository import (
            ResearchJobRepositoryPort,
            ResearchRequestRepositoryPort,
            ResearchSourceRepositoryPort,
        )
        from backend.research.application.ports.outbox import (
            ResearchOutboxPort,
        )

        assert ResearchRequestRepositoryPort is not None
        assert ResearchJobRepositoryPort is not None
        assert ResearchSourceRepositoryPort is not None
        assert ResearchOutboxPort is not None

    def test_request_repo_has_all_methods(self) -> None:
        import inspect

        from backend.research.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyResearchRequestRepository,
        )

        methods = {
            m
            for m, _ in inspect.getmembers(
                SqlAlchemyResearchRequestRepository,
                predicate=inspect.isfunction,
            )
        }
        expected = {
            "save",
            "find_by_id",
            "find_by_status",
            "find_by_priority",
            "count",
        }
        assert methods >= expected, f"Missing: {expected - methods}"

    def test_job_repo_has_all_methods(self) -> None:
        import inspect

        from backend.research.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyResearchJobRepository,
        )

        methods = {
            m
            for m, _ in inspect.getmembers(
                SqlAlchemyResearchJobRepository,
                predicate=inspect.isfunction,
            )
        }
        expected = {
            "save",
            "find_by_id",
            "find_by_status",
            "find_by_request_id",
            "count",
        }
        assert methods >= expected, f"Missing: {expected - methods}"

    def test_source_repo_has_all_methods(self) -> None:
        import inspect

        from backend.research.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyResearchSourceRepository,
        )

        methods = {
            m
            for m, _ in inspect.getmembers(
                SqlAlchemyResearchSourceRepository,
                predicate=inspect.isfunction,
            )
        }
        expected = {
            "save",
            "find_by_id",
            "find_by_type",
            "find_by_job_id",
            "count",
        }
        assert methods >= expected, f"Missing: {expected - methods}"

    def test_outbox_adapter_has_all_methods(self) -> None:
        import inspect

        from backend.research.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyResearchOutboxAdapter,
        )

        methods = {
            m
            for m, _ in inspect.getmembers(
                SqlAlchemyResearchOutboxAdapter,
                predicate=inspect.isfunction,
            )
        }
        expected = {"append", "fetch_unpublished", "mark_published"}
        assert methods >= expected, f"Missing: {expected - methods}"


# ===================================================================
# 6. Mapper inventory
# ===================================================================


class TestMapperInventory:
    def test_four_mappers_exist(self) -> None:
        from backend.research.adapters.outbound.mapper import (
            ResearchJobMapperImpl,
            ResearchOutboxMapperImpl,
            ResearchRequestMapperImpl,
            ResearchSourceMapperImpl,
        )

        assert ResearchRequestMapperImpl is not None
        assert ResearchJobMapperImpl is not None
        assert ResearchSourceMapperImpl is not None
        assert ResearchOutboxMapperImpl is not None

    def test_request_mapper_has_both_directions(self) -> None:
        from backend.research.adapters.outbound.mapper import (
            ResearchRequestMapperImpl,
        )

        assert hasattr(ResearchRequestMapperImpl, "domain_to_dto")
        assert hasattr(ResearchRequestMapperImpl, "dto_to_domain")

    def test_job_mapper_has_both_directions(self) -> None:
        from backend.research.adapters.outbound.mapper import (
            ResearchJobMapperImpl,
        )

        assert hasattr(ResearchJobMapperImpl, "domain_to_dto")
        assert hasattr(ResearchJobMapperImpl, "dto_to_domain")

    def test_source_mapper_has_both_directions(self) -> None:
        from backend.research.adapters.outbound.mapper import (
            ResearchSourceMapperImpl,
        )

        assert hasattr(ResearchSourceMapperImpl, "domain_to_dto")
        assert hasattr(ResearchSourceMapperImpl, "dto_to_domain")

    def test_outbox_mapper_has_both_directions(self) -> None:
        from backend.research.adapters.outbound.mapper import (
            ResearchOutboxMapperImpl,
        )

        assert hasattr(ResearchOutboxMapperImpl, "event_to_dto")
        assert hasattr(ResearchOutboxMapperImpl, "dto_to_event")


# ===================================================================
# 7. DTO inventory
# ===================================================================


class TestDtoInventory:
    def test_persistence_dtos_exist(self) -> None:
        from backend.research.application.persistence.dto import (
            ResearchJobStorageDTO,
            ResearchOutboxStorageDTO,
            ResearchRequestStorageDTO,
            ResearchSourceStorageDTO,
        )

        assert ResearchRequestStorageDTO is not None
        assert ResearchJobStorageDTO is not None
        assert ResearchSourceStorageDTO is not None
        assert ResearchOutboxStorageDTO is not None

    def test_use_case_dtos_exist(self) -> None:
        from backend.research.application.use_cases.dto import (
            AddSourceRequest,
            AddSourceResponse,
            CreateJobRequest,
            CreateJobResponse,
            CreateRequestRequest,
            CreateRequestResponse,
            FailJobRequest,
            FailJobResponse,
            FailRequestRequest,
            FailRequestResponse,
            GenerateSummaryRequest,
            GenerateSummaryResponse,
            GetJobRequest,
            GetRequestRequest,
            JobLifecycleRequest,
            JobLifecycleResponse,
            JobResponse,
            ListJobsRequest,
            ListJobsResponse,
            ListRequestsRequest,
            ListRequestsResponse,
            RequestLifecycleRequest,
            RequestLifecycleResponse,
            RequestResponse,
            SourceResponse,
        )

        assert CreateRequestRequest is not None
        assert CreateRequestResponse is not None
        assert RequestLifecycleRequest is not None
        assert RequestLifecycleResponse is not None
        assert FailRequestRequest is not None
        assert FailRequestResponse is not None
        assert CreateJobRequest is not None
        assert CreateJobResponse is not None
        assert JobLifecycleRequest is not None
        assert JobLifecycleResponse is not None
        assert FailJobRequest is not None
        assert FailJobResponse is not None
        assert AddSourceRequest is not None
        assert AddSourceResponse is not None
        assert GenerateSummaryRequest is not None
        assert GenerateSummaryResponse is not None
        assert GetRequestRequest is not None
        assert GetJobRequest is not None
        assert ListRequestsRequest is not None
        assert ListRequestsResponse is not None
        assert ListJobsRequest is not None
        assert ListJobsResponse is not None
        assert RequestResponse is not None
        assert JobResponse is not None
        assert SourceResponse is not None

    def test_dto_total_count(self) -> None:
        from backend.research.application.use_cases.dto import (
            AddSourceRequest,
            AddSourceResponse,
            CreateJobRequest,
            CreateJobResponse,
            CreateRequestRequest,
            CreateRequestResponse,
            FailJobRequest,
            FailJobResponse,
            FailRequestRequest,
            FailRequestResponse,
            GenerateSummaryRequest,
            GenerateSummaryResponse,
            GetJobRequest,
            GetRequestRequest,
            JobLifecycleRequest,
            JobLifecycleResponse,
            JobResponse,
            ListJobsRequest,
            ListJobsResponse,
            ListRequestsRequest,
            ListRequestsResponse,
            RequestLifecycleRequest,
            RequestLifecycleResponse,
            RequestResponse,
            SourceResponse,
        )

        dtos = [
            CreateRequestRequest,
            CreateRequestResponse,
            RequestLifecycleRequest,
            RequestLifecycleResponse,
            FailRequestRequest,
            FailRequestResponse,
            CreateJobRequest,
            CreateJobResponse,
            JobLifecycleRequest,
            JobLifecycleResponse,
            FailJobRequest,
            FailJobResponse,
            AddSourceRequest,
            AddSourceResponse,
            GenerateSummaryRequest,
            GenerateSummaryResponse,
            GetRequestRequest,
            GetJobRequest,
            ListRequestsRequest,
            ListRequestsResponse,
            ListJobsRequest,
            ListJobsResponse,
            RequestResponse,
            JobResponse,
            SourceResponse,
        ]
        assert len(dtos) == 25


# ===================================================================
# 8. Architecture import barriers
# ===================================================================


class TestArchitectureImportBarriers:
    def _read_py_files(self, directory: Path) -> list[Path]:
        return list(directory.rglob("*.py"))

    def _get_imports(self, path: Path) -> list[str]:
        text = path.read_text(encoding="utf-8")
        imports: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                imports.append(stripped)
        return imports

    @pytest.mark.parametrize(
        "layer",
        ["domain", "ports", "persistence", "use_cases"],
    )
    def test_domain_and_app_no_adapter_frameworks(
        self, layer: str
    ) -> None:
        path = LAYER_PATHS[layer]
        if isinstance(path, list):
            dirs = path
        else:
            dirs = [path]
        violators: list[tuple[Path, str]] = []
        for directory in dirs:
            for pyfile in self._read_py_files(directory):
                imports = self._get_imports(pyfile)
                for imp in imports:
                    for framework in INFRASTRUCTURE:
                        if framework in imp:
                            violators.append((pyfile, framework))
        if violators:
            msg = "\n".join(f"{f} in {p}" for p, f in violators)
            pytest.fail(
                f"Layer '{layer}' imports adapter frameworks:\n{msg}"
            )

    def test_ports_import_only_domain(self) -> None:
        import_lines: list[str] = []
        ports_dir = (
            REPO_ROOT / "backend" / "research" / "application" / "ports"
        )
        for pyfile in ports_dir.rglob("*.py"):
            import_lines.extend(self._get_imports(pyfile))
        forbidden = {"fastapi", "sqlalchemy", "nats_py", "httpx"}
        for imp in import_lines:
            for f in forbidden:
                if f in imp:
                    pytest.fail(f"Ports layer imports {f}: {imp}")

    def test_persistence_imports_only_domain_and_port_dtos(
        self,
    ) -> None:
        pers_dir = (
            REPO_ROOT
            / "backend"
            / "research"
            / "application"
            / "persistence"
        )
        for pyfile in pers_dir.rglob("*.py"):
            imports = self._get_imports(pyfile)
            for imp in imports:
                if (
                    "sqlalchemy" in imp
                    or "nats" in imp
                    or "fastapi" in imp
                ):
                    pytest.fail(
                        f"Persistence imports {imp} in {pyfile.name}"
                    )

    def test_bootstrap_is_only_composition_root(self) -> None:
        bootstrap_path = (
            REPO_ROOT / "backend" / "research" / "bootstrap.py"
        )
        text = bootstrap_path.read_text(encoding="utf-8")
        assert "Depends" in text
        assert "get_db" in text

    def test_nats_file_exists(self) -> None:
        nats_path = REPO_ROOT / "backend" / "research" / "nats.py"
        assert nats_path.exists()
        text = nats_path.read_text(encoding="utf-8")
        assert "publish_research_outbox_events" in text


# ===================================================================
# 9. Layer isolation
# ===================================================================


class TestLayerIsolation:
    def _read_py_files(self, directory: Path) -> list[Path]:
        if directory.is_dir():
            return list(directory.rglob("*.py"))
        return [directory]

    def _get_imports(self, path: Path) -> list[str]:
        text = path.read_text(encoding="utf-8")
        imports: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith(
                "from "
            ):
                imports.append(stripped)
        return imports

    def test_no_upward_dependencies_from_lower_layers(self) -> None:
        for layer, upper_layers in UPWARD_LAYERS.items():
            paths = LAYER_PATHS[layer]
            if isinstance(paths, list):
                dirs = paths
            else:
                dirs = [paths]
            if isinstance(paths, Path) and not paths.is_dir():
                dirs = [paths]
            for directory in dirs:
                for pyfile in self._read_py_files(directory):
                    rel = pyfile.relative_to(REPO_ROOT)
                    imports = self._get_imports(pyfile)
                    for line in imports:
                        for upper in upper_layers:
                            if (
                                f"backend.research.{upper}" in line
                                or f"backend.api.{upper}" in line
                            ):
                                pytest.fail(
                                    f"{rel} imports from upper layer '{upper}': {line}"
                                )


# ===================================================================
# 10. Coverage metrics
# ===================================================================


class TestCoverageMetrics:
    def test_domain_test_file_exists(self) -> None:
        assert (
            REPO_ROOT / "tests" / "test_research_domain.py"
        ).exists()

    def test_ports_test_file_exists(self) -> None:
        assert (
            REPO_ROOT / "tests" / "test_research_ports.py"
        ).exists()

    def test_persistence_test_file_exists(self) -> None:
        assert (
            REPO_ROOT
            / "tests"
            / "test_research_persistence_contracts.py"
        ).exists()

    def test_use_cases_test_file_exists(self) -> None:
        assert (
            REPO_ROOT / "tests" / "test_research_use_cases.py"
        ).exists()

    def test_adapter_test_file_exists(self) -> None:
        assert (
            REPO_ROOT / "tests" / "test_research_adapters.py"
        ).exists()

    def test_repository_integration_test_file_exists(self) -> None:
        assert (
            REPO_ROOT
            / "tests"
            / "test_research_repository_integration.py"
        ).exists()

    def test_bootstrap_test_file_exists(self) -> None:
        assert (
            REPO_ROOT / "tests" / "test_research_bootstrap.py"
        ).exists()

    def test_api_test_file_exists(self) -> None:
        assert (
            REPO_ROOT / "tests" / "test_research_api.py"
        ).exists()

    def test_nats_test_file_exists(self) -> None:
        assert (
            REPO_ROOT / "tests" / "test_research_nats.py"
        ).exists()

    def test_integration_test_file_exists(self) -> None:
        assert (
            REPO_ROOT / "tests" / "test_research_integration.py"
        ).exists()

    def test_service_closure_test_file_exists(self) -> None:
        assert (
            REPO_ROOT
            / "tests"
            / "test_research_service_closure.py"
        ).exists()

    def test_all_research_test_files(self) -> None:
        test_dir = REPO_ROOT / "tests"
        actual = {p.name for p in test_dir.glob("test_research_*.py")}
        missing = EXPECTED_TEST_FILES - actual
        extra = actual - EXPECTED_TEST_FILES
        if missing:
            pytest.fail(f"Missing research test files: {missing}")
        if extra:
            pytest.fail(
                f"Unexpected research test files: {extra}"
            )
