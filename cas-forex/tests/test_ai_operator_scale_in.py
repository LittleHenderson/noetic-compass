from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from cas_forex.ai_hedge_management_cycle import run_ai_hedge_management_cycle
from cas_forex.ai_operator_scale_in import build_winning_scale_in_actions
from cas_forex.broker.mt5_bridge import SimulatedBrokerBridge
from cas_forex.operator_scale_in_authorization import (
    OperatorScaleInNotAuthorized,
    authorize as authorize_scale_in,
    require as require_scale_in,
    reset as reset_scale_in_authorization,
)
from cas_forex.schemas.order import BrokerOrderRequest


class _WinningBridge(SimulatedBrokerBridge):
    def __init__(self, state_path):
        from cas_forex.time_utils import utc_now

        super().__init__(state_path=state_path, max_lot=1.0)
        self._positions = {
            7001: {
                "order": _parent_order(),
                "fill_price": 1.1000,
                "volume": 0.10,
                "current_price": 1.1020,
                "timestamp": utc_now(),
            }
        }
        self._persist_state()
        self.reported_profit = 20.0
        self.reported_swap = 0.0

    def symbol_info(self, symbol):
        return SimpleNamespace(
            point=0.00001,
            digits=5,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            trade_contract_size=100_000.0,
            trade_tick_size=0.00001,
            trade_tick_value=1.0,
            trade_tick_value_loss=1.0,
            trade_tick_value_profit=1.0,
            trade_stops_level=0,
            trade_freeze_level=0,
        )

    def symbols_get(self, pattern=None):
        return [SimpleNamespace(name="EURUSD")]

    def get_open_positions(self):
        rows = super().get_open_positions()
        for row in rows:
            if row["ticket"] == 7001:
                row["current_price"] = 1.1020
                row["profit"] = self.reported_profit
                row["swap"] = self.reported_swap
        return rows

    def get_open_positions_all(self):
        return self.get_open_positions()


class _ScaleInProvider:
    def generate(self, prompt, system=None, **kwargs):
        payload = json.loads(prompt)
        group = payload["position_action_candidates"][0]
        scale_actions = [row for row in group["actions"] if row.get("intent") == "scale_in"]
        selected = max(scale_actions, key=lambda row: float(row.get("volume") or 0.0))
        return {
            "ok": True,
            "text": json.dumps(
                {
                    "position_decisions": [
                        {
                            "position_key": group["position_key"],
                            "decision": "SELECT",
                            "action_ref": selected["action_ref"],
                            "conviction": "HIGH",
                            "reason": "The parent remains protected and winning; select the exact bounded add.",
                        }
                    ],
                    "summary": "Compound the protected winner with the bounded high-conviction size.",
                }
            ),
            "provider": "claude",
            "provider_label": "Claude test",
            "paid": True,
            "failover": False,
            "error": None,
        }


def _parent_order():
    from cas_forex.schemas.forecast import Direction
    from cas_forex.schemas.order import BrokerOrderRequest, OrderType

    return BrokerOrderRequest(
        order_id="parent-eurusd",
        decision_ref="parent-eurusd",
        symbol="EUR/USD",
        order_type=OrderType.MARKET,
        direction=Direction.LONG,
        volume=0.10,
        price=1.1000,
        stop_loss=1.0990,
        take_profit=1.1060,
        comment="CAS_PARENT",
    )


def _caps(*, max_positions_per_symbol=3, max_compound_units=1):
    from cas_forex.pre_execution_risk_gate import RiskCapConfig

    return RiskCapConfig(
        max_risk_per_trade_pct=0.5,
        max_total_exposure_lots=1.0,
        max_concentration_pct=None,
        max_margin_utilization_pct=70.0,
        max_positions_per_symbol=max_positions_per_symbol,
        max_open_position_count=6,
        max_drawdown_pct_from_equity_peak=None,
        max_floating_loss_usd=None,
        max_compound_units=max_compound_units,
    )


