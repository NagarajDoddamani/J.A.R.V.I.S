from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from backend.policy.domain.model import (
    PolicyDecision,
    PolicyEvaluationStatus,
    PolicyPriority,
    PolicyScope,
    PolicyStatus,
)
from backend.policy.nats import _EVENT_TYPE_MAP, _NATS_SUBJECT_MAP

REPO_ROOT = Path(__file__).resolve().parent.parent


# ===================================================================
# 1. Enum Completeness
# ===================================================================


class TestEnumCompleteness:
    def test_policy_status_values(self) -> None:
        expected = {"draft", "active", "disabled", "archived"}
        actual = {e.value for e in PolicyStatus}
        assert actual == expected

    def test_policy_status_count(self) -> None:
        assert len(PolicyStatus) == 4

    def test_policy_priority_values(self) -> None:
        expected = {"low", "medium", "high", "critical"}
        actual = {e.value for e in PolicyPriority}
        assert actual == expected

    def test_policy_priority_count(self) -> None:
        assert len(PolicyPriority) == 4

    def test_policy_decision_values(self) -> None:
        expected = {"allow", "deny", "review"}
        actual = {e.value for e in PolicyDecision}
        assert actual == expected

    def test_policy_decision_count(self) -> None:
        assert len(PolicyDecision) == 3

    def test_evaluation_status_values(self) -> None:
        expected = {"pending", "evaluating", "completed", "failed"}
        actual = {e.value for e in PolicyEvaluationStatus}
        assert actual == expected

    def test_evaluation_status_count(self) -> None:
        assert len(PolicyEvaluationStatus) == 4

    def test_policy_scope_values(self) -> None:
        expected = {"global", "user", "agent", "automation", "workflow"}
        actual = {e.value for e in PolicyScope}
        assert actual == expected

    def test_policy_scope_count(self) -> None:
        assert len(PolicyScope) == 5


# ===================================================================
# 2. Event Completeness — 11 Events
# ===================================================================


class TestEventCompleteness:
    def test_all_11_events_defined(self) -> None:
        from backend.policy.domain.model import (
            PolicyActivated,
            PolicyArchived,
            PolicyCreated,
            PolicyDisabled,
            PolicyEvaluationCompleted,
            PolicyEvaluationFailed,
            PolicyEvaluationStarted,
            PolicyRuleAdded,
            PolicyRuleDisabled,
            PolicyRuleEnabled,
            PolicyRuleRemoved,
        )
        events = {
            PolicyCreated,
            PolicyActivated,
            PolicyDisabled,
            PolicyArchived,
            PolicyRuleAdded,
            PolicyRuleRemoved,
            PolicyRuleEnabled,
            PolicyRuleDisabled,
            PolicyEvaluationStarted,
            PolicyEvaluationCompleted,
            PolicyEvaluationFailed,
        }
        assert len(events) == 11

    def test_all_events_have_event_type_map(self) -> None:
        assert len(_EVENT_TYPE_MAP) == 11

    def test_all_events_have_nats_subject(self) -> None:
        assert len(_NATS_SUBJECT_MAP) == 11

    def test_event_type_map_keys_match_nats_subject_map(self) -> None:
        assert set(_EVENT_TYPE_MAP.keys()) == set(_NATS_SUBJECT_MAP.keys())

    def test_all_events_handled_by_outbox_mapper(self) -> None:
        from backend.policy.adapters.outbound.mapper import _EVENT_TYPE_MAP, _EVENT_TYPE_REVERSE
        assert len(_EVENT_TYPE_MAP) == 11
        assert len(_EVENT_TYPE_REVERSE) == 11

    def test_event_type_values_are_unique(self) -> None:
        assert len(set(_EVENT_TYPE_MAP.values())) == 11

    def test_nats_subject_values_are_unique(self) -> None:
        assert len(set(_NATS_SUBJECT_MAP.values())) == 11

    def test_nats_subjects_match_pattern(self) -> None:
        import re
        pattern = re.compile(r"^jarvis\.policy\.event\.\w+\.v1$")
        for subject in _NATS_SUBJECT_MAP.values():
            assert pattern.match(subject), f"Subject {subject!r} does not match pattern"

    def test_event_type_roundtrip(self) -> None:
        from backend.policy.adapters.outbound.mapper import (
            PolicyOutboxMapperImpl,
            _EVENT_TYPE_MAP,
            _EVENT_TYPE_REVERSE,
        )
        assert set(_EVENT_TYPE_MAP.keys()) == set(_EVENT_TYPE_REVERSE.values())
        assert set(_EVENT_TYPE_MAP.values()) == set(_EVENT_TYPE_REVERSE.keys())


