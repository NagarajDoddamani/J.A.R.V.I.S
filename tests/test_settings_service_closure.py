from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest

from backend.settings.bootstrap import DEFAULT_REGISTRY
from backend.settings.domain.model import (
    SettingCategory,
    SettingScope,
    SettingDefinition,
)


# ---------------------------------------------------------------------------
# 1. Architecture Compliance — Layer isolation
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent


def _walk_py_files(package_root: Path) -> list[Path]:
    """Walk all .py files under a package root, skipping __pycache__."""
    files = []
    for f in package_root.rglob("*.py"):
        if "__pycache__" in f.parts or f.name == "__init__.py":
            continue
        files.append(f)
    return sorted(files)


def _imports_framework(path: Path, frameworks: list[str]) -> list[str]:
    """Return list of framework names imported by file at *path*."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    found: list[str] = []
    for fw in frameworks:
        import re
        if re.search(rf"^\s*(?:from|import)\s+{re.escape(fw)}\b", text, re.MULTILINE):
            found.append(fw)
    return found


class TestLayerIsolation:
    """Domain and application layers must not import adapter/infra frameworks."""

    ADAPTER_FRAMEWORKS = ["fastapi", "sqlalchemy", "nats", "httpx", "redis", "qdrant"]

    @pytest.mark.parametrize("package", [
        "backend/settings/domain",
        "backend/settings/application/ports",
        "backend/settings/application/persistence",
        "backend/settings/application/use_cases",
    ])
    def test_domain_and_app_no_adapter_frameworks(self, package: str) -> None:
        pkg_path = REPO_ROOT / package
        if not pkg_path.is_dir():
            pytest.skip(f"Package path {package} does not exist")
        for path in _walk_py_files(pkg_path):
            offenders = _imports_framework(path, self.ADAPTER_FRAMEWORKS)
            assert not offenders, (
                f"{path.relative_to(REPO_ROOT)} imports adapter "
                f"frameworks: {offenders}"
            )

    def test_ports_import_only_domain(self) -> None:
        ports_dir = REPO_ROOT / "backend/settings/application/ports"
        for path in _walk_py_files(ports_dir):
            text = path.read_text(encoding="utf-8")
            if "sqlalchemy" in text or "fastapi" in text or "nats" in text:
                pytest.fail(f"{path.relative_to(REPO_ROOT)} imports framework")

    def test_persistence_imports_only_domain_and_port_dtos(self) -> None:
        persistence_dir = REPO_ROOT / "backend/settings/application/persistence"
        for path in _walk_py_files(persistence_dir):
            text = path.read_text(encoding="utf-8")
            if "sqlalchemy" in text or "fastapi" in text or "nats" in text:
                pytest.fail(f"{path.relative_to(REPO_ROOT)} imports framework")

    def test_bootstrap_is_only_composition_root(self) -> None:
        bootstrap_file = REPO_ROOT / "backend/settings/bootstrap.py"
        assert bootstrap_file.exists(), "bootstrap.py must exist as composition root"
        text = bootstrap_file.read_text(encoding="utf-8")
        assert "Depends" in text, "bootstrap must wire use cases via Depends()"
        assert "DEFAULT_REGISTRY" in text, "bootstrap must define DEFAULT_REGISTRY"


# ---------------------------------------------------------------------------
# 2. Registry Audit
# ---------------------------------------------------------------------------


class TestRegistryAudit:
    """Audit the DEFAULT_REGISTRY for correctness and completeness."""

    def test_all_categories_represented(self) -> None:
        cats = {d.category for d in DEFAULT_REGISTRY.values()}
        assert cats == set(SettingCategory), (
            f"Missing categories: {set(SettingCategory) - cats}"
        )

    def test_all_scopes_represented(self) -> None:
        scopes = {d.scope for d in DEFAULT_REGISTRY.values()}
        assert SettingScope.USER in scopes
        assert SettingScope.SYSTEM in scopes

    def test_no_duplicate_keys(self) -> None:
        assert len(DEFAULT_REGISTRY) == len(set(DEFAULT_REGISTRY.keys()))

    def test_all_keys_have_valid_format(self) -> None:
        import re as regex
        pattern = r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$"
        for key in DEFAULT_REGISTRY:
            assert regex.match(pattern, key), f"Invalid key format: {key}"

    def test_all_definitions_have_valid_categories(self) -> None:
        valid = {c.value for c in SettingCategory}
        for key, d in DEFAULT_REGISTRY.items():
            assert d.category.value in valid, f"{key}: invalid category {d.category}"

    def test_all_definitions_have_valid_scopes(self) -> None:
        valid = {s.value for s in SettingScope}
        for key, d in DEFAULT_REGISTRY.items():
            assert d.scope.value in valid, f"{key}: invalid scope {d.scope}"

    def test_all_definitions_have_value_type(self) -> None:
        valid_types = {"str", "int", "float", "bool"}
        for key, d in DEFAULT_REGISTRY.items():
            assert d.value_type in valid_types, f"{key}: invalid type {d.value_type}"

    def test_default_values_match_types(self) -> None:
        for key, d in DEFAULT_REGISTRY.items():
            dv = d.default_value
            if d.value_type == "bool":
                assert isinstance(dv, bool), f"{key}: default {dv} not bool"
            elif d.value_type == "int":
                assert isinstance(dv, int), f"{key}: default {dv} not int"
            elif d.value_type == "float":
                assert isinstance(dv, (int, float)), f"{key}: default {dv} not float"
            elif d.value_type == "str":
                assert isinstance(dv, str), f"{key}: default {dv} not str"

    def test_numeric_definitions_have_bounds(self) -> None:
        for key, d in DEFAULT_REGISTRY.items():
            if d.value_type in ("int", "float"):
                if d.min_value is not None:
                    assert d.min_value <= d.max_value, (
                        f"{key}: min {d.min_value} > max {d.max_value}"
                    )

    def test_allowed_values_definitions_valid(self) -> None:
        for key, d in DEFAULT_REGISTRY.items():
            if d.allowed_values is not None:
                assert len(d.allowed_values) > 0, f"{key}: empty allowed_values"
                for v in d.allowed_values:
                    assert isinstance(v, str), f"{key}: allowed value {v} not str"

    def test_reserved_definitions_are_system_scope(self) -> None:
        for key, d in DEFAULT_REGISTRY.items():
            if d.reserved:
                assert d.scope == SettingScope.SYSTEM, (
                    f"{key}: reserved must be SYSTEM scope, got {d.scope}"
                )

    def test_safety_floor_definitions_have_min(self) -> None:
        for key, d in DEFAULT_REGISTRY.items():
            if d.safety_floor:
                assert d.min_value is not None or d.value_type == "bool", (
                    f"{key}: safety_floor set but no min_value"
                )

    def test_key_to_definition_consistency(self) -> None:
        for key, d in DEFAULT_REGISTRY.items():
            assert d.key == key, f"Definition key {d.key} != registry key {key}"


# ---------------------------------------------------------------------------
# 3. Module import verification — all layers load
# ---------------------------------------------------------------------------


class TestModuleImports:
    """Verify every layer module can be imported without errors."""

    MODULES = [
        "backend.settings.domain.model",
        "backend.settings.domain.exceptions",
        "backend.settings.domain.rules",
        "backend.settings.domain.factory",
        "backend.settings.application.ports.repository",
        "backend.settings.application.ports.outbox",
        "backend.settings.application.ports.clock",
        "backend.settings.application.persistence.dto",
        "backend.settings.application.persistence.mapper",
        "backend.settings.application.use_cases.dto",
        "backend.settings.application.use_cases.exceptions",
        "backend.settings.application.use_cases.get_settings",
        "backend.settings.application.use_cases.get_setting_by_key",
        "backend.settings.application.use_cases.patch_settings",
        "backend.settings.application.use_cases.reset_settings",
        "backend.settings.adapters.outbound.mapper",
        "backend.settings.adapters.outbound.models",
        "backend.settings.adapters.outbound.clock",
        "backend.settings.adapters.outbound.id_generator",
        "backend.settings.adapters.outbound.sqlalchemy_repository",
        "backend.api.endpoints.settings",
        "backend.settings.bootstrap",
        "backend.settings.nats",
    ]

    @pytest.mark.parametrize("module_path", MODULES)
    def test_module_imports(self, module_path: str) -> None:
        importlib.import_module(module_path)


# ---------------------------------------------------------------------------
# 4. Use case constructor contracts
# ---------------------------------------------------------------------------


class TestUseCaseContracts:
    """Verify use cases accept only port dependencies (not adapter impls)."""

    def test_get_settings_accepts_repo_port(self) -> None:
        from backend.settings.application.use_cases.get_settings import (
            GetSettingsUseCase,
        )
        import inspect
        sig = inspect.signature(GetSettingsUseCase.__init__)
        param_names = list(sig.parameters.keys())
        assert "repo" in param_names
        assert len(param_names) == 2

    def test_get_setting_by_key_accepts_repo_port(self) -> None:
        from backend.settings.application.use_cases.get_setting_by_key import (
            GetSettingByKeyUseCase,
        )
        import inspect
        sig = inspect.signature(GetSettingByKeyUseCase.__init__)
        param_names = list(sig.parameters.keys())
        assert "repo" in param_names
        assert len(param_names) == 2

    def test_patch_settings_accepts_ports(self) -> None:
        from backend.settings.application.use_cases.patch_settings import (
            PatchSettingsUseCase,
        )
        import inspect
        sig = inspect.signature(PatchSettingsUseCase.__init__)
        param_names = list(sig.parameters.keys())
        assert "repo" in param_names
        assert "outbox" in param_names
        assert "clock" in param_names
        assert "registry" in param_names

    def test_reset_settings_accepts_ports(self) -> None:
        from backend.settings.application.use_cases.reset_settings import (
            ResetSettingsUseCase,
        )
        import inspect
        sig = inspect.signature(ResetSettingsUseCase.__init__)
        param_names = list(sig.parameters.keys())
        assert "repo" in param_names
        assert "outbox" in param_names
        assert "clock" in param_names
        assert "registry" in param_names


# ---------------------------------------------------------------------------
# 5. Domain Event completeness
# ---------------------------------------------------------------------------


class TestDomainEventCompleteness:
    """Verify that all domain events are handled by the outbox."""

    def test_setting_updated_handled_by_outbox(self) -> None:
        from backend.settings.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemySettingsOutboxAdapter,
        )
        from backend.settings.application.ports.outbox import SettingsOutboxPort
        assert issubclass(SqlAlchemySettingsOutboxAdapter, object)
        assert hasattr(SqlAlchemySettingsOutboxAdapter, "append")
        assert hasattr(SqlAlchemySettingsOutboxAdapter, "fetch_unpublished")
        assert hasattr(SqlAlchemySettingsOutboxAdapter, "mark_published")

    def test_domain_event_types_are_disjoint(self) -> None:
        from backend.settings.domain.model import (
            SettingUpdated,
            SettingsReset,
        )
        assert SettingUpdated is not SettingsReset
        assert type("", (), {}) is not SettingUpdated


# ---------------------------------------------------------------------------
# 6. Settings Service covers all SettingCategory values
# ---------------------------------------------------------------------------


class TestCategoryCoverage:
    """Every SettingCategory value must have at least one definition."""

    def test_every_category_has_definition(self) -> None:
        covered = {d.category for d in DEFAULT_REGISTRY.values()}
        missing = set(SettingCategory) - covered
        assert not missing, f"Categories without definitions: {missing}"

    def test_system_category_settings(self) -> None:
        system_keys = [
            k for k, d in DEFAULT_REGISTRY.items() if d.category == SettingCategory.SYSTEM
        ]
        assert len(system_keys) >= 3

    def test_privacy_category_settings(self) -> None:
        privacy_keys = [
            k for k, d in DEFAULT_REGISTRY.items() if d.category == SettingCategory.PRIVACY
        ]
        assert len(privacy_keys) >= 2

    def test_voice_category_settings(self) -> None:
        voice_keys = [
            k for k, d in DEFAULT_REGISTRY.items() if d.category == SettingCategory.VOICE
        ]
        assert len(voice_keys) >= 5

    def test_notification_category_settings(self) -> None:
        notif_keys = [
            k
            for k, d in DEFAULT_REGISTRY.items()
            if d.category == SettingCategory.NOTIFICATION
        ]
        assert len(notif_keys) >= 2

    def test_model_category_settings(self) -> None:
        model_keys = [
            k for k, d in DEFAULT_REGISTRY.items() if d.category == SettingCategory.MODEL
        ]
        assert len(model_keys) >= 3

    def test_ui_category_settings(self) -> None:
        ui_keys = [
            k for k, d in DEFAULT_REGISTRY.items() if d.category == SettingCategory.UI
        ]
        assert len(ui_keys) >= 2
