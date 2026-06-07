"""Tests for the Compose hardening contract (Phase 01, FND-003).

The tests parse ``docker-compose.yml`` as text and YAML and
enforce the non-bypassable policies. They do not require a live
Docker daemon.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = REPO_ROOT / "docker-compose.yml"


pytestmark = pytest.mark.skipif(
    not COMPOSE_PATH.exists(),
    reason="docker-compose.yml missing",
)


def _read_compose_text() -> str:
    return COMPOSE_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Required services + healthchecks
# ---------------------------------------------------------------------------


REQUIRED_SERVICES = ("postgres", "redis", "qdrant", "nats", "ollama")


@pytest.mark.parametrize("service", REQUIRED_SERVICES)
def test_service_declared(service: str) -> None:
    text = _read_compose_text()
    assert f"  {service}:" in text, f"service {service!r} missing from docker-compose.yml"


@pytest.mark.parametrize("service", REQUIRED_SERVICES)
def test_service_has_healthcheck(service: str) -> None:
    text = _read_compose_text()
    # Find the block for the service and check it contains a healthcheck.
    block_start = text.find(f"  {service}:\n")
    assert block_start != -1, f"service {service!r} not declared"
    next_service = text.find("\n  ", block_start + 1)
    block = text[block_start:next_service if next_service != -1 else None]
    assert "healthcheck:" in block, f"service {service!r} missing healthcheck"


# ---------------------------------------------------------------------------
# Loopback binding
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("service", REQUIRED_SERVICES)
def test_service_binds_to_loopback_only(service: str) -> None:
    text = _read_compose_text()
    block_start = text.find(f"  {service}:\n")
    assert block_start != -1
    next_service = text.find("\n  ", block_start + 1)
    block = text[block_start:next_service if next_service != -1 else None]
    assert "127.0.0.1:" in block, (
        f"service {service!r} must bind to loopback (JDOS v1.2 constraint)"
    )
    # No 0.0.0.0 bindings.
    assert "0.0.0.0" not in block, (
        f"service {service!r} must NOT bind to 0.0.0.0"
    )


# ---------------------------------------------------------------------------
# Restart policies
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("service", REQUIRED_SERVICES)
def test_service_has_restart_policy(service: str) -> None:
    text = _read_compose_text()
    block_start = text.find(f"  {service}:\n")
    assert block_start != -1
    next_service = text.find("\n  ", block_start + 1)
    block = text[block_start:next_service if next_service != -1 else None]
    assert "restart: unless-stopped" in block, (
        f"service {service!r} must declare `restart: unless-stopped`"
    )


# ---------------------------------------------------------------------------
# Resource limits
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("service", REQUIRED_SERVICES)
def test_service_has_resource_limits(service: str) -> None:
    text = _read_compose_text()
    block_start = text.find(f"  {service}:\n")
    assert block_start != -1
    next_service = text.find("\n  ", block_start + 1)
    block = text[block_start:next_service if next_service != -1 else None]
    assert "deploy:" in block and "resources:" in block and "limits:" in block, (
        f"service {service!r} must declare resource limits"
    )
    assert "memory:" in block, f"service {service!r} must declare a memory limit"
    assert "cpus:" in block, f"service {service!r} must declare a cpu limit"


# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("service", REQUIRED_SERVICES)
def test_service_has_stop_grace_period(service: str) -> None:
    text = _read_compose_text()
    block_start = text.find(f"  {service}:\n")
    assert block_start != -1
    next_service = text.find("\n  ", block_start + 1)
    block = text[block_start:next_service if next_service != -1 else None]
    assert "stop_grace_period:" in block, (
        f"service {service!r} must declare stop_grace_period for graceful shutdown"
    )


# ---------------------------------------------------------------------------
# Startup ordering
# ---------------------------------------------------------------------------


def test_backend_service_depends_on_healthy_dependencies() -> None:
    text = _read_compose_text()
    assert "  backend:" in text, "backend service must be declared"
    block_start = text.find("  backend:\n")
    next_service = text.find("\n  ", block_start + 1)
    block = text[block_start:next_service if next_service != -1 else None]
    assert "depends_on:" in block
    for dep in ("postgres", "redis", "qdrant", "nats", "ollama"):
        assert f"      {dep}:" in block, (
            f"backend must depend on {dep}"
        )
        # The condition must require the dependency to be healthy.
        assert "condition: service_healthy" in block, (
            f"backend must wait for {dep} to be service_healthy"
        )


# ---------------------------------------------------------------------------
# Volumes
# ---------------------------------------------------------------------------


def test_stateful_services_have_named_volumes() -> None:
    text = _read_compose_text()
    for service in ("postgres", "redis", "qdrant", "nats", "ollama"):
        block_start = text.find(f"  {service}:\n")
        next_service = text.find("\n  ", block_start + 1)
        block = text[block_start:next_service if next_service != -1 else None]
        assert "volumes:" in block, f"service {service!r} must declare a volume"
        # All volume entries bind a named volume (not bind mounts).
        for line in block.splitlines():
            if line.strip().startswith("- "):
                assert ":" in line and not line.strip().endswith(":/"), (
                    f"service {service!r} should mount a named volume, not a root bind mount"
                )


def test_persistent_volumes_declared() -> None:
    text = _read_compose_text()
    assert "volumes:" in text
    for name in ("postgres_data", "redis_data", "qdrant_data", "nats_data", "ollama_data"):
        assert f"  {name}:" in text, f"persistent volume {name!r} must be declared"
