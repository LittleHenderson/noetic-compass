from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from api import server as api_server
from api.routes import settings as settings_route
from cas_forex.ai_hedge_management import (
    build_ai_hedge_management_handoff,
    build_ai_operator_discretionary_management_options,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _movement_position(**overrides: Any) -> dict[str, Any]:
    row = {
        "row_id": "pos-1",
        "symbol": "US30",
        "side": "LONG",
        "lot_size": 0.04,
        "open_price": 100.0,
        "current_price": 112.0,
        "stop_loss": 90.0,
        "take_profit": 140.0,
        "floating_pnl_usd": 12.0,
        "floating_pnl_units": 12.0,
        "price_source": "provider_snapshot:MT5TerminalMarketDataConnector",
        "price_stale": False,
        "stale_reason": None,
        "position_source_label": "PAPER_SIM_MT5_PRICED",
        "age_days": 0.5,
        "broker_ticket": 123456,
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


def test_ai_hedge_management_drafts_breakeven_modify_without_touching_broker():
    report = build_ai_hedge_management_handoff(
        movement_stream=_movement_stream(_movement_position())
    )

    assert report["report_kind"] == "cas_forex_ai_hedge_management_handoff"
    assert report["status"] == "READY_FOR_GUARDED_EXECUTION"
    assert report["management_action_count"] == 1
    assert report["ready_for_guarded_execution"] is True
    assert report["dry_run_only"] is False
    action = report["management_actions"][0]
    assert action["status"] == "READY_FOR_GUARDED_EXECUTION"
    assert action["intent"] == "move_stop_to_breakeven"
    assert action["broker_method"] == "modify_position"
    assert action["broker_ticket"] == 123456
    assert action["stop_loss"] == 100.0
    assert action["take_profit"] == 140.0
    assert action["requires_owner_confirmation"] is False
    assert action["requires_fresh_broker_truth"] is True
    assert action["requires_execution_guard"] is True
    assert report["broker_bound_action_authorized"] is False
    assert report["broker_touched"] is False
    assert report["orders_placed"] is False
    assert report["money_moved"] is False


def test_ai_hedge_management_blocks_static_or_stale_price_sources():
    report = build_ai_hedge_management_handoff(
        movement_stream=_movement_stream(
            _movement_position(
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

    assert report["status"] == "BLOCKED"
    assert report["management_action_count"] == 0
    assert report["blocked_actions"][0]["block_code"] == "STALE_OR_STATIC_PRICE_SOURCE"
    assert report["broker_touched"] is False


def test_ai_hedge_management_blocks_without_broker_ticket():
    report = build_ai_hedge_management_handoff(
        movement_stream=_movement_stream(_movement_position(broker_ticket=None))
    )

    assert report["status"] == "BLOCKED"
    assert report["blocked_actions"][0]["block_code"] == "MISSING_BROKER_TICKET"
    assert "broker ticket" in report["blocked_actions"][0]["reason"]
    assert report["management_action_count"] == 0


def test_ai_hedge_management_treats_mt5_zero_stop_as_unprotected():
    report = build_ai_hedge_management_handoff(
        movement_stream=_movement_stream(_movement_position(stop_loss=0.0))
    )

    assert report["status"] == "READY_FOR_GUARDED_EXECUTION"
    assert report["management_action_count"] == 1
    action = report["management_actions"][0]
    assert action["intent"] == "set_stop_loss"
    assert action["stop_loss"] == 80.0
    assert action["take_profit"] == 140.0
    assert action["risk_effect"] == "emergency_protective_stop"


def test_ai_hedge_management_drafts_take_profit_set_and_extension():
    missing = build_ai_hedge_management_handoff(
        movement_stream=_movement_stream(_movement_position(take_profit=0.0))
    )
    set_tp = next(row for row in missing["management_actions"] if row["intent"] == "set_take_profit")
    assert set_tp["stop_loss"] == 90.0
    assert set_tp["take_profit"] == 120.0
    assert set_tp["risk_effect"] == "bounded_profit_target"

    extending = build_ai_hedge_management_handoff(
        movement_stream=_movement_stream(
            _movement_position(current_price=137.0, stop_loss=100.0, take_profit=140.0)
        )
    )
    modify_tp = next(
        row for row in extending["management_actions"] if row["intent"] == "modify_take_profit"
    )
    assert modify_tp["stop_loss"] == 100.0
    assert modify_tp["take_profit"] == 160.0
    assert modify_tp["risk_effect"] == "profit_extension_after_principal_lock"


def test_ai_hedge_management_drafts_full_close_without_partial_volume():
    report = build_ai_hedge_management_handoff(
        movement_stream=_movement_stream(_movement_position(current_price=89.0))
    )

    action = report["management_actions"][0]
    assert action["intent"] == "close_full"
    assert action["broker_method"] == "close_position"
    assert action["volume"] is None
    assert action["expected_remaining_volume"] == 0.0
    assert action["risk_effect"] == "exposure_reducing_full_close"


def test_ai_hedge_management_drafts_partial_close_and_trailing_after_two_r():
    report = build_ai_hedge_management_handoff(
        movement_stream=_movement_stream(_movement_position(current_price=120.0))
    )

    actions = report["management_actions"]
    partial = next(row for row in actions if row["intent"] == "close_partial")
    trail = next(row for row in actions if row["intent"] == "trail_stop")

    assert report["status"] == "READY_FOR_GUARDED_EXECUTION"
    assert partial["broker_method"] == "close_position"
    assert partial["volume"] == 0.02
    assert partial["draft_call"] == {
        "method": "bridge.close_position",
        "ticket": 123456,
        "volume": 0.02,
    }
    assert trail["broker_method"] == "modify_position"
    assert trail["stop_loss"] == 110.0
    assert trail["stop_loss"] > 90.0
    assert trail["stop_loss"] < 120.0


def test_ai_hedge_management_uses_owner_trailing_lock_fraction():
    report = build_ai_hedge_management_handoff(
        movement_stream=_movement_stream(
            _movement_position(current_price=120.0),
            management_policy={
                "trailing_stop_enabled": True,
                "trailing_lock_fraction": 0.7,
            },
        )
    )

    trail = next(row for row in report["management_actions"] if row["intent"] == "trail_stop")
    assert trail["stop_loss"] == 114.0
    assert trail["decision_parameters"]["trailing_lock_fraction"] == 0.7


def test_ai_hedge_management_blocks_partial_close_when_volume_too_small():
    report = build_ai_hedge_management_handoff(
        movement_stream=_movement_stream(
            _movement_position(current_price=120.0, lot_size=0.01)
        )
    )

    block_codes = {row["block_code"] for row in report["blocked_actions"]}
    assert "VOLUME_TOO_SMALL_FOR_PARTIAL_CLOSE" in block_codes
    assert any(row["intent"] == "trail_stop" for row in report["management_actions"])


def test_operator_discretionary_options_offer_tiny_winner_full_close_without_policy_trigger():
    report = build_ai_operator_discretionary_management_options(
        _movement_stream(
            _movement_position(
                lot_size=0.01,
                current_price=108.0,
                floating_pnl_usd=8.0,
                position_price_pnl_usd=8.0,
                swap_usd=-1.0,
                commission_usd=0.0,
                net_open_pnl_after_reported_costs_usd=7.0,
            ),
            management_policy={
                "trailing_stop_enabled": False,
                "trailing_lock_fraction": 0.5,
            },
        )
    )

    assert report["status"] == "OPERATOR_DISCRETIONARY_OPTIONS_READY"
    assert report["option_count"] == 2
    assert report["option_position_count"] == 1
    assert {row["intent"] for row in report["options"]} == {
        "close_full",
        "move_stop_to_breakeven",
    }
    close = next(row for row in report["options"] if row["intent"] == "close_full")
    assert close["volume"] is None
    assert close["operator_discretionary_option"] is True
    assert close["operator_selection_required"] is True
    assert close["option_origin"] == "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW"
    assert report["model_failure_policy"] == "STAND_DOWN"
    assert all(row["intent"] != "close_partial" for row in report["options"])


def test_operator_discretionary_options_keep_same_symbol_positions_ticket_scoped():
    first = _movement_position(
        row_id="broker:111",
        broker_ticket=111,
        symbol="XAUUSD",
        side="SHORT",
        lot_size=0.01,
        open_price=4073.0,
        current_price=4060.0,
        stop_loss=4073.0,
        take_profit=4040.0,
        floating_pnl_usd=13.0,
        net_open_pnl_after_reported_costs_usd=13.0,
    )
    second = _movement_position(
        row_id="broker:222",
        broker_ticket=222,
        symbol="XAUUSD",
        side="SHORT",
        lot_size=0.01,
        open_price=4071.0,
        current_price=4060.0,
        stop_loss=4102.0,
        take_profit=4032.0,
        floating_pnl_usd=11.0,
        net_open_pnl_after_reported_costs_usd=11.0,
    )
    report = build_ai_operator_discretionary_management_options(
        _movement_stream(
            positions=[first, second],
            provider_usable_symbols=["XAUUSD"],
            management_policy={"trailing_stop_enabled": False},
        )
    )

    assert report["option_count"] == 3
    assert report["option_position_count"] == 2
    close_tickets = {
        row["broker_ticket"]
        for row in report["options"]
        if row["intent"] == "close_full"
    }
    assert close_tickets == {111, 222}
    breakeven = next(
        row for row in report["options"] if row["intent"] == "move_stop_to_breakeven"
    )
    assert breakeven["broker_ticket"] == 222
    assert len({row["action_id"] for row in report["options"]}) == 3


def test_ai_hedge_management_supports_short_trailing_without_loosening_stop():
    report = build_ai_hedge_management_handoff(
        movement_stream=_movement_stream(
            _movement_position(
                symbol="EURUSD",
                side="SHORT",
                open_price=1.1000,
                current_price=1.0800,
                stop_loss=1.1100,
                take_profit=1.0600,
                price_source="provider_snapshot:MT5TerminalMarketDataConnector",
                position_source_label="PAPER_SIM_MT5_PRICED",
            )
        )
    )

    trail = next(row for row in report["management_actions"] if row["intent"] == "trail_stop")
    assert trail["broker_method"] == "modify_position"
    assert trail["stop_loss"] == 1.09
    assert trail["stop_loss"] < 1.1100
    assert trail["stop_loss"] > 1.0800


def test_ai_hedge_management_settings_route_is_cache_first_and_proposal_only(monkeypatch):
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

    body = asyncio.run(settings_route.get_ai_hedge_management_handoff())

    assert captured == {
        "key": "settings_ai_hedge_management_handoff",
        "builder_callable": True,
        "ttl_seconds": 10.0,
        "block_on_cold": False,
    }
    assert body["report_kind"] == "cas_forex_ai_hedge_management_handoff"
    assert body["status"] == "WARMING"
    assert body["dry_run_only"] is False
    assert body["broker_touched"] is False
    assert body["orders_placed"] is False
    assert "guarded execution" in body["claim_boundary"]


def test_ai_hedge_management_settings_ui_operator_and_trace_skip_are_wired():
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    operator = (REPO_ROOT / "cas_forex" / "ai_operator.py").read_text(encoding="utf-8")

    assert "<AiHedgeManagementHandoffPanel />" in settings_page
    assert "function AiHedgeManagementHandoffPanel()" in settings_page
    assert "AI Operator Edge / Hedge Management Handoff" in settings_page
    assert "fetchAiHedgeManagementHandoff" in settings_page
    assert "AiHedgeManagementHandoffReport" in api_client
    assert '"/settings/ai-hedge-management-handoff"' in api_client
    assert "ai_hedge_management_handoff" in operator
    assert api_server._should_trace_request(
        "GET", "/api/forex/settings/ai-hedge-management-handoff"
    ) is False
