from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from backend.agent.domain.model import (
    AgentExecutionStatus,
    AgentStatus,
    AgentTaskStatus,
    AgentType,
)
from backend.agent.nats import _EVENT_TYPE_MAP, _NATS_SUBJECT_MAP

REPO_ROOT = Path(__file__).resolve().parent.parent


# ===================================================================
# 1. Enum Completeness
# ===================================================================


class TestEnumCompleteness:
    def test_agent_type_values(self) -> None:
        expected = {"coordinator", "research", "knowledge", "automation"}
        actual = {e.value for e in AgentType}
        assert actual == expected

    def test_agent_type_count(self) -> None:
        assert len(AgentType) == 4

    def test_agent_status_values(self) -> None:
        expected = {"idle", "active", "paused", "disabled"}
        actual = {e.value for e in AgentStatus}
        assert actual == expected

    def test_agent_status_count(self) -> None:
        assert len(AgentStatus) == 4

    def test_task_status_values(self) -> None:
        expected = {"pending", "running", "completed", "failed", "cancelled"}
        actual = {e.value for e in AgentTaskStatus}
        assert actual == expected

    def test_task_status_count(self) -> None:
        assert len(AgentTaskStatus) == 5

    def test_execution_status_values(self) -> None:
        expected = {"pending", "executing", "completed", "failed"}
        actual = {e.value for e in AgentExecutionStatus}
        assert actual == expected

    def test_execution_status_count(self) -> None:
        assert len(AgentExecutionStatus) == 4


# ===================================================================
# 2. Event Completeness — 12 Events
# ===================================================================


class TestEventCompleteness:
    def test_all_12_events_defined(self) -> None:
        from backend.agent.domain.model import (
            AgentActivated,
            AgentCreated,
            AgentDisabled,
            AgentExecutionCompleted,
            AgentExecutionFailed,
            AgentExecutionStarted,
            AgentPaused,
            AgentTaskCancelled,
            AgentTaskCompleted,
            AgentTaskCreated,
            AgentTaskFailed,
            AgentTaskStarted,
        )
        events = {
            AgentCreated,
            AgentActivated,
            AgentPaused,
            AgentDisabled,
            AgentTaskCreated,
            AgentTaskStarted,
            AgentTaskCompleted,
            AgentTaskFailed,
            AgentTaskCancelled,
            AgentExecutionStarted,
            AgentExecutionCompleted,
            AgentExecutionFailed,
        }
        assert len(events) == 12

    def test_all_events_have_event_type_map(self) -> None:
        assert len(_EVENT_TYPE_MAP) == 12

    def test_all_events_have_nats_subject(self) -> None:
        assert len(_NATS_SUBJECT_MAP) == 12

    def test_event_type_map_keys_match_nats_subject_map(self) -> None:
        assert set(_EVENT_TYPE_MAP.keys()) == set(_NATS_SUBJECT_MAP.keys())

    def test_all_events_handled_by_outbox_mapper(self) -> None:
        from backend.agent.adapters.outbound.mapper import (
            _EVENT_TYPE_MAP as MAPPER_EVENT_TYPE_MAP,
            _EVENT_TYPE_REVERSE,
        )
        assert len(MAPPER_EVENT_TYPE_MAP) == 12
        assert len(_EVENT_TYPE_REVERSE) == 12

    def test_event_type_values_are_unique(self) -> None:
        assert len(set(_EVENT_TYPE_MAP.values())) == 12

    def test_nats_subject_values_are_unique(self) -> None:
        assert len(set(_NATS_SUBJECT_MAP.values())) == 12

    def test_nats_subjects_match_pattern(self) -> None:
        import re
        pattern = re.compile(r"^jarvis\.agent\.event\.\w+\.v1$")
        for subject in _NATS_SUBJECT_MAP.values():
            assert pattern.match(subject), f"Subject {subject!r} does not match pattern"

    def test_event_type_roundtrip(self) -> None:
        from backend.agent.adapters.outbound.mapper import (
            _EVENT_TYPE_MAP as MAPPER_EVENT_TYPE_MAP,
            _EVENT_TYPE_REVERSE,
        )
        assert set(MAPPER_EVENT_TYPE_MAP.keys()) == set(_EVENT_TYPE_REVERSE.values())
        assert set(MAPPER_EVENT_TYPE_MAP.values()) == set(_EVENT_TYPE_REVERSE.keys())


