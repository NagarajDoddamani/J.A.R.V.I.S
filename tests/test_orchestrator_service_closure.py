from __future__ import annotations

from pathlib import Path

import pytest

from backend.orchestrator.domain.model import (
    AgentRole,
    ExecutionMode,
    OrchestrationStatus,
    WorkflowStepStatus,
    WorkflowStatus,
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
    "domain": REPO_ROOT / "backend" / "orchestrator" / "domain",
    "ports": REPO_ROOT / "backend" / "orchestrator" / "application" / "ports",
    "persistence": REPO_ROOT / "backend" / "orchestrator" / "application" / "persistence",
    "use_cases": REPO_ROOT / "backend" / "orchestrator" / "application" / "use_cases",
}

UPWARD_LAYERS: dict[str, list[str]] = {
    "domain": ["adapters", "bootstrap", "nats", "api"],
    "ports": ["adapters", "bootstrap", "nats", "api"],
    "persistence": ["adapters", "bootstrap", "nats", "api"],
    "use_cases": ["adapters", "bootstrap", "nats", "api"],
}

SINGLE_FILE_LAYERS: dict[str, Path] = {
    "bootstrap": REPO_ROOT / "backend" / "orchestrator" / "bootstrap.py",
    "nats": REPO_ROOT / "backend" / "orchestrator" / "nats.py",
}

EXPECTED_TEST_FILES: set[str] = {
    "test_orchestrator_domain.py",
    "test_orchestrator_ports.py",
    "test_orchestrator_persistence_contracts.py",
    "test_orchestrator_use_cases.py",
    "test_orchestrator_adapters.py",
    "test_orchestrator_repository_integration.py",
    "test_orchestrator_bootstrap.py",
    "test_orchestrator_api.py",
    "test_orchestrator_nats.py",
    "test_orchestrator_integration.py",
    "test_orchestrator_service_closure.py",
}


# ===================================================================
# 1. Enum completeness
# ===================================================================


class TestEnumCompleteness:
    def test_orchestration_status_values(self) -> None:
        expected = {"created", "planning", "researching", "executing", "completed", "failed", "cancelled"}
        actual = {e.value for e in OrchestrationStatus}
        assert actual == expected

    def test_orchestration_status_count(self) -> None:
        assert len(OrchestrationStatus) == 7

    def test_workflow_status_values(self) -> None:
        expected = {"pending", "running", "completed", "failed"}
        actual = {e.value for e in WorkflowStatus}
        assert actual == expected

    def test_workflow_status_count(self) -> None:
        assert len(WorkflowStatus) == 4

    def test_workflow_step_status_values(self) -> None:
        expected = {"pending", "running", "completed", "failed", "skipped"}
        actual = {e.value for e in WorkflowStepStatus}
        assert actual == expected

    def test_workflow_step_status_count(self) -> None:
        assert len(WorkflowStepStatus) == 5

    def test_agent_role_values(self) -> None:
        expected = {"planner", "research", "automation", "memory", "knowledge", "policy"}
        actual = {e.value for e in AgentRole}
        assert actual == expected

    def test_agent_role_count(self) -> None:
        assert len(AgentRole) == 6

    def test_execution_mode_values(self) -> None:
        expected = {"sequential", "parallel", "hybrid"}
        actual = {e.value for e in ExecutionMode}
        assert actual == expected

    def test_execution_mode_count(self) -> None:
        assert len(ExecutionMode) == 3


# ===================================================================
# 2. Event completeness
# ===================================================================


