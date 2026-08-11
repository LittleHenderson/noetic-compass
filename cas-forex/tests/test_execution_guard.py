"""Tests for the execution guard -- the chokepoint that finally wires the
pre-execution risk gate into order dispatch.

Covers: config->caps mapping, PASS within caps, REJECT on a cap breach, that a
rejected order never reaches the bridge, and that a live-mode dispatch re-asserts
the owner live-trading authorization before placing anything.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from cas_forex.time_utils import utc_now

from cas_forex.execution_guard import (
    ExecutionBlocked,
    LiveDispatchBlocked,
    build_snapshot_payload,
    caps_from_config,
    evaluate,
    _require_fresh_broker_truth_for_real_dispatch,
    guard,
    guarded_place_order,
)


def _cfg(*, live_mode: bool = False, **overrides) -> SimpleNamespace:
    """A minimal config stand-in with the fields caps_from_config reads."""
    base = dict(
        max_total_exposure_lots=0.5,
        max_open_positions=5,
        max_weekly_drawdown_pct=5.0,
        live_mode=live_mode,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeBridge:
    """Records every place_order call so tests can assert dispatch happened
    (or, on a block, did not)."""

    def __init__(self) -> None:
        self.calls: list = []

    def place_order(self, order):
        self.calls.append(order)
        return {"status": "FILLED", "order": order}


class _FakeRealBridge(_FakeBridge):
    def will_execute_real_order(self) -> bool:
        return True


class _Order:
    def __init__(
        self,
        symbol: str,
        direction: str,
        volume: float,
        *,
        price: float | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> None:
        direction_token = str(direction).strip().upper()
        entry_price = float(price if price is not None else 1.1000)
        if direction_token in {"SHORT", "SELL"}:
            default_stop_loss = entry_price + 0.0010
            default_take_profit = entry_price - 0.0010
        else:
            default_stop_loss = entry_price - 0.0010
            default_take_profit = entry_price + 0.0010
        self.order_id = "test-order-1"
        self.decision_ref = "test-decision-1"
        self.symbol = symbol
        self.direction = direction
        self.volume = volume
        self.price = entry_price
        self.stop_loss = float(stop_loss if stop_loss is not None else default_stop_loss)
        self.take_profit = float(
            take_profit if take_profit is not None else default_take_profit
        )
        self.comment = "TEST"


def _patch_real_dispatch_gates(monkeypatch) -> None:
    from cas_forex import edge_authorization, live_pilot, runtime_gates

    monkeypatch.setattr(runtime_gates, "require_authorized", lambda *args, **kwargs: None)
    monkeypatch.setattr(edge_authorization, "require", lambda *args, **kwargs: None)
    monkeypatch.setattr(edge_authorization, "consume", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_pilot, "require_live_pilot_intent", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        "cas_forex.execution_guard._runtime_live_stage_missing",
        lambda config=None: (
            {
                "live_gate": [],
                "auto_halt": [],
                "broker_truth": [],
                "mt5_terminal_permissions": [],
                "live_recovery": [],
                "live_order_dry_run_review": [],
                "live_risk_snapshot": [],
                "live_pilot": [],
            },
            {"next_action": ""},
        ),
    )
    monkeypatch.setattr(
        "cas_forex.execution_guard._fresh_broker_truth_ready_for_live",
        lambda: True,
    )
    monkeypatch.setattr(
        "cas_forex.execution_guard._action_time_broker_truth_snapshot",
        lambda: {
            "generated_at": utc_now().isoformat(),
            "monitor_status": "BROKER_TRUTH_RECONCILED",
            "overall_status": "RECONCILED",
            "mt5_connected": True,
            "mt5_is_demo": False,
            "mt5_account": 101321,
            "mt5_account_server": "Risen-Trade",
            "mt5_expected_account": 101321,
            "mt5_expected_server": "Risen-Trade",
            "mt5_account_identity_matches_config": True,
            "terminal_unmatched_open_position_count": 0,
            "terminal_pending_receipt_count": 0,
            "terminal_receipt_mismatch_count": 0,
            "fresh_for_live_seconds": 120,
            "action_time_refresh_performed": True,
            "action_time_refresh_error": None,
        },
    )
    monkeypatch.setattr(
        "cas_forex.execution_guard._latest_mt5_permission_snapshot",
        lambda: _mt5_permission_snapshot(),
    )
    monkeypatch.setattr(
        "cas_forex.execution_guard._latest_mt5_live_risk_snapshot",
        lambda: {},
    )
    monkeypatch.setattr(
        "cas_forex.execution_guard._require_fresh_broker_truth_for_real_dispatch",
        lambda: None,
    )


def _live_risk_telemetry(*, stale: bool = False) -> dict:
    return {
        "open_positions": [],
        "data_freshness": {"stale": stale},
    }


def _live_account_snapshot() -> dict:
    return {
        "balance": 1000.0,
        "equity": 1000.0,
        "margin": 0.0,
        "free_margin": 1000.0,
    }


def _mt5_live_risk_snapshot() -> dict:
    return {
        "connected": True,
        "cached": False,
        "is_demo": False,
        "account": {
            "login": 12345,
            "server": "HugosWay-Live",
            "currency": "USD",
            "leverage": 500,
            "balance_usd": 1000.0,
            "equity_usd": 1000.0,
            "margin_used_usd": 0.0,
            "free_margin_usd": 1000.0,
        },
        "positions": [],
        "open_position_count": 0,
    }


def _mt5_permission_snapshot(
    *,
    connected: bool = True,
    is_demo: bool = False,
    login: int = 12345,
    server: str = "HugosWay-Live",
    can_submit_order_send: bool = True,
    blockers: list[str] | None = None,
) -> dict:
    blocker_list = list(blockers or [])
    return {
        "connected": connected,
        "cached": False,
        "is_demo": is_demo,
        "account": {
            "login": login,
            "server": server,
            "currency": "USD",
        },
        "permission_state": {
            "status": "MT5_ORDER_SEND_READY" if can_submit_order_send and not blocker_list else "MT5_ORDER_SEND_BLOCKED",
            "permission_label": "MT5 READY" if can_submit_order_send and not blocker_list else "MT5 ORDER_SEND BLOCKED",
            "can_submit_order_send": can_submit_order_send,
            "blockers": blocker_list,
            "plain_english": (
                "MT5 order_send is ready for the connected real account."
                if can_submit_order_send and not blocker_list
                else "MT5 order_send is blocked before CAS can submit: " + "; ".join(blocker_list or ["Unknown blocker"])
            ),
        },
        "detail": "MT5 terminal permissions snapshot.",
        "error": None,
    }


# ---------------------------------------------------------------------------
# caps_from_config
# ---------------------------------------------------------------------------

def test_caps_from_config_ai_dials_drive_when_owner_has_not_overridden():
    # Owner directive 2026-07-03: with no explicit owner runtime override, the
    # AI operator's dials ARE the enforced caps (dial defaults: 15 open, 3 per
    # symbol, 2.0 total lots) — static config is only the last fallback.
    caps = caps_from_config(_cfg())
    assert caps.max_total_exposure_lots == 2.0
    assert caps.max_open_position_count == 15
    assert caps.max_positions_per_symbol == 3
    assert caps.max_drawdown_pct_from_equity_peak == 5.0
    # Dimensions nothing defines stay uncapped (None), rather than inventing
    # limits the operator never set.
    assert caps.max_concentration_pct is None
    assert caps.max_margin_utilization_pct is None
    assert caps.max_floating_loss_usd is None
    assert caps.max_risk_per_trade_pct == 0.5


def test_caps_from_config_maps_owner_margin_utilization_cap():
    caps = caps_from_config(_cfg(max_margin_utilization_pct=70.0))

    assert caps.max_margin_utilization_pct == 70.0


def test_caps_from_config_owner_override_beats_ai_dial():
    from cas_forex.risk_control import (
        clear_risk_control_overrides,
        set_risk_control_overrides,
    )

    try:
        set_risk_control_overrides(max_concurrent_trades=7, max_total_exposure_lots=9.0)
        caps = caps_from_config(_cfg())
        assert caps.max_open_position_count == 7
        assert caps.max_total_exposure_lots == 9.0
        # The per-symbol dial still applies, held under the owner's open cap.
        assert caps.max_positions_per_symbol == 3
    finally:
        clear_risk_control_overrides()


def test_caps_from_config_follows_the_ai_dial(tmp_path):
    from cas_forex.ai_control_authority import (
        AiControlAuthority,
        get_authority,
        set_authority_for_tests,
    )

    try:
        set_authority_for_tests(AiControlAuthority(tmp_path / "authority.json"))
        control = get_authority().control
        control.adjust("max_concurrent_trades", 4)
        control.adjust("max_positions_per_symbol", 2)
        control.adjust("max_compound_units", 1)
        control.adjust("max_total_exposure_lots", 0.8)
        control.adjust("max_risk_pct_per_trade", 0.25)
        caps = caps_from_config(_cfg())
        assert caps.max_open_position_count == 4
        assert caps.max_positions_per_symbol == 2
        assert caps.max_compound_units == 1
        assert caps.max_total_exposure_lots == 0.8
        assert caps.max_risk_per_trade_pct == 0.25
    finally:
        set_authority_for_tests(None)


# ---------------------------------------------------------------------------
# evaluate (pure)
# ---------------------------------------------------------------------------

def test_evaluate_passes_within_caps():
    decision = evaluate(
        {"symbol": "EURUSD", "direction": "BUY", "lots": 0.1}, config=_cfg()
    )
    assert decision.accepted
    assert decision.decision == "PASS"


def test_quote_only_telemetry_still_hydrates_durable_paper_positions(monkeypatch):
    from cas_forex import paper_outcome_sim

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(
        paper_outcome_sim,
        "open_paper_positions",
        lambda: [
            {
                "symbol": "US30",
                "direction": "SHORT",
                "lots": 0.01,
                "floating_pnl": 0.0,
            }
        ],
    )

    snapshot = build_snapshot_payload(
        live_telemetry={"market_snapshot": {"symbol": "US30", "bid": 52_590.0}}
    )

    assert snapshot["open_position_count"] == 1
    assert snapshot["by_symbol"][0]["symbol"] == "US30"
    assert snapshot["by_symbol"][0]["open_position_count"] == 1


def test_mt5_demo_and_durable_simulator_positions_merge_for_paper_risk(monkeypatch):
    from cas_forex import paper_outcome_sim

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(
        paper_outcome_sim,
        "open_paper_positions",
        lambda: [
            {
                "broker_ticket": 923871908,
                "symbol": "US30",
                "direction": "SHORT",
                "lots": 0.01,
                "floating_pnl": 0.0,
            }
        ],
    )

    snapshot = build_snapshot_payload(
        live_telemetry={
            "open_positions": [
                {
                    "broker_ticket": 7001,
                    "position_risk_source": "MT5Bridge",
                    "symbol": "NAS100",
                    "direction": "LONG",
                    "lots": 0.02,
                    "floating_pnl": 0.0,
                }
            ]
        },
        config=_cfg(live_mode=False),
    )

    assert snapshot["open_position_count"] == 2
    assert {row["symbol"] for row in snapshot["by_symbol"]} == {"NAS100", "US30"}


def test_active_and_durable_views_of_same_simulator_position_count_once(monkeypatch):
    from cas_forex import paper_outcome_sim

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(
        paper_outcome_sim,
        "open_paper_positions",
        lambda: [
            {
                "broker_ticket": 923871908,
                "order_id": "order-1",
                "decision_ref": "decision-1",
                "symbol": "US30",
                "direction": "SHORT",
                "lots": 0.01,
                "entry_price": 52_582.49,
                "floating_pnl": 0.0,
            }
        ],
    )

    snapshot = build_snapshot_payload(
        live_telemetry={
            "open_positions": [
                {
                    "broker_ticket": 923871908,
                    "position_risk_source": "SimulatedBrokerBridge",
                    "symbol": "US30",
                    "direction": "SHORT",
                    "lots": 0.01,
                    "entry_price": 52_582.49,
                    "floating_pnl": 0.0,
                }
            ]
        },
        config=_cfg(live_mode=False),
    )

    assert snapshot["open_position_count"] == 1
    assert snapshot["total_exposure_lots"] == pytest.approx(0.01)


def test_live_risk_does_not_merge_internal_paper_positions(monkeypatch):
    from cas_forex import paper_outcome_sim

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(
        paper_outcome_sim,
        "open_paper_positions",
        lambda: pytest.fail("live risk must not load internal simulator positions"),
    )

    snapshot = build_snapshot_payload(
        live_telemetry={
            "open_positions": [
                {
                    "broker_ticket": 7001,
                    "symbol": "NAS100",
                    "direction": "LONG",
                    "lots": 0.02,
                    "floating_pnl": 0.0,
                }
            ]
        },
        config=_cfg(live_mode=True),
    )

    assert snapshot["open_position_count"] == 1


def test_evaluate_rejects_total_exposure_breach():
    # 2.5 lots on an empty book exceeds the 2.0-lot total-exposure dial.
    decision = evaluate(
        {"symbol": "EURUSD", "direction": "BUY", "lots": 2.5}, config=_cfg()
    )
    assert not decision.accepted
    assert "max_total_exposure_lots" in decision.blocking_caps


def test_evaluate_rejects_missing_fields():
    decision = evaluate({"symbol": "EURUSD"}, config=_cfg())
    assert not decision.accepted
    assert "missing_required_fields" in decision.blocking_caps


# ---------------------------------------------------------------------------
# guard (raises)
# ---------------------------------------------------------------------------

def test_guard_raises_on_breach():
    with pytest.raises(ExecutionBlocked) as exc:
        guard({"symbol": "EURUSD", "direction": "BUY", "lots": 2.5}, config=_cfg())
    assert "max_total_exposure_lots" in exc.value.decision.blocking_caps


def test_guard_returns_decision_on_pass():
    decision = guard(
        {"symbol": "EURUSD", "direction": "BUY", "lots": 0.1}, config=_cfg()
    )
    assert decision.accepted


# ---------------------------------------------------------------------------
# guarded_place_order (full chokepoint)
# ---------------------------------------------------------------------------

def test_guarded_place_order_dispatches_on_pass():
    bridge = _FakeBridge()
    order = _Order("EURUSD", "BUY", 0.1)
    result = guarded_place_order(bridge, order, config=_cfg())
    assert len(bridge.calls) == 1
    assert result["status"] == "FILLED"


def test_guarded_place_order_blocks_and_does_not_touch_bridge():
    bridge = _FakeBridge()
    order = _Order("EURUSD", "BUY", 2.5)  # breaches the total-exposure dial
    with pytest.raises(ExecutionBlocked):
        guarded_place_order(bridge, order, config=_cfg())
    assert bridge.calls == []  # the bridge must never be reached on a block


def test_guarded_place_order_blocks_new_exposure_after_daily_realized_loss_cap(
    monkeypatch,
):
    bridge = _FakeBridge()
    order = _Order("EURUSD", "BUY", 0.1)
    monkeypatch.setattr(
        "cas_forex.daily_loss_guard.effective_daily_loss_cap_usd",
        lambda **_kwargs: (50.0, "test_owner_fenced_control"),
    )
    monkeypatch.setattr(
        "cas_forex.operator_account_context.build_operator_account_context",
        lambda *_args, **_kwargs: {
            "realized_today_usd": -50.13,
            "account_growth_reconciliation": {
                "reconciled": True,
                "event_hash": "growth-proof-1",
            },
        },
    )

    with pytest.raises(ExecutionBlocked) as exc:
        guarded_place_order(bridge, order, config=_cfg())

    assert exc.value.decision.blocking_caps == ("daily_loss_cap_usd",)
    assert "-50.13" in exc.value.decision.plain_english_reason
    assert bridge.calls == []


def test_paper_order_counts_primary_mt5_demo_positions_before_dispatch(monkeypatch):
    class _FakePaperMt5Bridge(_FakeBridge):
        def get_open_positions(self):
            return [
                {
                    "broker_ticket": 7001,
                    "symbol": "EURUSD",
                    "direction": "BUY",
                    "volume": 0.1,
                    "floating_pnl": 0.0,
                }
            ]

    bridge = _FakePaperMt5Bridge()
    order = _Order("EURUSD", "BUY", 0.1)
    monkeypatch.setattr("cas_forex.execution_guard._ai_dial", lambda name: None)

    with pytest.raises(ExecutionBlocked) as exc:
        guarded_place_order(
            bridge,
            order,
            config=_cfg(live_mode=False, max_open_positions=1),
            live_telemetry={"market_snapshot": {"symbol": "EURUSD", "bid": 1.1, "ask": 1.1001}},
        )

    assert "max_open_position_count" in exc.value.decision.blocking_caps
    assert bridge.calls == []


def test_guarded_place_order_live_mode_requires_authorization():
    # live_mode=True with no owner enable flags / creds -> the live-trading
    # gate is NOT LICENSED, so dispatch must raise before the bridge is hit.
    bridge = _FakeBridge()
    order = _Order("EURUSD", "BUY", 0.1)  # within risk caps; the block is the live gate
    with pytest.raises(PermissionError):
        guarded_place_order(bridge, order, config=_cfg(live_mode=True))
    assert bridge.calls == []


def test_fresh_broker_truth_gate_fails_closed_when_monitor_is_not_ready(monkeypatch):
    monkeypatch.setattr(
        "cas_forex.execution_guard._fresh_broker_truth_ready_for_live",
        lambda: False,
    )

    with pytest.raises(PermissionError, match="(?i)fresh broker truth( is)? required before real dispatch"):
        _require_fresh_broker_truth_for_real_dispatch()


def test_guarded_place_order_real_dispatch_requires_fresh_broker_truth(monkeypatch):
    _patch_real_dispatch_gates(monkeypatch)
    monkeypatch.setattr(
        "cas_forex.execution_guard._fresh_broker_truth_ready_for_live",
        lambda: False,
    )
    monkeypatch.setattr(
        "cas_forex.execution_guard._action_time_broker_truth_snapshot",
        lambda: {},
    )
    bridge = _FakeRealBridge()
    order = _Order("EURUSD", "BUY", 0.1)

    with pytest.raises(PermissionError, match="(?i)fresh broker truth( is)? required before real dispatch"):
        guarded_place_order(
            bridge,
            order,
            config=_cfg(),
            live_telemetry=_live_risk_telemetry(),
            account_snapshot=_live_account_snapshot(),
        )

    assert bridge.calls == []


def test_guarded_place_order_real_dispatch_uses_action_time_broker_truth_report_over_cached_helper(monkeypatch):
    _patch_real_dispatch_gates(monkeypatch)
    monkeypatch.setattr(
        "cas_forex.execution_guard._fresh_broker_truth_ready_for_live",
        lambda: False,
    )
    bridge = _FakeRealBridge()
    order = _Order("EURUSD", "BUY", 0.1)

    result = guarded_place_order(
        bridge,
        order,
        config=_cfg(),
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
    )

    assert len(bridge.calls) == 1
    assert result["status"] == "FILLED"


def test_guarded_place_order_blocks_fresh_non_demo_truth_for_wrong_account(monkeypatch):
    _patch_real_dispatch_gates(monkeypatch)
    monkeypatch.setattr(
        "cas_forex.execution_guard._action_time_broker_truth_snapshot",
        lambda: {
            "generated_at": utc_now().isoformat(),
            "overall_status": "RECONCILED",
            "mt5_connected": True,
            "mt5_is_demo": False,
            "mt5_account": 777777,
            "mt5_account_server": "Risen-Trade",
            "mt5_expected_account": 101321,
            "mt5_expected_server": "Risen-Trade",
            "mt5_account_identity_matches_config": False,
            "fresh_for_live_seconds": 120,
            "action_time_refresh_performed": True,
        },
    )
    bridge = _FakeRealBridge()

    with pytest.raises(PermissionError, match="(?i)fresh broker truth"):
        guarded_place_order(
            bridge,
            _Order("EURUSD", "BUY", 0.1),
            config=_cfg(),
            live_telemetry=_live_risk_telemetry(),
            account_snapshot=_live_account_snapshot(),
        )

    assert bridge.calls == []


def test_guarded_place_order_real_dispatch_blocks_on_failed_action_time_broker_truth_report_even_if_cached_helper_is_true(monkeypatch):
    _patch_real_dispatch_gates(monkeypatch)
    monkeypatch.setattr(
        "cas_forex.execution_guard._action_time_broker_truth_snapshot",
        lambda: {
            "generated_at": utc_now().isoformat(),
            "monitor_status": "BROKER_TRUTH_RECONCILIATION_FAILED",
            "overall_status": "RECONCILIATION_FAILED",
            "mt5_connected": True,
            "mt5_is_demo": False,
            "terminal_unmatched_open_position_count": 1,
            "terminal_pending_receipt_count": 1,
            "terminal_receipt_mismatch_count": 0,
            "fresh_for_live_seconds": 120,
            "action_time_refresh_performed": True,
            "action_time_refresh_error": None,
            "next_action": "Keep CAS in paper/fail-closed mode and inspect broker-truth mismatches before allowing another live cycle.",
        },
    )
    bridge = _FakeRealBridge()
    order = _Order("EURUSD", "BUY", 0.1)

    with pytest.raises(LiveDispatchBlocked, match="(?i)fresh broker truth"):
        guarded_place_order(
            bridge,
            order,
            config=_cfg(),
            live_telemetry=_live_risk_telemetry(),
            account_snapshot=_live_account_snapshot(),
        )

    assert bridge.calls == []


def test_guarded_place_order_real_dispatch_requires_live_risk_snapshot(monkeypatch):
    _patch_real_dispatch_gates(monkeypatch)
    bridge = _FakeRealBridge()
    order = _Order("EURUSD", "BUY", 0.1)

    with pytest.raises(PermissionError, match="(?i)fresh live risk (telemetry|snapshot) is required"):
        guarded_place_order(bridge, order, config=_cfg())

    assert bridge.calls == []


def test_guarded_place_order_real_dispatch_accepts_explicit_live_risk_snapshot(monkeypatch):
    _patch_real_dispatch_gates(monkeypatch)
    bridge = _FakeRealBridge()
    order = _Order("EURUSD", "BUY", 0.1)

    result = guarded_place_order(
        bridge,
        order,
        config=_cfg(),
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
    )

    assert len(bridge.calls) == 1
    assert result["status"] == "FILLED"


def test_guarded_place_order_real_dispatch_blocks_on_closed_market(monkeypatch):
    _patch_real_dispatch_gates(monkeypatch)
    bridge = _FakeRealBridge()
    order = _Order("EURUSD", "BUY", 0.1)
    live_telemetry = _live_risk_telemetry()
    live_telemetry["market_open"] = False

    with pytest.raises(LiveDispatchBlocked) as exc:
        guarded_place_order(
            bridge,
            order,
            config=_cfg(),
            live_telemetry=live_telemetry,
            account_snapshot=_live_account_snapshot(),
        )

    assert exc.value.stage == "market_availability"
    assert "market/session availability blocked" in exc.value.detail.lower()
    assert bridge.calls == []


def test_guarded_place_order_real_dispatch_blocks_on_macro_blackout(monkeypatch):
    _patch_real_dispatch_gates(monkeypatch)
    bridge = _FakeRealBridge()
    order = _Order("EURUSD", "BUY", 0.1)
    live_telemetry = _live_risk_telemetry()
    live_telemetry["market_open"] = True
    live_telemetry["macro_blackout_active"] = True

    with pytest.raises(LiveDispatchBlocked) as exc:
        guarded_place_order(
            bridge,
            order,
            config=_cfg(macro_blackout_enabled=True),
            live_telemetry=live_telemetry,
            account_snapshot=_live_account_snapshot(),
        )

    assert exc.value.stage == "macro_blackout"
    assert "macro" in exc.value.detail.lower()
    assert bridge.calls == []


def test_guarded_place_order_real_dispatch_blocks_on_execution_quality(monkeypatch):
    _patch_real_dispatch_gates(monkeypatch)
    bridge = _FakeRealBridge()
    order = _Order("EURUSD", "BUY", 0.1)
    live_telemetry = _live_risk_telemetry()
    live_telemetry["market_open"] = True
    live_telemetry["spread_pips"] = 4.2

    with pytest.raises(LiveDispatchBlocked) as exc:
        guarded_place_order(
            bridge,
            order,
            config=_cfg(broker_max_spread_pips=1.5),
            live_telemetry=live_telemetry,
            account_snapshot=_live_account_snapshot(),
        )

    assert exc.value.stage == "execution_quality"
    assert "execution quality blocked" in exc.value.detail.lower()
    assert bridge.calls == []


def test_guarded_place_order_real_dispatch_blocks_on_order_constraints(monkeypatch):
    _patch_real_dispatch_gates(monkeypatch)
    bridge = _FakeRealBridge()
    order = _Order("EURUSD", "BUY", 0.1)
    live_telemetry = _live_risk_telemetry()
    live_telemetry["market_open"] = True

    with pytest.raises(LiveDispatchBlocked) as exc:
        guarded_place_order(
            bridge,
            order,
            config=_cfg(broker_min_lot=0.2),
            live_telemetry=live_telemetry,
            account_snapshot=_live_account_snapshot(),
        )

    assert exc.value.stage == "order_constraints"
    assert "broker order constraints blocked" in exc.value.detail.lower()
    assert bridge.calls == []


def test_guarded_place_order_real_dispatch_blocks_on_unresolved_broker_symbol(monkeypatch):
    _patch_real_dispatch_gates(monkeypatch)

    class _BrokerAwareRealBridge(_FakeRealBridge):
        def connect(self):
            return True

        def is_connected(self):
            return True

        def symbol_info(self, symbol):
            return None

        def symbols_get(self, pattern=None):
            return []

    bridge = _BrokerAwareRealBridge()
    order = _Order("EURUSD", "BUY", 0.1)
    live_telemetry = _live_risk_telemetry()
    live_telemetry["market_open"] = True

    with pytest.raises(LiveDispatchBlocked) as exc:
        guarded_place_order(
            bridge,
            order,
            config=_cfg(),
            live_telemetry=live_telemetry,
            account_snapshot=_live_account_snapshot(),
        )

    assert exc.value.stage == "order_constraints"
    assert "No visible MT5 symbol was found" in exc.value.detail
    assert bridge.calls == []


def test_guarded_place_order_real_dispatch_blocks_on_broker_lot_step(monkeypatch):
    _patch_real_dispatch_gates(monkeypatch)

    class _BrokerAwareRealBridge(_FakeRealBridge):
        def connect(self):
            return True

        def is_connected(self):
            return True

        def symbol_info(self, symbol):
            if symbol != "EURUSD":
                return None
            return SimpleNamespace(
                point=0.00001,
                digits=5,
                trade_mode=4,
                volume_min=0.1,
                volume_step=0.1,
                volume_max=10.0,
                trade_stops_level=0,
                trade_freeze_level=0,
            )

        def symbols_get(self, pattern=None):
            return [SimpleNamespace(name="EURUSD")]

    bridge = _BrokerAwareRealBridge()
    order = _Order("EURUSD", "BUY", 0.15)
    live_telemetry = _live_risk_telemetry()
    live_telemetry["market_open"] = True

    with pytest.raises(LiveDispatchBlocked) as exc:
        guarded_place_order(
            bridge,
            order,
            config=_cfg(),
            live_telemetry=live_telemetry,
            account_snapshot=_live_account_snapshot(),
        )

    assert exc.value.stage == "order_constraints"
    assert "broker lot step 0.1" in exc.value.detail
    assert bridge.calls == []


def test_guarded_place_order_real_dispatch_accepts_market_quality_and_constraint_evidence(monkeypatch):
    _patch_real_dispatch_gates(monkeypatch)
    bridge = _FakeRealBridge()
    order = _Order("EURUSD", "BUY", 0.1)
    live_telemetry = _live_risk_telemetry()
    live_telemetry.update(
        {
            "market_open": True,
            "macro_blackout_active": False,
            "spread_pips": 1.2,
            "slippage_pips": 0.4,
            "bid": 1.1000,
            "ask": 1.1002,
        }
    )

    result = guarded_place_order(
        bridge,
        order,
        config=_cfg(
            macro_blackout_enabled=True,
            broker_max_spread_pips=2.5,
            broker_max_slippage_pips=1.0,
            broker_min_lot=0.01,
            broker_max_lot=1.0,
            broker_min_stop_distance_pips=5.0,
        ),
        live_telemetry=live_telemetry,
        account_snapshot=_live_account_snapshot(),
    )

    assert len(bridge.calls) == 1
    assert result["status"] == "FILLED"


def test_guarded_place_order_real_dispatch_self_hydrates_mt5_risk_snapshot(monkeypatch):
    _patch_real_dispatch_gates(monkeypatch)
    monkeypatch.setattr(
        "cas_forex.execution_guard._latest_mt5_live_risk_snapshot",
        lambda: _mt5_live_risk_snapshot(),
    )
    bridge = _FakeRealBridge()
    order = _Order("EURUSD", "BUY", 0.1)
    config = _cfg(
        live_mode=True,
        owner_enable_live_trading=True,
        live_trading_licensed=True,
        mt5_login=12345,
        mt5_password="pw",
        mt5_server="HugosWay-Live",
        prefer_mt5=True,
        personal_account_ack=True,
        no_pooled_capital_ack=True,
        account_type="personal",
        selected_broker_id="hugosway",
    )

    result = guarded_place_order(bridge, order, config=config)

    assert len(bridge.calls) == 1
    assert result["status"] == "FILLED"


def test_guarded_place_order_real_dispatch_requires_mt5_terminal_permissions(monkeypatch):
    _patch_real_dispatch_gates(monkeypatch)
    monkeypatch.setattr(
        "cas_forex.execution_guard._runtime_live_stage_missing",
        lambda config=None: ({stage: [] for stage in ("live_gate", "auto_halt", "broker_truth", "mt5_terminal_permissions", "live_recovery", "live_order_dry_run_review", "live_risk_snapshot", "live_pilot")}, {}),
    )
    monkeypatch.setattr(
        "cas_forex.execution_guard._fresh_broker_truth_ready_for_live",
        lambda: True,
    )
    monkeypatch.setattr(
        "cas_forex.execution_guard._latest_mt5_permission_snapshot",
        lambda: _mt5_permission_snapshot(
            can_submit_order_send=False,
            blockers=["MT5 Algo Trading is off in the terminal."],
        ),
    )

    bridge = _FakeRealBridge()
    order = _Order("EURUSD", "BUY", 0.1)
    config = _cfg(
        live_mode=True,
        owner_enable_live_trading=True,
        live_trading_licensed=True,
        mt5_login=12345,
        mt5_password="pw",
        mt5_server="HugosWay-Live",
        prefer_mt5=True,
        personal_account_ack=True,
        no_pooled_capital_ack=True,
        account_type="personal",
        selected_broker_id="hugosway",
    )

    with pytest.raises(LiveDispatchBlocked, match="Algo Trading is off"):
        guarded_place_order(
            bridge,
            order,
            config=config,
            live_telemetry=_live_risk_telemetry(),
            account_snapshot=_live_account_snapshot(),
        )

    assert bridge.calls == []
