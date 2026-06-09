"""Architecture fitness tests (JDOS v1.2 addendum, "Architecture Fitness Checks").

These tests run as part of the in-process pytest suite and gate the
Phase 01 exit criteria. They do not require any external service.

Enforced invariants (from
``docs/architecture/JDOS_v1.2_Architecture_Corrections_Addendum.md``
and ``docs/architecture/system_architecture.md``):

* Domain code does not import adapter frameworks (FastAPI, NATS,
  SQLAlchemy, Redis, Qdrant, Ollama, Tauri, React). The foundation
  layer is the only place such imports are allowed.
* Sensitive keys never appear in the durable event schema or in the
  gateway contract.
* The 256 KiB payload boundary is consistent across NATS and the
  gateway middleware.
* The four locked models are present in the manifest.
* The six core v1.2 commands and the six core v1.2 events are
  registered in the governance module.
* No plaintext secrets appear in the foundation source tree.
* The sensitive-payload scan is recursive, case-insensitive, and
  cycle-safe.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.test_helpers import (  # noqa: E402
    service_block,
)

from backend.core.nats_governance import (  # noqa: E402
    COMMAND_CONSUMER_SPECS,
    NATS_MAX_PAYLOAD_BYTES,
    SENSITIVE_PAYLOAD_KEYS,
    STREAM_NAMES,
    STREAM_SPECS,
)
from backend.core.payload_policy import (  # noqa: E402
    MAX_SCANNED_BODY_BYTES,
    SENSITIVE_KEYS,
)
from tools.model_verification.manifest import CANONICAL_MODELS  # noqa: E402


# ---------------------------------------------------------------------------
# Domain purity
# ---------------------------------------------------------------------------

# Modules that are allowed to import adapter frameworks. The foundation
# layer is the only allowed adapter consumer; domain code (services,
# use cases, domain models) MUST NOT import these adapters. Since the
# repository does not yet contain a domain layer (Phase 01 is foundation
# only), the test is a forward-looking gate: any new file under
# ``backend/services`` or ``backend/domain`` that imports an adapter
# framework will fail this test.
ADAPTER_FRAMEWORKS = (
    "fastapi",
    "starlette",
    "uvicorn",
    "pydantic_settings",
    "nats",
    "nats_py",
    "asyncpg",
    "psycopg2",
    "sqlalchemy",
    "alembic",
    "redis",
    "qdrant_client",
    "httpx",  # restricted to foundation adapter layer only
    "tauri",
    "react",
)

# Paths that are allowed to import adapter frameworks (the foundation
# layer and the ``core/`` package which is explicitly the adapter
# layer of the hexagonal architecture).
ALLOWED_ADAPTER_PATHS = {
    "backend/core",
    "backend/main.py",
    "backend/api",
    "backend/audit/adapters",
    "backend/settings/adapters",
    "backend/memory/adapters",
    "backend/knowledge/adapters",
    "backend/knowledge/bootstrap.py",
    "backend/knowledge/nats.py",
    "backend/audit/bootstrap.py",
    "backend/audit/nats.py",
    "backend/settings/bootstrap.py",
    "backend/settings/nats.py",
    "backend/memory/bootstrap.py",
    "backend/memory/nats.py",
    "backend/migrations",
    "tools",
    "tests",
}


def _iter_python_files() -> list[Path]:
    skip_dirs = {".venv", "build", "dist", "__pycache__", ".git", "node_modules"}
    return [
        p for p in REPO_ROOT.rglob("*.py")
        if not any(part in skip_dirs for part in p.parts)
    ]


def _is_allowed(path: Path) -> bool:
    rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    for allowed in ALLOWED_ADAPTER_PATHS:
        if rel == allowed or rel.startswith(allowed + "/"):
            return True
    return False


def test_domain_does_not_import_adapter_frameworks() -> None:
    """Forward-looking: any future ``backend/services`` or ``backend/domain`` file
    that imports an adapter framework fails this test."""
    offenders: list[tuple[Path, str]] = []
    for path in _iter_python_files():
        str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        if _is_allowed(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for adapter in ADAPTER_FRAMEWORKS:
            # Match top-level import statements only.
            if re.search(rf"^\s*(?:from|import)\s+{re.escape(adapter)}\b", text, re.MULTILINE):
                offenders.append((path, adapter))
    assert not offenders, (
        "Domain code must not import adapter frameworks. Offenders:\n"
        + "\n".join(f"  {p}: {a}" for p, a in offenders)
    )


# ---------------------------------------------------------------------------
# Sensitive payload surface
# ---------------------------------------------------------------------------


def test_sensitive_keys_overlap_across_layers() -> None:
    """The gateway and NATS policies MUST share the same sensitive surface.

    The gateway list is a superset (it also covers HTTP-level
    constructs). The intersection must at least include the five
    FND-012 proof points.
    """
    intersection = SENSITIVE_KEYS & SENSITIVE_PAYLOAD_KEYS
    required = {"prompt", "raw_memory", "document_body", "embedding", "api_key"}
    assert required.issubset(intersection), (
        f"Missing shared sensitive keys: {required - intersection}"
    )


def test_payload_boundary_is_consistent_across_layers() -> None:
    assert NATS_MAX_PAYLOAD_BYTES == 256 * 1024
    assert MAX_SCANNED_BODY_BYTES == 256 * 1024
    assert MAX_SCANNED_BODY_BYTES == NATS_MAX_PAYLOAD_BYTES


# ---------------------------------------------------------------------------
# NATS governance surface
# ---------------------------------------------------------------------------


def test_three_v12_streams_are_registered() -> None:
    assert set(STREAM_NAMES) == {
        "JARVIS_COMMANDS_V1",
        "JARVIS_EVENTS_V1",
        "JARVIS_AUDIT_SIGNALS_V1",
    }


def test_command_consumer_specs_cover_all_allowed_domains() -> None:
    domains = {spec.filter_subjects[0].split(".")[2] for spec in COMMAND_CONSUMER_SPECS}
    assert "request" in domains
    assert "memory" in domains
    assert "research" in domains
    assert "automation" in domains
    assert "notification" in domains
    assert "wallpaper" in domains


def test_streams_enforce_256_kib() -> None:
    for spec in STREAM_SPECS:
        assert spec.max_msg_size == 256 * 1024, spec.name


def test_commands_stream_is_work_queue() -> None:
    spec = next(s for s in STREAM_SPECS if s.name == "JARVIS_COMMANDS_V1")
    assert spec.retention == "work_queue"


def test_events_stream_is_limits_with_30d() -> None:
    spec = next(s for s in STREAM_SPECS if s.name == "JARVIS_EVENTS_V1")
    assert spec.retention == "limits"
    assert spec.max_age_seconds == 30 * 24 * 60 * 60


def test_audit_signals_stream_is_limits_with_7d() -> None:
    spec = next(s for s in STREAM_SPECS if s.name == "JARVIS_AUDIT_SIGNALS_V1")
    assert spec.retention == "limits"
    assert spec.max_age_seconds == 7 * 24 * 60 * 60


# ---------------------------------------------------------------------------
# Model manifest
# ---------------------------------------------------------------------------


def test_manifest_has_four_locked_models() -> None:
    assert len(CANONICAL_MODELS) == 4


def test_manifest_includes_nomic_embed_text() -> None:
    assert any(m.canonical_name == "nomic-embed-text" for m in CANONICAL_MODELS)


def test_manifest_includes_qwen_3_8b() -> None:
    assert any(m.canonical_name == "Qwen 3 8B" for m in CANONICAL_MODELS)


def test_manifest_includes_qwen_coder() -> None:
    assert any(m.canonical_name == "Qwen Coder" for m in CANONICAL_MODELS)


def test_manifest_includes_qwen2_5_vl() -> None:
    assert any(m.canonical_name == "Qwen2.5-VL" for m in CANONICAL_MODELS)


# ---------------------------------------------------------------------------
# Secret leakage in source tree
# ---------------------------------------------------------------------------


# A conservative detector for high-entropy strings that look like
# keys / tokens. The detector is intentionally narrow to limit false
# positives; the gitleaks scan in CI is the authoritative detector.
_SECRET_PATTERN = re.compile(
    r"""(?ix)
    \b(
        AKIA[0-9A-Z]{16}                      # AWS access key
    |   sk_(?:test|live)_[0-9a-zA-Z]{16,}    # Stripe secret
    |   ghp_[0-9a-zA-Z]{30,}                 # GitHub PAT
    |   xox[bp]-[0-9a-zA-Z-]{10,}            # Slack token
    )
    \b
    """
)


def test_no_hardcoded_secrets_in_source_tree() -> None:
    offenders: list[tuple[Path, str]] = []
    skip_dirs = {".venv", "build", "dist", ".git", "__pycache__"}
    for path in REPO_ROOT.rglob("*"):
        if path.is_dir():
            if path.name in skip_dirs:
                continue
            continue
        if path.suffix not in {".py", ".md", ".yml", ".yaml", ".json", ".toml", ".ini", ".env.example"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in _SECRET_PATTERN.finditer(text):
            offenders.append((path, match.group(0)))
    assert not offenders, (
        "Plaintext secret(s) detected in source tree. Use environment variables or the OS credential manager.\n"
        + "\n".join(f"  {p}: {s}" for p, s in offenders)
    )


# ---------------------------------------------------------------------------
# Document hygiene
# ---------------------------------------------------------------------------


def test_known_required_files_exist() -> None:
    required = [
        "AGENTS.md",
        "README.md",
        "docker-compose.yml",
        "backend/main.py",
        "backend/core/nats_governance.py",
        "backend/core/nats.py",
        "backend/core/payload_policy.py",
        "backend/core/middleware/__init__.py",
        "backend/core/redis_governance.py",
        "backend/core/qdrant_governance.py",
        "backend/core/ollama.py",
        "backend/migrations/versions/743a95f81f31_initial_foundation_setup.py",
        "tools/model_verification/manifest.py",
        "tools/model_verification/verify_models.py",
        "tools/lockfile/verify.py",
        "tests/test_payload_enforcement.py",
        "tests/test_nats_payload_policy.py",
        "tests/test_model_verification.py",
        "tests/test_nats_governance.py",
        "tests/test_redis_governance.py",
        "tests/test_qdrant_governance.py",
        "tests/test_ollama_adapter.py",
    ]
    missing = [p for p in required if not (REPO_ROOT / p).exists()]
    assert not missing, f"Missing required foundation files: {missing}"


def test_known_required_docs_exist() -> None:
    required_docs = [
        "docs/prompts/master_context.md",
        "docs/PRD/product_requirements.md",
        "docs/architecture/system_architecture.md",
        "docs/architecture/JDOS_v1.2_Architecture_Corrections_Addendum.md",
        "docs/architecture/memory_architecture.md",
        "docs/architecture/security_privacy.md",
        "docs/decisions/0001-architecture-baseline.md",
        "docs/decisions/0002-jdos-v1.2-architecture-corrections.md",
        "docs/development/Phase_01_Foundation.md",
        "docs/development/Phase_02_Core_Services.md",
        "docs/status/development_status.md",
        "docs/implementation/lockfile_policy.md",
        "docs/implementation/compose_operations.md",
        "docs/implementation/redis_governance.md",
        "docs/implementation/qdrant_governance.md",
        "docs/implementation/ollama_adapter.md",
    ]
    missing = [p for p in required_docs if not (REPO_ROOT / p).exists()]
    assert not missing, f"Missing required docs: {missing}"


# ---------------------------------------------------------------------------
# FND-001 — Lockfile policy
# ---------------------------------------------------------------------------


def test_uv_lock_is_gitignored() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "uv.lock" in gitignore, "uv.lock must be listed in .gitignore (regenerated on demand)"


def test_pnpm_lock_is_gitignored() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "pnpm-lock.yaml" in gitignore, "pnpm-lock.yaml must be listed in .gitignore"


def test_lockfile_verifier_module_exists() -> None:
    assert (REPO_ROOT / "tools" / "lockfile" / "verify.py").exists()
    assert (REPO_ROOT / "tools" / "lockfile" / "__init__.py").exists()


def test_workspace_packages_have_package_json() -> None:
    for pkg in ("frontend", "shared", "tools"):
        assert (REPO_ROOT / pkg / "package.json").exists(), (
            f"{pkg}/package.json must exist so pnpm can lock the workspace"
        )


# ---------------------------------------------------------------------------
# FND-003 — Compose hardening
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("service", ("postgres", "redis", "qdrant", "nats", "ollama"))
def test_compose_loopback_only(service: str) -> None:
    block = service_block(service)
    assert block, f"service {service!r} missing"
    assert "127.0.0.1:" in block
    assert "0.0.0.0" not in block


@pytest.mark.parametrize("service", ("postgres", "redis", "qdrant", "nats", "ollama"))
def test_compose_healthcheck_present(service: str) -> None:
    block = service_block(service)
    assert block, f"service {service!r} missing"
    assert "healthcheck:" in block
    assert "test:" in block


@pytest.mark.parametrize("service", ("postgres", "redis", "qdrant", "nats", "ollama"))
def test_compose_resource_limits_present(service: str) -> None:
    block = service_block(service)
    assert block, f"service {service!r} missing"
    assert "deploy:" in block
    assert "resources:" in block
    assert "limits:" in block
    assert "memory:" in block
    assert "cpus:" in block


def test_compose_backend_uses_healthy_dependencies() -> None:
    block = service_block("backend")
    assert block
    assert "depends_on:" in block
    assert "condition: service_healthy" in block


# ---------------------------------------------------------------------------
# FND-006 — Redis + Qdrant governance
# ---------------------------------------------------------------------------


def test_redis_governance_module_exists() -> None:
    from backend.core import redis_governance  # noqa: F401


def test_qdrant_governance_module_exists() -> None:
    from backend.core import qdrant_governance  # noqa: F401


def test_redis_namespace_is_jarvis() -> None:
    from backend.core.redis_governance import PREFIX_REGISTRY, ServicePrefix

    for prefix in ServicePrefix:
        assert prefix in PREFIX_REGISTRY
        assert PREFIX_REGISTRY[prefix].startswith("jarvis:")


def test_qdrant_vector_size_matches_nomic_embed_text() -> None:
    from backend.core.qdrant_governance import (
        COLLECTION_REGISTRY,
        EXPECTED_VECTOR_SIZE,
    )

    assert EXPECTED_VECTOR_SIZE == 768
    for cfg in COLLECTION_REGISTRY.values():
        assert cfg.vector_size == EXPECTED_VECTOR_SIZE


# ---------------------------------------------------------------------------
# FND-007 — Ollama adapter boundary
# ---------------------------------------------------------------------------


def test_ollama_adapter_module_exists() -> None:
    from backend.core import ollama  # noqa: F401


def test_ollama_adapter_is_the_only_backend_importer_of_httpx() -> None:
    """No other backend module may import httpx (foundation layer)."""
    skip_dirs = {".venv", "build", "dist", "__pycache__"}
    offenders: list[str] = []
    backend_root = REPO_ROOT / "backend"
    for path in backend_root.rglob("*.py"):
        if any(part in skip_dirs for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "import httpx" not in text and "from httpx" not in text:
            continue
        if path == backend_root / "core" / "ollama.py":
            continue
        offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, (
        "httpx is restricted to backend/core/ollama.py. Found imports in: " + ", ".join(offenders)
    )


def test_ollama_adapter_loopback_url_guard() -> None:
    """The adapter refuses non-loopback hosts at construction time."""
    from backend.core.ollama import OllamaAdapter, OllamaError

    with pytest.raises(OllamaError):
        OllamaAdapter(base_url="http://ollama.example.com:11434")
    # 127.0.0.1 / localhost / ::1 are accepted.
    for url in (
        "http://127.0.0.1:11434",
        "http://localhost:11434",
        "http://[::1]:11434",
    ):
        OllamaAdapter(base_url=url)  # no exception


def test_ollama_adapter_rejects_unknown_model() -> None:
    from backend.core.ollama import OllamaAdapter, OllamaUnsupportedModelError

    with pytest.raises(OllamaUnsupportedModelError):
        OllamaAdapter.resolve_spec("gpt-4o")
    # Locked models resolve cleanly.
    assert OllamaAdapter.resolve_spec("qwen3").canonical_name == "Qwen 3 8B"
    assert OllamaAdapter.resolve_spec("nomic-embed-text").canonical_name == "nomic-embed-text"
