"""Shared helpers for Phase 01 tests.

Contains utilities used across multiple test modules:
* compose block extraction (robust YAML-aware scanning)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
COMPOSE_PATH: Final[Path] = REPO_ROOT / "docker-compose.yml"


_SERVICE_BLOCK_CACHE: dict[str, str] = {}


def _parse_compose() -> dict[str, str]:
    """Return a dict mapping each top-level service name to its YAML block text.

    Handles the YAML block structure: services are at 2-space indent,
    service properties at 4+ spaces.
    """
    if _SERVICE_BLOCK_CACHE:
        return _SERVICE_BLOCK_CACHE

    if not COMPOSE_PATH.exists():
        return {}

    text = COMPOSE_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    result: dict[str, str] = {}
    current_service: str | None = None
    current_lines: list[str] = []

    # The compose file uses `  postgres:` (2-space indent) for service names.
    # Lines inside a service block use 4+ spaces.
    svc_pattern = re.compile(r"^  (\w[\w-]*):$")

    for line in lines:
        match = svc_pattern.match(line)
        if match:
            # Save previous service
            if current_service is not None:
                result[current_service] = "\n".join(current_lines)
            current_service = match.group(1)
            current_lines = [line]
        elif current_service is not None:
            current_lines.append(line)

    if current_service is not None:
        result[current_service] = "\n".join(current_lines)

    _SERVICE_BLOCK_CACHE.update(result)
    return result


def service_block(service: str) -> str:
    """Return the YAML block for a given service, or empty string if not found."""
    blocks = _parse_compose()
    return blocks.get(service, "")


def compose_text() -> str:
    """Return the raw docker-compose.yml text."""
    if not COMPOSE_PATH.exists():
        return ""
    return COMPOSE_PATH.read_text(encoding="utf-8")


__all__ = [
    "COMPOSE_PATH",
    "REPO_ROOT",
    "service_block",
    "compose_text",
]