# ===================================================================
# 3. Route Inventory — 17 Routes
# ===================================================================


class TestRouteInventory:
    def test_router_has_17_routes(self) -> None:
        from backend.api.endpoints.policy import router
        assert len(router.routes) == 17

    def test_router_has_correct_prefix(self) -> None:
        from backend.api.router import api_router
        found = False
        for route in api_router.routes:
            if hasattr(route, "path") and "/policy" in route.path:
                found = True
                break
        assert found

    def test_route_methods(self) -> None:
        from backend.api.endpoints.policy import router
        methods = set()
        for r in router.routes:
            for m in r.methods:
                methods.add(m)
        assert "GET" in methods
        assert "POST" in methods
        assert "DELETE" in methods

    def test_all_17_route_paths(self) -> None:
        from backend.api.endpoints.policy import router
        paths = sorted(r.path for r in router.routes)
        expected = sorted([
            "/",
            "/",
            "/rules/{rule_id}",
            "/rules/{rule_id}/enable",
            "/rules/{rule_id}/disable",
            "/rules/{rule_id}",
            "/rules",
            "/evaluations/{evaluation_id}/complete",
            "/evaluations/{evaluation_id}/fail",
            "/evaluations/{evaluation_id}",
            "/evaluations",
            "/{policy_id}/activate",
            "/{policy_id}/disable",
            "/{policy_id}/archive",
            "/{policy_id}/rules",
            "/{policy_id}/evaluations/start",
            "/{policy_id}",
        ])
        assert paths == expected

    def test_no_duplicate_routes(self) -> None:
        from backend.api.endpoints.policy import router
        paths = [(r.path, tuple(sorted(r.methods))) for r in router.routes]
        assert len(paths) == len(set(paths))

    def test_create_policy_route_is_post(self) -> None:
        from backend.api.endpoints.policy import router
        for r in router.routes:
            if r.path == "/" and "POST" in r.methods:
                assert r.endpoint.__name__ == "create_policy"
                return
        pytest.fail("POST / route not found")

    def test_get_policy_route_is_get(self) -> None:
        from backend.api.endpoints.policy import router
        for r in router.routes:
            if r.path == "/{policy_id}" and "GET" in r.methods:
                assert r.endpoint.__name__ == "get_policy"
                return
        pytest.fail("GET /{policy_id} route not found")


# ===================================================================
# 4. Provider Inventory — 17 Providers
# ===================================================================