def _config():
    return SimpleNamespace(
        live_mode=False,
        ai_scale_in_enabled=True,
        ai_scale_in_min_profit_r=0.5,
        ai_scale_in_max_parent_multiple=1.0,
        ai_hedge_position_scope="ALL_ACCOUNT",
        ai_hedge_management_attempt_cooldown_seconds=1,
        ai_hedge_management_max_actions_per_cycle=8,
        dispatch_quote_max_age_seconds=120,
        max_risk_per_trade_pct=0.5,
        max_total_exposure_lots=1.0,
        max_open_positions=6,
    )


def _quote(symbol, **kwargs):
    from cas_forex.time_utils import utc_now

    return {
        "quote_source": "test",
        "quote_feed_label": "fresh test quote",
        "market_snapshot": {
            "symbol": symbol,
            "bid": 1.1020,
            "ask": 1.1021,
            "spread": 1.0,
            "is_market_open": True,
            "timestamp": utc_now().isoformat(),
            "source": "test",
        },
    }


def test_scale_in_builder_offers_exact_sizes_only_for_protected_winner(monkeypatch, tmp_path):
    from cas_forex import execution_guard
    from cas_forex.ai_hedge_management_cycle import build_broker_position_management_snapshot

    monkeypatch.setattr(execution_guard, "caps_from_config", lambda config=None: _caps())
    bridge = _WinningBridge(tmp_path / "sim.json")
    snapshot = build_broker_position_management_snapshot(
        bridge,
        config=_config(),
        position_scope="ALL_ACCOUNT",
        quote_context_builder=_quote,
    )
    report = build_winning_scale_in_actions(snapshot, bridge=bridge, config=_config())

    assert report["status"] == "SCALE_IN_OPTIONS_READY"
    assert report["parent_candidate_count"] == 1
    assert all(row["intent"] == "scale_in" for row in report["actions"])
    assert all(row["parent_broker_ticket"] == "7001" for row in report["actions"])
    assert all(row["volume"] > 0 for row in report["actions"])
    assert report["daily_profit_target_used_for_sizing"] is False


def test_scale_in_same_side_exposure_collapses_supported_broker_aliases():
    from cas_forex.ai_operator_scale_in import _symbol_side_volume

    class AliasBridge:
        def get_open_positions(self):
            return [
                {"symbol": "USTEC.cash", "side": "LONG", "volume": 0.20},
                {"symbol": "NAS100", "side": "LONG", "volume": 0.10},
                {"symbol": "NAS100", "side": "SHORT", "volume": 0.40},
            ]

    assert _symbol_side_volume(AliasBridge(), "NAS100", "LONG") == 0.30


def test_scale_in_builder_blocks_pre_cost_winner_that_is_net_loser(monkeypatch, tmp_path):
    from cas_forex import execution_guard
    from cas_forex.ai_hedge_management_cycle import build_broker_position_management_snapshot

    monkeypatch.setattr(execution_guard, "caps_from_config", lambda config=None: _caps())
    bridge = _WinningBridge(tmp_path / "sim.json")
    bridge.reported_profit = 1.0
    bridge.reported_swap = -2.0
    snapshot = build_broker_position_management_snapshot(
        bridge,
        config=_config(),
        position_scope="ALL_ACCOUNT",
        quote_context_builder=_quote,
    )

    report = build_winning_scale_in_actions(snapshot, bridge=bridge, config=_config())

    assert snapshot["positions"][0]["position_price_pnl_usd"] == 1.0
    assert snapshot["positions"][0]["net_open_pnl_after_reported_costs_usd"] == -1.0
    assert report["status"] == "NO_SCALE_IN_CANDIDATE"
    assert report["actions"] == []
    assert "not net winning after reported carry and costs" in report["blockers"][0]["reason"]


