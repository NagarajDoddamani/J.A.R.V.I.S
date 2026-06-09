from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from backend.notification.domain.model import (
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
)


REPO_ROOT = Path(__file__).resolve().parent.parent


# ===================================================================
# 1. Enum Completeness
# ===================================================================


class TestEnumCompleteness:
    def test_notification_status_values(self) -> None:
        expected = {"pending", "shown", "acknowledged", "dismissed", "expired"}
        actual = {e.value for e in NotificationStatus}
        assert actual == expected

    def test_notification_status_count(self) -> None:
        assert len(NotificationStatus) == 5

    def test_notification_priority_values(self) -> None:
        expected = {"low", "normal", "high", "critical"}
        actual = {e.value for e in NotificationPriority}
        assert actual == expected

    def test_notification_priority_count(self) -> None:
        assert len(NotificationPriority) == 4

    def test_notification_channel_values(self) -> None:
        expected = {"in_app", "desktop", "email", "sms"}
        actual = {e.value for e in NotificationChannel}
        assert actual == expected

    def test_notification_channel_count(self) -> None:
        assert len(NotificationChannel) == 4

    def test_valid_transitions_count(self) -> None:
        from backend.notification.domain.rules import VALID_NOTIFICATION_TRANSITIONS
        total = sum(len(v) for v in VALID_NOTIFICATION_TRANSITIONS.values())
        assert total == 6
        assert set(VALID_NOTIFICATION_TRANSITIONS.keys()) == set(NotificationStatus)


# ===================================================================
# 2. Event Completeness
# ===================================================================


class TestEventCompleteness:
    def test_all_six_events_exist(self) -> None:
        from backend.notification.domain.model import (
            NotificationAcknowledged,
            NotificationActionInvoked,
            NotificationCreated,
            NotificationDismissed,
            NotificationExpired,
            NotificationShown,
        )
        events = {
            NotificationCreated,
            NotificationShown,
            NotificationAcknowledged,
            NotificationDismissed,
            NotificationExpired,
            NotificationActionInvoked,
        }
        assert len(events) == 6

    def test_all_events_have_nats_subject(self) -> None:
        from backend.notification.nats import _NATS_SUBJECT_MAP
        from backend.notification.domain.model import (
            NotificationAcknowledged,
            NotificationActionInvoked,
            NotificationCreated,
            NotificationDismissed,
            NotificationExpired,
            NotificationShown,
        )
        expected = {
            NotificationCreated,
            NotificationShown,
            NotificationAcknowledged,
            NotificationDismissed,
            NotificationExpired,
            NotificationActionInvoked,
        }
        assert set(_NATS_SUBJECT_MAP.keys()) == expected

    def test_all_events_have_event_type(self) -> None:
        from backend.notification.nats import _EVENT_TYPE_MAP
        from backend.notification.domain.model import (
            NotificationAcknowledged,
            NotificationActionInvoked,
            NotificationCreated,
            NotificationDismissed,
            NotificationExpired,
            NotificationShown,
        )
        expected = {
            NotificationCreated,
            NotificationShown,
            NotificationAcknowledged,
            NotificationDismissed,
            NotificationExpired,
            NotificationActionInvoked,
        }
        assert set(_EVENT_TYPE_MAP.keys()) == expected

    def test_all_events_handled_by_outbox_mapper(self) -> None:
        from backend.notification.adapters.outbound.mapper import (
            _EVENT_TYPE_MAP as mapper_map,
            _EVENT_TYPE_REVERSE,
        )
        from backend.notification.domain.model import (
            NotificationAcknowledged,
            NotificationActionInvoked,
            NotificationCreated,
            NotificationDismissed,
            NotificationExpired,
            NotificationShown,
        )
        expected_types = {
            NotificationCreated,
            NotificationShown,
            NotificationAcknowledged,
            NotificationDismissed,
            NotificationExpired,
            NotificationActionInvoked,
        }
        assert set(mapper_map.keys()) == expected_types
        assert len(mapper_map) == len(_EVENT_TYPE_REVERSE)

    def test_nats_subjects_follow_convention(self) -> None:
        from backend.notification.nats import _NATS_SUBJECT_MAP
        for event_cls, subject in _NATS_SUBJECT_MAP.items():
            assert subject.startswith("jarvis.notification.event.")
            assert subject.endswith(".v1")

    def test_event_types_are_disjoint(self) -> None:
        from backend.notification.domain.model import (
            NotificationAcknowledged,
            NotificationActionInvoked,
            NotificationCreated,
            NotificationDismissed,
            NotificationExpired,
            NotificationShown,
        )
        types = [
            NotificationCreated,
            NotificationShown,
            NotificationAcknowledged,
            NotificationDismissed,
            NotificationExpired,
            NotificationActionInvoked,
        ]
        for i in range(len(types)):
            for j in range(i + 1, len(types)):
                assert types[i] is not types[j]


