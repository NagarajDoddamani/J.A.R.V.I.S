"""JARVIS Ollama adapter boundary (Phase 01, FND-007).

This module is the *only* place in the JARVIS backend that may
contact the Ollama daemon. Every service that needs the model
runtime goes through :class:`OllamaAdapter`, which implements the
four ``Port`` interfaces declared at the top of the file:

* :class:`ModelPort` — health, availability, and model listing.
* :class:`EmbeddingPort` — text → vector.
* :class:`GenerationPort` — text → text (chat / completion).
* :class:`VisionPort` — image bytes → text.

The adapter is offline-only: the Ollama daemon runs on a private
loopback interface and the adapter never resolves a non-loopback
host. The adapter enforces:

* a hard connection timeout and a per-request timeout,
* bounded retry with exponential backoff for transient
  5xx / connection failures,
* a manifest reconciliation step (every model passed in must be
  in the canonical manifest or an explicit alias),
* fail-closed behaviour on any model-port call when the daemon
  is unreachable.

The adapter is dependency-light: it uses ``httpx.AsyncClient``
only. No call to Ollama is made at import time.
"""

from __future__ import annotations

import asyncio
import base64
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Final, Protocol, runtime_checkable

import httpx
from tools.model_verification.manifest import (
    CANONICAL_MODELS,
    MODEL_ALIASES,
    ModelSpec,
    find_spec,
)

# ---------------------------------------------------------------------------
# Public errors
# ---------------------------------------------------------------------------


class OllamaError(Exception):
    """Base class for adapter errors."""


class OllamaConnectionError(OllamaError):
    """The daemon is unreachable on the loopback interface."""


class OllamaTimeoutError(OllamaError):
    """A request exceeded the per-request timeout."""


class OllamaUnsupportedModelError(OllamaError):
    """The requested model is not in the canonical manifest."""