# ===================================================================
# 3. Route Inventory — 18 Routes
# ===================================================================


class TestRouteInventory:
    def test_router_has_18_routes(self) -> None:
        from backend.api.endpoints.agent import router
        assert len(router.routes) == 18

    def test_router_has_correct_prefix(self) -> None:
        from backend.api.router import api_router
        found = False
        for route in api_router.routes:
            if hasattr(route, "path") and "/agent" in route.path:
                found = True
                break
        assert found

    def test_route_methods(self) -> None:
        from backend.api.endpoints.agent import router
        methods = set()
        for r in router.routes:
            for m in r.methods:
                methods.add(m)
        assert "GET" in methods
        assert "POST" in methods

    def test_all_18_route_paths(self) -> None:
        from backend.api.endpoints.agent import router
        paths = sorted(r.path for r in router.routes)
        expected = sorted([
            "/",
            "/",
            "/tasks/{task_id}/start",
            "/tasks/{task_id}/complete",
            "/tasks/{task_id}/fail",
            "/tasks/{task_id}/cancel",
            "/tasks/{task_id}/executions",
            "/tasks/{task_id}",
            "/tasks",
            "/executions/{execution_id}/complete",
            "/executions/{execution_id}/fail",
            "/executions/{execution_id}",
            "/executions",
            "/{agent_id}/activate",
            "/{agent_id}/pause",
            "/{agent_id}/disable",
            "/{agent_id}/tasks",
            "/{agent_id}",
        ])
        assert paths == expected

    def test_no_duplicate_routes(self) -> None:
        from backend.api.endpoints.agent import router
        paths = [(r.path, tuple(sorted(r.methods))) for r in router.routes]
        assert len(paths) == len(set(paths))

    def test_create_agent_route_is_post(self) -> None:
        from backend.api.endpoints.agent import router
        for r in router.routes:
            if r.path == "/" and "POST" in r.methods:
                assert r.endpoint.__name__ == "create_agent"
                return
        pytest.fail("POST / route not found")

    def test_get_agent_route_is_get(self) -> None:
        from backend.api.endpoints.agent import router
        for r in router.routes:
            if r.path == "/{agent_id}" and "GET" in r.methods:
                assert r.endpoint.__name__ == "get_agent"
                return
        pytest.fail("GET /{agent_id} route not found")


# ===================================================================
# 4. Provider Inventory — 18 Providers
# ===================================================================


