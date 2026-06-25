"""ASGI tests for /api/forex/strategy-comparison routes.

These tests register the router on a fresh FastAPI app and inject a
fake sources loader so no real evidence_runs/ files are touched.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI

from api.routes import strategy_comparison as route_module


FORBIDDEN_PHRASES = [
    "you should pick",
    "pick a",
    "pick b",
    "is a better trade",
    "we recommend",
    "good choice",
    "is the winner",
    "go with",
    "should buy",
    "should sell",
]


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


@pytest.fixture(autouse=True)
def _reset_loader_between_tests():
    route_module.reset_loader_for_testing()
    yield
    route_module.reset_loader_for_testing()


def _install_sources(
    *,
    fury_candidates=None,
    strategy_leads=None,
    strategy_dev_queue_items=None,
    fury_imported_at="2026-06-24T04:08:20+00:00",
    leads_imported_at="2026-06-22",
    dev_queue_imported_at="2026-06-24T10:29:00+00:00",
) -> None:
    payload = {
        "fury_candidates": fury_candidates,
        "fury_imported_at": fury_imported_at,
        "strategy_leads": strategy_leads,
        "leads_imported_at": leads_imported_at,
        "strategy_dev_queue_items": strategy_dev_queue_items,
        "dev_queue_imported_at": dev_queue_imported_at,
    }
    route_module.set_loader_for_testing(lambda: payload)


def _fury_candidate(candidate_id="ff-1", **overrides):
    base = {
        "candidate_id": candidate_id,
        "cas_symbol": "AUD/CAD",
        "family": "swing",
        "evidence": {
            "profit_factor": 3.0,
            "equity_drawdown_relative_pct": 5.0,
            "total_trades": 200,
            "history_quality": "98%",
        },
        "replay_job": {"timeframes": ["M5"]},
        "walk_forward_grade": "WATCH",
    }
    base.update(overrides)
    return base


def _strategy_lead(lead_id="lead-1", **overrides):
    base = {
        "lead_id": lead_id,
        "family": "range_scalper",
        "symbols_promoted_for_next_tests": ["EUR/USD"],
        "condition_fit": {"preferred_timeframes": ["D1"]},
        "profit_factor": 1.6,
        "equity_drawdown_pct": 3.0,
        "walk_forward_grade": "WALK_FORWARD_LEAD",
        "total_trades": 80,
    }
    base.update(overrides)
    return base


def _dev_queue_item(work_item_id="wi-1", **overrides):
    base = {
        "work_item_id": work_item_id,
        "families": ["forex_fury"],
        "symbols": ["EUR/USD"],
        "timeframes": ["H1"],
        "profit_factor": 2.0,
        "equity_drawdown_pct": 6.0,
        "walk_forward_grade": "WATCH",
        "total_trades": 40,
    }
    base.update(overrides)
    return base


def test_ranked_returns_top_n_with_summary_and_diagnostics():
    _install_sources(
        fury_candidates=[_fury_candidate("ff-1"), _fury_candidate("ff-2", evidence={"profit_factor": 1.1})],
        strategy_leads=[_strategy_lead("lead-1")],
        strategy_dev_queue_items=[_dev_queue_item("wi-1")],
    )
    app = _build_app()
    status, body = asyncio.run(_asgi_get(app, "/api/forex/strategy-comparison/ranked?limit=2"))
    assert status == 200, body
    assert body["limit"] == 2
    assert body["record_count"] == 4
    assert body["returned_count"] == 2
    assert isinstance(body["plain_english_summary"], str) and body["plain_english_summary"]
    assert isinstance(body["diagnostic_hints"], list)
    # Each record carries the unified shape.
    rec0 = body["records"][0]
    for key in (
        "strategy_id",
        "source",
        "composite_score",
        "composite_rank",
        "metrics",
        "profit_factor",
    ):
        assert key in rec0


def test_ranked_default_limit_is_twenty():
    _install_sources(strategy_leads=[_strategy_lead(f"l-{i}") for i in range(25)])
    app = _build_app()
    status, body = asyncio.run(_asgi_get(app, "/api/forex/strategy-comparison/ranked"))
    assert status == 200
    assert body["limit"] == 20
    assert body["returned_count"] == 20
    assert body["record_count"] == 25


def test_diff_returns_field_diffs_and_match_flags():
    _install_sources(
        strategy_leads=[
            _strategy_lead("lead-a", profit_factor=2.0, family="range_scalper"),
            _strategy_lead("lead-b", profit_factor=3.5, family="meanrev"),
        ]
    )
    app = _build_app()
    status, body = asyncio.run(
        _asgi_get(
            app,
            "/api/forex/strategy-comparison/diff?strategy_id_a=lead-a&strategy_id_b=lead-b",
        )
    )
    assert status == 200, body
    fields = [d["field"] for d in body["field_diffs"]]
    assert "profit_factor" in fields
    assert "family" in fields
    assert body["family_match"] is False
    assert body["symbol_match"] is True  # both default to EUR/USD
    assert body["plain_english_diff"]


def test_diff_missing_id_returns_400_with_missing_ids_list():
    _install_sources(strategy_leads=[_strategy_lead("lead-a")])
    app = _build_app()
    status, body = asyncio.run(
        _asgi_get(
            app,
            "/api/forex/strategy-comparison/diff?strategy_id_a=lead-a&strategy_id_b=nope",
        )
    )
    assert status == 400, body
    detail = body["detail"]
    assert detail["error"] == "strategy_id_not_found"
    assert detail["missing_ids"] == ["nope"]


def test_ranked_text_never_contains_forbidden_phrases():
    _install_sources(
        fury_candidates=[_fury_candidate("ff-1")],
        strategy_leads=[_strategy_lead("lead-1"), {"lead_id": "bare"}],
        strategy_dev_queue_items=[_dev_queue_item("wi-1")],
    )
    app = _build_app()
    status, body = asyncio.run(_asgi_get(app, "/api/forex/strategy-comparison/ranked?limit=10"))
    assert status == 200
    combined = (body["plain_english_summary"] + " | " + " | ".join(body["diagnostic_hints"])).lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in combined, f"phrase {phrase!r} leaked into ranked text: {combined!r}"


def test_diff_text_never_contains_forbidden_phrases():
    _install_sources(
        strategy_leads=[
            _strategy_lead("lead-a", profit_factor=2.0),
            _strategy_lead("lead-b", profit_factor=4.5, equity_drawdown_pct=20.0),
        ]
    )
    app = _build_app()
    status, body = asyncio.run(
        _asgi_get(
            app,
            "/api/forex/strategy-comparison/diff?strategy_id_a=lead-a&strategy_id_b=lead-b",
        )
    )
    assert status == 200
    text = body["plain_english_diff"].lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in text, f"phrase {phrase!r} leaked into diff text: {text!r}"
