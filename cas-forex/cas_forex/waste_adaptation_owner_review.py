"""Owner review audit trail for WASTE adaptation previews.

This module records the owner's review decision for a WASTE adaptation preview.
It is deliberately paper-only: even an owner ``ACCEPT`` here is an audit record
for a reviewed preview, not permission to change runtime controls or trade live.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "waste-adaptation-owner-review.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "waste-adaptation-owner-review-audit.jsonl"

REPORT_KIND = "cas_forex_waste_adaptation_owner_review"
STATUS_OPEN = "OPEN"
STATUS_ACCEPT = "ACCEPT"

DECISION_HOLD = "HOLD_PAPER_ONLY"
DECISION_MORE_EVIDENCE = "REQUEST_MORE_EVIDENCE"
DECISION_ACCEPT = "ACCEPT_PAPER_ONLY"
DECISIONS = (DECISION_HOLD, DECISION_MORE_EVIDENCE, DECISION_ACCEPT)

CLAIM_BOUNDARY = (
    "WASTE adaptation owner review records the owner's paper-only review "
    "decision for an adaptation apply preview. It does not apply runtime "
    "changes, lower the edge threshold, enable live trading, place orders, "
    "close positions, create broker ACCEPT, create live-trading owner ACCEPT, "
    "mint edge tokens, deposit, withdraw, move bank/card money, automate "
    "payouts, or mark evidence LICENSED."
)


class WasteAdaptationOwnerReviewError(ValueError):
    """Raised when WASTE adaptation owner review cannot be recorded."""


def build_waste_adaptation_owner_review(
    *,
    adaptation_apply_preview: Mapping[str, Any] | None = None,
    state_path: Path | str | None = None,
) -> dict[str, Any]:
    """Return the current paper-only owner review status."""

    preview = (
        dict(adaptation_apply_preview)
        if adaptation_apply_preview is not None
        else _adaptation_apply_preview()
    )
    state = _load_state(state_path)
    findings = _findings(preview)
    fingerprint = _fingerprint(preview)
    latest_fingerprint = state.get("current_fingerprint")
    review_current = bool(latest_fingerprint and latest_fingerprint == fingerprint)
    accepted_current = (
        review_current
        and state.get("owner_review_status") == STATUS_ACCEPT
        and state.get("owner_review_decision") == DECISION_ACCEPT
        and findings["evidence_ready_for_owner_accept"]
    )
    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "owner_review_status": STATUS_ACCEPT if accepted_current else STATUS_OPEN,
        "owner_review_decision": state.get("owner_review_decision", ""),
        "owner_reviewed_at": state.get("owner_reviewed_at"),
        "owner_review_notes": state.get("notes", ""),
        "accepted_fingerprint": state.get("accepted_fingerprint"),
        "current_fingerprint": fingerprint,
        "reviewed_fingerprint": latest_fingerprint,
        "paper_only_review_current": review_current,
        "paper_only_accept_current": accepted_current,
        "evidence_ready_for_owner_accept": findings["evidence_ready_for_owner_accept"],
        "missing_requirements": [] if accepted_current else findings["missing_requirements"],
        "checks": findings["checks"],
        "preview_summary": findings["preview_summary"],
        "dry_run": True,
        "paper_only": True,
        "apply_allowed_now": False,
        "apply_endpoint_available": False,
        "runtime_changed": False,
        "runtime_change_attempted": False,
        "would_apply_runtime_change": False,
        "would_lower_edge_threshold": False,
        "would_enable_live_trading": False,
        "would_raise_risk": False,
        "would_create_live_authority": False,
        "broker_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "edge_token_minted": False,
        "owner_accept_created": False,
        "money_moved": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(accepted_current, review_current, findings["evidence_ready_for_owner_accept"]),
    }


def record_waste_adaptation_owner_review(
    *,
    decision: str,
    notes: str = "",
    confirm_owner_review: bool = False,
    confirm_owner_accept: bool = False,
    adaptation_apply_preview: Mapping[str, Any] | None = None,
    state_path: Path | str | None = None,
    audit_path: Path | str | None = None,
) -> dict[str, Any]:
    """Record an owner paper-only review decision for the current preview."""

    if not confirm_owner_review:
        raise WasteAdaptationOwnerReviewError("confirm_owner_review=true is required to record WASTE adaptation owner review")
    normalized = _normalize_decision(decision)
    preview = (
        dict(adaptation_apply_preview)
        if adaptation_apply_preview is not None
        else _adaptation_apply_preview()
    )
    report = build_waste_adaptation_owner_review(
        adaptation_apply_preview=preview,
        state_path=state_path,
    )
    if normalized == DECISION_ACCEPT:
        if not confirm_owner_accept:
            raise WasteAdaptationOwnerReviewError("confirm_owner_accept=true is required to record owner ACCEPT for paper-only WASTE adaptation review")
        if not report["evidence_ready_for_owner_accept"]:
            raise WasteAdaptationOwnerReviewError(
                "Cannot ACCEPT paper-only WASTE adaptation review; missing: "
                + "; ".join(report["missing_requirements"])
            )
    fingerprint = report["current_fingerprint"]
    owner_status = STATUS_ACCEPT if normalized == DECISION_ACCEPT else STATUS_OPEN
    payload = {
        "owner_review_status": owner_status,
        "owner_review_decision": normalized,
        "owner_reviewed_at": utc_now().isoformat(),
        "accepted_fingerprint": fingerprint if normalized == DECISION_ACCEPT else None,
        "current_fingerprint": fingerprint,
        "notes": str(notes or "").strip(),
        "paper_only": True,
    }
    _write_json(payload, _state_path(state_path))
    _append_audit(
        {
            "action": "waste_adaptation_owner_review_recorded",
            "timestamp": utc_now().isoformat(),
            "decision": normalized,
            "owner_review_status": owner_status,
            "current_fingerprint": fingerprint,
            "preview_status": report["preview_summary"].get("status"),
            "preview_ready_for_owner_review": report["preview_summary"].get("preview_ready_for_owner_review"),
            "notes": payload["notes"],
            "paper_only": True,
            "runtime_changed": False,
            "broker_touched": False,
            "money_moved": False,
        },
        _audit_path(audit_path),
    )
    return build_waste_adaptation_owner_review(
        adaptation_apply_preview=preview,
        state_path=state_path,
    )


def reset_waste_adaptation_owner_review(
    *,
    reason: str = "OWNER_RESET",
    state_path: Path | str | None = None,
    audit_path: Path | str | None = None,
) -> dict[str, Any]:
    payload = _empty_state()
    _write_json(payload, _state_path(state_path))
    _append_audit(
        {
            "action": "waste_adaptation_owner_review_reset",
            "timestamp": utc_now().isoformat(),
            "reason": str(reason or "OWNER_RESET"),
            "paper_only": True,
            "runtime_changed": False,
            "broker_touched": False,
            "money_moved": False,
        },
        _audit_path(audit_path),
    )
    return build_waste_adaptation_owner_review(state_path=state_path)


def _findings(preview: Mapping[str, Any]) -> dict[str, Any]:
    preview_present = str(preview.get("report_kind") or "") == "cas_forex_waste_adaptation_apply_preview"
    dry_run = bool(preview.get("dry_run", False))
    ready = bool(preview.get("preview_ready_for_owner_review", False))
    no_apply = not bool(preview.get("apply_allowed_now", False))
    no_endpoint = not bool(preview.get("apply_endpoint_available", False))
    no_runtime = (
        not bool(preview.get("runtime_changed", False))
        and not bool(preview.get("runtime_change_attempted", False))
        and not bool(preview.get("would_apply_runtime_change", False))
    )
    no_threshold_lower = not bool(preview.get("would_lower_edge_threshold", False))
    no_live = not bool(preview.get("would_enable_live_trading", False))
    no_risk_raise = not bool(preview.get("would_raise_risk", False))
    no_broker_money = (
        not bool(preview.get("broker_touched", False))
        and not bool(preview.get("live_order_attempted", False))
        and not bool(preview.get("attempt_finalized", False))
        and not bool(preview.get("edge_token_minted", False))
        and not bool(preview.get("owner_accept_created", False))
        and not bool(preview.get("money_moved", False))
    )
    checks = [
        _check("adaptation_apply_preview_present", preview_present, {"report_kind": preview.get("report_kind")}, "Adaptation apply preview is present." if preview_present else "No adaptation apply preview is available."),
        _check("adaptation_apply_preview_dry_run", dry_run, {"dry_run": preview.get("dry_run")}, "Preview is dry-run." if dry_run else "Preview is not marked dry-run."),
        _check("preview_ready_for_owner_review", ready, {"status": preview.get("status"), "blocker_count": preview.get("blocker_count")}, "Preview is ready for owner review." if ready else "Preview is not ready for owner ACCEPT."),
        _check("no_apply_available", no_apply and no_endpoint, {"apply_allowed_now": preview.get("apply_allowed_now"), "apply_endpoint_available": preview.get("apply_endpoint_available")}, "No apply endpoint/permission is active." if no_apply and no_endpoint else "Preview exposes an apply path; refuse owner review."),
        _check("no_runtime_change_requested", no_runtime, {"runtime_changed": preview.get("runtime_changed"), "runtime_change_attempted": preview.get("runtime_change_attempted"), "would_apply_runtime_change": preview.get("would_apply_runtime_change")}, "Preview does not request runtime changes." if no_runtime else "Preview indicates runtime mutation."),
        _check("edge_threshold_not_lowered", no_threshold_lower, {"would_lower_edge_threshold": preview.get("would_lower_edge_threshold")}, "Preview does not lower the edge threshold." if no_threshold_lower else "Preview would lower the edge threshold."),
        _check("live_trading_not_enabled", no_live, {"would_enable_live_trading": preview.get("would_enable_live_trading")}, "Preview does not enable live trading." if no_live else "Preview would enable live trading."),
        _check("risk_not_raised", no_risk_raise, {"would_raise_risk": preview.get("would_raise_risk")}, "Preview does not raise risk." if no_risk_raise else "Preview would raise risk."),
        _check("no_broker_or_money_side_effects", no_broker_money, {"broker_touched": preview.get("broker_touched"), "live_order_attempted": preview.get("live_order_attempted"), "edge_token_minted": preview.get("edge_token_minted"), "owner_accept_created": preview.get("owner_accept_created"), "money_moved": preview.get("money_moved")}, "Preview has no broker/money side effects." if no_broker_money else "Preview indicates broker, edge-token, owner-ACCEPT, or money side effects."),
    ]
    missing = [check["check_id"] for check in checks if check["status"] != "OK"]
    return {
        "evidence_ready_for_owner_accept": preview_present and dry_run and ready and no_apply and no_endpoint and no_runtime and no_threshold_lower and no_live and no_risk_raise and no_broker_money,
        "missing_requirements": missing,
        "checks": checks,
        "preview_summary": {
            "status": preview.get("status"),
            "dry_run": dry_run,
            "preview_ready_for_owner_review": ready,
            "simulated_change_count": preview.get("simulated_change_count"),
            "blocker_count": preview.get("blocker_count"),
            "next_action": preview.get("next_action"),
        },
    }


def _check(check_id: str, ok: bool, evidence: Mapping[str, Any], detail: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "OK" if ok else "MISSING",
        "evidence": dict(evidence),
        "detail": detail,
    }


def _fingerprint(preview: Mapping[str, Any]) -> str:
    material = {
        "report_kind": preview.get("report_kind"),
        "status": preview.get("status"),
        "preview_ready_for_owner_review": preview.get("preview_ready_for_owner_review"),
        "adaptation_plan_summary": preview.get("adaptation_plan_summary"),
        "current_controls": preview.get("current_controls"),
        "owner_envelope_summary": preview.get("owner_envelope_summary"),
        "simulated_changes": preview.get("simulated_changes"),
        "blocker_count": preview.get("blocker_count"),
        "blockers": preview.get("blockers"),
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:24]


def _adaptation_apply_preview() -> dict[str, Any]:
    try:
        from cas_forex.waste_adaptation_apply_preview import build_waste_adaptation_apply_preview

        return build_waste_adaptation_apply_preview()
    except Exception as exc:
        return {"report_kind": "cas_forex_waste_adaptation_apply_preview", "status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}"}


def _next_action(accepted_current: bool, review_current: bool, evidence_ready: bool) -> str:
    if accepted_current:
        return "Owner ACCEPT is current for this paper-only WASTE adaptation preview; no runtime apply is performed."
    if review_current:
        return "Owner review is recorded for this preview; keep collecting evidence or wait for a ready paper-only preview."
    if evidence_ready:
        return "Owner may record a paper-only review decision; ACCEPT still records review only and does not apply runtime changes."
    return "Record HOLD or REQUEST_MORE_EVIDENCE if the owner has reviewed this blocked preview; ACCEPT requires a ready preview."


def _normalize_decision(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text not in DECISIONS:
        raise WasteAdaptationOwnerReviewError(
            "decision must be one of: " + ", ".join(DECISIONS)
        )
    return text


def _load_state(path: Path | str | None) -> dict[str, Any]:
    target = _state_path(path)
    if not target.exists():
        return _empty_state()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_state()
    return payload if isinstance(payload, dict) else _empty_state()


def _empty_state() -> dict[str, Any]:
    return {
        "owner_review_status": STATUS_OPEN,
        "owner_review_decision": "",
        "owner_reviewed_at": None,
        "accepted_fingerprint": None,
        "current_fingerprint": None,
        "notes": "",
        "paper_only": True,
    }


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)


def _append_audit(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), sort_keys=True, default=str) + "\n")


def _state_path(path: Path | str | None) -> Path:
    return Path(path) if path is not None else Path(DEFAULT_STATE_PATH)


def _audit_path(path: Path | str | None) -> Path:
    return Path(path) if path is not None else Path(DEFAULT_AUDIT_PATH)


__all__ = [
    "DECISION_ACCEPT",
    "DECISION_HOLD",
    "DECISION_MORE_EVIDENCE",
    "REPORT_KIND",
    "STATUS_ACCEPT",
    "STATUS_OPEN",
    "WasteAdaptationOwnerReviewError",
    "build_waste_adaptation_owner_review",
    "record_waste_adaptation_owner_review",
    "reset_waste_adaptation_owner_review",
]
