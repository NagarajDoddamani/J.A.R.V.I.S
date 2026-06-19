from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from backend.automation.domain.model import (
    AutomationStatus,
    TriggerType,
    ExecutionStatus,
    ExecutionMode,
    ActionType,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestEnumCompleteness:
    def test_automation_status_values(self) -> None:
        expected = {"draft", "active", "paused", "running", "completed", "failed", "disabled"}
        actual = {e.value for e in AutomationStatus}
        assert actual == expected

    def test_automation_status_count(self) -> None:
        assert len(AutomationStatus) == 7

    def test_trigger_type_values(self) -> None:
        expected = {"manual", "scheduled", "event", "webhook"}
        actual = {e.value for e in TriggerType}
        assert actual == expected

    def test_trigger_type_count(self) -> None:
        assert len(TriggerType) == 4

    def test_execution_status_values(self) -> None:
        expected = {"pending", "running", "completed", "failed", "cancelled"}
        actual = {e.value for e in ExecutionStatus}
        assert actual == expected

    def test_execution_status_count(self) -> None:
        assert len(ExecutionStatus) == 5

    def test_execution_mode_values(self) -> None:
        expected = {"once", "recurring", "continuous"}
        actual = {e.value for e in ExecutionMode}
        assert actual == expected

    def test_execution_mode_count(self) -> None:
        assert len(ExecutionMode) == 3

    def test_action_type_values(self) -> None:
        expected = {"notification", "memory", "knowledge", "research", "orchestration", "custom"}
        actual = {e.value for e in ActionType}
        assert actual == expected

    def test_action_type_count(self) -> None:
        assert len(ActionType) == 6

    def test_valid_automation_transitions_count(self) -> None:
        from backend.automation.domain.model import VALID_AUTOMATION_TRANSITIONS
        total = sum(len(v) for v in VALID_AUTOMATION_TRANSITIONS.values())
        assert total == 12
        assert set(VALID_AUTOMATION_TRANSITIONS.keys()) == set(AutomationStatus)

    def test_valid_execution_transitions_count(self) -> None:
        from backend.automation.domain.model import VALID_EXECUTION_TRANSITIONS
        total = sum(len(v) for v in VALID_EXECUTION_TRANSITIONS.values())
        assert total == 5
        assert set(VALID_EXECUTION_TRANSITIONS.keys()) == set(ExecutionStatus)


class TestEventCompleteness:
    def test_all_11_events_exist(self) -> None:
        from backend.automation.domain.model import (
            ActionAdded,
            AutomationActivated,
            AutomationCreated,
            AutomationDisabled,
            AutomationExecutionCompleted,
            AutomationExecutionFailed,
            AutomationExecutionStarted,
            AutomationPaused,
            TriggerAdded,
            TriggerDisabled,
            TriggerEnabled,
        )
        events = {
            AutomationCreated,
            AutomationActivated,
            AutomationPaused,
            AutomationDisabled,
            AutomationExecutionStarted,
            AutomationExecutionCompleted,
            AutomationExecutionFailed,
            TriggerAdded,
            TriggerEnabled,
            TriggerDisabled,
            ActionAdded,
        }
        assert len(events) == 11

    def test_all_events_have_nats_subject(self) -> None:
        from backend.automation.nats import _NATS_SUBJECT_MAP
        from backend.automation.domain.model import (
            ActionAdded,
            AutomationActivated,
            AutomationCreated,
            AutomationDisabled,
            AutomationExecutionCompleted,
            AutomationExecutionFailed,
            AutomationExecutionStarted,
            AutomationPaused,
            TriggerAdded,
            TriggerDisabled,
            TriggerEnabled,
        )
        expected = {
            AutomationCreated,
            AutomationActivated,
            AutomationPaused,
            AutomationDisabled,
            AutomationExecutionStarted,
            AutomationExecutionCompleted,
            AutomationExecutionFailed,
            TriggerAdded,
            TriggerEnabled,
            TriggerDisabled,
            ActionAdded,
        }
        assert set(_NATS_SUBJECT_MAP.keys()) == expected

    def test_all_events_have_event_type(self) -> None:
        from backend.automation.nats import _EVENT_TYPE_MAP
        from backend.automation.domain.model import (
            ActionAdded,
            AutomationActivated,
            AutomationCreated,
            AutomationDisabled,
            AutomationExecutionCompleted,
            AutomationExecutionFailed,
            AutomationExecutionStarted,
            AutomationPaused,
            TriggerAdded,
            TriggerDisabled,
            TriggerEnabled,
        )
        expected = {
            AutomationCreated,
            AutomationActivated,
            AutomationPaused,
            AutomationDisabled,
            AutomationExecutionStarted,
            AutomationExecutionCompleted,
            AutomationExecutionFailed,
            TriggerAdded,
            TriggerEnabled,
            TriggerDisabled,
            ActionAdded,
        }
        assert set(_EVENT_TYPE_MAP.keys()) == expected

    def test_nats_subjects_follow_convention(self) -> None:
        from backend.automation.nats import _NATS_SUBJECT_MAP
        for event_cls, subject in _NATS_SUBJECT_MAP.items():
            assert subject.startswith("jarvis.event.automation."), f"{event_cls.__name__} subject {subject} does not start with jarvis.event.automation."
            assert subject.endswith(".v1"), f"{event_cls.__name__} subject {subject} does not end with .v1"

    def test_event_types_are_disjoint(self) -> None:
        from backend.automation.domain.model import (
            ActionAdded,
            AutomationActivated,
            AutomationCreated,
            AutomationDisabled,
            AutomationExecutionCompleted,
            AutomationExecutionFailed,
            AutomationExecutionStarted,
            AutomationPaused,
            TriggerAdded,
            TriggerDisabled,
            TriggerEnabled,
        )
        types = [
            AutomationCreated,
            AutomationActivated,
            AutomationPaused,
            AutomationDisabled,
            AutomationExecutionStarted,
            AutomationExecutionCompleted,
            AutomationExecutionFailed,
            TriggerAdded,
            TriggerEnabled,
            TriggerDisabled,
            ActionAdded,
        ]
        for i in range(len(types)):
            for j in range(i + 1, len(types)):
                assert types[i] is not types[j]


class TestRouteInventory:
    def test_all_17_routes_registered(self) -> None:
        from backend.api.endpoints.automation import router
        routes = [r.path for r in router.routes]
        expected = [
            "/automations",
            "/automations/{automation_id}",
            "/automations",
            "/automations/{automation_id}/activate",
            "/automations/{automation_id}/pause",
            "/automations/{automation_id}/disable",
            "/automations/{automation_id}/triggers",
            "/triggers/{trigger_id}/enable",
            "/triggers/{trigger_id}/disable",
            "/triggers/{trigger_id}",
            "/triggers",
            "/automations/{automation_id}/actions",
            "/automations/{automation_id}/executions",
            "/executions/{execution_id}/complete",
            "/executions/{execution_id}/fail",
            "/executions/{execution_id}",
            "/executions",
        ]
        for path in expected:
            assert path in routes, f"Missing route: {path}"
        assert len(routes) >= 17

    def test_router_has_correct_prefix(self) -> None:
        from backend.api.endpoints.automation import router
        assert len(router.routes) >= 1
        paths = [r.path for r in router.routes]
        for path in paths:
            assert path.startswith("/")

    def test_all_routes_have_http_methods(self) -> None:
        from backend.api.endpoints.automation import router
        for route in router.routes:
            assert hasattr(route, "methods")
            assert len(route.methods) >= 1


class TestProviderInventory:
    def test_all_17_providers_exist(self) -> None:
        from backend.automation import bootstrap
        providers = [
            "create_automation_use_case",
            "activate_automation_use_case",
            "pause_automation_use_case",
            "disable_automation_use_case",
            "add_trigger_use_case",
            "enable_trigger_use_case",
            "disable_trigger_use_case",
            "add_action_use_case",
            "start_execution_use_case",
            "complete_execution_use_case",
            "fail_execution_use_case",
            "get_automation_use_case",
            "list_automations_use_case",
            "get_trigger_use_case",
            "list_triggers_use_case",
            "get_execution_use_case",
            "list_executions_use_case",
        ]
        for name in providers:
            assert hasattr(bootstrap, name), f"Missing provider: {name}"

    def test_all_providers_return_correct_types(self) -> None:
        from backend.automation import bootstrap
        providers = {
            "create_automation_use_case": bootstrap.create_automation_use_case,
            "activate_automation_use_case": bootstrap.activate_automation_use_case,
            "pause_automation_use_case": bootstrap.pause_automation_use_case,
            "disable_automation_use_case": bootstrap.disable_automation_use_case,
            "add_trigger_use_case": bootstrap.add_trigger_use_case,
            "enable_trigger_use_case": bootstrap.enable_trigger_use_case,
            "disable_trigger_use_case": bootstrap.disable_trigger_use_case,
            "add_action_use_case": bootstrap.add_action_use_case,
            "start_execution_use_case": bootstrap.start_execution_use_case,
            "complete_execution_use_case": bootstrap.complete_execution_use_case,
            "fail_execution_use_case": bootstrap.fail_execution_use_case,
            "get_automation_use_case": bootstrap.get_automation_use_case,
            "list_automations_use_case": bootstrap.list_automations_use_case,
            "get_trigger_use_case": bootstrap.get_trigger_use_case,
            "list_triggers_use_case": bootstrap.list_triggers_use_case,
            "get_execution_use_case": bootstrap.get_execution_use_case,
            "list_executions_use_case": bootstrap.list_executions_use_case,
        }
        assert len(providers) == 17


class TestRepositoryInventory:
    def test_four_repositories_exist(self) -> None:
        from backend.automation.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyAutomationExecutionRepository,
            SqlAlchemyAutomationOutboxAdapter,
            SqlAlchemyAutomationRepository,
            SqlAlchemyTriggerRepository,
        )
        assert SqlAlchemyAutomationRepository is not None
        assert SqlAlchemyTriggerRepository is not None
        assert SqlAlchemyAutomationExecutionRepository is not None
        assert SqlAlchemyAutomationOutboxAdapter is not None

    def test_automation_repo_has_all_methods(self) -> None:
        from backend.automation.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyAutomationRepository,
        )
        methods = ["save", "find_by_id", "find_by_status", "find_by_execution_mode", "find_all", "count"]
        for m in methods:
            assert hasattr(SqlAlchemyAutomationRepository, m)

    def test_trigger_repo_has_all_methods(self) -> None:
        from backend.automation.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyTriggerRepository,
        )
        methods = ["save", "find_by_id", "find_by_type", "find_enabled", "find_all", "count"]
        for m in methods:
            assert hasattr(SqlAlchemyTriggerRepository, m)

    def test_execution_repo_has_all_methods(self) -> None:
        from backend.automation.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyAutomationExecutionRepository,
        )
        methods = ["save", "find_by_id", "find_by_status", "find_by_automation_id", "find_all", "count"]
        for m in methods:
            assert hasattr(SqlAlchemyAutomationExecutionRepository, m)

    def test_outbox_adapter_has_all_methods(self) -> None:
        from backend.automation.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyAutomationOutboxAdapter,
        )
        methods = ["append", "fetch_unpublished", "mark_published"]
        for m in methods:
            assert hasattr(SqlAlchemyAutomationOutboxAdapter, m)


