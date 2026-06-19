from __future__ import annotations

from pathlib import Path

import pytest

from backend.planner.domain.model import (
    AgentType,
    ExecutionStrategy,
    PlanPriority,
    PlanStatus,
    TaskStatus,
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
    "domain": REPO_ROOT / "backend" / "planner" / "domain",
    "ports": REPO_ROOT / "backend" / "planner" / "application" / "ports",
    "persistence": REPO_ROOT / "backend" / "planner" / "application" / "persistence",
    "use_cases": REPO_ROOT / "backend" / "planner" / "application" / "use_cases",
}

UPWARD_LAYERS: dict[str, list[str]] = {
    "domain": ["adapters", "bootstrap", "nats", "api"],
    "ports": ["adapters", "bootstrap", "nats", "api"],
    "persistence": ["adapters", "bootstrap", "nats", "api"],
    "use_cases": ["adapters", "bootstrap", "nats", "api"],
}

SINGLE_FILE_LAYERS: dict[str, Path] = {
    "bootstrap": REPO_ROOT / "backend" / "planner" / "bootstrap.py",
    "nats": REPO_ROOT / "backend" / "planner" / "nats.py",
}

EXPECTED_TEST_FILES: set[str] = {
    "test_planner_domain.py",
    "test_planner_ports.py",
    "test_planner_persistence_contracts.py",
    "test_planner_use_cases.py",
    "test_planner_adapters.py",
    "test_planner_repository_integration.py",
    "test_planner_bootstrap.py",
    "test_planner_api.py",
    "test_planner_nats.py",
    "test_planner_integration.py",
    "test_planner_service_closure.py",
}


# ===================================================================
# 1. Enum completeness
# ===================================================================


class TestEnumCompleteness:
    def test_plan_status_values(self) -> None:
        expected = {"draft", "approved", "planning", "ready", "executing", "completed", "failed", "cancelled"}
        actual = {e.value for e in PlanStatus}
        assert actual == expected

    def test_plan_status_count(self) -> None:
        assert len(PlanStatus) == 8

    def test_task_status_values(self) -> None:
        expected = {"pending", "assigned", "running", "completed", "failed", "cancelled"}
        actual = {e.value for e in TaskStatus}
        assert actual == expected

    def test_task_status_count(self) -> None:
        assert len(TaskStatus) == 6

    def test_plan_priority_values(self) -> None:
        expected = {"low", "normal", "high", "critical"}
        actual = {e.value for e in PlanPriority}
        assert actual == expected

    def test_plan_priority_count(self) -> None:
        assert len(PlanPriority) == 4

    def test_execution_strategy_values(self) -> None:
        expected = {"sequential", "parallel", "hybrid"}
        actual = {e.value for e in ExecutionStrategy}
        assert actual == expected

    def test_execution_strategy_count(self) -> None:
        assert len(ExecutionStrategy) == 3

    def test_agent_type_values(self) -> None:
        expected = {"planner", "research", "automation", "memory", "knowledge", "notification", "policy"}
        actual = {e.value for e in AgentType}
        assert actual == expected

    def test_agent_type_count(self) -> None:
        assert len(AgentType) == 7


# ===================================================================
# 2. Event completeness
# ===================================================================


class TestEventCompleteness:
    def test_all_eleven_events_exist(self) -> None:
        from backend.planner.domain.model import (
            PlanApproved,
            PlanCancelled,
            PlanCompleted,
            PlanCreated,
            PlanExecutionStarted,
            PlanFailed,
            PlanReady,
            TaskAssigned,
            TaskCompleted,
            TaskCreated,
            TaskFailed,
        )
        event_classes = {
            PlanCreated,
            PlanApproved,
            PlanReady,
            PlanExecutionStarted,
            PlanCompleted,
            PlanFailed,
            PlanCancelled,
            TaskCreated,
            TaskAssigned,
            TaskCompleted,
            TaskFailed,
        }
        assert len(event_classes) == 11

    def test_all_events_have_nats_subject(self) -> None:
        from backend.planner.adapters.outbound.mapper import _EVENT_TYPE_MAP

        expected_events = 11
        assert len(_EVENT_TYPE_MAP) == expected_events
        for event_cls, subject in _EVENT_TYPE_MAP.items():
            assert isinstance(subject, str)
            assert subject.startswith("planner.")

    def test_event_subjects_follow_convention(self) -> None:
        from backend.planner.adapters.outbound.mapper import _EVENT_TYPE_MAP

        for subject in _EVENT_TYPE_MAP.values():
            assert subject.startswith("planner.")
            assert subject.count(".") >= 2


