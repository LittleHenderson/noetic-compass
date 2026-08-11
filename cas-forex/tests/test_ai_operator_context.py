from __future__ import annotations

import copy
import json

from cas_forex.ai_operator import build_prompt
from cas_forex.ai_operator_context import (
    CRITICAL_SECTIONS,
    DEFAULT_MAX_JSON_CHARS,
    FAST_CHAT_CRITICAL_SECTIONS,
    SCHEMA_VERSION,
    build_operator_context_packet,
    serialize_operator_context_packet,
)
from cas_forex.pcba_prompt_injection import evaluate_pcba_prompt_injection


def _full_context() -> dict[str, object]:
    repeated_delivery_lessons = [
        {
            "category": "data_quality",
            "lesson": f"Tick payload was truncated before fresh evidence section {index}.",
            "reinforced": 1,
        }
        for index in range(30)
    ]
    return {
        "operator_constitution": (
            "# CAS Forex Operator Constitution\n"
            "- Version: spec-test\n"
            "- Authority boundary: autonomous actions stay inside runtime gates.\n"
            "- Primary objective: grow balance with evidence-backed edge.\n"
            "- The AI Operator is the trading edge and autonomous execution layer.\n"
            + ("STATIC-CONTEXT " * 10_000)
        ),
        "active_account_objective": {
            "report_kind": "cas_forex_active_account_objective",
            "status": "PRIMARY_MT5_DEMO_ACCOUNT_ACTIVE",
            "objective_account_established": True,
            "authoritative_account_source": "live_mt5",
            "execution": {
                "running": True,
                "execution_active": True,
                "execution_lane": "PAPER",
                "bridge_class": "MT5Bridge",
            },
            "current_account": {
                "login": 1000694,
                "server": "Hugosway-Demo",
                "currency": "USD",
                "is_demo": True,
                "balance_usd": 44757.89,
                "equity_usd": 44555.70,
                "floating_pnl_usd": -202.19,
                "open_position_count": 2,
                "position_price_pnl_usd": -188.94,
                "open_swap_usd": -13.25,
                "open_commission_usd": 0.0,
                "unattributed_open_pnl_usd": 0.0,
            },
            "growth_measurement": {
                "current_balance_usd": 44757.89,
                "current_equity_usd": 44555.70,
                "floating_pnl_usd": -202.19,
                "balance_baseline_status": "RECONCILED_CASHFLOW_ADJUSTED_ACCOUNT_HISTORY",
                "current_balance_is_profit": False,
                "period_realized_status": "RECONCILED_MT5_ACCOUNT_HISTORY",
                "cashflow_adjusted_realized_growth_usd": -55242.11,
                "realized_today_usd": -12.34,
                "realized_month_usd": -55242.11,
                "net_external_capital_flow_usd": 100000.0,
                "growth_pct_on_net_external_capital": -55.2421,
                "account_growth_reconciliation": {
                    "status": "RECONCILED_CASHFLOW_ADJUSTED_GROWTH",
                    "account_matches": True,
                    "balance_matches": True,
                    "reconciled": True,
                    "event_hash": "growth-event-1",
                    "refresh_status": "FULL_HISTORY_REFRESHED",
                },
                "open_pnl_decomposition": {
                    "price_pnl_usd": -188.94,
                    "swap_or_carry_usd": -13.25,
                    "commission_usd": 0.0,
                    "account_net_open_pnl_usd": -202.19,
                    "unattributed_open_pnl_usd": 0.0,
                    "interpretation": "NET_AFTER_REPORTED_OPEN_COSTS_NOT_REALIZED_PROFIT",
                },
                "cas_bound_closed_outcomes": {
                    "trades": 4,
                    "wins": 1,
                    "losses": 3,
                    "net_pnl_usd": -6.77,
                    "scope": "CAS_BOUND_MT5_DEMO_OUTCOMES_ONLY",
                },
            },
            "daily_objective": {
                "target_usd": 1000,
                "cap_usd": 3500,
                "policy": "REPORTING_ONLY_NOT_A_TRADE_QUOTA",
                "target_deficit_may_manufacture_trade": False,
                "target_deficit_may_increase_risk": False,
            },
            "secondary_simulator_performance": {
                "balance_usd": 3123.45,
                "net_pnl_usd": 1123.45,
                "authoritative_for_active_account": False,
            },
            "decision_rules": ["Never add simulator P&L to MT5 P&L."],
        },
        "profit_and_balance": {
            "objective": "PROFIT_SENTINEL grow the balance",
            "honest_paper_balance_usd": 3123.45,
            "balance_growth_net_pnl_usd": 1123.45,
            "unique_signals": 81,
            "unique_win_rate": 0.58,
            "unique_profit_factor": 1.22,
            "raw_trades": 120,
            "stacking_is_blind": False,
            "caveats": ["paper evidence", "costs included"],
        },
        "primary_execution_truth": {
            "report_kind": "cas_forex_primary_execution_truth",
            "status": "PRIMARY_MT5_RUNTIME_ACTIVE",
            "primary_runtime_established": True,
            "paper_runtime_active": True,
            "authoritative_sources": {
                "broker_account_and_positions": "live_mt5",
                "order_and_position_management": "trade_path_diagnostics.dispatch_loop",
            },
            "primary_runtime": {
                "running": True,
                "execution_active": True,
                "execution_lane": "PAPER",
                "bridge_class": "MT5Bridge",
                "management_status": "WATCHING_MARKET_CLOSED",
            },
            "broker_account": {
                "connected": True,
                "is_demo": True,
                "open_position_count": 2,
                "algo_allowed": True,
            },
            "conflict_count": 1,
            "conflicts": [
                {
                    "code": "LEGACY_STATIC_SIM_DOES_NOT_BLOCK_PRIMARY_MT5",
                    "detail": "Legacy static simulator evidence is secondary.",
                }
            ],
            "decision_rules": ["Use dispatch_loop for current management state."],
        },
        "entry_opportunity_pipeline": {
            "report_kind": "cas_forex_entry_opportunity_pipeline",
            "generated_at": "2026-07-14T12:00:00+00:00",
            "status": "ALL_OBSERVED_LANES_BELOW_DIRECTIONAL_FLOOR",
            "dispatch": {
                "running": True,
                "execution_lane": "PAPER",
                "paper_learning_active": True,
                "eligible_symbol_count": 17,
                "collected_intent_count": 0,
                "filtered_intent_count": 0,
                "risk_candidate_count": 0,
                "risk_feasible_count": 0,
                "operator_candidate_count": 0,
                "entry_risk_status": "NO_OVERSEER_APPROVED_CANDIDATES",
            },
            "current_scheduler_invocation": {
                "status": "SCAN_THROTTLED_CACHE",
                "selected_timeframe": "M1",
                "fresh_market_scan_performed": False,
                "cache_remaining_seconds": 31.5,
            },
            "multi_timeframe_scan_runtime": {
                "status": "ENTRY_SCAN_RUNTIME_OBSERVED",
                "full_scan_lane_count": 4,
                "timeframes_observed": ["H1", "M1", "M15", "M5"],
                "attempt_count": 68,
                "directional_candidate_count": 0,
                "candidate_formation_status_counts": {
                    "BELOW_DIRECTIONAL_FLOOR": 68
                },
                "shadow_edge_status_counts": {
                    "PASS": 1,
                    "NO_TRADE_NULL_FAILED": 67,
                },
                "shadow_pass_preview_count": 1,
                "all_observed_lanes_below_directional_floor": True,
                "best_shadow_pass_lane": {
                    "symbol": "EUR/USD",
                    "timeframe": "H1",
                    "direction": "SHORT",
                    "directional_score": 0.29,
                    "directional_floor": 0.5,
                    "shadow_edge_status": "PASS",
                    "shadow_measured_win_prob": 0.82,
                    "shadow_threshold": 0.65,
                    "shadow_edge_preview_unregistered": True,
                    "shadow_edge_authorization_minted": False,
                    "shadow_has_edge_token": False,
                },
                "shadow_pass_selection_basis": (
                    "highest_directional_score_then_measured_win_probability"
                ),
                "strongest_rejected_lane": {
                    "symbol": "NAS100",
                    "timeframe": "M5",
                    "direction": "LONG",
                    "directional_score": 0.31,
                    "directional_floor": 0.5,
                    "margin_to_floor": -0.19,
                    "shadow_edge_status": "PASS",
                    "shadow_measured_win_prob": 0.8,
                    "shadow_null_p95": 0.02,
                    "shadow_threshold": 0.65,
                    "shadow_edge_preview_unregistered": True,
                    "shadow_edge_authorization_minted": False,
                    "shadow_has_edge_token": False,
                },
                "broker_execution_touched": False,
                "orders_placed": False,
            },
            "operator_adjustable_candidate_controls": {
                "min_directional_confidence": 0.5,
                "min_directional_confidence_bounds": {"min": 0.05, "max": 0.9},
                "edge_threshold": 0.65,
                "max_concurrent_trades": 4,
                "max_concurrent_trades_bounds": {"min": 1, "max": 50},
                "max_total_exposure_lots": 2.0,
                "paper_learning_trades": 1,
                "timeframes": ["M1", "M5", "M15", "H1"],
            },
            "capacity_pressure": {
                "status": "POSITION_CAPACITY_STARVATION",
                "cap_block_event_count": 19,
                "distinct_symbol_count": 7,
                "symbols": ["EUR/GBP", "GBP/JPY", "USD/CHF"],
                "current_open_position_count": 4,
                "current_max_open_position_count": 4,
                "current_total_exposure_lots": 0.04,
                "current_max_total_exposure_lots": 2.0,
                "exposure_utilization_pct": 2.0,
                "low_exposure_threshold_pct": 25.0,
                "explicit_owner_override_active": False,
                "autonomous_one_slot_review_allowed": True,
                "recommended_review_cap": 5,
                "event_hash": "capacity-projection-sentinel",
            },
            "decision_rules": [
                "A cache-throttled scheduler invocation is not a completed market scan."
            ],
            "broker_execution_touched": False,
            "orders_placed": False,
        },
        "learning_outcomes": {
            "marker": "LEARNING_SENTINEL",
            "ranking_basis": "after_cost_expectancy_r_then_per_1_lot_then_raw_expectancy_then_net_pnl",
            "risk_normalized_ranking_required_for_promotion": True,
            "overall": {
                "trades": 81,
                "wins": 47,
                "losses": 34,
                "net_pnl": 1123.45,
                "after_cost_expectancy_r": 0.18,
                "risk_normalized_trade_count": 81,
                "risk_normalized_evidence_complete": True,
                "stored_pre_trade_risk_mismatch_count": 3,
            },
            "best_groups": [
                {
                    "symbol": "EUR/USD",
                    "net_pnl": 500,
                    "after_cost_expectancy_r": 0.25,
                    "risk_normalized_evidence_complete": True,
                }
            ],
        },
        "outcome_binding": {
            "status": "OUTCOME_READY",
            "bound_outcome_count": 81,
            "net_paper_pnl": 1123.45,
            "next_action": "OUTCOME_SENTINEL",
        },
        "learning": {
            "status": "LEARNING_ACTIVE",
            "direction_rows": 81,
            "confirmed_direction_count": 12,
            "blocked_direction_count": 69,
            "groups": [
                {
                    "symbol": "EUR/USD",
                    "timeframe": "H1",
                    "direction": "LONG",
                    "cycles": 20,
                    "confirmed_count": 12,
                    "last_edge_status": "PASS",
                    "last_edge_reason": "LEARNING_GROUP_SENTINEL",
                }
            ],
        },
        "adaptation": {
            "status": "ADAPTATION_REVIEW",
            "adaptation_ready_for_owner_review": True,
            "proposal_count": 1,
            "next_action": "ADAPTATION_SENTINEL",
        },
        "early_banking_analysis": {
            "report_kind": "early",
            "enough_data": True,
            "best_policy": {"bank_fraction_of_peak": 0.7, "delta_vs_hold": 50},
            "verdict": "EARLY_BANK_SENTINEL",
        },
        "trailing_stop_analysis": {
            "report_kind": "trailing",
            "enough_data": True,
            "best_policy": {"trail_lock_fraction": 0.5, "delta_vs_hold": 25},
            "verdict": "TRAILING_SENTINEL",
        },
        "inherited_lessons": [
            *repeated_delivery_lessons,
            {
                "category": "edge",
                "lesson": "LESSON_SENTINEL preserve independent profitable setups after costs.",
                "reinforced": 9,
            },
        ],
        "dials": {"edge_threshold": 0.61, "max_positions_per_symbol": 1},
        "dial_bounds": {"edge_threshold": {"min": 0.5, "max": 0.9}},
        "owner_guidance": [{"text": "OWNER_GUIDANCE_SENTINEL"}],
        "recent_cycles": {"available": True, "window": 20, "decision_counts": {"PASS": 4}},
        "account_health": {
            "status": "OBSERVING",
            "account": {"balance_usd": 3123.45, "equity_usd": 3130},
            "open_exposure": {"open_position_count": 2, "open_risk_estimate_usd": 30},
            "source_health": {"price_source_status": "PROVIDER_ACTIVE"},
        },
        "psychology_guard": {
            "available": True,
            "ai_dial": {"cooldown_active": False, "warning_active": False},
            "risk_caps": {
                "precedence": "explicit owner risk-control override > AI dial > static config",
                "explicit_owner_override_keys": ["max_total_exposure_lots"],
                "effective_max_open_position_count": 5,
                "effective_max_positions_per_symbol": 1,
                "effective_max_total_exposure_lots": 0.5,
                "effective_max_risk_per_trade_pct": 0.1,
                "real_money_controls_armed": True,
                "would_block_new_loosening": False,
            },
        },
        "auto_halt": {"available": True, "status": "CLEAR", "halt_active": False},
        "broker_truth_monitor": {
            "available": True,
            "status": "RUNNING",
            "ready_for_live": False,
            "mt5_connected": True,
            "mt5_is_demo": True,
        },
        "ai_hedge_supervision": {
            "available": True,
            "status": "WATCHING",
            "position_count": 2,
            "action_recommendation_count": 1,
            "recommendations": [{"intent": "protect_profit", "symbol": "EUR/USD"}],
        },
        "ai_hedge_management_handoff": {
            "available": True,
            "status": "READY",
            "management_action_count": 1,
            "management_actions": [{"intent": "set_take_profit"}],
        },
        "ai_hedge_management_execution": {
            "available": True,
            "status": "RECONCILED",
            "latest_terminal_receipt_status": "CONFIRMED",
        },
        "emergency_controls": {
            "available": True,
            "status": "OK",
            "automation_stop_ok": True,
            "controls": [{"key": "master_kill", "category": "automation_stop", "status": "OK"}],
        },
        "autonomous_money_movement": {
            "report_kind": "money",
            "autonomous_enabled": False,
            "provider_runtime": {"status": "NOT_CONFIGURED", "runtime_is_simulated": True},
        },
        "trade_path_diagnostics": {"dispatch_loop": {"running": True, "mode": "PAPER"}},
        "public_launch_gate": {"status": "ATTENTION", "launch_gate_status": "BLOCK_PUBLIC_LAUNCH"},
        "ai_hedge_intelligence_layer": {"status": "ACTIVE", "primary_role": "TRADING_EDGE"},
        "tool_manifest": {"mandatory_paths": {"broker_orders": ["order_dispatch.py"]}},
        "oversized_noncritical_history": ["NOISE" * 2_000 for _ in range(20)],
    }