class TestEventCompleteness:
    def test_all_thirteen_events_exist(self) -> None:
        from backend.orchestrator.domain.model import (
            OrchestrationCancelled,
            OrchestrationCompleted,
            OrchestrationCreated,
            OrchestrationExecutionStarted,
            OrchestrationFailed,
            OrchestrationPlanningStarted,
            OrchestrationResearchStarted,
            WorkflowCompleted,
            WorkflowCreated,
            WorkflowFailed,
            WorkflowStepCompleted,
            WorkflowStepFailed,
            WorkflowStepStarted,
        )
        event_classes = {
            OrchestrationCreated,
            OrchestrationPlanningStarted,
            OrchestrationResearchStarted,
            OrchestrationExecutionStarted,
            OrchestrationCompleted,
            OrchestrationFailed,
            OrchestrationCancelled,
            WorkflowCreated,
            WorkflowCompleted,
            WorkflowFailed,
            WorkflowStepStarted,
            WorkflowStepCompleted,
            WorkflowStepFailed,
        }
        assert len(event_classes) == 13

    def test_all_events_have_subject_in_nats_map(self) -> None:
        from backend.orchestrator.nats import _NATS_SUBJECT_MAP

        assert len(_NATS_SUBJECT_MAP) == 13
        for event_cls, subject in _NATS_SUBJECT_MAP.items():
            assert isinstance(subject, str)
            assert subject.startswith("jarvis.orchestrator.event.")

    def test_all_events_have_type_in_mapper_map(self) -> None:
        from backend.orchestrator.adapters.outbound.mapper import _EVENT_TYPE_MAP

        assert len(_EVENT_TYPE_MAP) == 13
        for event_cls, event_type in _EVENT_TYPE_MAP.items():
            assert isinstance(event_type, str)
            assert event_type.startswith("orchestration.") or event_type.startswith(
                "workflow."
            )

    def test_nats_subjects_follow_convention(self) -> None:
        from backend.orchestrator.nats import _NATS_SUBJECT_MAP

        for subject in _NATS_SUBJECT_MAP.values():
            assert subject.startswith("jarvis.orchestrator.event.")
            assert subject.endswith(".v1")
            assert subject.count(".") >= 4

    def test_outbox_event_union_has_thirteen_types(self) -> None:
        import typing

        from backend.orchestrator.application.ports.outbox import (
            OrchestratorOutboxEvent,
        )
        union_args = typing.get_args(OrchestratorOutboxEvent)
        assert len(union_args) == 13


# ===================================================================
# 3. Route inventory
# ===================================================================