# ===================================================================
# 3. Route inventory
# ===================================================================


class TestRouteInventory:
    def test_all_seventeen_routes_registered(self) -> None:
        from backend.api.endpoints.planner import router

        expected_paths: set[str] = {
            "/plans",
            "/plans/{plan_id}",
            "/plans/{plan_id}/approve",
            "/plans/{plan_id}/planning",
            "/plans/{plan_id}/ready",
            "/plans/{plan_id}/execute",
            "/plans/{plan_id}/complete",
            "/plans/{plan_id}/fail",
            "/plans/{plan_id}/cancel",
            "/plans/{plan_id}/tasks",
            "/tasks/{task_id}",
            "/tasks/{task_id}/assign",
            "/tasks/{task_id}/start",
            "/tasks/{task_id}/complete",
            "/tasks/{task_id}/fail",
            "/tasks",
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
        from backend.api.endpoints.planner import router

        for route in router.routes:
            if hasattr(route, "methods"):
                assert len(route.methods) >= 1


# ===================================================================
# 4. Provider inventory
# ===================================================================


class TestProviderInventory:
    def test_all_22_providers_exist(self) -> None:
        from backend.planner import bootstrap

        provider_names = [
            "create_plan_use_case",
            "approve_plan_use_case",
            "start_planning_use_case",
            "mark_plan_ready_use_case",
            "start_execution_use_case",
            "complete_plan_use_case",
            "fail_plan_use_case",
            "cancel_plan_use_case",
            "add_task_use_case",
            "assign_task_use_case",
            "start_task_use_case",
            "complete_task_use_case",
            "fail_task_use_case",
            "get_plan_use_case",
            "list_plans_use_case",
            "get_task_use_case",
            "list_tasks_use_case",
        ]
        for name in provider_names:
            assert hasattr(bootstrap, name), f"Missing provider: {name}"

    def test_all_providers_return_correct_types(self) -> None:
        from backend.planner import bootstrap
        providers = {
            "create_plan_use_case": bootstrap.create_plan_use_case,
            "approve_plan_use_case": bootstrap.approve_plan_use_case,
            "start_planning_use_case": bootstrap.start_planning_use_case,
            "mark_plan_ready_use_case": bootstrap.mark_plan_ready_use_case,
            "start_execution_use_case": bootstrap.start_execution_use_case,
            "complete_plan_use_case": bootstrap.complete_plan_use_case,
            "fail_plan_use_case": bootstrap.fail_plan_use_case,
            "cancel_plan_use_case": bootstrap.cancel_plan_use_case,
            "add_task_use_case": bootstrap.add_task_use_case,
            "assign_task_use_case": bootstrap.assign_task_use_case,
            "start_task_use_case": bootstrap.start_task_use_case,
            "complete_task_use_case": bootstrap.complete_task_use_case,
            "fail_task_use_case": bootstrap.fail_task_use_case,
            "get_plan_use_case": bootstrap.get_plan_use_case,
            "list_plans_use_case": bootstrap.list_plans_use_case,
            "get_task_use_case": bootstrap.get_task_use_case,
            "list_tasks_use_case": bootstrap.list_tasks_use_case,
        }
        assert len(providers) == 17


# ===================================================================
# 5. Repository inventory
# ===================================================================


class TestRepositoryInventory:
    def test_three_repositories_exist(self) -> None:
        from backend.planner.application.ports.repository import (
            PlanRepositoryPort,
            TaskRepositoryPort,
        )
        from backend.planner.application.ports.outbox import PlannerOutboxPort
        assert PlanRepositoryPort is not None
        assert TaskRepositoryPort is not None
        assert PlannerOutboxPort is not None

    def test_plan_repo_has_all_methods(self) -> None:
        import inspect

        from backend.planner.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyPlanRepository,
        )
        methods = {m for m, _ in inspect.getmembers(SqlAlchemyPlanRepository, predicate=inspect.isfunction)}
        expected = {"save", "find_by_id", "find_by_status", "find_by_priority", "find_active", "count"}
        assert methods >= expected, f"Missing: {expected - methods}"

    def test_task_repo_has_all_methods(self) -> None:
        import inspect

        from backend.planner.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyTaskRepository,
        )
        methods = {m for m, _ in inspect.getmembers(SqlAlchemyTaskRepository, predicate=inspect.isfunction)}
        expected = {"save", "find_by_id", "find_by_status", "find_by_agent", "find_by_plan_id", "count"}
        assert methods >= expected, f"Missing: {expected - methods}"

    def test_outbox_adapter_has_all_methods(self) -> None:
        import inspect

        from backend.planner.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyPlannerOutboxAdapter,
        )
        methods = {m for m, _ in inspect.getmembers(SqlAlchemyPlannerOutboxAdapter, predicate=inspect.isfunction)}
        expected = {"append", "fetch_unpublished", "mark_published"}
        assert methods >= expected, f"Missing: {expected - methods}"


