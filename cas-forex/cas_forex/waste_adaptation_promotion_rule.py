"""Read-only promotion rule for WASTE adaptation evidence.

The direction-learning ledger can say a LONG/SHORT profile has enough confirmed
PASS-token samples. This module makes that promotion threshold explicit for the
API/UI/live-money packet without applying any adaptation or creating authority.
"""

from __future__ import annotations

from typing import Any, Mapping

from cas_forex.instruments import canonical_or_normalized_symbol

from cas_forex.time_utils import utc_now

REPORT_KIND = "cas_forex_waste_adaptation_promotion_rule"
STATUS_NO_EVIDENCE = "WASTE_ADAPTATION_PROMOTION_NO_EVIDENCE"
STATUS_COLLECTING = "WASTE_ADAPTATION_PROMOTION_COLLECTING"
STATUS_READY = "WASTE_ADAPTATION_PROMOTION_READY_FOR_OWNER_REVIEW"
DEFAULT_MIN_CONFIRMED_FOR_ADAPTATION = 5

CLAIM_BOUNDARY = (
    "WASTE adaptation promotion rule is read-only evidence accounting. It can "
    "count confirmed PASS-token direction samples and decide whether an "
    "adaptation may be promoted to owner review, but it does not apply runtime "
    "changes, place orders, close positions, create broker ACCEPT, create owner "
    "ACCEPT, authorize live trading, mint edge tokens, lower thresholds, "
    "deposit, withdraw, move bank/card money, automate payouts, or mark "
    "evidence LICENSED."
)