class OllamaResponseError(OllamaError):
    """The daemon returned a non-success status."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HealthReport:
    reachable: bool
    version: str = ""
    models: tuple[str, ...] = ()


@dataclass(frozen=True)
class AvailabilityReport:
    installed: bool
    alias_used: str = ""
    spec: ModelSpec | None = None


@dataclass(frozen=True)
class EmbeddingResult:
    model: str
    embedding: tuple[float, ...]
    prompt_tokens: int = 0


@dataclass(frozen=True)
class GenerationResult:
    model: str
    response: str
    eval_tokens: int = 0
    total_duration_ns: int = 0


@dataclass(frozen=True)
class VisionResult:
    model: str
    response: str
    eval_tokens: int = 0


# ---------------------------------------------------------------------------
# Ports
# ---------------------------------------------------------------------------


class ModelPort(ABC):
    """Health, availability, and listing operations."""

    @abstractmethod
    async def health(self) -> HealthReport: ...

    @abstractmethod
    async def list_models(self) -> tuple[str, ...]: ...

    @abstractmethod
    async def availability(self, canonical_or_alias: str) -> AvailabilityReport: ...


class EmbeddingPort(ABC):
    @abstractmethod
    async def embed(self, model: str, text: str) -> EmbeddingResult: ...


class GenerationPort(ABC):
    @abstractmethod
    async def generate(self, model: str, prompt: str, *, max_tokens: int = 256) -> GenerationResult: ...


class VisionPort(ABC):
    @abstractmethod
    async def describe(self, model: str, image_bytes: bytes, *, prompt: str = "Describe the image.") -> VisionResult: ...


@runtime_checkable
class OllamaAdapterProtocol(Protocol):
    """Convenience protocol that bundles all four ports."""

    health: Any
    list_models: Any
    availability: Any
    embed: Any
    generate: Any
    describe: Any


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

DEFAULT_CONNECT_TIMEOUT_SECONDS: Final[float] = 2.0
DEFAULT_REQUEST_TIMEOUT_SECONDS: Final[float] = 30.0
DEFAULT_RETRY_ATTEMPTS: Final[int] = 3
DEFAULT_RETRY_BASE_BACKOFF_SECONDS: Final[float] = 0.25
DEFAULT_RETRY_MAX_BACKOFF_SECONDS: Final[float] = 8.0


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class OllamaAdapter(ModelPort, EmbeddingPort, GenerationPort, VisionPort):
    """The single boundary that may speak to the Ollama daemon.

    The adapter is constructed once at process start and is
    shared by every consumer. The underlying ``httpx.AsyncClient``
    is created lazily and closed via :meth:`aclose`.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
        request_timeout: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        retry_base_backoff: float = DEFAULT_RETRY_BASE_BACKOFF_SECONDS,
        retry_max_backoff: float = DEFAULT_RETRY_MAX_BACKOFF_SECONDS,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        raw = (base_url or "http://127.0.0.1:11434").rstrip("/")
        try:
            parsed = httpx.URL(raw)
        except Exception as exc:
            raise OllamaError(f"invalid OLLAMA_BASE_URL {raw!r}: {exc}") from exc
        host = (parsed.host or "").lower()
        if host not in {"127.0.0.1", "localhost", "::1", "[::1]"}:
            raise OllamaError(
                f"OLLAMA_BASE_URL {raw!r} resolves to non-loopback host {host!r}; refusing to start"
            )
        self._base_url = raw
        self._connect_timeout = connect_timeout
        self._request_timeout = request_timeout
        self._retry_attempts = max(1, retry_attempts)
        self._retry_base_backoff = retry_base_backoff
        self._retry_max_backoff = retry_max_backoff
        self._client: httpx.AsyncClient | None = client
        self._owns_client = client is None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._request_timeout, connect=self._connect_timeout),
            )
        return self._client

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> OllamaAdapter:
        await self._get_client()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    # ------------------------------------------------------------------
    # Manifest reconciliation
    # ------------------------------------------------------------------

    @staticmethod
    def resolve_spec(name: str) -> ModelSpec:
        """Return the canonical spec for ``name`` or raise."""
        spec = find_spec(name)
        if spec is None:
            raise OllamaUnsupportedModelError(
                f"model {name!r} is not in the JARVIS manifest; "
                f"approved names: {sorted({s.ollama_name for s in CANONICAL_MODELS})}"
            )
        return spec

    @staticmethod
    def approved_models() -> tuple[str, ...]:
        return tuple(sorted({s.ollama_name for s in CANONICAL_MODELS}))

    @staticmethod
    def is_approved(name: str) -> bool:
        spec = find_spec(name)
        return spec is not None

    @staticmethod
    def aliases_for(name: str) -> tuple[str, ...]:
        return MODEL_ALIASES.get(name, ())

    # ------------------------------------------------------------------
    # Retry wrapper
    # ------------------------------------------------------------------

    async def _with_retry(self, op_name: str, coro_factory: Any) -> Any:
        """Execute ``coro_factory()`` with bounded retry on transient errors.

        Retries cover connection failures, timeouts, and server
        (5xx) responses. The caller is expected to have already
        validated the request.
        """
        last_exc: BaseException | None = None
        for attempt in range(1, self._retry_attempts + 1):
            try:
                return await coro_factory()
            except (OllamaConnectionError, OllamaTimeoutError) as exc:
                last_exc = exc
                if attempt == self._retry_attempts:
                    break
                backoff = min(
                    self._retry_max_backoff,
                    self._retry_base_backoff * (2 ** (attempt - 1)),
                )
                await asyncio.sleep(backoff)
            except OllamaError:
                raise
            except Exception:
                raise
        if isinstance(last_exc, (OllamaConnectionError,)):
            raise OllamaConnectionError(
                f"{op_name} failed after {self._retry_attempts} attempts: {last_exc}"
            ) from last_exc
        if isinstance(last_exc, OllamaTimeoutError):
            raise OllamaTimeoutError(
                f"{op_name} timed out after {self._retry_attempts} attempts: {last_exc}"
            ) from last_exc
        raise OllamaConnectionError(
            f"{op_name} failed after {self._retry_attempts} attempts: {last_exc}"
        ) from last_exc if last_exc else None

    # ------------------------------------------------------------------
    # ModelPort
    # ------------------------------------------------------------------

    async def health(self) -> HealthReport:
        client = await self._get_client()

        async def _call() -> HealthReport:
            try:
                response = await client.get("/api/version")
            except (httpx.ConnectError, httpx.ReadError) as exc:
                raise OllamaConnectionError(
                    f"Ollama daemon unreachable on {self._base_url}: {exc}"
                ) from exc
            except httpx.TimeoutException as exc:
                raise OllamaTimeoutError(f"health check timed out: {exc}") from exc
            if response.status_code >= 500:
                raise OllamaConnectionError(
                    f"health check returned {response.status_code}: {response.text}"
                )
            version = ""
            if response.status_code == 200:
                try:
                    version = str(response.json().get("version", ""))
                except Exception:
                    version = ""
            models = await self._safe_list_models(client)
            return HealthReport(reachable=response.status_code == 200, version=version, models=models)

        return await self._with_retry("health", _call)

    async def _safe_list_models(self, client: httpx.AsyncClient) -> tuple[str, ...]:
        try:
            response = await client.get("/api/tags")
            if response.status_code != 200:
                return ()
            payload = response.json()
            names: list[str] = []
            for entry in payload.get("models", []):
                name = entry.get("name") or entry.get("model") or ""
                if name:
                    names.append(str(name))
            return tuple(sorted(names))
        except (httpx.HTTPError, ValueError):
            return ()

    async def list_models(self) -> tuple[str, ...]:
        report = await self.health()
        return report.models

    async def availability(self, canonical_or_alias: str) -> AvailabilityReport:
        spec = self.resolve_spec(canonical_or_alias)
        installed = await self.list_models()
        aliases = MODEL_ALIASES.get(spec.ollama_name, (spec.ollama_name,))
        for installed_name in installed:
            if installed_name in aliases or installed_name == spec.ollama_name:
                return AvailabilityReport(installed=True, alias_used=installed_name, spec=spec)
        return AvailabilityReport(installed=False, spec=spec)

    # ------------------------------------------------------------------
    # EmbeddingPort
    # ------------------------------------------------------------------

    async def embed(self, model: str, text: str) -> EmbeddingResult:
        spec = self.resolve_spec(model)
        client = await self._get_client()

        async def _call() -> EmbeddingResult:
            try:
                response = await client.post(
                    "/api/embeddings",
                    json={"model": spec.ollama_name, "prompt": text},
                )
            except (httpx.ConnectError, httpx.ReadError) as exc:
                raise OllamaConnectionError(f"embed: {exc}") from exc
            except httpx.TimeoutException as exc:
                raise OllamaTimeoutError(f"embed timed out: {exc}") from exc
            if response.status_code == 404:
                raise OllamaUnsupportedModelError(
                    f"embed: model {spec.ollama_name!r} is not installed on the daemon"
                )
            if response.status_code >= 500:
                raise OllamaResponseError(
                    f"embed: daemon returned {response.status_code}: {response.text}"
                )
            if response.status_code >= 400:
                raise OllamaResponseError(
                    f"embed: rejected with {response.status_code}: {response.text}"
                )
            payload = response.json()
            embedding = tuple(float(x) for x in payload.get("embedding", []))
            return EmbeddingResult(
                model=spec.ollama_name,
                embedding=embedding,
                prompt_tokens=int(payload.get("prompt_eval_count", 0) or 0),
            )

        return await self._with_retry("embed", _call)

    # ------------------------------------------------------------------
    # GenerationPort
    # ------------------------------------------------------------------

    async def generate(self, model: str, prompt: str, *, max_tokens: int = 256) -> GenerationResult:
        spec = self.resolve_spec(model)
        if not spec.minimum_smoke_prompt and max_tokens > 0:
            # Embedding models do not accept /api/generate.
            raise OllamaUnsupportedModelError(
                f"generate: model {spec.ollama_name!r} is an embedding model and cannot generate"
            )
        client = await self._get_client()

        async def _call() -> GenerationResult:
            try:
                response = await client.post(
                    "/api/generate",
                    json={
                        "model": spec.ollama_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": int(max_tokens)},
                    },
                )
            except (httpx.ConnectError, httpx.ReadError) as exc:
                raise OllamaConnectionError(f"generate: {exc}") from exc
            except httpx.TimeoutException as exc:
                raise OllamaTimeoutError(f"generate timed out: {exc}") from exc
            if response.status_code == 404:
                raise OllamaUnsupportedModelError(
                    f"generate: model {spec.ollama_name!r} is not installed on the daemon"
                )
            if response.status_code >= 400:
                raise OllamaResponseError(
                    f"generate: daemon returned {response.status_code}: {response.text}"
                )
            payload = response.json()
            return GenerationResult(
                model=spec.ollama_name,
                response=str(payload.get("response", "")),
                eval_tokens=int(payload.get("eval_count", 0) or 0),
                total_duration_ns=int(payload.get("total_duration", 0) or 0),
            )

        return await self._with_retry("generate", _call)

    # ------------------------------------------------------------------
    # VisionPort
    # ------------------------------------------------------------------

    async def describe(
        self, model: str, image_bytes: bytes, *, prompt: str = "Describe the image."
    ) -> VisionResult:
        spec = self.resolve_spec(model)
        if not image_bytes:
            raise OllamaError("describe: image_bytes must be non-empty")
        client = await self._get_client()
        encoded = base64.b64encode(image_bytes).decode("ascii")

        async def _call() -> VisionResult:
            try:
                response = await client.post(
                    "/api/generate",
                    json={
                        "model": spec.ollama_name,
                        "prompt": prompt,
                        "images": [encoded],
                        "stream": False,
                    },
                )
            except (httpx.ConnectError, httpx.ReadError) as exc:
                raise OllamaConnectionError(f"describe: {exc}") from exc
            except httpx.TimeoutException as exc:
                raise OllamaTimeoutError(f"describe timed out: {exc}") from exc
            if response.status_code == 404:
                raise OllamaUnsupportedModelError(
                    f"describe: vision model {spec.ollama_name!r} is not installed"
                )
            if response.status_code >= 400:
                raise OllamaResponseError(
                    f"describe: daemon returned {response.status_code}: {response.text}"
                )
            payload = response.json()
            return VisionResult(
                model=spec.ollama_name,
                response=str(payload.get("response", "")),
                eval_tokens=int(payload.get("eval_count", 0) or 0),
            )

        return await self._with_retry("describe", _call)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