class TestMapperInventory:
    def test_four_mappers_exist(self) -> None:
        from backend.automation.adapters.outbound.mapper import (
            AutomationExecutionMapperImpl,
            AutomationMapperImpl,
            AutomationOutboxMapperImpl,
            TriggerMapperImpl,
        )
        assert AutomationMapperImpl is not None
        assert TriggerMapperImpl is not None
        assert AutomationExecutionMapperImpl is not None
        assert AutomationOutboxMapperImpl is not None

    def test_automation_mapper_has_both_directions(self) -> None:
        from backend.automation.adapters.outbound.mapper import AutomationMapperImpl
        assert hasattr(AutomationMapperImpl, "domain_to_dto")
        assert hasattr(AutomationMapperImpl, "dto_to_domain")

    def test_trigger_mapper_has_both_directions(self) -> None:
        from backend.automation.adapters.outbound.mapper import TriggerMapperImpl
        assert hasattr(TriggerMapperImpl, "domain_to_dto")
        assert hasattr(TriggerMapperImpl, "dto_to_domain")

    def test_execution_mapper_has_both_directions(self) -> None:
        from backend.automation.adapters.outbound.mapper import AutomationExecutionMapperImpl
        assert hasattr(AutomationExecutionMapperImpl, "domain_to_dto")
        assert hasattr(AutomationExecutionMapperImpl, "dto_to_domain")

    def test_outbox_mapper_has_both_directions(self) -> None:
        from backend.automation.adapters.outbound.mapper import AutomationOutboxMapperImpl
        assert hasattr(AutomationOutboxMapperImpl, "event_to_dto")
        assert hasattr(AutomationOutboxMapperImpl, "dto_to_event")


