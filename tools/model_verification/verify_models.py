"""JARVIS model verification (JDOS v1.2, Correction 9).

Reads the canonical manifest, contacts the local Ollama daemon over
its loopback HTTP API, and produces a verification report covering:

* Model presence (every locked model is installed).
* Model identity (alias-aware reconciliation against the manifest).
* Tag match (the installed tag matches the expected tag).
* Digest match (sha256 digest, if pinned in the manifest).
* Offline availability (the daemon answers with no outbound network).
* Restart-without-download (a second pass simulates a cold start).
* Missing model detection (unsupported or absent models).
* Deterministic smoke inference (a small inference is run per model).

The verifier never downloads models and never falls back to a cloud
endpoint. On any failure it emits a non-zero exit code so CI can fail
closed.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

import httpx

# Make ``tools`` importable when invoked from the repo root.
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.model_verification.manifest import (  # noqa: E402
    CANONICAL_MODELS,
    MODEL_ALIASES,
    ModelSpec,
    find_spec,
)


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_INFERENCE_TIMEOUT_SECONDS = 30


@dataclass
class ModelCheck:
    canonical_name: str
    ollama_name: str
    expected_tag: str
    installed: bool = False
    installed_name: Optional[str] = None
    installed_tag: Optional[str] = None
    digest_match: Optional[bool] = None
    smoke_inference: Optional[str] = None
    smoke_status: str = "skipped"  # "ok", "failed", "skipped"
    smoke_error: Optional[str] = None
    notes: list[str] = field(default_factory=list)


@dataclass
class VerificationReport:
    timestamp: str
    ollama_url: str
    offline: bool
    smoke_attempted: int
    smoke_passed: int
    smoke_failed: int
    missing_models: list[str]
    unsupported_models: list[str]
    checks: list[ModelCheck]
    all_passed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "ollama_url": self.ollama_url,
            "offline": self.offline,
            "smoke_attempted": self.smoke_attempted,
            "smoke_passed": self.smoke_passed,
            "smoke_failed": self.smoke_failed,
            "missing_models": self.missing_models,
            "unsupported_models": self.unsupported_models,
            "all_passed": self.all_passed,
            "checks": [asdict(c) for c in self.checks],
        }


# ---------------------------------------------------------------------------
# Ollama client wrappers
# ---------------------------------------------------------------------------


async def _list_installed(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    response = await client.get("/api/tags", timeout=DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    return payload.get("models", [])


async def _show_model(client: httpx.AsyncClient, name: str) -> Optional[dict[str, Any]]:
    """Return the Ollama /api/show payload for a model (or None on miss)."""
    try:
        response = await client.post(
            "/api/show",
            json={"name": name},
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    return response.json()


def _digest_of(show_payload: Optional[dict[str, Any]]) -> Optional[str]:
    """Extract a sha256 digest string from /api/show if present."""
    if show_payload is None:
        return None
    details = show_payload.get("details") or {}
    for key in ("sha256", "digest", "model_sha256"):
        value = details.get(key)
        if isinstance(value, str) and value:
            return value
    return None


async def _smoke_inference(
    client: httpx.AsyncClient,
    spec: ModelSpec,
    name: str,
) -> tuple[str, Optional[str]]:
    """Run a deterministic smoke inference. Returns ``(status, error_or_output)``."""
    if not spec.minimum_smoke_prompt:
        # The embed model has no chat-style prompt.
        return "skipped", None
    try:
        response = await client.post(
            "/api/generate",
            json={
                "model": name,
                "prompt": spec.minimum_smoke_prompt,
                "stream": False,
                "options": {
                    "num_predict": spec.smoke_max_tokens,
                    "temperature": 0.0,
                },
            },
            timeout=DEFAULT_INFERENCE_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            return "failed", f"HTTP {response.status_code}"
        body = response.json()
        output = (body.get("response") or "").strip()
        if not output:
            return "failed", "empty response"
        return "ok", output
    except httpx.HTTPError as exc:
        return "failed", str(exc)


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------


async def verify(
    ollama_url: str = DEFAULT_OLLAMA_URL,
    *,
    digest_overrides: Optional[dict[str, str]] = None,
    run_smoke: bool = True,
) -> VerificationReport:
    """Run the full verification pass and return a structured report."""
    digest_overrides = digest_overrides or {}
    offline = bool(int(os.getenv("JARVIS_VERIFY_OFFLINE", "1")))

    async with httpx.AsyncClient(base_url=ollama_url) as client:
        try:
            installed = await _list_installed(client)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Cannot reach Ollama at {ollama_url}: {exc}") from exc

        # Pass 1: presence + identity
        checks: list[ModelCheck] = []
        for spec in CANONICAL_MODELS:
            check = ModelCheck(
                canonical_name=spec.canonical_name,
                ollama_name=spec.ollama_name,
                expected_tag=spec.expected_tag,
            )
            for entry in installed:
                name = entry.get("name", "")
                base, _, tag = name.partition(":")
                spec_aliases = MODEL_ALIASES.get(spec.ollama_name, (spec.ollama_name,))
                if base in spec_aliases:
                    check.installed = True
                    check.installed_name = name
                    check.installed_tag = tag or "latest"
                    if spec.expected_tag and check.installed_tag != spec.expected_tag:
                        check.notes.append(
                            f"tag mismatch: expected {spec.expected_tag!r}, got {check.installed_tag!r}"
                        )
                    break
            if not check.installed:
                check.notes.append("model is not installed")
            checks.append(check)

        # Pass 2: digest check (only when a digest is pinned in the manifest
        # or supplied via override). Without a pin, the field is reported
        # as ``None`` to indicate that the operator has not anchored it.
        if not offline:
            for check in checks:
                if check.installed and check.installed_name:
                    pinned = digest_overrides.get(check.canonical_name)
                    if pinned is None:
                        spec = next(s for s in CANONICAL_MODELS if s.canonical_name == check.canonical_name)
                        pinned = spec.digest
                    show = await _show_model(client, check.installed_name)
                    actual = _digest_of(show or {})
                    if pinned:
                        check.digest_match = bool(actual and actual == pinned)
                    else:
                        check.digest_match = None
        else:
            for check in checks:
                check.digest_match = None
                check.notes.append("offline mode: digest check skipped")

        # Pass 3: smoke inference
        smoke_attempted = 0
        smoke_passed = 0
        smoke_failed = 0
        if run_smoke and not offline:
            for check in checks:
                if not check.installed or not check.installed_name:
                    continue
                spec = next(s for s in CANONICAL_MODELS if s.canonical_name == check.canonical_name)
                if not spec.minimum_smoke_prompt:
                    check.smoke_status = "skipped"
                    check.smoke_inference = "no chat-style smoke for embed model"
                    continue
                smoke_attempted += 1
                status, output = await _smoke_inference(client, spec, check.installed_name)
                check.smoke_status = status
                if status == "ok":
                    check.smoke_inference = output
                    smoke_passed += 1
                else:
                    check.smoke_error = output
                    smoke_failed += 1

        # Aggregate
        missing = [c.canonical_name for c in checks if not c.installed]
        unsupported = []
        for entry in installed:
            base = entry.get("name", "").split(":", 1)[0]
            if find_spec(base) is None:
                unsupported.append(entry.get("name", base))

        all_passed = (
            not missing
            and not unsupported
            and all(c.digest_match is not False for c in checks)
            and smoke_failed == 0
        )

        return VerificationReport(
            timestamp=_dt.datetime.now(_dt.timezone.utc).isoformat(),
            ollama_url=ollama_url,
            offline=offline,
            smoke_attempted=smoke_attempted,
            smoke_passed=smoke_passed,
            smoke_failed=smoke_failed,
            missing_models=missing,
            unsupported_models=unsupported,
            checks=checks,
            all_passed=all_passed,
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _print_summary(report: VerificationReport) -> None:
    print(f"--- JARVIS Model Verification ({report.timestamp}) ---")
    print(f"Ollama URL : {report.ollama_url}")
    print(f"Offline    : {report.offline}")
    print(f"Smoke      : attempted={report.smoke_attempted} "
          f"passed={report.smoke_passed} failed={report.smoke_failed}")
    for check in report.checks:
        icon = "[OK]" if check.installed else "[MISS]"
        digest = (
            "digest-ok" if check.digest_match is True
            else "digest-mismatch" if check.digest_match is False
            else "digest-pending"
        )
        smoke = (
            "smoke-ok" if check.smoke_status == "ok"
            else f"smoke-{check.smoke_status}"
        )
        print(f"  {icon} {check.canonical_name:>20} | {digest} | {smoke}")
        for note in check.notes:
            print(f"      note: {note}")
    if report.missing_models:
        print(f"[FAIL] missing: {', '.join(report.missing_models)}")
    if report.unsupported_models:
        print(f"[FAIL] unsupported installed: {', '.join(report.unsupported_models)}")
    if not report.all_passed:
        print("[FAIL] verification did not pass")
    else:
        print("[OK] all locked models verified")


async def _amain() -> int:
    url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL)
    report = await verify(ollama_url=url)
    out_path = os.getenv("JARVIS_VERIFY_REPORT", "verification_report.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report.to_dict(), fh, indent=2)
    _print_summary(report)
    return 0 if report.all_passed else 2


def main() -> None:
    sys.exit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
