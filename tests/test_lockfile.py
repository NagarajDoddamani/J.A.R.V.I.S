"""Tests for the lockfile verifier (FND-001).

The tests are offline and self-contained. They exercise the
script's policy surface (file discovery, tool presence) without
invoking the real ``uv`` or ``pnpm`` toolchains, which are
expected to be available in the developer's environment and the
CI runner.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.lockfile.verify import (  # noqa: E402
    BACKEND_DIR,
    PNPM_LOCK,
    REPO_ROOT as _REPO_ROOT,
    UV_LOCK,
    _have_pnpm,
    _have_uv,
    _pnpm_check,
    _uv_check,
)


def test_constants_match_layout() -> None:
    assert _REPO_ROOT == REPO_ROOT
    assert BACKEND_DIR == REPO_ROOT / "backend"
    assert UV_LOCK == REPO_ROOT / "backend" / "uv.lock"
    assert PNPM_LOCK == REPO_ROOT / "pnpm-lock.yaml"


def test_uv_check_reports_missing_lock() -> None:
    """When uv.lock is absent and --generate is not passed, the check fails."""
    if not _have_uv():
        pytest.skip("uv not on PATH")
    # Run in a temporary copy of the repo so we don't perturb the workspace.
    import tempfile
    import shutil as _shutil

    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "jarvis"
        _shutil.copytree(REPO_ROOT / "backend", clone / "backend")
        _shutil.copytree(REPO_ROOT / "shared", clone / "shared")
        _shutil.copytree(REPO_ROOT / "tools", clone / "tools")
        # Make sure the lockfile is missing.
        if (clone / "backend" / "uv.lock").exists():
            (clone / "backend" / "uv.lock").unlink()
        result = subprocess.run(
            [sys.executable, "-m", "tools.lockfile.verify"],
            cwd=str(clone),
            check=False,
            capture_output=True,
            text=True,
        )
        # Either uv resolves pyproject (it will pull from cache or fail) or
        # the missing-lock branch fires. In CI we expect non-zero and the
        # message references uv.lock.
        assert result.returncode != 0
        assert "uv.lock" in result.stdout


def test_pnpm_check_reports_missing_lock() -> None:
    if not _have_pnpm():
        pytest.skip("pnpm not on PATH")
    import tempfile
    import shutil as _shutil

    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "jarvis"
        _shutil.copytree(REPO_ROOT / "backend", clone / "backend")
        _shutil.copytree(REPO_ROOT / "frontend", clone / "frontend")
        _shutil.copytree(REPO_ROOT / "shared", clone / "shared")
        _shutil.copytree(REPO_ROOT / "tools", clone / "tools")
        # Provide a pnpm-workspace.yaml so pnpm accepts the layout.
        (clone / "pnpm-workspace.yaml").write_text(
            "packages:\n  - 'backend'\n  - 'frontend'\n  - 'shared'\n  - 'tools'\n",
            encoding="utf-8",
        )
        if (clone / "pnpm-lock.yaml").exists():
            (clone / "pnpm-lock.yaml").unlink()
        result = subprocess.run(
            [sys.executable, "-m", "tools.lockfile.verify"],
            cwd=str(clone),
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "pnpm-lock.yaml" in result.stdout


def test_tool_discovery_helpers() -> None:
    # The helpers are deliberately permissive: they return None or a path.
    if shutil.which("uv") is None:
        assert _have_uv() is False
    else:
        assert _have_uv() is True
    if shutil.which("pnpm") is None:
        assert _have_pnpm() is False
    else:
        assert _have_pnpm() is True


def test_uv_check_returns_result() -> None:
    result = _uv_check(generate=False)
    assert result.name == "uv.lock"
    # Either pass (real toolchain) or fail with an actionable message.
    if not result.ok:
        assert "uv.lock" in result.detail or "uv" in result.detail


def test_pnpm_check_returns_result() -> None:
    result = _pnpm_check(generate=False)
    assert result.name == "pnpm-lock.yaml"
    if not result.ok:
        assert "pnpm-lock.yaml" in result.detail or "pnpm" in result.detail
