"""Forex Fury replay-result summary coverage."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

from api.server import app
from cas_forex.forex_fury_replay_results import build_forex_fury_replay_results


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


def test_forex_fury_replay_results_promote_strong_walk_forward_to_adaptive_review():
    report = build_forex_fury_replay_results(
        candidate_report={
            "report_kind": "cas_forex_forex_fury_replay_candidates",
            "summary": {"candidate_count": 1, "top_candidate_id": "ff-replay-test"},
        },
        condition_report={
            "run_id": "condition-lab-test",
            "source": "both",
            "symbols": ["AUD/CAD"],
            "nested_lacunarity": {"overall": 0.2},
            "rpm_routes": {
                "k": {"action": "ROUTE"},
                "n": {"action": "NO_TRADE"},
            },
            "cells": [
                {
                    "source": "real",
                    "symbol": "AUD/CAD",
                    "timeframe": "M5",
                    "event_context": "normal",
                    "regime": "shock",
                    "vol_mult": 1.0,
                    "setting": "range_scalper_12_80",
                    "family": "range_scalper",
                    "mean_return_pct": 1.2,
                    "mean_max_dd_pct": 0.0,
                    "mean_trades": 36.0,
                    "win_rate": 0.97,
                    "profit_factor": 20.0,
                    "region": "active",
                    "beta": 5.1,
                    "score": 5.0,
                    "is_gap": False,
                }
            ],
        },
        walk_forward_report={
            "run_id": "walk-forward-test",
            "combined_summary": {
                "windows": 20,
                "routed_windows": 12,
                "positive_routed_windows": 8,
                "positive_routed_window_rate": 0.6667,
                "routed_max_drawdown_pct": 0.5,
                "routed_total_trades": 80,
                "research_grade": "WALK_FORWARD_LEAD",
            },
        },
    )

    assert report["replay_verdict"] == "REPLAY_LEAD_FOR_ADAPTIVE_REVIEW"
    assert report["adaptive_compounding_next_step"] == "QUEUE_FOR_ADAPTIVE_COMPOUNDING_REVIEW"
    assert report["condition_summary"]["route_count"] == 1
    assert report["condition_summary"]["no_trade_route_count"] == 1
    assert report["condition_summary"]["top_condition_cells"][0]["setting"] == "range_scalper_12_80"
    assert "do not execute EA binaries" in report["claim_boundary"]


def test_forex_fury_replay_results_route_and_dashboard_surface_latest_report():
    status, body = asyncio.run(_asgi_get("/api/forex/strategy/forex-fury-replay-results"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_forex_fury_replay_results"
    assert body["walk_forward_summary"]["research_grade"] == "WALK_FORWARD_LEAD"
    assert body["replay_verdict"] == "REPLAY_LEAD_FOR_ADAPTIVE_REVIEW"

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert "forexFuryReplayResults" in dashboard
    assert dashboard["forexFuryReplayResults"]["adaptive_compounding_next_step"] == "QUEUE_FOR_ADAPTIVE_COMPOUNDING_REVIEW"

