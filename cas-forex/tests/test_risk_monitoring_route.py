"""ASGI tests for the /api/forex/risk-monitoring/portfolio route.

The route is not yet wired into `api/server.py` (parent agent integrates),
so we mount the router on a fresh FastAPI instance under the production
prefix. This validates handler, loader injection, and JSON schema in
isolation without depending on the rest of the API surface.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI

from api.routes import risk_monitoring as route_module


@pytest.fixture
def app():
    """Fresh app per test, with the router mounted at the production prefix."""
    a = FastAPI()
    a.include_router(
        route_module.router,
        prefix="/api/forex/risk-monitoring",
        tags=["risk-monitoring"],
    )
    return a


@pytest.fixture(autouse=True)
def _reset_loader_between_tests():
    route_module.reset_loader_for_testing()
    yield
    route_module.reset_loader_for_testing()


async def _asgi_get(app, path: str) -> tuple[int, Any]:
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


def test_route_returns_200_and_empty_snapshot_when_no_inputs(app):
    route_module.set_loader_for_testing(
        lambda: {"live_telemetry": None, "account_snapshot": None}
    )
    status, payload = asyncio.run(_asgi_get(app, "/api/forex/risk-monitoring/portfolio"))
    assert status == 200
    assert payload["open_position_count"] == 0
    assert payload["total_exposure_lots"] == 0.0
    assert payload["by_symbol"] == []
    assert payload["largest_symbol_exposure"] is None
    assert payload["margin_utilization_pct"] is None
    assert payload["telemetry_source"] == "none"
    assert payload["position_feed_label"] == "NONE"
    assert payload["movement_source_truth"]["movement_stream_present"] is False
    assert payload["movement_source_truth"]["position_feed_label"] == "NONE"
    assert "no open positions" in payload["plain_english_summary"].lower()


def test_route_returns_200_with_populated_payload_when_loader_provides_inputs(app):
    route_module.set_loader_for_testing(lambda: {
        "live_telemetry": {
            "open_positions": [
                {"symbol": "EURUSD", "direction": "BUY", "lots": 0.5, "floating_pnl": 12.0, "broker_ticket": None, "price_source": "paper_route_snapshot:static_simulation", "price_stale": True, "position_source_label": "PAPER_SIM_STATIC"},
                {"symbol": "GBPUSD", "direction": "SELL", "lots": 0.25, "floating_pnl": -3.0, "broker_ticket": None, "price_source": "paper_route_snapshot:static_simulation", "price_stale": True, "position_source_label": "PAPER_SIM_STATIC"},
            ],
            "data_freshness": {
                "source": "movement_stream",
                "stale": False,
                "last_update_iso": "2026-06-25T12:00:00+00:00",
                "movement_source": {"price_source_status": "STATIC_SIMULATION_FALLBACK"},
            },
        },
        "account_snapshot": {
            "balance": 10000.0,
            "equity": 10009.0,
            "margin": 200.0,
            "free_margin": 9809.0,
        },
    })
    status, payload = asyncio.run(_asgi_get(app, "/api/forex/risk-monitoring/portfolio"))
    assert status == 200
    assert payload["open_position_count"] == 2
    assert payload["total_exposure_lots"] == pytest.approx(0.75)
    assert len(payload["by_symbol"]) == 2
    assert payload["by_symbol"][0]["symbol"] == "EURUSD"  # largest first
    assert payload["largest_symbol_exposure"]["symbol"] == "EURUSD"
    assert payload["account_equity"] == pytest.approx(10009.0)
    assert payload["margin_utilization_pct"] is not None
    assert payload["telemetry_source"] == "movement_stream"
    assert payload["price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert payload["position_feed_label"] == "SIM PROOF"
    assert payload["static_position_count"] == 2
    assert payload["movement_source_truth"]["price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert payload["movement_source_truth"]["position_feed_label"] == "SIM PROOF"
    assert payload["movement_source_truth"]["static_position_count"] == 2
    assert payload["movement_source_truth"]["detail"] == payload["position_feed_detail"]


def test_route_preserves_canonical_position_feed_detail(app):
    detail = (
        "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions. "
        "Static simulator fallback is active for 1/1 row(s), so prices and floating P&L can remain at entry "
        "until usable provider or MT5 quotes arrive. Requested provider: Yahoo. Static fallback symbols: NAS100. "
        "Stale provider/MT5 snapshots were rejected for: NAS100 (max age 900s)."
    )
    route_module.set_loader_for_testing(lambda: {
        "live_telemetry": {
            "open_positions": [
                {
                    "symbol": "NAS100",
                    "direction": "BUY",
                    "lots": 0.1,
                    "floating_pnl": 0.0,
                    "broker_ticket": None,
                    "price_source": "paper_route_snapshot:static_simulation",
                    "price_stale": True,
                    "position_source_label": "PAPER_SIM_STATIC",
                }
            ],
            "position_feed_label": "SIM PROOF",
            "position_feed_detail": detail,
            "data_freshness": {
                "source": "movement_stream",
                "stale": False,
                "last_update_iso": "2026-06-25T12:00:00+00:00",
                "movement_source": {
                    "price_source_status": "STATIC_SIMULATION_FALLBACK",
                },
            },
        },
        "account_snapshot": None,
    })

    status, payload = asyncio.run(_asgi_get(app, "/api/forex/risk-monitoring/portfolio"))

    assert status == 200
    assert payload["position_feed_label"] == "SIM PROOF"
    assert payload["position_feed_detail"] == detail
    assert "Stale provider/MT5 snapshots were rejected for: NAS100 (max age 900s)." in payload["position_feed_detail"]


def test_route_payload_has_all_required_top_level_keys(app):
    route_module.set_loader_for_testing(
        lambda: {"live_telemetry": None, "account_snapshot": None}
    )
    _, payload = asyncio.run(_asgi_get(app, "/api/forex/risk-monitoring/portfolio"))
    required = {
        "snapshot_at_iso",
        "open_position_count",
        "total_floating_pnl",
        "total_exposure_lots",
        "largest_symbol_exposure",
        "largest_floating_pnl_loss",
        "largest_floating_pnl_gain",
        "by_symbol",
        "concentration_pct",
        "account_balance",
        "account_equity",
        "account_margin",
        "account_free_margin",
        "margin_utilization_pct",
        "telemetry_source",
        "telemetry_stale",
        "telemetry_last_update_iso",
        "price_source_status",
        "position_feed_label",
        "position_feed_detail",
        "broker_ticket_position_count",
        "static_position_count",
        "movement_source_truth",
        "plain_english_summary",
        "diagnostic_hints",
    }
    missing = required - set(payload.keys())
    assert not missing, f"missing keys in route payload: {missing}"


def test_route_payload_serializes_as_clean_json(app):
    route_module.set_loader_for_testing(lambda: {
        "live_telemetry": {
            "open_positions": [
                {"symbol": "EURUSD", "direction": "BUY", "lots": 1.0, "floating_pnl": 50.0},
            ]
        },
        "account_snapshot": {
            "balance": 10000.0,
            "equity": 10050.0,
            "margin": 100.0,
            "free_margin": 9950.0,
        },
    })
    _, payload = asyncio.run(_asgi_get(app, "/api/forex/risk-monitoring/portfolio"))
    # Round-trip through JSON unchanged.
    round_tripped = json.loads(json.dumps(payload))
    assert round_tripped == payload
    assert isinstance(payload["by_symbol"], list)
    assert isinstance(payload["diagnostic_hints"], list)
    assert isinstance(payload["by_symbol"][0], dict)


def test_route_default_loader_is_callable_without_arguments():
    """Smoke test: the default disk-backed loader must not raise on call,
    even when no evidence exists on disk. Returns dict with both keys."""
    result = route_module._default_loader()
    assert isinstance(result, dict)
    assert "live_telemetry" in result
    assert "account_snapshot" in result