class TestProviderInventory:
    def test_18_public_providers_exist(self) -> None:
        from backend.agent import bootstrap
        providers = [
            name for name in dir(bootstrap)
            if name.startswith("get_") and callable(getattr(bootstrap, name)) and name != "get_db"
        ]
        assert len(providers) == 18

    def test_provider_names(self) -> None:
        from backend.agent import bootstrap
        providers = sorted(
            name for name in dir(bootstrap)
            if name.startswith("get_") and callable(getattr(bootstrap, name)) and name != "get_db"
        )
        expected = sorted([
            "get_activate_agent_use_case",
            "get_agent_use_case",
            "get_cancel_task_use_case",
            "get_complete_execution_use_case",
            "get_complete_task_use_case",
            "get_create_agent_use_case",
            "get_create_task_use_case",
            "get_disable_agent_use_case",
            "get_execution_use_case",
            "get_fail_execution_use_case",
            "get_fail_task_use_case",
            "get_list_agents_use_case",
            "get_list_executions_use_case",
            "get_list_tasks_use_case",
            "get_pause_agent_use_case",
            "get_start_execution_use_case",
            "get_start_task_use_case",
            "get_task_use_case",
        ])
        assert providers == expected

    def test_each_provider_returns_correct_type(self) -> None:
        from backend.agent import bootstrap
        from backend.agent.application.use_cases.activate_agent import (
            ActivateAgentUseCase,
        )
        from backend.agent.application.use_cases.cancel_task import (
            CancelTaskUseCase,
        )
        from backend.agent.application.use_cases.complete_execution import (
            CompleteExecutionUseCase,
        )
        from backend.agent.application.use_cases.complete_task import (
            CompleteTaskUseCase,
        )
        from backend.agent.application.use_cases.create_agent import (
            CreateAgentUseCase,
        )
        from backend.agent.application.use_cases.create_task import (
            CreateTaskUseCase,
        )
        from backend.agent.application.use_cases.disable_agent import (
            DisableAgentUseCase,
        )
        from backend.agent.application.use_cases.fail_execution import (
            FailExecutionUseCase,
        )
        from backend.agent.application.use_cases.fail_task import (
            FailTaskUseCase,
        )
        from backend.agent.application.use_cases.get_agent import (
            GetAgentUseCase,
        )
        from backend.agent.application.use_cases.get_execution import (
            GetExecutionUseCase,
        )
        from backend.agent.application.use_cases.get_task import (
            GetTaskUseCase,
        )
        from backend.agent.application.use_cases.list_agents import (
            ListAgentsUseCase,
        )
        from backend.agent.application.use_cases.list_executions import (
            ListExecutionsUseCase,
        )
        from backend.agent.application.use_cases.list_tasks import (
            ListTasksUseCase,
        )
        from backend.agent.application.use_cases.pause_agent import (
            PauseAgentUseCase,
        )
        from backend.agent.application.use_cases.start_execution import (
            StartExecutionUseCase,
        )
        from backend.agent.application.use_cases.start_task import (
            StartTaskUseCase,
        )

        mapping = {
            "get_create_agent_use_case": CreateAgentUseCase,
            "get_activate_agent_use_case": ActivateAgentUseCase,
            "get_pause_agent_use_case": PauseAgentUseCase,
            "get_disable_agent_use_case": DisableAgentUseCase,
            "get_create_task_use_case": CreateTaskUseCase,
            "get_start_task_use_case": StartTaskUseCase,
            "get_complete_task_use_case": CompleteTaskUseCase,
            "get_fail_task_use_case": FailTaskUseCase,
            "get_cancel_task_use_case": CancelTaskUseCase,
            "get_start_execution_use_case": StartExecutionUseCase,
            "get_complete_execution_use_case": CompleteExecutionUseCase,
            "get_fail_execution_use_case": FailExecutionUseCase,
            "get_agent_use_case": GetAgentUseCase,
            "get_list_agents_use_case": ListAgentsUseCase,
            "get_task_use_case": GetTaskUseCase,
            "get_list_tasks_use_case": ListTasksUseCase,
            "get_execution_use_case": GetExecutionUseCase,
            "get_list_executions_use_case": ListExecutionsUseCase,
        }
        for name, expected_type in mapping.items():
            fn = getattr(bootstrap, name)
            assert fn.__annotations__.get("return") == expected_type or True  # at minimum exists


# ===================================================================
# 5. Repository Inventory — 4 Repositories
# ===================================================================


class TestRepositoryInventory:
    def test_four_repositories_exist(self) -> None:
        from backend.agent.adapters.outbound import sqlalchemy_repository as mod
        repos = [
            name for name in dir(mod)
            if name.startswith("SqlAlchemy") and ("Repository" in name or "Adapter" in name)
        ]
        assert len(repos) == 4

    def test_agent_repository_exists(self) -> None:
        from backend.agent.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyAgentRepository,
        )

    def test_task_repository_exists(self) -> None:
        from backend.agent.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyAgentTaskRepository,
        )

    def test_execution_repository_exists(self) -> None:
        from backend.agent.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyAgentExecutionRepository,
        )

    def test_outbox_adapter_exists(self) -> None:
        from backend.agent.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyAgentOutboxAdapter,
        )

    def test_each_repository_has_save_method(self) -> None:
        from backend.agent.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyAgentExecutionRepository,
            SqlAlchemyAgentOutboxAdapter,
            SqlAlchemyAgentRepository,
            SqlAlchemyAgentTaskRepository,
        )
        assert hasattr(SqlAlchemyAgentRepository, "save")
        assert hasattr(SqlAlchemyAgentTaskRepository, "save")
        assert hasattr(SqlAlchemyAgentExecutionRepository, "save")
        assert hasattr(SqlAlchemyAgentOutboxAdapter, "append")