def build_waste_adaptation_promotion_rule(
    *,
    direction_learning: Mapping[str, Any] | None = None,
    direction_outcome_binding: Mapping[str, Any] | None = None,
    min_confirmed_for_adaptation: int | None = None,
) -> dict[str, Any]:
    """Report whether WASTE direction evidence may be promoted for owner review."""

    learning = dict(direction_learning) if direction_learning is not None else _direction_learning()
    outcome_binding = (
        dict(direction_outcome_binding)
        if direction_outcome_binding is not None
        else _direction_outcome_binding()
    )
    recommendation = _mapping(learning.get("profile_recommendation"))
    min_confirmed = _min_confirmed(recommendation, min_confirmed_for_adaptation)
    rows = _int(learning.get("direction_rows"), 0)
    confirmed = _int(learning.get("confirmed_direction_count"), 0)
    blocked = _int(learning.get("blocked_direction_count"), 0)
    learning_ready = bool(learning.get("learning_ready_for_adaptation", False))
    directional_group = _dominant_group(recommendation)
    outcome_groups = [
        dict(group)
        for group in (outcome_binding.get("group_stats") or [])
        if isinstance(group, Mapping)
    ]
    directional_group_outcome = _matching_outcome_group(outcome_groups, directional_group)
    growth_group = _mapping(outcome_binding.get("recommended_growth_group"))
    if not growth_group:
        growth_group = next(
            (
                dict(group)
                for group in outcome_groups
                if bool(group.get("outcome_ready_for_promotion", False))
            ),
            {},
        )
    directional_group_profitable = bool(
        directional_group_outcome.get("outcome_ready_for_promotion", False)
    )
    selected_group = directional_group if directional_group_profitable else growth_group
    selected_group_outcome = (
        directional_group_outcome
        if directional_group_profitable
        else _matching_outcome_group(outcome_groups, selected_group) or growth_group
    )
    selected_group_ready = bool(
        selected_group
        and selected_group_outcome.get("outcome_ready_for_promotion", False)
    )
    outcome_ready = bool(outcome_binding.get("outcome_ready_for_promotion", False)) and selected_group_ready
    samples_needed = max(0, min_confirmed - confirmed)
    ready = rows > 0 and confirmed >= min_confirmed and learning_ready and outcome_ready

    if rows <= 0:
        status = STATUS_NO_EVIDENCE
    elif ready:
        status = STATUS_READY
    else:
        status = STATUS_COLLECTING

    proxy_conflict = bool(
        directional_group
        and growth_group
        and not _same_group(directional_group, growth_group)
    )
    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "read_only": True,
        "dry_run": True,
        "promotion_ready_for_owner_review": ready,
        "learning_ready_for_adaptation": learning_ready,
        "outcome_ready_for_promotion": outcome_ready,
        "outcome_ready_group_count": _int(
            outcome_binding.get("outcome_ready_group_count"), 0
        ),
        "selection_basis": (
            "exact_group_after_cost_expectancy_r_then_per_1_lot_then_raw_expectancy_then_net_pnl"
        ),
        "risk_normalized_evidence_required_for_promotion": True,
        "pooled_profit_cannot_promote_group": True,
        "directional_proxy_group": directional_group,
        "directional_proxy_group_outcome": directional_group_outcome,
        "directional_proxy_group_profitable": directional_group_profitable,
        "proxy_recommendation_overridden_by_growth": proxy_conflict and not directional_group_profitable,
        "min_confirmed_for_adaptation": min_confirmed,
        "confirmed_direction_count": confirmed,
        "confirmed_samples_needed": samples_needed,
        "bound_outcome_count": outcome_binding.get("bound_outcome_count"),
        "bound_outcomes_needed": outcome_binding.get("bound_outcomes_needed"),
        "net_paper_pnl": outcome_binding.get("net_paper_pnl"),
        "blocked_direction_count": blocked,
        "direction_rows": rows,
        "direction_counts": learning.get("direction_counts") or {},
        "edge_status_counts": learning.get("edge_status_counts") or {},
        "profile_recommendation_status": recommendation.get("status"),
        "outcome_binding_summary": _outcome_binding_summary(outcome_binding),
        "dominant_group": directional_group,
        "recommended_group": selected_group,
        "recommended_group_outcome": selected_group_outcome,
        "runtime_changed": False,
        "runtime_change_attempted": False,
        "would_apply_runtime_change": False,
        "would_lower_edge_threshold": False,
        "would_enable_live_trading": False,
        "would_raise_risk": False,
        "broker_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "edge_token_minted": False,
        "owner_accept_created": False,
        "money_moved": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(
            status,
            confirmed=samples_needed,
            dominant=selected_group or directional_group,
            outcome_binding=outcome_binding,
            outcome_ready=outcome_ready,
        ),
    }


def _direction_learning() -> dict[str, Any]:
    try:
        from cas_forex.waste_direction_learning_ledger import build_waste_direction_learning_ledger

        return build_waste_direction_learning_ledger()
    except Exception as exc:
        return {
            "report_kind": "cas_forex_waste_direction_learning_ledger",
            "status": "UNAVAILABLE",
            "error": f"{type(exc).__name__}: {exc}",
        }


def _direction_outcome_binding() -> dict[str, Any]:
    try:
        from cas_forex.waste_direction_outcome_binding import build_waste_direction_outcome_binding

        return build_waste_direction_outcome_binding()
    except Exception as exc:
        return {
            "report_kind": "cas_forex_waste_direction_outcome_binding",
            "status": "UNAVAILABLE",
            "error": f"{type(exc).__name__}: {exc}",
        }


