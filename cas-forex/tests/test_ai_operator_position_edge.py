from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from cas_forex.ai_hedge_management_cycle import run_ai_hedge_management_cycle
from cas_forex.ai_operator_position_edge import (
    _position_origin_by_ticket,
    _review_interval_seconds,
    review_management_actions_with_operator,
)
from cas_forex.schemas.order import OrderOutcome, OrderStatus
from cas_forex.time_utils import utc_now


class _SelectingProvider:
    def __init__(self, *, intent: str | None = None, stand_down: bool = False):
        self.intent = intent
        self.stand_down = stand_down
        self.calls: list[tuple[dict[str, Any], str, dict[str, Any]]] = []

    def generate(self, prompt, system=None, **kwargs):
        payload = json.loads(prompt)
        self.calls.append((payload, system or "", dict(kwargs)))
        decisions = []
        for group in payload["position_action_candidates"]:
            actions = list(group["actions"])
            selected = next(
                (row for row in actions if row.get("intent") == self.intent),
                actions[0],
            )
            decisions.append(
                {
                    "position_key": group["position_key"],
                    "decision": "STAND_DOWN" if self.stand_down else "SELECT",
                    "action_ref": None if self.stand_down else selected["action_ref"],
                    "conviction": "MEDIUM",
                    "reason": (
                        "Current position evidence does not justify changing the broker state."
                        if self.stand_down
                        else f"Select the exact {selected['intent']} draft for this position."
                    ),
                }
            )
        return {
            "ok": True,
            "text": json.dumps(
                {
                    "position_decisions": decisions,
                    "summary": "Grounded position-management decision.",
                }
            ),
            "provider": "claude",
            "provider_label": "Claude (stub)",
            "paid": True,
            "failover": False,
            "error": None,
        }


class _BareTicketSelectingProvider(_SelectingProvider):
    def generate(self, prompt, system=None, **kwargs):
        result = super().generate(prompt, system, **kwargs)
        payload = json.loads(result["text"])
        for row in payload["position_decisions"]:
            row["position_key"] = str(row["position_key"]).removeprefix("ticket:")
        result["text"] = json.dumps(payload)
        return result


class _BrokenProvider:
    def __init__(self):
        self.calls = 0

    def generate(self, *_args, **_kwargs):
        self.calls += 1
        return {
            "ok": False,
            "text": "",
            "provider": "claude",
            "provider_label": "Claude (stub)",
            "paid": True,
            "failover": False,
            "error": "provider timeout",
        }


class _RealizationCloseProvider:
    def __init__(
        self,
        *,
        growth_case: str | None,
        reason: str,
        summary: str,
    ):
        self.growth_case = growth_case
        self.reason = reason
        self.summary = summary

    def generate(self, prompt, system=None, **kwargs):
        payload = json.loads(prompt)
        group = payload["position_action_candidates"][0]
        selected = group["actions"][0]
        decision = {
            "position_key": group["position_key"],
            "decision": "SELECT",
            "action_ref": selected["action_ref"],
            "selected_intent": selected["intent"],
            "conviction": "HIGH",
            "reason": self.reason,
        }
        if self.growth_case is not None:
            decision["growth_case"] = self.growth_case
        return {
            "ok": True,
            "text": json.dumps(
                {"position_decisions": [decision], "summary": self.summary}
            ),
            "provider": "local-fallback",
            "provider_label": "Local model (contract stub)",
            "paid": False,
            "failover": False,
            "error": None,
        }


class _ActionlessSelectProvider:
    def __init__(self, *, reason: str, summary: str):
        self.reason = reason
        self.summary = summary

    def generate(self, prompt, system=None, **kwargs):
        payload = json.loads(prompt)
        decisions = [
            {
                "position_key": group["position_key"],
                "decision": "SELECT",
                "action_ref": None,
                "selected_intent": None,
                "growth_case": "NOT_APPLICABLE",
                "conviction": "HIGH",
                "reason": self.reason,
            }
            for group in payload["position_action_candidates"]
        ]
        return {
            "ok": True,
            "text": json.dumps(
                {"position_decisions": decisions, "summary": self.summary}
            ),
            "provider": "local-fallback",
            "provider_label": "Local model (contract stub)",
            "paid": False,
            "failover": False,
            "error": None,
        }


class _NoncanonicalPositionProvider:
    def __init__(
        self,
        *,
        position: str,
        action: str,
        reason: str,
        summary: str = "",
    ):
        self.position = position
        self.action = action
        self.reason = reason
        self.summary = summary

    def generate(self, prompt, system=None, **kwargs):
        json.loads(prompt)
        return {
            "ok": True,
            "text": json.dumps(
                {
                    "position": self.position,
                    "decision": "SELECT",
                    "action": self.action,
                    "conviction": "HIGH",
                    "reason": self.reason,
                    "summary": self.summary,
                }
            ),
            "provider": "local-fallback",
            "provider_label": "Local model (contract stub)",
            "paid": False,
            "failover": False,
            "error": None,
        }


class _ContextOveranswerProvider:
    """Returns one valid decision plus an irrelevant context-position row."""

    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    def generate(self, prompt, system=None, **kwargs):
        payload = json.loads(prompt)
        self.calls.append(payload)
        group = payload["position_action_candidates"][0]
        selected = group["actions"][0]
        context_only = next(
            row
            for row in payload["current_positions"]
            if f"ticket:{row['broker_ticket']}" not in payload["decision_position_keys"]
        )
        return {
            "ok": True,
            "text": json.dumps(
                {
                    "position_decisions": [
                        {
                            "position_key": group["position_key"],
                            "decision": "SELECT",
                            "action_ref": selected["action_ref"],
                            "conviction": "MEDIUM",
                            "reason": "Select the exact supplied management draft.",
                        },
                        {
                            "position_key": f"ticket:{context_only['broker_ticket']}",
                            "decision": "STAND_DOWN",
                            "action_ref": None,
                            "conviction": "LOW",
                            "reason": "This context-only position has no supplied action draft.",
                        },
                    ],
                    "summary": "Manage the actionable position and leave context unchanged.",
                }
            ),
            "provider": "claude",
            "provider_label": "Claude (overanswer stub)",
            "paid": True,
            "failover": False,
            "error": None,
        }


class _AccountBridge:
    def __init__(self, *, real: bool = False, demo: bool = True):
        self.real = real
        self.demo = demo
        self.broker_calls = 0

    def will_execute_real_order(self):
        return self.real

    def is_demo_account(self):
        return self.demo

    def get_account_info(self):
        return {
            "balance": 5000.0,
            "equity": 5020.0,
            "margin": 20.0,
            "margin_free": 5000.0,
            "profit": 20.0,
            "leverage": 500,
        }

    def modify_position(self, *_args, **_kwargs):
        self.broker_calls += 1
        raise AssertionError("Position-edge review must never call the broker")


