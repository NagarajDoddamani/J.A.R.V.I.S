from __future__ import annotations

import asyncio
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import asyncpg
import httpx
from nats import connect as nats_connect
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis as AsyncRedis
from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from backend.core.config import settings

START_TIME = time.monotonic()
REFRESH_INTERVAL = 3

_TIMEOUT = 5


@dataclass
class ServiceStatus:
    name: str
    group: str = "infra"
    connected: bool = False
    error: str = ""
    latency_ms: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def _format_latency(ms: float | None) -> str:
    if ms is None:
        return "\u2014"
    if ms < 1:
        return "<1ms"
    if ms < 1000:
        return f"{ms:.0f}ms"
    return f"{ms / 1000:.1f}s"


def _status_text(s: ServiceStatus) -> Text:
    if s.connected:
        return Text("Connected", style="bold green")
    if s.error:
        return Text(f"Error: {s.error}", style="bold red")
    return Text("Disconnected", style="bold red")


def _dot(s: ServiceStatus) -> Text:
    color = "green" if s.connected else "red"
    return Text("\u25cf  ", style=f"bold {color}")


def _make_service_table(services: list[ServiceStatus], title: str) -> Panel:
    table = Table.grid(padding=(0, 2))
    table.add_column(no_wrap=True)
    table.add_column(no_wrap=True)
    table.add_column(no_wrap=True)
    table.add_column(style="dim", no_wrap=True)
    for svc in services:
        lat = _format_latency(svc.latency_ms)
        extra = ""
        if svc.name == "Ollama" and svc.connected and svc.extra.get("models"):
            extra = f"  ({svc.extra['models']} models)"
        elif svc.name == "Runtime" and svc.connected and svc.extra.get("version"):
            extra = f"  v{svc.extra['version']}"
        table.add_row(
            _dot(svc),
            Text(svc.name, style="bold"),
            _status_text(svc),
            Text(f"{lat}{extra}", style="dim"),
        )
    return Panel(table, title=title, border_style="dim", padding=(1, 2))


# ---------------------------------------------------------------------------
# Infrastructure probes
# ---------------------------------------------------------------------------


async def check_postgres() -> ServiceStatus:
    s = ServiceStatus("PostgreSQL", group="infra")
    t0 = time.monotonic()
    try:
        conn = await asyncpg.connect(
            host=settings.POSTGRES_HOST,
            port=int(settings.POSTGRES_URL.split(":")[-1].split("/")[0]),
            user=settings.POSTGRES_URL.split("//")[1].split(":")[0],
            password=settings.POSTGRES_URL.split(":")[2].split("@")[0],
            database=settings.POSTGRES_URL.split("/")[-1],
            timeout=3,
        )
        await conn.execute("SELECT 1")
        await conn.close()
        s.connected = True
        s.latency_ms = (time.monotonic() - t0) * 1000
    except BaseException as e:
        s.error = str(e).split("\n")[0][:60]
    return s


async def check_redis() -> ServiceStatus:
    s = ServiceStatus("Redis", group="infra")
    t0 = time.monotonic()
    try:
        client = AsyncRedis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        await client.ping()
        await client.aclose()
        s.connected = True
        s.latency_ms = (time.monotonic() - t0) * 1000
    except BaseException as e:
        s.error = str(e).split("\n")[0][:60]
    return s


async def check_nats() -> ServiceStatus:
    s = ServiceStatus("NATS", group="infra")
    t0 = time.monotonic()
    try:
        nc = await nats_connect(settings.NATS_URL, connect_timeout=3)
        s.connected = nc.is_connected
        s.latency_ms = (time.monotonic() - t0) * 1000
        await nc.drain()
    except BaseException as e:
        s.error = str(e).split("\n")[0][:60]
    return s


async def check_qdrant() -> ServiceStatus:
    s = ServiceStatus("Qdrant", group="infra")
    t0 = time.monotonic()
    try:
        client = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=3)
        await client.get_collections()
        await client.close()
        s.connected = True
        s.latency_ms = (time.monotonic() - t0) * 1000
    except BaseException as e:
        s.error = str(e).split("\n")[0][:60]
    return s


async def check_ollama() -> ServiceStatus:
    s = ServiceStatus("Ollama", group="infra")
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
        s.connected = resp.status_code == 200
        s.latency_ms = (time.monotonic() - t0) * 1000
        if s.connected:
            data = resp.json()
            models = data.get("models", [])
            s.extra["models"] = str(len(models))
        else:
            s.error = f"HTTP {resp.status_code}"
    except BaseException as e:
        s.error = str(e).split("\n")[0][:60]
    return s


# ---------------------------------------------------------------------------
# Backend / Runtime probe (hits /api/v1/health)
# ---------------------------------------------------------------------------


async def check_backend() -> ServiceStatus:
    s = ServiceStatus("Runtime", group="app")
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"http://{settings.API_HOST}:{settings.API_PORT}/api/v1/health"
            )
        s.latency_ms = (time.monotonic() - t0) * 1000
        if resp.status_code == 200:
            s.connected = True
            data = resp.json()
            s.extra["version"] = data.get("version", "")
        else:
            s.error = f"HTTP {resp.status_code}"
    except BaseException as e:
        s.error = str(e).split("\n")[0][:60]
    return s


# ---------------------------------------------------------------------------
# Application-service probes (via backend API)
# ---------------------------------------------------------------------------