def test_scale_in_r_uses_original_entry_stop_after_breakeven(tmp_path):
    bridge = _WinningBridge(tmp_path / "sim.json")
    snapshot = {
        "timestamp": "2026-07-13T17:30:42+00:00",
        "positions": [
            {
                "broker_ticket": "9001",
                "row_id": "broker:9001",
                "symbol": "EUR/USD",
                "side": "LONG",
                "lot_size": 0.10,
                "open_price": 1.1000,
                "current_price": 1.1002,
                "stop_loss": 1.1000,
                "original_stop_loss": 1.0990,
                "take_profit": 1.1060,
                "floating_pnl_usd": 2.0,
                "position_price_pnl_usd": 2.0,
                "swap_usd": 0.0,
                "commission_usd": 0.0,
                "net_open_pnl_after_reported_costs_usd": 2.0,
                "price_stale": False,
            }
        ],
    }

    report = build_winning_scale_in_actions(
        snapshot,
        bridge=bridge,
        config=_config(),
    )

    assert report["status"] == "NO_SCALE_IN_CANDIDATE"
    assert report["threshold_waiting_parent_count"] == 1
    blocker = report["blockers"][0]
    assert blocker["reason_code"] == "BELOW_SCALE_IN_THRESHOLD"
    assert blocker["current_r"] == 0.2
    assert blocker["minimum_profit_r"] == 0.5
    assert blocker["distance_to_threshold_r"] == 0.3
    assert blocker["r_multiple_basis"] == "ORIGINAL_ENTRY_STOP_FROM_ORDER_RECEIPT"


def test_scale_in_does_not_invent_r_when_breakeven_parent_lacks_original_stop(tmp_path):
    bridge = _WinningBridge(tmp_path / "sim.json")
    snapshot = {
        "positions": [
            {
                "broker_ticket": "9002",
                "symbol": "EUR/USD",
                "side": "LONG",
                "lot_size": 0.10,
                "open_price": 1.1000,
                "current_price": 1.1002,
                "stop_loss": 1.1000,
                "take_profit": 1.1060,
                "net_open_pnl_after_reported_costs_usd": 2.0,
                "price_stale": False,
            }
        ],
    }

    report = build_winning_scale_in_actions(
        snapshot,
        bridge=bridge,
        config=_config(),
    )

    assert report["actions"] == []
    blocker = report["blockers"][0]
    assert blocker["reason_code"] == "ORIGINAL_RISK_GEOMETRY_UNAVAILABLE"
    assert blocker["current_r"] == 0.0
    assert blocker["r_multiple_basis"] == "UNAVAILABLE_NO_ORIGINAL_OR_ADVERSE_STOP"


def test_scale_in_authorization_rechecks_net_profit_and_parent_geometry(monkeypatch, tmp_path):
    from cas_forex import execution_guard
    from cas_forex.ai_hedge_management_cycle import build_broker_position_management_snapshot

    reset_scale_in_authorization()
    monkeypatch.setattr(execution_guard, "caps_from_config", lambda config=None: _caps())
    bridge = _WinningBridge(tmp_path / "sim.json")
    snapshot = build_broker_position_management_snapshot(
        bridge,
        config=_config(),
        position_scope="ALL_ACCOUNT",
        quote_context_builder=_quote,
    )
    action = build_winning_scale_in_actions(
        snapshot, bridge=bridge, config=_config()
    )["actions"][0]
    order = BrokerOrderRequest.model_validate(action["order_request"])
    authorization = authorize_scale_in(
        order,
        parent_position=action["parent_position"],
        operator_event_hash="operator-event-net-profit",
        sizing_plan_hash=action["sizing_plan_hash"],
        sizing_ref=action["sizing_ref"],
        bridge=bridge,
        config=_config(),
    )
    proposed = {
        "parent_broker_ticket": action["parent_broker_ticket"],
        "operator_event_hash": "operator-event-net-profit",
        "sizing_plan_hash": action["sizing_plan_hash"],
        "sizing_ref": action["sizing_ref"],
    }

    assert authorization["parent_snapshot_hash"]
    bridge.reported_swap = -25.0
    with pytest.raises(OperatorScaleInNotAuthorized, match="no longer net winning"):
        require_scale_in(order, proposed_intent=proposed, bridge=bridge, config=_config())

    bridge.reported_swap = 0.0
    bridge.modify_position(7001, stop_loss=1.1005)
    with pytest.raises(OperatorScaleInNotAuthorized, match="protective geometry changed"):
        require_scale_in(order, proposed_intent=proposed, bridge=bridge, config=_config())


