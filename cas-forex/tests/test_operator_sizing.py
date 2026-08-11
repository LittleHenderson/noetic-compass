from __future__ import annotations

import json
from types import SimpleNamespace

from cas_forex.agent_state import OverseerDecision, RouteIntent
from cas_forex.ai_operator_trade_edge import review_and_size_route_intents_with_operator
from cas_forex.operator_sizing import build_operator_sizing_plan
from cas_forex.schemas.forecast import Direction
from cas_forex.schemas.order import BrokerOrderRequest, OrderType
from cas_forex.time_utils import utc_now


class _SizingBridge:
    def symbol_info(self, symbol):
        return SimpleNamespace(
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

    def symbols_get(self, pattern=None):
        return [SimpleNamespace(name="US30")]

    def get_account_info(self):
        return {
            "balance": 44_757.89,
            "equity": 44_555.70,
            "margin": 411.75,
            "margin_free": 44_143.95,
            "leverage": 500,
        }

    def get_open_positions(self):
        return []

    def will_execute_real_order(self):
        return False


class _Provider:
    def generate(self, prompt, system=None, **kwargs):
        candidate = json.loads(prompt)["candidates"][0]
        selected = candidate["sizing_options"][-1]
        return {
            "ok": True,
            "text": json.dumps(
                {
                    "candidate_decisions": [
                        {
                            "intent_id": candidate["intent_id"],
                            "decision": "APPROVE",
                            "sizing_ref": selected["sizing_ref"],
                            "conviction": "HIGH",
                            "reason": "Current edge and account context justify pressing this exact bounded size.",
                        }
                    ],
                    "summary": "Select the high-conviction bounded lot option.",
                }
            ),
            "provider": "claude",
            "provider_label": "Claude test",
            "paid": True,
            "failover": False,
            "error": None,
        }


class _MissingSizingProvider(_Provider):
    def generate(self, prompt, system=None, **kwargs):
        result = super().generate(prompt, system=system, **kwargs)
        reply = json.loads(result["text"])
        reply["candidate_decisions"][0].pop("sizing_ref", None)
        result["text"] = json.dumps(reply)
        return result


def _caps():
    return SimpleNamespace(
        max_risk_per_trade_pct=0.1,
        max_total_exposure_lots=0.5,
        max_margin_utilization_pct=70.0,
        max_positions_per_symbol=3,
        max_open_position_count=5,
    )


def _intent(plan, *, regime: str | None = None):
    order = BrokerOrderRequest(
        order_id="operator-sized-us30",
        decision_ref="operator-sized-us30",
        symbol="US30",
        order_type=OrderType.MARKET,
        direction=Direction.SHORT,
        volume=0.01,
        price=0.0,
        stop_loss=52_617.82,
        take_profit=52_374.18,
        comment="CAS_SIZED",
    )
    runtime_context = {"operator_sizing_plan": plan}
    if regime is not None:
        runtime_context["setup"] = SimpleNamespace(
            regime=regime,
            signal_strength=0.8,
        )
    return RouteIntent(
        intent_id="intent-operator-sized-us30",
        agent_id="live_candle_agent",
        action="OPEN_LIVE_CANDLE_LEARNING",
        symbol="US30",
        timeframe="H1",
        strategy_setting="live_candle_test",
        direction="SHORT",
        confidence=0.8,
        evidence_score=2.0,
        lot_size=0.01,
        entry_price=52_597.82,
        stop_loss=52_617.82,
        take_profit=52_374.18,
        reason="fresh candidate",
        order_request=order.model_dump(mode="json"),
        _runtime_context=runtime_context,
    )


def test_sizing_plan_offers_more_than_broker_minimum_when_money_math_allows(monkeypatch):
    from cas_forex import execution_guard

    monkeypatch.setattr(execution_guard, "caps_from_config", lambda config=None: _caps())
    plan = build_operator_sizing_plan(
        symbol="US30",
        direction="SHORT",
        entry_price=52_597.82,
        stop_loss=52_617.82,
        take_profit=52_374.18,
        seed_lots=0.01,
        bridge=_SizingBridge(),
        config=SimpleNamespace(),
    )

    assert plan["status"] == "OPTIONS_READY"
    assert plan["max_executable_lots"] == 0.02
    assert [row["lots"] for row in plan["options"]] == [0.01, 0.02]
    assert plan["options"][-1]["risk_at_stop_pct_equity"] == 0.0898
    assert plan["daily_profit_target_used_for_sizing"] is False
    assert plan["target_deficit_may_increase_size"] is False


def test_sizing_plan_counts_broker_alias_position_against_canonical_symbol_cap(monkeypatch):
    from cas_forex import execution_guard

    caps = _caps()
    caps.max_positions_per_symbol = 1
    monkeypatch.setattr(execution_guard, "caps_from_config", lambda config=None: caps)

    class AliasExposureBridge(_SizingBridge):
        def get_open_positions(self):
            return [{"symbol": "DJ30.cash", "volume": 0.01, "side": "LONG"}]

    plan = build_operator_sizing_plan(
        symbol="US30",
        direction="SHORT",
        entry_price=52_597.82,
        stop_loss=52_617.82,
        take_profit=52_374.18,
        seed_lots=0.01,
        bridge=AliasExposureBridge(),
        config=SimpleNamespace(),
    )

    assert plan["status"] == "NO_COMPLIANT_SIZE"
    assert plan["portfolio_snapshot"]["symbol_position_count"] == 1
    assert "per-symbol position cap is already full" in plan["blockers"][0]


def test_scale_in_plan_reserves_only_dedicated_compound_slots(monkeypatch):
    from cas_forex import execution_guard

    caps = _caps()
    caps.max_positions_per_symbol = 1
    monkeypatch.setattr(execution_guard, "caps_from_config", lambda config=None: caps)

    class ParentBridge(_SizingBridge):
        def get_open_positions(self):
            return [{"symbol": "DJ30.cash", "volume": 0.01, "side": "SHORT"}]

    bridge = ParentBridge()
    entry_plan = build_operator_sizing_plan(
        symbol="US30",
        direction="SHORT",
        entry_price=52_597.82,
        stop_loss=52_617.82,
        take_profit=52_374.18,
        seed_lots=0.01,
        bridge=bridge,
        config=SimpleNamespace(),
    )
    scale_plan = build_operator_sizing_plan(
        symbol="US30",
        direction="SHORT",
        entry_price=52_597.82,
        stop_loss=52_617.82,
        take_profit=52_374.18,
        seed_lots=0.01,
        bridge=bridge,
        config=SimpleNamespace(),
        purpose="SCALE_IN",
        parent_position={"lot_size": 0.01},
        compound_slot_allowance=1,
    )

    assert entry_plan["status"] == "NO_COMPLIANT_SIZE"
    assert scale_plan["status"] == "OPTIONS_READY"
    assert scale_plan["compound_slot_allowance"] == 1
    assert scale_plan["cap_snapshot"]["max_positions_per_symbol"] == 1
    assert scale_plan["effective_max_positions_per_symbol"] == 2
    assert scale_plan["options"]


def test_operator_explicit_sizing_ref_binds_approved_order_to_exact_larger_option(monkeypatch, tmp_path):
    from cas_forex import execution_guard

    monkeypatch.setattr(execution_guard, "caps_from_config", lambda config=None: _caps())
    bridge = _SizingBridge()
    plan = build_operator_sizing_plan(
        symbol="US30",
        direction="SHORT",
        entry_price=52_597.82,
        stop_loss=52_617.82,
        take_profit=52_374.18,
        seed_lots=0.01,
        bridge=bridge,
        config=SimpleNamespace(),
    )
    intent = _intent(plan, regime="directional_pressure")
    decision = OverseerDecision(
        decision_id="decision-sized-us30",
        intent_id=intent.intent_id,
        agent_id=intent.agent_id,
        decision="APPROVE_ROUTE_INTENT",
        approved=True,
        reasons=["test"],
        command_ready=True,
        timestamp=utc_now().isoformat(),
    )

    resized, decisions, report = review_and_size_route_intents_with_operator(
        [intent],
        [decision],
        config=SimpleNamespace(live_mode=False),
        bridge=bridge,
        provider=_Provider(),
        enabled=True,
        decision_context={
            "status": "REALIZED_OUTCOMES_AVAILABLE",
            "recent_outcomes": [],
            "group_stats": [
                {
                    "symbol": intent.symbol,
                    "timeframe": intent.timeframe,
                    "direction": intent.direction,
                    "profile": intent.strategy_setting,
                    "trades": 5,
                    "wins": 4,
                    "losses": 1,
                    "sample_ready": True,
                    "net_pnl": 25.0,
                    "after_cost_expectancy": 5.0,
                    "after_cost_expectancy_r": 0.25,
                    "risk_normalized_trade_count": 5,
                    "risk_normalized_evidence_complete": True,
                    "after_cost_expectancy_per_1_lot_usd": 500.0,
                    "growth_robust_to_single_best_outcome": True,
                    "regime_breakdown": [
                        {
                            "market_regime": "DIRECTIONAL_PRESSURE",
                            "trades": 5,
                            "wins": 4,
                            "losses": 1,
                            "sample_ready": True,
                            "net_pnl": 25.0,
                            "after_cost_expectancy": 5.0,
                            "after_cost_expectancy_r": 0.25,
                            "risk_normalized_trade_count": 5,
                            "risk_normalized_evidence_complete": True,
                            "after_cost_expectancy_per_1_lot_usd": 500.0,
                            "growth_robust_to_single_best_outcome": True,
                        }
                    ],
                }
            ],
        },
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert decisions[0].approved is True
    assert resized[0].lot_size == 0.02
    assert resized[0].order_request["volume"] == 0.02
    assert report["decisions"][0]["selected_lots"] == 0.02
    assert report["decisions"][0]["selected_sizing_label"] == "MAX_WITHIN_ENVELOPE"
    assert report["decisions"][0]["growth_evidence_state"] == (
        "EXACT_GROUP_POSITIVE_SAMPLE_READY"
    )
    selection = resized[0]._runtime_context["operator_sizing_selection"]
    assert selection["operator_event_hash"] == report["event_hash"]
    assert selection["operator_prompt_version"] == "ai_operator_trade_edge.v11"
    assert selection["operator_decision_prompt_hash"] == report["model_prompt_hash"]
    assert selection["operator_system_prompt_hash"] == report["system_prompt_hash"]
    assert selection["operator_provider"] == "claude"
    assert selection["operator_provider_label"] == "Claude test"
    assert selection["operator_model_ref"] == "claude-sonnet-5"
    assert selection["operator_candidate_hash"] == report["decisions"][0]["candidate_hash"]
    assert selection["operator_decision_context_hash"] == report["decision_context_hash"]
    assert selection["operator_decision"] == "APPROVE"
    assert selection["operator_conviction"] == "HIGH"
    assert selection["sizing_option_count"] == len(plan["options"])
    assert selection["max_executable_lots"] == plan["max_executable_lots"]
    assert selection["sizing_limiting_source"] == plan["limiting_source"]
    assert selection["sizing_options_offered"][0]["sizing_ref"] == plan["options"][0][
        "sizing_ref"
    ]


def test_live_approval_without_explicit_sizing_ref_stands_down(monkeypatch, tmp_path):
    from cas_forex import execution_guard

    monkeypatch.setattr(execution_guard, "caps_from_config", lambda config=None: _caps())
    bridge = _SizingBridge()
    plan = build_operator_sizing_plan(
        symbol="US30",
        direction="SHORT",
        entry_price=52_597.82,
        stop_loss=52_617.82,
        take_profit=52_374.18,
        seed_lots=0.01,
        bridge=bridge,
        config=SimpleNamespace(),
    )
    intent = _intent(plan)
    decision = OverseerDecision(
        decision_id="decision-missing-size",
        intent_id=intent.intent_id,
        agent_id=intent.agent_id,
        decision="APPROVE_ROUTE_INTENT",
        approved=True,
        reasons=["test"],
        command_ready=True,
        timestamp=utc_now().isoformat(),
    )

    resized, decisions, report = review_and_size_route_intents_with_operator(
        [intent],
        [decision],
        config=SimpleNamespace(live_mode=True),
        bridge=bridge,
        provider=_MissingSizingProvider(),
        enabled=True,
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert decisions[0].approved is False
    assert resized[0].lot_size == 0.01
    assert report["status"] == "MODEL_RESPONSE_REJECTED_LIVE_STAND_DOWN"
    assert "must explicitly name one supplied sizing_ref" in report["model_error"]