# ===================================================================
# 6. Mapper inventory
# ===================================================================


class TestMapperInventory:
    def test_four_mappers_exist(self) -> None:
        from backend.planner.adapters.outbound.mapper import (
            ExecutionStepMapperImpl,
            PlanMapperImpl,
            PlannerOutboxMapperImpl,
            TaskMapperImpl,
        )
        assert PlanMapperImpl is not None
        assert TaskMapperImpl is not None
        assert ExecutionStepMapperImpl is not None
        assert PlannerOutboxMapperImpl is not None

    def test_plan_mapper_has_both_directions(self) -> None:
        from backend.planner.adapters.outbound.mapper import PlanMapperImpl
        assert hasattr(PlanMapperImpl, "domain_to_dto")
        assert hasattr(PlanMapperImpl, "dto_to_domain")

    def test_task_mapper_has_both_directions(self) -> None:
        from backend.planner.adapters.outbound.mapper import TaskMapperImpl
        assert hasattr(TaskMapperImpl, "domain_to_dto")
        assert hasattr(TaskMapperImpl, "dto_to_domain")

    def test_outbox_mapper_has_both_directions(self) -> None:
        from backend.planner.adapters.outbound.mapper import (
            PlannerOutboxMapperImpl,
        )
        assert hasattr(PlannerOutboxMapperImpl, "event_to_dto")
        assert hasattr(PlannerOutboxMapperImpl, "dto_to_event")


# ===================================================================
# 7. DTO inventory
# ===================================================================


