from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any

import cas_forex.ai_hedge_management_cycle as management_cycle
from cas_forex.ai_hedge_management import (
    build_ai_operator_discretionary_management_options,
)
from cas_forex.ai_hedge_management_cycle import (
    build_broker_position_management_snapshot,
    run_ai_hedge_management_cycle,
)
from cas_forex.schemas.order import OrderOutcome, OrderStatus
from cas_forex.time_utils import utc_now


class FakeManagementBridge:
    def __init__(
        self,
        *,
        current_price: float = 110.0,
        stop_loss: float = 90.0,
        volume: float = 0.04,
    ) -> None:
        self.positions: dict[int, dict[str, Any]] = {
            123456: {
                "ticket": 123456,
                "symbol": "US30",
                "type": "BUY",
                "volume": volume,
                "open_price": 100.0,
                "current_price": current_price,
                "stop_loss": stop_loss,
                "take_profit": 140.0,
                "profit": 20.0,
                "comment": "CAS_TEST",
                "opened_at_iso": utc_now().isoformat(),
            }
        }
        self.modify_calls: list[dict[str, Any]] = []
        self.close_calls: list[dict[str, Any]] = []

    def is_connected(self) -> bool:
        return True

    def will_execute_real_order(self) -> bool:
        return False

    def get_account_info(self) -> dict[str, Any]:
        return {
            "balance": 44_779.12,
            "equity": 44_779.12,
            "margin": 0.0,
            "margin_free": 44_779.12,
            "leverage": 500,
        }

    def symbol_info(self, symbol: str) -> SimpleNamespace | None:
        if symbol != "US30":
            return None
        return SimpleNamespace(
            name="US30",
            point=0.01,
            digits=2,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            trade_contract_size=1.0,
            trade_tick_size=0.01,
            trade_tick_value=1.0,
            trade_tick_value_loss=1.0,
            trade_tick_value_profit=1.0,
            trade_stops_level=0,
            trade_freeze_level=0,
        )

    def symbols_get(self, pattern: str | None = None) -> list[SimpleNamespace]:
        _ = pattern
        return [SimpleNamespace(name="US30")]

    def get_all_open_positions(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.positions.values()]

    def get_open_positions(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.positions.values()
            if "CAS" in str(row.get("comment") or "")
        ]

    def modify_position(
        self,
        ticket: int,
        *,
        stop_loss: float,
        take_profit: float | None = None,
    ) -> OrderOutcome:
        self.modify_calls.append(
            {"ticket": ticket, "stop_loss": stop_loss, "take_profit": take_profit}
        )
        self.positions[ticket]["stop_loss"] = stop_loss
        if take_profit is not None:
            self.positions[ticket]["take_profit"] = take_profit
        return OrderOutcome(
            order_ref=f"modify-{ticket}",
            broker_ticket=ticket,
            status=OrderStatus.EXECUTED,
        )

    def close_position(self, ticket: int, volume: float | None = None) -> bool:
        self.close_calls.append({"ticket": ticket, "volume": volume})
        if ticket not in self.positions:
            return False
        if volume is None:
            del self.positions[ticket]
            return True
        remaining = round(float(self.positions[ticket]["volume"]) - float(volume), 2)
        if remaining <= 0:
            del self.positions[ticket]
        else:
            self.positions[ticket]["volume"] = remaining
        return True


def _config() -> SimpleNamespace:
    return SimpleNamespace(
        live_mode=False,
        dispatch_quote_max_age_seconds=120,
        ai_hedge_management_attempt_cooldown_seconds=1,
        ai_hedge_management_max_actions_per_cycle=8,
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
            "max_risk_pct_per_trade": 0.1,
        },
    )


def _quote_builder(
    _symbol: str,
    *,
    config: Any = None,
    bid: float = 110.0,
    ask: float = 110.2,
    market_open: bool = True,
    timestamp: Any = None,
) -> dict[str, Any]:
    _ = config
    return {
        "quote_source": "fake_mt5",
        "quote_feed_label": "fake MT5 quote",
        "market_snapshot": {
            "symbol": "US30",
            "bid": bid,
            "ask": ask,
            "timestamp": timestamp or utc_now().isoformat(),
            "is_market_open": market_open,
            "synthetic_fallback": False,
            "source": "fake_mt5",
        },
    }