def _outcome_binding_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status"),
        "dry_run": bool(report.get("dry_run", False)),
        "read_only": bool(report.get("read_only", False)),
        "paper_only": bool(report.get("paper_only", False)),
        "outcome_ready_for_promotion": bool(report.get("outcome_ready_for_promotion", False)),
        "grouping_basis": report.get("grouping_basis"),
        "ranking_basis": report.get("ranking_basis"),
        "pooled_profit_cannot_promote_group": bool(
            report.get("pooled_profit_cannot_promote_group", False)
        ),
        "sample_ready_group_count": report.get("sample_ready_group_count"),
        "outcome_ready_group_count": report.get("outcome_ready_group_count"),
        "recommended_growth_group": _mapping(report.get("recommended_growth_group")),
        "min_bound_outcomes_for_promotion": report.get("min_bound_outcomes_for_promotion"),
        "bound_outcome_count": report.get("bound_outcome_count"),
        "bound_outcomes_needed": report.get("bound_outcomes_needed"),
        "confirmed_direction_count": report.get("confirmed_direction_count"),
        "executed_confirmed_count": report.get("executed_confirmed_count"),
        "closed_history_count": report.get("closed_history_count"),
        "unbound_confirmed_count": report.get("unbound_confirmed_count"),
        "net_paper_pnl": report.get("net_paper_pnl"),
        "runtime_changed": bool(report.get("runtime_changed", False)),
        "would_enable_live_trading": bool(report.get("would_enable_live_trading", False)),
        "money_moved": bool(report.get("money_moved", False)),
        "next_action": report.get("next_action"),
    }


def _min_confirmed(recommendation: Mapping[str, Any], override: int | None) -> int:
    source = override if override is not None else recommendation.get("min_confirmed_for_adaptation")
    value = _int(source, DEFAULT_MIN_CONFIRMED_FOR_ADAPTATION)
    return max(1, value)


def _dominant_group(recommendation: Mapping[str, Any]) -> dict[str, Any]:
    group = recommendation.get("recommended_group")
    if not isinstance(group, Mapping):
        group = recommendation.get("dominant_observed_group")
    return dict(group) if isinstance(group, Mapping) else {}


def _matching_outcome_group(
    groups: list[Mapping[str, Any]],
    target: Mapping[str, Any],
) -> dict[str, Any]:
    if not target:
        return {}
    return next((dict(group) for group in groups if _same_group(group, target)), {})


def _same_group(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return (
        _symbol(left.get("symbol")) == _symbol(right.get("symbol"))
        and _text(left.get("timeframe"), "UNKNOWN")
        == _text(right.get("timeframe"), "UNKNOWN")
        and _direction(left.get("direction")) == _direction(right.get("direction"))
        and _text(left.get("profile"), "UNKNOWN")
        == _text(right.get("profile"), "UNKNOWN")
    )


def _symbol(value: Any) -> str:
    return canonical_or_normalized_symbol(value)


def _direction(value: Any) -> str:
    text = _text(value, "UNKNOWN")
    if text in {"BUY", "LONG"}:
        return "LONG"
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    return text


def _text(value: Any, default: str = "") -> str:
    return str(value if value not in (None, "") else default).strip().upper()


def _next_action(
    status: str,
    *,
    confirmed: int,
    dominant: Mapping[str, Any],
    outcome_binding: Mapping[str, Any],
    outcome_ready: bool,
) -> str:
    if status == STATUS_NO_EVIDENCE:
        return "Let WASTE collect PAPER LONG/SHORT direction samples before promotion can be considered."
    if status == STATUS_READY:
        return "Promotion evidence is ready for owner review; any adaptation must remain dry-run until the owner explicitly accepts it."
    if confirmed <= 0 and not outcome_ready:
        return str(
            outcome_binding.get("next_action")
            or "Bind confirmed direction samples to closed paper/demo outcomes before promoting WASTE adaptation."
        )
    group = " ".join(
        str(part)
        for part in (
            dominant.get("symbol"),
            dominant.get("timeframe"),
            dominant.get("profile"),
            dominant.get("direction"),
        )
        if part
    )
    suffix = f" for {group}" if group else ""
    return f"Collect {confirmed} more confirmed PASS-token direction sample(s){suffix} before promoting WASTE adaptation."


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


__all__ = [
    "DEFAULT_MIN_CONFIRMED_FOR_ADAPTATION",
    "REPORT_KIND",
    "STATUS_COLLECTING",
    "STATUS_NO_EVIDENCE",
    "STATUS_READY",
    "build_waste_adaptation_promotion_rule",
]
