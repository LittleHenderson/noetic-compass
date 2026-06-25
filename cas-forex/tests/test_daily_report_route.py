"""ASGI tests for /api/forex/daily-report routes.

The router is mounted on a local FastAPI app so the parent ``api.server``
integration is not a prerequisite. Loader-injection (``set_loader_for_testing``)
keeps tests fully deterministic.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI

from api.routes import daily_report as route_module


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/daily-report")
    return app


async def _asgi_get(app: FastAPI, path: str) -> tuple[int, Any]:
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
    payload = json.loads(body.decode("utf-8")) if body else None
    return int(status), payload


@pytest.fixture(autouse=True)
def _reset_loader_between_tests():
    route_module.reset_loader_for_testing()
    yield
    route_module.reset_loader_for_testing()


def _empty_loader(_date: str) -> dict[str, Any]:
    return {
        "daily_rollup": None,
        "cycle_reports": None,
        "event_journal": None,
        "live_telemetry_snapshots": None,
        "risk_snapshots": None,
        "system_health_snapshots": None,
    }


def _rich_loader(date: str) -> dict[str, Any]:
    return {
        "daily_rollup": {
            "by_strategy": [
                {
                    "key": "alpha_strategy",
                    "closed_count": 2,
                    "net_profit_loss_account": 19.0,
                }
            ]
        },
        "cycle_reports": [
            {
                "cycle_id": f"cy-{date}",
                "overseer_decisions": [
                    {
                        "approved": True,
                        "command_ready": True,
                        "decision": "APPROVE_ROUTE_INTENT",
                        "reasons": [],
                    }
                ],
            }
        ],
        "event_journal": [
            {
                "event_type": "STRATEGY_PROMOTED",
                "created_at": f"{date}T01:00:00+00:00",
                "payload": {"strategy": "alpha_strategy"},
            }
        ],
        "live_telemetry_snapshots": [
            {"totals": {"open_position_count": 1, "total_floating_pnl": 4.5}}
        ],
        "risk_snapshots": [
            {
                "peak_concentration": 0.20,
                "peak_margin_utilization": 0.10,
                "max_floating_loss": -3.0,
                "max_floating_gain": 4.5,
            }
        ],
        "system_health_snapshots": [
            {"uvicorn_up": True, "autowake_up": True, "mt5_disconnected": False}
        ],
    }


def test_today_route_returns_200_with_today_date():
    route_module.set_loader_for_testing(_empty_loader)
    app = _make_app()
    status, body = asyncio.run(_asgi_get(app, "/api/forex/daily-report/today"))
    assert status == 200
    expected = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert body["report_date"] == expected
    assert "no activity" in body["overall_headline"].lower()


def test_date_route_returns_200_for_custom_date():
    route_module.set_loader_for_testing(_rich_loader)
    app = _make_app()
    status, body = asyncio.run(_asgi_get(app, "/api/forex/daily-report/2026-06-25"))
    assert status == 200
    assert body["report_date"] == "2026-06-25"
    section_names = [s["section_name"] for s in body["sections"]]
    assert section_names == [
        "cycles",
        "decisions",
        "executions",
        "strategies",
        "risk",
        "system",
        "incidents",
    ]


def test_payload_has_all_required_top_level_keys():
    route_module.set_loader_for_testing(_rich_loader)
    app = _make_app()
    _, body = asyncio.run(_asgi_get(app, "/api/forex/daily-report/2026-06-25"))
    required = {
        "report_date",
        "generated_at_iso",
        "overall_headline",
        "plain_english_summary",
        "sections",
        "diagnostic_hints",
    }
    assert required.issubset(set(body.keys()))


def test_invalid_date_returns_400():
    route_module.set_loader_for_testing(_empty_loader)
    app = _make_app()
    status, body = asyncio.run(
        _asgi_get(app, "/api/forex/daily-report/not-a-date")
    )
    assert status == 400


def test_payload_summary_has_no_advisory_phrase():
    route_module.set_loader_for_testing(_rich_loader)
    app = _make_app()
    _, body = asyncio.run(_asgi_get(app, "/api/forex/daily-report/2026-06-25"))
    summary = body["plain_english_summary"].lower()
    headline = body["overall_headline"].lower()
    forbidden = [
        "you should",
        "should have",
        "we recommend",
        "next time you should",
        "consider closing",
        "consider taking",
        "consider buying",
        "consider selling",
        "is a good",
        "would have been better",
    ]
    for phrase in forbidden:
        assert phrase not in summary, f"advisory phrase in summary: {phrase!r}"
        assert phrase not in headline, f"advisory phrase in headline: {phrase!r}"
