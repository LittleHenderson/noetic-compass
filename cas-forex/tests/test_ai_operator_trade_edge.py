from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

from cas_forex.ai_operator_trade_edge import (
    _dedupe_outcome_rows,
    _trade_decision_context,
    latest_operator_trade_edge_decision,
    review_route_intents_with_operator,
)
from cas_forex.agent_dispatch import run_agent_dispatch_cycle
from cas_forex.agent_state import OverseerDecision, RouteIntent
from cas_forex.broker.mt5_bridge import SimulatedBrokerBridge
from cas_forex.order_attempt_audit import OrderAttemptAuditStore
from cas_forex.order_dispatch import STATUS_DUPLICATE_SUPPRESSED, STATUS_OVERSEER_REJECTED
from cas_forex.time_utils import utc_now


class _Provider:
    def __init__(
        self,
        text: str,
        *,
        ok: bool = True,
        error: str | None = None,
        auto_select_exact_size: bool = False,
    ):
        self.text = text
        self.ok = ok
        self.error = error
        self.auto_select_exact_size = auto_select_exact_size
        self.calls: list[tuple[str, str, dict]] = []

    def generate(self, prompt, system=None, **kwargs):
        self.calls.append((prompt, system or "", dict(kwargs)))
        text = self.text
        if self.auto_select_exact_size and self.ok:
            payload = json.loads(prompt)
            reply = json.loads(text)
            candidates = {
                row["intent_id"]: row for row in payload.get("candidates") or []
            }
            for decision in reply.get("candidate_decisions") or []:
                candidate = candidates.get(decision.get("intent_id")) or {}
                options = list(candidate.get("sizing_options") or [])
                if decision.get("decision") == "APPROVE" and options:
                    decision["sizing_ref"] = options[-1]["sizing_ref"]
            text = json.dumps(reply)
        return {
            "ok": self.ok,
            "text": text,
            "provider": "claude",
            "provider_label": "Claude (stub)",
            "paid": True,
            "failover": False,
            "error": self.error,
        }


class _Bridge:
    def __init__(self, *, real: bool = False):
        self.real = real
        self.position_reads = 0
        self.account_reads = 0
        self.broker_calls = 0

    def will_execute_real_order(self):
        return self.real

    def get_open_positions(self):
        self.position_reads += 1
        return [
            {
                "broker_ticket": 7001,
                "symbol": "US30",
                "direction": "SHORT",
                "volume": 0.01,
                "fill_price": 52_582.49,
                "current_price": 52_560.0,
                "stop_loss": 52_674.47,
                "take_profit": 52_491.39,
                "floating_pnl": 0.22,
                "swap": -0.02,
                "commission": -0.01,
            }
        ]

    def get_account_info(self):
        self.account_reads += 1
        return {
            "balance": 5000.0,
            "equity": 5000.19,
            "margin": 8.21,
            "margin_free": 4991.98,
            "leverage": 500,
        }

    def place_order(self, _order):
        self.broker_calls += 1
        raise AssertionError("Operator decision review must never call the broker")


def _config(*, live: bool = False):
    return SimpleNamespace(
        live_mode=live,
        ai_operator_trade_edge_enabled=True,
        ai_operator_trade_edge_timeout_seconds=12,
    )


def _intent(intent_id: str, symbol: str, direction: str = "LONG") -> RouteIntent:
    entry = 29_500.0 if symbol == "NAS100" else 1.1000
    stop = entry - 100.0 if symbol == "NAS100" else entry - 0.0010
    target = entry + 180.0 if symbol == "NAS100" else entry + 0.0020
    return RouteIntent(
        intent_id=intent_id,
        agent_id="live_candle_agent",
        action="OPEN_LIVE_CANDLE_LEARNING",
        symbol=symbol,
        timeframe="H1",
        strategy_setting="live_candle_test_h1",
        direction=direction,
        confidence=0.67,
        evidence_score=1.0,
        lot_size=0.01,
        entry_price=entry,
        stop_loss=stop,
        take_profit=target,
        reason="completed H1 candidate",
        evidence_refs=["completed-candle:H1", "edge:NO_TRADE_NULL_FAILED"],
        order_request={
            "order_id": f"order-{intent_id}",
            "decision_ref": f"decision-{intent_id}",
            "symbol": symbol,
            "direction": direction,
            "order_type": "MARKET",
            "volume": 0.01,
            "price": 0.0,
            "stop_loss": stop,
            "take_profit": target,
            "magic_number": 20260710,
            "comment": "CAS_OPERATOR_EDGE_TEST",
        },
        learning_trade=True,
        edge_label={
            "status": "NO_TRADE_NULL_FAILED",
            "reason": "measured result did not beat the null",
            "measured_win_prob": 0.52,
            "threshold": 0.60,
        },
        market_quote_context={
            "quote_source": "mt5",
            "market_snapshot": {
                "symbol": symbol,
                "bid": entry - 1.0,
                "ask": entry,
                "spread": 1.0,
                "timestamp": utc_now().isoformat(),
            },
        },
    )


def _decision(intent: RouteIntent, *, approved: bool = True) -> OverseerDecision:
    return OverseerDecision(
        decision_id=f"overseer-{intent.intent_id}",
        intent_id=intent.intent_id,
        agent_id=intent.agent_id,
        decision="APPROVE_ROUTE_INTENT" if approved else "REJECT_ROUTE_INTENT",
        approved=approved,
        reasons=["deterministic overseer approved" if approved else "deterministic rejection"],
        command_ready=approved,
        timestamp="2026-07-10T12:00:01+00:00",
    )