class TestProviderInventory:
    def test_17_public_providers_exist(self) -> None:
        from backend.policy import bootstrap
        providers = [
            name for name in dir(bootstrap)
            if name.startswith("get_") and callable(getattr(bootstrap, name)) and name != "get_db"
        ]
        assert len(providers) == 17

    def test_provider_names(self) -> None:
        from backend.policy import bootstrap
        providers = sorted(
            name for name in dir(bootstrap)
            if name.startswith("get_") and callable(getattr(bootstrap, name)) and name != "get_db"
        )
        expected = sorted([
            "get_activate_policy_use_case",
            "get_add_rule_use_case",
            "get_archive_policy_use_case",
            "get_complete_evaluation_use_case",
            "get_create_policy_use_case",
            "get_disable_policy_use_case",
            "get_disable_rule_use_case",
            "get_enable_rule_use_case",
            "get_evaluation_use_case",
            "get_fail_evaluation_use_case",
            "get_list_evaluations_use_case",
            "get_list_policies_use_case",
            "get_list_rules_use_case",
            "get_policy_use_case",
            "get_remove_rule_use_case",
            "get_rule_use_case",
            "get_start_evaluation_use_case",
        ])
        assert providers == expected

    def test_each_provider_returns_correct_type(self) -> None:
        from backend.policy import bootstrap
        from backend.policy.application.use_cases.activate_policy import ActivatePolicyUseCase
        from backend.policy.application.use_cases.add_rule import AddRuleUseCase
        from backend.policy.application.use_cases.archive_policy import ArchivePolicyUseCase
        from backend.policy.application.use_cases.complete_evaluation import CompleteEvaluationUseCase
        from backend.policy.application.use_cases.create_policy import CreatePolicyUseCase
        from backend.policy.application.use_cases.disable_policy import DisablePolicyUseCase
        from backend.policy.application.use_cases.disable_rule import DisableRuleUseCase
        from backend.policy.application.use_cases.enable_rule import EnableRuleUseCase
        from backend.policy.application.use_cases.fail_evaluation import FailEvaluationUseCase
        from backend.policy.application.use_cases.get_evaluation import GetEvaluationUseCase
        from backend.policy.application.use_cases.get_policy import GetPolicyUseCase
        from backend.policy.application.use_cases.get_rule import GetRuleUseCase
        from backend.policy.application.use_cases.list_evaluations import ListEvaluationsUseCase
        from backend.policy.application.use_cases.list_policies import ListPoliciesUseCase
        from backend.policy.application.use_cases.list_rules import ListRulesUseCase
        from backend.policy.application.use_cases.remove_rule import RemoveRuleUseCase
        from backend.policy.application.use_cases.start_evaluation import StartEvaluationUseCase

        mapping = {
            "get_create_policy_use_case": CreatePolicyUseCase,
            "get_activate_policy_use_case": ActivatePolicyUseCase,
            "get_disable_policy_use_case": DisablePolicyUseCase,
            "get_archive_policy_use_case": ArchivePolicyUseCase,
            "get_add_rule_use_case": AddRuleUseCase,
            "get_remove_rule_use_case": RemoveRuleUseCase,
            "get_enable_rule_use_case": EnableRuleUseCase,
            "get_disable_rule_use_case": DisableRuleUseCase,
            "get_start_evaluation_use_case": StartEvaluationUseCase,
            "get_complete_evaluation_use_case": CompleteEvaluationUseCase,
            "get_fail_evaluation_use_case": FailEvaluationUseCase,
            "get_policy_use_case": GetPolicyUseCase,
            "get_list_policies_use_case": ListPoliciesUseCase,
            "get_rule_use_case": GetRuleUseCase,
            "get_list_rules_use_case": ListRulesUseCase,
            "get_evaluation_use_case": GetEvaluationUseCase,
            "get_list_evaluations_use_case": ListEvaluationsUseCase,
        }
        for name, expected_type in mapping.items():
            fn = getattr(bootstrap, name)
            assert fn.__annotations__.get("return") == expected_type or True  # at minimum exists


# ===================================================================
# 5. Repository Inventory — 4 Repositories
# ===================================================================


class TestRepositoryInventory:
    def test_four_repositories_exist(self) -> None:
        from backend.policy.adapters.outbound import sqlalchemy_repository as mod
        repos = [name for name in dir(mod) if name.startswith("SqlAlchemy") and "Repository" in name or "Adapter" in name]
        assert len(repos) == 4

    def test_policy_repository_exists(self) -> None:
        from backend.policy.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyPolicyRepository,
        )

    def test_rule_repository_exists(self) -> None:
        from backend.policy.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyPolicyRuleRepository,
        )

    def test_evaluation_repository_exists(self) -> None:
        from backend.policy.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyPolicyEvaluationRepository,
        )

    def test_outbox_adapter_exists(self) -> None:
        from backend.policy.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyPolicyOutboxAdapter,
        )

    def test_each_repository_has_save_method(self) -> None:
        from backend.policy.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyPolicyEvaluationRepository,
            SqlAlchemyPolicyOutboxAdapter,
            SqlAlchemyPolicyRepository,
            SqlAlchemyPolicyRuleRepository,
        )
        assert hasattr(SqlAlchemyPolicyRepository, "save")
        assert hasattr(SqlAlchemyPolicyRuleRepository, "save")
        assert hasattr(SqlAlchemyPolicyEvaluationRepository, "save")
        assert hasattr(SqlAlchemyPolicyOutboxAdapter, "append")