def test_broker_position_snapshot_uses_exit_side_fresh_quote():
    bridge = FakeManagementBridge(current_price=999.0)

    report = build_broker_position_management_snapshot(
        bridge,
        config=_config(),
        quote_context_builder=lambda symbol, **kwargs: _quote_builder(
            symbol, **kwargs, bid=111.5, ask=111.8
        ),
    )

    assert report["status"] == "FRESH"
    assert report["position_count"] == 1
    assert report["provider_usable_symbols"] == ["US30"]
    assert report["positions"][0]["broker_ticket"] == 123456
    assert report["positions"][0]["side"] == "LONG"
    assert report["positions"][0]["current_price"] == 111.5
    assert report["positions"][0]["price_stale"] is False
    assert report["positions"][0]["risk_at_stop_usd"] == 40.0
    assert report["positions"][0]["risk_at_stop_pct_equity"] == 0.0893
    assert report["positions"][0]["risk_cap_breached"] is False
    assert report["position_risk"]["status"] == "POSITION_RISK_WITHIN_CAP"
    assert report["management_policy"]["max_risk_pct_per_trade"] == 0.1


def test_exact_execution_receipt_time_overrides_future_broker_server_time(monkeypatch):
    bridge = FakeManagementBridge(current_price=101.0)
    receipt_opened = utc_now() - timedelta(minutes=20)
    bridge.positions[123456]["opened_at_iso"] = (
        utc_now() + timedelta(hours=3)
    ).isoformat()
    monkeypatch.setattr(
        management_cycle,
        "_position_origin_by_ticket",
        lambda: {
            "123456": {
                "broker_ticket": "123456",
                "opened_at_iso": receipt_opened.isoformat(),
                "opened_at_source": "BROKER_EXECUTION_RECEIPT_TIMESTAMP",
                "source": "ORDER_ATTEMPT_LEDGER",
            }
        },
    )

    report = build_broker_position_management_snapshot(
        bridge,
        config=_config(),
        quote_context_builder=lambda symbol, **kwargs: _quote_builder(
            symbol, **kwargs, bid=101.0, ask=101.2
        ),
    )

    row = report["positions"][0]
    assert row["opened_at_iso"] == receipt_opened.isoformat()
    assert row["opened_at_source"] == "BROKER_EXECUTION_RECEIPT_TIMESTAMP"
    assert row["age_days"] is not None
    assert row["age_days"] > 19.0 / (24.0 * 60.0)
    assert row["age_days"] < 21.0 / (24.0 * 60.0)
    options = build_ai_operator_discretionary_management_options(report)
    assert options["options"]
    assert all(
        option["opened_at_source"] == "BROKER_EXECUTION_RECEIPT_TIMESTAMP"
        for option in options["options"]
    )


def test_broker_position_snapshot_flags_inherited_entry_risk_for_operator_context():
    bridge = FakeManagementBridge(current_price=52_650.0, stop_loss=52_734.75, volume=0.01)
    bridge.positions[123456].update(
        {
            "open_price": 52_597.82,
            "take_profit": 52_374.18,
            "type": "SELL",
        }
    )

    report = build_broker_position_management_snapshot(
        bridge,
        config=_config(),
        quote_context_builder=lambda symbol, **kwargs: _quote_builder(
            symbol, **kwargs, bid=52_649.8, ask=52_650.0
        ),
    )

    row = report["positions"][0]
    assert row["side"] == "SHORT"
    assert row["risk_at_stop_usd"] == 136.93
    assert row["risk_at_stop_pct_equity"] == 0.3058
    assert row["risk_cap_breached"] is True
    assert report["position_risk"]["status"] == "POSITION_RISK_CAP_BREACH"
    assert report["position_risk"]["risk_cap_breach_tickets"] == [123456]
    assert "does not add a retroactive forced-close rule" in report["position_risk"]["detail"]


def test_mt5_management_snapshot_requests_broker_first_quote(monkeypatch):
    import cas_forex.order_dispatch as order_dispatch

    class FakeMT5Bridge(FakeManagementBridge):
        pass

    captured: dict[str, Any] = {}

    def quote(symbol: str, *, config: Any = None, prefer_mt5: bool = False):
        captured.update(
            {"symbol": symbol, "config": config, "prefer_mt5": prefer_mt5}
        )
        return _quote_builder(symbol, config=config)

    monkeypatch.setattr(order_dispatch, "build_dispatch_quote_context", quote)
    cfg = _config()

    report = build_broker_position_management_snapshot(
        FakeMT5Bridge(),
        config=cfg,
    )

    assert report["status"] == "FRESH"
    assert captured == {"symbol": "US30", "config": cfg, "prefer_mt5": True}