def test_operator_approves_exact_candidate_and_stands_down_other(tmp_path):
    first = _intent("intent-a", "NAS100")
    second = _intent("intent-b", "EUR/USD")
    provider = _Provider(
        json.dumps(
            {
                "candidate_decisions": [
                    {
                        "intent_id": "intent-a",
                        "decision": "APPROVE",
                        "conviction": "HIGH",
                        "reason": "Independent H1 setup is suitable for paper evidence collection.",
                        "symbol": "XAU/USD",
                        "lots": 5.0,
                    },
                    {
                        "intent_id": "intent-b",
                        "decision": "STAND_DOWN",
                        "conviction": "LOW",
                        "reason": "Current exposure and weak differentiation do not justify another position.",
                    },
                ],
                "summary": "Approve NAS100 and stand down EUR/USD.",
            }
        )
    )
    bridge = _Bridge()
    latest = tmp_path / "latest.json"
    updated, report = review_route_intents_with_operator(
        [first, second],
        [_decision(first), _decision(second)],
        config=_config(),
        bridge=bridge,
        provider=provider,
        enabled=True,
        owner_guidance=["Scout broadly, but do not stack weak copies."],
        control_values={"max_positions_per_symbol": 1},
        decision_context={
            "status": "REALIZED_OUTCOMES_AVAILABLE",
            "recent_outcomes": [
                {
                    "binding_id": "bound-nas-loss",
                    "broker_ticket": "7000",
                    "decision_ref": "previous-nas-direction",
                    "symbol": "NAS100",
                    "timeframe": first.timeframe,
                    "direction": first.direction,
                    "strategy_id": first.strategy_setting,
                    "lot_size": 0.01,
                    "net_pnl": -6.73,
                    "admission_stop_risk_usd": 6.7,
                    "realized_after_cost_r_multiple": -1.004478,
                    "commission": -0.05,
                    "origin_source": "ORDER_ATTEMPT_LEDGER",
                },
                {
                    "binding_id": "bound-nas-loss-legacy-view",
                    "broker_ticket": "7000",
                    "decision_ref": "previous-nas-direction",
                    "symbol": "NAS100",
                    "timeframe": first.timeframe,
                    "direction": first.direction,
                    "profile": "range_fade",
                    "net_pnl": -6.73,
                    "commission": -0.05,
                    "origin_source": "WASTE_CYCLE_AUDIT",
                }
            ],
        },
        audit_path=tmp_path / "audit.jsonl",
        latest_path=latest,
    )

    assert report["status"] == "AI_OPERATOR_DECIDED"
    assert report["operator_approved_count"] == 1
    assert report["operator_stand_down_count"] == 1
    assert updated[0].approved is True
    assert updated[0].decision == "AI_OPERATOR_APPROVE_ROUTE_INTENT"
    assert updated[1].approved is False
    assert updated[1].decision == "AI_OPERATOR_STAND_DOWN"
    assert updated[1].command_ready is False
    assert first.symbol == "NAS100"
    assert first.lot_size == 0.01
    assert bridge.position_reads == 1
    assert bridge.account_reads == 1
    assert bridge.broker_calls == 0
    assert len(provider.calls) == 1
    schema = provider.calls[0][2]["response_format"]
    assert schema["type"] == "object"
    assert schema["required"] == ["candidate_decisions", "summary"]
    decision_schema = schema["properties"]["candidate_decisions"]["items"]
    assert decision_schema["properties"]["decision"]["enum"] == [
        "APPROVE",
        "STAND_DOWN",
    ]

    prompt = json.loads(provider.calls[0][0])
    assert prompt["candidates"][0]["symbol"] == "NAS100"
    assert prompt["candidates"][0]["lots"] == 0.01
    assert prompt["candidates"][0]["stop_loss"] == first.stop_loss
    assert prompt["decision_contract"]["geometry_is_immutable"] is True
    assert prompt["current_positions"][0]["ticket"] == 7001
    assert prompt["current_account"]["balance"] == 5000.0
    assert prompt["current_account"]["equity"] == 5000.19
    assert prompt["current_account"]["north_star"] == "MAXIMIZE_SUSTAINABLE_REALIZED_NET_ACCOUNT_GROWTH"
    assert prompt["current_account"]["position_price_pnl_usd"] == 0.22
    assert prompt["current_account"]["open_swap_usd"] == -0.02
    assert prompt["current_account"]["open_commission_usd"] == -0.01
    assert prompt["current_account"]["account_net_open_pnl_usd"] == 0.19
    assert prompt["current_positions"][0]["net_open_pnl_after_reported_costs_usd"] == 0.19
    assert prompt["decision_contract"]["active_account_after_cost_truth_is_authoritative"] is True
    assert prompt["owner_guidance"] == ["Scout broadly, but do not stack weak copies."]
    outcome_context = prompt["realized_outcome_context"]
    assert outcome_context["status"] == "REALIZED_OUTCOMES_AVAILABLE"
    nas_group = outcome_context["candidate_groups"]["intent-a"]
    assert nas_group["same_symbol_direction"]["losses"] == 1
    assert nas_group["same_symbol_direction"]["net_pnl"] == -6.73
    assert nas_group["growth_evidence_state"] == "EXACT_GROUP_NON_POSITIVE_AND_SPARSE"
    assert prompt["candidates"][0]["growth_evidence"]["state"] == (
        "EXACT_GROUP_NON_POSITIVE_AND_SPARSE"
    )
    assert nas_group["requires_differentiation_after_loss"] is True
    assert report["decision_context_hash"]
    assert report["model_context_projection"]["full_context_retained_in_audit"] is True
    assert report["model_context_projection"]["projected_context_chars"] <= report[
        "model_context_projection"
    ]["full_context_chars"]
    assert report["account_context"]["margin_free"] == 4991.98
    assert report["current_position_count"] == 1
    assert len(report["decision_context"]["recent_outcomes"]) == 1
    assert report["decision_context"]["recent_outcomes"][0]["broker_ticket"] == "7000"
    assert report["decision_context"]["recent_outcomes"][0]["origin_sources"] == [
        "ORDER_ATTEMPT_LEDGER",
        "WASTE_CYCLE_AUDIT",
    ]
    assert "cannot change symbol" in provider.calls[0][1].lower()
    assert "realized outcome history" in provider.calls[0][1].lower()
    assert "after spread, commission, swap, slippage, and losses" in provider.calls[0][1].lower()
    assert "win rate is supporting evidence only" in provider.calls[0][1].lower()
    assert "profit pooled from another group cannot justify this one" in provider.calls[0][1].lower()
    assert "conviction is commentary" in provider.calls[0][1].lower()
    assert "after-cost r expectancy" in provider.calls[0][1].lower()
    assert "per-lot dollars are not comparable edge across instruments" in provider.calls[0][1].lower()

    stored = latest_operator_trade_edge_decision(latest)
    assert stored["event_hash"] == report["event_hash"]
    assert len(stored["event_hash"]) == 64
    assert stored["broker_touched"] is False
    assert stored["orders_placed"] is False