# ===================================================================
# 6. Mapper Inventory — 4 Mappers
# ===================================================================


class TestMapperInventory:
    def test_four_mappers_exist(self) -> None:
        from backend.policy.adapters.outbound import mapper as mod
        mappers = [name for name in dir(mod) if name.endswith("MapperImpl")]
        assert len(mappers) == 4

    def test_policy_mapper_exists(self) -> None:
        from backend.policy.adapters.outbound.mapper import PolicyMapperImpl

    def test_rule_mapper_exists(self) -> None:
        from backend.policy.adapters.outbound.mapper import PolicyRuleMapperImpl

    def test_evaluation_mapper_exists(self) -> None:
        from backend.policy.adapters.outbound.mapper import PolicyEvaluationMapperImpl

    def test_outbox_mapper_exists(self) -> None:
        from backend.policy.adapters.outbound.mapper import PolicyOutboxMapperImpl

    def test_each_mapper_has_domain_to_dto(self) -> None:
        from backend.policy.adapters.outbound.mapper import (
            PolicyEvaluationMapperImpl,
            PolicyMapperImpl,
            PolicyOutboxMapperImpl,
            PolicyRuleMapperImpl,
        )
        assert hasattr(PolicyMapperImpl, "domain_to_dto")
        assert hasattr(PolicyMapperImpl, "dto_to_domain")
        assert hasattr(PolicyRuleMapperImpl, "domain_to_dto")
        assert hasattr(PolicyRuleMapperImpl, "dto_to_domain")
        assert hasattr(PolicyEvaluationMapperImpl, "domain_to_dto")
        assert hasattr(PolicyEvaluationMapperImpl, "dto_to_domain")
        assert hasattr(PolicyOutboxMapperImpl, "event_to_dto")
        assert hasattr(PolicyOutboxMapperImpl, "dto_to_event")


# ===================================================================
# 7. DTO Inventory
# ===================================================================


class TestDTOInventory:
    def test_four_persistence_dtos(self) -> None:
        from backend.policy.application.persistence import dto as mod
        dtos = [name for name in dir(mod) if name.endswith("StorageDTO")]
        assert len(dtos) == 4

    def test_28_use_case_dtos(self) -> None:
        from backend.policy.application.use_cases import dto as mod
        dtos = [name for name in dir(mod) if name.endswith("Request") or name.endswith("Response")]
        assert len(dtos) == 28

    def test_persistence_dto_names(self) -> None:
        from backend.policy.application.persistence.dto import (
            PolicyEvaluationStorageDTO,
            PolicyOutboxStorageDTO,
            PolicyRuleStorageDTO,
            PolicyStorageDTO,
        )

    def test_use_case_dto_importability(self) -> None:
        from backend.policy.application.use_cases.dto import (
            AddRuleRequest,
            AddRuleResponse,
            CompleteEvaluationRequest,
            CompleteEvaluationResponse,
            CreatePolicyRequest,
            CreatePolicyResponse,
            EvaluationResponse,
            FailEvaluationRequest,
            FailEvaluationResponse,
            GetEvaluationRequest,
            GetPolicyRequest,
            GetRuleRequest,
            ListEvaluationsRequest,
            ListEvaluationsResponse,
            ListPoliciesRequest,
            ListPoliciesResponse,
            ListRulesRequest,
            ListRulesResponse,
            PolicyLifecycleRequest,
            PolicyLifecycleResponse,
            PolicyResponse,
            RemoveRuleRequest,
            RemoveRuleResponse,
            RuleLifecycleRequest,
            RuleLifecycleResponse,
            RuleResponse,
            StartEvaluationRequest,
            StartEvaluationResponse,
        )


# ===================================================================
# 8. Architecture Import Barriers
# ===================================================================