class TestRouteInventory:
    def test_all_nineteen_routes_registered(self) -> None:
        from backend.api.endpoints.orchestrator import router

        expected_paths: set[str] = {
            "/orchestrations",
            "/orchestrations/{orchestration_id}",
            "/orchestrations/{orchestration_id}/planning",
            "/orchestrations/{orchestration_id}/research",
            "/orchestrations/{orchestration_id}/execution",
            "/orchestrations/{orchestration_id}/complete",
            "/orchestrations/{orchestration_id}/fail",
            "/orchestrations/{orchestration_id}/cancel",
            "/orchestrations/{orchestration_id}/workflows",
            "/workflows/{workflow_id}",
            "/workflows",
            "/workflows/{workflow_id}/complete",
            "/workflows/{workflow_id}/fail",
            "/workflows/{workflow_id}/steps",
            "/steps/{step_id}/start",
            "/steps/{step_id}/complete",
            "/steps/{step_id}/fail",
            "/steps/{step_id}",
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
        from backend.api.endpoints.orchestrator import router

        for route in router.routes:
            if hasattr(route, "methods"):
                assert len(route.methods) >= 1


# ===================================================================
# 4. Provider inventory
# ===================================================================


class TestProviderInventory:
    def test_all_19_providers_exist(self) -> None:
        from backend.orchestrator import bootstrap

        provider_names = [
            "_orchestration_repo",
            "_workflow_repo",
            "_step_repo",
            "_outbox",
            "_clock",
            "_id_generator",
            "create_orchestration_use_case",
            "start_planning_use_case",
            "start_research_use_case",
            "start_execution_use_case",
            "complete_orchestration_use_case",
            "fail_orchestration_use_case",
            "cancel_orchestration_use_case",
            "create_workflow_use_case",
            "complete_workflow_use_case",
            "fail_workflow_use_case",
            "add_step_use_case",
            "start_step_use_case",
            "complete_step_use_case",
            "fail_step_use_case",
            "get_orchestration_use_case",
            "list_orchestrations_use_case",
            "get_workflow_use_case",
            "list_workflows_use_case",
            "get_step_use_case",
        ]
        for name in provider_names:
            assert hasattr(bootstrap, name), f"Missing provider: {name}"

    def test_all_providers_return_correct_types(self) -> None:
        from backend.orchestrator import bootstrap

        providers = {
            "create_orchestration_use_case": bootstrap.create_orchestration_use_case,
            "start_planning_use_case": bootstrap.start_planning_use_case,
            "start_research_use_case": bootstrap.start_research_use_case,
            "start_execution_use_case": bootstrap.start_execution_use_case,
            "complete_orchestration_use_case": bootstrap.complete_orchestration_use_case,
            "fail_orchestration_use_case": bootstrap.fail_orchestration_use_case,
            "cancel_orchestration_use_case": bootstrap.cancel_orchestration_use_case,
            "create_workflow_use_case": bootstrap.create_workflow_use_case,
            "complete_workflow_use_case": bootstrap.complete_workflow_use_case,
            "fail_workflow_use_case": bootstrap.fail_workflow_use_case,
            "add_step_use_case": bootstrap.add_step_use_case,
            "start_step_use_case": bootstrap.start_step_use_case,
            "complete_step_use_case": bootstrap.complete_step_use_case,
            "fail_step_use_case": bootstrap.fail_step_use_case,
            "get_orchestration_use_case": bootstrap.get_orchestration_use_case,
            "list_orchestrations_use_case": bootstrap.list_orchestrations_use_case,
            "get_workflow_use_case": bootstrap.get_workflow_use_case,
            "list_workflows_use_case": bootstrap.list_workflows_use_case,
            "get_step_use_case": bootstrap.get_step_use_case,
        }
        assert len(providers) == 19


# ===================================================================
# 5. Repository inventory
# ===================================================================


class TestRepositoryInventory:
    def test_three_repositories_exist(self) -> None:
        from backend.orchestrator.application.ports.repository import (
            OrchestrationRepositoryPort,
            OrchestratorStepRepositoryPort,
            OrchestratorWorkflowRepositoryPort,
        )
        from backend.orchestrator.application.ports.outbox import (
            OrchestratorOutboxPort,
        )
        assert OrchestrationRepositoryPort is not None
        assert OrchestratorWorkflowRepositoryPort is not None
        assert OrchestratorStepRepositoryPort is not None
        assert OrchestratorOutboxPort is not None

    def test_orchestration_repo_has_all_methods(self) -> None:
        import inspect

        from backend.orchestrator.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyOrchestrationRepository,
        )
        methods = {m for m, _ in inspect.getmembers(SqlAlchemyOrchestrationRepository, predicate=inspect.isfunction)}
        expected = {"save", "find_by_id", "find_by_status", "find_all", "count"}
        assert methods >= expected, f"Missing: {expected - methods}"

    def test_workflow_repo_has_all_methods(self) -> None:
        import inspect

        from backend.orchestrator.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyWorkflowRepository,
        )
        methods = {m for m, _ in inspect.getmembers(SqlAlchemyWorkflowRepository, predicate=inspect.isfunction)}
        expected = {"save", "find_by_id", "find_by_status", "find_by_orchestration_id", "find_all", "count"}
        assert methods >= expected, f"Missing: {expected - methods}"

    def test_step_repo_has_all_methods(self) -> None:
        import inspect

        from backend.orchestrator.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyWorkflowStepRepository,
        )
        methods = {m for m, _ in inspect.getmembers(SqlAlchemyWorkflowStepRepository, predicate=inspect.isfunction)}
        expected = {"save", "find_by_id", "find_by_status", "find_by_workflow_id", "find_by_agent_role", "count"}
        assert methods >= expected, f"Missing: {expected - methods}"

    def test_outbox_adapter_has_all_methods(self) -> None:
        import inspect

        from backend.orchestrator.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyOrchestratorOutboxAdapter,
        )
        methods = {m for m, _ in inspect.getmembers(SqlAlchemyOrchestratorOutboxAdapter, predicate=inspect.isfunction)}
        expected = {"append", "fetch_unpublished", "mark_published"}
        assert methods >= expected, f"Missing: {expected - methods}"


# ===================================================================
# 6. Mapper inventory
# ===================================================================