def test_outcome_rows_are_chronological_before_recent_loss_logic():
    rows = _dedupe_outcome_rows(
        [
            {
                "broker_ticket": "later",
                "decision_ref": "later-decision",
                "symbol": "NAS100",
                "timeframe": "H1",
                "direction": "SHORT",
                "strategy_id": "trend_h1",
                "net_pnl": -3.0,
                "close_time": "2026-07-10T22:00:00+00:00",
            },
            {
                "broker_ticket": "earlier",
                "decision_ref": "earlier-decision",
                "symbol": "NAS100",
                "timeframe": "H1",
                "direction": "SHORT",
                "strategy_id": "trend_h1",
                "net_pnl": 2.0,
                "close_time": "2026-07-10T16:00:00+00:00",
            },
        ]
    )

    assert [row["broker_ticket"] for row in rows] == ["earlier", "later"]


def test_natural_context_merges_broker_group_stats_when_combined_profile_differs(monkeypatch):
    import cas_forex.mt5_demo_learning_sync as broker_learning
    import cas_forex.waste_direction_outcome_binding as combined_learning

    strategy = "live_candle_broker-candle_h1"
    recent_losses = [
        {
            "binding_id": f"loss-{index}",
            "broker_ticket": f"ticket-{index}",
            "symbol": "SPX500",
            "timeframe": "H1",
            "direction": "LONG",
            "strategy_id": strategy,
            "profile": strategy,
            "net_pnl": value,
            "net_pnl_per_1_lot_usd": value * 100.0,
            "admission_stop_risk_usd": 20.0,
            "realized_after_cost_r_multiple": value / 20.0,
            "close_time": f"2026-07-13T2{index}:00:00+00:00",
        }
        for index, value in enumerate((-0.06, -0.48, -0.83))
    ]
    broker_exact_group = {
        "symbol": "SPX500",
        "timeframe": "H1",
        "direction": "LONG",
        "profile": strategy,
        "trades": 4,
        "wins": 1,
        "losses": 3,
        "sample_ready": True,
        "net_pnl": 1.47,
        "after_cost_expectancy": 0.3675,
        "after_cost_expectancy_r": 0.0132,
        "risk_normalized_trade_count": 4,
        "risk_normalized_evidence_complete": True,
        "after_cost_expectancy_per_1_lot_usd": 36.75,
    }
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(
        combined_learning,
        "build_waste_learning_outcomes",
        lambda: {
            "bound_trade_count": 4,
            "sample_bound_rows": recent_losses,
            "group_stats": [
                {
                    **broker_exact_group,
                    "profile": "range_fade",
                }
            ],
        },
    )
    monkeypatch.setattr(
        broker_learning,
        "load_mt5_demo_learning_sync",
        lambda: {
            "bound_trade_count": 4,
            "bound_outcomes": recent_losses,
            "learning_group_stats": [broker_exact_group],
        },
    )

    context = _trade_decision_context(
        [
            {
                "intent_id": "intent-spx-h1",
                "symbol": "SPX500",
                "timeframe": "H1",
                "direction": "LONG",
                "strategy": strategy,
            }
        ]
    )

    group = context["candidate_groups"]["intent-spx-h1"]
    assert group["exact_group_source"] == "FULL_GROUP_STATS"
    assert group["exact_group"]["trades"] == 4
    assert group["exact_group"]["net_pnl"] == 1.47
    assert group["growth_evidence_state"] == "EXACT_GROUP_POSITIVE_SAMPLE_READY"
    assert context["evidence_quality"]["candidate_group_stats_sources_merged"] is True
    assert context["evidence_quality"]["candidate_group_stats_merged_count"] == 2


def test_exact_group_r_growth_evidence_reaches_each_size_option(tmp_path):
    base_intent = _intent("intent-growth-size", "NAS100")
    sizing_plan = {
        "status": "OPTIONS_READY",
        "plan_hash": "plan-growth-size",
        "max_executable_lots": 0.02,
        "limiting_source": "max_risk_per_trade_pct",
        "options": [
            {
                "sizing_ref": "size-probe",
                "label": "PROBE",
                "lots": 0.01,
                "risk_at_stop_usd": 5.0,
            },
            {
                "sizing_ref": "size-press",
                "label": "PRESS_EDGE",
                "lots": 0.02,
                "risk_at_stop_usd": 10.0,
            },
        ],
    }
    intent = replace(
        base_intent,
        _runtime_context={
            "operator_sizing_plan": sizing_plan,
            "setup": SimpleNamespace(regime="trend", signal_strength=0.8),
        },
    )
    provider = _Provider(
        json.dumps(
            {
                "candidate_decisions": [
                    {
                        "intent_id": intent.intent_id,
                        "decision": "APPROVE",
                        "sizing_ref": "size-press",
                        "conviction": "HIGH",
                        "reason": "The exact group is sample-ready and profitable after costs per planned risk dollar.",
                    }
                ],
                "summary": "Press the exact profitable group inside the envelope.",
            }
        )
    )

    _updated, report = review_route_intents_with_operator(
        [intent],
        [_decision(intent)],
        config=_config(),
        bridge=_Bridge(),
        provider=provider,
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
                    "sample_ready": True,
                    "net_pnl": 10.0,
                    "after_cost_expectancy": 2.0,
                    "after_cost_expectancy_r": 0.2,
                    "risk_normalized_trade_count": 5,
                    "risk_normalized_evidence_complete": True,
                    "total_admission_stop_risk_usd": 50.0,
                    "after_cost_expectancy_per_1_lot_usd": 200.0,
                    "profit_factor": 1.8,
                    "win_rate": 0.6,
                    "regime_breakdown": [
                        {
                            "market_regime": "TREND",
                            "trades": 5,
                            "wins": 3,
                            "losses": 2,
                            "sample_ready": True,
                            "net_pnl": 10.0,
                            "after_cost_expectancy": 2.0,
                            "after_cost_expectancy_r": 0.2,
                            "risk_normalized_trade_count": 5,
                            "risk_normalized_evidence_complete": True,
                            "total_admission_stop_risk_usd": 50.0,
                            "after_cost_expectancy_per_1_lot_usd": 200.0,
                            "profit_factor": 1.8,
                            "win_rate": 0.6,
                            "growth_robust_to_single_best_outcome": True,
                        }
                    ],
                }
            ],
        },
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    prompt = json.loads(provider.calls[0][0])
    candidate = prompt["candidates"][0]
    assert candidate["growth_evidence"]["state"] == "EXACT_GROUP_POSITIVE_SAMPLE_READY"
    assert candidate["growth_evidence"]["press_size_supported_by_exact_group_outcomes"] is True
    assert candidate["sizing_options"][1]["historical_after_cost_projection_usd"] == 2.0
    assert candidate["sizing_options"][1]["historical_projection_basis"] == (
        "AFTER_COST_R_EXPECTANCY_X_CURRENT_STOP_RISK"
    )
    assert candidate["sizing_options"][1][
        "historical_projection_comparable_across_instruments"
    ] is True
    assert candidate["sizing_options"][1]["historical_projection_is_not_a_forecast"] is True
    assert report["decisions"][0]["exact_group_after_cost_expectancy_r"] == 0.2
    assert report["decisions"][0]["selected_historical_after_cost_projection_usd"] == 2.0
    assert report["decisions"][0]["selected_historical_projection_basis"] == (
        "AFTER_COST_R_EXPECTANCY_X_CURRENT_STOP_RISK"
    )
    assert report["decisions"][0]["sizing_option_count"] == 2
    assert report["decisions"][0]["max_executable_lots"] == 0.02
    assert report["decisions"][0]["sizing_limiting_source"] == (
        "max_risk_per_trade_pct"
    )
    offered = report["decisions"][0]["sizing_options_offered"]
    assert [row["sizing_ref"] for row in offered] == ["size-probe", "size-press"]
    assert offered[1]["historical_after_cost_projection_usd"] == 2.0


