from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from backend.memory.domain.model import (
    ConsentStatus,
    MemoryCategory,
    MemorySource,
    MemoryState,
    RetentionStatus,
)
from backend.memory.domain.rules import (
    MAX_CONTENT_LENGTH,
    VALID_CLASSIFICATIONS,
    VALID_SENSITIVITY_LEVELS,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


# ===================================================================
# Registry audit
# ===================================================================


class TestRegistryAudit:
    def test_memory_category_values(self) -> None:
        expected = {"general", "conversation", "document", "insight", "preference", "ephemeral"}
        actual = {e.value for e in MemoryCategory}
        assert actual == expected

    def test_memory_category_count(self) -> None:
        assert len(MemoryCategory) == 6

    def test_memory_state_values(self) -> None:
        expected = {"created", "updated", "deleted"}
        actual = {e.value for e in MemoryState}
        assert actual == expected

    def test_consent_status_values(self) -> None:
        expected = {"proposed", "active", "revoked", "purged"}
        actual = {e.value for e in ConsentStatus}
        assert actual == expected

    def test_memory_source_values(self) -> None:
        expected = {"user_input", "conversation", "inference", "system", "external"}
        actual = {e.value for e in MemorySource}
        assert actual == expected

    def test_retention_status_values(self) -> None:
        expected = {"active", "expired", "purge_pending", "purged"}
        actual = {e.value for e in RetentionStatus}
        assert actual == expected

    def test_valid_classifications(self) -> None:
        expected = {"public", "internal", "sensitive", "restricted"}
        assert VALID_CLASSIFICATIONS == expected

    def test_valid_sensitivity_levels(self) -> None:
        expected = {"public", "internal", "sensitive", "restricted"}
        assert VALID_SENSITIVITY_LEVELS == expected

    def test_max_content_length(self) -> None:
        assert MAX_CONTENT_LENGTH == 10000


# ===================================================================
# Architecture import verification
# ===================================================================


class TestArchitectureImports:
    DOMAIN_DIR = REPO_ROOT / "backend" / "memory" / "domain"
    PORTS_DIR = REPO_ROOT / "backend" / "memory" / "application" / "ports"
    PERSISTENCE_DIR = REPO_ROOT / "backend" / "memory" / "application" / "persistence"
    USE_CASES_DIR = REPO_ROOT / "backend" / "memory" / "application" / "use_cases"
    ADAPTERS_DIR = REPO_ROOT / "backend" / "memory" / "adapters"
    BOOTSTRAP_FILE = REPO_ROOT / "backend" / "memory" / "bootstrap.py"
    NATS_FILE = REPO_ROOT / "backend" / "memory" / "nats.py"
    API_FILE = REPO_ROOT / "backend" / "api" / "endpoints" / "memory.py"

    ADAPTER_FRAMEWORKS = {"fastapi", "sqlalchemy", "nats", "starlette", "httpx", "alembic"}
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
                if line.startswith("from backend.memory."):
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
        "domain": REPO_ROOT / "backend" / "memory" / "domain",
        "ports": REPO_ROOT / "backend" / "memory" / "application" / "ports",
        "persistence": REPO_ROOT / "backend" / "memory" / "application" / "persistence",
        "use_cases": REPO_ROOT / "backend" / "memory" / "application" / "use_cases",
        "adapters": REPO_ROOT / "backend" / "memory" / "adapters",
        "bootstrap": REPO_ROOT / "backend" / "memory" / "bootstrap.py",
        "nats": REPO_ROOT / "backend" / "memory" / "nats.py",
        "api": REPO_ROOT / "backend" / "api" / "endpoints" / "memory.py",
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
                    if line.startswith("from backend.memory."):
                        parts = line.split(".")[2:4] if "from backend.memory." in line else []
                        if len(parts) >= 2:
                            module = parts[1]
                            if module in upper_layers:
                                pytest.fail(
                                    f"{rel} imports from upper layer '{module}': {line}"
                                )


# ===================================================================
# Coverage metrics
# ===================================================================


class TestCoverageMetrics:
    def test_domain_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_memory_domain.py").exists()

    def test_ports_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_memory_ports.py").exists()

    def test_persistence_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_memory_persistence_contracts.py").exists()

    def test_use_cases_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_memory_use_cases.py").exists()

    def test_adapter_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_memory_adapters.py").exists()

    def test_bootstrap_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_memory_bootstrap.py").exists()

    def test_api_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_memory_api.py").exists()

    def test_nats_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_memory_nats.py").exists()

    def test_integration_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_memory_integration.py").exists()

    def test_repository_integration_test_file_exists(self) -> None:
        assert (REPO_ROOT / "tests" / "test_memory_repository_integration.py").exists()

    def test_all_memory_test_files(self) -> None:
        memory_test_dir = REPO_ROOT / "tests"
        memory_tests = sorted(memory_test_dir.glob("test_memory_*.py"))
        expected = {
            "test_memory_adapters.py",
            "test_memory_api.py",
            "test_memory_bootstrap.py",
            "test_memory_domain.py",
            "test_memory_integration.py",
            "test_memory_nats.py",
            "test_memory_persistence_contracts.py",
            "test_memory_ports.py",
            "test_memory_repository_integration.py",
            "test_memory_use_cases.py",
        }
        actual = {f.name for f in memory_tests}
        missing = expected - actual
        assert not missing, f"Missing test files: {missing}"


# ===================================================================
# Security compliance
# ===================================================================


class TestSecurityCompliance:
    SECRET_PATTERNS = ["password", "token", "api_key", "private_key", "secret", "authorization", "bearer"]

    def test_secret_patterns_defined(self) -> None:
        from backend.memory.domain.rules import SECRET_PATTERNS
        assert len(SECRET_PATTERNS) >= 7

    def test_sensitive_fields_defined(self) -> None:
        from backend.memory.domain.rules import SENSITIVE_FIELDS
        assert "password" in SENSITIVE_FIELDS
        assert "token" in SENSITIVE_FIELDS

    def test_content_security_validated(self) -> None:
        from backend.memory.domain.rules import assert_content_no_secrets
        with pytest.raises(Exception):
            assert_content_no_secrets("my password is 12345")

    def test_empty_content_rejected(self) -> None:
        from backend.memory.domain.rules import assert_content_not_empty
        with pytest.raises(Exception):
            assert_content_not_empty("")

    def test_oversized_content_rejected(self) -> None:
        from backend.memory.domain.rules import assert_content_max_length
        with pytest.raises(Exception):
            assert_content_max_length("x" * 10001, MAX_CONTENT_LENGTH)

    def test_restricted_classification_exists(self) -> None:
        assert "restricted" in VALID_CLASSIFICATIONS

    def test_sensitive_classification_exists(self) -> None:
        assert "sensitive" in VALID_CLASSIFICATIONS