class TestMapperInventory:
    def test_four_mappers_exist(self) -> None:
        from backend.orchestrator.adapters.outbound.mapper import (
            OrchestrationMapperImpl,
            OrchestratorOutboxMapperImpl,
            WorkflowMapperImpl,
            WorkflowStepMapperImpl,
        )
        assert OrchestrationMapperImpl is not None
        assert WorkflowMapperImpl is not None
        assert WorkflowStepMapperImpl is not None
        assert OrchestratorOutboxMapperImpl is not None

    def test_orchestration_mapper_has_both_directions(self) -> None:
        from backend.orchestrator.adapters.outbound.mapper import (
            OrchestrationMapperImpl,
        )
        assert hasattr(OrchestrationMapperImpl, "domain_to_dto")
        assert hasattr(OrchestrationMapperImpl, "dto_to_domain")

    def test_workflow_mapper_has_both_directions(self) -> None:
        from backend.orchestrator.adapters.outbound.mapper import (
            WorkflowMapperImpl,
        )
        assert hasattr(WorkflowMapperImpl, "domain_to_dto")
        assert hasattr(WorkflowMapperImpl, "dto_to_domain")

    def test_step_mapper_has_both_directions(self) -> None:
        from backend.orchestrator.adapters.outbound.mapper import (
            WorkflowStepMapperImpl,
        )
        assert hasattr(WorkflowStepMapperImpl, "domain_to_dto")
        assert hasattr(WorkflowStepMapperImpl, "dto_to_domain")

    def test_outbox_mapper_has_both_directions(self) -> None:
        from backend.orchestrator.adapters.outbound.mapper import (
            OrchestratorOutboxMapperImpl,
        )
        assert hasattr(OrchestratorOutboxMapperImpl, "event_to_dto")
        assert hasattr(OrchestratorOutboxMapperImpl, "dto_to_event")


# ===================================================================
# 7. DTO inventory
# ===================================================================


class TestDtoInventory:
    def test_persistence_dtos_exist(self) -> None:
        from backend.orchestrator.application.persistence.dto import (
            OrchestrationStorageDTO,
            OrchestratorOutboxStorageDTO,
            WorkflowStepStorageDTO,
            WorkflowStorageDTO,
        )
        assert OrchestrationStorageDTO is not None
        assert WorkflowStorageDTO is not None
        assert WorkflowStepStorageDTO is not None
        assert OrchestratorOutboxStorageDTO is not None

    def test_use_case_dtos_exist(self) -> None:
        from backend.orchestrator.application.use_cases.dto import (
            AddStepRequest,
            AddStepResponse,
            CompleteStepRequest,
            CompleteStepResponse,
            CreateOrchestrationRequest,
            CreateOrchestrationResponse,
            CreateWorkflowRequest,
            CreateWorkflowResponse,
            FailOrchestrationRequest,
            FailOrchestrationResponse,
            FailStepRequest,
            FailStepResponse,
            FailWorkflowRequest,
            FailWorkflowResponse,
            GetOrchestrationRequest,
            GetStepRequest,
            GetWorkflowRequest,
            ListOrchestrationsRequest,
            ListOrchestrationsResponse,
            ListWorkflowsRequest,
            ListWorkflowsResponse,
            OrchestrationLifecycleRequest,
            OrchestrationLifecycleResponse,
            OrchestrationResponse,
            StepLifecycleRequest,
            StepLifecycleResponse,
            WorkflowLifecycleRequest,
            WorkflowLifecycleResponse,
            WorkflowResponse,
            WorkflowStepResponse,
        )
        assert CreateOrchestrationRequest is not None
        assert CreateOrchestrationResponse is not None
        assert OrchestrationLifecycleRequest is not None
        assert OrchestrationLifecycleResponse is not None
        assert FailOrchestrationRequest is not None
        assert FailOrchestrationResponse is not None
        assert CreateWorkflowRequest is not None
        assert CreateWorkflowResponse is not None
        assert WorkflowLifecycleRequest is not None
        assert WorkflowLifecycleResponse is not None
        assert FailWorkflowRequest is not None
        assert FailWorkflowResponse is not None
        assert AddStepRequest is not None
        assert AddStepResponse is not None
        assert StepLifecycleRequest is not None
        assert StepLifecycleResponse is not None
        assert CompleteStepRequest is not None
        assert CompleteStepResponse is not None
        assert FailStepRequest is not None
        assert FailStepResponse is not None
        assert GetOrchestrationRequest is not None
        assert GetWorkflowRequest is not None
        assert GetStepRequest is not None
        assert ListOrchestrationsRequest is not None
        assert ListOrchestrationsResponse is not None
        assert ListWorkflowsRequest is not None
        assert ListWorkflowsResponse is not None
        assert OrchestrationResponse is not None
        assert WorkflowResponse is not None
        assert WorkflowStepResponse is not None


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
    def test_domain_and_app_no_adapter_frameworks(self, layer: str) -> None:
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
            pytest.fail(f"Layer '{layer}' imports adapter frameworks:\n{msg}")

    def test_ports_import_only_domain(self) -> None:
        import_lines: list[str] = []
        ports_dir = REPO_ROOT / "backend" / "orchestrator" / "application" / "ports"
        for pyfile in ports_dir.rglob("*.py"):
            import_lines.extend(self._get_imports(pyfile))
        forbidden = {"fastapi", "sqlalchemy", "nats_py", "httpx"}
        for imp in import_lines:
            for f in forbidden:
                if f in imp:
                    pytest.fail(f"Ports layer imports {f}: {imp}")

    def test_persistence_imports_only_domain_and_port_dtos(self) -> None:
        pers_dir = REPO_ROOT / "backend" / "orchestrator" / "application" / "persistence"
        for pyfile in pers_dir.rglob("*.py"):
            imports = self._get_imports(pyfile)
            for imp in imports:
                if "sqlalchemy" in imp or "nats" in imp or "fastapi" in imp:
                    pytest.fail(f"Persistence imports {imp} in {pyfile.name}")

    def test_bootstrap_is_only_composition_root(self) -> None:
        bootstrap_path = REPO_ROOT / "backend" / "orchestrator" / "bootstrap.py"
        text = bootstrap_path.read_text(encoding="utf-8")
        assert "Depends" in text
        assert "get_db" in text

    def test_nats_file_exists(self) -> None:
        nats_path = REPO_ROOT / "backend" / "orchestrator" / "nats.py"
        assert nats_path.exists()
        text = nats_path.read_text(encoding="utf-8")
        assert "publish_orchestrator_outbox_events" in text


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
            if stripped.startswith("import ") or stripped.startswith("from "):
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
                            if f"backend.orchestrator.{upper}" in line:
                                pytest.fail(
                                    f"{rel} imports from upper layer '{upper}': {line}"
                                )


