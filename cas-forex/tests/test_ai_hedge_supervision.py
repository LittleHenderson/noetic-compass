from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from api import server as api_server
from api.routes import settings as settings_route
from cas_forex.ai_hedge_supervision import build_ai_hedge_supervision_report
from ui_contract import assert_panel_wired


REPO_ROOT = Path(__file__).resolve().parents[1]


def _movement_position(**overrides: Any) -> dict[str, Any]:
    row = {
        "row_id": "pos-1",
        "symbol": "US30",
        "side": "LONG",
        "lot_size": 0.01,
        "open_price": 100.0,
        "current_price": 120.0,
        "stop_loss": 90.0,
        "take_profit": 140.0,
        "floating_pnl_usd": 20.0,
        "floating_pnl_units": 20.0,
        "price_source": "provider_snapshot:MT5TerminalMarketDataConnector",
        "price_stale": False,
        "stale_reason": None,
        "position_source_label": "PAPER_SIM_MT5_PRICED",
        "age_days": 0.5,
        "broker_ticket": None,
    }
    row.update(overrides)
    return row


def _movement_stream(position: dict[str, Any] | None = None, **overrides: Any) -> dict[str, Any]:
    payload = {
        "report_kind": "cas_forex_movement_stream",
        "stream_id": "movement-1",
        "timestamp": "2026-07-09T12:00:00Z",
        "positions": [] if position is None else [position],
        "price_source_status": "PROVIDER_ACTIVE",
        "price_source_label": "PROVIDER",
        "price_source_summary": "Provider or MT5 quotes are repricing paper/demo rows.",
        "price_source_warning": None,
        "static_simulation_active": False,
        "provider_usable_symbols": ["US30"] if position else [],
        "static_fallback_symbols": [],
    }
    payload.update(overrides)
    return payload


def test_ai_hedge_supervision_recommends_partial_and_trailing_after_two_r():
    report = build_ai_hedge_supervision_report(_movement_stream(_movement_position()))

    assert report["report_kind"] == "cas_forex_ai_hedge_supervision"
    assert report["status"] == "ACTIVE_RECOMMENDATIONS"
    assert report["position_count"] == 1
    assert report["positions"][0]["r_multiple"] == 2.0
    intents = [row["intent"] for row in report["recommendations"]]
    assert "close_partial" in intents
    assert "trail_stop" in intents
    assert report["broker_bound_action_authorized"] is False
    assert report["orders_placed"] is False
    assert report["money_moved"] is False
    assert "order_dispatch.py" in report["execution_required_path"]


def test_ai_hedge_supervision_honors_disabled_trailing_dial():
    report = build_ai_hedge_supervision_report(
        _movement_stream(
            _movement_position(),
            management_policy={
                "trailing_stop_enabled": False,
                "trailing_lock_fraction": 0.7,
            },
        )
    )

    intents = [row["intent"] for row in report["recommendations"]]
    assert "close_partial" in intents
    assert "trail_stop" not in intents
    assert report["management_policy"]["trailing_stop_enabled"] is False


def test_ai_hedge_supervision_carries_owner_trailing_fraction_into_draft():
    report = build_ai_hedge_supervision_report(
        _movement_stream(
            _movement_position(),
            management_policy={
                "trailing_stop_enabled": True,
                "trailing_lock_fraction": 0.7,
            },
        )
    )

    trail = next(row for row in report["recommendations"] if row["intent"] == "trail_stop")
    assert trail["parameters"]["trailing_lock_fraction"] == 0.7
    assert "70%" in trail["reason"]


def test_ai_hedge_supervision_requires_fresh_prices_before_management():
    report = build_ai_hedge_supervision_report(
        _movement_stream(
            _movement_position(
                current_price=100.0,
                price_source="paper_route_snapshot:static_simulation",
                price_stale=True,
                stale_reason="Static paper-route snapshot.",
                position_source_label="PAPER_SIM_STATIC",
            ),
            price_source_status="STATIC_SIMULATION_FALLBACK",
            price_source_label="STATIC SIM",
            price_source_summary="Static simulation only.",
            price_source_warning="Static simulator rows are not being moved.",
            static_simulation_active=True,
            provider_usable_symbols=[],
            static_fallback_symbols=["US30"],
        )
    )

    assert report["status"] == "ATTENTION"
    assert report["static_simulation_active"] is True
    assert report["source_health"]["fresh_for_trade_management"] is False
    assert report["position_feed_label"] == "SIM PROOF"
    assert "paper/demo proof rows" in report["position_feed_detail"]
    assert report["source_health"]["position_feed_label"] == "SIM PROOF"
    assert "paper/demo proof rows" in str(report["source_health"]["detail"])
    assert report["high_urgency_count"] >= 1
    assert report["recommendations"][0]["intent"] == "stand_down"
    assert "Static simulator fallback is active" in report["recommendations"][0]["reason"]


