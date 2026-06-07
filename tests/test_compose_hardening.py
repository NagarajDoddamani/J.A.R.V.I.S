"""Tests for the Compose hardening contract (Phase 01, FND-003).

The tests parse ``docker-compose.yml`` via a shared YAML-block
helper and enforce the non-bypassable policies. They do not
require a live Docker daemon.
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

from tests.test_helpers import (  # noqa: E402  # isort:skip
    service_block,
    compose_text,
)


# ---------------------------------------------------------------------------
# Required services + healthchecks
# ---------------------------------------------------------------------------


REQUIRED_SERVICES = ("postgres", "redis", "qdrant", "nats", "ollama")


@pytest.mark.parametrize("service", REQUIRED_SERVICES)
def test_service_declared(service: str) -> None:
    assert service_block(service), f"service {service!r} missing from docker-compose.yml"


@pytest.mark.parametrize("service", REQUIRED_SERVICES)
def test_service_has_healthcheck(service: str) -> None:
    block = service_block(service)
    assert block, f"service {service!r} not declared"
    assert "healthcheck:" in block, f"service {service!r} missing healthcheck"
    assert "test:" in block


# ---------------------------------------------------------------------------
# Loopback binding
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("service", REQUIRED_SERVICES)
def test_service_binds_to_loopback_only(service: str) -> None:
    block = service_block(service)
    assert block
    assert "127.0.0.1:" in block, (
        f"service {service!r} must bind to loopback (JDOS v1.2 constraint)"
    )
    assert "0.0.0.0" not in block, (
        f"service {service!r} must NOT bind to 0.0.0.0"
    )


# ---------------------------------------------------------------------------
# Restart policies
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("service", REQUIRED_SERVICES)
def test_service_has_restart_policy(service: str) -> None:
    block = service_block(service)
    assert block
    assert "restart: unless-stopped" in block, (
        f"service {service!r} must declare `restart: unless-stopped`"
    )


# ---------------------------------------------------------------------------
# Resource limits
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("service", REQUIRED_SERVICES)
def test_service_has_resource_limits(service: str) -> None:
    block = service_block(service)
    assert block
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
    block = service_block(service)
    assert block
    assert "stop_grace_period:" in block, (
        f"service {service!r} must declare stop_grace_period for graceful shutdown"
    )


# ---------------------------------------------------------------------------
# Startup ordering
# ---------------------------------------------------------------------------


def test_backend_service_depends_on_healthy_dependencies() -> None:
    block = service_block("backend")
    assert block, "backend service must be declared"
    assert "depends_on:" in block
    for dep in ("postgres", "redis", "qdrant", "nats", "ollama"):
        assert f"      {dep}:" in block, (
            f"backend must depend on {dep}"
        )
        assert "condition: service_healthy" in block, (
            f"backend must wait for {dep} to be service_healthy"
        )


# ---------------------------------------------------------------------------
# Volumes
# ---------------------------------------------------------------------------


def test_stateful_services_have_named_volumes() -> None:
    for service in REQUIRED_SERVICES:
        block = service_block(service)
        assert block, f"service {service!r} not declared"
        assert "volumes:" in block, f"service {service!r} must declare a volume"
        in_volumes = False
        for line in block.splitlines():
            stripped = line.strip()
            if stripped == "volumes:":
                in_volumes = True
                continue
            if in_volumes and stripped.startswith("- "):
                assert not stripped.endswith(":/"), (
                    f"service {service!r} should mount a named volume, not a root bind mount"
                )
            elif in_volumes and stripped and not stripped.startswith("- ") and not stripped.startswith("#"):
                in_volumes = False


def test_persistent_volumes_declared() -> None:
    text = compose_text()
    assert "volumes:" in text
    for name in ("postgres_data", "redis_data", "qdrant_data", "nats_data", "ollama_data"):
        assert f"  {name}:" in text, f"persistent volume {name!r} must be declared"