def test_candidate_receives_exact_group_growth_evidence_from_supported_broker_alias(tmp_path):
    intent = _intent("intent-alias-growth", "NAS100")
    provider = _Provider(
        json.dumps(
            {
                "candidate_decisions": [
                    {
                        "intent_id": intent.intent_id,
                        "decision": "STAND_DOWN",
                        "sizing_ref": None,
                        "conviction": "LOW",
                        "reason": "Alias-normalized prior outcomes are part of this exact market history.",
                    }
                ],
                "summary": "Use the canonical market history.",
            }
        )
    )

    review_route_intents_with_operator(
        [intent],
        [_decision(intent)],
        config=_config(),
        bridge=_Bridge(),
        provider=provider,
        enabled=True,
        decision_context={
            "status": "REALIZED_OUTCOMES_AVAILABLE",
            "recent_outcomes": [],
            "group_stats": [
                {
                    "symbol": "USTEC.cash",
                    "timeframe": intent.timeframe,
                    "direction": intent.direction,
                    "profile": intent.strategy_setting,
                    "trades": 5,
                    "sample_ready": True,
                    "net_pnl": -10.0,
                    "after_cost_expectancy": -2.0,
                    "after_cost_expectancy_r": -0.2,
                    "risk_normalized_trade_count": 5,
                    "risk_normalized_evidence_complete": True,
                    "after_cost_expectancy_per_1_lot_usd": -200.0,
                }
            ],
        },
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    candidate = json.loads(provider.calls[0][0])["candidates"][0]
    assert candidate["growth_evidence"]["state"] == "EXACT_GROUP_NON_POSITIVE_SAMPLE_READY"
    assert candidate["growth_evidence"]["symbol"] == "NAS100"
    assert candidate["growth_evidence"]["after_cost_expectancy_r"] == -0.2


def test_positive_per_lot_group_without_admission_risk_cannot_support_press_size(tmp_path):
    base_intent = _intent("intent-incomplete-risk", "NAS100")
    sizing_plan = {
        "status": "OPTIONS_READY",
        "plan_hash": "plan-incomplete-risk",
        "options": [
            {"sizing_ref": "size-probe", "label": "PROBE", "lots": 0.01, "risk_at_stop_usd": 5.0},
            {"sizing_ref": "size-press", "label": "PRESS_EDGE", "lots": 0.02, "risk_at_stop_usd": 10.0},
        ],
    }
    intent = replace(base_intent, _runtime_context={"operator_sizing_plan": sizing_plan})
    provider = _Provider(
        json.dumps(
            {
                "candidate_decisions": [
                    {
                        "intent_id": intent.intent_id,
                        "decision": "STAND_DOWN",
                        "sizing_ref": None,
                        "conviction": "LOW",
                        "reason": "Per-lot dollars are positive, but comparable admission-risk evidence is incomplete.",
                    }
                ],
                "summary": "Do not press incomplete risk evidence.",
            }
        )
    )

    review_route_intents_with_operator(
        [intent],
        [_decision(intent)],
        config=_config(),
        bridge=_Bridge(),
        provider=provider,
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
                    "sample_ready": True,
                    "net_pnl": 10.0,
                    "after_cost_expectancy": 2.0,
                    "after_cost_expectancy_per_1_lot_usd": 200.0,
                    "risk_normalized_evidence_complete": False,
                }
            ],
        },
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    prompt = json.loads(provider.calls[0][0])
    candidate = prompt["candidates"][0]
    assert candidate["growth_evidence"]["state"] == (
        "EXACT_GROUP_SAMPLE_READY_RISK_EVIDENCE_INCOMPLETE"
    )
    assert candidate["growth_evidence"][
        "press_size_supported_by_exact_group_outcomes"
    ] is False
    assert candidate["sizing_options"][1]["historical_after_cost_projection_usd"] == 4.0
    assert candidate["sizing_options"][1]["historical_projection_basis"] == (
        "PER_1_LOT_EXPECTANCY_X_LOTS_INCOMPLETE_RISK_FALLBACK"
    )
    assert candidate["sizing_options"][1][
        "historical_projection_comparable_across_instruments"
    ] is False


