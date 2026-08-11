"""Read-only WASTE promotion gate for a small controlled pilot sequence.

This module answers one owner-facing question: is the latest WASTE real-candle
entry dry-run ready to be considered for the small pilot envelope? It does not
dispatch, place, close, deposit, withdraw, move money, mint edge tokens, or
create owner/broker ACCEPT.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from cas_forex.live_order_dry_run import DEFAULT_AUDIT_PATH, LiveOrderDryRunAuditLog
from cas_forex.live_order_dry_run_review import build_live_order_dry_run_review
from cas_forex.live_pilot import build_live_pilot_policy, evaluate_live_pilot_intent
from cas_forex.live_recovery import build_live_recovery_report
from cas_forex.order_attempt_audit import build_order_attempt_audit_status
from cas_forex.time_utils import utc_now
from cas_forex.waste_runner import (
    build_waste_entry_dispatch_handoff_status,
    build_waste_entry_dispatch_intent_from_dry_run,
)

REPORT_KIND = "cas_forex_waste_pilot_promotion"
STATUS_READY = "WASTE_PILOT_READY"
STATUS_BLOCKED = "WASTE_PILOT_BLOCKED"

CLAIM_BOUNDARY = (
    "WASTE pilot promotion is a read-only readiness gate from owner-reviewed "
    "WASTE dry-run evidence into a small controlled pilot sequence. It does not "
    "place orders, close positions, touch a broker bridge, create broker ACCEPT, "
    "create owner ACCEPT, authorize live trading, deposit, withdraw, move "
    "bank/card money, automate payouts, mint edge tokens, or mark evidence "
    "LICENSED."
)


def build_waste_pilot_promotion_status(
    *,
    dry_run_audit: Optional[Mapping[str, Any]] = None,
    dry_run_review: Optional[Mapping[str, Any]] = None,
    live_pilot_policy: Optional[Mapping[str, Any]] = None,
    live_recovery_report: Optional[Mapping[str, Any]] = None,
    order_attempt_status: Optional[Mapping[str, Any]] = None,
    dry_run_audit_path: Any = None,
) -> dict[str, Any]:
    """Build the current WASTE pilot promotion status without side effects."""

    dry_run_record = dict(dry_run_audit) if dry_run_audit is not None else _latest_dry_run(dry_run_audit_path)
    dry_run = _dry_run_payload(dry_run_record)
    review = dict(dry_run_review) if dry_run_review is not None else build_live_order_dry_run_review(
        dry_run_audit=dry_run_record,
    )
    handoff = build_waste_entry_dispatch_handoff_status(dry_run, review=review)
    pilot = dict(live_pilot_policy) if live_pilot_policy is not None else build_live_pilot_policy()
    attempts = dict(order_attempt_status) if order_attempt_status is not None else build_order_attempt_audit_status()
    recovery = (
        dict(live_recovery_report)
        if live_recovery_report is not None
        else build_live_recovery_report(live_pilot_policy=pilot, order_attempt_status=attempts)
    )

    intent_payload = _intent_payload(dry_run)
    source = dry_run.get("waste_real_candle_source")
    source = source if isinstance(source, Mapping) else {}
    pilot_intent = _pilot_intent_review(pilot, intent_payload)

    handoff_ready = bool(handoff.get("would_call_dispatch_if_owner_attempted", False))
    owner_review_clear = bool(review.get("dry_run_review_clear_for_live", False))
    pilot_ready = bool(pilot.get("ready_for_next_live_order", False))
    recovery_clear = bool(recovery.get("recovery_clear_for_live", False))
    unresolved_clear = not (
        bool(attempts.get("has_unresolved_real_attempt", False))
        or int(attempts.get("unresolved_real_attempt_count", 0) or 0) > 0
    )
    source_direction = str(source.get("direction") or intent_payload.get("direction") or "").upper()
    direction_ready = source_direction in {"LONG", "SHORT"}

    checks = [
        _check(
            "waste_entry_handoff_ready",
            handoff_ready,
            {"status": handoff.get("status"), "would_call_dispatch_if_owner_attempted": handoff_ready},
            "WASTE entry handoff is owner-review ready." if handoff_ready else "WASTE entry handoff is not ready.",
        ),
        _check(
            "owner_dry_run_accept_current",
            owner_review_clear,
            {
                "owner_review_status": review.get("owner_review_status"),
                "dry_run_review_clear_for_live": owner_review_clear,
            },
            "Owner ACCEPT is current for the exact WASTE dry-run fingerprint."
            if owner_review_clear
            else "Owner ACCEPT is not current for the exact WASTE dry-run fingerprint.",
        ),
        _check(
            "long_short_hypothesis_present",
            direction_ready,
            {"direction": source_direction or None},
            "WASTE source carries an explicit LONG/SHORT hypothesis."
            if direction_ready
            else "WASTE source must carry an explicit LONG or SHORT hypothesis.",
        ),
        _check(
            "pilot_policy_accept_capacity",
            pilot_ready,
            {
                "owner_pilot_status": pilot.get("owner_pilot_status"),
                "pilot_capacity_remaining": pilot.get("pilot_capacity_remaining"),
                "ready_for_next_live_order": pilot_ready,
            },
            "Small controlled pilot policy is owner ACCEPT and has capacity."
            if pilot_ready
            else "Small controlled pilot policy is not ACCEPT or has no capacity.",
        ),
        _check(
            "intent_inside_pilot_envelope",
            bool(pilot_intent["passed"]),
            pilot_intent["evidence"],
            "WASTE intent is inside the owner-accepted pilot symbol, lot, and risk envelope."
            if pilot_intent["passed"]
            else "WASTE intent is outside or cannot be checked against the owner-accepted pilot envelope.",
        ),
        _check(
            "live_recovery_clear",
            recovery_clear,
            {
                "recovery_status": recovery.get("recovery_status"),
                "missing_requirements": recovery.get("missing_requirements", []),
            },
            "Live recovery is clear for the current broker/order-attempt evidence."
            if recovery_clear
            else "Live recovery is not clear.",
        ),
        _check(
            "unresolved_real_attempts_clear",
            unresolved_clear,
            {
                "unresolved_real_attempt_count": attempts.get("unresolved_real_attempt_count", 0),
                "has_unresolved_real_attempt": attempts.get("has_unresolved_real_attempt", False),
            },
            "No unresolved real broker order attempts are open."
            if unresolved_clear
            else "A real broker order attempt is unresolved and must be reconciled.",
        ),
    ]
    missing = [check["check_id"] for check in checks if check["status"] != "OK"]
    status = STATUS_READY if not missing else STATUS_BLOCKED

    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "ready_for_pilot_sequence": status == STATUS_READY,
        "broker_touched": False,
        "dispatched_to_bridge": False,
        "dispatch_attempted": False,
        "order_id": intent_payload.get("order_id") or dry_run.get("order_id") or dry_run_record.get("order_id"),
        "decision_ref": intent_payload.get("decision_ref") or dry_run.get("decision_ref") or dry_run_record.get("decision_ref"),
        "symbol": intent_payload.get("symbol") or source.get("symbol"),
        "direction": intent_payload.get("direction") or source.get("direction"),
        "lots": intent_payload.get("lots"),
        "entry_pair_count": _int(source.get("entry_pair_count"), 0),
        "missing_requirements": missing,
        "checks": checks,
        "handoff_status": handoff,
        "dry_run_review_summary": _dry_run_review_summary(review),
        "pilot_policy_summary": _pilot_summary(pilot),
        "live_recovery_summary": _recovery_summary(recovery),
        "order_attempt_summary": _attempt_summary(attempts),
        "waste_real_candle_source": dict(source),
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": (
            "Owner-reviewed WASTE evidence is ready for the small controlled pilot sequence; any actual dispatch still must go through the normal live, edge, pilot, risk, emergency-stop, audit, and broker gates."
            if status == STATUS_READY
            else "Resolve the listed WASTE pilot promotion blockers before considering this candidate for the small controlled pilot sequence."
        ),
    }


def _latest_dry_run(path: Any = None) -> dict[str, Any]:
    latest = LiveOrderDryRunAuditLog(path or DEFAULT_AUDIT_PATH).latest()
    return dict(latest) if isinstance(latest, Mapping) else {}


def _dry_run_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = record.get("payload") if isinstance(record, Mapping) else None
    return dict(payload) if isinstance(payload, Mapping) else {}


def _intent_payload(dry_run: Mapping[str, Any]) -> dict[str, Any]:
    try:
        intent = build_waste_entry_dispatch_intent_from_dry_run(dry_run)
    except Exception:
        return {}
    attached = dict(dry_run.get("proposed_intent") or {}) if isinstance(dry_run.get("proposed_intent"), Mapping) else {}
    return {
        **attached,
        "order_id": intent.order_id,
        "decision_ref": intent.decision_ref,
        "symbol": intent.symbol,
        "direction": str(intent.direction).upper(),
        "lots": float(intent.volume),
        "expected_loss_usd": intent.expected_loss_usd,
    }


def _pilot_intent_review(policy: Mapping[str, Any], intent: Mapping[str, Any]) -> dict[str, Any]:
    review = evaluate_live_pilot_intent(intent, policy=policy)
    problems: list[str] = list(review.get("missing_requirements") or [])
    direction = str(intent.get("direction") or "").strip().upper()

    if not intent:
        problems.append("waste_entry_intent_unavailable")
    if direction not in {"LONG", "SHORT"}:
        problems.append("direction must be LONG or SHORT")

    return {
        "passed": not problems,
        "missing_requirements": list(dict.fromkeys(problems)),
        "evidence": {
            **dict(review.get("evidence") or {}),
            "direction": direction or None,
            "missing_requirements": list(dict.fromkeys(problems)),
        },
    }


def _check(check_id: str, ok: bool, evidence: Mapping[str, Any], detail: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "OK" if ok else "MISSING",
        "evidence": dict(evidence),
        "detail": detail,
    }


def _dry_run_review_summary(review: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "owner_review_status": review.get("owner_review_status"),
        "dry_run_review_clear_for_live": bool(review.get("dry_run_review_clear_for_live", False)),
        "evidence_ready_for_owner_accept": bool(review.get("evidence_ready_for_owner_accept", False)),
        "current_fingerprint": review.get("current_fingerprint"),
        "accepted_fingerprint": review.get("accepted_fingerprint"),
        "missing_requirements": list(review.get("missing_requirements") or []),
    }


def _pilot_summary(policy: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "owner_pilot_status": policy.get("owner_pilot_status"),
        "ready_for_next_live_order": bool(policy.get("ready_for_next_live_order", False)),
        "pilot_capacity_remaining": policy.get("pilot_capacity_remaining"),
        "allowed_symbols": list(policy.get("allowed_symbols") or []),
        "max_trade_lots": policy.get("max_trade_lots"),
        "max_open_live_lots": policy.get("max_open_live_lots"),
        "max_live_trade_count": policy.get("max_live_trade_count"),
        "live_trade_count": policy.get("live_trade_count"),
        "missing_requirements": list(policy.get("missing_requirements") or []),
    }


def _recovery_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "recovery_status": report.get("recovery_status"),
        "recovery_clear_for_live": bool(report.get("recovery_clear_for_live", False)),
        "requires_recovery_review": bool(report.get("requires_recovery_review", False)),
        "missing_requirements": list(report.get("missing_requirements") or []),
    }


def _attempt_summary(status: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "attempt_count": status.get("attempt_count", 0),
        "real_attempt_count": status.get("real_attempt_count", 0),
        "unresolved_real_attempt_count": status.get("unresolved_real_attempt_count", 0),
        "has_unresolved_real_attempt": bool(status.get("has_unresolved_real_attempt", False)),
        "latest_attempt": status.get("latest_attempt"),
    }


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)
