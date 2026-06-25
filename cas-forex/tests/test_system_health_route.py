"""Tests for the /api/forex/system-health route.

The route module is mounted onto a local FastAPI app under the same
prefix the parent integration will use. Loader-injection lets us
exercise every status branch without touching disk.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI

from api.routes import system_health as route_module
from cas_forex.system_health_monitor import DiskSpace


_TEST_PREFIX = "/api/forex/system-health"

_app = FastAPI()
_app.include_router(route_module.router, prefix=_TEST_PREFIX, tags=["system-health"])


async def _asgi_get(path: str) -> tuple[int, Any]:
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    parsed = urlsplit(path)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("utf-8"),
        "query_string": parsed.query.encode("utf-8"),
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await _app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    payload = json.loads(body.decode("utf-8")) if body else None
    return int(status), payload


@pytest.fixture(autouse=True)
def _reset_loader_between_tests():
    route_module.reset_loader_for_testing()
    yield
    route_module.reset_loader_for_testing()


def test_route_returns_200_when_no_evidence() -> None:
    route_module.set_loader_for_testing(lambda: {
        "process_signals": {
            "uvicorn-api": None,
            "autowake-supervisor": None,
            "mt5-terminal": None,
        },
        "artifact_latests": {},
        "disk_space": None,
        "recent_error_count": 0,
    })
    status, body = asyncio.run(_asgi_get(f"{_TEST_PREFIX}/snapshot"))
    assert status == 200
    assert body["overall_status"] == "unknown"


def test_payload_carries_required_fields() -> None:
    route_module.set_loader_for_testing(lambda: {
        "process_signals": {
            "uvicorn-api": None,
            "autowake-supervisor": None,
            "mt5-terminal": None,
        },
        "artifact_latests": {},
        "disk_space": None,
        "recent_error_count": 0,
    })
    _, body = asyncio.run(_asgi_get(f"{_TEST_PREFIX}/snapshot"))
    required = {
        "snapshot_at_iso",
        "processes",
        "evidence_freshness",
        "disk_space",
        "recent_error_count",
        "plain_english_summary",
        "diagnostic_hints",
        "overall_status",
    }
    assert required.issubset(set(body.keys()))


def test_route_surfaces_healthy_branch() -> None:
    from datetime import datetime, timezone

    now_iso = datetime.now(timezone.utc).isoformat()
    route_module.set_loader_for_testing(lambda: {
        "process_signals": {
            "uvicorn-api": now_iso,
            "autowake-supervisor": now_iso,
            "mt5-terminal": now_iso,
        },
        "artifact_latests": {"agent-workflow-cycle": now_iso},
        "disk_space": DiskSpace(
            repo_root="/tmp/repo",
            evidence_runs_bytes=0,
            free_disk_bytes=100 * (1024 ** 3),
            free_disk_pct=40.0,
        ),
        "recent_error_count": 0,
    })
    status, body = asyncio.run(_asgi_get(f"{_TEST_PREFIX}/snapshot"))
    assert status == 200
    assert body["overall_status"] == "healthy"
    blob = (body["plain_english_summary"] + " " + " ".join(body["diagnostic_hints"])).lower()
    for phrase in ("you should restart", "consider restarting", "kill the", "should be killed", "force restart"):
        assert phrase not in blob


def test_default_loader_is_load_system_health_inputs() -> None:
    route_module.reset_loader_for_testing()
    assert route_module._LOADER is route_module._default_loader
