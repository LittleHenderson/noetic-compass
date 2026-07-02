"""PAPER-only WASTE adaptation apply audit.

This module records that an owner-accepted WASTE adaptation preview was applied
to the paper adaptation audit trail. It does not mutate the AI control authority
or any live/broker/money state.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "waste-adaptation-paper-apply.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "waste-adaptation-paper-apply-audit.jsonl"

REPORT_KIND = "cas_forex_waste_adaptation_paper_apply"
STATUS_BLOCKED = "WASTE_ADAPTATION_PAPER_APPLY_BLOCKED"
STATUS_READY = "WASTE_ADAPTATION_PAPER_APPLY_READY"
STATUS_CURRENT = "WASTE_ADAPTATION_PAPER_APPLY_CURRENT"

CLAIM_BOUNDARY = (
    "WASTE adaptation paper apply records an owner-accepted adaptation preview "
    "to a paper-only audit trail. It does not apply runtime changes, lower the "
    "edge threshold, enable live trading, place orders, close positions, create "
    "broker ACCEPT, create live-trading owner ACCEPT, mint edge tokens, deposit, "
    "withdraw, move bank/card money, automate payouts, or mark evidence LICENSED."
)


class WasteAdaptationPaperApplyError(ValueError):
    """Raised when a paper-only adaptation apply cannot be recorded."""


def build_waste_adaptation_paper_apply_status(
    *,
    owner_review: Mapping[str, Any] | None = None,
    state_path: Path | str | None = None,
) -> dict[str, Any]:
    """Return the current paper-only apply audit status."""

    review = dict(owner_review) if owner_review is not None else _owner_review()
    state = _load_state(state_path)
    findings = _findings(review)
    fingerprint = _fingerprint(review)
    applied_current = (
        findings["paper_apply_ready"]
        and state.get("applied_fingerprint") == fingerprint
        and state.get("paper_apply_status") == STATUS_CURRENT
    )
    status = STATUS_CURRENT if applied_current else STATUS_READY if findings["paper_apply_ready"] else STATUS_BLOCKED
    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "paper_apply_ready": findings["paper_apply_ready"],
        "paper_apply_current": applied_current,
        "paper_apply_recorded": applied_current,
        "paper_apply_recorded_at": state.get("paper_apply_recorded_at") if applied_current else None,
        "applied_fingerprint": state.get("applied_fingerprint") if applied_current else None,
        "current_fingerprint": fingerprint,
        "accepted_fingerprint": review.get("accepted_fingerprint"),
        "paper_only": True,
        "dry_run": True,
        "apply_requires_owner_confirm": True,
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
        "owner_review_summary": _owner_review_summary(review),
        "simulated_change_count": _simulated_change_count(review),
        "paper_apply_effect": _paper_apply_effect(review),
        "missing_requirements": [] if applied_current else findings["missing_requirements"],
        "checks": findings["checks"],
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(status, findings["paper_apply_ready"]),
    }


def record_waste_adaptation_paper_apply(
    *,
    notes: str = "",
    confirm_owner_apply: bool = False,
    owner_review: Mapping[str, Any] | None = None,
    state_path: Path | str | None = None,
    audit_path: Path | str | None = None,
) -> dict[str, Any]:
    """Record the current owner-accepted preview to the paper apply audit."""

    if not confirm_owner_apply:
        raise WasteAdaptationPaperApplyError("confirm_owner_apply=true is required to record WASTE adaptation paper apply")
    review = dict(owner_review) if owner_review is not None else _owner_review()
    status = build_waste_adaptation_paper_apply_status(owner_review=review, state_path=state_path)
    if not status["paper_apply_ready"]:
        raise WasteAdaptationPaperApplyError(
            "Cannot record WASTE adaptation paper apply; missing: "
            + "; ".join(status["missing_requirements"])
        )
    fingerprint = status["current_fingerprint"]
    payload = {
        "paper_apply_status": STATUS_CURRENT,
        "paper_apply_recorded_at": utc_now().isoformat(),
        "applied_fingerprint": fingerprint,
        "accepted_fingerprint": status.get("accepted_fingerprint"),
        "notes": str(notes or "").strip(),
        "paper_only": True,
        "runtime_changed": False,
        "broker_touched": False,
        "money_moved": False,
    }
    _write_json(payload, _state_path(state_path))
    _append_audit(
        {
            "action": "waste_adaptation_paper_apply_recorded",
            "timestamp": utc_now().isoformat(),
            "current_fingerprint": fingerprint,
            "accepted_fingerprint": status.get("accepted_fingerprint"),
            "owner_review_status": status["owner_review_summary"].get("owner_review_status"),
            "owner_review_decision": status["owner_review_summary"].get("owner_review_decision"),
            "simulated_change_count": status.get("simulated_change_count"),
            "paper_apply_effect": status.get("paper_apply_effect"),
            "notes": payload["notes"],
            "paper_only": True,
            "runtime_changed": False,
            "broker_touched": False,
            "money_moved": False,
        },
        _audit_path(audit_path),
    )
    return build_waste_adaptation_paper_apply_status(owner_review=review, state_path=state_path)


def reset_waste_adaptation_paper_apply(
    *,
    reason: str = "OWNER_RESET",
    state_path: Path | str | None = None,
    audit_path: Path | str | None = None,
) -> dict[str, Any]:
    payload = _empty_state()
    _write_json(payload, _state_path(state_path))
    _append_audit(
        {
            "action": "waste_adaptation_paper_apply_reset",
            "timestamp": utc_now().isoformat(),
            "reason": str(reason or "OWNER_RESET"),
            "paper_only": True,
            "runtime_changed": False,
            "broker_touched": False,
            "money_moved": False,
        },
        _audit_path(audit_path),
    )
    return build_waste_adaptation_paper_apply_status(state_path=state_path)


def _findings(review: Mapping[str, Any]) -> dict[str, Any]:
    review_present = str(review.get("report_kind") or "") == "cas_forex_waste_adaptation_owner_review"
    paper_only = bool(review.get("paper_only", False))
    dry_run = bool(review.get("dry_run", False))
    owner_accept = bool(review.get("paper_only_accept_current", False))
    evidence_ready = bool(review.get("evidence_ready_for_owner_accept", False))
    accepted_current = bool(review.get("accepted_fingerprint")) and review.get("accepted_fingerprint") == review.get("current_fingerprint")
    no_runtime = (
        not bool(review.get("runtime_changed", False))
        and not bool(review.get("runtime_change_attempted", False))
        and not bool(review.get("would_apply_runtime_change", False))
    )
    no_threshold_lower = not bool(review.get("would_lower_edge_threshold", False))
    no_live = not bool(review.get("would_enable_live_trading", False))
    no_risk_raise = not bool(review.get("would_raise_risk", False))
    no_broker_money = (
        not bool(review.get("broker_touched", False))
        and not bool(review.get("live_order_attempted", False))
        and not bool(review.get("attempt_finalized", False))
        and not bool(review.get("edge_token_minted", False))
        and not bool(review.get("owner_accept_created", False))
        and not bool(review.get("money_moved", False))
    )
    checks = [
        _check("owner_review_present", review_present, {"report_kind": review.get("report_kind")}, "Owner review is present." if review_present else "No WASTE adaptation owner review is available."),
        _check("owner_review_paper_only", paper_only, {"paper_only": review.get("paper_only")}, "Owner review is paper-only." if paper_only else "Owner review is not paper-only."),
        _check("owner_review_dry_run", dry_run, {"dry_run": review.get("dry_run")}, "Owner review remains dry-run." if dry_run else "Owner review is not marked dry-run."),
        _check("owner_paper_accept_current", owner_accept, {"paper_only_accept_current": review.get("paper_only_accept_current")}, "Owner ACCEPT is current for paper-only adaptation." if owner_accept else "Owner ACCEPT is not current for this preview."),
        _check("owner_accept_evidence_ready", evidence_ready, {"evidence_ready_for_owner_accept": review.get("evidence_ready_for_owner_accept")}, "Owner review evidence is ready." if evidence_ready else "Owner review evidence is not ready."),
        _check("accepted_fingerprint_current", accepted_current, {"accepted_fingerprint": review.get("accepted_fingerprint"), "current_fingerprint": review.get("current_fingerprint")}, "Accepted fingerprint matches current preview." if accepted_current else "Accepted fingerprint is missing or stale."),
        _check("no_runtime_change_requested", no_runtime, {"runtime_changed": review.get("runtime_changed"), "runtime_change_attempted": review.get("runtime_change_attempted"), "would_apply_runtime_change": review.get("would_apply_runtime_change")}, "No runtime change is requested." if no_runtime else "Owner review indicates runtime mutation."),
        _check("edge_threshold_not_lowered", no_threshold_lower, {"would_lower_edge_threshold": review.get("would_lower_edge_threshold")}, "Edge threshold is not lowered." if no_threshold_lower else "Owner review would lower the edge threshold."),
        _check("live_trading_not_enabled", no_live, {"would_enable_live_trading": review.get("would_enable_live_trading")}, "Live trading is not enabled." if no_live else "Owner review would enable live trading."),
        _check("risk_not_raised", no_risk_raise, {"would_raise_risk": review.get("would_raise_risk")}, "Risk is not raised." if no_risk_raise else "Owner review would raise risk."),
        _check("no_broker_or_money_side_effects", no_broker_money, {"broker_touched": review.get("broker_touched"), "live_order_attempted": review.get("live_order_attempted"), "edge_token_minted": review.get("edge_token_minted"), "owner_accept_created": review.get("owner_accept_created"), "money_moved": review.get("money_moved")}, "No broker/money side effects are present." if no_broker_money else "Owner review indicates broker, edge-token, owner-ACCEPT, or money side effects."),
    ]
    missing = [check["check_id"] for check in checks if check["status"] != "OK"]
    return {
        "paper_apply_ready": not missing,
        "missing_requirements": missing,
        "checks": checks,
    }


def _check(check_id: str, ok: bool, evidence: Mapping[str, Any], detail: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "OK" if ok else "MISSING",
        "evidence": dict(evidence),
        "detail": detail,
    }


def _fingerprint(review: Mapping[str, Any]) -> str:
    material = {
        "report_kind": review.get("report_kind"),
        "accepted_fingerprint": review.get("accepted_fingerprint"),
        "current_fingerprint": review.get("current_fingerprint"),
        "owner_review_status": review.get("owner_review_status"),
        "owner_review_decision": review.get("owner_review_decision"),
        "preview_summary": review.get("preview_summary"),
        "paper_only": review.get("paper_only"),
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:24]


def _owner_review() -> dict[str, Any]:
    try:
        from cas_forex.waste_adaptation_owner_review import build_waste_adaptation_owner_review

        return build_waste_adaptation_owner_review()
    except Exception as exc:
        return {"report_kind": "cas_forex_waste_adaptation_owner_review", "status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}"}


def _owner_review_summary(review: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "owner_review_status": review.get("owner_review_status"),
        "owner_review_decision": review.get("owner_review_decision"),
        "paper_only_review_current": bool(review.get("paper_only_review_current", False)),
        "paper_only_accept_current": bool(review.get("paper_only_accept_current", False)),
        "evidence_ready_for_owner_accept": bool(review.get("evidence_ready_for_owner_accept", False)),
        "accepted_fingerprint": review.get("accepted_fingerprint"),
        "current_fingerprint": review.get("current_fingerprint"),
    }


def _simulated_change_count(review: Mapping[str, Any]) -> int:
    preview = review.get("preview_summary") if isinstance(review.get("preview_summary"), Mapping) else {}
    try:
        return int(preview.get("simulated_change_count") or 0)
    except (TypeError, ValueError):
        return 0


def _paper_apply_effect(review: Mapping[str, Any]) -> dict[str, Any]:
    preview = review.get("preview_summary") if isinstance(review.get("preview_summary"), Mapping) else {}
    return {
        "paper_policy_audit_recorded": True,
        "runtime_controls_changed": False,
        "live_trading_changed": False,
        "broker_changed": False,
        "money_changed": False,
        "preview_status": preview.get("status"),
    }


def _next_action(status: str, ready: bool) -> str:
    if status == STATUS_CURRENT:
        return "Paper-only WASTE adaptation apply is current for the owner-accepted preview; runtime controls remain unchanged."
    if ready:
        return "Owner may record the paper-only adaptation apply audit; this will not change runtime controls or live trading."
    return "Wait for current owner ACCEPT on a ready dry-run adaptation preview before any paper-only apply record."


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
        "paper_apply_status": STATUS_BLOCKED,
        "paper_apply_recorded_at": None,
        "applied_fingerprint": None,
        "accepted_fingerprint": None,
        "notes": "",
        "paper_only": True,
        "runtime_changed": False,
        "broker_touched": False,
        "money_moved": False,
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
    "REPORT_KIND",
    "STATUS_BLOCKED",
    "STATUS_CURRENT",
    "STATUS_READY",
    "WasteAdaptationPaperApplyError",
    "build_waste_adaptation_paper_apply_status",
    "record_waste_adaptation_paper_apply",
    "reset_waste_adaptation_paper_apply",
]