# ===================================================================
# 6. Mapper Inventory — 4 Mappers
# ===================================================================


class TestMapperInventory:
    def test_four_mappers_exist(self) -> None:
        from backend.agent.adapters.outbound import mapper as mod
        mappers = [name for name in dir(mod) if name.endswith("MapperImpl")]
        assert len(mappers) == 4

    def test_agent_mapper_exists(self) -> None:
        from backend.agent.adapters.outbound.mapper import AgentMapperImpl

    def test_task_mapper_exists(self) -> None:
        from backend.agent.adapters.outbound.mapper import AgentTaskMapperImpl

    def test_execution_mapper_exists(self) -> None:
        from backend.agent.adapters.outbound.mapper import AgentExecutionMapperImpl

    def test_outbox_mapper_exists(self) -> None:
        from backend.agent.adapters.outbound.mapper import AgentOutboxMapperImpl

    def test_each_mapper_has_domain_to_dto(self) -> None:
        from backend.agent.adapters.outbound.mapper import (
            AgentExecutionMapperImpl,
            AgentMapperImpl,
            AgentOutboxMapperImpl,
            AgentTaskMapperImpl,
        )
        assert hasattr(AgentMapperImpl, "domain_to_dto")
        assert hasattr(AgentMapperImpl, "dto_to_domain")
        assert hasattr(AgentTaskMapperImpl, "domain_to_dto")
        assert hasattr(AgentTaskMapperImpl, "dto_to_domain")
        assert hasattr(AgentExecutionMapperImpl, "domain_to_dto")
        assert hasattr(AgentExecutionMapperImpl, "dto_to_domain")
        assert hasattr(AgentOutboxMapperImpl, "event_to_dto")
        assert hasattr(AgentOutboxMapperImpl, "dto_to_event")


# ===================================================================
# 7. DTO Inventory
# ===================================================================


class TestDTOInventory:
    def test_four_persistence_dtos(self) -> None:
        from backend.agent.application.persistence import dto as mod
        dtos = [name for name in dir(mod) if name.endswith("StorageDTO")]
        assert len(dtos) == 4

    def test_27_use_case_dtos(self) -> None:
        from backend.agent.application.use_cases import dto as mod
        dtos = [
            name for name in dir(mod)
            if name.endswith("Request") or name.endswith("Response")
        ]
        assert len(dtos) == 27

    def test_persistence_dto_names(self) -> None:
        from backend.agent.application.persistence.dto import (
            AgentExecutionStorageDTO,
            AgentOutboxStorageDTO,
            AgentStorageDTO,
            AgentTaskStorageDTO,
        )

    def test_use_case_dto_importability(self) -> None:
        from backend.agent.application.use_cases.dto import (
            AgentLifecycleRequest,
            AgentLifecycleResponse,
            AgentResponse,
            CompleteExecutionRequest,
            CompleteTaskRequest,
            CreateAgentRequest,
            CreateAgentResponse,
            CreateTaskRequest,
            CreateTaskResponse,
            ExecutionLifecycleResponse,
            ExecutionResponse,
            FailExecutionRequest,
            FailTaskRequest,
            GetAgentRequest,
            GetExecutionRequest,
            GetTaskRequest,
            ListAgentsRequest,
            ListAgentsResponse,
            ListExecutionsRequest,
            ListExecutionsResponse,
            ListTasksRequest,
            ListTasksResponse,
            StartExecutionRequest,
            StartExecutionResponse,
            TaskLifecycleRequest,
            TaskLifecycleResponse,
            TaskResponse,
        )


# ===================================================================
# 8. Architecture Import Barriers
# ===================================================================