def test_learning_projection_tolerates_count_only_groups_summary():
    context = _full_context()
    context["learning"]["groups"] = {"count": 42}

    packet = build_operator_context_packet(context)

    assert packet["context_delivery"]["decision_grade"] is True
    assert packet["learning"]["leading_groups"] == []


def test_operator_context_packet_preserves_all_critical_sections_without_blind_slice():
    context = _full_context()

    packet = build_operator_context_packet(context)
    delivery = packet["context_delivery"]
    serialized = serialize_operator_context_packet(packet)

    assert delivery["status"] == "DECISION_GRADE_CONTEXT"
    assert delivery["schema_version"] == SCHEMA_VERSION
    assert delivery["decision_grade"] is True
    assert delivery["blind_character_slice_used"] is False
    assert delivery["critical_sections_missing"] == []
    assert set(delivery["critical_sections_present"]) == set(CRITICAL_SECTIONS)
    assert delivery["source_context_chars"] > 100_000
    assert delivery["packet_json_chars"] == len(serialized)
    assert delivery["included_section_count"] == len(packet) - 1
    assert delivery.get("budget_exhausted") is not True
    assert len(serialized) <= DEFAULT_MAX_JSON_CHARS
    assert packet["active_account_objective"]["status"] == "PRIMARY_MT5_DEMO_ACCOUNT_ACTIVE"
    assert packet["active_account_objective"]["current_account"]["balance_usd"] == 44757.89
    assert packet["active_account_objective"]["growth_measurement"]["open_pnl_decomposition"]["account_net_open_pnl_usd"] == -202.19
    assert packet["active_account_objective"]["growth_measurement"]["open_pnl_decomposition"]["swap_or_carry_usd"] == -13.25
    assert packet["active_account_objective"]["growth_measurement"]["cashflow_adjusted_realized_growth_usd"] == -55242.11
    assert packet["active_account_objective"]["growth_measurement"]["realized_today_usd"] == -12.34
    assert packet["active_account_objective"]["growth_measurement"]["account_growth_reconciliation"]["reconciled"] is True
    assert packet["active_account_objective"]["daily_objective"]["target_deficit_may_increase_risk"] is False
    assert packet["profit_and_balance"]["objective"].startswith("PROFIT_SENTINEL")
    assert packet["primary_execution_truth"]["status"] == "PRIMARY_MT5_RUNTIME_ACTIVE"
    assert packet["primary_execution_truth"]["conflicts"][0]["code"] == (
        "LEGACY_STATIC_SIM_DOES_NOT_BLOCK_PRIMARY_MT5"
    )
    opportunity = packet["entry_opportunity_pipeline"]
    assert opportunity["status"] == "ALL_OBSERVED_LANES_BELOW_DIRECTIONAL_FLOOR"
    assert opportunity["current_scheduler_invocation"]["status"] == (
        "SCAN_THROTTLED_CACHE"
    )
    assert opportunity["multi_timeframe_scan_runtime"][
        "all_observed_lanes_below_directional_floor"
    ] is True
    assert opportunity["multi_timeframe_scan_runtime"]["strongest_rejected_lane"][
        "directional_score"
    ] == 0.31
    assert opportunity["multi_timeframe_scan_runtime"]["shadow_pass_preview_count"] == 1
    assert opportunity["multi_timeframe_scan_runtime"]["best_shadow_pass_lane"][
        "symbol"
    ] == "EUR/USD"
    assert opportunity["multi_timeframe_scan_runtime"]["strongest_rejected_lane"][
        "shadow_edge_status"
    ] == "PASS"
    assert opportunity["multi_timeframe_scan_runtime"]["strongest_rejected_lane"][
        "shadow_has_edge_token"
    ] is False
    assert opportunity["operator_adjustable_candidate_controls"][
        "min_directional_confidence"
    ] == 0.5
    assert opportunity["capacity_pressure"]["cap_block_event_count"] == 19
    assert opportunity["capacity_pressure"]["recommended_review_cap"] == 5
    assert opportunity["capacity_pressure"]["event_hash"] == (
        "capacity-projection-sentinel"
    )
    assert opportunity["operator_adjustable_candidate_controls"][
        "max_concurrent_trades"
    ] == 4
    assert packet["psychology_guard"]["risk_caps"]["effective_max_total_exposure_lots"] == 0.5
    assert packet["psychology_guard"]["risk_caps"]["effective_max_open_position_count"] == 5
    assert packet["learning_outcomes"]["marker"] == "LEARNING_SENTINEL"
    assert packet["learning_outcomes"]["overall"]["after_cost_expectancy_r"] == 0.18
    assert packet["learning_outcomes"]["overall"][
        "risk_normalized_evidence_complete"
    ] is True
    assert packet["learning_outcomes"]["best_groups"][0][
        "after_cost_expectancy_r"
    ] == 0.25
    lessons = json.dumps(packet["inherited_lessons"])
    assert "LESSON_SENTINEL" in lessons
    assert packet["inherited_lessons"]["repetitive_context_delivery_lessons_suppressed"] == 30
    assert "oversized_noncritical_history" in delivery["sections_omitted"]


