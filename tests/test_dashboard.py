from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from backend.cli.dashboard import (
    ServiceStatus,
    _probe_api_service,
    check_backend,
    check_nats,
    check_qdrant,
    poll_all,
)

# ---------------------------------------------------------------------------
# Probe-level resilience
# ---------------------------------------------------------------------------


class TestProbeResilience:
    """Every probe must catch BaseException and return a graceful failure."""

    @pytest.mark.parametrize("exc_cls", [TimeoutError, ConnectionError, asyncio.CancelledError, RuntimeError, OSError])
    async def test_nats_catches_all_exceptions(self, exc_cls) -> None:
        """NATS probe catches TimeoutError, CancelledError, etc."""
        with patch("backend.cli.dashboard.nats_connect", side_effect=exc_cls("test")):
            result = await check_nats()
        assert result.connected is False
        assert result.latency_ms is None
        assert result.error != ""

    @pytest.mark.parametrize("exc_cls", [TimeoutError, ConnectionError, asyncio.CancelledError, RuntimeError])
    async def test_qdrant_catches_all_exceptions(self, exc_cls) -> None:
        """Qdrant probe catches CancelledError and others."""
        mock_client = AsyncMock()
        mock_client.get_collections = AsyncMock(side_effect=exc_cls("test"))
        with patch("backend.cli.dashboard.AsyncQdrantClient", return_value=mock_client):
            result = await check_qdrant()
        assert result.connected is False
        assert result.latency_ms is None
        assert result.error != ""

    @pytest.mark.parametrize("exc_cls", [TimeoutError, ConnectionError, asyncio.CancelledError, RuntimeError])
    async def test_backend_catches_all_exceptions(self, exc_cls) -> None:
        """Backend probe catches CancelledError and others."""
        async def _raise(*args, **kwargs):
            raise exc_cls("test")

        with patch("httpx.AsyncClient.get", _raise):
            result = await check_backend()
        assert result.connected is False
        assert result.latency_ms is None
        assert result.error != ""

    @pytest.mark.parametrize("exc_cls", [TimeoutError, ConnectionError, asyncio.CancelledError, RuntimeError])
    async def test_app_service_probe_catches_all_exceptions(self, exc_cls) -> None:
        """Application service probe catches CancelledError and others."""
        async def _raise(*args, **kwargs):
            raise exc_cls("test")

        with patch("httpx.AsyncClient.get", _raise):
            result = await _probe_api_service("TestService", "/api/v1/test")
        assert result.connected is False
        assert result.latency_ms is None
        assert result.error != ""


# ---------------------------------------------------------------------------
# poll_all resilience
# ---------------------------------------------------------------------------