def _config(*, live: bool = False):
    return SimpleNamespace(
        live_mode=live,
        ai_operator_position_edge_enabled=True,
        ai_operator_position_edge_timeout_seconds=12,
        ai_operator_position_edge_review_interval_seconds=60,
        ai_control_values={
            "trailing_stop_enabled": 1,
            "trailing_lock_fraction": 0.5,
        },
    )


def test_local_fallback_reserves_capacity_with_longer_discretionary_interval():
    local = SimpleNamespace(status=lambda: {"active_provider": "local-fallback"})
    paid = SimpleNamespace(status=lambda: {"active_provider": "claude"})

    assert _review_interval_seconds(_config(), local) == 300
    assert _review_interval_seconds(_config(), paid) == 60


def _action(
    intent: str,
    *,
    ticket: int = 123456,
    symbol: str = "US30",
    stop_loss: float | None = 110.0,
    take_profit: float | None = 140.0,
    volume: float | None = None,
    urgency: str = "MEDIUM",
    price_pnl: float = 20.0,
    swap: float = 0.0,
    commission: float = 0.0,
) -> dict[str, Any]:
    return {
        "action_id": f"ai-hedge-management:broker:{ticket}:{intent}",
        "intent": intent,
        "broker_ticket": ticket,
        "position_id": f"broker:{ticket}",
        "symbol": symbol,
        "side": "LONG",
        "timeframe": "H1",
        "strategy": "live_candle_test_h1",
        "broker_method": "close_position" if intent in {"close_partial", "close_full", "reduce"} else "modify_position",
        "open_price": 100.0,
        "current_price": 120.0,
        "previous_stop_loss": 90.0,
        "stop_loss": stop_loss,
        "previous_take_profit": 140.0,
        "take_profit": take_profit,
        "original_volume": 0.04,
        "volume": volume,
        "expected_remaining_volume": 0.02 if volume else None,
        "r_multiple": 2.0,
        "floating_pnl_usd": price_pnl,
        "position_price_pnl_usd": price_pnl,
        "swap_usd": swap,
        "commission_usd": commission,
        "net_open_pnl_after_reported_costs_usd": round(
            price_pnl + swap + commission, 2
        ),
        "open_pnl_basis": "PRICE_PLUS_REPORTED_SWAP_AND_COMMISSION",
        "urgency": urgency,
        "risk_effect": "test_effect",
        "reason": f"Deterministic supervisor drafted {intent}.",
        "evidence_refs": ["position.r_multiple"],
    }


def _snapshot(*, real: bool = False, ticket: int = 123456) -> dict[str, Any]:
    return {
        "status": "FRESH",
        "bridge_executes_real_orders": real,
        "management_policy": {
            "take_profit_reward_risk": 2.0,
            "max_risk_pct_per_trade": 0.1,
        },
        "position_risk": {
            "status": "POSITION_RISK_CAP_BREACH",
            "risk_cap_pct": 0.1,
            "risk_cap_breach_count": 1,
            "risk_cap_breach_tickets": [ticket],
            "combined_entry_to_stop_risk_usd": 40.0,
            "detail": "Existing entry risk exceeds the current cap; evidence only.",
        },
        "quote_attempts": [
            {
                "symbol": "US30",
                "usable": True,
                "quote_source": "fake_mt5",
                "age_seconds": 0.1,
            }
        ],
        "positions": [
            {
                "broker_ticket": ticket,
                "row_id": f"broker:{ticket}",
                "symbol": "US30",
                "side": "LONG",
                "timeframe": "H1",
                "strategy": "live_candle_test_h1",
                "lot_size": 0.04,
                "open_price": 100.0,
                "current_price": 120.0,
                "stop_loss": 90.0,
                "take_profit": 140.0,
                "floating_pnl_usd": 20.0,
                "position_price_pnl_usd": 20.0,
                "swap_usd": 0.0,
                "commission_usd": 0.0,
                "net_open_pnl_after_reported_costs_usd": 20.0,
                "risk_at_stop_usd": 40.0,
                "risk_at_stop_pct_equity": 0.7968,
                "remaining_to_stop_drawdown_usd": 120.0,
                "remaining_to_stop_drawdown_pct_equity": 2.3904,
                "stop_locked_profit_usd": 0.0,
                "risk_cap_pct": 0.1,
                "risk_cap_breached": True,
                "risk_basis": "ORIGINAL_ENTRY_TO_CURRENT_PROTECTIVE_STOP",
                "risk_economics_source": "broker.trade_tick_value/trade_tick_size",
                "price_source": "fake_mt5",
                "quote_age_seconds": 0.1,
            }
        ],
    }


def _outcome_context() -> dict[str, Any]:
    return {
        "status": "REALIZED_OUTCOMES_AVAILABLE",
        "recent_outcomes": [
            {
                "binding_id": "bound-us30-win",
                "broker_ticket": "120000",
                "decision_ref": "prior-us30-long",
                "symbol": "US30",
                "timeframe": "H1",
                "direction": "LONG",
                "strategy_id": "live_candle_test_h1",
                "lot_size": 0.04,
                "net_pnl_per_1_lot_usd": 312.5,
                "net_pnl": 12.5,
                "admission_stop_risk_usd": 10.0,
                "realized_after_cost_r_multiple": 1.25,
                "origin_source": "ORDER_ATTEMPT_LEDGER",
            }
        ],
        "group_stats": [
            {
                "symbol": "US30",
                "timeframe": "H1",
                "direction": "LONG",
                "profile": "live_candle_test_h1",
                "trades": 4,
                "sample_ready": True,
                "net_pnl": 40.0,
                "after_cost_expectancy": 10.0,
                "after_cost_expectancy_r": 0.5,
                "risk_normalized_trade_count": 4,
                "risk_normalized_evidence_complete": True,
                "total_admission_stop_risk_usd": 80.0,
                "after_cost_expectancy_per_1_lot_usd": 250.0,
                "profit_factor": 2.0,
                "win_rate": 0.75,
            }
        ],
    }


