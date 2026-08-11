from __future__ import annotations

import asyncio
from types import SimpleNamespace

from api.routes import ai_hedge_management as management_route
from cas_forex import dispatch_loop
from cas_forex.ai_hedge_management_runtime import (
    prepare_current_ai_hedge_management,
)
from cas_forex.time_utils import utc_now


class _ActiveBridge:
    def get_open_positions(self):
        return [
            {
                "ticket": 987654,
                "broker_ticket": 987654,
                "symbol": "EURUSD",
                "side": "LONG",
                "type": "BUY",
                "volume": 0.02,
                "open_price": 1.1000,
                "current_price": 1.1020,
                "stop_loss": 1.1005,
                "take_profit": 1.1040,
                "profit": 4.0,
                "swap": 0.0,
                "commission": 0.0,
            }
        ]

    def get_all_open_positions(self):
        return self.get_open_positions()

    def get_account_info(self):
        return {
            "balance": 5000.0,
            "equity": 5004.0,
            "margin": 10.0,
            "margin_free": 4994.0,
        }

    def is_connected(self):
        return True

    def is_demo_account(self):
        return True

    def will_execute_real_order(self):
        return False


def _config():
    return SimpleNamespace(
        live_mode=False,
        paper_trading=True,
        dispatch_quote_max_age_seconds=120,
        ai_hedge_position_scope="CAS_ONLY",
        ai_hedge_emergency_stop_distance_pct=0.5,
        ai_hedge_emergency_stop_market_buffer_pct=0.05,
        ai_hedge_take_profit_reward_risk=2.0,
        ai_hedge_take_profit_extension_trigger_fraction=0.8,
        ai_hedge_take_profit_extension_factor=1.5,
        ai_hedge_time_stop_hours=72.0,
        ai_control_values={
            "trailing_stop_enabled": 1,
            "trailing_lock_fraction": 0.5,
        },
    )


def _quote(_symbol, *, config=None, prefer_mt5=False):
    _ = (config, prefer_mt5)
    return {
        "quote_source": "fake_mt5",
        "quote_feed_label": "fresh fake MT5 quote",
        "market_snapshot": {
            "symbol": "EURUSD",
            "bid": 1.1020,
            "ask": 1.1021,
            "timestamp": utc_now().isoformat(),
            "is_market_open": True,
            "synthetic_fallback": False,
            "source": "fake_mt5",
        },
    }


def test_current_handoff_uses_active_bridge_positions_not_static_simulator():
    bridge = _ActiveBridge()
    prepared = prepare_current_ai_hedge_management(
        runtime_context={
            "status": "READY",
            "effective_mode": "PAPER_FALLBACK",
            "execution_lane": "PAPER",
            "position_scope": "CAS_ONLY",
            "runtime_config": _config(),
            "bridge": bridge,
            "bridge_selection": {
                "status": "PAPER_MT5_ORDER_SEND_READY",
                "detail": "fake active MT5 demo bridge",
            },
        },
        quote_context_builder=_quote,
    )

    assert prepared["status"] == "READY"
    assert prepared["position_snapshot"]["position_count"] == 1
    assert prepared["position_snapshot"]["static_simulation_active"] is False
    assert prepared["supervision"]["runtime_truth_source"] == (
        "ACTIVE_DISPATCH_MANAGEMENT_LANE"
    )
    assert prepared["handoff"]["runtime_mode"] == "PAPER_FALLBACK"
    assert prepared["handoff"]["execution_lane"] == "PAPER"
    assert prepared["handoff"]["bridge_class"] == "_ActiveBridge"
    assert prepared["handoff"]["position_count"] == 1
    assert prepared["handoff"]["static_simulation_active"] is False


def test_active_management_runtime_matches_paper_scheduler_selector(monkeypatch):
    bridge = _ActiveBridge()
    config = _config()
    monkeypatch.setattr(dispatch_loop, "_effective_mode", lambda: "PAPER_FALLBACK")
    monkeypatch.setattr(dispatch_loop, "_runtime_config_for_mode", lambda _mode: config)
    monkeypatch.setattr(
        dispatch_loop,
        "_effective_management_position_scope",
        lambda _config=None: "CAS_ONLY",
    )
    monkeypatch.setattr(
        "cas_forex.broker_control.select_paper_learning_bridge",
        lambda supplied: bridge if supplied is config else None,
    )
    monkeypatch.setattr(
        "cas_forex.broker_control.bridge_selection_report",
        lambda selected: {
            "status": "PAPER_MT5_ORDER_SEND_READY",
            "detail": "selected active paper bridge",
            "bridge_class": type(selected).__name__,
        },
    )

    result = dispatch_loop.resolve_active_management_runtime()

    assert result["status"] == "READY"
    assert result["effective_mode"] == "PAPER_FALLBACK"
    assert result["execution_lane"] == "PAPER"
    assert result["runtime_config"] is config
    assert result["bridge"] is bridge
    assert result["bridge_selection"]["status"] == "PAPER_MT5_ORDER_SEND_READY"


def test_management_handoff_route_returns_broker_backed_builder_result(monkeypatch):
    monkeypatch.setattr(
        management_route,
        "build_current_ai_hedge_management_handoff",
        lambda: {
            "report_kind": "cas_forex_ai_hedge_management_handoff",
            "status": "READY_FOR_GUARDED_EXECUTION",
            "runtime_truth_source": "ACTIVE_DISPATCH_MANAGEMENT_LANE",
            "position_count": 2,
        },
    )

    result = asyncio.run(management_route.get_ai_hedge_management_handoff())

    assert result["status"] == "READY_FOR_GUARDED_EXECUTION"
    assert result["runtime_truth_source"] == "ACTIVE_DISPATCH_MANAGEMENT_LANE"
    assert result["position_count"] == 2
