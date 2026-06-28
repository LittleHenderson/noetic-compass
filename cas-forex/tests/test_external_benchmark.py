"""External benchmark snapshot coverage."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

from api.server import app
from cas_forex.external_benchmark import load_external_benchmark_report


async def _asgi_get(path: str) -> tuple[int, dict[str, Any]]:
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
    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return int(status), json.loads(body.decode("utf-8"))


def test_external_benchmark_snapshot_loads_forex_fury_mt4_targets():
    report = load_external_benchmark_report()

    assert report["report_kind"] == "cas_forex_external_benchmark_snapshot"
    assert report["summary"]["benchmark_count"] == 3
    assert report["summary"]["mt4_account_count"] == 3
    assert report["summary"]["real_account_count"] == 3
    assert report["summary"]["symbols"] == ["AUDUSD", "GBPUSD", "USDCAD"]
    assert report["summary"]["total_public_trade_count"] == 646
    assert any("MT4 mailbox bridge" in target for target in report["implementation_targets"])
    assert any("private" in limitation.lower() for limitation in report["source_limitations"])
    assert "does not create broker ACCEPT" in report["claim_boundary"]


def test_external_benchmarks_route_and_dashboard_surface_snapshot():
    status, body = asyncio.run(_asgi_get("/api/forex/strategy/external-benchmarks"))
    assert status == 200
    assert body["summary"]["benchmark_count"] == 3
    assert body["benchmarks"][0]["public_account_descriptor"].endswith("MetaTrader 4")

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert "externalBenchmarks" in dashboard
    assert dashboard["externalBenchmarks"]["summary"]["mt4_account_count"] == 3
    assert dashboard["externalBenchmarks"]["claim_boundary"].startswith("External benchmark snapshot only")