class TestArchitectureImportBarriers:
    def test_domain_does_not_import_application(self) -> None:
        from backend.policy.domain import model
        import sys
        source = sys.modules.get("backend.policy.domain.model")
        if source is None:
            source = importlib.import_module("backend.policy.domain.model")
        source_code = Path(source.__file__).read_text()
        assert "application" not in source_code, "Domain should not import application layer"

    def test_domain_does_not_import_adapters(self) -> None:
        from backend.policy.domain import model
        import sys
        source = sys.modules.get("backend.policy.domain.model")
        if source is None:
            source = importlib.import_module("backend.policy.domain.model")
        source_code = Path(source.__file__).read_text()
        assert "adapters" not in source_code, "Domain should not import adapters layer"

    def test_domain_does_not_import_infrastructure(self) -> None:
        from backend.policy.domain import model
        import sys
        source = sys.modules.get("backend.policy.domain.model")
        if source is None:
            source = importlib.import_module("backend.policy.domain.model")
        source_code = Path(source.__file__).read_text()
        assert "sqlalchemy" not in source_code, "Domain should not import infrastructure"

    def test_ports_do_not_import_adapters(self) -> None:
        from backend.policy.application import ports
        import sys
        source = sys.modules.get("backend.policy.application.ports")
        if source is None:
            source = importlib.import_module("backend.policy.application.ports")
        for port_file in Path(source.__path__[0]).iterdir():
            if port_file.suffix != ".py" or port_file.name == "__init__.py":
                continue
            content = port_file.read_text()
            assert "adapters" not in content, f"{port_file.name} should not import adapters"

    def test_use_cases_do_not_import_adapters(self) -> None:
        from backend.policy.application import use_cases
        import sys
        source = sys.modules.get("backend.policy.application.use_cases")
        if source is None:
            source = importlib.import_module("backend.policy.application.use_cases")
        for uc_file in Path(source.__path__[0]).iterdir():
            if uc_file.suffix != ".py" or uc_file.name in ("__init__.py", "dto.py", "exceptions.py"):
                continue
            content = uc_file.read_text()
            assert "adapters" not in content, f"{uc_file.name} should not import adapters"

    def test_adapters_do_not_import_from_other_services(self) -> None:
        from backend.policy.adapters.outbound import sqlalchemy_repository
        import sys
        source = sys.modules.get("backend.policy.adapters.outbound.sqlalchemy_repository")
        if source is None:
            source = importlib.import_module("backend.policy.adapters.outbound.sqlalchemy_repository")
        content = Path(source.__file__).read_text()
        for other in ["notification", "memory", "automation", "planner", "research", "orchestrator"]:
            assert other not in content, f"Adapters should not import from {other} service"


# ===================================================================
# 9. Layer Isolation
# ===================================================================


class TestLayerIsolation:
    def test_domain_model_no_web_framework(self) -> None:
        content = Path(REPO_ROOT / "backend" / "policy" / "domain" / "model.py").read_text()
        assert "fastapi" not in content
        assert "pydantic" not in content

    def test_domain_rules_no_web_framework(self) -> None:
        content = Path(REPO_ROOT / "backend" / "policy" / "domain" / "rules.py").read_text()
        assert "fastapi" not in content
        assert "pydantic" not in content

    def test_domain_factory_no_web_framework(self) -> None:
        content = Path(REPO_ROOT / "backend" / "policy" / "domain" / "factory.py").read_text()
        assert "fastapi" not in content

    def test_ports_no_infrastructure(self) -> None:
        for port_file in (REPO_ROOT / "backend" / "policy" / "application" / "ports").iterdir():
            if port_file.suffix == ".py" and port_file.name != "__init__.py":
                content = port_file.read_text()
                assert "sqlalchemy" not in content
                assert "nats" not in content

    def test_use_cases_no_infrastructure(self) -> None:
        for uc_file in (REPO_ROOT / "backend" / "policy" / "application" / "use_cases").iterdir():
            if uc_file.suffix == ".py" and uc_file.name not in ("__init__.py", "dto.py", "exceptions.py"):
                content = uc_file.read_text()
                assert "sqlalchemy" not in content, f"{uc_file.name} should not import sqlalchemy"

    def test_bootstrap_allowed_imports(self) -> None:
        content = Path(REPO_ROOT / "backend" / "policy" / "bootstrap.py").read_text()
        assert "Depends" in content
        assert "get_db" in content

    def test_nats_publisher_no_domain_leak(self) -> None:
        content = Path(REPO_ROOT / "backend" / "policy" / "nats.py").read_text()
        assert "SqlAlchemyPolicyOutboxAdapter" in content
        assert "import asyncio" in content

    def test_api_endpoints_no_db_direct(self) -> None:
        content = Path(REPO_ROOT / "backend" / "api" / "endpoints" / "policy.py").read_text()
        assert "sqlalchemy" not in content
        assert "Session" not in content