class TestPollAllResilience:
    """poll_all() must never raise; it must return partial results."""

    async def test_all_probes_fail_still_returns_results(self) -> None:
        """Even if every probe fails, poll_all returns a dict with error info."""
        with (
            patch("backend.cli.dashboard.check_postgres", return_value=ServiceStatus("PostgreSQL", error="fail")),
            patch("backend.cli.dashboard.check_redis", return_value=ServiceStatus("Redis", error="fail")),
            patch("backend.cli.dashboard.check_nats", return_value=ServiceStatus("NATS", error="fail")),
            patch("backend.cli.dashboard.check_qdrant", return_value=ServiceStatus("Qdrant", error="fail")),
            patch("backend.cli.dashboard.check_ollama", return_value=ServiceStatus("Ollama", error="fail")),
            patch("backend.cli.dashboard.check_backend", return_value=ServiceStatus("Runtime", error="fail")),
        ):
            results = await poll_all()

        assert isinstance(results, dict)
        assert len(results) >= 5
        assert results["PostgreSQL"].error == "fail"
        assert results["Runtime"].error == "fail"

    async def test_poll_all_handles_exception_from_probe(self) -> None:
        """If a probe raises instead of returning a ServiceStatus, poll_all captures it."""
        with (
            patch("backend.cli.dashboard.check_postgres", side_effect=RuntimeError("boom")),
            patch("backend.cli.dashboard.check_redis", return_value=ServiceStatus("Redis", connected=True)),
            patch("backend.cli.dashboard.check_nats", return_value=ServiceStatus("NATS", connected=True)),
            patch("backend.cli.dashboard.check_qdrant", return_value=ServiceStatus("Qdrant", connected=True)),
            patch("backend.cli.dashboard.check_ollama", return_value=ServiceStatus("Ollama", connected=True)),
            patch("backend.cli.dashboard.check_backend", return_value=ServiceStatus("Runtime", connected=True)),
        ):
            results = await poll_all()

        # Should not crash; should return partial results
        assert "Redis" in results
        assert results["Redis"].connected is True

    async def test_partial_failure_still_returns_successful_probes(self) -> None:
        """When one probe fails, successful probes are still returned."""
        with (
            patch("backend.cli.dashboard.check_postgres", return_value=ServiceStatus("PostgreSQL", connected=True)),
            patch("backend.cli.dashboard.check_redis", return_value=ServiceStatus("Redis", connected=True)),
            patch("backend.cli.dashboard.check_nats", return_value=ServiceStatus("NATS", error="NATS timeout")),
            patch("backend.cli.dashboard.check_qdrant", return_value=ServiceStatus("Qdrant", error="Qdrant timeout")),
            patch("backend.cli.dashboard.check_ollama", return_value=ServiceStatus("Ollama", connected=True)),
            patch("backend.cli.dashboard.check_backend", return_value=ServiceStatus("Runtime", connected=True)),
            patch("backend.cli.dashboard._probe_api_service", return_value=ServiceStatus("Memory", connected=True)),
        ):
            results = await poll_all()

        assert results["PostgreSQL"].connected is True
        assert results["Redis"].connected is True
        assert results["NATS"].connected is False
        assert results["NATS"].error == "NATS timeout"
        assert results["Qdrant"].connected is False
        assert results["Ollama"].connected is True

    async def test_runtime_offline_shows_app_services_offline(self) -> None:
        """When backend is unreachable, app services show 'Runtime offline'."""
        with (
            patch("backend.cli.dashboard.check_postgres", return_value=ServiceStatus("PostgreSQL", connected=True)),
            patch("backend.cli.dashboard.check_redis", return_value=ServiceStatus("Redis", connected=True)),
            patch("backend.cli.dashboard.check_nats", return_value=ServiceStatus("NATS", connected=True)),
            patch("backend.cli.dashboard.check_qdrant", return_value=ServiceStatus("Qdrant", connected=True)),
            patch("backend.cli.dashboard.check_ollama", return_value=ServiceStatus("Ollama", connected=True)),
            patch("backend.cli.dashboard.check_backend", return_value=ServiceStatus("Runtime", error="Backend down")),
        ):
            results = await poll_all()

        assert results["Runtime"].connected is False
        # Memory should exist even if runtime is down, with "Runtime offline" error
        memory = results.get("Memory")
        assert memory is not None
        assert memory.connected is False
        assert memory.error == "Runtime offline"

    async def test_runtime_healthy_probes_app_services(self) -> None:
        """When backend is healthy, app services are probed individually."""
        with (
            patch("backend.cli.dashboard.check_postgres", return_value=ServiceStatus("PostgreSQL", connected=True)),
            patch("backend.cli.dashboard.check_redis", return_value=ServiceStatus("Redis", connected=True)),
            patch("backend.cli.dashboard.check_nats", return_value=ServiceStatus("NATS", connected=True)),
            patch("backend.cli.dashboard.check_qdrant", return_value=ServiceStatus("Qdrant", connected=True)),
            patch("backend.cli.dashboard.check_ollama", return_value=ServiceStatus("Ollama", connected=True)),
            patch("backend.cli.dashboard.check_backend", return_value=ServiceStatus("Runtime", connected=True)),
            patch(
                "backend.cli.dashboard._probe_api_service",
                side_effect=lambda name, path: ServiceStatus(name, group="app", connected=True),
            ),
        ):
            results = await poll_all()

        assert results["Runtime"].connected is True
        assert results["Memory"].connected is True
        assert results["Knowledge"].connected is True
        assert results["Planner"].connected is True


# ---------------------------------------------------------------------------
# ServiceStatus contract
# ---------------------------------------------------------------------------


class TestServiceStatusContract:
    """Failed probes must return connected=False, latency=None, error."""

    def test_defaults(self) -> None:
        s = ServiceStatus("test")
        assert s.connected is False
        assert s.latency_ms is None
        assert s.error == ""

    def test_failure_shape(self) -> None:
        """A failed probe must set connected=False, latency=None, error."""
        s = ServiceStatus("test", error="something went wrong")
        assert s.connected is False
        assert s.latency_ms is None
        assert s.error == "something went wrong"

    def test_success_shape(self) -> None:
        """A successful probe must set connected=True and latency."""
        s = ServiceStatus("test", connected=True, latency_ms=42.0)
        assert s.connected is True
        assert s.latency_ms == 42.0
        assert s.error == ""


# ---------------------------------------------------------------------------
# asyncio.gather return_exceptions=True enforcement
# ---------------------------------------------------------------------------


class TestGatherReturnExceptions:
    """asyncio.gather must use return_exceptions=True so one failure
    does not prevent other results from being collected."""

    async def test_gather_with_exceptions(self) -> None:
        """Verify that gather with return_exceptions=True collects both
        successes and exceptions."""

        async def ok():
            return ServiceStatus("ok", connected=True)

        async def fail():
            raise RuntimeError("probe failure")

        results = await asyncio.gather(ok(), fail(), return_exceptions=True)
        successes = [r for r in results if isinstance(r, ServiceStatus)]
        exceptions = [r for r in results if isinstance(r, BaseException)]
        assert len(successes) == 1
        assert len(exceptions) == 1
        assert isinstance(exceptions[0], RuntimeError)

    async def test_gather_without_exceptions_raises(self) -> None:
        """Without return_exceptions, a single failure crashes the gather."""

        async def ok():
            return ServiceStatus("ok", connected=True)

        async def fail():
            raise RuntimeError("probe failure")

        with pytest.raises(RuntimeError, match="probe failure"):
            await asyncio.gather(ok(), fail(), return_exceptions=False)