def test_cycle_autonomously_moves_stop_to_breakeven_and_reconciles(tmp_path):
    bridge = FakeManagementBridge(current_price=110.0, stop_loss=90.0)

    result = run_ai_hedge_management_cycle(
        bridge=bridge,
        config=_config(),
        execute=True,
        state_path=tmp_path / "cycle-state.json",
        audit_path=tmp_path / "execution-audit.jsonl",
        quote_context_builder=_quote_builder,
    )

    assert result["status"] == "ACTIONS_EXECUTED"
    assert result["state_persisted"] is True
    assert result["attempted_action_count"] == 1
    assert result["terminal_effect_count"] == 1
    assert result["per_action_owner_confirmation_required"] is False
    assert bridge.modify_calls == [
        {"ticket": 123456, "stop_loss": 100.0, "take_profit": 140.0}
    ]
    assert result["executions"][0]["status"] == "EXECUTED_RECONCILED"


def test_partial_profit_is_one_shot_then_cycle_can_trail_remainder(tmp_path):
    bridge = FakeManagementBridge(current_price=120.0, stop_loss=90.0, volume=0.04)
    state_path = tmp_path / "cycle-state.json"
    audit_path = tmp_path / "execution-audit.jsonl"

    first = run_ai_hedge_management_cycle(
        bridge=bridge,
        config=_config(),
        execute=True,
        state_path=state_path,
        audit_path=audit_path,
        quote_context_builder=lambda symbol, **kwargs: _quote_builder(
            symbol, **kwargs, bid=120.0, ask=120.2
        ),
    )
    second = run_ai_hedge_management_cycle(
        bridge=bridge,
        config=_config(),
        execute=True,
        state_path=state_path,
        audit_path=audit_path,
        quote_context_builder=lambda symbol, **kwargs: _quote_builder(
            symbol, **kwargs, bid=120.0, ask=120.2
        ),
    )
    third = run_ai_hedge_management_cycle(
        bridge=bridge,
        config=_config(),
        execute=True,
        state_path=state_path,
        audit_path=audit_path,
        quote_context_builder=lambda symbol, **kwargs: _quote_builder(
            symbol, **kwargs, bid=120.0, ask=120.2
        ),
    )

    assert first["executions"][0]["selected_action"]["intent"] == "close_partial"
    assert bridge.close_calls == [{"ticket": 123456, "volume": 0.02}]
    assert second["executions"][0]["selected_action"]["intent"] == "trail_stop"
    assert bridge.modify_calls == [
        {"ticket": 123456, "stop_loss": 110.0, "take_profit": 140.0}
    ]
    assert third["attempted_action_count"] == 0
    assert third["status"] in {"WATCHING_NO_ACTION", "ACTIONS_SUPPRESSED"}


def test_cycle_blocks_management_without_fresh_open_quote(tmp_path):
    bridge = FakeManagementBridge(current_price=110.0, stop_loss=90.0)
    state_path = tmp_path / "cycle-state.json"

    result = run_ai_hedge_management_cycle(
        bridge=bridge,
        config=_config(),
        execute=True,
        state_path=state_path,
        audit_path=tmp_path / "execution-audit.jsonl",
        quote_context_builder=lambda symbol, **kwargs: _quote_builder(
            symbol, **kwargs, market_open=False
        ),
    )

    assert result["status"] == "WATCHING_MARKET_CLOSED"
    assert result["attempted_action_count"] == 0
    assert result["stale_position_count"] == 1
    assert result["price_source_status"] == "UNAVAILABLE"
    quote_attempt = result["quote_attempts"][0]
    assert quote_attempt["symbol"] == "US30"
    assert quote_attempt["usable"] is False
    assert quote_attempt["detail"] == "quote reports the market or symbol is closed"
    assert quote_attempt["quote_source"] == "fake_mt5"
    assert quote_attempt["quote_feed_label"] == "fake MT5 quote"
    assert 0.0 <= quote_attempt["age_seconds"] < 0.1
    assert result["blocked_actions"][0]["block_code"] == "HIGH_URGENCY_STAND_DOWN"
    assert result["blocked_actions"][0]["symbol"] == "US30"
    assert result["state_persisted"] is False
    assert not state_path.exists()
    assert bridge.modify_calls == []
    assert bridge.close_calls == []


def test_cycle_still_blocks_an_open_but_stale_quote(tmp_path):
    bridge = FakeManagementBridge(current_price=110.0, stop_loss=90.0)

    result = run_ai_hedge_management_cycle(
        bridge=bridge,
        config=_config(),
        execute=True,
        state_path=tmp_path / "cycle-state.json",
        audit_path=tmp_path / "execution-audit.jsonl",
        quote_context_builder=lambda symbol, **kwargs: _quote_builder(
            symbol,
            **kwargs,
            market_open=True,
            timestamp=(utc_now() - timedelta(minutes=10)).isoformat(),
        ),
    )

    assert result["status"] == "MANAGEMENT_BLOCKED"
    assert result["stale_position_count"] == 1
    assert "quote is stale" in result["quote_attempts"][0]["detail"]