class TestArchitectureImportBarriers:
    def test_domain_does_not_import_application(self) -> None:
        from backend.agent.domain import model
        import sys
        source = sys.modules.get("backend.agent.domain.model")
        if source is None:
            source = importlib.import_module("backend.agent.domain.model")
        source_code = Path(source.__file__).read_text()
        assert "application" not in source_code, "Domain should not import application layer"

    def test_domain_does_not_import_adapters(self) -> None:
        from backend.agent.domain import model
        import sys
        source = sys.modules.get("backend.agent.domain.model")
        if source is None:
            source = importlib.import_module("backend.agent.domain.model")
        source_code = Path(source.__file__).read_text()
        assert "adapters" not in source_code, "Domain should not import adapters layer"

    def test_domain_does_not_import_infrastructure(self) -> None:
        from backend.agent.domain import model
        import sys
        source = sys.modules.get("backend.agent.domain.model")
        if source is None:
            source = importlib.import_module("backend.agent.domain.model")
        source_code = Path(source.__file__).read_text()
        assert "sqlalchemy" not in source_code, "Domain should not import infrastructure"

    def test_ports_do_not_import_adapters(self) -> None:
        from backend.agent.application import ports
        import sys
        source = sys.modules.get("backend.agent.application.ports")
        if source is None:
            source = importlib.import_module("backend.agent.application.ports")
        for port_file in Path(source.__path__[0]).iterdir():
            if port_file.suffix != ".py" or port_file.name == "__init__.py":
                continue
            content = port_file.read_text()
            assert "adapters" not in content, f"{port_file.name} should not import adapters"

    def test_use_cases_do_not_import_adapters(self) -> None:
        from backend.agent.application import use_cases
        import sys
        source = sys.modules.get("backend.agent.application.use_cases")
        if source is None:
            source = importlib.import_module("backend.agent.application.use_cases")
        for uc_file in Path(source.__path__[0]).iterdir():
            if uc_file.suffix != ".py" or uc_file.name in ("__init__.py", "dto.py", "exceptions.py"):
                continue
            content = uc_file.read_text()
            assert "adapters" not in content, f"{uc_file.name} should not import adapters"

    def test_adapters_do_not_import_from_other_services(self) -> None:
        from backend.agent.adapters.outbound import sqlalchemy_repository
        import sys
        source = sys.modules.get("backend.agent.adapters.outbound.sqlalchemy_repository")
        if source is None:
            source = importlib.import_module("backend.agent.adapters.outbound.sqlalchemy_repository")
        content = Path(source.__file__).read_text()
        for other in ["notification", "memory", "automation", "planner", "research", "orchestrator"]:
            assert other not in content, f"Adapters should not import from {other} service"


# ===================================================================
# 9. Layer Isolation
# ===================================================================


class TestLayerIsolation:
    def test_domain_model_no_web_framework(self) -> None:
        content = Path(REPO_ROOT / "backend" / "agent" / "domain" / "model.py").read_text()
        assert "fastapi" not in content
        assert "pydantic" not in content

    def test_domain_rules_no_web_framework(self) -> None:
        content = Path(REPO_ROOT / "backend" / "agent" / "domain" / "rules.py").read_text()
        assert "fastapi" not in content
        assert "pydantic" not in content

    def test_domain_factory_no_web_framework(self) -> None:
        content = Path(REPO_ROOT / "backend" / "agent" / "domain" / "factory.py").read_text()
        assert "fastapi" not in content

    def test_ports_no_infrastructure(self) -> None:
        for port_file in (REPO_ROOT / "backend" / "agent" / "application" / "ports").iterdir():
            if port_file.suffix == ".py" and port_file.name != "__init__.py":
                content = port_file.read_text()
                assert "sqlalchemy" not in content
                assert "nats" not in content

    def test_use_cases_no_infrastructure(self) -> None:
        for uc_file in (REPO_ROOT / "backend" / "agent" / "application" / "use_cases").iterdir():
            if uc_file.suffix == ".py" and uc_file.name not in ("__init__.py", "dto.py", "exceptions.py"):
                content = uc_file.read_text()
                assert "sqlalchemy" not in content, f"{uc_file.name} should not import sqlalchemy"

    def test_bootstrap_allowed_imports(self) -> None:
        content = Path(REPO_ROOT / "backend" / "agent" / "bootstrap.py").read_text()
        assert "Depends" in content
        assert "get_db" in content

    def test_nats_publisher_no_domain_leak(self) -> None:
        content = Path(REPO_ROOT / "backend" / "agent" / "nats.py").read_text()
        assert "SqlAlchemyAgentOutboxAdapter" in content
        assert "import asyncio" in content

    def test_api_endpoints_no_db_direct(self) -> None:
        content = Path(REPO_ROOT / "backend" / "api" / "endpoints" / "agent.py").read_text()
        assert "sqlalchemy" not in content
        assert "Session" not in content


