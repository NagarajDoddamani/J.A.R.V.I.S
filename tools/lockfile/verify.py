"""JARVIS lockfile verifier (Phase 01, FND-001).

The lockfile policy requires reproducible installs:

* ``backend/uv.lock`` must exist and be in sync with
  ``backend/pyproject.toml`` (verified via ``uv lock --check``).
* ``pnpm-lock.yaml`` must exist at the repo root and be in sync
  with every workspace package's ``package.json`` (verified via
  ``pnpm install --lockfile-only`` or
  ``pnpm install --frozen-lockfile``).

The script is dependency-light (stdlib only) and works on
Windows, macOS, and Linux. It exits non-zero on any failure so it
can be wired into CI, bootstrap, and the local pre-flight script.

Usage::

    python -m tools.lockfile.verify            # check (default)
    python -m tools.lockfile.verify --generate # generate when missing/stale
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
BACKEND_DIR: Final[Path] = REPO_ROOT / "backend"
UV_LOCK: Final[Path] = BACKEND_DIR / "uv.lock"
PNPM_LOCK: Final[Path] = REPO_ROOT / "pnpm-lock.yaml"


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str

    def render(self) -> str:
        marker = "PASS" if self.ok else "FAIL"
        return f"[{marker}] {self.name}: {self.detail}"


# ---------------------------------------------------------------------------
# Tool discovery
# ---------------------------------------------------------------------------


def _which(candidates: tuple[str, ...]) -> str | None:
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    return None


def _have_uv() -> bool:
    return _which(("uv",)) is not None


def _have_pnpm() -> bool:
    return _which(("pnpm",)) is not None


# ---------------------------------------------------------------------------
# uv
# ---------------------------------------------------------------------------


def _uv_check(generate: bool) -> CheckResult:
    if not _have_uv():
        return CheckResult("uv.lock", False, "uv not on PATH; install from https://astral.sh/uv")

    if not UV_LOCK.exists():
        if not generate:
            return CheckResult(
                "uv.lock",
                False,
                f"missing {UV_LOCK.relative_to(REPO_ROOT)}; run with --generate or `uv lock`",
            )
        result = subprocess.run(
            ["uv", "lock"],
            cwd=str(BACKEND_DIR),
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return CheckResult("uv.lock", False, f"uv lock failed: {result.stderr.strip()}")

    result = subprocess.run(
        ["uv", "lock", "--check"],
        cwd=str(BACKEND_DIR),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return CheckResult("uv.lock", True, "uv.lock is in sync with pyproject.toml")
    return CheckResult(
        "uv.lock",
        False,
        f"uv lock --check failed: {result.stderr.strip() or result.stdout.strip()}",
    )


# ---------------------------------------------------------------------------
# pnpm
# ---------------------------------------------------------------------------


def _pnpm_check(generate: bool) -> CheckResult:
    if not _have_pnpm():
        return CheckResult("pnpm-lock.yaml", False, "pnpm not on PATH; install via `corepack enable pnpm`")

    if not PNPM_LOCK.exists():
        if not generate:
            return CheckResult(
                "pnpm-lock.yaml",
                False,
                f"missing {PNPM_LOCK.relative_to(REPO_ROOT)}; run with --generate or `pnpm install`",
            )
        # Generate the lockfile without touching node_modules.
        result = subprocess.run(
            ["pnpm", "install", "--lockfile-only"],
            cwd=str(REPO_ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return CheckResult("pnpm-lock.yaml", False, f"pnpm install --lockfile-only failed: {result.stderr.strip()}")

    # Verify the lockfile is in sync.
    result = subprocess.run(
        ["pnpm", "install", "--frozen-lockfile"],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return CheckResult("pnpm-lock.yaml", True, "pnpm-lock.yaml is in sync with workspace package.json files")
    return CheckResult(
        "pnpm-lock.yaml",
        False,
        f"pnpm install --frozen-lockfile failed: {result.stderr.strip() or result.stdout.strip()}",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS lockfile verifier (FND-001)")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate missing or stale lockfiles before checking.",
    )
    args = parser.parse_args()

    # The verifier runs offline by intent; if the operator wants to
    # regenerate, opt in explicitly.
    if args.generate:
        os.environ.setdefault("UV_OFFLINE", "0")
    else:
        os.environ.setdefault("UV_OFFLINE", "1")

    results = [_uv_check(args.generate), _pnpm_check(args.generate)]
    for r in results:
        print(r.render())
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