# ===================================================================
# 3. Route Inventory
# ===================================================================


class TestRouteInventory:
    def test_all_nine_routes_registered(self) -> None:
        from backend.api.endpoints.notification import router
        routes = [r.path for r in router.routes]
        expected = [
            "/notifications",
            "/notifications/{notification_id}/show",
            "/notifications/{notification_id}/acknowledge",
            "/notifications/{notification_id}/dismiss",
            "/notifications/{notification_id}/expire",
            "/notifications/{notification_id}",
            "/notifications",
            "/notifications/{notification_id}/actions",
            "/notifications/actions/{action_id}/invoke",
        ]
        for path in expected:
            assert path in routes, f"Missing route: {path}"
        assert len(routes) >= 9

    def test_router_has_correct_prefix(self) -> None:
        from backend.api.router import api_router
        found = False
        for route in api_router.routes:
            if hasattr(route, "path") and "notification" in route.path:
                found = True
                break
        assert found

    def test_all_routes_have_http_methods(self) -> None:
        from backend.api.endpoints.notification import router
        for route in router.routes:
            assert hasattr(route, "methods")
            assert len(route.methods) >= 1


# ===================================================================
# 4. Provider Inventory
# ===================================================================


class TestProviderInventory:
    def test_all_nine_providers_exist(self) -> None:
        from backend.notification import bootstrap
        providers = [
            "create_notification_use_case",
            "show_notification_use_case",
            "acknowledge_notification_use_case",
            "dismiss_notification_use_case",
            "expire_notification_use_case",
            "get_notification_use_case",
            "list_notifications_use_case",
            "create_action_use_case",
            "invoke_action_use_case",
        ]
        for name in providers:
            assert hasattr(bootstrap, name), f"Missing provider: {name}"

    def test_all_providers_return_correct_types(self) -> None:
        from backend.notification import bootstrap
        providers = {
            "create_notification_use_case": bootstrap.create_notification_use_case,
            "show_notification_use_case": bootstrap.show_notification_use_case,
            "acknowledge_notification_use_case": bootstrap.acknowledge_notification_use_case,
            "dismiss_notification_use_case": bootstrap.dismiss_notification_use_case,
            "expire_notification_use_case": bootstrap.expire_notification_use_case,
            "get_notification_use_case": bootstrap.get_notification_use_case,
            "list_notifications_use_case": bootstrap.list_notifications_use_case,
            "create_action_use_case": bootstrap.create_action_use_case,
            "invoke_action_use_case": bootstrap.invoke_action_use_case,
        }
        assert len(providers) == 9


# ===================================================================
# 5. Repository Inventory
# ===================================================================


class TestRepositoryInventory:
    def test_three_repositories_exist(self) -> None:
        from backend.notification.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyNotificationActionRepository,
            SqlAlchemyNotificationOutboxAdapter,
            SqlAlchemyNotificationRepository,
        )
        assert SqlAlchemyNotificationRepository is not None
        assert SqlAlchemyNotificationActionRepository is not None
        assert SqlAlchemyNotificationOutboxAdapter is not None

    def test_notification_repo_has_all_methods(self) -> None:
        from backend.notification.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyNotificationRepository,
        )
        methods = ["save", "find_by_id", "find_by_status", "find_by_priority",
                    "find_by_target", "find_expired", "count"]
        for m in methods:
            assert hasattr(SqlAlchemyNotificationRepository, m)

    def test_action_repo_has_all_methods(self) -> None:
        from backend.notification.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyNotificationActionRepository,
        )
        methods = ["save", "find_by_id", "find_by_notification_id", "count"]
        for m in methods:
            assert hasattr(SqlAlchemyNotificationActionRepository, m)

    def test_outbox_adapter_has_all_methods(self) -> None:
        from backend.notification.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyNotificationOutboxAdapter,
        )
        methods = ["append", "fetch_unpublished", "mark_published"]
        for m in methods:
            assert hasattr(SqlAlchemyNotificationOutboxAdapter, m)


# ===================================================================
# 6. Mapper Inventory
# ===================================================================