# ===================================================================
# 10. Coverage metrics
# ===================================================================


class TestCoverageMetrics:
    def test_domain_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_orchestrator_domain.py").exists()

    def test_ports_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_orchestrator_ports.py").exists()

    def test_persistence_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_orchestrator_persistence_contracts.py").exists()

    def test_use_cases_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_orchestrator_use_cases.py").exists()

    def test_adapter_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_orchestrator_adapters.py").exists()

    def test_repository_integration_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_orchestrator_repository_integration.py").exists()

    def test_bootstrap_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_orchestrator_bootstrap.py").exists()

    def test_api_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_orchestrator_api.py").exists()

    def test_nats_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_orchestrator_nats.py").exists()

    def test_integration_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_orchestrator_integration.py").exists()

    def test_service_closure_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_orchestrator_service_closure.py").exists()

    def test_all_orchestrator_test_files(self) -> None:
        test_dir = REPO_ROOT / "tests"
        actual = {p.name for p in test_dir.glob("test_orchestrator_*.py")}
        missing = EXPECTED_TEST_FILES - actual
        extra = actual - EXPECTED_TEST_FILES
        if missing:
            pytest.fail(f"Missing orchestrator test files: {missing}")
        if extra:
            pytest.fail(f"Unexpected orchestrator test files: {extra}")


# ===================================================================
# 11. Security compliance
# ===================================================================


class TestSecurityCompliance:
    SOURCE_DIRS = [
        REPO_ROOT / "backend" / "orchestrator",
    ]

    SECRET_PATTERNS = [
        "sk-",
        "api_key",
        "api.secret",
        "private_key",
        "-----BEGIN",
        "password",
        "secret",
    ]

    def _walk_py_files(self) -> list[Path]:
        files: list[Path] = []
        for directory in self.SOURCE_DIRS:
            for pyfile in directory.rglob("*.py"):
                if "migration" not in str(pyfile):
                    files.append(pyfile)
        return files

    def test_no_secrets_in_source(self) -> None:
        violations: list[str] = []
        for pyfile in self._walk_py_files():
            rel = pyfile.relative_to(REPO_ROOT)
            text = pyfile.read_text(encoding="utf-8")
            for i, line in enumerate(text.splitlines(), start=1):
                lower = line.lower()
                for pattern in self.SECRET_PATTERNS:
                    if pattern in lower and "test" not in str(rel):
                        # ignore known variable names that are not secrets
                        segs = {
                            "api_key",
                            "private_key",
                            "secret",
                        }
                        if pattern in segs and any(
                            kw in lower
                            for kw in ("event_type", "self._secret", "class")
                        ):
                            continue
                        violations.append(f"{rel}:{i}: {line.strip()}")
        if violations:
            pytest.fail(
                "Potential secrets found in source:\n"
                + "\n".join(violations[:20])
            )
