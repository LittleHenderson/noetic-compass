"""Tests for the AI operator brain (cas_forex/ai_operator.py).

Load-bearing invariant for this tick surface: it can only apply owner-fenced
dial changes, each clamped to owner bounds. Product-wide autonomous order and
money-movement intent must use the separate guarded dispatch/provider paths,
and an unparseable / malicious model reply produces NO action.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from cas_forex import ai_operator, model_provider
from cas_forex.ai_control_authority import AiControlAuthority, set_authority_for_tests
from cas_forex.mt5_account_growth import account_identity_hash


class _StubProvider:
    def __init__(self, text, *, ok=True, provider="claude", paid=True, failover=False):
        self._text = text
        self._ok = ok
        self._provider = provider
        self._paid = paid
        self._failover = failover

    def generate(self, prompt, system=None):
        return {
            "ok": self._ok,
            "text": self._text,
            "provider": self._provider,
            "provider_label": f"{self._provider} (stub)",
            "paid": self._paid,
            "failover": self._failover,
            "switch_reason": "",
            "error": None if self._ok else "no model",
        }


def _operator(tmp_path, monkeypatch, provider):
    set_authority_for_tests(AiControlAuthority(tmp_path / "authority.json"))
    model_provider.set_model_provider_for_tests(provider)
    import cas_forex.spec_context as spec_context

    monkeypatch.setattr(spec_context, "operator_constitution", lambda: "")
    return ai_operator.AIOperator(actions_path=tmp_path / "actions.jsonl")


def _teardown():
    set_authority_for_tests(None)
    model_provider.set_model_provider_for_tests(None)


def test_compact_learning_keeps_bounded_leading_group_rows():
    groups = [{"symbol": f"PAIR-{index}", "confirmed_count": index} for index in range(12)]

    compact = ai_operator._compact({"status": "ACTIVE", "groups": groups})

    assert compact["group_count"] == 12
    assert compact["groups"] == groups[:8]


def test_compact_mt5_snapshot_keeps_broker_stop_risk_for_operator_chat():
    assert "A value of 0.1 means 0.1%" in ai_operator._OPERATOR_SYSTEM_PROMPT
    assert "never as a direct comparison to the per-trade cap" in ai_operator._OPERATOR_SYSTEM_PROMPT
    assert "PAPER_SIM, research, replay, or demo evidence is not proof" in ai_operator._OPERATOR_SYSTEM_PROMPT
    assert "does not change the stop, size, or risk geometry" in ai_operator._OPERATOR_SYSTEM_PROMPT
    assert "net winning after currently reported" in ai_operator._OPERATOR_SYSTEM_PROMPT
    assert "pre-cost winner" in ai_operator._OPERATOR_SYSTEM_PROMPT
    compact = ai_operator._compact_mt5_snapshot(
        {
            "connected": True,
            "is_demo": True,
            "account": {
                "login": 1000694,
                "equity_usd": 44_779.12,
                "floating_pnl_usd": -60.0,
            },
            "position_risk": {
                "status": "POSITION_RISK_CAP_BREACH",
                "risk_cap_pct": 0.1,
                "risk_cap_breach_count": 1,
            },
            "positions": [
                {
                    "ticket": 45944855,
                    "symbol": "US30",
                    "side": "SHORT",
                    "lots": 0.01,
                    "open_price": 52_597.82,
                    "current_price": 52_650.0,
                    "stop_loss": 52_734.75,
                    "take_profit": 52_374.18,
                    "floating_pnl_usd": -52.18,
                    "swap_usd": -7.60,
                    "commission_usd": -0.22,
                    "risk_at_stop_usd": 136.93,
                    "risk_at_stop_pct_equity": 0.3058,
                    "remaining_to_stop_drawdown_usd": 84.75,
                    "risk_cap_pct": 0.1,
                    "risk_cap_breached": True,
                    "risk_basis": "ORIGINAL_ENTRY_TO_CURRENT_PROTECTIVE_STOP",
                    "risk_economics_source": "broker.trade_tick_value/trade_tick_size",
                }
            ],
        }
    )

    assert compact["position_risk"]["status"] == "POSITION_RISK_CAP_BREACH"
    assert compact["percentage_convention"].startswith("Fields ending in _pct")
    assert compact["position_risk"]["risk_cap_label"] == "0.1% of current equity per trade"
    assert compact["position_risk"]["comparison_note"].startswith("The per-trade cap applies separately")
    assert compact["position_risk_preview"][0]["ticket"] == 45944855
    assert compact["position_risk_preview"][0]["risk_at_stop_usd"] == 136.93
    assert compact["position_risk_preview"][0]["risk_at_stop_label"] == "$136.93 (0.3% of current equity)"
    assert compact["position_risk_preview"][0]["risk_cap_label"] == "0.1% of current equity per trade"
    assert compact["position_risk_preview"][0]["risk_cap_breached"] is True
    assert compact["position_risk_preview"][0]["swap_usd"] == -7.60
    assert compact["position_risk_preview"][0]["commission_usd"] == -0.22
    assert compact["position_risk_preview"][0]["net_open_pnl_after_reported_costs_usd"] == -60.0
    assert compact["open_pnl_decomposition"] == {
        "price_pnl_usd": -52.18,
        "swap_or_carry_usd": -7.6,
        "commission_usd": -0.22,
        "reported_components_usd": -60.0,
        "account_net_open_pnl_usd": -60.0,
        "unattributed_open_pnl_usd": 0.0,
        "interpretation": "NET_AFTER_REPORTED_OPEN_COSTS_NOT_REALIZED_PROFIT",
    }
    assert compact["top_symbols_by_abs_floating_pnl"][0]["entry_to_stop_risk_usd"] == 136.93


def test_operator_applies_a_fenced_dial(tmp_path, monkeypatch):
    decision = {
        "observations": "too few candidates in quiet markets",
        "actions": [
            {
                "type": "adjust_dial",
                "lever": "min_directional_confidence",
                "value": 0.1,
                "reason": "paper scan is starved; rollback if weak candidates rise",
            }
        ],
        "summary": "loosen confidence",
    }
    op = _operator(tmp_path, monkeypatch, _StubProvider(json.dumps(decision)))
    try:
        tick = op.tick()
        d = tick.to_dict()
        assert d["ok"] is True
        assert d["provider"] == "claude"
        assert len(d["actions_applied"]) == 1
        assert d["actions_applied"][0]["lever"] == "min_directional_confidence"
        from cas_forex.ai_control_authority import get_authority

        assert abs(float(get_authority().control.get("min_directional_confidence")) - 0.1) < 1e-9
    finally:
        _teardown()


def _starved_entry_context() -> dict[str, object]:
    from cas_forex.ai_operator_context import CRITICAL_SECTIONS

    context: dict[str, object] = {
        key: {"status": "TEST_PRESENT"} for key in CRITICAL_SECTIONS
    }
    context["operator_constitution"] = "# Test Operator Constitution"
    context["entry_opportunity_pipeline"] = {
        "status": "ALL_OBSERVED_LANES_BELOW_DIRECTIONAL_FLOOR",
        "dispatch": {
            "running": True,
            "execution_lane": "PAPER",
            "paper_learning_active": True,
            "eligible_symbol_count": 17,
            "operator_candidate_count": 0,
            "bridge_class": "MT5Bridge",
            "bridge_selection_status": "PAPER_MT5_ORDER_SEND_READY",
        },
        "multi_timeframe_scan_runtime": {
            "attempt_count": 68,
            "shadow_edge_status_counts": {"PASS": 1, "NO_TRADE_NULL_FAILED": 67},
            "shadow_pass_preview_count": 1,
            "all_observed_lanes_below_directional_floor": True,
            "best_shadow_pass_lane": {
                "symbol": "EUR/USD",
                "timeframe": "H1",
                "direction": "SHORT",
                "directional_score": 0.32,
                "directional_floor": 0.5,
                "shadow_edge_status": "PASS",
                "shadow_measured_win_prob": 0.9091,
                "shadow_null_p95": 0.02,
                "shadow_threshold": 0.65,
                "shadow_edge_preview_unregistered": True,
                "shadow_edge_authorization_minted": False,
                "shadow_has_edge_token": False,
            },
            "strongest_rejected_lane": {
                "symbol": "EUR/GBP",
                "timeframe": "H1",
                "direction": "SHORT",
                "directional_score": 0.3895,
                "directional_floor": 0.5,
                "shadow_edge_status": "PASS",
                "shadow_measured_win_prob": 0.9091,
                "shadow_null_p95": 0.02,
                "shadow_threshold": 0.65,
                "shadow_edge_preview_unregistered": True,
                "shadow_edge_authorization_minted": False,
                "shadow_has_edge_token": False,
            },
        },
        "operator_adjustable_candidate_controls": {
            "min_directional_confidence": 0.5,
            "min_directional_confidence_bounds": {"min": 0.05, "max": 0.9},
            "paper_learning_trades": 1,
        },
    }
    return context


def _capacity_starved_context() -> dict[str, object]:
    from cas_forex.ai_operator_context import CRITICAL_SECTIONS

    context: dict[str, object] = {
        key: {"status": "TEST_PRESENT"} for key in CRITICAL_SECTIONS
    }
    context["operator_constitution"] = "# Test Operator Constitution"
    context["entry_opportunity_pipeline"] = {
        "status": "POSITION_CAPACITY_STARVATION",
        "dispatch": {
            "running": True,
            "execution_lane": "PAPER",
            "paper_learning_active": True,
            "operator_candidate_count": 0,
            "bridge_class": "MT5Bridge",
            "bridge_selection_status": "PAPER_MT5_ORDER_SEND_READY",
        },
        "capacity_pressure": {
            "status": "POSITION_CAPACITY_STARVATION",
            "mode": "PAPER_FALLBACK",
            "cap_block_event_count": 29,
            "distinct_symbol_count": 12,
            "symbols": ["AUD/JPY", "EUR/GBP", "GBP/JPY", "USD/CHF"],
            "current_open_position_count": 4,
            "current_max_open_position_count": 4,
            "current_total_exposure_lots": 0.04,
            "current_max_total_exposure_lots": 2.0,
            "exposure_utilization_pct": 2.0,
            "explicit_owner_override_active": False,
            "autonomous_one_slot_review_allowed": True,
            "recommended_review_cap": 5,
            "event_hash": "capacity-test-hash",
        },
        "operator_adjustable_candidate_controls": {
            "max_concurrent_trades": 4,
            "max_concurrent_trades_bounds": {"min": 1, "max": 50},
            "max_total_exposure_lots": 2.0,
        },
    }
    return context


def test_operator_applies_exact_one_slot_capacity_decision(tmp_path, monkeypatch):
    decision = {
        "observations": (
            "29 repeated cross-market candidates hit the 4-position capacity cap "
            "while total exposure utilization is only 2%."
        ),
        "actions": [
            {
                "type": "adjust_dial",
                "lever": "max_concurrent_trades",
                "value": 5,
                "reason": (
                    "Add one capacity slot because 29 repeated cross-market candidate "
                    "blocks occurred while separate exposure utilization is 2%; every "
                    "fresh PAPER entry gate still applies."
                ),
            }
        ],
        "lessons": [],
        "summary": "Raise the capacity cap one slot; this does not approve an entry.",
    }

    class _CapacityProvider:
        def __init__(self):
            self.prompts = []
            self.systems = []

        def generate(self, prompt, system=None, **_kwargs):
            self.prompts.append(prompt)
            self.systems.append(system)
            return {
                "ok": True,
                "text": json.dumps(decision),
                "provider": "local-fallback",
                "provider_label": "Local model (test)",
                "paid": False,
                "failover": False,
            }

    provider = _CapacityProvider()
    op = _operator(tmp_path, monkeypatch, provider)
    monkeypatch.setattr(
        ai_operator,
        "_capacity_policy_apply_revalidation",
        lambda _authority, _proposed: {
            "allowed": True,
            "status": "CAPACITY_PRESSURE_REVALIDATED_AT_APPLY",
        },
    )
    monkeypatch.setattr(
        ai_operator,
        "gather_context",
        lambda _config=None: _capacity_starved_context(),
    )
    from cas_forex.ai_control_authority import get_authority

    get_authority().control.adjust("max_concurrent_trades", 4)
    try:
        tick = op.tick().to_dict()

        assert tick["ok"] is True
        assert provider.prompts[0].startswith("FOCUSED ENTRY-CAPACITY DECISION")
        assert "focused portfolio-capacity specialist" in provider.systems[0]
        assert tick["response_contract_status"] == (
            "EVIDENCE_BASED_ONE_SLOT_CAPACITY_ADJUSTMENT"
        )
        assert tick["actions_applied"][0]["lever"] == "max_concurrent_trades"
        assert tick["actions_applied"][0]["new_value"] == 5
        assert get_authority().control.get("max_concurrent_trades") == 5
    finally:
        _teardown()


def test_capacity_contract_rejects_multi_slot_jump():
    context = _capacity_starved_context()
    decision = {
        "observations": "29 candidates were blocked at capacity with exposure at 2%.",
        "actions": [
            {
                "type": "adjust_dial",
                "lever": "max_concurrent_trades",
                "value": 8,
                "reason": (
                    "Repeated candidate capacity blocks occurred while exposure "
                    "utilization remained low."
                ),
            }
        ],
        "lessons": [],
        "summary": "Increase capacity.",
    }

    result = ai_operator._entry_opportunity_decision_contract(decision, context)

    assert result["valid"] is False
    assert result["status"] == "CAPACITY_ACTION_EXCEEDS_ONE_SLOT_CONTRACT"
    assert "exact recommended cap 5" in result["error"]


def test_capacity_contract_accepts_explicit_evidence_based_stand_down():
    context = _capacity_starved_context()
    decision = {
        "observations": (
            "STAND_DOWN at the current cap 4 despite 29 blocked candidates and "
            "2% exposure utilization because correlated portfolio risk and weak "
            "after-cost edge evidence do not justify another slot."
        ),
        "actions": [],
        "lessons": [],
        "summary": "STAND_DOWN and retain the current portfolio cap.",
    }

    result = ai_operator._entry_opportunity_decision_contract(decision, context)

    assert result["valid"] is True
    assert result["status"] == "EXPLICIT_CAPACITY_STAND_DOWN"


def test_capacity_policy_fallback_applies_after_invalid_model_replies(
    tmp_path, monkeypatch
):
    invalid = {
        "observations": "There are no candidates in this current scheduler tick.",
        "actions": [],
        "lessons": [],
        "summary": "No change.",
    }

    class _InvalidCapacityProvider:
        def __init__(self):
            self.calls = 0

        def generate(self, _prompt, _system=None, **_kwargs):
            self.calls += 1
            return {
                "ok": True,
                "text": json.dumps(invalid),
                "provider": "local-fallback",
                "provider_label": "Local model (test)",
                "paid": False,
                "failover": False,
            }

    provider = _InvalidCapacityProvider()
    op = _operator(tmp_path, monkeypatch, provider)
    monkeypatch.setattr(
        ai_operator,
        "_capacity_policy_apply_revalidation",
        lambda _authority, _proposed: {
            "allowed": True,
            "status": "CAPACITY_PRESSURE_REVALIDATED_AT_APPLY",
        },
    )
    monkeypatch.setattr(
        ai_operator,
        "gather_context",
        lambda _config=None: _capacity_starved_context(),
    )
    from cas_forex.ai_control_authority import get_authority

    get_authority().control.adjust("max_concurrent_trades", 4)
    try:
        tick = op.tick().to_dict()

        assert provider.calls == 1
        assert tick["ok"] is True
        assert tick["response_contract_status"] == (
            "CAPACITY_PRESSURE_POLICY_FALLBACK"
        )
        assert tick["actions_applied"][0]["lever"] == "max_concurrent_trades"
        assert tick["actions_applied"][0]["new_value"] == 5
        assert tick["actions_applied"][0]["source"] == (
            "ai_operator.capacity_pressure_policy"
        )
        assert get_authority().control.get("max_concurrent_trades") == 5
    finally:
        _teardown()


def test_entry_pipeline_surfaces_durable_capacity_starvation(monkeypatch):
    from cas_forex import ai_control_authority as authority_module
    from cas_forex import live_candle_route_policy as live_policy

    class _Authority:
        def snapshot(self):
            return {
                "control_surface": {
                    "values": {
                        "max_concurrent_trades": 4,
                        "max_total_exposure_lots": 2.0,
                    },
                    "bounds": {
                        "max_concurrent_trades": {"min": 1, "max": 50},
                    },
                }
            }

    monkeypatch.setattr(authority_module, "get_authority", lambda: _Authority())
    monkeypatch.setattr(
        live_policy,
        "live_candle_route_runtime_status",
        lambda: {
            "status": "ENTRY_SCAN_RUNTIME_OBSERVED",
            # Persistent, cross-market capacity starvation must outrank one
            # current scan whose lanes happen to sit below the signal floor.
            "all_observed_lanes_below_directional_floor": True,
        },
    )
    pressure = _capacity_starved_context()["entry_opportunity_pipeline"][
        "capacity_pressure"
    ]

    result = ai_operator._entry_opportunity_pipeline_context(
        {
            "dispatch_loop": {
                "running": True,
                "execution_lane": "PAPER",
                "paper_learning_active": True,
                "last_collected_intent_count": 1,
                "last_entry_risk_operator_candidate_count": 0,
                "last_entry_capacity_pressure": pressure,
            },
            "entry_timeframe_scan": {"status": "SCAN_COMPLETED"},
            "entry_risk_feasibility": {
                "status": "ALL_CANDIDATES_BLOCKED_BEFORE_OPERATOR",
                "candidate_count": 1,
                "operator_candidate_count": 0,
                "candidates": [{"symbol": "USD/CHF", "reason": "position cap"}],
            },
            "live_candle_route_source": {"status": "ROUTE_READY"},
        }
    )

    assert result["status"] == "POSITION_CAPACITY_STARVATION"
    assert result["capacity_pressure"]["recommended_review_cap"] == 5
    assert result["entry_risk_preflight"]["candidates"][0]["symbol"] == "USD/CHF"
    assert "CAPACITY-PRESSURE DUTY" in ai_operator._OPERATOR_SYSTEM_PROMPT


def test_capacity_apply_revalidation_blocks_when_positions_cleared(
    tmp_path, monkeypatch
):
    op = _operator(tmp_path, monkeypatch, _StubProvider("{}"))
    from cas_forex.ai_control_authority import get_authority
    from cas_forex import mt5_live

    authority = get_authority()
    authority.control.adjust("max_concurrent_trades", 4)
    authority.control.adjust("max_total_exposure_lots", 2.0)
    monkeypatch.setattr(
        mt5_live,
        "get_mt5_account_snapshot",
        lambda force=False: {
            "connected": True,
            "snapshot_fresh": True,
            "snapshot_observed_at": "2026-07-14T17:30:00+00:00",
            "snapshot_age_seconds": 0.1,
            "open_position_count": 2,
            "positions": [{"lots": 0.01}, {"lots": 0.01}],
        },
    )
    try:
        result = ai_operator._capacity_policy_apply_revalidation(authority, 5)

        assert result["allowed"] is False
        assert result["status"] == "CAPACITY_PRESSURE_CLEARED_BEFORE_APPLY"
        assert result["fresh_open_position_count"] == 2
        assert authority.control.get("max_concurrent_trades") == 4
    finally:
        _teardown()


def test_operator_retries_incomplete_entry_starvation_hold_and_applies_valid_floor(
    tmp_path, monkeypatch
):
    weak_hold = {
        "observations": "No observed lane is above the directional floor.",
        "actions": [],
        "lessons": [],
        "summary": "No changes needed.",
    }
    repaired = {
        "observations": (
            "The strongest rejected lane scored 0.3895 against the current 0.5 "
            "floor across 68 paper-learning attempts."
        ),
        "actions": [
            {
                "type": "adjust_dial",
                "lever": "min_directional_confidence",
                "value": 0.3,
                "reason": (
                    "The read-only shadow PASS supports one bounded PAPER-learning "
                    "candidate while every fresh downstream gate remains active."
                ),
            }
        ],
        "lessons": [],
        "summary": "Lower the starved paper-learning floor once.",
    }

    class _SequenceProvider:
        def __init__(self):
            self.calls = 0
            self.prompts = []
            self.systems = []

        def generate(self, _prompt, _system=None, **_kwargs):
            self.prompts.append(_prompt)
            self.systems.append(_system)
            payload = weak_hold if self.calls == 0 else repaired
            self.calls += 1
            return {
                "ok": True,
                "text": json.dumps(payload),
                "provider": "local-fallback",
                "provider_label": "Local model (test)",
                "paid": False,
                "failover": False,
            }

    provider = _SequenceProvider()
    op = _operator(tmp_path, monkeypatch, provider)
    monkeypatch.setattr(ai_operator, "gather_context", lambda _config=None: _starved_entry_context())
    from cas_forex.ai_control_authority import get_authority

    get_authority().control.adjust("min_directional_confidence", 0.5)
    try:
        tick = op.tick().to_dict()

        assert tick["ok"] is True
        assert provider.calls == 2
        assert provider.prompts[1].startswith("FOCUSED ENTRY-OPPORTUNITY REPAIR")
        assert "trailing_stop_analysis" not in provider.prompts[1]
        assert "focused entry-opportunity decision specialist" in provider.systems[1]
        assert tick["response_contract_retry"] is True
        assert tick["response_contract_status"] == (
            "EVIDENCE_BASED_DIRECTIONAL_FLOOR_ADJUSTMENT"
        )
        assert tick["actions_applied"][0]["lever"] == "min_directional_confidence"
        assert tick["actions_applied"][0]["new_value"] == 0.3
        assert get_authority().control.get("min_directional_confidence") == 0.3
    finally:
        _teardown()


def test_operator_rejects_repeated_incomplete_entry_starvation_hold(
    tmp_path, monkeypatch
):
    weak_hold = {
        "observations": "No observed lane is above the directional floor.",
        "actions": [],
        "lessons": [],
        "summary": "No changes needed.",
    }

    class _RepeatingProvider:
        def __init__(self):
            self.calls = 0

        def generate(self, _prompt, _system=None, **_kwargs):
            self.calls += 1
            return {
                "ok": True,
                "text": json.dumps(weak_hold),
                "provider": "local-fallback",
                "provider_label": "Local model (test)",
                "paid": False,
                "failover": False,
            }

    provider = _RepeatingProvider()
    op = _operator(tmp_path, monkeypatch, provider)
    context = _starved_entry_context()
    runtime = context["entry_opportunity_pipeline"]["multi_timeframe_scan_runtime"]
    runtime["best_shadow_pass_lane"] = None
    runtime["shadow_pass_preview_count"] = 0
    runtime["shadow_edge_status_counts"] = {"NO_TRADE_NULL_FAILED": 68}
    monkeypatch.setattr(ai_operator, "gather_context", lambda _config=None: context)
    from cas_forex.ai_control_authority import get_authority

    get_authority().control.adjust("min_directional_confidence", 0.5)
    try:
        tick = op.tick().to_dict()

        assert tick["ok"] is False
        assert provider.calls == 2
        assert tick["response_contract_retry"] is True
        assert tick["response_contract_status"] == (
            "INCOMPLETE_ENTRY_OPPORTUNITY_DECISION"
        )
        assert tick["actions_applied"] == []
        assert "explicit STAND_DOWN" in tick["error"]
        assert get_authority().control.get("min_directional_confidence") == 0.5
    finally:
        _teardown()


def test_operator_uses_paper_shadow_pass_policy_after_two_invalid_model_answers(
    tmp_path, monkeypatch
):
    weak_hold = {
        "observations": "No observed lane is above the directional floor.",
        "actions": [],
        "lessons": [],
        "summary": "No changes needed.",
    }

    class _RepeatingProvider:
        def __init__(self):
            self.calls = 0

        def generate(self, _prompt, _system=None, **_kwargs):
            self.calls += 1
            return {
                "ok": True,
                "text": json.dumps(weak_hold),
                "provider": "local-fallback",
                "provider_label": "Local model (test)",
                "paid": False,
                "failover": False,
            }

    provider = _RepeatingProvider()
    op = _operator(tmp_path, monkeypatch, provider)
    monkeypatch.setattr(
        ai_operator,
        "gather_context",
        lambda _config=None: _starved_entry_context(),
    )
    from cas_forex.ai_control_authority import get_authority

    get_authority().control.adjust("min_directional_confidence", 0.5)
    try:
        tick = op.tick().to_dict()

        assert tick["ok"] is True
        assert provider.calls == 2
        assert tick["response_contract_retry"] is True
        assert tick["response_contract_status"] == (
            "PAPER_SHADOW_PASS_POLICY_FALLBACK"
        )
        assert tick["actions_applied"][0]["lever"] == "min_directional_confidence"
        assert tick["actions_applied"][0]["new_value"] == 0.32
        assert tick["actions_applied"][0]["source"] == (
            "ai_operator.paper_shadow_pass_policy"
        )
        assert get_authority().control.get("min_directional_confidence") == 0.32
    finally:
        _teardown()


def test_entry_opportunity_contract_rejects_false_static_simulator_block():
    context = _starved_entry_context()
    pipeline = context["entry_opportunity_pipeline"]
    pipeline["multi_timeframe_scan_runtime"]["best_shadow_pass_lane"] = None
    pipeline["multi_timeframe_scan_runtime"]["shadow_pass_preview_count"] = 0
    decision = {
        "observations": (
            "STAND_DOWN: strongest score 0.3895 remains below current floor 0.5; "
            "the static simulation fallback blocks broker learning and independent "
            "outcome evidence is insufficient."
        ),
        "actions": [],
        "lessons": [],
        "summary": "Retain the floor because the simulator fallback blocks execution.",
    }

    result = ai_operator._entry_opportunity_decision_contract(decision, context)

    assert result["valid"] is False
    assert result["status"] == "INCOMPLETE_ENTRY_OPPORTUNITY_DECISION"
    assert "conflicts with active MT5Bridge" in result["error"]


def test_operator_cannot_touch_non_dial_levers(tmp_path, monkeypatch):
    decision = {
        "actions": [
            {"type": "adjust_dial", "lever": "live_mode", "value": True, "reason": "go live"},
            {"type": "adjust_dial", "lever": "owner_enable_live_trading", "value": True, "reason": "nope"},
            {"type": "wire_money", "amount": 5000, "reason": "withdraw"},
        ],
        "summary": "attempted forbidden actions",
    }
    op = _operator(tmp_path, monkeypatch, _StubProvider(json.dumps(decision)))
    try:
        tick = op.tick()
        d = tick.to_dict()
        assert d["actions_applied"] == []
        assert len(d["actions_skipped"]) == 3
        whys = " ".join(s["why"] for s in d["actions_skipped"])
        assert "not an owner-fenced dial" in whys
        assert "unsupported action type" in whys
    finally:
        _teardown()


def test_operator_clamps_to_owner_bounds(tmp_path, monkeypatch):
    decision = {
        "actions": [{"type": "adjust_dial", "lever": "edge_threshold", "value": 0.99, "reason": "max out"}],
        "summary": "clamp test",
    }
    op = _operator(tmp_path, monkeypatch, _StubProvider(json.dumps(decision)))
    try:
        tick = op.tick()
        applied = tick.to_dict()["actions_applied"][0]
        assert applied["clamped"] is True
        assert float(applied["new_value"]) <= 0.95  # owner max
    finally:
        _teardown()


def test_unparseable_reply_makes_no_change(tmp_path, monkeypatch):
    op = _operator(tmp_path, monkeypatch, _StubProvider("I think you should sell everything!!!"))
    try:
        tick = op.tick()
        d = tick.to_dict()
        assert d["ok"] is False
        assert d["actions_applied"] == []
        assert "parseable" in (d["error"] or "")
    finally:
        _teardown()


def test_no_model_available_is_safe(tmp_path, monkeypatch):
    op = _operator(tmp_path, monkeypatch, _StubProvider("", ok=False))
    try:
        tick = op.tick()
        d = tick.to_dict()
        assert d["ok"] is False
        assert d["actions_applied"] == []
        assert "running" in d["summary"].lower()  # "trading loop keeps running"
    finally:
        _teardown()


def test_empty_actions_list_is_a_valid_hold(tmp_path, monkeypatch):
    decision = {"observations": "all healthy", "actions": [], "summary": "no change"}
    op = _operator(tmp_path, monkeypatch, _StubProvider(json.dumps(decision)))
    try:
        tick = op.tick()
        d = tick.to_dict()
        assert d["ok"] is True
        assert d["actions_applied"] == []
        assert d["summary"] == "no change"
    finally:
        _teardown()


def test_recent_actions_are_logged_and_readable(tmp_path, monkeypatch):
    decision = {"actions": [{"type": "adjust_dial", "lever": "max_concurrent_trades", "value": 10, "reason": "cap"}], "summary": "cap"}
    op = _operator(tmp_path, monkeypatch, _StubProvider(json.dumps(decision)))
    try:
        op.tick()
        recent = op.recent_actions()
        assert len(recent) == 1
        assert recent[0]["summary"] == "cap"
    finally:
        _teardown()


def test_recent_actions_supersede_legacy_advisory_only_claim(tmp_path):
    path = tmp_path / "operator-actions.jsonl"
    path.write_text(
        json.dumps(
            {
                "report_kind": ai_operator.REPORT_KIND,
                "summary": "legacy row",
                "claim_boundary": "The AI operator never places trades or moves money.",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    recent = ai_operator.AIOperator(actions_path=path).recent_actions()

    assert recent[0]["claim_boundary"] == ai_operator.CLAIM_BOUNDARY
    assert recent[0]["legacy_claim_boundary_superseded"] is True
    assert "never places trades" not in recent[0]["claim_boundary"]


def test_tool_manifest_lists_autonomous_paths_and_hard_blocks(tmp_path):
    manifest = ai_operator.TOOL_MANIFEST
    assert "M1/M5 are micro-scalp" in manifest["dials_you_can_set"]["timeframes"]
    assert "set_take_profit" in manifest["autonomous_authority_when_armed"]["trading"]
    assert "withdrawal" in manifest["autonomous_authority_when_armed"]["money_movement"]
    assert manifest["autonomous_authority_when_armed"]["human_in_loop_per_order_required"] is False
    assert manifest["mandatory_paths"]["broker_orders"] == [
        "order_dispatch.py",
        "execution_guard.py",
        "broker_bridge",
    ]
    assert "stale_broker_truth" in manifest["hard_blocks"]
    assert "missing_receipt_for_money_movement" in manifest["hard_blocks"]
    assert "stored_pre_trade_risk_used_without_broker_contract_recalculation" in manifest["hard_blocks"]
    assert "per_lot_dollars_compared_across_instruments_as_edge" in manifest["hard_blocks"]
    assert "incomplete_admission_risk_promotes_behavior" in manifest["hard_blocks"]


class _CapturingProvider(_StubProvider):
    """Stub that also records every prompt it was asked to answer."""

    def __init__(self, text, **kw):
        super().__init__(text, **kw)
        self.prompts = []
        self.systems = []

    def generate(self, prompt, system=None):
        self.prompts.append(prompt)
        self.systems.append(system)
        return super().generate(prompt, system)


def test_next_tick_sees_its_own_prior_dial_changes(tmp_path, monkeypatch):
    """Self-continuity (2026-07-03): a tick re-added a market the prior tick
    had just cut, calling it 'previously unused'. The next tick's prompt must
    carry the operator's own recent applied changes ahead of inherited lessons
    inside the structured evidence packet."""
    decision = {
        "observations": "cut the chronic loser",
        "actions": [{"type": "adjust_dial", "lever": "max_positions_per_symbol", "value": 2, "reason": "stop blind stacking"}],
        "summary": "tightened per-symbol stacking",
    }
    provider = _CapturingProvider(json.dumps(decision))
    op = _operator(tmp_path, monkeypatch, provider)
    try:
        first = op.tick()
        assert first.ok is True
        # First tick: no prior applied actions -> no self-history block.
        assert "your_recent_dial_changes" not in provider.prompts[0]

        second = op.tick()
        assert second.ok is True
        follow_up = provider.prompts[1]
        assert "your_recent_dial_changes" in follow_up
        packet = json.loads(follow_up.split("\n\n", 1)[1])
        assert "max_positions_per_symbol" in json.dumps(packet["your_recent_dial_changes"])
        packet_keys = list(packet)
        assert packet_keys.index("your_recent_dial_changes") < packet_keys.index("inherited_lessons")
    finally:
        _teardown()


def test_operator_prompt_includes_compact_spec_constitution(tmp_path, monkeypatch):
    import cas_forex.spec_context as spec_context

    decision = {"observations": "hold", "actions": [], "summary": "hold"}
    provider = _CapturingProvider(json.dumps(decision))
    op = _operator(tmp_path, monkeypatch, provider)
    monkeypatch.setattr(
        spec_context,
        "operator_constitution",
        lambda: "CAS Forex Operator Constitution\nNever call local desktop evidence real phone proof.",
    )
    try:
        tick = op.tick()
        assert tick.ok is True
        assert "operator_constitution" in provider.prompts[0]
        assert "CAS Forex Operator Constitution" in provider.prompts[0]
        assert "Never call local desktop evidence real phone proof." in provider.prompts[0]
    finally:
        _teardown()


def test_operator_tick_records_decision_grade_context_delivery(tmp_path, monkeypatch):
    from cas_forex.ai_operator_context import CRITICAL_SECTIONS

    context = {key: {} for key in CRITICAL_SECTIONS}
    context["operator_constitution"] = (
        "- Version: test\n"
        "- Authority boundary: guarded autonomy.\n"
        + ("STATIC " * 20_000)
    )
    context["profit_and_balance"] = {
        "objective": "TICK_PROFIT_SENTINEL",
        "balance_growth_net_pnl_usd": 125.0,
    }
    context["learning_outcomes"] = {"marker": "TICK_LEARNING_SENTINEL"}
    context["inherited_lessons"] = [
        {"category": "edge", "lesson": "TICK_LESSON_SENTINEL", "reinforced": 2}
    ]
    monkeypatch.setattr(ai_operator, "gather_context", lambda _config=None: context)

    provider = _CapturingProvider(
        json.dumps({"observations": "packet complete", "actions": [], "summary": "hold"})
    )
    op = _operator(tmp_path, monkeypatch, provider)
    try:
        tick = op.tick()
        delivery = tick.to_dict()["context_delivery"]
        assert delivery["status"] == "DECISION_GRADE_CONTEXT"
        assert delivery["decision_grade"] is True
        assert delivery["blind_character_slice_used"] is False
        assert delivery["critical_sections_missing"] == []
        assert "TICK_LEARNING_SENTINEL" in provider.prompts[0]
        assert "TICK_LESSON_SENTINEL" in provider.prompts[0]
    finally:
        _teardown()


def test_operator_prompt_includes_public_launch_gate_context(tmp_path, monkeypatch):
    import cas_forex.public_launch_gate as public_launch_gate

    decision = {"observations": "hold", "actions": [], "summary": "hold"}
    provider = _CapturingProvider(json.dumps(decision))
    op = _operator(tmp_path, monkeypatch, provider)
    monkeypatch.setattr(
        public_launch_gate,
        "build_public_launch_gate",
        lambda: {
            "report_kind": "cas_forex_public_launch_gate",
            "status": "ATTENTION",
            "launch_gate_status": "BLOCK_PUBLIC_LAUNCH",
            "public_launch_status": "BLOCKED",
            "live_money_production_status": "BLOCKED",
            "pass_count": 4,
            "block_count": 4,
            "hard_blockers": ["Counsel legal review is missing."],
            "gates": [],
            "release_policy": "Treat BLOCK_PUBLIC_LAUNCH as a hard stop.",
        },
    )
    try:
        tick = op.tick()
        assert tick.ok is True
        prompt = provider.prompts[0]
        assert "public_launch_gate" in prompt
        assert "BLOCK_PUBLIC_LAUNCH" in prompt
        assert "Counsel legal review is missing." in prompt
    finally:
        _teardown()


def test_gather_chat_context_includes_emergency_status(monkeypatch):
    import api.data as api_data
    from api.routes import strategy_comparison as strategy_comparison_route
    import cas_forex.broker_truth_monitor as broker_truth_monitor
    import cas_forex.critical_notifications as critical_notifications
    import cas_forex.emergency_controls as emergency_controls
    import cas_forex.ai_hedge_management as ai_hedge_management
    import cas_forex.ai_hedge_management_execution as ai_hedge_management_execution
    import cas_forex.ai_hedge_supervision as ai_hedge_supervision
    import cas_forex.legal_review_readiness as legal_review_readiness
    import cas_forex.operational_readiness as operational_readiness
    import cas_forex.professional_claims as professional_claims
    import cas_forex.professional_readiness_matrix as professional_readiness_matrix

    monkeypatch.setattr(
        api_data,
        "auto_halt_status",
        lambda persist=False: {
            "report_kind": "cas_forex_auto_halt",
            "status": "AUTO_HALT_ACTIVE",
            "halt_active": True,
            "force_paper_mode": True,
            "triggered_checks": ["manual_emergency_stop"],
            "active_state": {"reasons": ["MANUAL_EMERGENCY_STOP"]},
            "next_action": "Keep live trading blocked until owner review.",
        },
    )
    monkeypatch.setattr(
        broker_truth_monitor,
        "monitor_fast_status",
        lambda: {
            "report_kind": "cas_forex_broker_truth_monitor_status_fast",
            "status": "RUNNING",
            "running": True,
            "monitor_status": "BROKER_TRUTH_RECONCILIATION_FAILED",
            "ready_for_live": False,
            "latest_report": {
                "overall_status": "RECONCILIATION_FAILED",
                "mt5_connected": True,
                "mt5_is_demo": False,
                "mt5_open_position_count": 2,
                "auto_halt_latched_from_monitor": True,
                "monitor_auto_halt_reason_ids": [
                    "live_position_stop_loss_protection",
                    "terminal_position_reconciliation",
                ],
                "position_protection_status": "UNPROTECTED_POSITIONS",
                "position_protection_open_position_count": 2,
                "position_protection_unprotected_position_count": 2,
                "position_protection_requires_owner_attention": True,
                "position_protection_detail": "2 broker-visible live positions have no stop-loss protection.",
                "position_protection_unprotected_preview": [
                    {"ticket": 123, "symbol": "NAS100", "side": "LONG"},
                ],
                "terminal_unmatched_open_position_count": 1,
                "terminal_pending_receipt_count": 0,
                "next_action": "Keep paper force active until broker truth clears.",
            },
        },
    )
    monkeypatch.setattr(
        critical_notifications,
        "build_critical_notification_delivery_readiness",
        lambda limit=5: {
            "report_kind": "cas_forex_critical_notification_delivery_readiness",
            "status": "DELIVERY_CONFIRMED",
            "offscreen_delivery_status": "DELIVERY_CONFIRMED",
            "subscription_count": 1,
            "recent_dispatch_success_count": 1,
            "recent_dispatch_attempt_count": 1,
            "owner_setup_required_for_offscreen_alerts": False,
            "blockers": [],
            "next_action": "Critical notification delivery has a recent successful webhook attempt.",
            "local_in_app_alert_channel": {
                "status": "ACTIVE",
                "visible_warning_or_alert_count": 1,
            },
        },
    )
    monkeypatch.setattr(
        critical_notifications,
        "build_critical_notification_report",
        lambda limit=5: {
            "report_kind": "cas_forex_critical_notification_audit",
            "rows": [
                {
                    "at": "2026-07-09T00:00:00+00:00",
                    "event": {
                        "event_kind": "UNPROTECTED_POSITION",
                        "title": "Unprotected position",
                        "body": "One open position has no stop loss.",
                        "severity": "alert",
                    },
                }
            ],
        },
    )
    monkeypatch.setattr(
        emergency_controls,
        "build_emergency_controls_report",
        lambda: {
            "report_kind": "cas_forex_emergency_controls",
            "status": "OK",
            "automation_stop_ok": True,
            "broker_exposure_gap": False,
            "attention_items": [],
            "automation_stop_scope": "Stops new automated dispatch only.",
            "recommended_terminal_actions": ["Keep MT5 visible."],
            "controls": [
                {"key": "broker_close_all_positions", "status": "OK"},
            ],
        },
    )
    monkeypatch.setattr(
        ai_hedge_supervision,
        "build_ai_hedge_supervision_report",
        lambda: {
            "report_kind": "cas_forex_ai_hedge_supervision",
            "status": "ACTIVE_RECOMMENDATIONS",
            "movement_stream_id": "movement-1",
            "price_source_status": "PROVIDER_ACTIVE",
            "price_source_label": "PROVIDER",
            "static_simulation_active": False,
            "position_count": 1,
            "action_recommendation_count": 1,
            "high_urgency_count": 0,
            "broker_bound_action_authorized": False,
            "orders_placed": False,
            "money_moved": False,
            "next_action": "Review the top AI Hedge recommendation, then route any broker-bound action through the protected dispatch path.",
            "recommendations": [
                {
                    "intent": "move_stop_to_breakeven",
                    "scope": "position",
                    "symbol": "US30",
                    "urgency": "MEDIUM",
                    "reason": "Position is up 1.20R and stop is not at breakeven.",
                    "gate_path": "AI Hedge -> order_dispatch.py -> execution_guard.py",
                }
            ],
            "positions": [
                {
                    "symbol": "US30",
                    "side": "LONG",
                    "r_multiple": 1.2,
                    "floating_pnl_usd": 12.0,
                    "price_source": "provider_snapshot:MT5TerminalMarketDataConnector",
                    "price_stale": False,
                    "position_source_label": "PAPER_SIM_MT5_PRICED",
                }
            ],
            "claim_boundary": "AI Hedge supervision is read-only.",
        },
    )
    monkeypatch.setattr(
        ai_hedge_management,
        "build_ai_hedge_management_handoff",
        lambda: {
            "report_kind": "cas_forex_ai_hedge_management_handoff",
            "status": "READY_FOR_GUARDED_EXECUTION",
            "supervision_status": "ACTIVE_RECOMMENDATIONS",
            "price_source_status": "PROVIDER_ACTIVE",
            "management_action_count": 1,
            "blocked_action_count": 0,
            "ready_for_owner_review": False,
            "ready_for_guarded_execution": True,
            "dry_run_only": False,
            "broker_bound_action_authorized": False,
            "broker_touched": False,
            "orders_placed": False,
            "money_moved": False,
            "next_action": "Drafted management action is ready for guarded execution.",
            "management_actions": [
                {
                    "intent": "move_stop_to_breakeven",
                    "symbol": "US30",
                    "broker_method": "modify_position",
                    "broker_ticket": 123456,
                    "volume": None,
                    "stop_loss": 100.0,
                    "take_profit": 140.0,
                    "risk_effect": "principal_lock",
                    "requires_owner_confirmation": False,
                    "requires_fresh_broker_truth": True,
                    "requires_execution_guard": True,
                    "reason": "Position is up 1.20R and stop is not at breakeven.",
                }
            ],
            "blocked_actions": [],
            "claim_boundary": "AI Hedge management handoff prepares guarded execution drafts.",
        },
    )
    monkeypatch.setattr(
        ai_hedge_management_execution,
        "latest_ai_hedge_management_execution",
        lambda: {
            "report_kind": "cas_forex_ai_hedge_management_execution_latest",
            "status": "EXECUTED_RECONCILED",
            "broker_touched": True,
            "latest": {
                "status": "EXECUTED_RECONCILED",
                "audit_id": "abc123",
                "generated_at_iso": "2026-07-09T12:00:00+00:00",
                "selected_action_id": "ai-hedge-management:pos-1:move_stop_to_breakeven",
                "selected_action": {
                    "broker_method": "modify_position",
                    "symbol": "US30",
                    "broker_ticket": 123456,
                    "stop_loss": 100.0,
                    "volume": None,
                },
                "broker_result": {"status": "EXECUTED"},
                "terminal_receipt_status": "RECONCILED",
                "terminal_receipt": {"status": "RECONCILED"},
                "post_execution_refresh_status": "REFRESH_RAN",
                "post_execution_refresh": {
                    "status": "REFRESH_RAN",
                    "error_count": 0,
                    "refreshed_packets": {
                        "account_reconciliation": {},
                        "live_telemetry": {},
                    },
                },
                "next_action": "Refresh broker truth.",
            },
            "claim_boundary": "AI Hedge management execution is confirmed only.",
        },
    )
    monkeypatch.setattr(
        strategy_comparison_route,
        "_LOADER",
        lambda: {
            "fury_candidates": None,
            "strategy_leads": [
                {
                    "lead_id": "thin-lead",
                    "profit_factor": 1.8,
                    "max_drawdown_pct": 6.0,
                    "total_trades": 40,
                }
            ],
            "strategy_dev_queue_items": None,
        },
    )
    monkeypatch.setattr(
        operational_readiness,
        "build_operational_readiness_report",
        lambda: {
            "report_kind": "cas_forex_operational_readiness",
            "status": "ATTENTION",
            "attention_count": 1,
            "attention_items": ["Configure external uptime monitoring, error tracking, and off-screen alert destinations before hosted production."],
            "runbook_path": "docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md",
            "backup_inventory": {
                "snapshot_count": 0,
                "latest_snapshot": None,
            },
            "external_monitoring": {
                "status": "ATTENTION",
                "attention_count": 2,
                "top_attention_items": [
                    "Configure external uptime monitoring.",
                    "Configure CAS_FOREX_ERROR_TRACKING_DSN or SENTRY_DSN before hosted production.",
                ],
                "next_action": "Configure external uptime monitoring, error tracking, and off-screen alert destinations before hosted production.",
                "deployment_handoff": {
                    "status": "ACTION_REQUIRED",
                    "owner_ui_path": "?page=settings",
                    "health_endpoints": ["/health", "/api/forex/stack-health/check"],
                    "verification_commands": ["curl -fsS https://your-cas-forex-host/health"],
                    "setup_steps": ["Deploy CAS Forex behind HTTPS with owner authentication enabled."],
                    "package_documents": [
                        {"path": "docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md", "present": True},
                        {"path": "docs/operations/CAS_FOREX_EXTERNAL_MONITORING_ENV_TEMPLATE.env.example", "present": True},
                        {"path": "cas_forex/external_monitoring_control.py", "present": True},
                    ],
                },
                "checks": [
                    {"key": "external_uptime_monitor", "status": "MISSING"},
                    {"key": "error_tracking_dsn", "status": "MISSING"},
                    {"key": "offscreen_alert_destination", "status": "ATTENTION"},
                    {"key": "external_monitoring_runbook", "status": "OK"},
                ],
            },
        },
    )
    monkeypatch.setattr(
        legal_review_readiness,
        "build_legal_review_readiness",
        lambda: {
            "report_kind": "cas_forex_legal_review_readiness",
            "status": "ATTENTION",
            "launch_legal_status": "BLOCK_PUBLIC_LAUNCH",
            "counsel_review_accepted": False,
            "attention_count": 1,
            "counsel_review_record_path": "docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md",
            "top_attention_items": ["Counsel review record is absent or incomplete; drafts are not public-launch approval."],
            "next_action": "Complete qualified legal/compliance review and add an accepted counsel review record before public launch.",
            "counsel_review_handoff": {
                "status": "COUNSEL_REVIEW_REQUIRED",
                "launch_legal_status": "BLOCK_PUBLIC_LAUNCH",
                "attention_keys": ["counsel_review_record"],
                "package_documents": [
                    {"path": "docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md", "present": True},
                    {"path": "docs/legal/CAS_FOREX_TERMS_OF_SERVICE_DRAFT.md", "present": True},
                    {"path": "docs/legal/CAS_FOREX_PRIVACY_POLICY_DRAFT.md", "present": True},
                    {"path": "docs/legal/CAS_FOREX_LEGAL_REVIEW_CHECKLIST.md", "present": True},
                    {"path": "docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md", "present": False},
                ],
                "required_record_fields": [
                    "counsel_review_status: accepted",
                    "reviewed_by",
                    "review_date",
                    "scope",
                    "qualified_counsel_confirmed: yes",
                    "review_artifact_path",
                    "review_artifact_sha256",
                ],
                "setup_steps": [
                    "Give qualified counsel the draft disclosure, Terms, Privacy Policy, legal review checklist, and current product/spec evidence."
                ],
                "record_template": [
                    "counsel_review_status: accepted",
                    "reviewed_by: <qualified counsel name or firm>",
                ],
            },
            "checks": [
                {"key": "draft_disclosure_package", "status": "OK"},
                {"key": "legal_review_checklist", "status": "OK"},
                {"key": "counsel_review_record", "status": "MISSING"},
                {"key": "public_launch_legal_status", "status": "ATTENTION"},
            ],
        },
    )
    monkeypatch.setattr(
        professional_claims,
        "build_professional_claims_report",
        lambda: {
            "report_kind": "cas_forex_professional_claims",
            "status": "ATTENTION",
            "risky_claim_count": 1,
            "boundary_reference_count": 2,
            "disclosure_document": {"present": True, "path": "docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md"},
            "missing_disclosures": [
                {"key": "not_financial_advice", "label": "No Financial Advice", "status": "MISSING_DRAFT_COPY"}
            ],
            "claim_hits": [
                {
                    "path": "ui/src/pages/FakePage.tsx",
                    "line": 12,
                    "claim_type": "guaranteed_profit",
                    "label": "Guaranteed profit/return claim",
                    "severity": "needs_review",
                    "excerpt": "Guaranteed profits every day.",
                }
            ],
        },
    )
    monkeypatch.setattr(
        professional_readiness_matrix,
        "build_professional_readiness_matrix",
        lambda: {
            "report_kind": "cas_forex_professional_readiness_matrix",
            "status": "ATTENTION",
            "item_count": 37,
            "ok_count": 34,
            "partial_count": 3,
            "gap_count": 0,
            "satisfied_count": 34,
            "internal_partial_count": 0,
            "external_blocked_count": 3,
            "missing_count": 0,
            "top_attention_items": [
                "Obtain legal/compliance review before public launch or advising others for compensation.",
                "Obtain counsel-reviewed final Terms, Privacy, risk, automated trading, AI, and broker disclosures before public launch.",
            ],
            "rows": [
                {
                    "item_number": 13,
                    "key": "compliance_awareness",
                    "category": "Legal/Compliance",
                    "status": "PARTIAL",
                    "completion_state": "EXTERNAL_BLOCKED",
                    "blocked_by_external_dependency": True,
                    "external_dependency": "Qualified legal/compliance review and accepted counsel record.",
                    "remaining_gap": "External legal counsel review is not a code artifact.",
                    "next_action": "Obtain legal/compliance review before public launch or advising others for compensation.",
                },
                {
                    "item_number": 32,
                    "key": "legal_disclosures",
                    "category": "Legal/Compliance",
                    "status": "PARTIAL",
                    "completion_state": "EXTERNAL_BLOCKED",
                    "blocked_by_external_dependency": True,
                    "external_dependency": "Counsel-reviewed final Terms, Privacy, risk, automated trading, AI, and broker disclosures.",
                    "remaining_gap": "Counsel-approved final policy set is still needed.",
                    "next_action": "Obtain counsel-reviewed final Terms, Privacy, risk, automated trading, AI, and broker disclosures before public launch.",
                },
                {
                    "item_number": 34,
                    "key": "production_operations",
                    "category": "Production Operations",
                    "status": "PARTIAL",
                    "completion_state": "EXTERNAL_BLOCKED",
                    "blocked_by_external_dependency": True,
                    "external_dependency": "Hosted uptime monitor and error-tracking DSN configured in the deployment environment.",
                    "remaining_gap": "Hosted uptime/error tracking destinations still need deployment config.",
                    "next_action": "Add external uptime/error monitoring before public cloud deployment.",
                },
            ],
        },
    )

    context = ai_operator.gather_chat_context()

    assert context["auto_halt"]["status"] == "AUTO_HALT_ACTIVE"
    risk_caps = context["psychology_guard"]["risk_caps"]
    assert risk_caps["precedence"] == "explicit owner risk-control override > AI dial > static config"
    assert "effective_max_open_position_count" in risk_caps
    assert "effective_max_total_exposure_lots" in risk_caps
    assert "effective_max_risk_per_trade_pct" in risk_caps
    assert "override_persistence_status" in risk_caps
    assert context["ai_hedge_intelligence_layer"]["status"] == "SPECIFIED_GOVERNED_LAYER"
    assert "move_stop_to_breakeven" in context["ai_hedge_intelligence_layer"]["allowed_trade_intents"]
    assert context["ai_hedge_supervision"]["status"] == "ACTIVE_RECOMMENDATIONS"
    assert context["ai_hedge_supervision"]["recommendations"][0]["intent"] == "move_stop_to_breakeven"
    assert context["ai_hedge_supervision"]["orders_placed"] is False
    assert context["ai_hedge_management_handoff"]["status"] == "READY_FOR_GUARDED_EXECUTION"
    assert context["ai_hedge_management_handoff"]["ready_for_guarded_execution"] is True
    assert context["ai_hedge_management_handoff"]["management_actions"][0]["broker_method"] == "modify_position"
    assert context["ai_hedge_management_handoff"]["broker_touched"] is False
    assert context["ai_hedge_management_execution"]["latest_status"] == "EXECUTED_RECONCILED"
    assert context["ai_hedge_management_execution"]["latest_terminal_receipt_status"] == "RECONCILED"
    assert context["ai_hedge_management_execution"]["latest_post_execution_refresh_status"] == "REFRESH_RAN"
    assert context["ai_hedge_management_execution"]["latest_post_execution_refresh_error_count"] == 0
    assert context["ai_hedge_management_execution"]["latest_post_execution_refresh_packets"] == [
        "account_reconciliation",
        "live_telemetry",
    ]
    assert context["ai_hedge_management_execution"]["latest_method"] == "modify_position"
    assert context["ai_hedge_management_execution"]["broker_touched"] is True
    assert context["auto_halt"]["halt_active"] is True
    assert context["broker_truth_monitor"]["monitor_status"] == "BROKER_TRUTH_RECONCILIATION_FAILED"
    assert context["broker_truth_monitor"]["ready_for_live"] is False
    assert context["broker_truth_monitor"]["auto_halt_latched_from_monitor"] is True
    assert context["broker_truth_monitor"]["monitor_auto_halt_reason_labels"] == [
        "Stop-Loss Protection",
        "Terminal Reconciliation",
    ]
    assert context["broker_truth_monitor"]["position_protection_label"] == "UNPROTECTED POSITIONS"
    assert context["broker_truth_monitor"]["position_protection_unprotected_position_count"] == 2
    assert context["broker_truth_monitor"]["position_protection_detail"] == "2 broker-visible live positions have no stop-loss protection."
    assert context["critical_notifications"]["delivery_status"] == "DELIVERY_CONFIRMED"
    assert context["critical_notifications"]["latest_event_kind"] == "UNPROTECTED_POSITION"
    assert context["performance_discipline"]["status"] == "ATTENTION"
    assert context["performance_discipline"]["records"][0]["strategy_id"] == "thin-lead"
    assert "cost_model" in context["performance_discipline"]["records"][0]["critical_missing"]
    assert context["operational_readiness"]["status"] == "ATTENTION"
    assert context["operational_readiness"]["external_monitoring"]["status"] == "ATTENTION"
    assert context["operational_readiness"]["external_monitoring"]["deployment_handoff"]["status"] == "ACTION_REQUIRED"
    assert context["operational_readiness"]["external_monitoring"]["deployment_handoff"]["verification_commands"][0] == "curl -fsS https://your-cas-forex-host/health"
    assert context["operational_readiness"]["external_monitoring"]["deployment_handoff"]["package_documents"][0] == {
        "path": "docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md",
        "present": True,
    }
    assert context["legal_review"]["launch_legal_status"] == "BLOCK_PUBLIC_LAUNCH"
    assert context["legal_review"]["counsel_review_handoff"]["status"] == "COUNSEL_REVIEW_REQUIRED"
    assert context["legal_review"]["counsel_review_handoff"]["package_documents"][-1] == {
        "path": "docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md",
        "present": False,
    }
    assert context["legal_review"]["counsel_review_handoff"]["required_record_fields"][0] == "counsel_review_status: accepted"
    assert context["professional_claims"]["risky_claim_count"] == 1
    assert context["professional_claims"]["missing_disclosures"][0]["key"] == "not_financial_advice"
    assert context["professional_readiness"]["status"] == "ATTENTION"
    assert context["professional_readiness"]["partial_count"] == 3
    assert context["professional_readiness"]["external_blocked_count"] == 3
    assert context["professional_readiness"]["missing_count"] == 0
    assert context["professional_readiness"]["remaining_rows"][0]["key"] == "compliance_awareness"
    assert context["professional_readiness"]["remaining_rows"][0]["completion_state"] == "EXTERNAL_BLOCKED"
    assert context["professional_readiness"]["remaining_rows"][0]["external_dependency"] == "Qualified legal/compliance review and accepted counsel record."
    assert context["emergency_controls"]["status"] == "OK"
    assert context["emergency_controls"]["automation_stop_ok"] is True


def test_chat_proposes_a_command_with_preview(tmp_path, monkeypatch):
    """The operator can PROPOSE an owner command in chat; the reply carries the
    broker preview and strips the raw command block from the display text.
    Nothing is executed (proposing != executing)."""
    reply_text = (
        "Sure — I'll raise the edge threshold to 0.7 so we only take stronger setups.\n"
        "```command\n{\"command\": \"set_ai_dial\", \"params\": {\"lever\": \"edge_threshold\", \"value\": 0.7}}\n```"
    )
    op = _operator(tmp_path, monkeypatch, _StubProvider(reply_text))
    try:
        res = op.chat("raise the edge threshold to 0.7")
        assert res["ok"] is True
        assert res["proposed_command"]["command"] == "set_ai_dial"
        assert res["proposed_command"]["params"]["lever"] == "edge_threshold"
        # The preview is attached and ready, with the confirm phrase.
        assert res["command_preview"]["ready"] is True
        assert res["command_preview"]["confirm_phrase"] == "CONFIRM"
        # The raw ```command block is stripped from the shown reply.
        assert "```" not in res["reply"]
        assert "edge threshold" in res["reply"].lower()
        # Chat did NOT change the dial (proposing != executing).
        from cas_forex.ai_control_authority import get_authority
        assert float(get_authority().control.get("edge_threshold")) != 0.7
    finally:
        _teardown()


def test_chat_plain_question_proposes_no_command(tmp_path, monkeypatch):
    op = _operator(tmp_path, monkeypatch, _StubProvider("The balance grew on paper but there's no proven edge yet."))
    try:
        res = op.chat("how are we doing?")
        assert res["ok"] is True
        assert res["proposed_command"] is None
        assert res["command_preview"] is None
    finally:
        _teardown()


def test_trade_stall_question_uses_model_with_grounded_context(tmp_path, monkeypatch):
    provider = _CapturingProvider("No fresh eligible candidate has formed, so the Operator is standing down.")
    op = _operator(tmp_path, monkeypatch, provider)
    try:
        res = op.chat("why hasn't the Operator made a trade in 3 days?")
        assert res["ok"] is True
        assert res["model_ok"] is True
        assert res["fallback"] is False
        assert res["chat_path_status"] == "MODEL_PRIMARY"
        assert len(provider.prompts) == 1
        assert "OWNER'S MESSAGE" in provider.prompts[0]
        assert "why hasn't the Operator made a trade" in provider.prompts[0]
        assert "local Operator fallback" not in res["reply"]
    finally:
        _teardown()


def test_entry_opportunity_context_exposes_pre_operator_starvation(monkeypatch):
    import cas_forex.ai_control_authority as authority_module
    import cas_forex.live_candle_route_policy as live_policy

    class _Authority:
        @staticmethod
        def snapshot():
            return {
                "control_surface": {
                    "values": {
                        "min_directional_confidence": 0.5,
                        "edge_threshold": 0.65,
                        "paper_learning_trades": 1,
                        "timeframes": ["M1", "M5", "M15", "H1"],
                        "symbols": ["NAS100"],
                    },
                    "bounds": {
                        "min_directional_confidence": {"min": 0.05, "max": 0.9}
                    },
                }
            }

    monkeypatch.setattr(authority_module, "get_authority", lambda: _Authority())
    monkeypatch.setattr(
        live_policy,
        "live_candle_route_runtime_status",
        lambda: {
            "status": "ENTRY_SCAN_RUNTIME_OBSERVED",
            "attempt_count": 68,
            "all_observed_lanes_below_directional_floor": True,
            "strongest_rejected_lane": {
                "symbol": "NAS100",
                "timeframe": "M5",
                "directional_score": 0.31,
                "directional_floor": 0.5,
            },
            "broker_execution_touched": False,
            "orders_placed": False,
        },
    )

    context = ai_operator._entry_opportunity_pipeline_context(
        {
            "dispatch_loop": {
                "running": True,
                "execution_lane": "PAPER",
                "paper_learning_active": True,
                "last_eligible_entry_symbols": ["NAS100"],
                "last_collected_intent_count": 0,
                "last_entry_risk_operator_candidate_count": 0,
            },
            "entry_timeframe_scan": {
                "status": "SCAN_THROTTLED_CACHE",
                "fresh_market_scan_performed": False,
                "cache_remaining_seconds": 20.0,
            },
            "entry_risk_feasibility": {
                "status": "NO_OVERSEER_APPROVED_CANDIDATES"
            },
            "live_candle_route_source": {"status": "NO_ROUTE"},
        }
    )

    assert context["status"] == "ALL_OBSERVED_LANES_BELOW_DIRECTIONAL_FLOOR"
    assert context["current_scheduler_invocation"]["status"] == (
        "SCAN_THROTTLED_CACHE"
    )
    assert context["operator_adjustable_candidate_controls"][
        "min_directional_confidence"
    ] == 0.5
    assert context["broker_execution_touched"] is False
    assert context["orders_placed"] is False
    assert "daily target" in " ".join(context["decision_rules"])
    assert "ENTRY OPPORTUNITY DUTY" in ai_operator._OPERATOR_SYSTEM_PROMPT
    assert "SCAN_THROTTLED_CACHE" in ai_operator._OPERATOR_SYSTEM_PROMPT


def test_scalping_question_reaches_model_instead_of_local_trade_shortcut(tmp_path, monkeypatch):
    provider = _CapturingProvider("Scalping is not currently selected because the present strategy and cost evidence does not justify it.")
    op = _operator(tmp_path, monkeypatch, provider)
    monkeypatch.setattr(
        ai_operator,
        "gather_chat_context",
        lambda _config=None, **_kwargs: {
            "oversized_noncritical_context": "x" * 20_000,
            "trade_path_diagnostics": {
                "dispatch_loop": {
                    "running": True,
                    "execution_lane": "PAPER",
                    "last_management_status": "WATCHING_MARKET_CLOSED",
                    "last_management_detail": "The broker market is closed.",
                    "active_entry_timeframes": ["M1", "M5", "M15", "H1"],
                    "last_entry_timeframe": "M1",
                    "last_entry_lane": "MICRO_SCALP",
                },
                "entry_timeframe_scan": {
                    "selected_timeframe": "M1",
                    "entry_lane": "MICRO_SCALP",
                },
                "live_candle_route_source": {
                    "route_key": None,
                    "blockers": ["current broker quote reports the market or symbol is closed"],
                },
            },
        },
    )
    try:
        res = op.chat("WHY DONT YOU SCALP TRADE??")
        assert res["ok"] is True
        assert res["model_ok"] is True
        assert res["fallback"] is False
        assert res["response_source"] == "MODEL"
        assert res["chat_path_status"] == "MODEL_PRIMARY"
        assert len(provider.prompts) == 1
        assert "WHY DONT YOU SCALP TRADE??" in provider.prompts[0]
        assert "CURRENT_TRADE_PATH" in provider.prompts[0]
        assert "WATCHING_MARKET_CLOSED" in provider.prompts[0]
        assert "MICRO_SCALP" in provider.prompts[0]
        assert "current broker quote reports the market or symbol is closed" in provider.prompts[0]
        assert provider.prompts[0].index("CURRENT_TRADE_PATH") < provider.prompts[0].index("owner_guidance")
        assert "Say 0.1% for a value of 0.1" in provider.systems[0]
        assert "Do not compare combined portfolio risk directly" in provider.systems[0]
        assert "inspect CURRENT_TRADE_PATH first" in provider.systems[0]
        assert "does not by itself block paper/demo execution" in provider.systems[0]
        assert "not proof of a durable or live edge" in provider.systems[0]
        assert "does not modify the stop, size, or risk" in provider.systems[0]
        assert "Scalping is not currently selected" in res["reply"]
    finally:
        _teardown()


def test_chat_preserves_operator_lot_size_and_winner_compounding_authority(tmp_path, monkeypatch):
    from cas_forex.ai_operator_context import CRITICAL_SECTIONS

    provider = _CapturingProvider(
        "Yes. The Operator runtime may select an exact broker-grid size and a qualified winner add."
    )
    op = _operator(tmp_path, monkeypatch, provider)
    context = {key: {"status": "TEST_PRESENT"} for key in CRITICAL_SECTIONS}
    context["operator_constitution"] = (
        "# CAS Forex Operator Constitution\n"
        "- The AI Operator is the trading edge and autonomous execution layer. "
        "AUTHORITY_SENTINEL.\n"
        "- Exact sizing_ref and protected-winner scale_in actions need no per-add human confirmation."
    )
    context["psychology_guard"] = {
        "available": True,
        "risk_caps": {
            "precedence": "explicit owner risk-control override > AI dial > static config",
            "effective_max_open_position_count": 5,
            "effective_max_positions_per_symbol": 2,
            "effective_max_total_exposure_lots": 0.5,
            "effective_max_risk_per_trade_pct": 0.1,
            "override_persistence_status": "PERSISTED_OWNER_OVERRIDES_ACTIVE",
            "overrides_loaded_from_disk": True,
        },
    }
    context["active_account_objective"] = {
        "status": "PRIMARY_MT5_DEMO_ACCOUNT_ACTIVE",
        "objective_account_established": True,
        "authoritative_account_source": "live_mt5",
        "current_account": {
            "login": 1000694,
            "server": "Hugosway-Demo",
            "is_demo": True,
            "balance_usd": 44757.89,
            "equity_usd": 44555.70,
            "floating_pnl_usd": -202.19,
            "open_position_count": 2,
        },
        "growth_measurement": {
            "balance_baseline_status": "UNAVAILABLE_NO_RECONCILED_CASHFLOW_BASELINE",
            "current_balance_is_profit": False,
            "open_pnl_decomposition": {
                "price_pnl_usd": -188.94,
                "swap_or_carry_usd": -13.25,
                "commission_usd": 0.0,
                "reported_components_usd": -202.19,
                "account_net_open_pnl_usd": -202.19,
                "unattributed_open_pnl_usd": 0.0,
            },
        },
        "secondary_simulator_performance": {
            "scope": "SEPARATE_SIMULATOR_EVIDENCE_NOT_ACTIVE_ACCOUNT",
            "balance_usd": 5000.0,
            "performance_evidence_balance_usd": 3040.87,
            "authoritative_for_active_account": False,
        },
    }
    context["trade_path_diagnostics"] = {
        "dispatch_loop": {
            "running": True,
            "execution_lane": "PAPER",
            "last_management_status": "WATCHING_MARKET_CLOSED",
            "last_management_detail": "The primary MT5 broker market is closed.",
        }
    }
    context["primary_execution_truth"] = {
        "status": "PRIMARY_MT5_RUNTIME_ACTIVE",
        "paper_runtime_active": True,
        "conflicts": [
            {
                "code": "LEGACY_STATIC_SIM_DOES_NOT_BLOCK_PRIMARY_MT5",
                "detail": "Static simulator evidence is secondary.",
            }
        ],
    }
    context["live_mt5"] = {
        "connected": True,
        "is_demo": True,
        "open_position_count": 2,
        "position_risk_preview": [
            {"symbol": "US30", "floating_pnl_usd": -97.57},
            {"symbol": "NAS100", "floating_pnl_usd": -91.37},
        ],
    }
    context["oversized_noncritical_context"] = "x" * 40_000
    monkeypatch.setattr(
        ai_operator,
        "gather_chat_context",
        lambda _config=None, **_kwargs: context,
    )

    try:
        res = op.chat("Can you choose more than 0.01 lots and compound a winning trade?")

        assert res["ok"] is True
        assert res["chat_path_status"] == "MODEL_PRIMARY"
        assert res["context_delivery"]["decision_grade"] is True
        assert res["context_delivery"]["required_section_profile"] == "fast_owner_chat"
        assert "ACTIVE_ACCOUNT_NORTH_STAR" in res["priority_context_sections"]
        assert "CURRENT_TRADE_PATH" in res["priority_context_sections"]
        assert "ACTIVE_ACCOUNT_NORTH_STAR" not in res["context_delivery"]["sections_omitted"]
        assert len(provider.prompts) == 1
        assert "DECISION_GRADE_CONTEXT:" in provider.prompts[0]
        assert "ACTIVE_ACCOUNT_NORTH_STAR" in provider.prompts[0]
        assert '"swap_or_carry_usd":-13.25' in provider.prompts[0]
        assert '"performance_evidence_balance_usd":3040.87' in provider.prompts[0]
        assert "AUTHORITY_SENTINEL" in provider.prompts[0]
        assert "CURRENT_TRADE_PATH" in provider.prompts[0]
        assert "LEGACY_STATIC_SIM_DOES_NOT_BLOCK_PRIMARY_MT5" in provider.prompts[0]
        assert '"floating_pnl_usd":-97.57' in provider.prompts[0]
        assert '"effective_max_total_exposure_lots":0.5' in provider.prompts[0]
        assert '"override_persistence_status":"PERSISTED_OWNER_OVERRIDES_ACTIVE"' in provider.prompts[0]
        assert '"oversized_noncritical_context":"' not in provider.prompts[0]
        assert "COMMAND_CATALOG:" in provider.prompts[0]
        assert "OWNER'S MESSAGE:" in provider.prompts[0]
        assert "immediate Operator runtime can and must" in provider.systems[0]
        assert "net winning after currently reported" in provider.systems[0]
        assert "never add to a net loser after reported costs" in provider.systems[0]
        assert "broker minimum is a floor, not a permanent lot-size policy" in provider.systems[0]
        assert "No per-order or per-add human confirmation" in provider.systems[0]
        assert "Dispatch and execution guards are enforcement gates" in provider.systems[0]
        assert "never present a looser dial value as the actual dispatch limit" in provider.systems[0]
        assert "never present that secondary diagnostic as the current execution blocker" in provider.systems[0]
        assert "inspect PRIORITY_CONTEXT.ACTIVE_ACCOUNT_NORTH_STAR" in provider.systems[0]
    finally:
        _teardown()


def test_operator_chat_uses_a_realistic_model_timeout(tmp_path, monkeypatch):
    class _TimeoutAwareProvider:
        request_kind = None
        request_timeout = None
        max_attempts = None
        max_output_tokens = None

        def generate(
            self,
            prompt,
            system=None,
            *,
            request_kind=None,
            request_timeout=None,
            max_attempts=None,
            max_output_tokens=None,
        ):
            self.request_kind = request_kind
            self.request_timeout = request_timeout
            self.max_attempts = max_attempts
            self.max_output_tokens = max_output_tokens
            return {
                "ok": True,
                "text": "Claude received the Operator question.",
                "provider": "claude",
                "provider_label": "Claude (stub)",
                "model_ref": "claude-test",
                "model_backend": "frontier_anthropic",
                "model_role": "general",
                "request_kind": request_kind,
                "paid": True,
            }

    provider = _TimeoutAwareProvider()
    op = _operator(tmp_path, monkeypatch, provider)
    try:
        res = op.chat("explain the current strategy selection")
        assert res["model_ok"] is True
        assert provider.request_timeout == ai_operator.CHAT_MODEL_TIMEOUT_SECONDS
        assert provider.request_timeout == 10.0
        assert provider.request_kind == "operator_chat"
        assert provider.max_attempts == ai_operator.CHAT_MODEL_MAX_ATTEMPTS
        assert provider.max_attempts == 4
        assert provider.max_output_tokens == ai_operator.CHAT_MODEL_MAX_OUTPUT_TOKENS
        assert res["model_ref"] == "claude-test"
        assert res["model_backend"] == "frontier_anthropic"
        assert res["model_role"] == "general"
        assert res["model_request_kind"] == "operator_chat"
    finally:
        _teardown()


def test_operator_greeting_uses_fast_real_model_path_without_full_context(
    tmp_path, monkeypatch
):
    class _GreetingProvider:
        def __init__(self):
            self.calls = []

        def generate(self, prompt, system=None, **kwargs):
            self.calls.append({"prompt": prompt, "system": system, **kwargs})
            return {
                "ok": True,
                "text": "Hey. I'm here and ready. What do you want me to examine?",
                "provider": "deepseek-flash",
                "provider_label": "DeepSeek V4 Flash (test)",
                "model_ref": "deepseek-v4-flash-test",
                "model_backend": "deepseek_cloud",
                "model_role": kwargs.get("model_role"),
                "request_kind": kwargs.get("request_kind"),
                "paid": True,
            }

    def _full_context_must_not_run(*_args, **_kwargs):
        raise AssertionError("a greeting must not build the full Operator context")

    provider = _GreetingProvider()
    op = _operator(tmp_path, monkeypatch, provider)
    monkeypatch.setattr(ai_operator, "gather_chat_context", _full_context_must_not_run)
    try:
        res = op.chat("HEY")

        assert res["ok"] is True
        assert res["model_ok"] is True
        assert res["fallback"] is False
        assert res["chat_path_status"] == "MODEL_GREETING"
        assert res["response_source"] == "MODEL"
        assert res["provider"] == "deepseek-flash"
        assert res["model_request_kind"] == "operator_chat_greeting"
        assert res["proposed_command"] is None
        assert res["dials_changed"] is False
        assert len(provider.calls) == 1
        call = provider.calls[0]
        assert call["request_kind"] == "operator_chat_greeting"
        assert call["model_role"] == "fast"
        assert call["request_timeout"] == ai_operator.GREETING_MODEL_TIMEOUT_SECONDS
        assert call["max_attempts"] == ai_operator.CHAT_MODEL_MAX_ATTEMPTS
        assert call["max_output_tokens"] == ai_operator.GREETING_MODEL_MAX_OUTPUT_TOKENS
        assert "OWNER GREETING:\nHEY" in call["prompt"]
        assert "DECISION_GRADE_CONTEXT" not in call["prompt"]
        assert len(call["prompt"]) < 1_000
    finally:
        _teardown()


def test_launch_readiness_question_reaches_model_with_public_launch_gate(tmp_path, monkeypatch):
    import cas_forex.public_launch_gate as public_launch_gate

    provider = _CapturingProvider("The current public launch gate remains blocked by the missing counsel review.")
    op = _operator(tmp_path, monkeypatch, provider)
    monkeypatch.setattr(
        public_launch_gate,
        "build_public_launch_gate",
        lambda: {
            "report_kind": "cas_forex_public_launch_gate",
            "status": "ATTENTION",
            "launch_gate_status": "BLOCK_PUBLIC_LAUNCH",
            "public_launch_status": "BLOCKED",
            "live_money_production_status": "BLOCKED",
            "pass_count": 4,
            "block_count": 4,
            "hard_blockers": ["Counsel legal review is missing."],
            "gates": [
                {"status": "BLOCK", "label": "Counsel Legal Review", "detail": "Counsel review missing."},
            ],
            "release_policy": "Treat BLOCK_PUBLIC_LAUNCH as a hard stop.",
        },
    )
    try:
        res = op.chat("are we ready for public launch?")
        assert res["ok"] is True
        assert res["model_ok"] is True
        assert res["fallback"] is False
        assert len(provider.prompts) == 1
        assert "BLOCK_PUBLIC_LAUNCH" in provider.prompts[0]
        assert "Counsel legal review is missing." in provider.prompts[0]
        assert "missing counsel review" in res["reply"]
    finally:
        _teardown()


def test_chat_fails_soft_when_full_context_build_raises(tmp_path, monkeypatch):
    provider = _CapturingProvider("model should not be called")
    op = _operator(tmp_path, monkeypatch, provider)

    def _boom(_config=None, **_kwargs):
        raise RuntimeError("context exploded")

    monkeypatch.setattr(ai_operator, "gather_chat_context", _boom)
    try:
        res = op.chat("why hasn't the floating P&L changed in 24 hours?")
        assert res["ok"] is True
        assert res["model_ok"] is False
        assert res["fallback"] is True
        assert res["chat_path_status"] == "DEGRADED_CONTEXT_FALLBACK"
        assert provider.prompts == []
        assert "Operator chat degraded before the full reply path completed." in res["reply"]
        assert "Model issue: RuntimeError: context exploded." in res["reply"]
        assert "No dials changed and no command was executed" in res["reply"]
    finally:
        _teardown()


def test_chat_fails_soft_even_if_local_fallback_builder_raises(tmp_path, monkeypatch):
    provider = _CapturingProvider("model should not be called")
    op = _operator(tmp_path, monkeypatch, provider)

    def _boom(_config=None, **_kwargs):
        raise RuntimeError("primary context exploded")

    def _fallback_boom(*_args, **_kwargs):
        raise RuntimeError("fallback copy exploded")

    monkeypatch.setattr(ai_operator, "gather_chat_context", _boom)
    monkeypatch.setattr(ai_operator, "_local_chat_reply", _fallback_boom)
    try:
        res = op.chat("is everything working correctly?")
        assert res["ok"] is True
        assert res["model_ok"] is False
        assert res["fallback"] is True
        assert res["chat_path_status"] == "DEGRADED_CONTEXT_FALLBACK"
        assert provider.prompts == []
        assert "Operator chat degraded before the full reply path completed." in res["reply"]
        assert "RuntimeError: primary context exploded" in res["reply"]
        assert "No dials changed and no command was executed" in res["reply"]
    finally:
        _teardown()


def test_primary_execution_truth_prevents_legacy_simulator_override():
    truth = ai_operator._primary_execution_truth_context(
        trade_path={
            "dispatch_loop": {
                "running": True,
                "execution_active": True,
                "execution_lane": "PAPER",
                "mode": "PAPER_FALLBACK",
                "last_bridge_class": "MT5Bridge",
                "last_bridge_selection_status": "PAPER_MT5_ORDER_SEND_READY",
                "last_management_status": "WATCHING_MARKET_CLOSED",
                "last_management_detail": "Broker market is closed.",
                "last_management_broker_touched": False,
                "last_error": None,
            }
        },
        live_mt5={
            "connected": True,
            "is_demo": True,
            "open_position_count": 2,
            "positions": [
                {"symbol": "US30", "floating_pnl_usd": -97.57, "swap_usd": -7.60},
                {"symbol": "NAS100", "floating_pnl_usd": -91.37, "swap_usd": -5.65},
            ],
            "algo_allowed": True,
            "account": {"login": 1000694, "server": "Hugosway-Demo"},
        },
        auto_halt={"halt_active": True, "force_paper_mode": True},
        broker_truth={"running": False, "ready_for_live": False},
        supervision={
            "status": "ATTENTION",
            "price_source_status": "STATIC_SIMULATION_FALLBACK",
            "static_simulation_active": True,
        },
        handoff={"status": "BLOCKED"},
        account_health={"open_exposure": {"open_position_count": 0}},
    )

    codes = {row["code"] for row in truth["conflicts"]}
    assert truth["status"] == "PRIMARY_MT5_RUNTIME_ACTIVE"
    assert truth["paper_runtime_active"] is True
    assert truth["primary_runtime"]["management_status"] == "WATCHING_MARKET_CLOSED"
    assert "LEGACY_STATIC_SIM_DOES_NOT_BLOCK_PRIMARY_MT5" in codes
    assert "SIMULATOR_LEDGER_POSITION_COUNT_DIFFERS_FROM_MT5" in codes
    assert "AUTO_HALT_FORCE_PAPER_BLOCKS_LIVE_ONLY" in codes
    assert "LIVE_MONITOR_STOPPED_DOES_NOT_STOP_PAPER_LOOP" in codes
    assert "EXECUTION TRUTH PRECEDENCE" in ai_operator._OPERATOR_SYSTEM_PROMPT


def test_lesson_filter_rejects_primary_mt5_contradiction():
    context = {
        "primary_execution_truth": {
            "primary_runtime_established": True,
            "conflicts": [
                {"code": "LEGACY_STATIC_SIM_DOES_NOT_BLOCK_PRIMARY_MT5"}
            ],
        }
    }
    reason = ai_operator._lesson_primary_truth_conflict(
        text=(
            "AI Hedge trade-management supervision is blocked end-to-end because "
            "the price source is STATIC_SIMULATION_FALLBACK."
        ),
        evidence="static simulator fallback",
        context=context,
    )
    assert reason is not None
    assert "does not block the primary MT5 runtime" in reason


def test_active_account_objective_uses_mt5_and_keeps_simulator_secondary():
    result = ai_operator._active_account_objective_context(
        live_mt5={
            "connected": True,
            "is_demo": True,
            "open_position_count": 2,
            "positions": [
                {"symbol": "US30", "floating_pnl_usd": -97.57, "swap_usd": -7.60},
                {"symbol": "NAS100", "floating_pnl_usd": -91.37, "swap_usd": -5.65},
            ],
            "account": {
                "login": 1000694,
                "server": "Hugosway-Demo",
                "currency": "USD",
                "balance_usd": 44757.89,
                "equity_usd": 44555.70,
                "floating_pnl_usd": -202.19,
                "margin_used_usd": 411.75,
                "free_margin_usd": 44143.95,
                "leverage": 500,
            },
        },
        dispatch_loop={
            "running": True,
            "execution_active": True,
            "execution_lane": "PAPER",
            "mode": "PAPER_FALLBACK",
            "last_bridge_class": "MT5Bridge",
            "last_bridge_selection_status": "PAPER_MT5_ORDER_SEND_READY",
        },
        simulator_performance={
            "scope": "PAPER_SIMULATOR_PERFORMANCE",
            "honest_paper_balance_usd": 3040.87,
            "balance_growth_net_pnl_usd": 1040.87,
            "honest_unique_signal_net_pnl_usd": 1274.07,
            "daily_winnings_target_usd": 1000,
            "daily_cap_usd": 3500,
        },
        account_health={"account": {"balance_usd": 5000.0}},
        demo_learning={
            "status": "MT5_DEMO_LEARNING_BOUND",
            "learning_overall": {
                "trades": 4,
                "wins": 1,
                "losses": 3,
                "net_pnl": -6.77,
            },
            "net_profit_loss_account": -1489.50,
        },
    )

    assert result["status"] == "PRIMARY_MT5_DEMO_ACCOUNT_ACTIVE"
    assert result["authoritative_account_source"] == "live_mt5"
    assert result["current_account"]["balance_usd"] == 44757.89
    assert result["current_account"]["position_price_pnl_usd"] == -188.94
    assert result["current_account"]["open_swap_usd"] == -13.25
    assert result["current_account"]["unattributed_open_pnl_usd"] == 0.0
    assert result["growth_measurement"]["current_balance_is_profit"] is False
    assert result["growth_measurement"]["open_pnl_decomposition"]["account_net_open_pnl_usd"] == -202.19
    assert result["growth_measurement"]["cas_bound_closed_outcomes"]["net_pnl_usd"] == -6.77
    assert result["secondary_simulator_performance"]["balance_usd"] == 5000.0
    assert result["secondary_simulator_performance"]["balance_source"] == "ACCOUNT_HEALTH_SIMULATOR_LEDGER"
    assert result["secondary_simulator_performance"]["performance_evidence_balance_usd"] == 3040.87
    assert result["secondary_simulator_performance"]["authoritative_for_active_account"] is False
    assert result["daily_objective"]["target_deficit_may_manufacture_trade"] is False
    assert result["daily_objective"]["target_deficit_may_increase_risk"] is False


def test_active_account_objective_recovers_after_cost_pnl_from_compact_mt5_context():
    compact = ai_operator._compact_mt5_snapshot(
        {
            "connected": True,
            "is_demo": True,
            "open_position_count": 2,
            "account": {
                "login": 1000694,
                "server": "Hugosway-Demo",
                "balance_usd": 44757.89,
                "equity_usd": 44555.70,
                "floating_pnl_usd": -202.19,
            },
            "positions": [
                {"symbol": "US30", "floating_pnl_usd": -97.57, "swap_usd": -7.60},
                {"symbol": "NAS100", "floating_pnl_usd": -91.37, "swap_usd": -5.65},
            ],
        }
    )

    result = ai_operator._active_account_objective_context(
        live_mt5=compact,
        dispatch_loop={
            "running": True,
            "execution_active": True,
            "execution_lane": "PAPER",
            "last_bridge_class": "MT5Bridge",
        },
        simulator_performance={"honest_paper_balance_usd": 3040.87},
        account_health={"account": {"balance_usd": 5000.0}},
    )

    decomposition = result["growth_measurement"]["open_pnl_decomposition"]
    assert result["current_account"]["open_position_count"] == 2
    assert decomposition["price_pnl_usd"] == -188.94
    assert decomposition["swap_or_carry_usd"] == -13.25
    assert decomposition["commission_usd"] == 0.0
    assert decomposition["account_net_open_pnl_usd"] == -202.19
    assert decomposition["unattributed_open_pnl_usd"] == 0.0
    assert result["secondary_simulator_performance"]["balance_usd"] == 5000.0
    assert result["secondary_simulator_performance"]["performance_evidence_balance_usd"] == 3040.87


def test_active_account_objective_uses_only_matching_reconciled_growth():
    live_mt5 = {
        "connected": True,
        "is_demo": True,
        "open_position_count": 0,
        "account": {
            "login": 1000694,
            "server": "Hugosway-Demo",
            "currency": "USD",
            "balance_usd": 44757.89,
            "equity_usd": 44757.89,
            "floating_pnl_usd": 0.0,
        },
    }
    growth = {
        "status": "RECONCILED_CASHFLOW_ADJUSTED_GROWTH",
        "generated_at": "2026-07-11T13:00:00+00:00",
        "event_hash": "growth-event-1",
        "refresh_status": "FULL_HISTORY_REFRESHED",
        "period_realized_status": "RECONCILED_MT5_ACCOUNT_HISTORY",
        "period": {
            "utc_day": datetime.now(timezone.utc).date().isoformat(),
            "utc_month": datetime.now(timezone.utc).strftime("%Y-%m"),
        },
        "account": {
            "account_id_hash": account_identity_hash(1000694, "Hugosway-Demo"),
            "current_balance_account_currency": 44757.89,
        },
        "baseline": {
            "status": "RECONCILED_CASHFLOW_ADJUSTED_ACCOUNT_HISTORY",
            "net_external_capital_flow_account_currency": 100000.0,
        },
        "realized_growth": {
            "cashflow_adjusted_all_time_account_currency": -55242.11,
            "today_account_currency": -12.34,
            "month_account_currency": -55242.11,
            "growth_pct_on_net_external_capital": -55.2421,
        },
        "reconciliation": {
            "ledger_ties_to_current_balance": True,
            "growth_components_tie": True,
        },
    }

    result = ai_operator._active_account_objective_context(
        live_mt5=live_mt5,
        dispatch_loop={
            "running": True,
            "execution_active": True,
            "execution_lane": "PAPER",
            "last_bridge_class": "MT5Bridge",
        },
        simulator_performance={},
        account_growth=growth,
    )

    measured = result["growth_measurement"]
    assert measured["balance_baseline_status"] == "RECONCILED_CASHFLOW_ADJUSTED_ACCOUNT_HISTORY"
    assert measured["cashflow_adjusted_realized_growth_usd"] == -55242.11
    assert measured["realized_today_usd"] == -12.34
    assert measured["net_external_capital_flow_usd"] == 100000.0
    assert measured["account_growth_reconciliation"]["reconciled"] is True
    assert measured["current_balance_is_profit"] is False


def test_operator_prompt_forbids_daily_target_chasing_and_scoreboard_mixing():
    prompt = ai_operator._OPERATOR_SYSTEM_PROMPT

    assert "ACTIVE ACCOUNT OBJECTIVE" in prompt
    assert "NEVER a trade quota" in prompt
    assert "never add simulator and MT5 P&L together" in prompt
    assert "size up toward it" not in prompt
    assert "Being behind target must never manufacture a setup" in prompt
    assert "broker-valued after-cost R expectancy first" in prompt
    assert "Per-lot dollars are not comparable edge across instruments" in prompt
    assert "Be Rank learned behavior" not in prompt