def test_cycle_autonomously_installs_missing_stop_and_reconciles(tmp_path):
    bridge = FakeManagementBridge(stop_loss=0.0)

    result = run_ai_hedge_management_cycle(
        bridge=bridge,
        config=_config(),
        execute=True,
        state_path=tmp_path / "cycle-state.json",
        audit_path=tmp_path / "execution-audit.jsonl",
        quote_context_builder=lambda symbol, **kwargs: _quote_builder(
            symbol, **kwargs, bid=110.0, ask=110.2
        ),
    )

    assert result["status"] == "ACTIONS_EXECUTED"
    assert result["executions"][0]["selected_action"]["intent"] == "set_stop_loss"
    assert bridge.modify_calls == [
        {"ticket": 123456, "stop_loss": 80.0, "take_profit": 140.0}
    ]
    assert result["executions"][0]["status"] == "EXECUTED_RECONCILED"


def test_missing_stop_action_rearms_when_fresh_truth_shows_protection_removed(tmp_path):
    bridge = FakeManagementBridge(stop_loss=0.0)
    state_path = tmp_path / "cycle-state.json"
    audit_path = tmp_path / "execution-audit.jsonl"

    first = run_ai_hedge_management_cycle(
        bridge=bridge,
        config=_config(),
        execute=True,
        state_path=state_path,
        audit_path=audit_path,
        quote_context_builder=_quote_builder,
    )
    bridge.positions[123456]["stop_loss"] = 0.0
    restored = run_ai_hedge_management_cycle(
        bridge=bridge,
        config=_config(),
        execute=True,
        state_path=state_path,
        audit_path=audit_path,
        quote_context_builder=_quote_builder,
    )

    assert first["status"] == "ACTIONS_EXECUTED"
    assert restored["status"] == "ACTIONS_EXECUTED"
    assert [row["stop_loss"] for row in bridge.modify_calls] == [80.0, 80.0]


def test_cycle_full_closes_invalidated_position_and_reconciles(tmp_path):
    bridge = FakeManagementBridge(current_price=89.0, stop_loss=90.0)

    result = run_ai_hedge_management_cycle(
        bridge=bridge,
        config=_config(),
        execute=True,
        state_path=tmp_path / "cycle-state.json",
        audit_path=tmp_path / "execution-audit.jsonl",
        quote_context_builder=lambda symbol, **kwargs: _quote_builder(
            symbol, **kwargs, bid=89.0, ask=89.2
        ),
    )

    assert result["status"] == "ACTIONS_EXECUTED"
    assert bridge.close_calls == [{"ticket": 123456, "volume": None}]
    assert result["executions"][0]["terminal_receipt"]["status"] == "RECONCILED"


def test_position_scope_defaults_to_cas_only_and_all_account_is_explicit():
    bridge = FakeManagementBridge()
    bridge.positions[999999] = {
        **bridge.positions[123456],
        "ticket": 999999,
        "comment": "MANUAL_TRADE",
    }

    cas_only = build_broker_position_management_snapshot(
        bridge,
        config=_config(),
        quote_context_builder=_quote_builder,
    )
    all_account = build_broker_position_management_snapshot(
        bridge,
        config=_config(),
        position_scope="ALL_ACCOUNT",
        quote_context_builder=_quote_builder,
    )

    assert cas_only["position_scope"] == "CAS_ONLY"
    assert cas_only["position_count"] == 1
    assert cas_only["account_position_count"] == 2
    assert cas_only["excluded_position_count"] == 1
    assert all_account["position_scope"] == "ALL_ACCOUNT"
    assert all_account["position_count"] == 2
    assert all_account["excluded_position_count"] == 0


def test_position_scope_fails_closed_when_bridge_cannot_prove_requested_reader():
    class AllOnlyBridge:
        def is_connected(self) -> bool:
            return True

        def get_all_open_positions(self) -> list[dict[str, Any]]:
            return []

    class CasOnlyBridge:
        def is_connected(self) -> bool:
            return True

        def get_open_positions(self) -> list[dict[str, Any]]:
            return []

    cas_only = build_broker_position_management_snapshot(
        AllOnlyBridge(),
        config=_config(),
        position_scope="CAS_ONLY",
        quote_context_builder=_quote_builder,
    )
    all_account = build_broker_position_management_snapshot(
        CasOnlyBridge(),
        config=_config(),
        position_scope="ALL_ACCOUNT",
        quote_context_builder=_quote_builder,
    )

    assert cas_only["status"] == "BRIDGE_UNAVAILABLE"
    assert "get_open_positions" in cas_only["detail"]
    assert all_account["status"] == "BRIDGE_UNAVAILABLE"
    assert "get_all_open_positions" in all_account["detail"]