def test_malformed_operator_output_uses_guarded_paper_fallback(tmp_path):
    intent = _intent("intent-paper", "NAS100")
    original = _decision(intent)
    updated, report = review_route_intents_with_operator(
        [intent],
        [original],
        config=_config(live=False),
        bridge=_Bridge(real=False),
        provider=_Provider("not json"),
        enabled=True,
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert report["status"] == "DEGRADED_PAPER_GROWTH_GATED_FALLBACK"
    assert updated[0].approved is True
    assert updated[0].decision == original.decision
    assert "growth-gated PAPER fallback" in updated[0].reasons[-1]
    assert report["decisions"][0]["decision"] == "PAPER_BOUNDED_EXPLORATION_FALLBACK"
    assert report["decisions"][0]["fallback_selection_policy"] == (
        "NO_HISTORY_BOUNDED_EXPLORATION"
    )


def test_model_failure_stands_down_sample_ready_losing_paper_group(tmp_path):
    intent = _intent("intent-known-loser", "NAS100")
    updated, report = review_route_intents_with_operator(
        [intent],
        [_decision(intent)],
        config=_config(live=False),
        bridge=_Bridge(real=False),
        provider=_Provider("not json"),
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
                    "wins": 0,
                    "losses": 5,
                    "sample_ready": True,
                    "net_pnl": -42.36,
                    "after_cost_expectancy": -8.472,
                    "after_cost_expectancy_r": -0.40839,
                    "risk_normalized_trade_count": 5,
                    "risk_normalized_evidence_complete": True,
                    "after_cost_expectancy_per_1_lot_usd": -847.2,
                }
            ],
        },
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert report["status"] == "MODEL_RESPONSE_REJECTED_PAPER_GROWTH_STAND_DOWN"
    assert report["model_transport_ok"] is True
    assert report["model_response_rejected"] is True
    assert report["model_failure_stage"] == "MODEL_RESPONSE_CONTRACT"
    assert report["operator_approved_count"] == 0
    assert report["operator_stand_down_count"] == 1
    assert updated[0].approved is False
    assert updated[0].command_ready is False
    assert updated[0].decision == "AI_OPERATOR_MODEL_RESPONSE_REJECTED_PAPER_GROWTH_STAND_DOWN"
    row = report["decisions"][0]
    assert row["decision"] == "PAPER_GROWTH_EVIDENCE_STAND_DOWN"
    assert row["fallback_selection_policy"] == "SAMPLE_READY_NON_POSITIVE_STAND_DOWN"
    assert row["selected_lots"] is None
    assert row["exact_group_after_cost_expectancy"] == -8.472


def test_model_failure_allows_one_loss_only_as_bounded_probe(tmp_path):
    base = _intent("intent-one-loss", "NAS100")
    plan = {
        "status": "OPTIONS_READY",
        "plan_hash": "plan-one-loss",
        "max_executable_lots": 0.04,
        "limiting_source": "max_risk_per_trade_pct",
        "options": [
            {"sizing_ref": "size-min", "label": "BROKER_MINIMUM", "lots": 0.01},
            {"sizing_ref": "size-probe", "label": "PROBE", "lots": 0.02},
            {"sizing_ref": "size-standard", "label": "STANDARD", "lots": 0.03},
            {"sizing_ref": "size-max", "label": "MAX_WITHIN_ENVELOPE", "lots": 0.04},
        ],
    }
    intent = replace(base, _runtime_context={"operator_sizing_plan": plan})
    updated, report = review_route_intents_with_operator(
        [intent],
        [_decision(intent)],
        config=_config(live=False),
        bridge=_Bridge(real=False),
        provider=_Provider("not json"),
        enabled=True,
        decision_context={
            "status": "REALIZED_OUTCOMES_AVAILABLE",
            "recent_outcomes": [
                {
                    "broker_ticket": "one-loss",
                    "decision_ref": "one-loss-ref",
                    "symbol": intent.symbol,
                    "timeframe": intent.timeframe,
                    "direction": intent.direction,
                    "strategy_id": intent.strategy_setting,
                    "lot_size": 0.01,
                    "net_pnl": -6.0,
                    "admission_stop_risk_usd": 6.0,
                    "realized_after_cost_r_multiple": -1.0,
                }
            ],
        },
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert updated[0].approved is True
    row = report["decisions"][0]
    assert row["fallback_selection_policy"] == "ONE_LOSS_BOUNDED_RETEST"
    assert row["sizing_ref"] == "size-probe"
    assert row["selected_lots"] == 0.02
    assert row["sizing_option_count"] == 4
    assert row["max_executable_lots"] == 0.04
    assert row["sizing_limiting_source"] == "max_risk_per_trade_pct"


def test_model_failure_uses_standard_only_for_positive_sample_ready_group(tmp_path):
    base = _intent("intent-positive-fallback", "NAS100")
    plan = {
        "status": "OPTIONS_READY",
        "plan_hash": "plan-positive-fallback",
        "max_executable_lots": 0.04,
        "limiting_source": "max_risk_per_trade_pct",
        "options": [
            {"sizing_ref": "size-min", "label": "BROKER_MINIMUM", "lots": 0.01},
            {"sizing_ref": "size-probe", "label": "PROBE", "lots": 0.02},
            {"sizing_ref": "size-standard", "label": "STANDARD", "lots": 0.03},
            {"sizing_ref": "size-max", "label": "MAX_WITHIN_ENVELOPE", "lots": 0.04},
        ],
    }
    intent = replace(base, _runtime_context={"operator_sizing_plan": plan})
    updated, report = review_route_intents_with_operator(
        [intent],
        [_decision(intent)],
        config=_config(live=False),
        bridge=_Bridge(real=False),
        provider=_Provider("not json"),
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
                    "wins": 3,
                    "losses": 2,
                    "sample_ready": True,
                    "net_pnl": 25.0,
                    "after_cost_expectancy": 5.0,
                    "after_cost_expectancy_r": 0.25,
                    "risk_normalized_trade_count": 5,
                    "risk_normalized_evidence_complete": True,
                    "after_cost_expectancy_per_1_lot_usd": 500.0,
                }
            ],
        },
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert updated[0].approved is True
    row = report["decisions"][0]
    assert row["decision"] == "PAPER_POSITIVE_EVIDENCE_FALLBACK"
    assert row["fallback_selection_policy"] == "POSITIVE_SAMPLE_READY_STANDARD"
    assert row["sizing_ref"] == "size-standard"
    assert row["selected_lots"] == 0.03