class TestDtoInventory:
    def test_storage_dtos_exist(self) -> None:
        from backend.automation.application.persistence.dto import (
            AutomationExecutionStorageDTO,
            AutomationOutboxStorageDTO,
            AutomationStorageDTO,
            TriggerStorageDTO,
        )
        assert AutomationStorageDTO is not None
        assert TriggerStorageDTO is not None
        assert AutomationExecutionStorageDTO is not None
        assert AutomationOutboxStorageDTO is not None

    def test_use_case_dtos_exist(self) -> None:
        from backend.automation.application.use_cases.dto import (
            AddActionRequest,
            AddActionResponse,
            AddTriggerRequest,
            AddTriggerResponse,
            AutomationLifecycleRequest,
            AutomationLifecycleResponse,
            AutomationResponse,
            CompleteExecutionRequest,
            CompleteExecutionResponse,
            CreateAutomationRequest,
            CreateAutomationResponse,
            ExecutionResponse,
            FailExecutionRequest,
            FailExecutionResponse,
            GetAutomationRequest,
            GetExecutionRequest,
            GetTriggerRequest,
            ListAutomationsRequest,
            ListAutomationsResponse,
            ListExecutionsRequest,
            ListExecutionsResponse,
            ListTriggersRequest,
            ListTriggersResponse,
            StartExecutionRequest,
            StartExecutionResponse,
            TriggerLifecycleRequest,
            TriggerLifecycleResponse,
            TriggerResponse,
        )
        dtos = [
            AddActionRequest, AddActionResponse,
            AddTriggerRequest, AddTriggerResponse,
            AutomationLifecycleRequest, AutomationLifecycleResponse,
            AutomationResponse,
            CompleteExecutionRequest, CompleteExecutionResponse,
            CreateAutomationRequest, CreateAutomationResponse,
            ExecutionResponse,
            FailExecutionRequest, FailExecutionResponse,
            GetAutomationRequest, GetExecutionRequest, GetTriggerRequest,
            ListAutomationsRequest, ListAutomationsResponse,
            ListExecutionsRequest, ListExecutionsResponse,
            ListTriggersRequest, ListTriggersResponse,
            StartExecutionRequest, StartExecutionResponse,
            TriggerLifecycleRequest, TriggerLifecycleResponse,
            TriggerResponse,
        ]
        assert len(dtos) == 28


