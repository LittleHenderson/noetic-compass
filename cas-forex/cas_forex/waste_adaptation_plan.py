"""Dry-run WASTE adaptation plan from direction-learning evidence.

The learning ledger tells CAS what has happened. This module turns that evidence
into owner-visible proposals without applying them. It cannot lower gates,
authorize trading, change runtime controls, or move money.
"""

from __future__ import annotations

from typing import Any, Mapping

from cas_forex.time_utils import utc_now

REPORT_KIND = "cas_forex_waste_adaptation_plan"
STATUS_NO_EVIDENCE = "WASTE_ADAPTATION_PLAN_NO_EVIDENCE"
STATUS_COLLECTING = "WASTE_ADAPTATION_PLAN_COLLECTING"
STATUS_READY = "WASTE_ADAPTATION_PLAN_READY_FOR_OWNER_REVIEW"

CLAIM_BOUNDARY = (
    "WASTE adaptation plan is a dry-run owner review layer over direction "
    "learning evidence. It can propose profile priority, threshold discipline, "
    "or no-trade discipline changes, but it does not apply runtime changes, "
    "place orders, close positions, create broker ACCEPT, create owner ACCEPT, "
    "authorize live trading, mint edge tokens, deposit, withdraw, move "
    "bank/card money, automate payouts, or mark evidence LICENSED."
)