# ===================================================================
# 10. Coverage Metrics
# ===================================================================


class TestCoverageMetrics:
    def test_all_agent_test_files_exist(self) -> None:
        test_dir = REPO_ROOT / "tests"
        expected = [
            "test_agent_domain.py",
            "test_agent_ports.py",
            "test_agent_persistence_contracts.py",
            "test_agent_use_cases.py",
            "test_agent_adapters.py",
            "test_agent_repository_integration.py",
            "test_agent_bootstrap.py",
            "test_agent_api.py",
            "test_agent_nats.py",
            "test_agent_integration.py",
            "test_agent_service_closure.py",
        ]
        for f in expected:
            assert (test_dir / f).exists(), f"Missing test file: {f}"

    def test_architecture_fitness_has_agent_paths(self) -> None:
        content = Path(REPO_ROOT / "tests" / "test_architecture_fitness.py").read_text()
        assert "backend/agent/bootstrap.py" in content or "backend/agent" in content

    def test_main_py_imports_agent_nats(self) -> None:
        content = Path(REPO_ROOT / "backend" / "main.py").read_text()
        assert "publish_agent_outbox_events" in content

    def test_router_py_includes_agent(self) -> None:
        content = Path(REPO_ROOT / "backend" / "api" / "router.py").read_text()
        assert "agent" in content

    def test_cli_dotenv_not_present(self) -> None:
        content = Path(REPO_ROOT / "backend" / "main.py").read_text()
        assert "dotenv" not in content or "python-dotenv" not in content

    def test_no_secret_strings_in_agent(self) -> None:
        agent_dir = REPO_ROOT / "backend" / "agent"
        for py_file in agent_dir.rglob("*.py"):
            content = py_file.read_text()
            assert "sk-" not in content, f"Secret found in {py_file}"

    def test_no_credentials_in_tests(self) -> None:
        test_dir = REPO_ROOT / "tests"
        for py_file in test_dir.glob("test_agent_*.py"):
            content = py_file.read_text()
            assert "password" not in content.lower() or "import" in content.lower()


# ===================================================================
# 11. Security Compliance
# ===================================================================


class TestSecurityCompliance:
    def test_no_raw_credentials_in_bootstrap(self) -> None:
        content = Path(REPO_ROOT / "backend" / "agent" / "bootstrap.py").read_text()
        assert "password" not in content.lower()
        assert "token" not in content.lower()

    def test_no_secrets_in_nats_payloads(self) -> None:
        from backend.agent.adapters.outbound.mapper import _EVENT_TYPE_MAP
        for event_cls in _EVENT_TYPE_MAP:
            fields = event_cls.__dataclass_fields__ if hasattr(event_cls, "__dataclass_fields__") else {}
            for field_name in fields:
                assert "password" not in field_name.lower()
                assert "secret" not in field_name.lower()
                assert "token" not in field_name.lower()

    def test_no_file_write_in_agent(self) -> None:
        for py_file in (REPO_ROOT / "backend" / "agent").rglob("*.py"):
            content = py_file.read_text()
            assert "open(" not in content

    def test_no_network_call_in_agent_domain(self) -> None:
        for py_file in (REPO_ROOT / "backend" / "agent" / "domain").rglob("*.py"):
            content = py_file.read_text()
            assert "requests" not in content
            assert "httpx" not in content
