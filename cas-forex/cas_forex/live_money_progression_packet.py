"""Single fail-closed packet for CAS Forex live-money progression.

This is an owner-readable synthesis layer. It does not decide trades, touch a
broker, approve live authority, or move money. It only answers: what still keeps
CAS Forex from progressing through live dispatch, WASTE pilot, and verified
profit payout?
"""

from __future__ import annotations

from typing import Any, Mapping

from cas_forex.time_utils import utc_now

REPORT_KIND = "cas_forex_live_money_progression_packet"
STATUS_BLOCKED = "LIVE_MONEY_PROGRESS_BLOCKED"
STATUS_READY_FOR_OWNER_REVIEW = "LIVE_MONEY_PROGRESS_READY_FOR_OWNER_REVIEW"

CLAIM_BOUNDARY = (
    "Live-money progression packet is a read-only synthesis of runtime gates, "
    "broker truth, live recovery, WASTE pilot readiness, verified-profit sweep, "
    "and payout recovery. It does not place orders, close positions, create "
    "broker ACCEPT, create owner ACCEPT, authorize live trading, mint edge "
    "tokens, deposit, withdraw, move bank/card money, automate payouts, or mark "
    "evidence LICENSED."
)


def build_live_money_progression_packet(
    *,
    runtime_gates: Mapping[str, Any] | None = None,
    broker_truth_packet: Mapping[str, Any] | None = None,
    live_recovery_report: Mapping[str, Any] | None = None,
    waste_pilot_promotion: Mapping[str, Any] | None = None,
    waste_direction_review: Mapping[str, Any] | None = None,
    waste_direction_learning: Mapping[str, Any] | None = None,
    waste_direction_outcome_binding: Mapping[str, Any] | None = None,
    waste_adaptation_promotion_rule: Mapping[str, Any] | None = None,
    waste_adaptation_plan: Mapping[str, Any] | None = None,
    waste_adaptation_apply_preview: Mapping[str, Any] | None = None,
    waste_adaptation_owner_review: Mapping[str, Any] | None = None,
    waste_adaptation_paper_apply: Mapping[str, Any] | None = None,
    sweep_preview: Mapping[str, Any] | None = None,
    payout_recovery_status: Mapping[str, Any] | None = None,
    live_readiness_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact owner packet without causing broker or payout side effects."""

    runtime = dict(runtime_gates) if runtime_gates is not None else _runtime_gates()
    broker_truth = (
        dict(broker_truth_packet)
        if broker_truth_packet is not None
        else _broker_truth_packet()
    )
    recovery = (
        dict(live_recovery_report)
        if live_recovery_report is not None
        else _live_recovery_report()
    )
    pilot = (
        dict(waste_pilot_promotion)
        if waste_pilot_promotion is not None
        else _waste_pilot_promotion()
    )
    direction_review = (
        dict(waste_direction_review)
        if waste_direction_review is not None
        else _waste_direction_review()
    )
    direction_learning = (
        dict(waste_direction_learning)
        if waste_direction_learning is not None
        else _waste_direction_learning()
    )
    direction_outcome_binding = (
        dict(waste_direction_outcome_binding)
        if waste_direction_outcome_binding is not None
        else _waste_direction_outcome_binding()
    )
    adaptation_promotion_rule = (
        dict(waste_adaptation_promotion_rule)
        if waste_adaptation_promotion_rule is not None
        else _waste_adaptation_promotion_rule()
    )
    adaptation_plan = (
        dict(waste_adaptation_plan)
        if waste_adaptation_plan is not None
        else _waste_adaptation_plan()
    )
    adaptation_preview = (
        dict(waste_adaptation_apply_preview)
        if waste_adaptation_apply_preview is not None
        else _waste_adaptation_apply_preview()
    )
    adaptation_owner_review = (
        dict(waste_adaptation_owner_review)
        if waste_adaptation_owner_review is not None
        else _waste_adaptation_owner_review()
    )
    adaptation_paper_apply = (
        dict(waste_adaptation_paper_apply)
        if waste_adaptation_paper_apply is not None
        else _waste_adaptation_paper_apply()
    )
    sweep = dict(sweep_preview) if sweep_preview is not None else _sweep_preview()
    payout_recovery = (
        dict(payout_recovery_status)
        if payout_recovery_status is not None
        else _payout_recovery_status()
    )
    readiness = (
        dict(live_readiness_report)
        if live_readiness_report is not None
        else _live_readiness_report()
    )

    decisions = runtime.get("decisions") if isinstance(runtime.get("decisions"), Mapping) else {}
    live_gate = _decision(decisions, "live_trading")
    broker_accept_gate = _decision(decisions, "broker_accept")
    payout_gate = _decision(decisions, "payout_automation")
    sweep_payout_gate = (
        sweep.get("payout_gate")
        if isinstance(sweep.get("payout_gate"), Mapping)
        else {}
    )
    winnings = sweep.get("winnings") if isinstance(sweep.get("winnings"), Mapping) else {}

    live_dispatch_clear = (
        bool(live_gate.get("authorized", False))
        and bool(broker_truth.get("broker_truth_clear_for_live_recovery", False))
        and bool(recovery.get("recovery_clear_for_live", False))
    )
    direction_clear = bool(direction_review.get("direction_edge_confirmed", False))
    waste_pilot_clear = (
        live_dispatch_clear
        and direction_clear
        and bool(pilot.get("ready_for_pilot_sequence", False))
    )
    # A crashed payout-recovery builder yields _unavailable() - a dict WITHOUT
    # has_pending_recovery - and `not .get(..., False)` would read that crash
    # as "no pending recovery". Same fail-open family as the readiness gate
    # below: an unevaluable recovery status is NOT clear.
    payout_recovery_evaluable = (
        str(payout_recovery.get("status") or "") != "UNAVAILABLE"
        and "has_pending_recovery" in payout_recovery
    )
    payout_recovery_clear = payout_recovery_evaluable and not bool(
        payout_recovery.get("has_pending_recovery", False)
    )
    verified_payout_clear = (
        bool(payout_gate.get("authorized", False))
        and bool(sweep_payout_gate.get("authorized", False))
        and str(sweep.get("status") or "") == "READY"
        and str(winnings.get("claim_status") or "") == "SWEEPABLE"
        and payout_recovery_clear
    )
    # Fail CLOSED when the readiness report is missing: `not readiness` used to
    # count an unbuildable checklist as clear, so a crash in the readiness
    # builder cleared the live-money blocker. A gate that cannot be evaluated
    # is not passed.
    live_readiness_clear = (
        str(readiness.get("overall_status") or "") == "READY_FOR_LIVE_EXECUTION"
    )

    direction_summary = (
        direction_review.get("direction_summary")
        if isinstance(direction_review.get("direction_summary"), Mapping)
        else {}
    )
    blockers: list[dict[str, Any]] = []
    _add_blocker(
        blockers,
        "runtime_live_trading_authorized",
        "live_dispatch",
        bool(live_gate.get("authorized", False)),
        _gate_value(live_gate),
        "Runtime live-trading gate is not AUTHORIZED.",
        live_gate.get("next_action"),
    )
    _add_blocker(
        blockers,
        "broker_truth_clear_for_live_recovery",
        "broker_truth",
        bool(broker_truth.get("broker_truth_clear_for_live_recovery", False)),
        {
            "status": broker_truth.get("status"),
            "blocker_count": len(broker_truth.get("blockers") or []),
        },
        "Broker truth is not clear for live recovery.",
        broker_truth.get("next_action"),
    )
    _add_blocker(
        blockers,
        "live_recovery_clear_for_live",
        "live_recovery",
        bool(recovery.get("recovery_clear_for_live", False)),
        {
            "recovery_status": recovery.get("recovery_status"),
            "missing_requirements": recovery.get("missing_requirements") or [],
        },
        "Live crash/disconnect recovery is not CLEAR.",
        recovery.get("next_action"),
    )
    _add_blocker(
        blockers,
        "runtime_broker_accept_authorized",
        "live_dispatch",
        bool(broker_accept_gate.get("authorized", False)),
        _gate_value(broker_accept_gate),
        "Broker ACCEPT creation is not AUTHORIZED.",
        broker_accept_gate.get("next_action"),
    )
    _add_blocker(
        blockers,
        "waste_direction_edge_confirmed",
        "directional_edge",
        direction_clear,
        {
            "status": direction_review.get("status"),
            "direction_summary": direction_review.get("direction_summary") or {},
            "edge_gate_summary": direction_review.get("edge_gate_summary") or {},
            "blocker_count": len(direction_review.get("blockers") or []),
        },
        "WASTE LONG/SHORT direction is not confirmed by the edge gate.",
        direction_review.get("next_action"),
    )
    _add_blocker(
        blockers,
        "waste_pilot_ready_for_sequence",
        "waste_pilot",
        bool(pilot.get("ready_for_pilot_sequence", False)),
        {
            "status": pilot.get("status"),
            "symbol": pilot.get("symbol"),
            "direction": pilot.get("direction"),
            "entry_pair_count": pilot.get("entry_pair_count"),
            "missing_requirements": pilot.get("missing_requirements") or [],
        },
        "WASTE candidate is not ready for the owner-controlled pilot sequence.",
        pilot.get("next_action"),
    )
    _add_blocker(
        blockers,
        "runtime_payout_automation_authorized",
        "verified_payout",
        bool(payout_gate.get("authorized", False)),
        _gate_value(payout_gate),
        "Runtime payout-automation gate is not AUTHORIZED.",
        payout_gate.get("next_action"),
    )
    _add_blocker(
        blockers,
        "verified_profit_sweep_ready",
        "verified_payout",
        str(sweep.get("status") or "") == "READY"
        and str(winnings.get("claim_status") or "") == "SWEEPABLE",
        {
            "preview_status": sweep.get("status"),
            "claim_status": winnings.get("claim_status"),
            "sweepable_winnings_usd": winnings.get("sweepable_winnings_usd"),
            "sweep_amount_usd": sweep.get("sweep_amount_usd"),
        },
        "Verified-profit sweep is not READY from broker-confirmed live net winnings.",
        sweep.get("reason"),
    )
    _add_blocker(
        blockers,
        "payout_recovery_clear",
        "verified_payout",
        payout_recovery_clear,
        {
            "pending_count": payout_recovery.get("pending_count", 0),
            "latest_attempt": payout_recovery.get("latest_attempt"),
            "recovery_status": payout_recovery.get("status") or (
                "REPORT_UNAVAILABLE" if not payout_recovery_evaluable else None
            ),
        },
        (
            "Payout recovery has pending attempts that must be owner-resolved."
            if payout_recovery_evaluable
            else "Payout recovery status could not be built; an unevaluable gate is not a passed gate."
        ),
        payout_recovery.get("next_action"),
    )
    # Registered unconditionally: an EMPTY readiness report (builder crashed or
    # unavailable) must surface as a blocker, not vanish. Previously this whole
    # block sat behind `if readiness:` - the packet could report
    # READY_FOR_OWNER_REVIEW precisely because the readiness gate could not be
    # evaluated.
    _add_blocker(
        blockers,
        "live_readiness_ready_for_live_execution",
        "live_readiness",
        live_readiness_clear,
        {
            "overall_status": readiness.get("overall_status") or "REPORT_UNAVAILABLE",
            "checks_open": readiness.get("checks_open"),
            "checks_mismatch": readiness.get("checks_mismatch"),
            "checks_currently_not_licensed": readiness.get("checks_currently_not_licensed"),
        },
        (
            "The plain-English live readiness checklist is not ready for live execution."
            if readiness
            else "The live readiness checklist could not be built; an unevaluable gate is not a passed gate."
        ),
        _first(readiness.get("next_actions"))
        or (None if readiness else "Repair the live-readiness builder, then re-run this packet."),
    )

    status = STATUS_READY_FOR_OWNER_REVIEW if not blockers else STATUS_BLOCKED
    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "live_dispatch_clear": live_dispatch_clear,
        "waste_pilot_clear": waste_pilot_clear,
        "verified_payout_clear": verified_payout_clear,
        "full_progression_clear": not blockers,
        "broker_truth_clear": bool(broker_truth.get("broker_truth_clear_for_live_recovery", False)),
        "live_recovery_clear": bool(recovery.get("recovery_clear_for_live", False)),
        "live_readiness_clear": live_readiness_clear,
        "broker_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "edge_token_minted": False,
        "owner_accept_created": False,
        "money_moved": False,
        "active_waste_intent": {
            "symbol": pilot.get("symbol") or direction_summary.get("symbol"),
            "direction": pilot.get("direction") or direction_summary.get("direction"),
            "lots": pilot.get("lots"),
            "entry_pair_count": pilot.get("entry_pair_count") or direction_summary.get("entry_pair_count"),
            "status": pilot.get("status") or direction_review.get("status"),
        },
        "source_summaries": {
            "runtime_gates": _runtime_summary(runtime),
            "broker_truth": _broker_truth_summary(broker_truth),
            "live_recovery": _live_recovery_summary(recovery),
            "waste_direction": _waste_direction_summary(direction_review),
            "waste_direction_learning": _waste_direction_learning_summary(direction_learning),
            "waste_direction_outcome_binding": _waste_direction_outcome_binding_summary(direction_outcome_binding),
            "waste_adaptation_promotion_rule": _waste_adaptation_promotion_rule_summary(adaptation_promotion_rule),
            "waste_adaptation_plan": _waste_adaptation_summary(adaptation_plan),
            "waste_adaptation_apply_preview": _waste_adaptation_apply_preview_summary(adaptation_preview),
            "waste_adaptation_owner_review": _waste_adaptation_owner_review_summary(adaptation_owner_review),
            "waste_adaptation_paper_apply": _waste_adaptation_paper_apply_summary(adaptation_paper_apply),
            "waste_pilot": _waste_pilot_summary(pilot),
            "verified_profit_sweep": _sweep_summary(sweep),
            "payout_recovery": _payout_recovery_summary(payout_recovery),
            "live_readiness": _readiness_summary(readiness),
        },
        "blocker_count": len(blockers),
        "blockers": blockers,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(blockers),
    }


def _runtime_gates() -> dict[str, Any]:
    try:
        from cas_forex.runtime_gates import build_runtime_gates_report

        return build_runtime_gates_report().to_dict()
    except Exception as exc:
        return _unavailable("cas_forex_runtime_gates", exc)


def _broker_truth_packet() -> dict[str, Any]:
    try:
        from cas_forex.broker_truth_recovery_packet import build_broker_truth_recovery_packet

        return build_broker_truth_recovery_packet()
    except Exception as exc:
        return _unavailable("cas_forex_broker_truth_recovery_packet", exc)


def _live_recovery_report() -> dict[str, Any]:
    try:
        from cas_forex.live_recovery import build_live_recovery_report

        return build_live_recovery_report()
    except Exception as exc:
        return _unavailable("cas_forex_live_recovery_review", exc)


def _waste_pilot_promotion() -> dict[str, Any]:
    try:
        from cas_forex.live_order_dry_run import DEFAULT_AUDIT_PATH, LiveOrderDryRunAuditLog
        from cas_forex.waste_pilot_promotion import build_waste_pilot_promotion_status

        latest = LiveOrderDryRunAuditLog(DEFAULT_AUDIT_PATH).latest()
        return build_waste_pilot_promotion_status(dry_run_audit=latest or {})
    except Exception as exc:
        return _unavailable("cas_forex_waste_pilot_promotion", exc)


def _waste_direction_review() -> dict[str, Any]:
    try:
        from cas_forex.waste_direction_review_packet import build_waste_direction_review_packet

        return build_waste_direction_review_packet()
    except Exception as exc:
        return _unavailable("cas_forex_waste_direction_review_packet", exc)


def _waste_direction_learning() -> dict[str, Any]:
    try:
        from cas_forex.waste_direction_learning_ledger import build_waste_direction_learning_ledger

        return build_waste_direction_learning_ledger()
    except Exception as exc:
        return _unavailable("cas_forex_waste_direction_learning_ledger", exc)


def _waste_direction_outcome_binding() -> dict[str, Any]:
    try:
        from cas_forex.waste_direction_outcome_binding import build_waste_direction_outcome_binding

        return build_waste_direction_outcome_binding()
    except Exception as exc:
        return _unavailable("cas_forex_waste_direction_outcome_binding", exc)


def _waste_adaptation_promotion_rule() -> dict[str, Any]:
    try:
        from cas_forex.waste_adaptation_promotion_rule import build_waste_adaptation_promotion_rule

        return build_waste_adaptation_promotion_rule()
    except Exception as exc:
        return _unavailable("cas_forex_waste_adaptation_promotion_rule", exc)


def _waste_adaptation_plan() -> dict[str, Any]:
    try:
        from cas_forex.waste_adaptation_plan import build_waste_adaptation_plan

        return build_waste_adaptation_plan()
    except Exception as exc:
        return _unavailable("cas_forex_waste_adaptation_plan", exc)


def _waste_adaptation_apply_preview() -> dict[str, Any]:
    try:
        from cas_forex.waste_adaptation_apply_preview import build_waste_adaptation_apply_preview

        return build_waste_adaptation_apply_preview()
    except Exception as exc:
        return _unavailable("cas_forex_waste_adaptation_apply_preview", exc)


def _waste_adaptation_owner_review() -> dict[str, Any]:
    try:
        from cas_forex.waste_adaptation_owner_review import build_waste_adaptation_owner_review

        return build_waste_adaptation_owner_review()
    except Exception as exc:
        return _unavailable("cas_forex_waste_adaptation_owner_review", exc)


def _waste_adaptation_paper_apply() -> dict[str, Any]:
    try:
        from cas_forex.waste_adaptation_paper_apply import build_waste_adaptation_paper_apply_status

        return build_waste_adaptation_paper_apply_status()
    except Exception as exc:
        return _unavailable("cas_forex_waste_adaptation_paper_apply", exc)


def _sweep_preview() -> dict[str, Any]:
    try:
        from api.data import verified_profit_account_ledger
        from cas_forex.verified_profit_sweep import ProfitSweepPolicyStore, build_sweep_preview

        return build_sweep_preview(verified_profit_account_ledger(), ProfitSweepPolicyStore().load()).to_dict()
    except Exception as exc:
        return _unavailable("cas_forex_verified_profit_sweep_preview", exc)


def _payout_recovery_status() -> dict[str, Any]:
    try:
        from cas_forex.payout_recovery import build_payout_recovery_status

        return build_payout_recovery_status()
    except Exception as exc:
        return _unavailable("cas_forex_payout_recovery", exc)


def _live_readiness_report() -> dict[str, Any]:
    try:
        from api.data import live_readiness

        return live_readiness()
    except Exception:
        return {}


def _decision(decisions: Mapping[str, Any], capability: str) -> dict[str, Any]:
    value = decisions.get(capability) if isinstance(decisions, Mapping) else None
    return dict(value) if isinstance(value, Mapping) else {}


def _gate_value(gate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "authorized": bool(gate.get("authorized", False)),
        "status": gate.get("status"),
        "missing_requirements": gate.get("missing_requirements") or [],
    }


def _add_blocker(
    out: list[dict[str, Any]],
    blocker_id: str,
    plane: str,
    clear: bool,
    value: Any,
    detail: str,
    next_action: Any = None,
) -> None:
    if clear:
        return
    out.append(
        {
            "blocker_id": blocker_id,
            "plane": plane,
            "clear": False,
            "value": value,
            "detail": detail,
            "next_action": str(next_action or "").strip(),
        }
    )


def _runtime_summary(runtime: Mapping[str, Any]) -> dict[str, Any]:
    decisions = runtime.get("decisions") if isinstance(runtime.get("decisions"), Mapping) else {}
    return {
        "all_real_money_authorized": bool(runtime.get("all_real_money_authorized", False)),
        "live_trading": _gate_value(_decision(decisions, "live_trading")),
        "broker_accept": _gate_value(_decision(decisions, "broker_accept")),
        "payout_automation": _gate_value(_decision(decisions, "payout_automation")),
        "summary": runtime.get("summary"),
    }


def _broker_truth_summary(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": packet.get("status"),
        "broker_truth_clear_for_live_recovery": bool(
            packet.get("broker_truth_clear_for_live_recovery", False)
        ),
        "blocker_count": len(packet.get("blockers") or []),
        "monitor_summary": packet.get("monitor_summary") or {},
        "next_action": packet.get("next_action"),
    }


def _live_recovery_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "recovery_status": report.get("recovery_status"),
        "recovery_clear_for_live": bool(report.get("recovery_clear_for_live", False)),
        "requires_recovery_review": bool(report.get("requires_recovery_review", False)),
        "missing_requirements": report.get("missing_requirements") or [],
        "next_action": report.get("next_action"),
    }


def _waste_pilot_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status"),
        "ready_for_pilot_sequence": bool(report.get("ready_for_pilot_sequence", False)),
        "symbol": report.get("symbol"),
        "direction": report.get("direction"),
        "lots": report.get("lots"),
        "entry_pair_count": report.get("entry_pair_count"),
        "missing_requirements": report.get("missing_requirements") or [],
        "next_action": report.get("next_action"),
    }


def _waste_direction_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    direction = (
        report.get("direction_summary")
        if isinstance(report.get("direction_summary"), Mapping)
        else {}
    )
    edge = (
        report.get("edge_gate_summary")
        if isinstance(report.get("edge_gate_summary"), Mapping)
        else {}
    )
    profit_box = (
        report.get("profit_box")
        if isinstance(report.get("profit_box"), Mapping)
        else {}
    )
    return {
        "status": report.get("status"),
        "direction_edge_confirmed": bool(report.get("direction_edge_confirmed", False)),
        "symbol": direction.get("symbol"),
        "timeframe": direction.get("timeframe"),
        "direction": direction.get("direction"),
        "opposite_direction": direction.get("opposite_direction"),
        "chosen_score": direction.get("chosen_score"),
        "opposite_score": direction.get("opposite_score"),
        "score_margin": direction.get("score_margin"),
        "entry_pair_count": direction.get("entry_pair_count"),
        "edge_status": edge.get("status"),
        "has_edge_token": edge.get("has_edge_token"),
        "reward_r": profit_box.get("reward_r"),
        "blocker_count": len(report.get("blockers") or []),
        "next_action": report.get("next_action"),
    }


def _waste_direction_learning_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    recommendation = (
        report.get("profile_recommendation")
        if isinstance(report.get("profile_recommendation"), Mapping)
        else {}
    )
    dominant = (
        recommendation.get("dominant_observed_group")
        if isinstance(recommendation.get("dominant_observed_group"), Mapping)
        else recommendation.get("recommended_group")
        if isinstance(recommendation.get("recommended_group"), Mapping)
        else {}
    )
    return {
        "status": report.get("status"),
        "direction_rows": report.get("direction_rows"),
        "confirmed_direction_count": report.get("confirmed_direction_count"),
        "blocked_direction_count": report.get("blocked_direction_count"),
        "learning_ready_for_adaptation": bool(report.get("learning_ready_for_adaptation", False)),
        "direction_counts": report.get("direction_counts") or {},
        "edge_status_counts": report.get("edge_status_counts") or {},
        "profile_recommendation_status": recommendation.get("status"),
        "dominant_symbol": dominant.get("symbol"),
        "dominant_timeframe": dominant.get("timeframe"),
        "dominant_profile": dominant.get("profile"),
        "dominant_direction": dominant.get("direction"),
        "dominant_cycles": dominant.get("cycles"),
        "dominant_confirmed_count": dominant.get("confirmed_count"),
        "next_action": report.get("next_action"),
    }


def _waste_direction_outcome_binding_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status"),
        "dry_run": bool(report.get("dry_run", False)),
        "read_only": bool(report.get("read_only", False)),
        "paper_only": bool(report.get("paper_only", False)),
        "outcome_ready_for_promotion": bool(report.get("outcome_ready_for_promotion", False)),
        "min_bound_outcomes_for_promotion": report.get("min_bound_outcomes_for_promotion"),
        "confirmed_direction_count": report.get("confirmed_direction_count"),
        "executed_confirmed_count": report.get("executed_confirmed_count"),
        "closed_history_count": report.get("closed_history_count"),
        "bound_outcome_count": report.get("bound_outcome_count"),
        "unbound_confirmed_count": report.get("unbound_confirmed_count"),
        "bound_outcomes_needed": report.get("bound_outcomes_needed"),
        "profitable_bound_count": report.get("profitable_bound_count"),
        "losing_bound_count": report.get("losing_bound_count"),
        "net_paper_pnl": report.get("net_paper_pnl"),
        "runtime_changed": bool(report.get("runtime_changed", False)),
        "would_enable_live_trading": bool(report.get("would_enable_live_trading", False)),
        "money_moved": bool(report.get("money_moved", False)),
        "next_action": report.get("next_action"),
    }


def _waste_adaptation_promotion_rule_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    dominant = (
        report.get("recommended_group")
        if isinstance(report.get("recommended_group"), Mapping)
        else report.get("dominant_group")
        if isinstance(report.get("dominant_group"), Mapping)
        else {}
    )
    return {
        "status": report.get("status"),
        "dry_run": bool(report.get("dry_run", False)),
        "read_only": bool(report.get("read_only", False)),
        "promotion_ready_for_owner_review": bool(report.get("promotion_ready_for_owner_review", False)),
        "learning_ready_for_adaptation": bool(report.get("learning_ready_for_adaptation", False)),
        "outcome_ready_for_promotion": bool(report.get("outcome_ready_for_promotion", False)),
        "min_confirmed_for_adaptation": report.get("min_confirmed_for_adaptation"),
        "confirmed_direction_count": report.get("confirmed_direction_count"),
        "confirmed_samples_needed": report.get("confirmed_samples_needed"),
        "bound_outcome_count": report.get("bound_outcome_count"),
        "bound_outcomes_needed": report.get("bound_outcomes_needed"),
        "net_paper_pnl": report.get("net_paper_pnl"),
        "blocked_direction_count": report.get("blocked_direction_count"),
        "direction_rows": report.get("direction_rows"),
        "profile_recommendation_status": report.get("profile_recommendation_status"),
        "dominant_symbol": dominant.get("symbol"),
        "dominant_timeframe": dominant.get("timeframe"),
        "dominant_profile": dominant.get("profile"),
        "dominant_direction": dominant.get("direction"),
        "runtime_changed": bool(report.get("runtime_changed", False)),
        "would_enable_live_trading": bool(report.get("would_enable_live_trading", False)),
        "money_moved": bool(report.get("money_moved", False)),
        "next_action": report.get("next_action"),
    }


def _waste_adaptation_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    learning = (
        report.get("learning_summary")
        if isinstance(report.get("learning_summary"), Mapping)
        else {}
    )
    latest = (
        report.get("latest_direction_summary")
        if isinstance(report.get("latest_direction_summary"), Mapping)
        else {}
    )
    return {
        "status": report.get("status"),
        "dry_run": bool(report.get("dry_run", False)),
        "adaptation_ready_for_owner_review": bool(report.get("adaptation_ready_for_owner_review", False)),
        "runtime_changed": bool(report.get("runtime_changed", False)),
        "proposal_count": report.get("proposal_count"),
        "learning_ready_for_adaptation": learning.get("learning_ready_for_adaptation"),
        "confirmed_direction_count": learning.get("confirmed_direction_count"),
        "blocked_direction_count": learning.get("blocked_direction_count"),
        "latest_direction": latest.get("direction"),
        "latest_edge_status": latest.get("edge_status"),
        "next_action": report.get("next_action"),
    }


def _waste_adaptation_apply_preview_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    plan = (
        report.get("adaptation_plan_summary")
        if isinstance(report.get("adaptation_plan_summary"), Mapping)
        else {}
    )
    return {
        "status": report.get("status"),
        "dry_run": bool(report.get("dry_run", False)),
        "preview_ready_for_owner_review": bool(report.get("preview_ready_for_owner_review", False)),
        "apply_allowed_now": bool(report.get("apply_allowed_now", False)),
        "apply_endpoint_available": bool(report.get("apply_endpoint_available", False)),
        "runtime_changed": bool(report.get("runtime_changed", False)),
        "would_apply_runtime_change": bool(report.get("would_apply_runtime_change", False)),
        "would_lower_edge_threshold": bool(report.get("would_lower_edge_threshold", False)),
        "would_enable_live_trading": bool(report.get("would_enable_live_trading", False)),
        "simulated_change_count": report.get("simulated_change_count"),
        "blocker_count": report.get("blocker_count"),
        "adaptation_plan_status": plan.get("status"),
        "next_action": report.get("next_action"),
    }


def _waste_adaptation_owner_review_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    preview = (
        report.get("preview_summary")
        if isinstance(report.get("preview_summary"), Mapping)
        else {}
    )
    return {
        "status": report.get("owner_review_status"),
        "owner_review_decision": report.get("owner_review_decision"),
        "paper_only_review_current": bool(report.get("paper_only_review_current", False)),
        "paper_only_accept_current": bool(report.get("paper_only_accept_current", False)),
        "evidence_ready_for_owner_accept": bool(report.get("evidence_ready_for_owner_accept", False)),
        "dry_run": bool(report.get("dry_run", False)),
        "paper_only": bool(report.get("paper_only", False)),
        "apply_allowed_now": bool(report.get("apply_allowed_now", False)),
        "runtime_changed": bool(report.get("runtime_changed", False)),
        "would_apply_runtime_change": bool(report.get("would_apply_runtime_change", False)),
        "would_enable_live_trading": bool(report.get("would_enable_live_trading", False)),
        "money_moved": bool(report.get("money_moved", False)),
        "preview_status": preview.get("status"),
        "next_action": report.get("next_action"),
    }


def _waste_adaptation_paper_apply_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status"),
        "paper_apply_ready": bool(report.get("paper_apply_ready", False)),
        "paper_apply_current": bool(report.get("paper_apply_current", False)),
        "paper_apply_recorded": bool(report.get("paper_apply_recorded", False)),
        "dry_run": bool(report.get("dry_run", False)),
        "paper_only": bool(report.get("paper_only", False)),
        "runtime_changed": bool(report.get("runtime_changed", False)),
        "would_apply_runtime_change": bool(report.get("would_apply_runtime_change", False)),
        "would_enable_live_trading": bool(report.get("would_enable_live_trading", False)),
        "money_moved": bool(report.get("money_moved", False)),
        "simulated_change_count": report.get("simulated_change_count"),
        "missing_count": len(report.get("missing_requirements") or []),
        "next_action": report.get("next_action"),
    }


def _sweep_summary(preview: Mapping[str, Any]) -> dict[str, Any]:
    winnings = preview.get("winnings") if isinstance(preview.get("winnings"), Mapping) else {}
    payout_gate = (
        preview.get("payout_gate")
        if isinstance(preview.get("payout_gate"), Mapping)
        else {}
    )
    provider_runtime = (
        preview.get("provider_runtime")
        if isinstance(preview.get("provider_runtime"), Mapping)
        else {}
    )
    return {
        "status": preview.get("status"),
        "claim_status": winnings.get("claim_status"),
        "sweepable_winnings_usd": winnings.get("sweepable_winnings_usd"),
        "sweep_amount_usd": preview.get("sweep_amount_usd"),
        "payout_gate_authorized": bool(payout_gate.get("authorized", False)),
        "payout_runtime_ready": bool(preview.get("payout_runtime_ready", False)),
        "provider_runtime_status": provider_runtime.get("status"),
        "reason": preview.get("reason"),
    }


def _payout_recovery_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "has_pending_recovery": bool(report.get("has_pending_recovery", False)),
        "pending_count": report.get("pending_count", 0),
        "latest_attempt": report.get("latest_attempt"),
        "next_action": report.get("next_action"),
    }


def _readiness_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "overall_status": report.get("overall_status"),
        "live_money_authorized": bool(report.get("live_money_authorized", False)),
        "payment_movement_authorized": bool(report.get("payment_movement_authorized", False)),
        "checks_open": report.get("checks_open"),
        "checks_mismatch": report.get("checks_mismatch"),
        "checks_currently_not_licensed": report.get("checks_currently_not_licensed"),
        "next_action": _first(report.get("next_actions")),
    }


def _next_action(blockers: list[Mapping[str, Any]]) -> str:
    if not blockers:
        return (
            "All progression sources are clear for owner review; actual live "
            "dispatch or payout still must use its own explicit owner-confirmed endpoint."
        )
    first = next((item for item in blockers if item.get("next_action")), None)
    if first:
        return str(first.get("next_action"))
    planes = sorted({str(item.get("plane")) for item in blockers})
    return "Resolve live-money progression blockers in these planes: " + ", ".join(planes)


def _first(value: Any) -> str:
    if isinstance(value, (list, tuple)) and value:
        return str(value[0])
    if value:
        return str(value)
    return ""


def _unavailable(report_kind: str, exc: Exception) -> dict[str, Any]:
    return {
        "report_kind": report_kind,
        "status": "UNAVAILABLE",
        "error": f"{type(exc).__name__}: {exc}",
    }


__all__ = [
    "REPORT_KIND",
    "STATUS_BLOCKED",
    "STATUS_READY_FOR_OWNER_REVIEW",
    "build_live_money_progression_packet",
]