def build_waste_adaptation_plan(
    *,
    direction_learning: Mapping[str, Any] | None = None,
    direction_review: Mapping[str, Any] | None = None,
    adaptation_promotion_rule: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a dry-run adaptation plan from WASTE direction learning."""

    learning = dict(direction_learning) if direction_learning is not None else _direction_learning()
    review = dict(direction_review) if direction_review is not None else _direction_review()
    promotion = (
        dict(adaptation_promotion_rule)
        if adaptation_promotion_rule is not None
        else _adaptation_promotion_rule(learning)
    )
    proposals = _proposals(learning, review, promotion)
    ready = bool(promotion.get("promotion_ready_for_owner_review", False))
    rows = _int(promotion.get("direction_rows"), _int(learning.get("direction_rows"), 0))
    if rows <= 0:
        status = STATUS_NO_EVIDENCE
    elif ready:
        status = STATUS_READY
    else:
        status = STATUS_COLLECTING
    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "dry_run": True,
        "adaptation_ready_for_owner_review": ready,
        "runtime_changed": False,
        "runtime_change_attempted": False,
        "would_lower_edge_threshold": False,
        "would_enable_live_trading": False,
        "broker_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "edge_token_minted": False,
        "owner_accept_created": False,
        "money_moved": False,
        "learning_summary": _learning_summary(learning),
        "promotion_rule_summary": _promotion_rule_summary(promotion),
        "latest_direction_summary": _latest_direction_summary(review),
        "proposal_count": len(proposals),
        "proposals": proposals,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(status, ready, proposals),
    }


def _direction_learning() -> dict[str, Any]:
    try:
        from cas_forex.waste_direction_learning_ledger import build_waste_direction_learning_ledger

        return build_waste_direction_learning_ledger()
    except Exception as exc:
        return {"report_kind": "cas_forex_waste_direction_learning_ledger", "status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}"}


def _direction_review() -> dict[str, Any]:
    try:
        from cas_forex.waste_direction_review_packet import build_waste_direction_review_packet

        return build_waste_direction_review_packet()
    except Exception as exc:
        return {"report_kind": "cas_forex_waste_direction_review_packet", "status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}"}


def _adaptation_promotion_rule(learning: Mapping[str, Any]) -> dict[str, Any]:
    try:
        from cas_forex.waste_adaptation_promotion_rule import build_waste_adaptation_promotion_rule

        return build_waste_adaptation_promotion_rule(direction_learning=learning)
    except Exception as exc:
        return {"report_kind": "cas_forex_waste_adaptation_promotion_rule", "status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}"}


def _proposals(
    learning: Mapping[str, Any],
    review: Mapping[str, Any],
    promotion: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows = _int(learning.get("direction_rows"), 0)
    confirmed = _int(learning.get("confirmed_direction_count"), 0)
    blocked = _int(learning.get("blocked_direction_count"), 0)
    ready = bool(promotion.get("promotion_ready_for_owner_review", False))
    rec = _mapping(learning.get("profile_recommendation"))
    latest_edge = _mapping(review.get("edge_gate_summary"))
    proposals: list[dict[str, Any]] = []

    if rows <= 0:
        proposals.append(
            _proposal(
                "collect_direction_evidence",
                "COLLECT_MORE_EVIDENCE",
                "Run WASTE in PAPER or real-candle probe mode until the direction ledger has LONG/SHORT samples.",
                {"min_direction_rows": 1, "current_direction_rows": rows},
            )
        )
        return proposals

    if confirmed <= 0:
        proposals.append(
            _proposal(
                "hold_no_trade_discipline",
                "NO_TRADE_DISCIPLINE",
                "Keep WASTE in PAPER/no-trade discipline because no recent direction has earned a PASS edge token.",
                {
                    "direction_rows": rows,
                    "blocked_direction_count": blocked,
                    "confirmed_direction_count": confirmed,
                    "latest_edge_status": latest_edge.get("status"),
                    "latest_edge_reason": latest_edge.get("reason"),
                    "do_not_lower_edge_threshold": True,
                    "require_pass_token": True,
                },
            )
        )
        proposals.append(
            _proposal(
                "diagnose_profile_failure",
                "PROFILE_DIAGNOSTIC",
                "Review the dominant blocked profile/direction before changing any profile priority.",
                {
                    "dominant_group": _dominant_group(rec),
                    "edge_status_counts": learning.get("edge_status_counts") or {},
                    "direction_counts": learning.get("direction_counts") or {},
                    "runtime_change_allowed": False,
                },
            )
        )
        return proposals

    if not ready:
        proposals.append(
            _proposal(
                "collect_confirmed_direction_samples",
                "COLLECT_MORE_CONFIRMED_EDGE",
                "Some directions have passed, but not enough confirmed samples exist to adapt profile selection.",
                {
                    "confirmed_direction_count": confirmed,
                    "min_confirmed_for_adaptation": promotion.get("min_confirmed_for_adaptation")
                    or rec.get("min_confirmed_for_adaptation"),
                    "confirmed_samples_needed": promotion.get("confirmed_samples_needed"),
                    "promotion_rule_status": promotion.get("status"),
                    "require_owner_review_before_apply": True,
                },
            )
        )
        return proposals

    recommended = _dominant_group(rec)
    proposals.append(
        _proposal(
            "review_profile_direction_priority",
            "PROFILE_PRIORITY_REVIEW",
            "Use the recommended profile/direction as an owner-reviewed input to future PAPER profile selection.",
            {
                "recommended_group": recommended,
                "confirmed_direction_count": confirmed,
                "runtime_change_allowed": False,
                "owner_accept_required_before_any_apply": True,
            },
        )
    )
    proposals.append(
        _proposal(
            "keep_edge_gate_authority",
            "GATE_DISCIPLINE",
            "Even if profile priority is later adjusted, every candidate still needs a fresh PASS edge token before execution.",
            {
                "would_lower_edge_threshold": False,
                "require_pass_token": True,
                "live_gates_still_required": True,
            },
        )
    )
    return proposals


def _proposal(
    proposal_id: str,
    proposal_type: str,
    detail: str,
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "proposal_id": proposal_id,
        "proposal_type": proposal_type,
        "detail": detail,
        "dry_run": True,
        "would_apply_runtime_change": False,
        "would_lower_edge_threshold": False,
        "would_enable_live_trading": False,
        "requires_owner_review": True,
        "evidence": dict(evidence),
    }


def _learning_summary(learning: Mapping[str, Any]) -> dict[str, Any]:
    recommendation = _mapping(learning.get("profile_recommendation"))
    return {
        "status": learning.get("status"),
        "direction_rows": learning.get("direction_rows"),
        "confirmed_direction_count": learning.get("confirmed_direction_count"),
        "blocked_direction_count": learning.get("blocked_direction_count"),
        "learning_ready_for_adaptation": bool(learning.get("learning_ready_for_adaptation", False)),
        "direction_counts": learning.get("direction_counts") or {},
        "edge_status_counts": learning.get("edge_status_counts") or {},
        "profile_recommendation_status": recommendation.get("status"),
        "min_confirmed_for_adaptation": recommendation.get("min_confirmed_for_adaptation"),
    }


def _promotion_rule_summary(promotion: Mapping[str, Any]) -> dict[str, Any]:
    dominant = _mapping(promotion.get("recommended_group")) or _mapping(promotion.get("dominant_group"))
    return {
        "status": promotion.get("status"),
        "dry_run": bool(promotion.get("dry_run", False)),
        "read_only": bool(promotion.get("read_only", False)),
        "promotion_ready_for_owner_review": bool(promotion.get("promotion_ready_for_owner_review", False)),
        "learning_ready_for_adaptation": bool(promotion.get("learning_ready_for_adaptation", False)),
        "outcome_ready_for_promotion": bool(promotion.get("outcome_ready_for_promotion", False)),
        "min_confirmed_for_adaptation": promotion.get("min_confirmed_for_adaptation"),
        "confirmed_direction_count": promotion.get("confirmed_direction_count"),
        "confirmed_samples_needed": promotion.get("confirmed_samples_needed"),
        "bound_outcome_count": promotion.get("bound_outcome_count"),
        "bound_outcomes_needed": promotion.get("bound_outcomes_needed"),
        "net_paper_pnl": promotion.get("net_paper_pnl"),
        "blocked_direction_count": promotion.get("blocked_direction_count"),
        "direction_rows": promotion.get("direction_rows"),
        "profile_recommendation_status": promotion.get("profile_recommendation_status"),
        "dominant_symbol": dominant.get("symbol"),
        "dominant_timeframe": dominant.get("timeframe"),
        "dominant_profile": dominant.get("profile"),
        "dominant_direction": dominant.get("direction"),
        "runtime_changed": bool(promotion.get("runtime_changed", False)),
        "would_enable_live_trading": bool(promotion.get("would_enable_live_trading", False)),
        "money_moved": bool(promotion.get("money_moved", False)),
        "next_action": promotion.get("next_action"),
    }


def _latest_direction_summary(review: Mapping[str, Any]) -> dict[str, Any]:
    direction = _mapping(review.get("direction_summary"))
    edge = _mapping(review.get("edge_gate_summary"))
    return {
        "status": review.get("status"),
        "direction_edge_confirmed": bool(review.get("direction_edge_confirmed", False)),
        "symbol": direction.get("symbol"),
        "timeframe": direction.get("timeframe"),
        "direction": direction.get("direction"),
        "opposite_direction": direction.get("opposite_direction"),
        "chosen_score": direction.get("chosen_score"),
        "opposite_score": direction.get("opposite_score"),
        "score_margin": direction.get("score_margin"),
        "edge_status": edge.get("status"),
        "edge_reason": edge.get("reason"),
    }


def _dominant_group(recommendation: Mapping[str, Any]) -> dict[str, Any]:
    group = recommendation.get("recommended_group")
    if not isinstance(group, Mapping):
        group = recommendation.get("dominant_observed_group")
    return dict(group) if isinstance(group, Mapping) else {}


def _next_action(status: str, ready: bool, proposals: list[Mapping[str, Any]]) -> str:
    if status == STATUS_NO_EVIDENCE:
        return "Let WASTE collect direction evidence in PAPER before adaptation is considered."
    if not ready:
        return "Keep collecting PAPER direction evidence; no runtime adaptation is ready or applied."
    if proposals:
        return "Review the dry-run adaptation proposals; any future apply path must require explicit owner review and preserve all gates."
    return "No adaptation proposal is available."


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


__all__ = [
    "REPORT_KIND",
    "STATUS_COLLECTING",
    "STATUS_NO_EVIDENCE",
    "STATUS_READY",
    "build_waste_adaptation_plan",
]