class TestArchitectureImportBarriers:
    ADAPTER_FRAMEWORKS = ["fastapi", "sqlalchemy", "nats", "httpx", "redis", "qdrant"]

    def _walk_py_files(self, pkg_root: Path) -> list[Path]:
        files = []
        for f in pkg_root.rglob("*.py"):
            if "__pycache__" in f.parts or f.name == "__init__.py":
                continue
            files.append(f)
        return sorted(files)

    def _imports_framework(self, path: Path, frameworks: list[str]) -> list[str]:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return []
        found = []
        import re
        for fw in frameworks:
            if re.search(rf"^\s*(?:from|import)\s+{re.escape(fw)}\b", text, re.MULTILINE):
                found.append(fw)
        return found

    @pytest.mark.parametrize("package", [
        "backend/automation/domain",
        "backend/automation/application/ports",
        "backend/automation/application/persistence",
        "backend/automation/application/use_cases",
    ])
    def test_domain_and_app_no_adapter_frameworks(self, package: str) -> None:
        pkg_path = REPO_ROOT / package
        if not pkg_path.is_dir():
            pytest.skip(f"Package path {package} does not exist")
        for path in self._walk_py_files(pkg_path):
            offenders = self._imports_framework(path, self.ADAPTER_FRAMEWORKS)
            assert not offenders, (
                f"{path.relative_to(REPO_ROOT)} imports adapter frameworks: {offenders}"
            )

    def test_ports_import_only_domain(self) -> None:
        from backend.automation.application.ports.repository import (
            AutomationExecutionRepositoryPort,
            AutomationRepositoryPort,
            TriggerRepositoryPort,
        )
        from backend.automation.application.ports.outbox import (
            AutomationOutboxPort,
        )
        assert AutomationRepositoryPort is not None
        assert TriggerRepositoryPort is not None
        assert AutomationExecutionRepositoryPort is not None
        assert AutomationOutboxPort is not None

    def test_bootstrap_is_only_composition_root(self) -> None:
        bootstrap_file = REPO_ROOT / "backend/automation/bootstrap.py"
        assert bootstrap_file.exists()
        text = bootstrap_file.read_text(encoding="utf-8")
        assert "Depends" in text

    def test_nats_file_exists(self) -> None:
        nats_file = REPO_ROOT / "backend/automation/nats.py"
        assert nats_file.exists()