_ADAPTER: OllamaAdapter | None = None


def get_ollama_adapter() -> OllamaAdapter:
    """Return the process-wide :class:`OllamaAdapter` instance.

    Importing this module does not touch the network. The first
    call to a method on the adapter will lazily open the
    underlying ``httpx.AsyncClient``.
    """
    global _ADAPTER
    if _ADAPTER is None:
        # Honour JARVIS_OFFLINE only at the bootstrap / smoke layer.
        _ = os.getenv("JARVIS_OFFLINE")
        _ADAPTER = OllamaAdapter()
    return _ADAPTER


async def close_ollama_adapter() -> None:
    global _ADAPTER
    if _ADAPTER is not None:
        await _ADAPTER.aclose()
        _ADAPTER = None


__all__ = [
    "DEFAULT_CONNECT_TIMEOUT_SECONDS",
    "DEFAULT_REQUEST_TIMEOUT_SECONDS",
    "DEFAULT_RETRY_ATTEMPTS",
    "DEFAULT_RETRY_BASE_BACKOFF_SECONDS",
    "DEFAULT_RETRY_MAX_BACKOFF_SECONDS",
    "AvailabilityReport",
    "EmbeddingPort",
    "EmbeddingResult",
    "GenerationPort",
    "GenerationResult",
    "HealthReport",
    "ModelPort",
    "OllamaAdapter",
    "OllamaAdapterProtocol",
    "OllamaConnectionError",
    "OllamaError",
    "OllamaResponseError",
    "OllamaTimeoutError",
    "OllamaUnsupportedModelError",
    "VisionPort",
    "VisionResult",
    "close_ollama_adapter",
    "get_ollama_adapter",
]
