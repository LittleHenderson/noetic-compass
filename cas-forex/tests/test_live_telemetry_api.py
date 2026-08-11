"""Tests for the /api/forex/live-telemetry route.

Drives the FastAPI ASGI app directly (same pattern as
``tests/test_timeframes_api.py``) and patches the route's evidence
collectors so we control upstream shape without touching real evidence
files. The route MUST never fabricate prices or PnL when no data exists.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import pytest

from api.server import app
from api.routes import live_telemetry as lt_route

_ORIGINAL_COLLECT_FROM_MOVEMENT_STREAM = lt_route._collect_from_movement_stream
_ORIGINAL_COLLECT_FROM_MT5_TERMINAL = lt_route._collect_from_mt5_terminal


async def _asgi(path: str, *, method: str = "GET") -> tuple[int, Any]:
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
        "method": method,
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
def _empty_sources(monkeypatch: pytest.MonkeyPatch):
    """Default to no live evidence; individual tests opt in to mocked data."""
    monkeypatch.setattr(lt_route, "_collect_from_mt5_terminal", lambda: None)
    monkeypatch.setattr(lt_route, "_collect_from_movement_stream", lambda: None)
    yield


# ---------------------------------------------------------------------------


def test_endpoint_registered_and_returns_200():
    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert isinstance(body, dict)


def test_http_cache_does_not_outlive_mt5_mirror_cadence():
    assert lt_route.LIVE_TELEMETRY_CACHE_TTL_SECONDS <= 4.0


def test_http_cache_blocks_on_cold_before_returning_zero_positions(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, Any] = {}

    def fake_cache_first_payload(key: str, **kwargs: Any) -> dict[str, Any]:
        captured["key"] = key
        captured.update(kwargs)
        return {"telemetry_source": "mt5_demo_account_snapshot"}

    monkeypatch.setattr(lt_route, "cache_first_payload", fake_cache_first_payload)

    body = asyncio.run(lt_route.get_live_telemetry())

    assert body["telemetry_source"] == "mt5_demo_account_snapshot"
    assert captured["key"] == "live_telemetry"
    assert captured["block_on_cold"] is True


def test_cached_none_is_rechecked_when_mt5_becomes_available(monkeypatch: pytest.MonkeyPatch):
    mt5_payload = {
        "telemetry_source": "mt5_demo_account_snapshot",
        "totals": {"open_position_count": 7},
    }
    stored: dict[str, Any] = {}
    monkeypatch.setattr(
        lt_route,
        "cache_first_payload",
        lambda *args, **kwargs: {"telemetry_source": "none"},
    )
    monkeypatch.setattr(lt_route, "collect_live_telemetry", lambda: mt5_payload)
    monkeypatch.setattr(
        lt_route,
        "store_cache_payload",
        lambda key, payload: stored.update({"key": key, "payload": payload}),
    )
    monkeypatch.setattr(
        lt_route,
        "cached_payload_snapshot",
        lambda *args, **kwargs: {**mt5_payload, "cache_status": "fresh"},
    )

    body = asyncio.run(lt_route.get_live_telemetry())

    assert body["telemetry_source"] == "mt5_demo_account_snapshot"
    assert body["totals"]["open_position_count"] == 7
    assert stored == {"key": "live_telemetry", "payload": mt5_payload}


def test_response_schema_has_all_required_fields():
    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert set(body.keys()) >= {
        "as_of_iso",
        "open_positions",
        "totals",
        "telemetry_source",
        "telemetry_stale",
        "telemetry_last_update_iso",
        "price_source_status",
        "position_feed_label",
        "position_feed_detail",
        "broker_ticket_position_count",
        "static_position_count",
        "movement_source_truth",
        "data_freshness",
    }
    assert set(body["totals"].keys()) >= {"open_position_count", "total_floating_pnl"}
    assert set(body["data_freshness"].keys()) >= {"source", "stale", "last_update_iso"}
    assert "movement_source" in body["data_freshness"]


def test_no_live_evidence_returns_none_source_and_stale():
    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert body["open_positions"] == []
    assert body["totals"]["open_position_count"] == 0
    assert body["totals"]["total_floating_pnl"] == 0.0
    assert body["telemetry_source"] == "none"
    assert body["telemetry_stale"] is True
    assert body["telemetry_last_update_iso"] is None
    assert body["position_feed_label"] == "NONE"
    assert "No broker or paper/demo movement snapshot" in body["position_feed_detail"]
    assert body["broker_ticket_position_count"] == 0
    assert body["static_position_count"] == 0
    assert body["movement_source_truth"]["movement_stream_present"] is False
    assert body["movement_source_truth"]["position_feed_label"] == "NONE"
    assert body["data_freshness"]["source"] == "none"
    assert body["data_freshness"]["stale"] is True
    assert body["data_freshness"]["last_update_iso"] is None


def test_current_mt5_account_snapshot_outranks_exported_verifier_evidence(monkeypatch: pytest.MonkeyPatch):
    snapshot = {
        "connected": True,
        "is_demo": True,
        "snapshot_observed_at": "2026-07-11T10:00:00+00:00",
        "snapshot_age_seconds": 1.25,
        "snapshot_fresh": True,
        "cached": True,
        "account": {"login": 1000694, "server": "Hugosway-Demo"},
        "positions": [
            {
                "ticket": 45944855,
                "symbol": "US30",
                "side": "SHORT",
                "lots": 0.01,
                "open_price": 52597.82,
                "current_price": 52695.39,
                "floating_pnl_usd": -97.57,
                "swap_usd": -7.60,
                "stop_loss": 52734.75,
                "take_profit": 52374.18,
                "risk_at_stop_usd": 136.93,
            }
        ],
        "position_protection": {"status": "ALL_POSITIONS_PROTECTED"},
        "position_risk": {"status": "POSITION_RISK_CAP_BREACH", "risk_cap_breach_count": 1},
    }
    monkeypatch.setattr(lt_route, "get_mt5_account_snapshot", lambda: snapshot)

    result = _ORIGINAL_COLLECT_FROM_MT5_TERMINAL()

    assert result is not None
    positions, observed_at, context = result
    assert observed_at == snapshot["snapshot_observed_at"]
    assert context["telemetry_source"] == "mt5_demo_account_snapshot"
    assert context["account_mode"] == "DEMO"
    assert context["account_login"] == 1000694
    assert positions[0]["position_source_label"] == "MT5_DEMO_BROKER"
    assert positions[0]["floating_pnl"] == -97.57
    assert positions[0]["swap"] == -7.60
    assert positions[0]["net_open_pnl"] == -105.17
    assert positions[0]["risk_at_stop_usd"] == 136.93

    payload = lt_route._build_payload(
        positions,
        context["telemetry_source"],
        observed_at,
        source_context=context,
    )
    assert payload["telemetry_source"] == "mt5_demo_account_snapshot"
    assert payload["position_feed_label"] == "MT5 DEMO"
    assert "current MT5 demo broker positions" in payload["position_feed_detail"]
    assert payload["totals"]["open_position_count"] == 1
    assert payload["totals"]["gross_floating_pnl"] == -97.57
    assert payload["totals"]["total_swap"] == -7.60
    assert payload["totals"]["total_open_pnl_after_costs"] == -105.17
    assert payload["totals"]["total_floating_pnl"] == -105.17
    assert payload["movement_source_truth"]["account_login"] == 1000694


def test_mocked_paper_evidence_echoed_with_correct_totals(monkeypatch: pytest.MonkeyPatch):
    """When canonical mt5-terminal evidence is missing, fall back to the
    paper/demo movement stream and surface those positions verbatim."""
    paper_positions = [
        {
            "symbol": "EURUSD",
            "side": "LONG",
            "lot_size": 0.01,
            "open_price": 1.0850,
            "current_price": 1.0855,
            "floating_pnl_usd": 0.50,
            "broker_ticket": "P-100",
        },
        {
            "symbol": "GBPUSD",
            "side": "SHORT",
            "lot_size": 0.02,
            "open_price": 1.2700,
            "current_price": 1.2680,
            "floating_pnl_usd": 4.00,
            "broker_ticket": None,
        },
    ]
    from cas_forex.time_utils import utc_now

    fresh_ts = utc_now().isoformat()
    monkeypatch.setattr(
        lt_route,
        "_collect_from_movement_stream",
        lambda: (
            [lt_route._normalize_paper_position(p) for p in paper_positions],
            fresh_ts,
        ),
    )

    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert body["telemetry_source"] == "movement_stream"
    assert body["telemetry_stale"] is False
    assert body["position_feed_label"] == "SIM PROOF"
    assert body["broker_ticket_position_count"] == 1
    assert body["data_freshness"]["source"] == "movement_stream"
    assert body["data_freshness"]["stale"] is False
    assert body["totals"]["open_position_count"] == 2
    symbols = {row["symbol"] for row in body["open_positions"]}
    assert symbols == {"EURUSD", "GBPUSD"}


def test_live_telemetry_surfaces_movement_source_summary(monkeypatch: pytest.MonkeyPatch):
    paper_positions = [
        {
            "symbol": "NAS100",
            "side": "LONG",
            "lot_size": 0.01,
            "open_price": 29173.02,
            "current_price": 29173.02,
            "floating_pnl_usd": 0.0,
            "broker_ticket": None,
        }
    ]
    from cas_forex.time_utils import utc_now

    fresh_ts = utc_now().isoformat()
    monkeypatch.setattr(
        lt_route,
        "_collect_from_movement_stream",
        lambda: (
            [lt_route._normalize_paper_position(p) for p in paper_positions],
            fresh_ts,
            {
                "movement_stream_present": True,
                "telemetry_source": "movement_stream",
                "telemetry_stale": False,
                "telemetry_last_update_iso": fresh_ts,
                "price_source_status": "STATIC_SIMULATION_FALLBACK",
                "price_source_label": "STATIC SIM",
                "price_source_summary": "Static simulation only: paper/demo rows are not being repriced by usable provider or MT5 quotes right now.",
                "price_source_warning": "Static simulator rows are not being moved by usable provider/MT5 quotes right now; prices and floating P/L can remain unchanged at entry.",
                "position_feed_label": "SIM PROOF",
                "position_feed_detail": "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions. Static simulator fallback is active for 1/1 row(s), so prices and floating P&L can remain at entry until usable provider or MT5 quotes arrive. Requested provider: Yahoo. Static fallback symbols: NAS100. Stale provider/MT5 snapshots were rejected for: NAS100 (max age 900s).",
                "static_simulation_active": True,
                "market_data_provider_requested": True,
                "configured_market_data_provider": "YFinanceConnector",
                "provider_usable_symbols": [],
                "static_fallback_symbols": ["NAS100"],
                "mt5_fallback_symbols": [],
                "closed_market_symbols": ["NAS100"],
                "closed_market_quote_count": 1,
                "unsupported_provider_symbols": ["NAS100"],
                "provider_stale_symbols": ["NAS100"],
                "provider_freshness_max_age_seconds": 900,
                "static_quote_count": 1,
                "snapshot_age_seconds_by_symbol": {"NAS100": 960},
                "provider_errors": {"NAS100": "YFinanceConnector: snapshot marked market closed for movement pricing"},
                "snapshot_source_by_symbol": {"NAS100": "static_simulation"},
            },
        ),
    )

    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert body["price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert body["position_feed_label"] == "SIM PROOF"
    assert "Static simulator fallback is active for 1/1 row(s)" in body["position_feed_detail"]
    assert "Stale provider/MT5 snapshots were rejected for: NAS100 (max age 900s)." in body["position_feed_detail"]
    assert body["broker_ticket_position_count"] == 0
    assert body["static_position_count"] == 1
    assert body["movement_source_truth"]["price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert body["movement_source_truth"]["position_feed_label"] == "SIM PROOF"
    assert body["movement_source_truth"]["static_position_count"] == 1
    assert body["movement_source_truth"]["static_quote_count"] == 1
    assert body["movement_source_truth"]["closed_market_symbols"] == ["NAS100"]
    assert body["movement_source_truth"]["closed_market_quote_count"] == 1
    assert body["movement_source_truth"]["unsupported_provider_symbols"] == ["NAS100"]
    assert body["movement_source_truth"]["detail"] == body["position_feed_detail"]
    assert body["data_freshness"]["source"] == "movement_stream"
    assert body["data_freshness"]["movement_source"]["price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert body["data_freshness"]["movement_source"]["price_source_label"] == "STATIC SIM"
    assert body["data_freshness"]["movement_source"]["static_simulation_active"] is True
    assert "Static simulation" in body["data_freshness"]["movement_source"]["price_source_summary"]
    assert "Static simulator rows are not being moved by usable provider/MT5 quotes right now" in body["data_freshness"]["movement_source"]["price_source_warning"]
    assert body["data_freshness"]["movement_source"]["position_feed_label"] == "SIM PROOF"
    assert "Stale provider/MT5 snapshots were rejected for: NAS100 (max age 900s)." in body["data_freshness"]["movement_source"]["position_feed_detail"]
    assert body["data_freshness"]["movement_source"]["market_data_provider_requested"] is True
    assert body["data_freshness"]["movement_source"]["configured_market_data_provider"] == "YFinanceConnector"
    assert body["data_freshness"]["movement_source"]["static_fallback_symbols"] == ["NAS100"]
    assert body["data_freshness"]["movement_source"]["provider_stale_symbols"] == ["NAS100"]
    assert body["data_freshness"]["movement_source"]["provider_freshness_max_age_seconds"] == 900
    assert body["data_freshness"]["movement_source"]["static_quote_count"] == 1
    assert body["data_freshness"]["movement_source"]["closed_market_symbols"] == ["NAS100"]
    assert body["data_freshness"]["movement_source"]["closed_market_quote_count"] == 1
    assert body["data_freshness"]["movement_source"]["unsupported_provider_symbols"] == ["NAS100"]
    assert body["data_freshness"]["movement_source"]["snapshot_age_seconds_by_symbol"] == {"NAS100": 960}


def test_collect_from_movement_stream_prefers_canonical_movement_source_truth(monkeypatch: pytest.MonkeyPatch):
    from cas_forex.time_utils import utc_now

    fresh_ts = utc_now().isoformat()
    canonical_truth = {
        "movement_stream_present": True,
        "telemetry_source": "movement_stream",
        "telemetry_stale": False,
        "telemetry_last_update_iso": fresh_ts,
        "price_source_status": "PROVIDER_ACTIVE",
        "price_source_label": "PROVIDER",
        "price_source_summary": "Provider/MT5-backed movement is repricing paper/demo rows where quotes are usable.",
        "position_feed_label": "SIM PROOF",
        "position_feed_detail": "Rows are repriced by provider/MT5 quotes.",
        "static_simulation_active": False,
        "open_position_count": 1,
        "broker_ticket_position_count": 0,
        "simulator_position_count": 1,
        "provider_priced_simulator_position_count": 1,
        "static_simulator_position_count": 0,
        "stale_price_position_count": 0,
        "static_position_count": 0,
        "static_quote_count": 0,
        "source_label_counts": {"PAPER_SIM_PROVIDER_PRICED": 1},
        "configured_market_data_provider": "YFinanceConnector",
        "provider_usable_symbols": ["US30"],
        "static_fallback_symbols": [],
        "mt5_fallback_symbols": [],
        "provider_stale_symbols": [],
        "closed_market_symbols": ["US30"],
        "closed_market_quote_count": 1,
        "unsupported_provider_symbols": ["NAS100"],
        "provider_freshness_max_age_seconds": 900,
        "snapshot_age_seconds_by_symbol": {"US30": 45},
        "provider_error_count": 1,
        "attention_required": False,
        "detail": "Rows are repriced by provider/MT5 quotes.",
        "local_detail": "Rows are repriced by provider/MT5 quotes.",
    }
    monkeypatch.setattr(
        lt_route.data_module,
        "movement_stream",
        lambda use_provider_quotes=True: {
            "timestamp": fresh_ts,
            "positions": [
                {
                    "symbol": "US30",
                    "side": "LONG",
                    "lots": 0.01,
                    "open_price": 42000.0,
                    "current_price": 42010.0,
                    "floating_pnl_usd": 1.0,
                }
            ],
            "movement_source_truth": canonical_truth,
            "price_source_status": "STATIC_SIMULATION_FALLBACK",
            "price_source_label": "STATIC SIM",
        },
    )

    result = _ORIGINAL_COLLECT_FROM_MOVEMENT_STREAM()

    assert result is not None
    _, seen_ts, movement_source = result
    assert seen_ts == fresh_ts
    assert movement_source["price_source_status"] == "PROVIDER_ACTIVE"
    assert movement_source["static_quote_count"] == 0
    assert movement_source["closed_market_symbols"] == ["US30"]
    assert movement_source["unsupported_provider_symbols"] == ["NAS100"]


def test_total_floating_pnl_equals_sum_of_positions(monkeypatch: pytest.MonkeyPatch):
    positions = [
        {
            "symbol": "EURUSD",
            "direction": "BUY",
            "lots": 0.01,
            "entry_price": 1.0,
            "current_price": 1.001,
            "floating_pnl": 1.25,
            "opened_at_iso": None,
            "broker_ticket": None,
        },
        {
            "symbol": "USDJPY",
            "direction": "SELL",
            "lots": 0.05,
            "entry_price": 150.0,
            "current_price": 149.8,
            "floating_pnl": -3.40,
            "opened_at_iso": None,
            "broker_ticket": None,
        },
        {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "lots": 0.10,
            "entry_price": 2000.0,
            "current_price": 2001.5,
            "floating_pnl": 15.00,
            "opened_at_iso": None,
            "broker_ticket": None,
        },
    ]
    from cas_forex.time_utils import utc_now

    monkeypatch.setattr(
        lt_route,
        "_collect_from_movement_stream",
        lambda: (positions, utc_now().isoformat()),
    )

    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    expected = round(sum(p["floating_pnl"] for p in positions), 2)
    assert body["totals"]["total_floating_pnl"] == expected
    assert body["totals"]["open_position_count"] == 3


def test_direction_is_normalized_to_buy_or_sell(monkeypatch: pytest.MonkeyPatch):
    """MT5 verifier reports direction as an int (0=BUY, 1=SELL); paper
    movement stream reports it as ``side: LONG|SHORT``. Both must
    surface as the canonical "BUY" / "SELL" tokens."""
    mt5_positions_raw = [
        {
            "ticket": 12345,
            "symbol": "EURUSD",
            "type": 0,  # 0 = BUY
            "volume": 0.01,
            "price_open": 1.0850,
            "price_current": 1.0855,
            "profit": 0.50,
        },
        {
            "ticket": 12346,
            "symbol": "GBPUSD",
            "type": 1,  # 1 = SELL
            "volume": 0.02,
            "price_open": 1.2700,
            "price_current": 1.2680,
            "profit": 4.00,
        },
        # Tolerate already-string upstream shapes too.
        {
            "ticket": 12347,
            "symbol": "USDJPY",
            "type": "SELL",
            "volume": 0.03,
            "price_open": 150.0,
            "price_current": 149.8,
            "profit": 6.00,
        },
    ]
    from cas_forex.time_utils import utc_now

    monkeypatch.setattr(
        lt_route,
        "_collect_from_mt5_terminal",
        lambda: (
            [lt_route._normalize_mt5_position(p) for p in mt5_positions_raw],
            utc_now().isoformat(),
        ),
    )

    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert body["data_freshness"]["source"] == "mt5_terminal_api_verifier"
    by_symbol = {row["symbol"]: row["direction"] for row in body["open_positions"]}
    assert by_symbol == {"EURUSD": "BUY", "GBPUSD": "SELL", "USDJPY": "SELL"}
    # And the only allowed values are BUY / SELL.
    assert {row["direction"] for row in body["open_positions"]} <= {"BUY", "SELL"}


def test_stale_flag_set_when_last_update_is_old(monkeypatch: pytest.MonkeyPatch):
    """Evidence older than the staleness window must surface stale=True
    even though the source is non-empty."""
    from datetime import timedelta
    from cas_forex.time_utils import utc_now

    old_ts = (utc_now() - timedelta(hours=2)).isoformat()
    positions = [
        {
            "symbol": "EURUSD",
            "direction": "BUY",
            "lots": 0.01,
            "entry_price": 1.0,
            "current_price": 1.001,
            "floating_pnl": 1.0,
            "opened_at_iso": None,
            "broker_ticket": None,
        }
    ]
    monkeypatch.setattr(
        lt_route,
        "_collect_from_movement_stream",
        lambda: (positions, old_ts),
    )

    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert body["data_freshness"]["stale"] is True
    assert body["data_freshness"]["last_update_iso"] == old_ts


def test_empty_mt5_snapshot_still_reports_authoritative_source(monkeypatch: pytest.MonkeyPatch):
    from cas_forex.time_utils import utc_now

    monkeypatch.setattr(
        lt_route,
        "_collect_from_mt5_terminal",
        lambda: ([], utc_now().isoformat()),
    )

    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert body["open_positions"] == []
    assert body["totals"]["open_position_count"] == 0
    assert body["telemetry_source"] == "mt5_terminal_api_verifier"
    assert body["position_feed_label"] == "LIVE MT5"
    assert "MT5 broker positions" in body["position_feed_detail"]
    assert body["movement_source_truth"]["position_feed_label"] == "LIVE MT5"
    assert body["movement_source_truth"]["broker_ticket_position_count"] == 0
    assert body["data_freshness"]["source"] == "mt5_terminal_api_verifier"
    assert body["data_freshness"]["stale"] is False


def test_empty_movement_snapshot_still_reports_paper_source(monkeypatch: pytest.MonkeyPatch):
    from cas_forex.time_utils import utc_now

    movement_source = {
        "price_source_status": "CACHE_WARMING",
        "price_source_label": "WARMING",
        "price_source_summary": "Movement snapshot is warming; source truth is not ready yet.",
        "price_source_warning": None,
        "static_simulation_active": False,
        "market_data_provider_requested": True,
        "configured_market_data_provider": "YFinanceConnector",
        "provider_usable_symbols": [],
        "static_fallback_symbols": [],
        "mt5_fallback_symbols": [],
        "provider_errors": {},
        "snapshot_source_by_symbol": {},
    }
    monkeypatch.setattr(
        lt_route,
        "_collect_from_movement_stream",
        lambda: ([], utc_now().isoformat(), movement_source),
    )

    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert body["open_positions"] == []
    assert body["totals"]["open_position_count"] == 0
    assert body["telemetry_source"] == "movement_stream"
    assert body["price_source_status"] == "CACHE_WARMING"
    assert body["position_feed_label"] == "SIM PROOF"
    assert body["movement_source_truth"]["price_source_status"] == "CACHE_WARMING"
    assert body["movement_source_truth"]["position_feed_label"] == "SIM PROOF"
    assert body["data_freshness"]["source"] == "movement_stream"
    assert body["data_freshness"]["stale"] is False
    assert body["data_freshness"]["movement_source"]["price_source_status"] == "CACHE_WARMING"
    assert body["data_freshness"]["movement_source"]["price_source_label"] == "WARMING"


def test_movement_rows_preserve_position_source_metadata(monkeypatch: pytest.MonkeyPatch):
    from cas_forex.time_utils import utc_now

    raw_position = {
        "symbol": "NAS100",
        "side": "LONG",
        "lot_size": 0.01,
        "open_price": 29173.02,
        "current_price": 29173.02,
        "floating_pnl_usd": 0.0,
        "opened_at_iso": "2026-07-05T12:00:00+00:00",
        "broker_ticket": None,
        "price_source": "paper_route_snapshot:static_simulation",
        "price_stale": True,
        "stale_reason": "Static simulation only",
        "age_seconds": 7200,
        "age_days": 0.08,
        "position_source_label": "PAPER_SIM_STATIC",
    }
    monkeypatch.setattr(
        lt_route,
        "_collect_from_movement_stream",
        lambda: (
            [lt_route._normalize_paper_position(raw_position)],
            utc_now().isoformat(),
            {"price_source_status": "STATIC_SIMULATION_FALLBACK"},
        ),
    )

    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert body["position_feed_label"] == "SIM PROOF"
    assert body["static_position_count"] == 1
    row = body["open_positions"][0]
    assert row["price_source"] == "paper_route_snapshot:static_simulation"
    assert row["price_stale"] is True
    assert row["stale_reason"] == "Static simulation only"
    assert row["age_seconds"] == 7200
    assert row["age_days"] == 0.08
    assert row["position_source_label"] == "PAPER_SIM_STATIC"


def test_broker_ticket_backed_movement_rows_stay_sim_proof_not_live_mt5(monkeypatch: pytest.MonkeyPatch):
    from cas_forex.time_utils import utc_now

    raw_position = {
        "symbol": "EURUSD",
        "side": "LONG",
        "lot_size": 0.01,
        "open_price": 1.0850,
        "current_price": 1.0850,
        "floating_pnl_usd": 0.0,
        "opened_at_iso": "2026-07-05T12:00:00+00:00",
        "broker_ticket": "45938644",
        "price_source": "paper_route_snapshot:static_simulation",
        "price_stale": True,
        "stale_reason": "Static simulation only",
        "age_seconds": 7200,
        "age_days": 0.08,
        "position_source_label": "PAPER_SIM_BROKER_TICKET_STATIC",
    }
    monkeypatch.setattr(
        lt_route,
        "_collect_from_movement_stream",
        lambda: (
            [lt_route._normalize_paper_position(raw_position)],
            utc_now().isoformat(),
            {"price_source_status": "STATIC_SIMULATION_FALLBACK"},
        ),
    )

    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert body["position_feed_label"] == "SIM PROOF"
    assert "not live MT5 terminal positions" in body["position_feed_detail"]
    assert "carry broker tickets" in body["position_feed_detail"]
    assert body["broker_ticket_position_count"] == 1
    row = body["open_positions"][0]
    assert row["broker_ticket"] == "45938644"
    assert row["position_source_label"] == "PAPER_SIM_BROKER_TICKET_STATIC"


def test_mt5_rows_are_tagged_as_live_broker_positions(monkeypatch: pytest.MonkeyPatch):
    from datetime import timedelta
    from cas_forex.time_utils import utc_now

    snapshot_iso = utc_now().isoformat()
    opened_at_iso = (utc_now() - timedelta(days=3, hours=4)).isoformat()
    raw_position = {
        "ticket": 12345,
        "symbol": "EURUSD",
        "type": 0,
        "volume": 0.01,
        "price_open": 1.0850,
        "price_current": 1.0855,
        "profit": 0.50,
        "time_open_iso": opened_at_iso,
    }
    monkeypatch.setattr(
        lt_route,
        "_collect_from_mt5_terminal",
        lambda: ([lt_route._normalize_mt5_position(raw_position, snapshot_iso=snapshot_iso)], snapshot_iso),
    )

    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert body["position_feed_label"] == "LIVE MT5"
    assert body["broker_ticket_position_count"] == 1
    assert body["static_position_count"] == 0
    row = body["open_positions"][0]
    assert row["price_source"] == "mt5_terminal_api_verifier"
    assert row["price_stale"] is False
    assert row["position_source_label"] == "MT5_LIVE_BROKER"
    assert row["age_seconds"] >= 3 * 86400
    assert row["age_days"] >= 3.0