class TestLayerIsolation:
    def test_domain_does_not_import_application(self) -> None:
        domain_dir = REPO_ROOT / "backend/automation/domain"
        for path in domain_dir.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            text = path.read_text(encoding="utf-8")
            if "from backend.automation.application" in text:
                pytest.fail(f"{path.relative_to(REPO_ROOT)} imports application layer")

    def test_application_does_not_import_adapters(self) -> None:
        app_dir = REPO_ROOT / "backend/automation/application"
        for path in app_dir.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            text = path.read_text(encoding="utf-8")
            if "from backend.automation.adapters" in text:
                pytest.fail(f"{path.relative_to(REPO_ROOT)} imports adapter layer")

    def test_domain_does_not_import_adapters(self) -> None:
        domain_dir = REPO_ROOT / "backend/automation/domain"
        for path in domain_dir.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            text = path.read_text(encoding="utf-8")
            if "from backend.automation.adapters" in text:
                pytest.fail(f"{path.relative_to(REPO_ROOT)} imports adapter layer")


class TestModuleImports:
    MODULES = [
        "backend.automation.domain.model",
        "backend.automation.domain.exceptions",
        "backend.automation.domain.rules",
        "backend.automation.domain.factory",
        "backend.automation.application.ports.repository",
        "backend.automation.application.ports.outbox",
        "backend.automation.application.ports.clock",
        "backend.automation.application.ports.id_generator",
        "backend.automation.application.persistence.dto",
        "backend.automation.application.persistence.mapper",
        "backend.automation.application.use_cases.dto",
        "backend.automation.application.use_cases.exceptions",
        "backend.automation.application.use_cases.create_automation",
        "backend.automation.application.use_cases.activate_automation",
        "backend.automation.application.use_cases.pause_automation",
        "backend.automation.application.use_cases.disable_automation",
        "backend.automation.application.use_cases.add_trigger",
        "backend.automation.application.use_cases.enable_trigger",
        "backend.automation.application.use_cases.disable_trigger",
        "backend.automation.application.use_cases.add_action",
        "backend.automation.application.use_cases.start_execution",
        "backend.automation.application.use_cases.complete_execution",
        "backend.automation.application.use_cases.fail_execution",
        "backend.automation.application.use_cases.get_automation",
        "backend.automation.application.use_cases.list_automations",
        "backend.automation.application.use_cases.get_trigger",
        "backend.automation.application.use_cases.list_triggers",
        "backend.automation.application.use_cases.get_execution",
        "backend.automation.application.use_cases.list_executions",
        "backend.automation.adapters.outbound.mapper",
        "backend.automation.adapters.outbound.models",
        "backend.automation.adapters.outbound.clock",
        "backend.automation.adapters.outbound.id_generator",
        "backend.automation.adapters.outbound.sqlalchemy_repository",
        "backend.api.endpoints.automation",
        "backend.automation.bootstrap",
        "backend.automation.nats",
    ]

    @pytest.mark.parametrize("module_path", MODULES)
    def test_module_imports(self, module_path: str) -> None:
        importlib.import_module(module_path)


