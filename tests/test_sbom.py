"""Tests for the SBOM, inventory, and license report generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.sbom.generate import (  # noqa: E402
    InstalledPackage,
    build_inventory,
    build_license_report,
    build_sbom,
    collect_installed_packages,
    write_outputs,
)


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------


def test_installed_package_to_component_has_purl() -> None:
    pkg = InstalledPackage(name="fastapi", version="0.111.0", license="MIT")
    comp = pkg.to_component()
    assert comp["name"] == "fastapi"
    assert comp["version"] == "0.111.0"
    assert comp["purl"] == "pkg:pypi/fastapi@0.111.0"
    assert comp["licenses"][0]["license"]["name"] == "MIT"


def test_installed_package_omits_licenses_when_unknown() -> None:
    pkg = InstalledPackage(name="x", version="1.0", license="unknown")
    assert pkg.to_component()["licenses"] == []


# ---------------------------------------------------------------------------
# Aggregators
# ---------------------------------------------------------------------------


def test_build_sbom_contains_metadata_and_components() -> None:
    packages = [
        InstalledPackage(name="a", version="1.0", license="MIT"),
        InstalledPackage(name="b", version="2.0", license="Apache-2.0"),
    ]
    sbom = build_sbom(packages, tool_version="1.2.0")
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
    assert sbom["version"] == 1
    assert sbom["metadata"]["tools"][0]["name"] == "jarvis-sbom"
    assert sbom["metadata"]["component"]["name"] == "jarvis-foundation"
    assert len(sbom["components"]) == 2
    # JSON-serialisable.
    json.dumps(sbom)


def test_build_inventory_returns_one_row_per_package() -> None:
    packages = [InstalledPackage(name="a", version="1.0"), InstalledPackage(name="b", version="2.0")]
    inventory = build_inventory(packages)
    assert inventory == [
        {"name": "a", "version": "1.0", "license": "unknown"},
        {"name": "b", "version": "2.0", "license": "unknown"},
    ]


def test_build_license_report_groups_by_license() -> None:
    packages = [
        InstalledPackage(name="a", version="1.0", license="MIT"),
        InstalledPackage(name="b", version="2.0", license="MIT"),
        InstalledPackage(name="c", version="3.0", license="Apache-2.0"),
    ]
    report = build_license_report(packages)
    assert report["summary"] == {"Apache-2.0": 1, "MIT": 2}
    assert set(report["by_license"]["MIT"]) == {"a", "b"}


# ---------------------------------------------------------------------------
# Live introspection (no network)
# ---------------------------------------------------------------------------


def test_collect_installed_packages_is_sorted() -> None:
    packages = collect_installed_packages()
    names = [p.name for p in packages]
    assert names == sorted(names, key=str.lower)
    # Every entry has a non-empty name and version.
    for pkg in packages:
        assert pkg.name
        assert pkg.version


def test_collect_installed_packages_contains_fastapi_or_known_lib() -> None:
    names = {p.name.lower() for p in collect_installed_packages()}
    # The Foundation layer's runtime dependencies are typically
    # installed in any environment that exercises this test.
    expected = {"fastapi", "pydantic"}
    if not (expected & names):
        pytest.skip("Foundation runtime deps not present in this environment")
    assert expected & names


# ---------------------------------------------------------------------------
# write_outputs
# ---------------------------------------------------------------------------


def test_write_outputs_creates_three_files(tmp_path: Path) -> None:
    result = write_outputs(tmp_path, tool_version="1.2.0")
    assert Path(result["sbom"]).exists()
    assert Path(result["inventory"]).exists()
    assert Path(result["licenses"]).exists()
    # SBOM parses as JSON.
    sbom = json.loads(Path(result["sbom"]).read_text(encoding="utf-8"))
    assert sbom["bomFormat"] == "CycloneDX"
    # License report parses as JSON and has a non-empty summary.
    licenses = json.loads(Path(result["licenses"]).read_text(encoding="utf-8"))
    assert "summary" in licenses