def test_operator_selects_one_exact_management_action_with_context(tmp_path):
    actions = [
        _action("close_partial", volume=0.02, stop_loss=None, take_profit=None),
        _action("trail_stop", stop_loss=110.0),
    ]
    provider = _SelectingProvider(intent="trail_stop")
    bridge = _AccountBridge()

    selected, report = review_management_actions_with_operator(
        actions,
        position_snapshot=_snapshot(),
        bridge=bridge,
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        owner_guidance=["Bank profit when the evidence supports it."],
        control_values={"trailing_lock_fraction": 0.5},
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert report["status"] == "AI_OPERATOR_POSITION_DECIDED"
    assert report["selected_action_count"] == 1
    assert report["operator_selected_count"] == 1
    assert report["operator_stand_down_count"] == 0
    assert selected[0]["intent"] == "trail_stop"
    assert selected[0]["stop_loss"] == 110.0
    assert bridge.broker_calls == 0
    assert len(provider.calls) == 1
    prompt, system, kwargs = provider.calls[0]
    assert prompt["current_account"]["balance"] == 5000.0
    assert prompt["current_account"]["north_star"] == "MAXIMIZE_SUSTAINABLE_REALIZED_NET_ACCOUNT_GROWTH"
    assert prompt["current_account"]["position_price_pnl_usd"] == 20.0
    assert prompt["current_account"]["open_swap_usd"] == 0.0
    assert prompt["current_account"]["account_net_open_pnl_usd"] == 20.0
    assert prompt["current_positions"][0]["broker_ticket"] == 123456
    assert prompt["current_positions"][0]["net_open_pnl_after_reported_costs_usd"] == 20.0
    assert prompt["current_positions"][0]["risk_at_stop_usd"] == 40.0
    assert prompt["current_positions"][0]["risk_cap_breached"] is True
    assert prompt["position_risk_summary"]["status"] == "POSITION_RISK_CAP_BREACH"
    assert prompt["management_policy"]["max_risk_pct_per_trade"] == 0.1
    assert prompt["realized_outcome_context"]["candidate_groups"]["ticket:123456"]["same_symbol_direction"]["wins"] == 1
    exact_group = prompt["realized_outcome_context"]["candidate_groups"]["ticket:123456"]
    assert exact_group["growth_evidence_state"] == "EXACT_GROUP_POSITIVE_SAMPLE_READY"
    candidates = prompt["position_action_candidates"][0]["actions"]
    close_partial = next(row for row in candidates if row["intent"] == "close_partial")
    trail = next(row for row in candidates if row["intent"] == "trail_stop")
    assert close_partial["growth_effect"][
        "estimated_immediate_realization_after_reported_costs_usd"
    ] == 10.0
    assert close_partial["growth_effect"]["future_exit_commission_and_slippage_included"] is False
    assert trail["growth_effect"][
        "estimated_immediate_realization_after_reported_costs_usd"
    ] == 0.0
    assert prompt["decision_contract"]["action_geometry_is_immutable"] is True
    assert prompt["decision_contract"]["scale_in_requires_net_profit_after_reported_costs"] is True
    assert prompt["decision_contract"]["current_positions_are_context_only"] is True
    assert prompt["decision_position_keys"] == ["ticket:123456"]
    assert prompt["owner_guidance"] == ["Bank profit when the evidence supports it."]
    assert kwargs["request_timeout"] == 12.0
    schema = kwargs["response_format"]
    assert schema["type"] == "object"
    assert schema["required"] == ["position_decisions", "summary"]
    decision_schema = schema["properties"]["position_decisions"]["items"]
    assert decision_schema["properties"]["decision"]["enum"] == [
        "SELECT",
        "STAND_DOWN",
    ]
    assert report["model_context_projection"]["full_context_retained_in_audit"] is True
    assert "cannot change broker ticket" in system.lower()
    assert "rank learned behavior first by after-cost r expectancy" in system.lower()
    assert "per-lot dollars are not comparable across instruments" in system.lower()
    assert "do not rank learned behavior" not in system.lower()
    assert len(report["event_hash"]) == 64
    assert (tmp_path / "latest.json").exists()


def test_bare_broker_ticket_key_normalizes_to_exact_supplied_position(tmp_path):
    actions = [_action("trail_stop", stop_loss=110.0)]
    provider = _BareTicketSelectingProvider(intent="trail_stop")

    selected, report = review_management_actions_with_operator(
        actions,
        position_snapshot=_snapshot(),
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert [row["intent"] for row in selected] == ["trail_stop"]
    assert report["operator_selected_count"] == 1
    assert report["model_response_normalizations"] == [
        {
            "position_key": "ticket:123456",
            "normalization": "NONCANONICAL_POSITION_KEY_TO_CANONICAL",
            "raw_model_decision": None,
            "raw_model_action": None,
            "raw_model_position_key": "123456",
        }
    ]
    assert report["decisions"][0]["raw_model_position_key"] == "123456"


def test_position_prompt_treats_stand_down_as_hold_and_exposes_scale_horizon(tmp_path):
    action = {
        **_action("close_full", price_pnl=0.36),
        "r_multiple": 0.02,
        "r_multiple_basis": "ORIGINAL_ENTRY_STOP_FROM_ORDER_RECEIPT",
        "operator_discretionary_option": True,
        "operator_selection_required": True,
        "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
        "decision_parameters": {
            "close_basis": "REALIZATION_ONLY_NO_INVALIDATION_EVIDENCE",
            "thesis_invalidation_evidence_supplied": False,
        },
    }
    snapshot = _snapshot()
    snapshot["scale_in_readiness"] = {
        "status": "NO_SCALE_IN_CANDIDATE",
        "action_count": 0,
        "parent_candidate_count": 0,
        "threshold_waiting_parent_count": 1,
        "max_compound_units": 1,
        "minimum_profit_r": 0.5,
        "blockers": [
            {
                "parent_broker_ticket": "123456",
                "symbol": "US30",
                "reason": "winner has not reached the 0.50R scale-in threshold",
                "reason_code": "BELOW_SCALE_IN_THRESHOLD",
                "current_r": 0.02,
                "minimum_profit_r": 0.5,
                "distance_to_threshold_r": 0.48,
                "r_multiple_basis": "ORIGINAL_ENTRY_STOP_FROM_ORDER_RECEIPT",
                "net_open_pnl_after_reported_costs_usd": 0.36,
                "original_stop_loss": 90.0,
                "current_stop_loss": 90.0,
            }
        ],
    }
    provider = _SelectingProvider(stand_down=True)

    selected, report = review_management_actions_with_operator(
        [action],
        position_snapshot=snapshot,
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert selected == []
    assert report["operator_stand_down_count"] == 1
    prompt, system, _kwargs = provider.calls[0]
    readiness = prompt["scale_in_readiness"]
    assert readiness["threshold_waiting_parent_count"] == 1
    assert readiness["blockers"][0]["current_r"] == 0.02
    assert readiness["blockers"][0]["distance_to_threshold_r"] == 0.48
    assert prompt["decision_contract"]["stand_down_semantics"] == "HOLD_CURRENT_POSITION"
    assert prompt["decision_contract"]["tiny_positive_pnl_alone_is_not_a_close_thesis"] is True
    candidate = prompt["position_action_candidates"][0]["actions"][0]
    assert candidate["decision_parameters"]["close_basis"] == "REALIZATION_ONLY_NO_INVALIDATION_EVIDENCE"
    assert "stand_down is an active hold decision" in system.lower()
    assert report["scale_in_readiness"]["minimum_profit_r"] == 0.5


def test_scale_in_choice_routes_position_review_to_pro_escalation(tmp_path):
    action = {
        **_action("scale_in", volume=0.01),
        "broker_method": "order_dispatch",
        "operator_discretionary_option": True,
        "operator_selection_required": True,
        "option_origin": "AI_OPERATOR_WINNING_SCALE_IN",
        "scale_in_unit_index": 1,
        "max_compound_units": 2,
        "sizing_ref": "compound-balanced",
        "sizing_label": "Balanced compound add",
        "sizing_plan_hash": "scale-plan-test",
        "risk_at_stop_usd": 5.0,
        "risk_at_stop_pct_equity": 0.1,
    }
    snapshot = _snapshot()
    snapshot["scale_in_readiness"] = {
        "status": "SCALE_IN_ACTIONS_READY",
        "action_count": 1,
        "parent_candidate_count": 1,
        "threshold_waiting_parent_count": 0,
        "max_compound_units": 2,
        "minimum_profit_r": 0.5,
        "blockers": [],
    }
    provider = _SelectingProvider(intent="scale_in")

    _selected, report = review_management_actions_with_operator(
        [action],
        position_snapshot=snapshot,
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert provider.calls[0][2]["request_kind"] == "compound_scale_in"
    assert report["model_request_kind"] == "compound_scale_in"
    assert report["requested_model_role"] == "pro"


def test_fresh_protected_tiny_loser_cannot_be_closed_as_generic_account_risk(tmp_path):
    action = {
        **_action("close_full", price_pnl=-0.22, urgency="LOW"),
        "r_multiple": -0.0087,
        "r_multiple_basis": "ORIGINAL_ENTRY_STOP_FROM_ORDER_RECEIPT",
        "opened_at_iso": "2026-07-13T22:12:46+00:00",
        "age_days": 24.0 / 86_400.0,
        "operator_discretionary_option": True,
        "operator_selection_required": True,
        "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
        "decision_parameters": {
            "close_basis": "RISK_REDUCTION_REQUIRES_THESIS_REVIEW",
            "thesis_invalidation_evidence_supplied": False,
        },
    }
    provider = _RealizationCloseProvider(
        growth_case="ACCOUNT_RISK_REDUCTION",
        reason="The small opening loss creates account pressure, so close now.",
        summary="Close the fresh position to reduce account pressure.",
    )

    selected, report = review_management_actions_with_operator(
        [action],
        position_snapshot=_snapshot(),
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert selected == []
    assert report["status"] == "MODEL_RESPONSE_REJECTED_PAPER_DISCRETIONARY_STAND_DOWN"
    assert report["model_transport_ok"] is True
    assert report["model_response_rejected"] is True
    assert report["model_failure_stage"] == "MODEL_RESPONSE_CONTRACT"
    assert "fresh-position close rejected" in report["model_error"]
    assert "initial spread or a tiny opening loss is not thesis invalidation" in report[
        "model_error"
    ]


def _tiny_winner_realization_only_close_scenario():
    action = {
        **_action("close_full", price_pnl=0.36),
        "r_multiple": 0.02,
        "r_multiple_basis": "ORIGINAL_ENTRY_STOP_FROM_ORDER_RECEIPT",
        "operator_discretionary_option": True,
        "operator_selection_required": True,
        "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
        "decision_parameters": {
            "close_basis": "REALIZATION_ONLY_NO_INVALIDATION_EVIDENCE",
            "thesis_invalidation_evidence_supplied": False,
        },
    }
    snapshot = _snapshot()
    snapshot["scale_in_readiness"] = {
        "status": "NO_SCALE_IN_CANDIDATE",
        "action_count": 0,
        "parent_candidate_count": 0,
        "threshold_waiting_parent_count": 1,
        "max_compound_units": 1,
        "minimum_profit_r": 0.5,
        "blockers": [
            {
                "parent_broker_ticket": "123456",
                "reason_code": "BELOW_SCALE_IN_THRESHOLD",
                "current_r": 0.02,
                "minimum_profit_r": 0.5,
                "distance_to_threshold_r": 0.48,
            }
        ],
    }
    return action, snapshot


def test_tiny_winner_close_below_scale_horizon_requires_explicit_growth_case(tmp_path):
    action, snapshot = _tiny_winner_realization_only_close_scenario()
    provider = _RealizationCloseProvider(
        growth_case=None,
        reason="Bank the tiny positive amount now.",
        summary="Close the position.",
    )

    selected, report = review_management_actions_with_operator(
        [action],
        position_snapshot=snapshot,
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert selected == []
    assert report["status"] == "MODEL_RESPONSE_REJECTED_PAPER_DISCRETIONARY_STAND_DOWN"
    assert "requires an explicit non-horizon growth_case" in report["model_error"]
    assert report["rejected_model_response"]["position_decisions"][0][
        "selected_intent"
    ] == "close_full"
    assert report["broker_touched"] is False


def test_select_close_with_hold_rationale_is_semantic_contract_failure(tmp_path):
    action, snapshot = _tiny_winner_realization_only_close_scenario()
    provider = _RealizationCloseProvider(
        growth_case="DETERIORATING_EDGE",
        reason="Holding this position allows potential for a larger winner.",
        summary="HOLD position to preserve potential upside.",
    )

    selected, report = review_management_actions_with_operator(
        [action],
        position_snapshot=snapshot,
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert selected == []
    assert "contradicts its bound close_full" in report["model_error"]
    assert report["broker_touched"] is False


def test_actionless_select_with_explicit_hold_normalizes_to_audited_stand_down(tmp_path):
    action = {
        **_action("close_full", volume=None),
        "operator_discretionary_option": True,
        "operator_selection_required": True,
        "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
    }
    provider = _ActionlessSelectProvider(
        reason=(
            "Position is a net loser. Hold to protect the thesis and avoid closing "
            "on a minimal loss without growth justification."
        ),
        summary="Hold the position; no broker-state change is justified.",
    )

    selected, report = review_management_actions_with_operator(
        [action],
        position_snapshot=_snapshot(),
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert selected == []
    assert report["status"] == "AI_OPERATOR_POSITION_DECIDED"
    assert report["model_ok"] is True
    assert report["model_error"] is None
    assert report["operator_stand_down_count"] == 1
    assert report["model_response_normalization_count"] == 1
    assert report["model_response_normalizations"] == [
        {
            "position_key": "ticket:123456",
            "normalization": "ACTIONLESS_SELECT_EXPLICIT_HOLD_TO_STAND_DOWN",
            "raw_model_decision": "SELECT",
            "raw_model_action": None,
        }
    ]
    assert report["decisions"][0]["decision"] == "STAND_DOWN"
    assert report["decisions"][0]["raw_model_decision"] == "SELECT"
    assert report["decisions"][0]["action_ref"] is None
    assert report["broker_touched"] is False


def test_actionless_select_with_action_rationale_remains_contract_failure(tmp_path):
    action = {
        **_action("close_full", volume=None),
        "operator_discretionary_option": True,
        "operator_selection_required": True,
        "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
    }
    provider = _ActionlessSelectProvider(
        reason="Close the position immediately because the thesis has failed.",
        summary="Execute the full close now.",
    )

    selected, report = review_management_actions_with_operator(
        [action],
        position_snapshot=_snapshot(),
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert selected == []
    assert report["status"] == "MODEL_RESPONSE_REJECTED_PAPER_DISCRETIONARY_STAND_DOWN"
    assert "must name one exact supplied action_ref" in report["model_error"]
    assert report["broker_touched"] is False


def test_noncanonical_explicit_hold_maps_unique_position_and_holds_omission(tmp_path):
    actions = [
        {
            **_action("close_full", ticket=1001, symbol="SPX500", volume=None),
            "operator_discretionary_option": True,
            "operator_selection_required": True,
            "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
        },
        {
            **_action("close_full", ticket=1002, symbol="XAUUSD", volume=None),
            "operator_discretionary_option": True,
            "operator_selection_required": True,
            "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
        },
    ]
    snapshot = _snapshot(ticket=1001)
    snapshot["positions"][0]["symbol"] = "SPX500"
    snapshot["positions"].append(
        {
            **snapshot["positions"][0],
            "broker_ticket": 1002,
            "row_id": "broker:1002",
            "symbol": "XAUUSD",
        }
    )
    provider = _NoncanonicalPositionProvider(
        position="SPX500 Long",
        action="HOLD",
        reason="Hold because the growth horizon has not been reached.",
    )

    selected, report = review_management_actions_with_operator(
        actions,
        position_snapshot=snapshot,
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert selected == []
    assert report["status"] == "AI_OPERATOR_POSITION_DECIDED"
    assert report["model_ok"] is True
    assert report["operator_stand_down_count"] == 2
    assert report["model_response_normalization_count"] == 2
    decisions = {row["position_key"]: row for row in report["decisions"]}
    assert decisions["ticket:1001"]["decision_normalization"] == (
        "NONCANONICAL_EXPLICIT_HOLD_TO_STAND_DOWN"
    )
    assert decisions["ticket:1001"]["raw_model_action"] == "HOLD"
    assert decisions["ticket:1002"]["decision_normalization"] == (
        "OMITTED_POSITION_TO_STAND_DOWN"
    )
    assert report["broker_touched"] is False


def test_noncanonical_global_hold_maps_every_position_to_no_action(tmp_path):
    actions = [
        {
            **_action("close_full", ticket=1001, symbol="SPX500", volume=None),
            "operator_discretionary_option": True,
            "operator_selection_required": True,
            "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
        },
        {
            **_action("close_full", ticket=1002, symbol="XAUUSD", volume=None),
            "operator_discretionary_option": True,
            "operator_selection_required": True,
            "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
        },
    ]
    snapshot = _snapshot(ticket=1001)
    snapshot["positions"].append(
        {
            **snapshot["positions"][0],
            "broker_ticket": 1002,
            "row_id": "broker:1002",
            "symbol": "XAUUSD",
        }
    )
    provider = _NoncanonicalPositionProvider(
        position="",
        action="",
        reason="No immediate action required; continue monitoring both positions.",
        summary="Hold positions under the current risk-management plan.",
    )

    selected, report = review_management_actions_with_operator(
        actions,
        position_snapshot=snapshot,
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert selected == []
    assert report["status"] == "AI_OPERATOR_POSITION_DECIDED"
    assert report["model_ok"] is True
    assert report["operator_stand_down_count"] == 2
    assert report["model_response_normalization_count"] == 2
    assert {
        row["decision_normalization"] for row in report["decisions"]
    } == {"NONCANONICAL_GLOBAL_HOLD_TO_STAND_DOWN"}
    assert report["broker_touched"] is False


def test_noncanonical_action_request_without_exact_ref_remains_contract_failure(tmp_path):
    action = {
        **_action("close_full", volume=None),
        "operator_discretionary_option": True,
        "operator_selection_required": True,
        "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
    }
    provider = _NoncanonicalPositionProvider(
        position="US30 Long",
        action="CLOSE",
        reason="Close the position immediately.",
    )

    selected, report = review_management_actions_with_operator(
        [action],
        position_snapshot=_snapshot(),
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert selected == []
    assert report["status"] == "MODEL_RESPONSE_REJECTED_PAPER_DISCRETIONARY_STAND_DOWN"
    assert report["model_error"] == "position_decisions must be a list"
    assert report["broker_touched"] is False


def test_tiny_winner_close_with_explicit_deteriorating_edge_case_is_bound(tmp_path):
    action, snapshot = _tiny_winner_realization_only_close_scenario()
    provider = _RealizationCloseProvider(
        growth_case="DETERIORATING_EDGE",
        reason=(
            "Exact-group after-cost evidence has deteriorated enough that the "
            "remaining expected loss exceeds the tiny realization value."
        ),
        summary="Close the full position because its measured edge deteriorated.",
    )

    selected, report = review_management_actions_with_operator(
        [action],
        position_snapshot=snapshot,
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert [row["intent"] for row in selected] == ["close_full"]
    assert report["decisions"][0]["selected_intent"] == "close_full"
    assert report["decisions"][0]["growth_case"] == "DETERIORATING_EDGE"


def test_context_only_position_row_cannot_invalidate_valid_operator_decision(tmp_path):
    snapshot = _snapshot()
    snapshot["positions"].append(
        {
            **snapshot["positions"][0],
            "broker_ticket": 987654,
            "row_id": "broker:987654",
            "symbol": "XAUUSD",
        }
    )
    provider = _ContextOveranswerProvider()
    action = _action("trail_stop", stop_loss=110.0)

    selected, report = review_management_actions_with_operator(
        [action],
        position_snapshot=snapshot,
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert report["status"] == "AI_OPERATOR_POSITION_DECIDED"
    assert report["model_ok"] is True
    assert report["selected_action_count"] == 1
    assert selected[0]["action_id"] == action["action_id"]
    assert len(report["decisions"]) == 1
    assert report["decisions"][0]["position_key"] == "ticket:123456"
    assert report["decisions"][0]["decision"] == "SELECT"
    assert report["decisions"][0]["action_ref"] == report["selected_action_refs"][0]


def test_position_origin_recovers_strategy_and_timeframe_from_executed_order(tmp_path):
    path = tmp_path / "order-attempts.json"
    path.write_text(
        json.dumps(
            {
                "attempts": {
                    "attempt-key": {
                        "executed": True,
                        "decision_ref": "entry-decision-1",
                        "order_id": "entry-order-1",
                        "order": {
                            "price": 0.0,
                            "stop_loss": 99.0,
                            "take_profit": 104.0,
                            "volume": 0.04,
                        },
                        "updated_at": "2026-07-11T10:00:00+00:00",
                        "proposed_intent": {
                            "timeframe": "M5",
                            "entry_price": 100.0,
                            "risk_at_stop_usd": 10.0,
                        },
                        "execution_provenance": {
                            "strategy": {"strategy_id": "micro_scalp_m5"}
                        },
                        "result": {
                            "outcome": {
                                "broker_ticket": 987654,
                                "timestamp": "2026-07-11T09:59:58Z",
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    origins = _position_origin_by_ticket(path)

    assert origins["987654"]["timeframe"] == "M5"
    assert origins["987654"]["strategy"] == "micro_scalp_m5"
    assert origins["987654"]["decision_ref"] == "entry-decision-1"
    assert origins["987654"]["source"] == "ORDER_ATTEMPT_LEDGER"
    assert origins["987654"]["original_entry_price"] == 100.0
    assert origins["987654"]["original_stop_loss"] == 99.0
    assert origins["987654"]["original_take_profit"] == 104.0
    assert origins["987654"]["original_volume"] == 0.04
    assert origins["987654"]["admission_stop_risk_usd"] == 10.0
    assert origins["987654"]["opened_at_iso"] == "2026-07-11T09:59:58+00:00"
    assert origins["987654"]["opened_at_source"] == (
        "BROKER_EXECUTION_RECEIPT_TIMESTAMP"
    )


def test_hard_protection_action_is_non_vetoable_and_does_not_call_model(tmp_path):
    provider = _SelectingProvider(stand_down=True)
    action = _action("set_stop_loss", stop_loss=95.0, urgency="HIGH")

    selected, report = review_management_actions_with_operator(
        [action],
        position_snapshot=_snapshot(),
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert selected == [action]
    assert report["status"] == "HARD_POLICY_ACTIONS_SELECTED"
    assert report["hard_policy_selected_count"] == 1
    assert report["decisions"][0]["decision"] == "HARD_POLICY_SELECT"
    assert provider.calls == []


def test_malformed_paper_response_uses_guarded_priority_fallback(tmp_path):
    actions = [
        _action("trail_stop", stop_loss=110.0),
        _action("close_partial", volume=0.02, stop_loss=None, take_profit=None),
    ]
    provider = _BrokenProvider()

    selected, report = review_management_actions_with_operator(
        actions,
        position_snapshot=_snapshot(),
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert report["status"] == "DEGRADED_PAPER_POLICY_FALLBACK"
    assert [row["intent"] for row in selected] == ["close_partial"]
    assert report["decisions"][0]["decision"] == "PAPER_POLICY_FALLBACK"


def test_model_failure_never_auto_selects_operator_only_position_option(tmp_path):
    action = {
        **_action("close_full", volume=None),
        "operator_discretionary_option": True,
        "operator_selection_required": True,
        "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
    }
    provider = _BrokenProvider()

    selected, report = review_management_actions_with_operator(
        [action],
        position_snapshot=_snapshot(),
        bridge=_AccountBridge(),
        config=_config(),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert selected == []
    assert report["status"] == "MODEL_UNAVAILABLE_PAPER_DISCRETIONARY_STAND_DOWN"
    assert report["model_transport_ok"] is False
    assert report["model_response_rejected"] is False
    assert report["model_failure_stage"] == "MODEL_PROVIDER"
    assert report["policy_fallback_selected_count"] == 0
    assert report["operator_stand_down_count"] == 1
    assert report["decisions"][0]["decision"] == "STAND_DOWN"


def test_live_model_failure_stands_down_discretionary_but_keeps_other_position_protected(tmp_path):
    actions = [
        _action("set_stop_loss", ticket=1001, stop_loss=95.0, urgency="HIGH"),
        _action("trail_stop", ticket=1002, stop_loss=110.0),
    ]
    provider = _BrokenProvider()
    snapshot = _snapshot(real=True, ticket=1001)
    snapshot["positions"].append(
        {**snapshot["positions"][0], "broker_ticket": 1002, "row_id": "broker:1002"}
    )

    selected, report = review_management_actions_with_operator(
        actions,
        position_snapshot=snapshot,
        bridge=_AccountBridge(real=True, demo=False),
        config=_config(live=True),
        provider=provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=tmp_path / "latest.json",
    )

    assert report["status"] == "MODEL_UNAVAILABLE_LIVE_DISCRETIONARY_STAND_DOWN"
    assert [(row["broker_ticket"], row["intent"]) for row in selected] == [(1001, "set_stop_loss")]
    assert report["operator_stand_down_count"] == 1
    assert report["hard_policy_selected_count"] == 1


def test_same_exact_action_set_reuses_recent_operator_decision(tmp_path):
    action = _action("trail_stop", stop_loss=110.0)
    latest = tmp_path / "latest.json"
    first_provider = _SelectingProvider(intent="trail_stop")
    first, first_report = review_management_actions_with_operator(
        [action],
        position_snapshot=_snapshot(),
        bridge=_AccountBridge(),
        config=_config(),
        provider=first_provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=latest,
    )
    second_provider = _SelectingProvider(stand_down=True)
    second, second_report = review_management_actions_with_operator(
        [action],
        position_snapshot=_snapshot(),
        bridge=_AccountBridge(),
        config=_config(),
        provider=second_provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=latest,
    )

    assert first[0]["intent"] == "trail_stop"
    assert first_report["status"] == "AI_OPERATOR_POSITION_DECIDED"
    assert second[0]["intent"] == "trail_stop"
    assert second_report["status"] == "AI_OPERATOR_POSITION_DECISION_REUSED"
    assert second_report["source_event_hash"] == first_report["event_hash"]
    assert second_provider.calls == []


def test_moving_operator_only_geometry_waits_for_review_interval_without_stale_reuse(tmp_path):
    latest = tmp_path / "latest.json"
    first_action = {
        **_action("close_full", price_pnl=20.0),
        "operator_discretionary_option": True,
        "operator_selection_required": True,
        "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
    }
    first_provider = _SelectingProvider(stand_down=True)
    _, first_report = review_management_actions_with_operator(
        [first_action],
        position_snapshot=_snapshot(),
        bridge=_AccountBridge(),
        config=_config(),
        provider=first_provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=latest,
    )

    changed = {
        **_action("close_full", price_pnl=21.0),
        "current_price": 121.0,
        "operator_discretionary_option": True,
        "operator_selection_required": True,
        "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
    }
    changed_snapshot = _snapshot()
    changed_snapshot["positions"][0].update(
        {
            "current_price": 121.0,
            "floating_pnl_usd": 21.0,
            "position_price_pnl_usd": 21.0,
            "net_open_pnl_after_reported_costs_usd": 21.0,
        }
    )
    second_provider = _SelectingProvider(intent="close_full")
    selected, second_report = review_management_actions_with_operator(
        [changed],
        position_snapshot=changed_snapshot,
        bridge=_AccountBridge(),
        config=_config(),
        provider=second_provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=latest,
    )

    assert first_report["status"] == "AI_OPERATOR_POSITION_DECIDED"
    assert selected == []
    assert second_report["status"] == "AI_OPERATOR_DISCRETIONARY_REVIEW_DEFERRED"
    assert second_report["operator_stand_down_count"] == 0
    assert second_report["operator_deferred_count"] == 1
    assert second_report["decisions"][0]["decision"] == "DEFERRED_INTERVAL"
    assert second_report["next_review_at"]
    assert second_report["event_hash"]
    assert second_provider.calls == []


def test_material_profit_band_change_wakes_operator_inside_review_interval(tmp_path):
    latest = tmp_path / "latest.json"
    first_action = {
        **_action("trail_stop", price_pnl=4.0),
        "current_price": 104.0,
        "r_multiple": 0.4,
        "operator_discretionary_option": True,
        "operator_selection_required": True,
        "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
    }
    first_snapshot = _snapshot()
    first_snapshot["positions"][0].update(
        {
            "current_price": 104.0,
            "floating_pnl_usd": 4.0,
            "position_price_pnl_usd": 4.0,
            "net_open_pnl_after_reported_costs_usd": 4.0,
        }
    )
    first_provider = _SelectingProvider(stand_down=True)
    _, first_report = review_management_actions_with_operator(
        [first_action],
        position_snapshot=first_snapshot,
        bridge=_AccountBridge(),
        config=_config(),
        provider=first_provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=latest,
    )

    scale_horizon_action = {
        **first_action,
        "current_price": 106.0,
        "r_multiple": 0.6,
        "floating_pnl_usd": 6.0,
        "position_price_pnl_usd": 6.0,
        "net_open_pnl_after_reported_costs_usd": 6.0,
    }
    changed_snapshot = _snapshot()
    changed_snapshot["positions"][0].update(
        {
            "current_price": 106.0,
            "floating_pnl_usd": 6.0,
            "position_price_pnl_usd": 6.0,
            "net_open_pnl_after_reported_costs_usd": 6.0,
        }
    )
    second_provider = _SelectingProvider(intent="trail_stop")
    selected, second_report = review_management_actions_with_operator(
        [scale_horizon_action],
        position_snapshot=changed_snapshot,
        bridge=_AccountBridge(),
        config=_config(),
        provider=second_provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=latest,
    )

    assert first_report["status"] == "AI_OPERATOR_POSITION_DECIDED"
    assert first_report["review_trigger_hash"] != second_report["review_trigger_hash"]
    assert second_report["status"] == "AI_OPERATOR_POSITION_DECIDED"
    assert selected[0]["intent"] == "trail_stop"
    assert len(second_provider.calls) == 1


def test_position_decision_is_not_reused_after_after_cost_pnl_changes(tmp_path):
    latest = tmp_path / "latest.json"
    first_action = _action("trail_stop", stop_loss=110.0, price_pnl=20.0)
    first_provider = _SelectingProvider(intent="trail_stop")
    first_snapshot = _snapshot()
    _, first_report = review_management_actions_with_operator(
        [first_action],
        position_snapshot=first_snapshot,
        bridge=_AccountBridge(),
        config=_config(),
        provider=first_provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=latest,
    )

    second_action = _action(
        "trail_stop",
        stop_loss=110.0,
        price_pnl=20.0,
        swap=-25.0,
    )
    second_snapshot = _snapshot()
    second_snapshot["positions"][0].update(
        {
            "position_price_pnl_usd": 20.0,
            "floating_pnl_usd": 20.0,
            "swap_usd": -25.0,
            "commission_usd": 0.0,
            "net_open_pnl_after_reported_costs_usd": -5.0,
        }
    )
    second_provider = _SelectingProvider(stand_down=True)
    selected, second_report = review_management_actions_with_operator(
        [second_action],
        position_snapshot=second_snapshot,
        bridge=_AccountBridge(),
        config=_config(),
        provider=second_provider,
        enabled=True,
        decision_context=_outcome_context(),
        audit_path=tmp_path / "audit.jsonl",
        latest_path=latest,
    )

    assert first_report["status"] == "AI_OPERATOR_POSITION_DECIDED"
    assert second_report["status"] == "AI_OPERATOR_POSITION_DECIDED"
    assert selected == []
    assert len(second_provider.calls) == 1
    assert second_provider.calls[0][0]["current_positions"][0][
        "net_open_pnl_after_reported_costs_usd"
    ] == -5.0


class _CycleBridge:
    def __init__(self):
        self.positions = {
            123456: {
                "ticket": 123456,
                "symbol": "US30",
                "type": "BUY",
                "volume": 0.04,
                "open_price": 100.0,
                "current_price": 120.0,
                "stop_loss": 90.0,
                "take_profit": 140.0,
                "profit": 20.0,
                "comment": "CAS_TEST",
                "opened_at_iso": utc_now().isoformat(),
            }
        }
        self.modify_calls: list[dict[str, Any]] = []
        self.close_calls: list[dict[str, Any]] = []

    def is_connected(self):
        return True

    def will_execute_real_order(self):
        return False

    def get_open_positions(self):
        return [dict(row) for row in self.positions.values()]

    def get_all_open_positions(self):
        return [dict(row) for row in self.positions.values()]

    def get_account_info(self):
        return {"balance": 5000.0, "equity": 5020.0, "margin": 20.0, "margin_free": 5000.0}

    def modify_position(self, ticket, *, stop_loss, take_profit=None):
        self.modify_calls.append({"ticket": ticket, "stop_loss": stop_loss, "take_profit": take_profit})
        self.positions[ticket]["stop_loss"] = stop_loss
        if take_profit is not None:
            self.positions[ticket]["take_profit"] = take_profit
        return OrderOutcome(
            order_ref=f"modify-{ticket}",
            broker_ticket=ticket,
            status=OrderStatus.EXECUTED,
        )

    def close_position(self, ticket, volume=None):
        self.close_calls.append({"ticket": ticket, "volume": volume})
        if volume is None:
            self.positions.pop(ticket, None)
        elif ticket in self.positions:
            remaining = round(float(self.positions[ticket]["volume"]) - float(volume), 2)
            if remaining <= 0:
                self.positions.pop(ticket, None)
            else:
                self.positions[ticket]["volume"] = remaining
        return True


def _cycle_config():
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
        ai_operator_position_edge_enabled=True,
        ai_operator_position_edge_timeout_seconds=12,
        ai_operator_position_edge_review_interval_seconds=60,
        ai_control_values={
            "trailing_stop_enabled": 1,
            "trailing_lock_fraction": 0.5,
        },
    )


def _quote_builder(_symbol, *, config=None):
    _ = config
    return {
        "quote_source": "fake_mt5",
        "quote_feed_label": "fake MT5 quote",
        "market_snapshot": {
            "symbol": "US30",
            "bid": 120.0,
            "ask": 120.2,
            "timestamp": utc_now().isoformat(),
            "is_market_open": True,
            "synthetic_fallback": False,
            "source": "fake_mt5",
        },
    }


def test_management_cycle_executes_only_operator_selected_exact_action(tmp_path):
    bridge = _CycleBridge()
    provider = _SelectingProvider(intent="trail_stop")

    result = run_ai_hedge_management_cycle(
        bridge=bridge,
        config=_cycle_config(),
        execute=True,
        state_path=tmp_path / "cycle-state.json",
        audit_path=tmp_path / "execution-audit.jsonl",
        quote_context_builder=_quote_builder,
        operator_provider=provider,
        operator_review_enabled=True,
        operator_decision_context=_outcome_context(),
        operator_audit_path=tmp_path / "operator-audit.jsonl",
        operator_latest_path=tmp_path / "operator-latest.json",
    )

    assert result["status"] == "ACTIONS_EXECUTED"
    assert result["operator_position_edge_status"] == "AI_OPERATOR_POSITION_DECIDED"
    assert result["operator_position_edge_selected_count"] == 1
    assert bridge.close_calls == []
    assert bridge.modify_calls == [
        {"ticket": 123456, "stop_loss": 110.0, "take_profit": 140.0}
    ]
    assert result["executions"][0]["selected_action"]["intent"] == "trail_stop"
    assert result["executions"][0]["operator_position_edge_event_hash"]
    selected = result["executions"][0]["selected_action"]
    assert selected["operator_prompt_version"] == "ai_operator_position_edge.v14"
    assert selected["operator_provider"] == "claude"
    assert selected["operator_model_ref"] == "claude-sonnet-5"
    assert selected["operator_event_hash"] == result["executions"][0][
        "operator_position_edge_event_hash"
    ]
    provenance = result["executions"][0]["order_dispatch"]["execution_provenance"]
    assert provenance["operator_decision"]["action_ref"] == selected[
        "operator_action_ref"
    ]
    assert provenance["operator_decision"]["model_ref"] == "claude-sonnet-5"
    assert provenance["version_trace"]["prompt_version"] == (
        "ai_operator_position_edge.v14"
    )
    assert provenance["version_trace"]["model_ref"] == "claude-sonnet-5"


def test_management_cycle_records_operator_stand_down_without_broker_call(tmp_path):
    bridge = _CycleBridge()
    provider = _SelectingProvider(stand_down=True)

    result = run_ai_hedge_management_cycle(
        bridge=bridge,
        config=_cycle_config(),
        execute=True,
        state_path=tmp_path / "cycle-state.json",
        audit_path=tmp_path / "execution-audit.jsonl",
        quote_context_builder=_quote_builder,
        operator_provider=provider,
        operator_review_enabled=True,
        operator_decision_context=_outcome_context(),
        operator_audit_path=tmp_path / "operator-audit.jsonl",
        operator_latest_path=tmp_path / "operator-latest.json",
    )

    assert result["status"] == "AI_OPERATOR_STOOD_DOWN"
    assert result["attempted_action_count"] == 0
    assert result["operator_position_edge_stand_down_count"] == 1
    assert bridge.modify_calls == []
    assert bridge.close_calls == []


def test_management_cycle_lets_operator_bank_profit_between_fixed_r_triggers(tmp_path):
    bridge = _CycleBridge()
    bridge.positions[123456].update({"current_price": 108.0, "profit": 8.0})
    provider = _SelectingProvider(intent="close_full")

    result = run_ai_hedge_management_cycle(
        bridge=bridge,
        config=_cycle_config(),
        execute=True,
        state_path=tmp_path / "cycle-state.json",
        audit_path=tmp_path / "execution-audit.jsonl",
        quote_context_builder=lambda symbol, **kwargs: {
            **_quote_builder(symbol, **kwargs),
            "market_snapshot": {
                **_quote_builder(symbol, **kwargs)["market_snapshot"],
                "bid": 108.0,
                "ask": 108.2,
            },
        },
        operator_provider=provider,
        operator_review_enabled=True,
        operator_decision_context=_outcome_context(),
        operator_audit_path=tmp_path / "operator-audit.jsonl",
        operator_latest_path=tmp_path / "operator-latest.json",
    )

    prompt = provider.calls[0][0]
    supplied_intents = {
        row["intent"]
        for group in prompt["position_action_candidates"]
        for row in group["actions"]
    }
    assert "close_full" in supplied_intents
    assert prompt["decision_contract"][
        "fresh_manageable_positions_receive_operator_options"
    ] is True
    assert result["status"] == "ACTIONS_EXECUTED"
    assert result["operator_discretionary_status"] == (
        "OPERATOR_DISCRETIONARY_OPTIONS_READY"
    )
    assert result["operator_discretionary_option_count"] >= 1
    assert result["operator_position_edge_status"] == "AI_OPERATOR_POSITION_DECIDED"
    assert result["executions"][0]["selected_action"]["intent"] == "close_full"
    assert bridge.close_calls == [{"ticket": 123456, "volume": None}]