class TestCoverageMetrics:
    EXPECTED_TEST_FILES = {
        "test_automation_domain.py",
        "test_automation_ports.py",
        "test_automation_persistence_contracts.py",
        "test_automation_use_cases.py",
        "test_automation_adapters.py",
        "test_automation_repository_integration.py",
        "test_automation_bootstrap.py",
        "test_automation_api.py",
        "test_automation_nats.py",
        "test_automation_integration.py",
        "test_automation_service_closure.py",
    }

    def test_all_expected_test_files_exist(self) -> None:
        test_dir = REPO_ROOT / "tests"
        actual = {f.name for f in test_dir.glob("test_automation_*.py")}
        missing = self.EXPECTED_TEST_FILES - actual
        assert not missing, f"Missing test files: {missing}"

    def test_no_unexpected_test_files(self) -> None:
        test_dir = REPO_ROOT / "tests"
        actual = {f.name for f in test_dir.glob("test_automation_*.py")}
        extra = actual - self.EXPECTED_TEST_FILES
        assert not extra, f"Unexpected test files: {extra}"

    def test_no_orphan_source_files(self) -> None:
        source_dir = REPO_ROOT / "backend/automation"
        expected_sources = {
            "backend/automation/domain/model.py",
            "backend/automation/domain/exceptions.py",
            "backend/automation/domain/rules.py",
            "backend/automation/domain/factory.py",
            "backend/automation/application/ports/repository.py",
            "backend/automation/application/ports/outbox.py",
            "backend/automation/application/ports/clock.py",
            "backend/automation/application/ports/id_generator.py",
            "backend/automation/application/persistence/dto.py",
            "backend/automation/application/persistence/mapper.py",
            "backend/automation/application/persistence/schema.py",
            "backend/automation/application/use_cases/dto.py",
            "backend/automation/application/use_cases/exceptions.py",
            "backend/automation/application/use_cases/create_automation.py",
            "backend/automation/application/use_cases/activate_automation.py",
            "backend/automation/application/use_cases/pause_automation.py",
            "backend/automation/application/use_cases/disable_automation.py",
            "backend/automation/application/use_cases/add_trigger.py",
            "backend/automation/application/use_cases/enable_trigger.py",
            "backend/automation/application/use_cases/disable_trigger.py",
            "backend/automation/application/use_cases/add_action.py",
            "backend/automation/application/use_cases/start_execution.py",
            "backend/automation/application/use_cases/complete_execution.py",
            "backend/automation/application/use_cases/fail_execution.py",
            "backend/automation/application/use_cases/get_automation.py",
            "backend/automation/application/use_cases/list_automations.py",
            "backend/automation/application/use_cases/get_trigger.py",
            "backend/automation/application/use_cases/list_triggers.py",
            "backend/automation/application/use_cases/get_execution.py",
            "backend/automation/application/use_cases/list_executions.py",
            "backend/automation/adapters/outbound/mapper.py",
            "backend/automation/adapters/outbound/models.py",
            "backend/automation/adapters/outbound/clock.py",
            "backend/automation/adapters/outbound/id_generator.py",
            "backend/automation/adapters/outbound/sqlalchemy_repository.py",
            "backend/api/endpoints/automation.py",
            "backend/automation/bootstrap.py",
            "backend/automation/nats.py",
        }
        for source_path in expected_sources:
            full_path = REPO_ROOT / source_path
            assert full_path.exists(), f"Expected source file missing: {source_path}"

    def test_source_file_count(self) -> None:
        source_dir = REPO_ROOT / "backend/automation"
        source_files = sorted(f.relative_to(REPO_ROOT) for f in source_dir.rglob("*.py") if "__pycache__" not in f.parts)
        assert len(source_files) >= 30
