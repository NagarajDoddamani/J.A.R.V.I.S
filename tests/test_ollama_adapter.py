"""Tests for the Ollama adapter (Phase 01, FND-007).

These tests use a mocked ``httpx.AsyncClient`` so the suite is
fully offline. The mocks are injected through the adapter's
``client`` constructor argument to avoid the loopback guard and
keep the tests hermetic.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.ollama import (  # noqa: E402
    DEFAULT_RETRY_ATTEMPTS,
    AvailabilityReport,
    EmbeddingResult,
    GenerationResult,
    HealthReport,
    OllamaAdapter,
    OllamaConnectionError,
    OllamaError,
    OllamaResponseError,
    OllamaUnsupportedModelError,
    VisionResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mock_transport(responses: list[httpx.Response]) -> httpx.MockTransport:
    """Build a transport that returns ``responses`` in order, then echoes."""
    queue = list(responses)
    seen = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["count"] += 1
        if queue:
            return queue.pop(0)
        # Fall back to a generic 200 JSON to avoid blowing up tests that
        # expect the request to be retried.
        return httpx.Response(200, json={"ok": True, "path": request.url.path})

    return httpx.MockTransport(handler)


@pytest.fixture
def adapter_factory() -> type[OllamaAdapter]:
    """Return the adapter class so tests can construct with a mock client."""

    class _Factory(OllamaAdapter):
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            kwargs.setdefault("retry_attempts", 3)
            kwargs.setdefault("retry_base_backoff", 0.0)
            kwargs.setdefault("retry_max_backoff", 0.0)
            super().__init__(*args, **kwargs)

    return _Factory


# ---------------------------------------------------------------------------
# Manifest reconciliation (offline, no HTTP)
# ---------------------------------------------------------------------------


def test_resolve_spec_for_locked_models(adapter_factory: type[OllamaAdapter]) -> None:
    spec = adapter_factory.resolve_spec("qwen3")
    assert spec.canonical_name == "Qwen 3 8B"
    spec = adapter_factory.resolve_spec("qwen-coder")
    assert spec.canonical_name == "Qwen Coder"
    spec = adapter_factory.resolve_spec("qwen2.5-vl")
    assert spec.canonical_name == "Qwen2.5-VL"
    spec = adapter_factory.resolve_spec("nomic-embed-text")
    assert spec.canonical_name == "nomic-embed-text"


def test_resolve_spec_supports_aliases(adapter_factory: type[OllamaAdapter]) -> None:
    spec = adapter_factory.resolve_spec("qwen2.5-coder")
    assert spec.canonical_name == "Qwen Coder"


def test_resolve_spec_rejects_unknown_model(adapter_factory: type[OllamaAdapter]) -> None:
    with pytest.raises(OllamaUnsupportedModelError):
        adapter_factory.resolve_spec("gpt-4o")


def test_approved_models_lists_four_locked(adapter_factory: type[OllamaAdapter]) -> None:
    approved = adapter_factory.approved_models()
    assert set(approved) == {"qwen3", "qwen-coder", "qwen2.5-vl", "nomic-embed-text"}


def test_is_approved(adapter_factory: type[OllamaAdapter]) -> None:
    assert adapter_factory.is_approved("qwen3")
    assert adapter_factory.is_approved("qwen2.5-coder")
    assert not adapter_factory.is_approved("gpt-4o")


# ---------------------------------------------------------------------------
# Loopback URL guard
# ---------------------------------------------------------------------------


def test_loopback_url_guard_accepts_loopback(adapter_factory: type[OllamaAdapter]) -> None:
    for url in (
        "http://127.0.0.1:11434",
        "http://localhost:11434",
        "http://[::1]:11434",
    ):
        adapter = adapter_factory(base_url=url)
        assert adapter._base_url == url.rstrip("/")  # noqa: SLF001


def test_loopback_url_guard_rejects_external(adapter_factory: type[OllamaAdapter]) -> None:
    with pytest.raises(OllamaError):
        adapter_factory(base_url="http://ollama.example.com:11434")
    with pytest.raises(OllamaError):
        adapter_factory(base_url="http://10.0.0.5:11434")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_ok(adapter_factory: type[OllamaAdapter]) -> None:
    transport = _mock_transport([
        httpx.Response(200, json={"version": "0.3.12"}),
        httpx.Response(200, json={"models": [{"name": "qwen3:8b"}, {"name": "nomic-embed-text:latest"}]}),
    ])
    client = httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=transport)
    adapter = adapter_factory(client=client)
    report = await adapter.health()
    assert isinstance(report, HealthReport)
    assert report.reachable is True
    assert report.version == "0.3.12"
    assert "qwen3:8b" in report.models
    assert "nomic-embed-text:latest" in report.models
    await adapter.aclose()


@pytest.mark.asyncio
async def test_health_unreachable(adapter_factory: type[OllamaAdapter]) -> None:
    transport = _mock_transport([])

    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=transport)
    adapter = adapter_factory(client=client, retry_attempts=2)
    with pytest.raises(OllamaConnectionError):
        await adapter.health()
    await adapter.aclose()


@pytest.mark.asyncio
async def test_health_5xx_retries(adapter_factory: type[OllamaAdapter]) -> None:
    transport = _mock_transport([
        httpx.Response(503, text="busy"),
        httpx.Response(503, text="busy"),
        httpx.Response(200, json={"version": "0.3.12"}),
        httpx.Response(200, json={"models": []}),
    ])
    client = httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=transport)
    adapter = adapter_factory(client=client)
    report = await adapter.health()
    assert report.reachable is True
    await adapter.aclose()


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_availability_installed(adapter_factory: type[OllamaAdapter]) -> None:
    transport = _mock_transport([
        httpx.Response(200, json={"version": "0.3.12"}),
        httpx.Response(200, json={"models": [{"name": "qwen3:8b"}]}),
    ])
    client = httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=transport)
    adapter = adapter_factory(client=client)
    report = await adapter.availability("qwen3")
    assert isinstance(report, AvailabilityReport)
    assert report.installed is True
    assert report.alias_used == "qwen3:8b"
    await adapter.aclose()


@pytest.mark.asyncio
async def test_availability_missing(adapter_factory: type[OllamaAdapter]) -> None:
    transport = _mock_transport([
        httpx.Response(200, json={"version": "0.3.12"}),
        httpx.Response(200, json={"models": []}),
    ])
    client = httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=transport)
    adapter = adapter_factory(client=client)
    report = await adapter.availability("qwen3")
    assert report.installed is False
    await adapter.aclose()


# ---------------------------------------------------------------------------
# Embed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_happy_path(adapter_factory: type[OllamaAdapter]) -> None:
    transport = _mock_transport([
        httpx.Response(
            200,
            json={"embedding": [0.1, 0.2, 0.3], "prompt_eval_count": 4},
        )
    ])
    client = httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=transport)
    adapter = adapter_factory(client=client)
    result = await adapter.embed("nomic-embed-text", "hello world")
    assert isinstance(result, EmbeddingResult)
    assert result.model == "nomic-embed-text"
    assert result.embedding == (0.1, 0.2, 0.3)
    assert result.prompt_tokens == 4
    await adapter.aclose()


@pytest.mark.asyncio
async def test_embed_rejects_non_embedding_model(adapter_factory: type[OllamaAdapter]) -> None:
    client = httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=_mock_transport([]))
    adapter = adapter_factory(client=client)
    # generate is called on an embedding model
    with pytest.raises(OllamaUnsupportedModelError):
        await adapter.generate("nomic-embed-text", "hello", max_tokens=4)


@pytest.mark.asyncio
async def test_embed_404(adapter_factory: type[OllamaAdapter]) -> None:
    transport = _mock_transport([httpx.Response(404, json={"error": "model not found"})])
    client = httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=transport)
    adapter = adapter_factory(client=client)
    with pytest.raises(OllamaUnsupportedModelError):
        await adapter.embed("nomic-embed-text", "hi")
    await adapter.aclose()


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_happy_path(adapter_factory: type[OllamaAdapter]) -> None:
    transport = _mock_transport([
        httpx.Response(
            200,
            json={"response": "OK", "eval_count": 1, "total_duration": 12345},
        )
    ])
    client = httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=transport)
    adapter = adapter_factory(client=client)
    result = await adapter.generate("qwen3", "Reply OK.", max_tokens=4)
    assert isinstance(result, GenerationResult)
    assert result.model == "qwen3"
    assert result.response == "OK"
    assert result.eval_tokens == 1
    await adapter.aclose()


@pytest.mark.asyncio
async def test_generate_400_raises(adapter_factory: type[OllamaAdapter]) -> None:
    transport = _mock_transport([httpx.Response(400, text="bad")])
    client = httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=transport)
    adapter = adapter_factory(client=client)
    with pytest.raises(OllamaResponseError):
        await adapter.generate("qwen3", "x", max_tokens=4)
    await adapter.aclose()


# ---------------------------------------------------------------------------
# Vision
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_describe_happy_path(adapter_factory: type[OllamaAdapter]) -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        captured["model"] = body.get("model", "")
        captured["images_len"] = str(len(body.get("images", [])))
        return httpx.Response(
            200,
            json={"response": "a small image", "eval_count": 7},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=transport)
    adapter = adapter_factory(client=client)
    result = await adapter.describe("qwen2.5-vl", b"\x89PNG\r\n\x1a\n")
    assert isinstance(result, VisionResult)
    assert result.model == "qwen2.5-vl"
    assert result.response == "a small image"
    assert result.eval_tokens == 7
    assert captured["model"] == "qwen2.5-vl"
    assert captured["images_len"] == "1"
    await adapter.aclose()


@pytest.mark.asyncio
async def test_describe_rejects_empty_image(adapter_factory: type[OllamaAdapter]) -> None:
    client = httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=_mock_transport([]))
    adapter = adapter_factory(client=client)
    with pytest.raises(OllamaError):
        await adapter.describe("qwen2.5-vl", b"")
    await adapter.aclose()


# ---------------------------------------------------------------------------
# Retry behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_then_success(adapter_factory: type[OllamaAdapter]) -> None:
    """Two transient connect errors, then a success."""
    attempts = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise httpx.ConnectError("busy")
        return httpx.Response(
            200,
            json={"embedding": [0.0, 0.0, 0.0], "prompt_eval_count": 1},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=transport)
    adapter = adapter_factory(client=client, retry_attempts=3)
    result = await adapter.embed("nomic-embed-text", "hi")
    assert result.embedding == (0.0, 0.0, 0.0)
    assert attempts["n"] == 3
    await adapter.aclose()


@pytest.mark.asyncio
async def test_retry_exhausted(adapter_factory: type[OllamaAdapter]) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("never")

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=transport)
    adapter = adapter_factory(client=client, retry_attempts=2)
    with pytest.raises(OllamaConnectionError):
        await adapter.embed("nomic-embed-text", "hi")
    await adapter.aclose()


# ---------------------------------------------------------------------------
# Lazy client / close
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lazy_client_creation(adapter_factory: type[OllamaAdapter]) -> None:
    adapter = adapter_factory()
    assert adapter._client is None  # noqa: SLF001
    client = await adapter._get_client()  # noqa: SLF001
    assert isinstance(client, httpx.AsyncClient)
    await adapter.aclose()
    assert adapter._client is None  # noqa: SLF001


@pytest.mark.asyncio
async def test_default_retry_attempts_is_three() -> None:
    assert DEFAULT_RETRY_ATTEMPTS == 3
    # Spin a quick event loop to ensure nothing is created on import.
    await asyncio.sleep(0)
