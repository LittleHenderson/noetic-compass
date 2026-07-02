"""Crash/disconnect recovery gate for CAS Forex live-money operation.

Live trading needs a way to recover after the app restarts, MT5 disconnects,
broker truth is stale while real positions may exist, or a real broker order
attempt was started but not finalized. This module records an owner recovery
review tied to the latest broker-truth evidence, order-attempt audit, and
live-pilot activity. New live orders can stay blocked until that review is
clear.

It is read-only with respect to the broker: it never places, closes, deposits,
withdraws, moves bank/card money, automates payouts, or authorizes trading by
itself.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from cas_forex.account_reconciliation import RECONCILIATION_FAILED
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "live-recovery-state.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "live-recovery-audit.jsonl"

REPORT_KIND = "cas_forex_live_recovery_review"
STATUS_CLEAR = "CLEAR"
STATUS_OPEN = "OPEN"
STATUS_ACCEPT = "ACCEPT"
DEFAULT_FRESH_SECONDS = 180

CLAIM_BOUNDARY = (
    "Live recovery review is a fail-closed restart/disconnect safety gate. It "
    "compares latest broker-truth evidence, open-position reconciliation, "
    "durable order-attempt audit, and live-pilot activity before allowing more "
    "live orders. It does not place orders, close positions, deposit, withdraw, "
    "move bank/card money, automate payouts, create broker ACCEPT, or authorize "
    "live trading by itself."
)


class LiveRecoveryError(ValueError):
    """Raised when live recovery cannot be accepted or loaded."""


def build_live_recovery_report(
    *,
    broker_truth_report: Mapping[str, Any] | None = None,
    live_pilot_policy: Mapping[str, Any] | None = None,
    order_attempt_status: Mapping[str, Any] | None = None,
    state_path: Path | str | None = None,
    fresh_seconds: int = DEFAULT_FRESH_SECONDS,
) -> dict[str, Any]:
    state = _load_state(state_path)
    broker_truth = dict(broker_truth_report) if broker_truth_report is not None else _latest_broker_truth()
    pilot = dict(live_pilot_policy) if live_pilot_policy is not None else _live_pilot_policy()
    order_attempts = dict(order_attempt_status) if order_attempt_status is not None else _order_attempt_status()
    findings = _findings(broker_truth, pilot, order_attempts, fresh_seconds=fresh_seconds)
    fingerprint = _fingerprint(broker_truth, pilot, order_attempts)
    accepted_current = (
        state.get("owner_recovery_status") == STATUS_ACCEPT
        and state.get("accepted_fingerprint") == fingerprint
    )
    requires_review = bool(findings["requires_recovery_review"])
    evidence_ready = bool(findings["evidence_ready_for_owner_accept"])
    clear = not requires_review or (accepted_current and evidence_ready)
    status = STATUS_CLEAR if clear else STATUS_OPEN
    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "recovery_status": status,
        "owner_recovery_status": state.get("owner_recovery_status", STATUS_OPEN),
        "owner_accepted_at": state.get("owner_accepted_at"),
        "accepted_fingerprint": state.get("accepted_fingerprint"),
        "current_fingerprint": fingerprint,
        "recovery_clear_for_live": clear,
        "requires_recovery_review": requires_review,
        "evidence_ready_for_owner_accept": evidence_ready,
        "missing_requirements": [] if clear else findings["missing_requirements"],
        "checks": findings["checks"],
        "broker_truth_summary": findings["broker_truth_summary"],
        "live_pilot_summary": findings["live_pilot_summary"],
        "order_attempt_summary": findings["order_attempt_summary"],
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(clear, requires_review, evidence_ready, findings["missing_requirements"]),
    }


def accept_live_recovery_review(
    *,
    notes: str = "",
    confirm_owner_accept: bool = False,
    broker_truth_report: Mapping[str, Any] | None = None,
    live_pilot_policy: Mapping[str, Any] | None = None,
    order_attempt_status: Mapping[str, Any] | None = None,
    state_path: Path | str | None = None,
    audit_path: Path | str | None = None,
) -> dict[str, Any]:
    if not confirm_owner_accept:
        raise LiveRecoveryError("confirm_owner_accept=true is required to ACCEPT live recovery review")
    report = build_live_recovery_report(
        broker_truth_report=broker_truth_report,
        live_pilot_policy=live_pilot_policy,
        order_attempt_status=order_attempt_status,
        state_path=state_path,
    )
    if not report["requires_recovery_review"]:
        raise LiveRecoveryError("No live recovery review is currently required")
    if not report["evidence_ready_for_owner_accept"]:
        raise LiveRecoveryError("Cannot ACCEPT live recovery review; missing: " + "; ".join(report["missing_requirements"]))
    payload = {
        "owner_recovery_status": STATUS_ACCEPT,
        "owner_accepted_at": utc_now().isoformat(),
        "accepted_fingerprint": report["current_fingerprint"],
        "notes": str(notes or "").strip(),
    }
    _write_json(payload, _state_path(state_path))
    _append_audit(
        {
            "action": "live_recovery_accept",
            "timestamp": utc_now().isoformat(),
            "accepted_fingerprint": report["current_fingerprint"],
            "notes": payload["notes"],
        },
        _audit_path(audit_path),
    )
    return build_live_recovery_report(
        broker_truth_report=broker_truth_report,
        live_pilot_policy=live_pilot_policy,
        order_attempt_status=order_attempt_status,
        state_path=state_path,
    )


def reset_live_recovery_review(
    *,
    reason: str = "OWNER_RESET",
    state_path: Path | str | None = None,
    audit_path: Path | str | None = None,
) -> dict[str, Any]:
    payload = {
        "owner_recovery_status": STATUS_OPEN,
        "owner_accepted_at": None,
        "accepted_fingerprint": None,
        "notes": "",
    }
    _write_json(payload, _state_path(state_path))
    _append_audit(
        {
            "action": "live_recovery_reset",
            "timestamp": utc_now().isoformat(),
            "reason": str(reason or "OWNER_RESET"),
        },
        _audit_path(audit_path),
    )
    return build_live_recovery_report(state_path=state_path)


def is_live_recovery_clear_for_live() -> bool:
    return bool(build_live_recovery_report().get("recovery_clear_for_live", False))


def _findings(
    broker_truth: Mapping[str, Any] | None,
    pilot: Mapping[str, Any],
    order_attempts: Mapping[str, Any],
    *,
    fresh_seconds: int,
) -> dict[str, Any]:
    truth = dict(broker_truth or {})
    attempts = dict(order_attempts or {})
    live_trade_count = int(pilot.get("live_trade_count", 0) or 0)
    last_live_order_at = pilot.get("last_live_order_at")
    mt5_open = int(truth.get("mt5_open_position_count", 0) or 0) if truth else 0
    unmatched = int(truth.get("terminal_unmatched_open_position_count", 0) or 0) if truth else 0
    pending = int(truth.get("terminal_pending_receipt_count", 0) or 0) if truth else 0
    receipt_mismatch = int(truth.get("terminal_receipt_mismatch_count", 0) or 0) if truth else 0
    unresolved_rows = [
        dict(row)
        for row in attempts.get("unresolved_real_attempts", [])
        if isinstance(row, Mapping)
    ]
    classified_attempts = [_classify_unresolved_attempt(row) for row in unresolved_rows]
    synthetic_like_count = sum(1 for row in classified_attempts if row["classification_status"] == "SYNTHETIC_TEST_LIKE")
    broker_review_required_count = sum(1 for row in classified_attempts if row["classification_status"] == "BROKER_REVIEW_REQUIRED")
    unresolved_real = int(attempts.get("unresolved_real_attempt_count", len(unresolved_rows)) or len(unresolved_rows))
    unknown_unresolved_count = max(0, unresolved_real - len(classified_attempts))
    broker_review_required_count += unknown_unresolved_count
    has_unresolved_real = broker_review_required_count > 0
    requires = (
        live_trade_count > 0
        or bool(last_live_order_at)
        or mt5_open > 0
        or unmatched > 0
        or pending > 0
        or receipt_mismatch > 0
        or has_unresolved_real
    )
    fresh = _fresh_enough(truth, fresh_seconds=fresh_seconds)
    connected = bool(truth.get("mt5_connected", False))
    live_visible = connected and truth.get("mt5_is_demo") is False
    failed = str(truth.get("overall_status") or "") == RECONCILIATION_FAILED

    checks = [
        _check("prior_live_activity_or_positions", "OK" if requires else "CLEAR", {"live_trade_count": live_trade_count, "mt5_open_positions": mt5_open}, "Recovery review is required after live activity or visible positions." if requires else "No prior live activity or broker-visible positions require recovery review."),
        _check("broker_truth_present", "OK" if truth else "MISSING", {"present": bool(truth)}, "Latest broker-truth report is present." if truth else "No broker-truth report is available."),
        _check("broker_truth_fresh", "OK" if fresh else "MISSING", {"generated_at": truth.get("generated_at"), "fresh_seconds": fresh_seconds}, "Latest broker-truth report is fresh." if fresh else "Latest broker-truth report is missing or stale."),
        _check("live_account_visible", "OK" if live_visible else "MISSING", {"mt5_connected": connected, "mt5_is_demo": truth.get("mt5_is_demo")}, "Live MT5 account is visible." if live_visible else "A connected live MT5 account is not visible."),
        _check("position_reconciliation_clean", "OK" if not failed and unmatched == 0 and pending == 0 and receipt_mismatch == 0 else "MISSING", {"overall_status": truth.get("overall_status"), "unmatched": unmatched, "pending": pending, "receipt_mismatch": receipt_mismatch}, "Open-position reconciliation is clean." if not failed and unmatched == 0 and pending == 0 and receipt_mismatch == 0 else "Open-position reconciliation is failed, pending, or unmatched."),
        _check(
            "synthetic_test_like_attempts_classified",
            "OK",
            {
                "synthetic_test_like_count": synthetic_like_count,
                "broker_review_required_count": broker_review_required_count,
                "unknown_unresolved_count": unknown_unresolved_count,
            },
            (
                "Unresolved synthetic/test-like attempts are classified separately and do not block live recovery by themselves."
                if synthetic_like_count
                else "No unresolved synthetic/test-like attempts are present."
            ),
        ),
        _check("unresolved_real_order_attempts_clear", "OK" if not has_unresolved_real else "MISSING", {"unresolved_real_attempt_count": unresolved_real, "has_unresolved_real_attempt": has_unresolved_real, "broker_review_required_count": broker_review_required_count, "unknown_unresolved_count": unknown_unresolved_count}, "No broker-review-required unresolved real order attempts are open." if not has_unresolved_real else "A real broker order attempt was started but not finalized; reconcile broker truth before any more live orders."),
    ]
    missing = [
        check["check_id"]
        for check in checks
        if requires and check["status"] == "MISSING"
    ]
    evidence_ready = requires and not missing
    return {
        "requires_recovery_review": requires,
        "evidence_ready_for_owner_accept": evidence_ready,
        "missing_requirements": missing,
        "checks": checks,
        "broker_truth_summary": {
            "present": bool(truth),
            "generated_at": truth.get("generated_at"),
            "overall_status": truth.get("overall_status"),
            "mt5_connected": truth.get("mt5_connected"),
            "mt5_is_demo": truth.get("mt5_is_demo"),
            "mt5_open_position_count": mt5_open,
            "terminal_unmatched_open_position_count": unmatched,
            "terminal_pending_receipt_count": pending,
            "terminal_receipt_mismatch_count": receipt_mismatch,
        },
        "live_pilot_summary": {
            "live_trade_count": live_trade_count,
            "last_live_order_at": last_live_order_at,
            "owner_pilot_status": pilot.get("owner_pilot_status"),
        },
        "order_attempt_summary": {
            "present": bool(attempts),
            "attempt_count": attempts.get("attempt_count", 0),
            "real_attempt_count": attempts.get("real_attempt_count", 0),
            "unresolved_attempt_count": attempts.get("unresolved_attempt_count", 0),
            "unresolved_real_attempt_count": unresolved_real,
            "synthetic_test_like_unresolved_attempt_count": synthetic_like_count,
            "broker_review_required_unresolved_attempt_count": broker_review_required_count,
            "unknown_unresolved_attempt_count": unknown_unresolved_count,
            "unresolved_real_attempts": classified_attempts,
            "has_unresolved_real_attempt": has_unresolved_real,
            "latest_attempt": attempts.get("latest_attempt"),
        },
    }


def _check(check_id: str, status: str, evidence: Mapping[str, Any], detail: str) -> dict[str, Any]:
    return {"check_id": check_id, "status": status, "evidence": dict(evidence), "detail": detail}


def _classify_unresolved_attempt(row: Mapping[str, Any]) -> dict[str, Any]:
    """Classify old fake/test bridge attempts so they do not masquerade as broker risk."""

    bridge = str(row.get("bridge_name") or "")
    order_id = str(row.get("order_id") or "")
    decision_ref = str(row.get("decision_ref") or "")
    source = str(row.get("source") or "")
    reasons: list[str] = []
    if bridge.startswith("_") or "fake" in bridge.lower():
        reasons.append("bridge_name_is_test_like")
    if order_id.startswith(("ord-1", "compound-add-1", "waste-add-dref-test")):
        reasons.append("order_id_matches_test_fixture_pattern")
    if decision_ref.startswith(("dec-1", "compound-add-ref-1", "dref-test-")):
        reasons.append("decision_ref_matches_test_fixture_pattern")
    if source in {"test_crash_window", "waste_compound_add_handoff"} and "fake" in bridge.lower():
        reasons.append("source_bridge_pair_is_test_like")

    classified = dict(row)
    classified["classification_status"] = "SYNTHETIC_TEST_LIKE" if reasons else "BROKER_REVIEW_REQUIRED"
    classified["classification_reasons"] = reasons
    classified["live_recovery_blocks"] = classified["classification_status"] == "BROKER_REVIEW_REQUIRED"
    return classified


def _fingerprint(
    broker_truth: Mapping[str, Any] | None,
    pilot: Mapping[str, Any],
    order_attempts: Mapping[str, Any],
) -> str:
    truth = dict(broker_truth or {})
    attempts = dict(order_attempts or {})
    latest_attempt = attempts.get("latest_attempt")
    latest_attempt = latest_attempt if isinstance(latest_attempt, Mapping) else {}
    classified_attempts = [
        _classify_unresolved_attempt(row)
        for row in attempts.get("unresolved_real_attempts", [])
        if isinstance(row, Mapping)
    ]
    synthetic_like_count = sum(1 for row in classified_attempts if row["classification_status"] == "SYNTHETIC_TEST_LIKE")
    broker_review_required_count = sum(1 for row in classified_attempts if row["classification_status"] == "BROKER_REVIEW_REQUIRED")
    unresolved_real = int(attempts.get("unresolved_real_attempt_count", len(classified_attempts)) or len(classified_attempts))
    unknown_unresolved_count = max(0, unresolved_real - len(classified_attempts))
    broker_review_required_count += unknown_unresolved_count
    material = {
        "truth_generated_at": truth.get("generated_at"),
        "truth_status": truth.get("overall_status"),
        "mt5_open": truth.get("mt5_open_position_count"),
        "unmatched": truth.get("terminal_unmatched_open_position_count"),
        "pending": truth.get("terminal_pending_receipt_count"),
        "receipt_mismatch": truth.get("terminal_receipt_mismatch_count"),
        "live_trade_count": pilot.get("live_trade_count"),
        "last_live_order_at": pilot.get("last_live_order_at"),
        "order_attempt_count": attempts.get("attempt_count"),
        "order_real_attempt_count": attempts.get("real_attempt_count"),
        "unresolved_attempt_count": attempts.get("unresolved_attempt_count"),
        "unresolved_real_attempt_count": attempts.get("unresolved_real_attempt_count"),
        "has_unresolved_real_attempt": broker_review_required_count > 0,
        "synthetic_test_like_unresolved_attempt_count": synthetic_like_count,
        "broker_review_required_unresolved_attempt_count": broker_review_required_count,
        "unknown_unresolved_attempt_count": unknown_unresolved_count,
        "latest_attempt_id": latest_attempt.get("attempt_id"),
        "latest_attempt_status": latest_attempt.get("status"),
        "latest_attempt_result_finalized": latest_attempt.get("result_finalized"),
        "latest_attempt_result_status": latest_attempt.get("result_status"),
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:24]


def _fresh_enough(report: Mapping[str, Any], *, fresh_seconds: int) -> bool:
    generated_at = report.get("generated_at")
    if not generated_at:
        return False
    try:
        generated = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
        return (utc_now() - generated).total_seconds() <= max(1, int(fresh_seconds))
    except Exception:
        return False


def _next_action(
    clear: bool,
    requires_review: bool,
    evidence_ready: bool,
    missing_requirements: list[str],
) -> str:
    if clear:
        return "Live recovery is clear for the current broker-truth and live-pilot evidence."
    if not requires_review:
        return "No prior live activity requires recovery review."
    if "unresolved_real_order_attempts_clear" in missing_requirements:
        return "Reconcile unresolved real order attempts against broker truth before owner-reviewing recovery."
    if evidence_ready:
        return "Owner-review the fresh broker-truth recovery evidence and confirm ACCEPT before any more live orders."
    return "Refresh broker-truth monitoring until live account and open-position reconciliation are clean, then owner-review recovery."


def _latest_broker_truth() -> dict[str, Any] | None:
    try:
        from cas_forex.broker_truth_monitor import load_latest_broker_truth_monitor_report

        return load_latest_broker_truth_monitor_report()
    except Exception:
        return None


def _live_pilot_policy() -> dict[str, Any]:
    try:
        from cas_forex.live_pilot import build_live_pilot_policy

        return build_live_pilot_policy()
    except Exception:
        return {}


def _order_attempt_status() -> dict[str, Any]:
    try:
        from cas_forex.order_attempt_audit import build_order_attempt_audit_status

        return build_order_attempt_audit_status()
    except Exception:
        return {}


def _load_state(path: Path | str | None) -> dict[str, Any]:
    target = _state_path(path)
    if not target.exists():
        return {"owner_recovery_status": STATUS_OPEN, "owner_accepted_at": None, "accepted_fingerprint": None, "notes": ""}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"owner_recovery_status": STATUS_OPEN, "owner_accepted_at": None, "accepted_fingerprint": None, "notes": ""}
    return payload if isinstance(payload, dict) else {}


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