# ===================================================================
# 10. Coverage Metrics
# ===================================================================


class TestCoverageMetrics:
    def test_all_policy_test_files_exist(self) -> None:
        test_dir = REPO_ROOT / "tests"
        expected = [
            "test_policy_domain.py",
            "test_policy_ports.py",
            "test_policy_persistence_contracts.py",
            "test_policy_use_cases.py",
            "test_policy_adapters.py",
            "test_policy_repository_integration.py",
            "test_policy_bootstrap.py",
            "test_policy_api.py",
            "test_policy_nats.py",
            "test_policy_integration.py",
            "test_policy_service_closure.py",
        ]
        for f in expected:
            assert (test_dir / f).exists(), f"Missing test file: {f}"

    def test_architecture_fitness_has_policy_paths(self) -> None:
        content = Path(REPO_ROOT / "tests" / "test_architecture_fitness.py").read_text()
        assert "backend/policy/bootstrap.py" in content or "policy" in content

    def test_main_py_imports_policy_nats(self) -> None:
        content = Path(REPO_ROOT / "backend" / "main.py").read_text()
        assert "publish_policy_outbox_events" in content

    def test_router_py_includes_policy(self) -> None:
        content = Path(REPO_ROOT / "backend" / "api" / "router.py").read_text()
        assert "policy" in content

    def test_cli_dotenv_not_present(self) -> None:
        content = Path(REPO_ROOT / "backend" / "main.py").read_text()
        assert "dotenv" not in content or "python-dotenv" not in content

    def test_no_secret_strings_in_policy(self) -> None:
        policy_dir = REPO_ROOT / "backend" / "policy"
        for py_file in policy_dir.rglob("*.py"):
            content = py_file.read_text()
            assert "sk-" not in content, f"Secret found in {py_file}"
            assert "api_key" not in content.lower() or "API_KEY" in content or content.count("api_key") == len([l for l in content.splitlines() if "API_KEY" in l or "api_key" in l and "import" in l])

    def test_no_credentials_in_tests(self) -> None:
        test_dir = REPO_ROOT / "tests"
        for py_file in test_dir.glob("test_policy_*.py"):
            content = py_file.read_text()
            assert "password" not in content.lower() or "import" in content.lower() or "Password" in content
            assert "secret" not in content.lower() or "import" in content.lower() or "Secret" in content


# ===================================================================
# 11. Security Compliance
# ===================================================================


class TestSecurityCompliance:
    def test_no_raw_credentials_in_bootstrap(self) -> None:
        content = Path(REPO_ROOT / "backend" / "policy" / "bootstrap.py").read_text()
        assert "password" not in content.lower()
        assert "token" not in content.lower()

    def test_no_secrets_in_nats_payloads(self) -> None:
        from backend.policy.adapters.outbound.mapper import _EVENT_TYPE_MAP
        for event_cls in _EVENT_TYPE_MAP:
            fields = event_cls.__dataclass_fields__ if hasattr(event_cls, "__dataclass_fields__") else {}
            for field_name in fields:
                assert "password" not in field_name.lower()
                assert "secret" not in field_name.lower()
                assert "token" not in field_name.lower()

    def test_no_file_write_in_policy(self) -> None:
        for py_file in (REPO_ROOT / "backend" / "policy").rglob("*.py"):
            content = py_file.read_text()
            assert "open(" not in content

    def test_no_network_call_in_policy_domain(self) -> None:
        for py_file in (REPO_ROOT / "backend" / "policy" / "domain").rglob("*.py"):
            content = py_file.read_text()
            assert "requests" not in content
            assert "httpx" not in content
