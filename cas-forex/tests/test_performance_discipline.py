from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI

from api.routes import strategy_comparison as route_module
from cas_forex.performance_discipline import build_performance_discipline_report


REPO_ROOT = Path(__file__).resolve().parents[1]


def _rich_lead(**overrides):
    base = {
        "lead_id": "rich-lead",
        "net_return_after_costs_pct": 12.4,
        "spread_pips": 0.8,
        "slippage_pips": 0.2,
        "commission_usd": -14.0,
        "swap_usd": -2.0,
        "max_drawdown_pct": 4.2,
        "total_trades": 180,
        "win_rate_pct": 54.0,
        "profit_factor": 1.7,
        "average_r_multiple": 0.34,
        "walk_forward_grade": "WALK_FORWARD_LEAD",
        "account_mode": "BACKTEST",
        "sharpe_ratio": 1.2,
        "sortino_ratio": 1.7,
        "worst_day_usd": -88.0,
        "monte_carlo_drawdown": 8.0,
    }
    base.update(overrides)
    return base


def test_performance_discipline_ok_when_critical_fields_are_present():
    report = build_performance_discipline_report(strategy_leads=[_rich_lead()])

    assert report["report_kind"] == "cas_forex_performance_discipline"
    assert report["status"] == "OK"
    assert report["record_count"] == 1
    row = report["records"][0]
    assert row["strategy_id"] == "rich-lead"
    assert row["status"] == "OK"
    assert row["cost_model_present"] is True
    assert row["out_of_sample_present"] is True
    assert row["mode_separation_present"] is True
    assert row["critical_missing"] == []


def test_performance_discipline_surfaces_missing_cost_and_oos_fields():
    report = build_performance_discipline_report(
        strategy_leads=[
            {
                "lead_id": "thin-lead",
                "profit_factor": 1.8,
                "max_drawdown_pct": 6.0,
                "total_trades": 40,
            }
        ]
    )

    assert report["status"] == "ATTENTION"
    row = report["records"][0]
    assert row["critical_missing_count"] > 0
    assert "cost_model" in row["critical_missing"]
    assert "out_of_sample" in row["critical_missing"]
    assert any("thin-lead" in hint for hint in report["diagnostic_hints"])


def test_performance_discipline_mode_separation_uses_loaded_source():
    report = build_performance_discipline_report(
        strategy_dev_queue_items=[
            {
                "work_item_id": "source-only-mode",
                "net_pnl_usd": 100,
                "spread_pips": 1.0,
                "max_drawdown_pct": 3,
                "total_trades": 20,
                "profit_factor": 1.4,
                "walk_forward_grade": "WATCH",
            }
        ]
    )

    row = report["records"][0]
    assert row["mode_separation_present"] is True
    assert row["mode_label"] == "RESEARCH/BACKTEST"


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(
        route_module.router,
        prefix="/api/forex/strategy-comparison",
        tags=["strategy-comparison"],
    )
    return app


async def _asgi_get(app: FastAPI, path: str) -> tuple[int, Any]:
    body_sent = False

    async def receive() -> dict[str, Any]:
        nonlocal body_sent
        if body_sent:
            return {"type": "http.disconnect"}
        body_sent = True
        return {"type": "http.request", "body": b"", "more_body": False}

    sent: list[dict[str, Any]] = []

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
    out = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    parsed_body = json.loads(out.decode("utf-8")) if out else None
    return int(status), parsed_body


def test_strategy_comparison_performance_discipline_route(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "_LOADER",
        lambda: {
            "fury_candidates": None,
            "strategy_leads": [_rich_lead()],
            "strategy_dev_queue_items": None,
        },
    )

    status, body = asyncio.run(
        _asgi_get(_build_app(), "/api/forex/strategy-comparison/performance-discipline?limit=10")
    )

    assert status == 200
    assert body["report_kind"] == "cas_forex_performance_discipline"
    assert body["status"] == "OK"
    assert body["records"][0]["strategy_id"] == "rich-lead"
    assert "past" in body["claim_boundary"].lower()


def test_strategy_comparison_page_exposes_performance_discipline_panel():
    page = (REPO_ROOT / "ui" / "src" / "pages" / "StrategyComparisonPage.tsx").read_text(encoding="utf-8")
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert "fetchPerformanceDiscipline" in page
    assert "Performance Discipline" in page
    assert "cost_model_present" in page
    assert "mode_separation_present" in page
    assert "Mode Sep" in page
    assert "PerformanceDisciplineReport" in api_client
    assert "strategy-comparison/performance-discipline" in api_client
