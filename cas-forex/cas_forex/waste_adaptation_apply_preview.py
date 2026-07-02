"""Owner-reviewed dry-run preview for WASTE adaptation apply decisions.

The adaptation plan says what CAS has learned. This module answers the next
owner question: if this proposal were reviewed later, what would it alter?

It is intentionally read-only. It does not call ``ai_adjust``, write the control
authority file, create owner ACCEPT, mint edge tokens, touch broker bridges, or
move money.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

from cas_forex.time_utils import utc_now

REPORT_KIND = "cas_forex_waste_adaptation_apply_preview"
STATUS_BLOCKED = "WASTE_ADAPTATION_APPLY_PREVIEW_BLOCKED"
STATUS_READY = "WASTE_ADAPTATION_APPLY_PREVIEW_READY_FOR_OWNER_REVIEW"

CLAIM_BOUNDARY = (
    "WASTE adaptation apply preview is a dry-run owner review simulator. It "
    "shows the current AI control surface, the paper-only changes that would be "
    "considered, and the blockers that prevent any apply. It does not apply "
    "runtime changes, lower the edge threshold, enable live trading, place "
    "orders, close positions, create broker ACCEPT, create owner ACCEPT, mint "
    "edge tokens, deposit, withdraw, move bank/card money, automate payouts, or "
    "mark evidence LICENSED."
)


def build_waste_adaptation_apply_preview(
    *,
    adaptation_plan: Mapping[str, Any] | None = None,
    authority_snapshot: Mapping[str, Any] | None = None,
    runtime_gates: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an owner-readable dry-run preview of adaptation apply impact."""

    plan = dict(adaptation_plan) if adaptation_plan is not None else _adaptation_plan()
    authority = dict(authority_snapshot) if authority_snapshot is not None else _authority_snapshot()
    runtime = dict(runtime_gates) if runtime_gates is not None else _runtime_gates()

    current = _current_controls(authority)
    owner = _owner_envelope(authority)
    proposals = list(plan.get("proposals") or [])
    simulated_changes = _simulated_changes(proposals, current=current, owner=owner)
    blockers = _blockers(plan, simulated_changes)
    ready = not blockers
    status = STATUS_READY if ready else STATUS_BLOCKED
    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "dry_run": True,
        "owner_review_required": True,
        "preview_ready_for_owner_review": ready,
        "apply_allowed_now": False,
        "apply_endpoint_available": False,
        "runtime_changed": False,
        "runtime_change_attempted": False,
        "would_apply_runtime_change": False,
        "would_lower_edge_threshold": False,
        "would_enable_live_trading": False,
        "would_raise_risk": False,
        "would_create_owner_accept": False,
        "broker_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "edge_token_minted": False,
        "owner_accept_created": False,
        "money_moved": False,
        "adaptation_plan_summary": _plan_summary(plan),
        "runtime_gate_summary": _runtime_summary(runtime),
        "current_controls": current,
        "owner_envelope_summary": owner,
        "simulated_change_count": len(simulated_changes),
        "simulated_changes": simulated_changes,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(ready, blockers),
    }


def _adaptation_plan() -> dict[str, Any]:
    try:
        from cas_forex.waste_adaptation_plan import build_waste_adaptation_plan

        return build_waste_adaptation_plan()
    except Exception as exc:
        return _unavailable("cas_forex_waste_adaptation_plan", exc)


def _authority_snapshot() -> dict[str, Any]:
    try:
        from cas_forex.ai_control_authority import get_authority

        return get_authority().snapshot()
    except Exception as exc:
        return _unavailable("cas_forex_ai_control_authority", exc)


def _runtime_gates() -> dict[str, Any]:
    try:
        from cas_forex.runtime_gates import build_runtime_gates_report

        return build_runtime_gates_report().to_dict()
    except Exception as exc:
        return _unavailable("cas_forex_runtime_gates", exc)


def _current_controls(authority: Mapping[str, Any]) -> dict[str, Any]:
    surface = _mapping(authority.get("control_surface"))
    values = _mapping(surface.get("values"))
    bounds = _mapping(surface.get("bounds"))
    return {
        "edge_threshold": values.get("edge_threshold"),
        "max_risk_pct_per_trade": values.get("max_risk_pct_per_trade"),
        "max_concurrent_trades": values.get("max_concurrent_trades"),
        "daily_loss_cap_usd": values.get("daily_loss_cap_usd"),
        "max_compound_units": values.get("max_compound_units"),
        "symbols": values.get("symbols") or [],
        "sessions": values.get("sessions") or [],
        "bounds": _json_safe(bounds),
    }


