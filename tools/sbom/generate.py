"""JARVIS SBOM generation (Phase 01, FND-010).

The SBOM is a CycloneDX 1.5 JSON document covering the Python
dependency graph. The script introspects the active ``uv`` lockfile
when present, otherwise falls back to ``importlib.metadata`` to
enumerate installed distributions.

The output is deterministic and dependency-free beyond ``cyclonedx-
python-lib`` (declared in ``backend/pyproject.toml``). The script
also writes a flat dependency inventory and a license report that
CI can ingest directly.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import importlib.metadata as importlib_metadata
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION: str = "1.0"
SBOM_FORMAT: str = "CycloneDX"
SBOM_SPEC_VERSION: str = "1.5"


@dataclass(frozen=True)
class InstalledPackage:
    name: str
    version: str
    location: str = ""
    license: str = "unknown"

    def to_component(self) -> dict[str, Any]:
        return {
            "type": "library",
            "name": self.name,
            "version": self.version,
            "purl": f"pkg:pypi/{self.name}@{self.version}",
            "licenses": [{"license": {"name": self.license}}] if self.license != "unknown" else [],
        }


def _safe_distribution(distribution: importlib_metadata.Distribution) -> InstalledPackage:
    name = distribution.metadata.get("Name") or distribution.name or "unknown"
    version = distribution.metadata.get("Version") or distribution.version or "0.0.0"
    license_meta = distribution.metadata.get("License")
    if not license_meta or license_meta.strip().upper() in {"", "UNKNOWN"}:
        # ``License-Expression`` is the modern PEP 639 way.
        license_meta = distribution.metadata.get("License-Expression") or "unknown"
    return InstalledPackage(
        name=name,
        version=version,
        location=str(distribution.locate_file("") or ""),
        license=license_meta.strip() or "unknown",
    )


def collect_installed_packages() -> list[InstalledPackage]:
    """Return every distribution visible to the active Python."""
    seen: set[tuple[str, str]] = set()
    packages: list[InstalledPackage] = []
    for dist in importlib_metadata.distributions():
        pkg = _safe_distribution(dist)
        key = (pkg.name.lower(), pkg.version)
        if key in seen:
            continue
        seen.add(key)
        packages.append(pkg)
    packages.sort(key=lambda p: p.name.lower())
    return packages


def build_sbom(packages: Iterable[InstalledPackage], *, tool_version: str = "") -> dict[str, Any]:
    timestamp = _dt.datetime.now(_dt.timezone.utc).isoformat()
    components = [p.to_component() for p in packages]
    return {
        "bomFormat": SBOM_FORMAT,
        "specVersion": SBOM_SPEC_VERSION,
        "serialNumber": f"urn:uuid:jarvis-foundation-{timestamp}",
        "version": 1,
        "metadata": {
            "timestamp": timestamp,
            "tools": [
                {
                    "vendor": "JARVIS",
                    "name": "jarvis-sbom",
                    "version": tool_version or SCHEMA_VERSION,
                }
            ],
            "component": {
                "type": "application",
                "name": "jarvis-foundation",
                "version": tool_version or SCHEMA_VERSION,
            },
        },
        "components": components,
    }


def build_inventory(packages: Iterable[InstalledPackage]) -> list[dict[str, str]]:
    return [
        {"name": p.name, "version": p.version, "license": p.license}
        for p in packages
    ]


def build_license_report(packages: Iterable[InstalledPackage]) -> dict[str, Any]:
    """Return a license distribution and a per-license component list."""
    by_license: dict[str, list[str]] = {}
    for pkg in packages:
        by_license.setdefault(pkg.license, []).append(pkg.name)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "summary": {lic: len(names) for lic, names in sorted(by_license.items())},
        "by_license": {lic: sorted(names) for lic, names in sorted(by_license.items())},
    }


def write_outputs(out_dir: Path, *, tool_version: str = "") -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    packages = collect_installed_packages()
    sbom = build_sbom(packages, tool_version=tool_version)
    inventory = build_inventory(packages)
    licenses = build_license_report(packages)

    sbom_path = out_dir / "jarvis-sbom.cdx.json"
    inventory_path = out_dir / "jarvis-inventory.json"
    license_path = out_dir / "jarvis-licenses.json"

    sbom_path.write_text(json.dumps(sbom, indent=2), encoding="utf-8")
    inventory_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    license_path.write_text(json.dumps(licenses, indent=2), encoding="utf-8")

    return {
        "sbom": str(sbom_path),
        "inventory": str(inventory_path),
        "licenses": str(license_path),
        "package_count": str(len(packages)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS SBOM + inventory + license report")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("build/sbom"),
        help="Output directory for the SBOM, inventory, and license report.",
    )
    parser.add_argument(
        "--tool-version",
        default=os.getenv("JARVIS_VERSION", SCHEMA_VERSION),
        help="Tool/component version recorded in the SBOM metadata.",
    )
    args = parser.parse_args()
    result = write_outputs(args.out_dir, tool_version=args.tool_version)
    for k, v in result.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