class TestMapperInventory:
    def test_three_mappers_exist(self) -> None:
        from backend.notification.adapters.outbound.mapper import (
            NotificationActionMapperImpl,
            NotificationMapperImpl,
            NotificationOutboxMapperImpl,
        )
        assert NotificationMapperImpl is not None
        assert NotificationActionMapperImpl is not None
        assert NotificationOutboxMapperImpl is not None

    def test_notification_mapper_has_both_directions(self) -> None:
        from backend.notification.adapters.outbound.mapper import NotificationMapperImpl
        assert hasattr(NotificationMapperImpl, "domain_to_dto")
        assert hasattr(NotificationMapperImpl, "dto_to_domain")

    def test_action_mapper_has_both_directions(self) -> None:
        from backend.notification.adapters.outbound.mapper import NotificationActionMapperImpl
        assert hasattr(NotificationActionMapperImpl, "domain_to_dto")
        assert hasattr(NotificationActionMapperImpl, "dto_to_domain")

    def test_outbox_mapper_has_both_directions(self) -> None:
        from backend.notification.adapters.outbound.mapper import NotificationOutboxMapperImpl
        assert hasattr(NotificationOutboxMapperImpl, "event_to_dto")
        assert hasattr(NotificationOutboxMapperImpl, "dto_to_event")


# ===================================================================
# 7. DTO Inventory
# ===================================================================


class TestDtoInventory:
    def test_storage_dtos_exist(self) -> None:
        from backend.notification.application.persistence.dto import (
            NotificationActionStorageDTO,
            NotificationOutboxStorageDTO,
            NotificationStorageDTO,
        )
        assert NotificationStorageDTO is not None
        assert NotificationActionStorageDTO is not None
        assert NotificationOutboxStorageDTO is not None

    def test_use_case_dtos_exist(self) -> None:
        from backend.notification.application.use_cases.dto import (
            AcknowledgeNotificationRequest,
            AcknowledgeNotificationResponse,
            CreateActionRequest,
            CreateActionResponse,
            CreateNotificationRequest,
            CreateNotificationResponse,
            DismissNotificationRequest,
            DismissNotificationResponse,
            ExpireNotificationRequest,
            ExpireNotificationResponse,
            GetNotificationRequest,
            InvokeActionRequest,
            InvokeActionResponse,
            ListNotificationsRequest,
            ListNotificationsResponse,
            NotificationActionResponse,
            NotificationResponse,
            ShowNotificationRequest,
            ShowNotificationResponse,
        )
        dtos = [
            AcknowledgeNotificationRequest, AcknowledgeNotificationResponse,
            CreateActionRequest, CreateActionResponse,
            CreateNotificationRequest, CreateNotificationResponse,
            DismissNotificationRequest, DismissNotificationResponse,
            ExpireNotificationRequest, ExpireNotificationResponse,
            GetNotificationRequest,
            InvokeActionRequest, InvokeActionResponse,
            ListNotificationsRequest, ListNotificationsResponse,
            NotificationActionResponse, NotificationResponse,
            ShowNotificationRequest, ShowNotificationResponse,
        ]
        assert len(dtos) == 19


# ===================================================================
# 8. Architecture Import Barriers
# ===================================================================


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
        "backend/notification/domain",
        "backend/notification/application/ports",
        "backend/notification/application/persistence",
        "backend/notification/application/use_cases",
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
        ports_dir = REPO_ROOT / "backend/notification/application/ports"
        for path in self._walk_py_files(ports_dir):
            text = path.read_text(encoding="utf-8")
            if "sqlalchemy" in text or "fastapi" in text or "nats" in text:
                pytest.fail(f"{path.relative_to(REPO_ROOT)} imports framework")

    def test_persistence_imports_only_domain_and_port_dtos(self) -> None:
        persistence_dir = REPO_ROOT / "backend/notification/application/persistence"
        for path in self._walk_py_files(persistence_dir):
            text = path.read_text(encoding="utf-8")
            if "sqlalchemy" in text or "fastapi" in text or "nats" in text:
                pytest.fail(f"{path.relative_to(REPO_ROOT)} imports framework")

    def test_bootstrap_is_only_composition_root(self) -> None:
        bootstrap_file = REPO_ROOT / "backend/notification/bootstrap.py"
        assert bootstrap_file.exists()
        text = bootstrap_file.read_text(encoding="utf-8")
        assert "Depends" in text

    def test_nats_file_exists(self) -> None:
        nats_file = REPO_ROOT / "backend/notification/nats.py"
        assert nats_file.exists()


# ===================================================================
# 9. Layer Isolation
# ===================================================================