def _owner_envelope(authority: Mapping[str, Any]) -> dict[str, Any]:
    owner = _mapping(authority.get("owner_envelope"))
    return {
        "monthly_profit_target_usd": owner.get("monthly_profit_target_usd"),
        "daily_profit_floor_usd": owner.get("daily_profit_floor_usd"),
        "daily_profit_cap_usd": owner.get("daily_profit_cap_usd"),
        "allowed_symbols": owner.get("allowed_symbols") or [],
        "allowed_sessions": owner.get("allowed_sessions") or [],
        "allow_long": bool(owner.get("allow_long", True)),
        "allow_short": bool(owner.get("allow_short", True)),
        "edge_threshold_min": owner.get("edge_threshold_min"),
        "edge_threshold_max": owner.get("edge_threshold_max"),
        "max_risk_pct_per_trade": owner.get("max_risk_pct_per_trade"),
        "max_concurrent_trades": owner.get("max_concurrent_trades"),
        "max_compound_units": owner.get("max_compound_units"),
        "require_fresh_pass_for_entry": bool(owner.get("require_fresh_pass_for_entry", True)),
        "require_fresh_pass_for_compound": bool(owner.get("require_fresh_pass_for_compound", True)),
    }


def _simulated_changes(
    proposals: list[Any],
    *,
    current: Mapping[str, Any],
    owner: Mapping[str, Any],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for proposal in proposals:
        if not isinstance(proposal, Mapping):
            continue
        proposal_type = str(proposal.get("proposal_type") or "")
        evidence = _mapping(proposal.get("evidence"))
        if proposal_type == "PROFILE_PRIORITY_REVIEW":
            group = _mapping(evidence.get("recommended_group"))
            changes.append(
                _change(
                    proposal,
                    change_type="PAPER_PROFILE_PRIORITY_HINT",
                    field="profile_priority",
                    current_value=None,
                    preview_value={
                        "symbol": group.get("symbol"),
                        "timeframe": group.get("timeframe"),
                        "profile": group.get("profile"),
                        "direction": group.get("direction"),
                    },
                    rationale="Owner could later review this as a PAPER profile-selection hint only.",
                )
            )
        elif proposal_type == "NO_TRADE_DISCIPLINE":
            changes.append(
                _change(
                    proposal,
                    change_type="HOLD_NO_TRADE_DISCIPLINE",
                    field="edge_threshold",
                    current_value=current.get("edge_threshold"),
                    preview_value=current.get("edge_threshold"),
                    rationale="No PASS-token evidence exists, so the preview keeps the edge gate unchanged.",
                )
            )
        elif proposal_type == "PROFILE_DIAGNOSTIC":
            changes.append(
                _change(
                    proposal,
                    change_type="PAPER_DIAGNOSTIC_ONLY",
                    field="profile_diagnostic",
                    current_value=None,
                    preview_value=evidence.get("dominant_group") or {},
                    rationale="Diagnose repeated blocked directions before any profile priority change.",
                )
            )
        elif proposal_type == "GATE_DISCIPLINE":
            changes.append(
                _change(
                    proposal,
                    change_type="KEEP_GATE_AUTHORITY",
                    field="require_fresh_pass_for_entry",
                    current_value=owner.get("require_fresh_pass_for_entry"),
                    preview_value=True,
                    rationale="Any later profile hint still requires a fresh PASS token before execution.",
                )
            )
        elif proposal_type in {"COLLECT_MORE_EVIDENCE", "COLLECT_MORE_CONFIRMED_EDGE"}:
            changes.append(
                _change(
                    proposal,
                    change_type="COLLECT_MORE_EVIDENCE",
                    field="runtime_controls",
                    current_value="unchanged",
                    preview_value="unchanged",
                    rationale="Evidence is not mature enough for an owner-reviewed apply preview.",
                )
            )
    return changes


def _change(
    proposal: Mapping[str, Any],
    *,
    change_type: str,
    field: str,
    current_value: Any,
    preview_value: Any,
    rationale: str,
) -> dict[str, Any]:
    return {
        "proposal_id": proposal.get("proposal_id"),
        "proposal_type": proposal.get("proposal_type"),
        "change_type": change_type,
        "field": field,
        "current_value": current_value,
        "preview_value": preview_value,
        "dry_run": True,
        "would_apply_runtime_change": False,
        "would_lower_edge_threshold": False,
        "would_enable_live_trading": False,
        "would_raise_risk": False,
        "requires_owner_review": True,
        "rationale": rationale,
    }


def _blockers(plan: Mapping[str, Any], simulated_changes: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    _add_blocker(
        out,
        "adaptation_plan_available",
        str(plan.get("report_kind") or "") == "cas_forex_waste_adaptation_plan",
        "No WASTE adaptation plan is available.",
        {"report_kind": plan.get("report_kind"), "status": plan.get("status")},
    )
    _add_blocker(
        out,
        "adaptation_plan_dry_run",
        bool(plan.get("dry_run", False)),
        "Adaptation plan is not marked dry-run.",
        {"dry_run": plan.get("dry_run")},
    )
    _add_blocker(
        out,
        "adaptation_ready_for_owner_review",
        bool(plan.get("adaptation_ready_for_owner_review", False)),
        "Direction evidence is not ready for owner-reviewed adaptation.",
        _plan_summary(plan),
    )
    _add_blocker(
        out,
        "simulated_changes_available",
        bool(simulated_changes),
        "No simulated adaptation change is available.",
        {"simulated_change_count": len(simulated_changes)},
    )
    _add_blocker(
        out,
        "no_runtime_change_attempted",
        not bool(plan.get("runtime_change_attempted", False))
        and not any(bool(change.get("would_apply_runtime_change", False)) for change in simulated_changes),
        "A runtime change was attempted or requested inside a preview.",
        {"runtime_change_attempted": plan.get("runtime_change_attempted")},
    )
    _add_blocker(
        out,
        "edge_threshold_not_lowered",
        not bool(plan.get("would_lower_edge_threshold", False))
        and not any(bool(change.get("would_lower_edge_threshold", False)) for change in simulated_changes),
        "Preview would lower the edge threshold.",
        {"would_lower_edge_threshold": plan.get("would_lower_edge_threshold")},
    )
    _add_blocker(
        out,
        "live_trading_not_enabled",
        not bool(plan.get("would_enable_live_trading", False))
        and not any(bool(change.get("would_enable_live_trading", False)) for change in simulated_changes),
        "Preview would enable live trading.",
        {"would_enable_live_trading": plan.get("would_enable_live_trading")},
    )
    return out


def _add_blocker(
    out: list[dict[str, Any]],
    blocker_id: str,
    clear: bool,
    detail: str,
    evidence: Mapping[str, Any],
) -> None:
    if clear:
        return
    out.append(
        {
            "blocker_id": blocker_id,
            "clear": False,
            "detail": detail,
            "evidence": dict(evidence),
        }
    )


def _plan_summary(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": plan.get("status"),
        "dry_run": bool(plan.get("dry_run", False)),
        "adaptation_ready_for_owner_review": bool(plan.get("adaptation_ready_for_owner_review", False)),
        "proposal_count": plan.get("proposal_count"),
        "runtime_changed": bool(plan.get("runtime_changed", False)),
        "runtime_change_attempted": bool(plan.get("runtime_change_attempted", False)),
        "next_action": plan.get("next_action"),
    }


def _runtime_summary(runtime: Mapping[str, Any]) -> dict[str, Any]:
    decisions = _mapping(runtime.get("decisions"))
    live = _mapping(decisions.get("live_trading"))
    broker_accept = _mapping(decisions.get("broker_accept"))
    payout = _mapping(decisions.get("payout_automation"))
    return {
        "all_real_money_authorized": bool(runtime.get("all_real_money_authorized", False)),
        "live_trading_authorized": bool(live.get("authorized", False)),
        "broker_accept_authorized": bool(broker_accept.get("authorized", False)),
        "payout_automation_authorized": bool(payout.get("authorized", False)),
        "summary": runtime.get("summary"),
    }


def _next_action(ready: bool, blockers: list[Mapping[str, Any]]) -> str:
    if ready:
        return (
            "Review the dry-run simulated changes. A future apply endpoint must "
            "still require explicit owner confirmation and preserve edge, broker, "
            "risk, recovery, and live-money gates."
        )
    first = blockers[0]["detail"] if blockers else "Preview is not ready."
    return f"Keep WASTE adaptation in preview only: {first}"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _json_safe(value: Any) -> Any:
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return "+inf" if value > 0 else "-inf"
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value


def _unavailable(report_kind: str, exc: Exception) -> dict[str, Any]:
    return {
        "report_kind": report_kind,
        "status": "UNAVAILABLE",
        "error": f"{type(exc).__name__}: {exc}",
    }


__all__ = [
    "REPORT_KIND",
    "STATUS_BLOCKED",
    "STATUS_READY",
    "build_waste_adaptation_apply_preview",
]