def test_ai_hedge_supervision_recommends_breakeven_after_one_r():
    report = build_ai_hedge_supervision_report(
        _movement_stream(_movement_position(current_price=112.0))
    )

    assert report["status"] == "ACTIVE_RECOMMENDATIONS"
    assert report["positions"][0]["r_multiple"] == 1.2
    assert report["recommendations"][0]["intent"] == "move_stop_to_breakeven"
    assert "stop is not at breakeven" in report["recommendations"][0]["reason"]


def test_ai_hedge_supervision_recommends_emergency_stop_for_unprotected_position():
    report = build_ai_hedge_supervision_report(
        _movement_stream(_movement_position(stop_loss=0.0))
    )

    recommendation = report["recommendations"][0]
    assert recommendation["intent"] == "set_stop_loss"
    assert recommendation["urgency"] == "HIGH"
    assert recommendation["parameters"]["stop_loss"] == 80.0


def test_ai_hedge_supervision_recommends_missing_and_extended_take_profit():
    missing = build_ai_hedge_supervision_report(
        _movement_stream(_movement_position(current_price=112.0, take_profit=0.0))
    )
    set_tp = next(row for row in missing["recommendations"] if row["intent"] == "set_take_profit")
    assert set_tp["parameters"]["take_profit"] == 120.0

    extending = build_ai_hedge_supervision_report(
        _movement_stream(
            _movement_position(current_price=137.0, stop_loss=100.0, take_profit=140.0)
        )
    )
    modify_tp = next(
        row for row in extending["recommendations"] if row["intent"] == "modify_take_profit"
    )
    assert modify_tp["parameters"]["take_profit"] == 160.0


def test_ai_hedge_supervision_recommends_full_close_on_invalidation_or_time_stop():
    invalidated = build_ai_hedge_supervision_report(
        _movement_stream(_movement_position(current_price=89.0))
    )
    assert invalidated["recommendations"][0]["intent"] == "close_full"
    assert "invalidated" in invalidated["recommendations"][0]["reason"]

    stale_loser = build_ai_hedge_supervision_report(
        _movement_stream(
            _movement_position(
                current_price=99.0,
                floating_pnl_usd=-1.0,
                floating_pnl_units=-1.0,
                age_days=4.0,
            )
        )
    )
    assert stale_loser["recommendations"][0]["intent"] == "close_full"
    assert "time stop" in stale_loser["recommendations"][0]["reason"]


def test_time_stop_uses_net_open_pnl_after_reported_carry():
    report = build_ai_hedge_supervision_report(
        _movement_stream(
            _movement_position(
                current_price=101.0,
                floating_pnl_usd=1.0,
                swap_usd=-2.0,
                commission_usd=0.0,
                age_days=4.0,
            )
        )
    )

    assert report["positions"][0]["position_price_pnl_usd"] == 1.0
    assert report["positions"][0]["net_open_pnl_after_reported_costs_usd"] == -1.0
    assert report["recommendations"][0]["intent"] == "close_full"
    assert "time stop" in report["recommendations"][0]["reason"]


def test_ai_hedge_supervision_settings_route_is_cache_first_and_read_only(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_cache_first_payload(key, *, builder, fallback, ttl_seconds, block_on_cold):
        captured.update(
            {
                "key": key,
                "builder_callable": callable(builder),
                "ttl_seconds": ttl_seconds,
                "block_on_cold": block_on_cold,
            }
        )
        return fallback()

    monkeypatch.setattr(settings_route, "cache_first_payload", fake_cache_first_payload)

    body = asyncio.run(settings_route.get_ai_hedge_supervision())

    assert captured == {
        "key": "settings_ai_hedge_supervision",
        "builder_callable": True,
        "ttl_seconds": 10.0,
        "block_on_cold": False,
    }
    assert body["report_kind"] == "cas_forex_ai_hedge_supervision"
    assert body["status"] == "WARMING"
    assert body["position_feed_label"] == "WARMING"
    assert "canonical movement position-feed truth" in body["position_feed_detail"]
    assert "canonical movement position-feed truth" in str(body["source_health"]["detail"])
    assert body["broker_bound_action_authorized"] is False
    assert body["orders_placed"] is False
    assert body["money_moved"] is False
    assert "autonomous management executor" in body["claim_boundary"]
    assert "execution_guard.py" in body["claim_boundary"]


def test_ai_hedge_supervision_settings_ui_and_trace_skip_are_wired():
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert_panel_wired("AiHedgeSupervisionPanel")
    # Moved to components/settings/AiHedgePanels.tsx in the settings decomposition (slice 2).
    extracted_aihedgepanels = (Path(__file__).resolve().parents[1] / "ui" / "src" / "components" / "settings" / "AiHedgePanels.tsx").read_text(encoding="utf-8")
    assert "AI Operator Edge / Hedge Supervision" in extracted_aihedgepanels
    assert 'label="Position Feed"' in extracted_aihedgepanels
    assert "report?.position_feed_detail" in extracted_aihedgepanels
    assert "fetchAiHedgeSupervision" in extracted_aihedgepanels
    assert "AiHedgeSupervisionReport" in api_client
    assert "position_feed_detail?: string;" in api_client
    assert '"/settings/ai-hedge-supervision"' in api_client
    assert api_server._should_trace_request("GET", "/api/forex/settings/ai-hedge-supervision") is False
