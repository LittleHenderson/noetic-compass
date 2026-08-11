"""Bounded, decision-grade evidence packets for AI Operator ticks."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from cas_forex.time_utils import utc_now


REPORT_KIND = "cas_forex_ai_operator_context_delivery"
SCHEMA_VERSION = "cas_forex_operator_edge_context.v11"
DEFAULT_MAX_JSON_CHARS = 30_000
MIN_MAX_JSON_CHARS = 8_000

CLAIM_BOUNDARY = (
    "The Operator context packet is an intentionally compact evidence projection, "
    "not a complete raw event history. decision_grade means every section required by "
    "the declared context profile is present in structured form. It does not mean every "
    "historical row is included, "
    "and it does not authorize a trade, transfer, or risk-limit bypass."
)

CRITICAL_SECTIONS = (
    "operator_constitution",
    "active_account_objective",
    "profit_and_balance",
    "primary_execution_truth",
    "entry_opportunity_pipeline",
    "learning_outcomes",
    "outcome_binding",
    "learning",
    "adaptation",
    "early_banking_analysis",
    "trailing_stop_analysis",
    "inherited_lessons",
    "dials",
    "dial_bounds",
    "owner_guidance",
    "recent_cycles",
    "account_health",
    "psychology_guard",
    "auto_halt",
    "broker_truth_monitor",
    "ai_hedge_supervision",
    "ai_hedge_management_handoff",
    "ai_hedge_management_execution",
    "emergency_controls",
    "autonomous_money_movement",
)

# Owner chat answers need current account, execution, authority, and protection
# truth without blocking on the slower learning/replay builders used by a
# scheduled strategy tick. This is a narrower decision scope, not a weaker
# autonomous-trading packet.
FAST_CHAT_CRITICAL_SECTIONS = (
    "operator_constitution",
    "active_account_objective",
    "profit_and_balance",
    "primary_execution_truth",
    "entry_opportunity_pipeline",
    "inherited_lessons",
    "dials",
    "dial_bounds",
    "owner_guidance",
    "account_health",
    "psychology_guard",
    "auto_halt",
    "broker_truth_monitor",
    "ai_hedge_supervision",
    "ai_hedge_management_handoff",
    "ai_hedge_management_execution",
    "emergency_controls",
    "autonomous_money_movement",
)

SECTION_ORDER = (
    "your_recent_dial_changes",
    "previous_context_delivery",
    "operator_constitution",
    "active_account_objective",
    "profit_and_balance",
    "primary_execution_truth",
    "entry_opportunity_pipeline",
    "learning_outcomes",
    "outcome_binding",
    "learning",
    "adaptation",
    "early_banking_analysis",
    "trailing_stop_analysis",
    "inherited_lessons",
    "dials",
    "dial_bounds",
    "owner_guidance",
    "recent_cycles",
    "account_health",
    "psychology_guard",
    "auto_halt",
    "broker_truth_monitor",
    "ai_hedge_supervision",
    "ai_hedge_management_handoff",
    "ai_hedge_management_execution",
    "emergency_controls",
    "autonomous_money_movement",
    "trade_path_diagnostics",
    "public_launch_gate",
    "ai_hedge_intelligence_layer",
    "tool_manifest",
)

SECTION_BUDGETS = {
    "your_recent_dial_changes": 1_000,
    "previous_context_delivery": 500,
    "operator_constitution": 1_300,
    "active_account_objective": 2_400,
    "profit_and_balance": 1_750,
    "primary_execution_truth": 1_650,
    "entry_opportunity_pipeline": 3_000,
    "learning_outcomes": 800,
    "outcome_binding": 1_000,
    "learning": 1_700,
    "adaptation": 1_100,
    "early_banking_analysis": 1_000,
    "trailing_stop_analysis": 900,
    "inherited_lessons": 2_800,
    "dials": 800,
    "dial_bounds": 1_100,
    "owner_guidance": 800,
    "recent_cycles": 500,
    "account_health": 1_300,
    "psychology_guard": 1_100,
    "auto_halt": 650,
    "broker_truth_monitor": 1_100,
    "ai_hedge_supervision": 1_400,
    "ai_hedge_management_handoff": 850,
    "ai_hedge_management_execution": 850,
    "emergency_controls": 900,
    "autonomous_money_movement": 900,
    "trade_path_diagnostics": 1_100,
    "public_launch_gate": 650,
    "ai_hedge_intelligence_layer": 600,
    "tool_manifest": 700,
}

SUPPORTING_SECTIONS = (
    "tool_manifest",
    "ai_hedge_intelligence_layer",
    "public_launch_gate",
    "trade_path_diagnostics",
)

FINAL_OPTIONAL_SECTIONS = (
    "previous_context_delivery",
    "tool_manifest",
    "ai_hedge_intelligence_layer",
    "trade_path_diagnostics",
    # A current BLOCK_PUBLIC_LAUNCH status is a hard stop, not decorative
    # context. Keep its compact projection until every other supporting
    # section has already been removed for size.
    "public_launch_gate",
)

_VOLATILE_HASH_KEYS = {
    "generated_at",
    "generated_at_iso",
    "updated_at",
    "cache_age_seconds",
    "cache_built_at_epoch",
    "cache_generated_at_iso",
    "cache_refreshing",
    "cache_stale",
}


def build_operator_context_packet(
    context: Mapping[str, Any],
    *,
    max_json_chars: int = DEFAULT_MAX_JSON_CHARS,
    critical_sections: tuple[str, ...] | None = None,
    required_section_profile: str = "scheduled_operator_tick",
) -> dict[str, Any]:
    """Project full runtime context into valid JSON without blind text slicing."""

    limit = max(MIN_MAX_JSON_CHARS, int(max_json_chars))
    required = tuple(critical_sections) if critical_sections is not None else CRITICAL_SECTIONS
    source = dict(context)
    source_chars = _json_len(source)
    projected: dict[str, Any] = {}
    summarized: list[str] = []

    for key in SECTION_ORDER:
        if key not in source:
            continue
        raw = source[key]
        section = _project_section(key, raw)
        fitted = _fit_value(section, SECTION_BUDGETS.get(key, 800))
        projected[key] = fitted
        if _json_len(fitted) < _json_len(raw):
            summarized.append(key)

    omitted = [key for key in source if key not in projected]
    packet: dict[str, Any] = {"context_delivery": {}, **projected}

    for key in SUPPORTING_SECTIONS:
        if _json_len(packet) <= limit:
            break
        if key in packet:
            packet.pop(key)
            omitted.append(key)

    compression_level = 1
    while _json_len(packet) > limit and compression_level <= 5:
        for key in reversed(SECTION_ORDER):
            if key not in packet or key == "context_delivery":
                continue
            packet[key] = _shrink_value(packet[key], compression_level)
            if _json_len(packet) <= limit:
                break
        compression_level += 1

    present = [key for key in required if key in packet]
    missing = [key for key in required if key not in packet]
    decision_grade = not missing
    section_fingerprints = {
        key: _fingerprint(packet[key]) for key in present
    }
    evidence_fingerprint = _fingerprint(
        {key: packet[key] for key in packet if key != "context_delivery"}
    )
    packet["context_delivery"] = {
        "report_kind": REPORT_KIND,
        "schema_version": SCHEMA_VERSION,
        "required_section_profile": str(required_section_profile),
        "decision_scope": (
            "OWNER_CHAT_EXPLANATION_NO_SIDE_EFFECTS"
            if required_section_profile == "fast_owner_chat"
            else "AUTONOMOUS_OPERATOR_TICK"
        ),
        "generated_at": utc_now().isoformat(),
        "status": "DECISION_GRADE_CONTEXT" if decision_grade else "INCOMPLETE_CRITICAL_CONTEXT",
        "decision_grade": decision_grade,
        "blind_character_slice_used": False,
        "raw_context_compacted": bool(summarized or omitted),
        "source_context_chars": source_chars,
        "max_packet_json_chars": limit,
        "packet_json_chars": 0,
        "source_section_count": len(source),
        "included_section_count": len(packet) - 1,
        "critical_section_count": len(required),
        "critical_sections_present": present,
        "critical_sections_missing": missing,
        "sections_summarized": _unique(summarized),
        "sections_omitted": _unique(omitted),
        "evidence_fingerprint": evidence_fingerprint,
        "critical_section_fingerprints": section_fingerprints,
        "instruction": (
            "When decision_grade is true, this packet is intentionally summarized "
            "and must not be described as truncated or missing. When it is false, "
            "hold dial changes that depend on the missing critical sections."
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    _stabilize_packet_size(packet)

    if _json_len(packet) > limit:
        for key in FINAL_OPTIONAL_SECTIONS:
            if key in packet:
                packet.pop(key)
                packet["context_delivery"]["sections_omitted"] = _unique(
                    [*packet["context_delivery"]["sections_omitted"], key]
                )
                if _json_len(packet) <= limit:
                    break
        _refresh_delivery_metadata(packet, required_sections=required)

    compression_level = 6
    while _json_len(packet) > limit and compression_level <= 12:
        for key in reversed(SECTION_ORDER):
            if key not in packet or key == "context_delivery":
                continue
            packet[key] = _shrink_value(packet[key], compression_level)
            if _json_len(packet) <= limit:
                break
        compression_level += 1
        _refresh_delivery_metadata(packet, required_sections=required)

    if _json_len(packet) > limit:
        packet["context_delivery"]["status"] = "INCOMPLETE_CRITICAL_CONTEXT"
        packet["context_delivery"]["decision_grade"] = False
        packet["context_delivery"]["budget_exhausted"] = True
        _stabilize_packet_size(packet)
    else:
        packet["context_delivery"].pop("budget_exhausted", None)
        _refresh_delivery_metadata(packet, required_sections=required)
    return packet


def serialize_operator_context_packet(packet: Mapping[str, Any]) -> str:
    return json.dumps(packet, ensure_ascii=True, separators=(",", ":"), default=str)


def _project_section(key: str, value: Any) -> Any:
    if key == "operator_constitution":
        return _project_constitution(value)
    if key == "active_account_objective":
        return _project_active_account_objective(value)
    if key == "profit_and_balance":
        return _project_profit(value)
    if key == "primary_execution_truth":
        return _project_primary_execution_truth(value)
    if key == "entry_opportunity_pipeline":
        return _project_entry_opportunity_pipeline(value)
    if key == "inherited_lessons":
        return _project_lessons(value)
    if key == "learning":
        return _project_learning(value)
    if key == "learning_outcomes":
        return _project_learning_outcomes(value)
    if key == "outcome_binding":
        return _project_outcome(value)
    if key == "adaptation":
        return _project_adaptation(value)
    if key in {"early_banking_analysis", "trailing_stop_analysis"}:
        return _project_exit_analysis(value)
    if key == "account_health":
        return _project_account_health(value)
    if key == "psychology_guard":
        return _project_psychology(value)
    if key == "broker_truth_monitor":
        return _project_broker_truth(value)
    if key == "ai_hedge_supervision":
        return _project_supervision(value)
    if key == "ai_hedge_management_handoff":
        return _pick(value, (
            "available", "status", "supervision_status", "price_source_status",
            "management_action_count", "blocked_action_count",
            "ready_for_guarded_execution", "broker_bound_action_authorized",
            "next_action", "management_actions", "blocked_actions", "scope",
            "authoritative_for_primary_dispatch", "interpretation",
        ))
    if key == "ai_hedge_management_execution":
        return _pick(value, (
            "available", "status", "broker_touched", "latest_status",
            "latest_generated_at_iso", "latest_action_id", "latest_method",
            "latest_symbol", "latest_ticket", "latest_stop_loss", "latest_volume",
            "latest_broker_result_status", "latest_terminal_receipt_status",
            "latest_post_execution_refresh_status", "latest_next_action",
        ))
    if key == "emergency_controls":
        return _project_emergency(value)
    if key == "autonomous_money_movement":
        return _project_money_movement(value)
    if key == "trade_path_diagnostics":
        return _project_trade_path(value)
    if key == "public_launch_gate":
        return _pick(value, (
            "available", "status", "launch_gate_status", "public_launch_status",
            "live_money_production_status", "hard_blockers", "next_action",
        ))
    if key == "ai_hedge_intelligence_layer":
        return _pick(value, (
            "available", "status", "primary_role", "edge_decisions",
            "allowed_intents", "hard_boundaries",
        ))
    if key == "tool_manifest":
        return _pick(value, (
            "mandatory_paths", "hard_blocks", "autonomous_authority_when_armed",
        ))
    if key == "previous_context_delivery":
        return _pick(value, (
            "status", "decision_grade", "generated_at", "evidence_fingerprint",
            "packet_json_chars", "critical_sections_missing",
        ))
    return value


def _project_constitution(value: Any) -> dict[str, Any]:
    text = str(value or "")
    lines = [line.strip().lstrip("- ") for line in text.splitlines() if line.strip()]
    directives: list[str] = []
    markers = (
        "authority boundary:", "primary objective:", "governing correction version:",
        "trading edge and autonomous execution layer", "once the owner has armed",
        "human-in-the-loop", "normal autonomous side effects", "hard blocks retained",
        "adaptive trading edge engine", "every broker-bound intent",
    )
    for line in lines:
        low = line.lower()
        if any(marker in low for marker in markers):
            clipped = _clip_text(line, 260)
            if clipped not in directives:
                directives.append(clipped)
        if len(directives) >= 9:
            break
    for line in lines[1:]:
        if len(directives) >= 9:
            break
        if line.startswith("#"):
            continue
        clipped = _clip_text(line, 260)
        if clipped not in directives:
            directives.append(clipped)
        if len(directives) >= 2:
            break
    version = next((line for line in lines if line.lower().startswith("version:")), None)
    source_hash = next((line for line in lines if line.lower().startswith("source sha-256:")), None)
    return {
        "present": bool(text),
        "source_chars": len(text),
        "title": _clip_text(lines[0], 160) if lines else None,
        "version": _clip_text(version, 120) if version else None,
        "source_sha256": _clip_text(source_hash, 120) if source_hash else None,
        "governing_directives": directives,
    }


def _project_profit(value: Any) -> dict[str, Any]:
    obj = _as_mapping(value)
    out = _pick(obj, (
        "objective", "scope", "authoritative_for_active_account", "interpretation",
        "daily_winnings_target_usd", "daily_cap_usd",
        "monthly_target_usd", "seed_capital_usd", "balance_growth_net_pnl_usd",
        "honest_paper_balance_usd", "honest_unique_signal_net_pnl_usd",
        "unique_signals", "unique_win_rate", "unique_profit_factor", "raw_net_pnl_usd",
        "raw_trades", "cluster_inflation_x", "biggest_cluster_size",
        "avg_winning_stack_depth", "avg_losing_stack_depth", "stacking_is_blind",
        "test_artifacts_quarantined", "test_artifacts_net_pnl_usd", "data_class",
        "daily_target_policy", "target_deficit_may_increase_risk",
    ))
    out["caveats"] = [_clip_text(item, 260) for item in (obj.get("caveats") or [])[:3]]
    return out


def _project_active_account_objective(value: Any) -> dict[str, Any]:
    obj = _as_mapping(value)
    growth = _as_mapping(obj.get("growth_measurement"))
    return {
        **_pick(obj, (
            "report_kind", "status", "objective_account_established",
            "authoritative_account_source",
        )),
        "execution": _pick(obj.get("execution"), (
            "running", "execution_active", "execution_lane", "mode",
            "bridge_class", "bridge_status",
        )),
        "current_account": _pick(obj.get("current_account"), (
            "login", "server", "currency", "is_demo", "balance_usd",
            "equity_usd", "floating_pnl_usd", "open_position_count",
            "position_price_pnl_usd", "open_swap_usd", "open_commission_usd",
            "reported_open_components_usd", "unattributed_open_pnl_usd",
        )),
        "growth_measurement": {
            **_pick(growth, (
                "balance_baseline_status", "current_balance_is_profit",
                "period_realized_status",
                "cashflow_adjusted_realized_growth_usd", "realized_today_usd",
                "realized_month_usd", "net_external_capital_flow_usd",
                "growth_pct_on_net_external_capital",
            )),
            "account_growth_reconciliation": _pick(
                growth.get("account_growth_reconciliation"),
                (
                    "status", "account_matches", "balance_matches", "reconciled",
                ),
            ),
            "cas_bound_closed_outcomes": _pick(
                growth.get("cas_bound_closed_outcomes"),
                ("status", "trades", "wins", "losses", "net_pnl_usd", "scope"),
            ),
            "open_pnl_decomposition": _pick(
                growth.get("open_pnl_decomposition"),
                (
                    "price_pnl_usd", "swap_or_carry_usd", "commission_usd",
                    "reported_components_usd", "account_net_open_pnl_usd",
                    "unattributed_open_pnl_usd", "interpretation",
                ),
            ),
        },
        "daily_objective": _pick(obj.get("daily_objective"), (
            "target_usd", "cap_usd", "monthly_target_usd", "policy",
            "target_deficit_may_manufacture_trade",
            "target_deficit_may_increase_risk", "cap_may_suppress_new_entries",
        )),
        "secondary_simulator_performance": _pick(
            obj.get("secondary_simulator_performance"),
            (
                "scope", "balance_usd", "balance_source",
                "performance_evidence_scope", "performance_evidence_balance_usd",
                "performance_evidence_net_pnl_usd", "net_pnl_usd",
                "unique_signal_net_pnl_usd", "authoritative_for_active_account",
                "relationship",
            ),
        ),
    }


def _project_primary_execution_truth(value: Any) -> dict[str, Any]:
    obj = _as_mapping(value)
    return {
        **_pick(
            obj,
            (
                "report_kind",
                "status",
                "primary_runtime_established",
                "paper_runtime_active",
                "conflict_count",
                "decision_rules",
            ),
        ),
        "authoritative_sources": _pick(
            obj.get("authoritative_sources"),
            (
                "broker_account_and_positions",
                "order_and_position_management",
                "live_readiness",
                "simulator_proof_only",
            ),
        ),
        "primary_runtime": _pick(
            obj.get("primary_runtime"),
            (
                "running",
                "execution_active",
                "execution_lane",
                "mode",
                "bridge_class",
                "bridge_status",
                "management_status",
                "management_detail",
                "management_broker_touched",
                "last_error",
            ),
        ),
        "broker_account": _pick(
            obj.get("broker_account"),
            (
                "connected",
                "is_demo",
                "open_position_count",
                "algo_allowed",
                "account",
            ),
        ),
        "secondary_diagnostics": _pick(
            obj.get("secondary_diagnostics"),
            (
                "movement_stream_supervision_status",
                "movement_stream_price_source_status",
                "movement_stream_handoff_status",
                "simulator_ledger_position_count",
                "live_readiness_monitor_running",
                "auto_halt_force_paper_mode",
            ),
        ),
        "conflicts": [
            _pick(row, ("code", "detail"))
            for row in (obj.get("conflicts") or [])[:6]
            if isinstance(row, Mapping)
        ],
    }


def _project_entry_opportunity_pipeline(value: Any) -> dict[str, Any]:
    """Preserve the candidate-stage facts the Operator needs to create edge."""

    obj = _as_mapping(value)
    runtime = _as_mapping(obj.get("multi_timeframe_scan_runtime"))
    return {
        **_pick(
            obj,
            (
                "report_kind",
                "generated_at",
                "status",
                "decision_rules",
                "broker_execution_touched",
                "orders_placed",
            ),
        ),
        "dispatch": _pick(
            obj.get("dispatch"),
            (
                "running",
                "execution_lane",
                "paper_learning_active",
                "eligible_symbol_count",
                "collected_intent_count",
                "filtered_intent_count",
                "risk_candidate_count",
                "risk_feasible_count",
                "operator_candidate_count",
                "entry_risk_status",
                "last_timeframe",
                "last_entry_lane",
                "bridge_class",
                "bridge_selection_status",
                "requested_mode",
                "mode",
            ),
        ),
        "current_scheduler_invocation": _pick(
            obj.get("current_scheduler_invocation"),
            (
                "status",
                "selected_timeframe",
                "entry_lane",
                "fresh_market_scan_performed",
                "route_scan_status",
                "route_source_status",
                "waste_market_scan_status",
                "market_attempt_count",
                "cache_remaining_seconds",
                "fresh_intent_count",
                "entry_stage_summary",
            ),
        ),
        "multi_timeframe_scan_runtime": {
            "strongest_rejected_lane": _pick(
                runtime.get("strongest_rejected_lane"),
                (
                    "symbol",
                    "timeframe",
                    "direction",
                    "directional_score",
                    "directional_floor",
                    "margin_to_floor",
                    "formation_status",
                    "shadow_edge_status",
                    "shadow_measured_win_prob",
                    "shadow_threshold",
                    "shadow_edge_preview_unregistered",
                    "shadow_edge_authorization_minted",
                    "shadow_has_edge_token",
                ),
            ),
            "best_shadow_pass_lane": _pick(
                runtime.get("best_shadow_pass_lane"),
                (
                    "symbol",
                    "timeframe",
                    "direction",
                    "directional_score",
                    "directional_floor",
                    "margin_to_floor",
                    "formation_status",
                    "shadow_edge_status",
                    "shadow_measured_win_prob",
                    "shadow_threshold",
                    "shadow_edge_preview_unregistered",
                    "shadow_edge_authorization_minted",
                    "shadow_has_edge_token",
                ),
            ),
            **_pick(
                runtime,
                (
                    "status",
                    "full_scan_lane_count",
                    "timeframes_observed",
                    "attempt_count",
                    "directional_candidate_count",
                    "edge_status_counts",
                    "candidate_formation_status_counts",
                    "shadow_edge_status_counts",
                    "shadow_pass_preview_count",
                    "all_observed_lanes_below_directional_floor",
                    "shadow_pass_selection_basis",
                    "broker_execution_touched",
                    "orders_placed",
                ),
            ),
            "latest_by_timeframe": runtime.get("latest_by_timeframe"),
        },
        "latest_route_source": _pick(
            obj.get("latest_route_source"),
            ("status", "symbol", "timeframe", "entry_lane", "blockers", "setup", "edge"),
        ),
        "entry_risk_preflight": _pick(
            obj.get("entry_risk_preflight"),
            (
                "status",
                "candidate_count",
                "feasible_count",
                "blocked_count",
                "unknown_count",
                "operator_candidate_count",
            ),
        ),
        "capacity_pressure": _pick(
            obj.get("capacity_pressure"),
            (
                "status",
                "cap_block_event_count",
                "distinct_symbol_count",
                "current_open_position_count",
                "current_max_open_position_count",
                "current_total_exposure_lots",
                "current_max_total_exposure_lots",
                "exposure_utilization_pct",
                "low_exposure_threshold_pct",
                "explicit_owner_override_active",
                "autonomous_one_slot_review_allowed",
                "recommended_review_cap",
                "current_cycle_candidate_count",
                "current_cycle_cap_only_block_count",
                "event_hash",
            ),
        ),
        "operator_adjustable_candidate_controls": _pick(
            obj.get("operator_adjustable_candidate_controls"),
            (
                "min_directional_confidence",
                "min_directional_confidence_bounds",
                "edge_threshold",
                "max_concurrent_trades",
                "max_concurrent_trades_bounds",
                "max_total_exposure_lots",
                "paper_learning_trades",
                "timeframes",
                "symbols",
            ),
        ),
    }


def _project_lessons(value: Any) -> dict[str, Any]:
    rows = [dict(row) for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []
    selected: list[dict[str, Any]] = []
    suppressed_delivery = 0
    seen: set[str] = set()
    for row in rows:
        lesson = str(row.get("lesson") or row.get("text") or "").strip()
        if not lesson:
            continue
        low = lesson.lower()
        delivery_lesson = (
            any(token in low for token in ("truncat", "incomplete", "missing fresh"))
            and any(token in low for token in ("tick", "context", "payload", "evidence packet"))
        )
        if delivery_lesson:
            suppressed_delivery += 1
            continue
        signature = " ".join(_normalize_words(lesson)[:12])
        if signature in seen:
            continue
        seen.add(signature)
        selected.append({
            "category": row.get("category"),
            "lesson": _clip_text(lesson, 340),
            "reinforced": row.get("reinforced", row.get("reinforced_count", 1)),
        })
        if len(selected) >= 9:
            break
    return {
        "source_count": len(rows),
        "included_count": len(selected),
        "repetitive_context_delivery_lessons_suppressed": suppressed_delivery,
        "lessons": selected,
    }


def _project_learning(value: Any) -> dict[str, Any]:
    obj = _as_mapping(value)
    out = _pick(obj, (
        "status", "cycles_loaded", "direction_rows", "confirmed_direction_count",
        "blocked_direction_count", "direction_counts", "edge_status_counts",
        "learning_ready_for_adaptation", "profile_recommendation", "next_action",
    ))
    groups = []
    raw_groups = obj.get("groups") or []
    if not isinstance(raw_groups, list):
        raw_groups = []
    for row in raw_groups[:4]:
        groups.append(_pick(row, (
            "symbol", "timeframe", "profile", "direction", "cycles",
            "confirmed_count", "blocked_count", "confirmed_rate",
            "avg_measured_win_prob", "avg_reward_r", "last_edge_status",
            "last_edge_reason", "broker_grade_count", "holdout_count",
        )))
    out["leading_groups"] = groups
    return out


def _project_outcome(value: Any) -> dict[str, Any]:
    obj = _as_mapping(value)
    out = _pick(obj, (
        "status", "paper_only", "outcome_ready_for_promotion",
        "grouping_basis", "ranking_basis", "pooled_profit_cannot_promote_group",
        "risk_normalized_ranking_required_for_promotion",
        "sample_ready_group_count", "risk_incomplete_sample_ready_group_count",
        "outcome_ready_group_count",
        "min_bound_outcomes_for_promotion", "confirmed_direction_count",
        "executed_confirmed_count", "closed_history_count", "bound_outcome_count",
        "unbound_confirmed_count", "bound_outcomes_needed", "profitable_bound_count",
        "losing_bound_count", "net_paper_pnl", "avg_bound_pnl",
        "paper_demo_history_status", "history_account_mode", "next_action",
    ))
    out["recommended_growth_group"] = _pick(obj.get("recommended_growth_group"), (
        "symbol", "timeframe", "direction", "profile", "trades", "wins", "losses",
        "win_rate", "net_pnl", "after_cost_expectancy",
        "after_cost_expectancy_r", "risk_normalized_trade_count",
        "risk_normalized_evidence_complete", "total_admission_stop_risk_usd",
        "net_pnl_per_dollar_admission_risk",
        "after_cost_expectancy_per_1_lot_usd", "lot_normalized_trade_count",
        "lot_normalized_evidence_complete", "profit_factor",
        "profit_factor_state", "sample_ready", "growth_positive_after_costs",
        "growth_positive_after_costs_per_risk_dollar",
        "promotion_blocked_by_incomplete_admission_risk",
        "outcome_ready_for_promotion", "last_close_time",
    ))
    return out


def _project_learning_outcomes(value: Any) -> dict[str, Any]:
    obj = _as_mapping(value)
    out = _pick(obj, (
        "marker", "read_only", "paper_only", "learning_ready", "group_learning_ready",
        "overall_sample_ready", "learning_ready_group_count",
        "min_samples_per_group", "grouping_basis", "ranking_basis",
        "risk_normalized_ranking_required_for_promotion",
        "win_rate_is_supporting_metric_only", "bound_trade_count",
        "closed_history_count", "group_count", "next_action",
    ))
    metric_keys = (
        "trades", "wins", "losses", "win_rate", "net_pnl",
        "after_cost_expectancy", "after_cost_expectancy_r",
        "risk_normalized_trade_count", "risk_normalized_evidence_complete",
        "total_admission_stop_risk_usd", "net_pnl_per_dollar_admission_risk",
        "stored_pre_trade_risk_mismatch_count",
        "after_cost_expectancy_per_1_lot_usd", "lot_normalized_trade_count",
        "lot_normalized_evidence_complete", "profit_factor",
    )
    out["overall"] = _pick(obj.get("overall"), metric_keys)
    for key in ("best_groups", "worst_groups"):
        raw_rows = obj.get(key) if isinstance(obj.get(key), list) else []
        out[key] = [
            _pick(
                row,
                (
                    "symbol", "timeframe", "direction", "profile",
                    "sample_ready", "outcome_ready_for_promotion",
                    *metric_keys,
                ),
            )
            for row in raw_rows[:3]
            if isinstance(row, Mapping)
        ]
    return out


def _project_adaptation(value: Any) -> dict[str, Any]:
    obj = _as_mapping(value)
    out = _pick(obj, (
        "status", "adaptation_ready_for_owner_review", "runtime_changed",
        "would_lower_edge_threshold", "would_enable_live_trading", "proposal_count",
        "next_action",
    ))
    out["learning_summary"] = _pick(obj.get("learning_summary"), (
        "status", "direction_rows", "confirmed_direction_count",
        "blocked_direction_count", "learning_ready_for_adaptation",
        "profile_recommendation_status",
    ))
    out["promotion_rule_summary"] = _pick(obj.get("promotion_rule_summary"), (
        "status", "promotion_ready_for_owner_review", "learning_ready_for_adaptation",
        "outcome_ready_for_promotion", "bound_outcome_count", "bound_outcomes_needed",
        "outcome_ready_group_count", "selection_basis",
        "proxy_recommendation_overridden_by_growth", "net_paper_pnl",
        "dominant_symbol", "dominant_timeframe", "dominant_profile", "dominant_direction",
        "next_action",
    ))
    out["latest_direction_summary"] = _pick(obj.get("latest_direction_summary"), (
        "status", "direction_edge_confirmed", "symbol", "timeframe", "direction",
        "score_margin", "edge_status", "edge_reason",
    ))
    return out


def _project_exit_analysis(value: Any) -> dict[str, Any]:
    return _pick(value, (
        "report_kind", "resolved_trades_with_mfe", "resolved_trades_with_trailing",
        "enough_data", "min_trades", "actual_net_pnl_hold_to_sl_tp", "winner_count",
        "avg_captured_fraction_of_peak", "best_policy", "verdict", "note", "caveats",
    ))


def _project_account_health(value: Any) -> dict[str, Any]:
    obj = _as_mapping(value)
    out = _pick(obj, (
        "status", "blockers", "scope", "authoritative_for_mt5_account", "interpretation",
    ))
    out["account"] = _pick(obj.get("account"), (
        "mode", "balance_usd", "equity_usd", "free_margin_usd", "realized_pnl_usd",
        "floating_pnl_usd", "drawdown_pct",
    ))
    out["closed_trade_performance"] = _pick(obj.get("closed_trade_performance"), (
        "closed_trade_count", "win_rate_pct", "profit_factor", "profit_factor_state",
        "expectancy_usd",
    ))
    out["open_exposure"] = _pick(obj.get("open_exposure"), (
        "open_position_count", "open_lots", "unprotected_position_count",
        "protective_order_coverage_pct", "open_risk_estimate_usd",
    ))
    out["source_health"] = _pick(obj.get("source_health"), (
        "price_source_status", "broker_ticket_position_count", "simulator_position_count",
        "provider_priced_simulator_position_count", "stale_price_position_count",
        "configured_market_data_provider", "provider_error_count", "attention_required",
        "detail",
    ))
    return out


def _project_psychology(value: Any) -> dict[str, Any]:
    obj = _as_mapping(value)
    return {
        "available": obj.get("available"),
        "daily_target_policy": obj.get("daily_target_policy"),
        "target_deficit_may_manufacture_trade": obj.get("target_deficit_may_manufacture_trade"),
        "target_deficit_may_increase_risk": obj.get("target_deficit_may_increase_risk"),
        "target_chasing_warning": _clip_text(obj.get("target_chasing_warning"), 260),
        "ai_dial": _pick(obj.get("ai_dial"), (
            "cooldown_active", "cooldown_remaining_seconds", "recent_loosen_count",
            "loosen_warning_limit", "warning_active", "journal_prompt_required",
            "last_loosened_at",
        )),
        "risk_caps": _pick(obj.get("risk_caps"), (
            "precedence", "explicit_owner_override_keys",
            "override_persistence_status", "override_persistence_load_error",
            "overrides_loaded_from_disk",
            "effective_max_open_position_count",
            "effective_max_positions_per_symbol",
            "effective_max_total_exposure_lots",
            "effective_max_risk_per_trade_pct",
            "effective_max_margin_utilization_pct",
            "effective_max_drawdown_pct_from_equity_peak",
            "effective_max_floating_loss_usd",
            "real_money_controls_armed", "typed_confirmation_required_on_loosen",
            "journal_required_on_loosen", "would_block_new_loosening",
            "cooldown_active", "cooldown_remaining_seconds", "last_loosened_at",
        )),
    }


def _project_broker_truth(value: Any) -> dict[str, Any]:
    return _pick(value, (
        "available", "status", "running", "monitor_status", "ready_for_live",
        "last_error", "mt5_connected", "mt5_is_demo", "mt5_open_position_count",
        "mt5_account", "mt5_account_server", "mt5_expected_account",
        "mt5_expected_server", "mt5_account_identity_matches_config",
        "overall_status", "auto_halt_latched_from_monitor",
        "position_protection_status", "position_protection_open_position_count",
        "position_protection_unprotected_position_count",
        "terminal_unmatched_open_position_count", "terminal_pending_receipt_count",
        "cas_receipt_pending_open_position_count", "terminal_account_snapshot_present",
        "terminal_reconciliation_status", "scope",
        "authoritative_for_primary_paper_execution", "interpretation", "next_action",
    ))


def _project_supervision(value: Any) -> dict[str, Any]:
    obj = _as_mapping(value)
    out = _pick(obj, (
        "available", "status", "movement_stream_id", "price_source_status",
        "static_simulation_active", "position_count", "action_recommendation_count",
        "high_urgency_count", "broker_bound_action_authorized", "next_action", "scope",
        "authoritative_for_primary_dispatch", "static_simulation_blocks_primary_dispatch",
        "interpretation",
    ))
    out["recommendations"] = [
        _pick(row, ("intent", "scope", "symbol", "urgency", "reason", "gate_path"))
        for row in (obj.get("recommendations") or [])[:4]
    ]
    out["positions"] = [
        _pick(row, (
            "symbol", "side", "r_multiple", "floating_pnl_usd", "price_source",
            "price_stale", "position_source_label",
        ))
        for row in (obj.get("positions") or [])[:6]
    ]
    return out


def _project_emergency(value: Any) -> dict[str, Any]:
    obj = _as_mapping(value)
    out = _pick(obj, (
        "available", "status", "automation_stop_ok", "broker_exposure_gap",
        "attention_items", "automation_stop_scope",
    ))
    out["controls"] = [
        _pick(row, ("key", "category", "status"))
        for row in (obj.get("controls") or [])[:10]
    ]
    return out


def _project_money_movement(value: Any) -> dict[str, Any]:
    obj = _as_mapping(value)
    return {
        **_pick(obj, (
            "report_kind", "autonomous_enabled", "policy_id", "destination_configured",
            "next_action",
        )),
        "payout_recovery": _pick(obj.get("payout_recovery"), (
            "attempt_count", "pending_count", "pending_amount_usd",
            "has_pending_recovery", "next_action",
        )),
        "provider_runtime": _pick(obj.get("provider_runtime"), (
            "requested_provider", "runtime_provider_name", "status", "detail",
            "supported_real_provider", "runtime_is_simulated",
            "real_money_provider_ready", "broker_account_bound", "custody_scope",
            "supported_actions",
        )),
    }


def _project_trade_path(value: Any) -> dict[str, Any]:
    obj = _as_mapping(value)
    return {
        "dispatch_loop": _pick(obj.get("dispatch_loop"), (
            "running", "desired_running", "interval_seconds", "symbols", "sessions",
            "last_summary", "last_error", "last_collected_intent_count",
            "last_filtered_intent_count", "last_target_warning", "mode",
            "last_symbol_targeting", "last_symbol_targeting_status",
            "last_effective_entry_symbols", "last_eligible_entry_symbols",
            "last_saturated_entry_symbols", "control_revision",
            "control_updated_at", "control_updated_by", "control_change_reason",
            "control_event_hash",
            "requested_mode", "execution_lane", "last_bridge_class",
            "last_bridge_selection_status", "last_management_status",
            "last_management_account_position_count",
            "last_management_primary_position_count",
            "last_management_simulator_handoff_position_count",
            "last_management_sources",
            "last_mt5_demo_learning_sync_status",
            "last_mt5_demo_learning_sync_at",
            "last_mt5_demo_learning_sync_error",
            "last_mt5_demo_learning_history_count",
            "last_mt5_demo_learning_bound_trade_count",
            "last_operator_trade_edge_status",
            "last_operator_trade_edge_at",
            "last_operator_trade_edge_provider",
            "last_operator_trade_edge_summary",
            "last_operator_trade_edge_candidate_count",
            "last_operator_trade_edge_approved_count",
            "last_operator_trade_edge_stand_down_count",
            "last_operator_trade_edge",
        )),
        "route_filter": _pick(obj.get("route_filter"), (
            "status", "collected_count", "kept_count", "filtered_count", "kept", "filtered",
        )),
        "live_candle_route_source": _pick(obj.get("live_candle_route_source"), (
            "status", "symbol", "timeframe", "broker_grade_market_truth", "blockers",
            "setup", "edge",
        )),
        "mt5_symbol_diagnostic": _pick(obj.get("mt5_symbol_diagnostic"), (
            "status", "ready_symbol_count", "checked_symbol_count", "next_action", "symbols",
        )),
    }


def _pick(value: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    obj = _as_mapping(value)
    return {key: obj.get(key) for key in keys if key in obj}


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _fit_value(value: Any, budget: int) -> Any:
    if _json_len(value) <= budget:
        return value
    for level in range(1, 7):
        fitted = _shrink_value(value, level)
        if _json_len(fitted) <= budget:
            return fitted
    return {
        "status": "COMPACTED_TO_SECTION_BUDGET",
        "source_type": type(value).__name__,
        "source_chars": _json_len(value),
        "summary": _clip_text(_scalar_summary(value), max(80, budget - 160)),
    }


def _shrink_value(value: Any, level: int) -> Any:
    string_limit = max(80, 360 // max(1, level))
    list_limit = max(1, 8 // max(1, level))
    dict_limit = max(6, 28 // max(1, level))
    if isinstance(value, str):
        return _clip_text(value, string_limit)
    if isinstance(value, list):
        return {
            "items": [_shrink_value(item, level + 1) for item in value[:list_limit]],
            "source_count": len(value),
            "omitted_count": max(0, len(value) - list_limit),
        }
    if isinstance(value, Mapping):
        items = list(value.items())
        scalar = [(key, item) for key, item in items if not isinstance(item, (Mapping, list))]
        nested = [(key, item) for key, item in items if isinstance(item, (Mapping, list))]
        out: dict[str, Any] = {}
        for key, item in [*scalar, *nested][:dict_limit]:
            out[str(key)] = _shrink_value(item, level + 1)
        if len(items) > len(out):
            out["_omitted_key_count"] = len(items) - len(out)
        return out
    return value


def _scalar_summary(value: Any) -> str:
    if isinstance(value, Mapping):
        scalar = [f"{key}={item}" for key, item in value.items() if not isinstance(item, (Mapping, list))]
        return "; ".join(scalar[:10]) or f"mapping with {len(value)} keys"
    if isinstance(value, list):
        return f"list with {len(value)} items"
    return str(value)


def _clip_text(value: Any, limit: int) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 18)].rstrip() + " [summarized]"


def _normalize_words(value: str) -> list[str]:
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in value.lower())
    return cleaned.split()


def _stable_for_hash(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _stable_for_hash(item)
            for key, item in value.items()
            if str(key) not in _VOLATILE_HASH_KEYS
        }
    if isinstance(value, list):
        return [_stable_for_hash(item) for item in value]
    return value


def _fingerprint(value: Any) -> str:
    stable = json.dumps(
        _stable_for_hash(value),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()[:24]


def _json_len(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=True, separators=(",", ":"), default=str))


def _stabilize_packet_size(packet: dict[str, Any]) -> None:
    delivery = packet.get("context_delivery")
    if not isinstance(delivery, dict):
        return
    for _ in range(4):
        current = _json_len(packet)
        if delivery.get("packet_json_chars") == current:
            return
        delivery["packet_json_chars"] = current


def _refresh_delivery_metadata(
    packet: dict[str, Any],
    *,
    required_sections: tuple[str, ...] = CRITICAL_SECTIONS,
) -> None:
    delivery = packet.get("context_delivery")
    if not isinstance(delivery, dict):
        return
    present = [key for key in required_sections if key in packet]
    missing = [key for key in required_sections if key not in packet]
    decision_grade = not missing
    delivery["status"] = (
        "DECISION_GRADE_CONTEXT" if decision_grade else "INCOMPLETE_CRITICAL_CONTEXT"
    )
    delivery["decision_grade"] = decision_grade
    delivery["included_section_count"] = len(packet) - 1
    delivery["critical_section_count"] = len(required_sections)
    delivery["critical_sections_present"] = present
    delivery["critical_sections_missing"] = missing
    delivery["critical_section_fingerprints"] = {
        key: _fingerprint(packet[key]) for key in present
    }
    delivery["evidence_fingerprint"] = _fingerprint(
        {key: packet[key] for key in packet if key != "context_delivery"}
    )
    _stabilize_packet_size(packet)


def _unique(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


__all__ = [
    "CLAIM_BOUNDARY",
    "CRITICAL_SECTIONS",
    "FAST_CHAT_CRITICAL_SECTIONS",
    "DEFAULT_MAX_JSON_CHARS",
    "REPORT_KIND",
    "SCHEMA_VERSION",
    "build_operator_context_packet",
    "serialize_operator_context_packet",
]