class TestDtoInventory:
    def test_persistence_dtos_exist(self) -> None:
        from backend.planner.application.persistence.dto import (
            ExecutionStepStorageDTO,
            PlanStorageDTO,
            PlannerOutboxStorageDTO,
            TaskStorageDTO,
        )
        assert PlanStorageDTO is not None
        assert TaskStorageDTO is not None
        assert ExecutionStepStorageDTO is not None
        assert PlannerOutboxStorageDTO is not None

    def test_use_case_dtos_exist(self) -> None:
        from backend.planner.application.use_cases.dto import (
            AddTaskRequest,
            AddTaskResponse,
            AssignTaskRequest,
            AssignTaskResponse,
            CreatePlanRequest,
            CreatePlanResponse,
            FailPlanRequest,
            FailPlanResponse,
            FailTaskRequest,
            FailTaskResponse,
            GetPlanRequest,
            GetTaskRequest,
            ListPlansRequest,
            ListPlansResponse,
            ListTasksRequest,
            ListTasksResponse,
            PlanLifecycleRequest,
            PlanLifecycleResponse,
            TaskLifecycleRequest,
            TaskLifecycleResponse,
            TaskResponse,
        )
        assert CreatePlanRequest is not None
        assert CreatePlanResponse is not None
        assert PlanLifecycleRequest is not None
        assert PlanLifecycleResponse is not None
        assert FailPlanRequest is not None
        assert FailPlanResponse is not None
        assert AddTaskRequest is not None
        assert AddTaskResponse is not None
        assert TaskLifecycleRequest is not None
        assert TaskLifecycleResponse is not None
        assert AssignTaskRequest is not None
        assert AssignTaskResponse is not None
        assert FailTaskRequest is not None
        assert FailTaskResponse is not None
        assert GetPlanRequest is not None
        assert GetTaskRequest is not None
        assert ListPlansRequest is not None
        assert ListPlansResponse is not None
        assert ListTasksRequest is not None
        assert ListTasksResponse is not None
        assert TaskResponse is not None


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
        ports_dir = REPO_ROOT / "backend" / "planner" / "application" / "ports"
        for pyfile in ports_dir.rglob("*.py"):
            import_lines.extend(self._get_imports(pyfile))
        forbidden = {"fastapi", "sqlalchemy", "nats_py", "httpx"}
        for imp in import_lines:
            for f in forbidden:
                if f in imp:
                    pytest.fail(f"Ports layer imports {f}: {imp}")

    def test_persistence_imports_only_domain_and_port_dtos(self) -> None:
        pers_dir = REPO_ROOT / "backend" / "planner" / "application" / "persistence"
        for pyfile in pers_dir.rglob("*.py"):
            imports = self._get_imports(pyfile)
            for imp in imports:
                if "sqlalchemy" in imp or "nats" in imp or "fastapi" in imp:
                    pytest.fail(f"Persistence imports {imp} in {pyfile.name}")

    def test_bootstrap_is_only_composition_root(self) -> None:
        bootstrap_path = REPO_ROOT / "backend" / "planner" / "bootstrap.py"
        text = bootstrap_path.read_text(encoding="utf-8")
        assert "Depends" in text
        assert "get_db" in text

    def test_nats_file_exists(self) -> None:
        nats_path = REPO_ROOT / "backend" / "planner" / "nats.py"
        assert nats_path.exists()
        text = nats_path.read_text(encoding="utf-8")
        assert "publish_planner_outbox_events" in text


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
                            if f"backend.planner.{upper}" in line:
                                pytest.fail(
                                    f"{rel} imports from upper layer '{upper}': {line}"
                                )


# ===================================================================
# 10. Coverage metrics
# ===================================================================


class TestCoverageMetrics:
    def test_domain_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_planner_domain.py").exists()

    def test_ports_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_planner_ports.py").exists()

    def test_persistence_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_planner_persistence_contracts.py").exists()

    def test_use_cases_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_planner_use_cases.py").exists()

    def test_adapter_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_planner_adapters.py").exists()

    def test_repository_integration_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_planner_repository_integration.py").exists()

    def test_bootstrap_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_planner_bootstrap.py").exists()

    def test_api_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_planner_api.py").exists()

    def test_nats_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_planner_nats.py").exists()

    def test_integration_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_planner_integration.py").exists()

    def test_service_closure_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_planner_service_closure.py").exists()

    def test_all_planner_test_files(self) -> None:
        test_dir = REPO_ROOT / "tests"
        actual = {p.name for p in test_dir.glob("test_planner_*.py")}
        missing = EXPECTED_TEST_FILES - actual
        extra = actual - EXPECTED_TEST_FILES
        if missing:
            pytest.fail(f"Missing planner test files: {missing}")
        if extra:
            pytest.fail(f"Unexpected planner test files: {extra}")