def test_operator_cannot_press_from_profitable_pooled_but_sparse_regime_evidence(
    tmp_path,
):
    base = _intent("intent-regime-sparse", "NAS100")
    plan = {
        "status": "OPTIONS_READY",
        "plan_hash": "plan-regime-sparse",
        "max_executable_lots": 0.04,
        "limiting_source": "max_risk_per_trade_pct",
        "options": [
            {"sizing_ref": "size-min", "label": "BROKER_MINIMUM", "lots": 0.01},
            {"sizing_ref": "size-probe", "label": "PROBE", "lots": 0.02},
            {"sizing_ref": "size-standard", "label": "STANDARD", "lots": 0.03},
            {
                "sizing_ref": "size-max",
                "label": "MAX_WITHIN_ENVELOPE",
                "lots": 0.04,
            },
        ],
    }
    intent = replace(
        base,
        _runtime_context={
            "operator_sizing_plan": plan,
            "setup": SimpleNamespace(regime="trend", signal_strength=0.8),
        },
    )
    provider = _Provider(
        json.dumps(
            {
                "candidate_decisions": [
                    {
                        "intent_id": intent.intent_id,
                        "decision": "APPROVE",
                        "sizing_ref": "size-max",
                        "conviction": "HIGH",
                        "reason": "The pooled group is profitable, so use maximum size.",
                    }
                ],
                "summary": "Press pooled profitability.",
            }
        )
    )
    pooled_group = {
        "symbol": intent.symbol,
        "timeframe": intent.timeframe,
        "direction": intent.direction,
        "profile": intent.strategy_setting,
        "trades": 6,
        "wins": 6,
        "losses": 0,
        "sample_ready": True,
        "net_pnl": 30.0,
        "after_cost_expectancy": 5.0,
        "after_cost_expectancy_r": 0.25,
        "risk_normalized_trade_count": 6,
        "risk_normalized_evidence_complete": True,
        "after_cost_expectancy_per_1_lot_usd": 500.0,
        "growth_robust_to_single_best_outcome": True,
        "regime_breakdown": [
            {
                "market_regime": "TREND",
                "trades": 3,
                "wins": 3,
                "losses": 0,
                "sample_ready": False,
                "net_pnl": 15.0,
                "after_cost_expectancy": 5.0,
                "after_cost_expectancy_r": 0.25,
                "risk_normalized_trade_count": 3,
                "risk_normalized_evidence_complete": True,
                "after_cost_expectancy_per_1_lot_usd": 500.0,
                "growth_robust_to_single_best_outcome": True,
            },
            {
                "market_regime": "RANGE",
                "trades": 3,
                "wins": 3,
                "losses": 0,
                "sample_ready": False,
                "net_pnl": 15.0,
                "after_cost_expectancy": 5.0,
                "after_cost_expectancy_r": 0.25,
                "risk_normalized_trade_count": 3,
                "risk_normalized_evidence_complete": True,
                "after_cost_expectancy_per_1_lot_usd": 500.0,
                "growth_robust_to_single_best_outcome": True,
            },
        ],
    }

    updated, report = review_route_intents_with_operator(
        [intent],
        [_decision(intent)],
        config=_config(live=False),
        bridge=_Bridge(real=False),
        provider=provider,
        enabled=True,
        decision_context={
            "status": "REALIZED_OUTCOMES_AVAILABLE",
            "recent_outcomes": [],
            "group_stats": [pooled_group],
        },
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    candidate = json.loads(provider.calls[0][0])["candidates"][0]
    growth = candidate["growth_evidence"]
    assert growth["market_regime_key"] == "TREND"
    assert growth["source"] == "FULL_REGIME_GROUP_STATS"
    assert growth["regime_comparable_outcome_count"] == 3
    assert growth["state"] == "EXACT_GROUP_POSITIVE_BUT_SPARSE"
    assert growth["all_regimes_group"]["trades"] == 6
    assert growth["all_regimes_growth_evidence_state"] == (
        "EXACT_GROUP_POSITIVE_SAMPLE_READY"
    )
    assert growth["press_size_supported_by_exact_group_outcomes"] is False
    assert report["model_response_rejected"] is True
    assert "regime-comparable" in report["model_error"]
    row = report["decisions"][0]
    assert row["decision"] == "PAPER_BOUNDED_EXPLORATION_FALLBACK"
    assert row["sizing_ref"] == "size-probe"
    assert updated[0].approved is True


def test_outlier_dependent_group_cannot_press_when_model_selects_max(tmp_path):
    base = _intent("intent-outlier-dependent", "NAS100")
    plan = {
        "status": "OPTIONS_READY",
        "plan_hash": "plan-outlier-dependent",
        "max_executable_lots": 0.04,
        "limiting_source": "max_risk_per_trade_pct",
        "options": [
            {"sizing_ref": "size-min", "label": "BROKER_MINIMUM", "lots": 0.01},
            {"sizing_ref": "size-probe", "label": "PROBE", "lots": 0.02},
            {"sizing_ref": "size-standard", "label": "STANDARD", "lots": 0.03},
            {
                "sizing_ref": "size-max",
                "label": "MAX_WITHIN_ENVELOPE",
                "lots": 0.04,
            },
        ],
    }
    intent = replace(base, _runtime_context={"operator_sizing_plan": plan})
    provider = _Provider(
        json.dumps(
            {
                "candidate_decisions": [
                    {
                        "intent_id": intent.intent_id,
                        "decision": "APPROVE",
                        "sizing_ref": "size-max",
                        "conviction": "HIGH",
                        "reason": "Press the historically positive group.",
                    }
                ],
                "summary": "Press the edge.",
            }
        )
    )

    updated, report = review_route_intents_with_operator(
        [intent],
        [_decision(intent)],
        config=_config(live=False),
        bridge=_Bridge(real=False),
        provider=provider,
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
                    "trades": 7,
                    "wins": 2,
                    "losses": 5,
                    "sample_ready": True,
                    "net_pnl": 75.54,
                    "after_cost_expectancy": 10.7914,
                    "after_cost_expectancy_r": 0.11093,
                    "risk_normalized_trade_count": 7,
                    "risk_normalized_evidence_complete": True,
                    "after_cost_expectancy_per_1_lot_usd": 1089.0,
                    "growth_robust_to_single_best_outcome": False,
                    "outlier_dependency_status": (
                        "POSITIVE_DEPENDS_ON_SINGLE_BEST_OUTCOME"
                    ),
                    "leave_one_best_out_net_pnl": -9.32,
                    "leave_one_best_out_after_cost_expectancy_r": -0.00306,
                    "recent_consecutive_losses": 3,
                }
            ],
        },
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    row = report["decisions"][0]
    assert report["model_response_rejected"] is True
    assert "robust regime-comparable exact-group press-size evidence" in report[
        "model_error"
    ]
    assert row["decision"] == "PAPER_BOUNDED_EXPLORATION_FALLBACK"
    assert row["sizing_ref"] == "size-probe"
    assert row["selected_lots"] == 0.02
    assert row["growth_evidence_state"] == (
        "EXACT_GROUP_POSITIVE_SAMPLE_READY_OUTLIER_DEPENDENT"
    )
    assert updated[0].approved is True