def test_operator_scale_in_executes_once_and_reconciles_added_volume(monkeypatch, tmp_path):
    from cas_forex import execution_guard, order_attempt_audit, order_dispatch

    reset_scale_in_authorization()
    monkeypatch.setattr(
        execution_guard,
        "caps_from_config",
        lambda config=None: _caps(max_positions_per_symbol=1, max_compound_units=1),
    )
    monkeypatch.setattr(execution_guard, "_is_live_execution", lambda config=None: False)
    monkeypatch.setattr(order_dispatch, "_mode_from_config", lambda config=None: "PAPER")
    monkeypatch.setattr(order_attempt_audit, "DEFAULT_STATE_PATH", tmp_path / "orders.json")
    monkeypatch.setattr(order_attempt_audit, "DEFAULT_AUDIT_PATH", tmp_path / "orders.jsonl")
    bridge = _WinningBridge(tmp_path / "sim.json")
    report = run_ai_hedge_management_cycle(
        bridge=bridge,
        config=_config(),
        position_scope="ALL_ACCOUNT",
        execute=True,
        state_path=tmp_path / "cycle-state.json",
        audit_path=tmp_path / "management-audit.jsonl",
        quote_context_builder=_quote,
        operator_provider=_ScaleInProvider(),
        operator_review_enabled=True,
        operator_audit_path=tmp_path / "operator-audit.jsonl",
        operator_latest_path=tmp_path / "operator-latest.json",
        scale_in_audit_path=tmp_path / "scale-in-audit.jsonl",
    )

    assert report["status"] == "ACTIONS_EXECUTED"
    assert report["operator_position_edge"]["status"] == "AI_OPERATOR_POSITION_DECIDED"
    assert report["scale_in_status"] == "SCALE_IN_OPTIONS_READY"
    assert report["scale_in_action_count"] > 0
    assert report["scale_in_parent_candidate_count"] == 1
    assert report["scale_in_blocker_count"] == 0
    assert report["scale_in_blockers"] == []
    assert report["scale_in_max_compound_units"] > 0
    assert report["draft_action_count"] >= report["scale_in_action_count"]
    execution = report["executions"][0]
    assert execution["status"] == "EXECUTED_RECONCILED"
    slot_policy = execution["compound_slot_policy"]
    assert slot_policy["base_max_positions_per_symbol"] == 1
    assert slot_policy["authorized_compound_slot_allowance"] == 1
    assert slot_policy["effective_max_positions_per_symbol"] == 2
    assert slot_policy["ordinary_entry_cap_unchanged"] is True
    provenance = execution["dispatch_result"]["execution_provenance"]
    assert provenance["operator_decision"]["action_ref"]
    assert provenance["operator_decision"]["decision"] == "SELECT"
    assert provenance["operator_decision"]["provider"] == "claude"
    assert provenance["operator_decision"]["reason"]
    assert provenance["operator_decision"]["operator_event_hash"]
    assert provenance["version_trace"]["model_provider"] == "claude"
    assert execution["terminal_receipt"]["actual_after_volume"] > 0.10
    assert len(bridge.get_open_positions()) == 2
    state = json.loads((tmp_path / "cycle-state.json").read_text(encoding="utf-8"))
    assert state["scale_in_units_by_parent"]["7001"] == 1