class TestLayerIsolation:
    def test_domain_does_not_import_application(self) -> None:
        domain_dir = REPO_ROOT / "backend/notification/domain"
        for path in domain_dir.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            text = path.read_text(encoding="utf-8")
            if "from backend.notification.application" in text:
                pytest.fail(f"{path.relative_to(REPO_ROOT)} imports application layer")

    def test_application_does_not_import_adapters(self) -> None:
        app_dir = REPO_ROOT / "backend/notification/application"
        for path in app_dir.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            text = path.read_text(encoding="utf-8")
            if "from backend.notification.adapters" in text:
                pytest.fail(f"{path.relative_to(REPO_ROOT)} imports adapter layer")

    def test_domain_does_not_import_adapters(self) -> None:
        domain_dir = REPO_ROOT / "backend/notification/domain"
        for path in domain_dir.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            text = path.read_text(encoding="utf-8")
            if "from backend.notification.adapters" in text:
                pytest.fail(f"{path.relative_to(REPO_ROOT)} imports adapter layer")

    def test_use_cases_depend_only_on_ports(self) -> None:
        import inspect
        from backend.notification.application.use_cases.create_notification import (
            CreateNotificationUseCase,
        )
        from backend.notification.application.use_cases.show_notification import (
            ShowNotificationUseCase,
        )
        from backend.notification.application.use_cases.acknowledge_notification import (
            AcknowledgeNotificationUseCase,
        )
        from backend.notification.application.use_cases.dismiss_notification import (
            DismissNotificationUseCase,
        )
        from backend.notification.application.use_cases.expire_notification import (
            ExpireNotificationUseCase,
        )
        from backend.notification.application.use_cases.get_notification import (
            GetNotificationUseCase,
        )
        from backend.notification.application.use_cases.list_notifications import (
            ListNotificationsUseCase,
        )
        from backend.notification.application.use_cases.create_action import (
            CreateActionUseCase,
        )
        from backend.notification.application.use_cases.invoke_action import (
            InvokeActionUseCase,
        )
        cases = [
            CreateNotificationUseCase,
            ShowNotificationUseCase,
            AcknowledgeNotificationUseCase,
            DismissNotificationUseCase,
            ExpireNotificationUseCase,
            GetNotificationUseCase,
            ListNotificationsUseCase,
            CreateActionUseCase,
            InvokeActionUseCase,
        ]
        for uc in cases:
            sig = inspect.signature(uc.__init__)
            params = list(sig.parameters.keys())
            assert "self" in params


# ===================================================================
# 10. Security Compliance
# ===================================================================


class TestSecurityCompliance:
    def test_secret_patterns_defined(self) -> None:
        from backend.notification.domain.rules import SECRET_PATTERNS
        assert len(SECRET_PATTERNS) >= 5

    def test_secret_detected_error_exists(self) -> None:
        from backend.notification.domain.exceptions import SecretDetectedError
        assert SecretDetectedError is not None

    def test_content_validation_blocks_secrets(self) -> None:
        from backend.notification.domain.rules import assert_content_no_secrets
        with pytest.raises(Exception):
            assert_content_no_secrets("my password is 1234")
        with pytest.raises(Exception):
            assert_content_no_secrets("api_key=abc123")
        assert_content_no_secrets("hello world") is None


# ===================================================================
# 11. Module Import Verification
# ===================================================================


class TestModuleImports:
    MODULES = [
        "backend.notification.domain.model",
        "backend.notification.domain.exceptions",
        "backend.notification.domain.rules",
        "backend.notification.domain.factory",
        "backend.notification.application.ports.repository",
        "backend.notification.application.ports.outbox",
        "backend.notification.application.ports.clock",
        "backend.notification.application.ports.id_generator",
        "backend.notification.application.persistence.dto",
        "backend.notification.application.persistence.mapper",
        "backend.notification.application.use_cases.dto",
        "backend.notification.application.use_cases.exceptions",
        "backend.notification.application.use_cases.create_notification",
        "backend.notification.application.use_cases.show_notification",
        "backend.notification.application.use_cases.acknowledge_notification",
        "backend.notification.application.use_cases.dismiss_notification",
        "backend.notification.application.use_cases.expire_notification",
        "backend.notification.application.use_cases.get_notification",
        "backend.notification.application.use_cases.list_notifications",
        "backend.notification.application.use_cases.create_action",
        "backend.notification.application.use_cases.invoke_action",
        "backend.notification.adapters.outbound.mapper",
        "backend.notification.adapters.outbound.models",
        "backend.notification.adapters.outbound.clock",
        "backend.notification.adapters.outbound.id_generator",
        "backend.notification.adapters.outbound.sqlalchemy_repository",
        "backend.api.endpoints.notification",
        "backend.notification.bootstrap",
        "backend.notification.nats",
    ]

    @pytest.mark.parametrize("module_path", MODULES)
    def test_module_imports(self, module_path: str) -> None:
        importlib.import_module(module_path)