_APP_SERVICE_ENDPOINTS: dict[str, str] = {
    "Memory": "/api/v1/memory/memories",
    "Knowledge": "/api/v1/knowledge/sources",
    "Planner": "/api/v1/planner/plans",
    "Research": "/api/v1/research/requests",
    "Automation": "/api/v1/automation/automations",
    "Policy": "/api/v1/policy/",
    "Agent": "/api/v1/agent/",
}


async def _probe_api_service(name: str, path: str) -> ServiceStatus:
    """Probe a backend API endpoint for availability.

    Returns connected=True when the endpoint returns any HTTP response
    (including 4xx). Returns connected=False on connection errors or
    server-side errors (5xx).
    """
    s = ServiceStatus(name, group="app")
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"http://{settings.API_HOST}:{settings.API_PORT}{path}"
            )
        s.latency_ms = (time.monotonic() - t0) * 1000
        if resp.status_code < 500:
            s.connected = True
        else:
            s.error = f"HTTP {resp.status_code}"
    except BaseException as e:
        s.error = str(e).split("\n")[0][:60]
        if not s.error:
            s.error = type(e).__name__
    return s


# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------


async def poll_all() -> dict[str, ServiceStatus]:
    results: dict[str, ServiceStatus] = {}

    # 1. Check infra (direct connections)
    infra_coros = [
        check_postgres(),
        check_redis(),
        check_nats(),
        check_qdrant(),
        check_ollama(),
    ]
    infra_results = await asyncio.gather(*infra_coros, return_exceptions=True)
    for res in infra_results:
        if isinstance(res, ServiceStatus):
            results[res.name] = res
        else:
            results["unknown_infra"] = ServiceStatus(
                "unknown_infra", error=str(res)[:60]
            )

    # 2. Check backend runtime
    runtime = await check_backend()
    results[runtime.name] = runtime

    # 3. Check individual app services only if runtime is reachable
    if runtime.connected:
        app_coros = [
            _probe_api_service(name, path)
            for name, path in _APP_SERVICE_ENDPOINTS.items()
        ]
        app_results = await asyncio.gather(*app_coros, return_exceptions=True)
        for res in app_results:
            if isinstance(res, ServiceStatus):
                results[res.name] = res
            else:
                results["unknown_app"] = ServiceStatus(
                    "unknown_app", error=str(res)[:60]
                )
    else:
        for name in _APP_SERVICE_ENDPOINTS:
            results[name] = ServiceStatus(
                name=name,
                group="app",
                error="Runtime offline",
            )

    return results


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------


def _error_count(results: dict[str, ServiceStatus]) -> int:
    return sum(1 for s in results.values() if not s.connected and s.error)


def _build_layout(results: dict[str, ServiceStatus]) -> Layout:
    infra_order = ["PostgreSQL", "Redis", "NATS", "Qdrant", "Ollama"]
    app_order = ["Runtime", "Memory", "Knowledge", "Planner", "Research", "Automation", "Policy", "Agent"]

    infra_services = [results[n] for n in infra_order if n in results]
    app_services = [results[n] for n in app_order if n in results]

    infra_panel = _make_service_table(infra_services, "Infrastructure")
    app_panel = _make_service_table(app_services, "Application")

    body = Table.grid(padding=(0, 2))
    body.add_column(ratio=1)
    body.add_column(ratio=1)
    body.add_row(infra_panel, app_panel)

    elapsed = time.monotonic() - START_TIME
    errors = _error_count(results)
    infra_healthy = all(
        s.connected for s in infra_services
    )
    runtime_ok = results.get("Runtime", ServiceStatus("Runtime")).connected

    if infra_healthy and runtime_ok:
        status_text = "All Systems Operational"
        status_color = "bold green"
    elif errors > 0:
        status_text = f"{errors} Service Error{'s' if errors != 1 else ''}"
        status_color = "bold yellow"
    else:
        status_text = "Disconnected"
        status_color = "bold red"

    summary = Text.assemble(
        ("\u25c6 ", "bold"),
        (status_text, status_color),
        ("  \u2502  ", "dim"),
        (f"Uptime: {elapsed:.0f}s", "cyan"),
        ("  \u2502  ", "dim"),
        (f"{datetime.now(UTC):%H:%M:%S UTC}", "dim"),
    )
    summary_bar = Panel(
        Align.center(summary),
        border_style="dim" if infra_healthy else "yellow",
        padding=(1, 2),
    )

    header = Panel(
        Align.center(
            Text.assemble(("J.A.R.V.I.S", "bold white"), (" AI Brain", "bold cyan")),
        ),
        border_style="bright_blue",
        padding=(1, 2),
    )

    layout = Layout()
    layout.split(
        Layout(header, size=4),
        Layout(body),
        Layout(summary_bar, size=4),
    )
    return layout


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    console = Console()
    console.print("[dim]J.A.R.V.I.S AI Brain Dashboard — probing services...[/]")

    results = await poll_all()

    with Live(
        _build_layout(results),
        console=console,
        screen=True,
        auto_refresh=False,
        refresh_per_second=1 / REFRESH_INTERVAL,
    ) as live:
        while True:
            try:
                results = await poll_all()
                live.update(_build_layout(results))
            except BaseException:
                traceback.print_exc(file=sys.stderr)
            await asyncio.sleep(REFRESH_INTERVAL)


def entry() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    entry()