def test_daily_realized_loss_cap_stands_down_before_model_or_paper_fallback(
    tmp_path,
    monkeypatch,
):
    intent = _intent("intent-cap", "NAS100")
    provider = _Provider("not json")
    monkeypatch.setattr(
        "cas_forex.ai_operator_trade_edge._current_account",
        lambda *_args, **_kwargs: {
            "realized_today_usd": -50.13,
            "account_growth_reconciliation": {
                "reconciled": True,
                "event_hash": "growth-proof-1",
            },
        },
    )

    updated, report = review_route_intents_with_operator(
        [intent],
        [_decision(intent)],
        config=_config(live=False),
        bridge=_Bridge(real=False),
        provider=provider,
        enabled=True,
        control_values={"daily_loss_cap_usd": 50.0},
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert report["status"] == "DAILY_REALIZED_LOSS_CAP_REACHED"
    assert report["model_invoked"] is False
    assert report["operator_approved_count"] == 0
    assert report["operator_stand_down_count"] == 1
    assert report["daily_realized_loss_gate"]["block_new_exposure"] is True
    assert updated[0].decision == "AI_OPERATOR_DAILY_LOSS_CAP_STAND_DOWN"
    assert updated[0].approved is False
    assert updated[0].command_ready is False
    assert provider.calls == []


def test_model_failure_stands_down_live_candidate(tmp_path):
    intent = _intent("intent-live", "NAS100")
    updated, report = review_route_intents_with_operator(
        [intent],
        [_decision(intent)],
        config=_config(live=True),
        bridge=_Bridge(real=True),
        provider=_Provider("", ok=False, error="provider timeout"),
        enabled=True,
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert report["status"] == "MODEL_UNAVAILABLE_LIVE_STAND_DOWN"
    assert report["model_transport_ok"] is False
    assert report["model_response_rejected"] is False
    assert report["operator_approved_count"] == 0
    assert report["operator_stand_down_count"] == 1
    assert updated[0].approved is False
    assert updated[0].command_ready is False
    assert updated[0].decision == "AI_OPERATOR_UNAVAILABLE_LIVE_STAND_DOWN"


def test_missing_candidate_decision_is_contract_failure_in_live_mode(tmp_path):
    first = _intent("intent-a", "NAS100")
    second = _intent("intent-b", "EUR/USD")
    provider = _Provider(
        json.dumps(
            {
                "candidate_decisions": [
                    {
                        "intent_id": "intent-a",
                        "decision": "APPROVE",
                        "conviction": "HIGH",
                        "reason": "approve one",
                    }
                ],
                "summary": "incomplete",
            }
        )
    )
    updated, report = review_route_intents_with_operator(
        [first, second],
        [_decision(first), _decision(second)],
        config=_config(live=True),
        bridge=_Bridge(real=True),
        provider=provider,
        enabled=True,
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert report["status"] == "MODEL_RESPONSE_REJECTED_LIVE_STAND_DOWN"
    assert report["model_transport_ok"] is True
    assert report["model_response_rejected"] is True
    assert "missing candidate decisions" in report["model_error"]
    assert all(not row.approved for row in updated)


def test_operator_never_resurrects_overseer_rejected_candidate(tmp_path):
    first = _intent("intent-approved", "NAS100")
    rejected = _intent("intent-rejected", "EUR/USD")
    provider = _Provider(
        json.dumps(
            {
                "candidate_decisions": [
                    {
                        "intent_id": "intent-approved",
                        "decision": "APPROVE",
                        "conviction": "MEDIUM",
                        "reason": "candidate remains inside the grounded contract",
                    }
                ],
                "summary": "Only the overseer-approved candidate was reviewed.",
            }
        )
    )
    updated, report = review_route_intents_with_operator(
        [first, rejected],
        [_decision(first), _decision(rejected, approved=False)],
        config=_config(),
        bridge=_Bridge(),
        provider=provider,
        enabled=True,
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    prompt = json.loads(provider.calls[0][0])
    assert [row["intent_id"] for row in prompt["candidates"]] == ["intent-approved"]
    assert updated[0].approved is True
    assert updated[1].approved is False
    assert updated[1].decision == "REJECT_ROUTE_INTENT"
    assert report["overseer_approved_candidate_count"] == 1


def test_disabled_operator_review_does_not_call_provider_or_change_decision(tmp_path):
    intent = _intent("intent-disabled", "NAS100")
    provider = _Provider("should not be read")
    original = _decision(intent)
    updated, report = review_route_intents_with_operator(
        [intent],
        [original],
        config=_config(),
        bridge=_Bridge(),
        provider=provider,
        enabled=False,
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert report["status"] == "NOT_ENABLED"
    assert updated == [original]
    assert provider.calls == []
    assert not (tmp_path / "latest.json").exists()


def test_agent_dispatch_executes_only_after_operator_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "cas_forex.ai_operator_trade_edge._control_values",
        lambda: {"daily_loss_cap_usd": 0.0},
    )
    intent = _intent("intent-dispatch-approved", "NAS100")
    provider = _Provider(
        json.dumps(
            {
                "candidate_decisions": [
                    {
                        "intent_id": intent.intent_id,
                        "decision": "APPROVE",
                        "conviction": "MEDIUM",
                        "reason": "Grounded paper candidate is suitable for independent outcome collection.",
                    }
                ],
                "summary": "Approve the exact paper candidate.",
            }
        ),
        auto_select_exact_size=True,
    )
    bridge = SimulatedBrokerBridge(state_path=tmp_path / "simulated-broker.json")
    audit_store = OrderAttemptAuditStore(
        tmp_path / "order-attempts.json",
        tmp_path / "order-attempts-audit.jsonl",
    )

    cycle = run_agent_dispatch_cycle(
        intents=[intent],
        bridge=bridge,
        config=_config(),
        enforce_receipt_gates=False,
        audit_store=audit_store,
        operator_trade_edge_enabled=True,
        operator_trade_edge_provider=provider,
        operator_trade_edge_audit_path=tmp_path / "operator-edge-audit.jsonl",
        operator_trade_edge_latest_path=tmp_path / "operator-edge-latest.json",
    )

    assert cycle.operator_trade_edge_report["status"] == "AI_OPERATOR_DECIDED"
    assert cycle.operator_trade_edge_report["operator_approved_count"] == 1
    assert cycle.overseer_decisions[0].decision == "AI_OPERATOR_APPROVE_ROUTE_INTENT"
    assert cycle.dispatch_report.executed_count == 1
    positions = bridge.get_open_positions()
    assert len(positions) == 1
    assert positions[0]["symbol"] == "NAS100"
    serialized = cycle.to_dict()
    assert serialized["operator_trade_edge"]["event_hash"]
    assert serialized["dispatch_report"]["executed_count"] == 1


def test_agent_dispatch_records_operator_stand_down_without_broker_touch(tmp_path):
    intent = _intent("intent-dispatch-stand-down", "NAS100")
    provider = _Provider(
        json.dumps(
            {
                "candidate_decisions": [
                    {
                        "intent_id": intent.intent_id,
                        "decision": "STAND_DOWN",
                        "conviction": "LOW",
                        "reason": "The setup does not justify adding exposure now.",
                    }
                ],
                "summary": "Stand down.",
            }
        )
    )
    bridge = SimulatedBrokerBridge(state_path=tmp_path / "simulated-broker.json")
    audit_store = OrderAttemptAuditStore(
        tmp_path / "order-attempts.json",
        tmp_path / "order-attempts-audit.jsonl",
    )

    cycle = run_agent_dispatch_cycle(
        intents=[intent],
        bridge=bridge,
        config=_config(),
        enforce_receipt_gates=False,
        audit_store=audit_store,
        operator_trade_edge_enabled=True,
        operator_trade_edge_provider=provider,
        operator_trade_edge_audit_path=tmp_path / "operator-edge-audit.jsonl",
        operator_trade_edge_latest_path=tmp_path / "operator-edge-latest.json",
    )

    assert cycle.overseer_decisions[0].approved is False
    assert cycle.overseer_decisions[0].decision == "AI_OPERATOR_STAND_DOWN"
    assert cycle.dispatch_report.executed_count == 0
    assert cycle.dispatch_report.results[0].status == STATUS_OVERSEER_REJECTED
    assert bridge.get_open_positions() == []


def test_agent_dispatch_model_failure_cannot_execute_sample_ready_loser(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        "cas_forex.ai_operator_trade_edge._control_values",
        lambda: {"daily_loss_cap_usd": 0.0},
    )
    intent = _intent("intent-dispatch-known-loser", "NAS100")
    bridge = SimulatedBrokerBridge(state_path=tmp_path / "simulated-broker.json")
    audit_store = OrderAttemptAuditStore(
        tmp_path / "order-attempts.json",
        tmp_path / "order-attempts-audit.jsonl",
    )

    cycle = run_agent_dispatch_cycle(
        intents=[intent],
        bridge=bridge,
        config=_config(),
        enforce_receipt_gates=False,
        audit_store=audit_store,
        operator_trade_edge_enabled=True,
        operator_trade_edge_provider=_Provider("not json"),
        operator_trade_edge_context={
            "status": "REALIZED_OUTCOMES_AVAILABLE",
            "recent_outcomes": [],
            "group_stats": [
                {
                    "symbol": intent.symbol,
                    "timeframe": intent.timeframe,
                    "direction": intent.direction,
                    "profile": intent.strategy_setting,
                    "trades": 5,
                    "wins": 0,
                    "losses": 5,
                    "sample_ready": True,
                    "net_pnl": -42.36,
                    "after_cost_expectancy": -8.472,
                    "after_cost_expectancy_r": -0.40839,
                    "risk_normalized_trade_count": 5,
                    "risk_normalized_evidence_complete": True,
                    "after_cost_expectancy_per_1_lot_usd": -847.2,
                }
            ],
        },
        operator_trade_edge_audit_path=tmp_path / "operator-edge-audit.jsonl",
        operator_trade_edge_latest_path=tmp_path / "operator-edge-latest.json",
    )

    assert cycle.operator_trade_edge_report["status"] == (
        "MODEL_RESPONSE_REJECTED_PAPER_GROWTH_STAND_DOWN"
    )
    assert cycle.overseer_decisions[0].approved is False
    assert cycle.dispatch_report.executed_count == 0
    assert cycle.dispatch_report.results[0].status == STATUS_OVERSEER_REJECTED
    assert bridge.get_open_positions() == []


def test_repeated_operator_approval_cannot_duplicate_same_order(tmp_path):
    intent = _intent("intent-repeat", "NAS100")
    provider = _Provider(
        json.dumps(
            {
                "candidate_decisions": [
                    {
                        "intent_id": intent.intent_id,
                        "decision": "APPROVE",
                        "conviction": "MEDIUM",
                        "reason": "Approve the exact grounded candidate.",
                    }
                ],
                "summary": "Approve.",
            }
        ),
        auto_select_exact_size=True,
    )
    bridge = SimulatedBrokerBridge(state_path=tmp_path / "simulated-broker.json")
    audit_store = OrderAttemptAuditStore(
        tmp_path / "order-attempts.json",
        tmp_path / "order-attempts-audit.jsonl",
    )
    kwargs = {
        "intents": [intent],
        "bridge": bridge,
        "config": _config(),
        "enforce_receipt_gates": False,
        "audit_store": audit_store,
        "operator_trade_edge_enabled": True,
        "operator_trade_edge_provider": provider,
        "operator_trade_edge_audit_path": tmp_path / "operator-edge-audit.jsonl",
        "operator_trade_edge_latest_path": tmp_path / "operator-edge-latest.json",
    }

    first = run_agent_dispatch_cycle(**kwargs)
    second = run_agent_dispatch_cycle(**kwargs)

    assert first.dispatch_report.executed_count == 1
    assert second.dispatch_report.executed_count == 0
    assert second.dispatch_report.results[0].status == STATUS_DUPLICATE_SUPPRESSED
    assert len(bridge.get_open_positions()) == 1
    assert len(provider.calls) == 2