def test_fast_owner_chat_profile_is_decision_grade_without_scheduled_learning_sections():
    context = {
        key: {"status": "CHAT_FACT_PRESENT"}
        for key in FAST_CHAT_CRITICAL_SECTIONS
    }
    context["active_account_objective"] = _full_context()["active_account_objective"]

    packet = build_operator_context_packet(
        context,
        critical_sections=FAST_CHAT_CRITICAL_SECTIONS,
        required_section_profile="fast_owner_chat",
    )
    delivery = packet["context_delivery"]

    assert delivery["status"] == "DECISION_GRADE_CONTEXT"
    assert delivery["decision_grade"] is True
    assert delivery["required_section_profile"] == "fast_owner_chat"
    assert delivery["decision_scope"] == "OWNER_CHAT_EXPLANATION_NO_SIDE_EFFECTS"
    assert delivery["critical_section_count"] == len(FAST_CHAT_CRITICAL_SECTIONS)
    assert delivery["critical_sections_missing"] == []
    assert "learning" not in packet
    assert packet["active_account_objective"]["growth_measurement"]["open_pnl_decomposition"]["swap_or_carry_usd"] == -13.25


def test_operator_prompt_contains_parseable_packet_and_late_edge_evidence():
    context = _full_context()
    prompt = build_prompt(context)
    payload = prompt.split("\n\n", 1)[1]
    packet = json.loads(payload)

    assert packet["context_delivery"]["decision_grade"] is True
    assert packet["learning_outcomes"]["marker"] == "LEARNING_SENTINEL"
    assert "LESSON_SENTINEL" in payload
    assert "PROFIT_SENTINEL" in payload
    assert "do not call the packet truncated" in prompt
    assert evaluate_pcba_prompt_injection(prompt) == (False, [])


def test_operator_context_fingerprint_ignores_builder_timestamps_but_tracks_profit_change():
    first_context = _full_context()
    first_context["learning"]["generated_at"] = "2026-07-10T01:00:00Z"
    second_context = copy.deepcopy(first_context)
    second_context["learning"]["generated_at"] = "2026-07-10T02:00:00Z"

    first = build_operator_context_packet(first_context)["context_delivery"]
    second = build_operator_context_packet(second_context)["context_delivery"]
    assert first["evidence_fingerprint"] == second["evidence_fingerprint"]

    second_context["profit_and_balance"]["balance_growth_net_pnl_usd"] = 9999
    changed = build_operator_context_packet(second_context)["context_delivery"]
    assert changed["evidence_fingerprint"] != first["evidence_fingerprint"]
