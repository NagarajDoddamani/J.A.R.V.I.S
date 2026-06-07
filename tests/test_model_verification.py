"""In-process tests for the model verification manifest + verifier.

These tests do not require a live Ollama daemon. They cover:

* Canonical manifest reconciliation (the four locked models are
  present and alias-aware).
* Offline / missing-model / unsupported-model detection.
* Digest override and report aggregation.

The actual HTTP smoke inference is exercised separately by the
``scripts/verify_models.sh`` script, which is gated by the
``JARVIS_RUN_LIVE_OLLAMA`` environment variable in CI.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.model_verification.manifest import (  # noqa: E402
    CANONICAL_MODELS,
    MODEL_ALIASES,
    find_spec,
    find_spec_by_canonical,
)
from tools.model_verification.verify_models import (  # noqa: E402
    ModelCheck,
    VerificationReport,
    _digest_of,
    verify,
)


# ---------------------------------------------------------------------------
# Manifest reconciliation
# ---------------------------------------------------------------------------


def test_manifest_contains_four_locked_models() -> None:
    canonical = {m.canonical_name for m in CANONICAL_MODELS}
    assert canonical == {
        "Qwen 3 8B",
        "Qwen Coder",
        "Qwen2.5-VL",
        "nomic-embed-text",
    }


def test_manifest_ollama_names_match_docker_compose_lock() -> None:
    ollama_names = {m.ollama_name for m in CANONICAL_MODELS}
    assert ollama_names == {"qwen3", "qwen-coder", "qwen2.5-vl", "nomic-embed-text"}


def test_find_spec_resolves_canonical_alias() -> None:
    assert find_spec("qwen3:8b") is not None
    assert find_spec("qwen3") is not None
    assert find_spec("qwen-coder") is not None
    assert find_spec("qwen2.5-vl") is not None
    assert find_spec("nomic-embed-text") is not None


def test_find_spec_returns_none_for_unsupported_name() -> None:
    assert find_spec("llama3") is None
    assert find_spec("phi-2") is None
    assert find_spec("gpt-4") is None


def test_find_spec_by_canonical_resolves() -> None:
    spec = find_spec_by_canonical("Qwen 3 8B")
    assert spec is not None
    assert spec.ollama_name == "qwen3"
    assert spec.expected_tag == "8b"


def test_find_spec_by_canonical_returns_none_for_unknown() -> None:
    assert find_spec_by_canonical("Unknown Model") is None


def test_aliases_are_nonempty() -> None:
    for ollama_name, aliases in MODEL_ALIASES.items():
        assert ollama_name in {m.ollama_name for m in CANONICAL_MODELS}
        assert aliases, f"aliases for {ollama_name} must be non-empty"
        assert ollama_name in aliases, f"{ollama_name} must alias to itself"


def test_embed_model_has_no_chat_smoke() -> None:
    spec = find_spec_by_canonical("nomic-embed-text")
    assert spec is not None
    assert spec.minimum_smoke_prompt == ""
    assert spec.smoke_max_tokens == 0


def test_general_model_has_chat_smoke() -> None:
    spec = find_spec_by_canonical("Qwen 3 8B")
    assert spec is not None
    assert spec.minimum_smoke_prompt
    assert spec.smoke_max_tokens > 0


# ---------------------------------------------------------------------------
# Digest extraction
# ---------------------------------------------------------------------------


def test_digest_of_extracts_sha256() -> None:
    payload = {"details": {"sha256": "abc123"}}
    assert _digest_of(payload) == "abc123"


def test_digest_of_returns_none_for_missing() -> None:
    assert _digest_of({}) is None
    assert _digest_of({"details": {}}) is None
    assert _digest_of(None) is None


# ---------------------------------------------------------------------------
# Report aggregation (no network)
# ---------------------------------------------------------------------------


class _MockTransport(httpx.MockTransport):
    """Alias for clarity in the test body."""


import httpx  # noqa: E402  (kept after the alias to avoid an import cycle)


def _ok_response(payload: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json=payload)


def _make_manager_payload(models: list[dict[str, Any]]) -> dict[str, Any]:
    return {"models": models}


def _patch_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_VERIFY_OFFLINE", "1")


def test_verify_reports_missing_models(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_offline(monkeypatch)
    # Empty Ollama install
    import httpx as _httpx

    transport = httpx.MockTransport(lambda req: _ok_response(_make_manager_payload([])))
    orig_init = _httpx.AsyncClient.__init__

    def _init(self, *args, **kwargs):
        kwargs.setdefault("transport", transport)
        orig_init(self, *args, **kwargs)

    monkeypatch.setattr(_httpx.AsyncClient, "__init__", _init)

    report = asyncio.run(verify(ollama_url="http://127.0.0.1:11434"))
    assert set(report.missing_models) == {
        "Qwen 3 8B",
        "Qwen Coder",
        "Qwen2.5-VL",
        "nomic-embed-text",
    }
    assert report.all_passed is False
    assert report.unsupported_models == []


def test_verify_reports_unsupported_models(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_offline(monkeypatch)
    payload = _make_manager_payload(
        [
            {"name": "qwen3:8b"},
            {"name": "qwen-coder:latest"},
            {"name": "qwen2.5-vl:latest"},
            {"name": "nomic-embed-text:latest"},
            {"name": "rogue-model:1"},
        ]
    )
    transport = httpx.MockTransport(lambda req: _ok_response(payload))
    import httpx as _httpx

    orig_init = _httpx.AsyncClient.__init__

    def _init(self, *args, **kwargs):
        kwargs.setdefault("transport", transport)
        orig_init(self, *args, **kwargs)

    monkeypatch.setattr(_httpx.AsyncClient, "__init__", _init)
    report = asyncio.run(verify(ollama_url="http://127.0.0.1:11434"))
    assert report.missing_models == []
    assert report.unsupported_models == ["rogue-model:1"]
    assert report.all_passed is False


def test_verify_accepts_clean_install(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_offline(monkeypatch)
    payload = _make_manager_payload(
        [
            {"name": "qwen3:8b"},
            {"name": "qwen-coder:latest"},
            {"name": "qwen2.5-vl:latest"},
            {"name": "nomic-embed-text:latest"},
        ]
    )
    transport = httpx.MockTransport(lambda req: _ok_response(payload))
    import httpx as _httpx

    orig_init = _httpx.AsyncClient.__init__

    def _init(self, *args, **kwargs):
        kwargs.setdefault("transport", transport)
        orig_init(self, *args, **kwargs)

    monkeypatch.setattr(_httpx.AsyncClient, "__init__", _init)
    report = asyncio.run(verify(ollama_url="http://127.0.0.1:11434"))
    assert report.missing_models == []
    assert report.unsupported_models == []
    # Offline mode: smoke_attempted=0 (no inference runs), digest_match is None.
    assert report.all_passed is True
    assert report.offline is True


def test_verify_handles_ollama_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_offline(monkeypatch)
    transport = httpx.MockTransport(lambda req: (_ for _ in ()).throw(httpx.ConnectError("no ollama")))

    import httpx as _httpx

    orig_init = _httpx.AsyncClient.__init__

    def _init(self, *args, **kwargs):
        kwargs.setdefault("transport", transport)
        orig_init(self, *args, **kwargs)

    monkeypatch.setattr(_httpx.AsyncClient, "__init__", _init)
    with pytest.raises(RuntimeError):
        asyncio.run(verify(ollama_url="http://127.0.0.1:11434"))


def test_report_to_dict_roundtrip() -> None:
    report = VerificationReport(
        timestamp="2026-06-07T00:00:00Z",
        ollama_url="http://127.0.0.1:11434",
        offline=True,
        smoke_attempted=0,
        smoke_passed=0,
        smoke_failed=0,
        missing_models=[],
        unsupported_models=[],
        checks=[
            ModelCheck(
                canonical_name="Qwen 3 8B",
                ollama_name="qwen3",
                expected_tag="8b",
                installed=True,
                installed_name="qwen3:8b",
                installed_tag="8b",
            )
        ],
        all_passed=True,
    )
    blob = report.to_dict()
    # JSON-serialisable
    json.dumps(blob)
    assert blob["all_passed"] is True
    assert blob["checks"][0]["canonical_name"] == "Qwen 3 8B"
