"""Owner review gate for passing live-order dry-run evidence.

The dry-run audit proves a proposed live order would clear the base live gates
without touching the broker. This module records the owner's explicit ACCEPT of
that exact evidence fingerprint before real live dispatch is allowed.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional

from cas_forex.account_reconciliation import RECONCILIATION_FAILED
from cas_forex.live_order_dry_run import DEFAULT_AUDIT_PATH as DEFAULT_DRY_RUN_AUDIT_PATH
from cas_forex.live_order_dry_run import STATUS_PASS, LiveOrderDryRunAuditLog
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "live-order-dry-run-review.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "live-order-dry-run-review-audit.jsonl"

REPORT_KIND = "cas_forex_live_order_dry_run_review"
STATUS_OPEN = "OPEN"
STATUS_ACCEPT = "ACCEPT"
DEFAULT_FRESH_SECONDS = 300

CLAIM_BOUNDARY = (
    "Live-order dry-run review is an owner ACCEPT gate tied to the latest "
    "passing dry-run evidence and fresh live broker truth. It does not place "
    "orders, close positions, create broker ACCEPT, deposit, withdraw, move "
    "bank/card money, automate payouts, mint edge tokens, or authorize live "
    "trading by itself."
)


class LiveOrderDryRunReviewError(ValueError):
    """Raised when dry-run review cannot be accepted or loaded."""


def build_live_order_dry_run_review(
    *,
    dry_run_audit: Optional[Mapping[str, Any]] = None,
    broker_truth_report: Optional[Mapping[str, Any]] = None,
    state_path: Path | str | None = None,
    dry_run_audit_path: Path | str | None = None,
    fresh_seconds: int = DEFAULT_FRESH_SECONDS,
) -> dict[str, Any]:
    state = _load_state(state_path)
    dry_run_record = dict(dry_run_audit) if dry_run_audit is not None else _latest_dry_run(dry_run_audit_path)
    dry_run_payload = _dry_run_payload(dry_run_record)
    broker_truth = dict(broker_truth_report) if broker_truth_report is not None else _latest_broker_truth()
    findings = _findings(dry_run_record, dry_run_payload, broker_truth, fresh_seconds=fresh_seconds)
    fingerprint = _fingerprint(dry_run_record, dry_run_payload, broker_truth)
    accepted_current = (
        state.get("owner_review_status") == STATUS_ACCEPT
        and state.get("accepted_fingerprint") == fingerprint
    )
    evidence_ready = bool(findings["evidence_ready_for_owner_accept"])
    clear = accepted_current and evidence_ready
    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "review_status": STATUS_ACCEPT if clear else STATUS_OPEN,
        "owner_review_status": state.get("owner_review_status", STATUS_OPEN),
        "owner_accepted_at": state.get("owner_accepted_at"),
        "accepted_fingerprint": state.get("accepted_fingerprint"),
        "current_fingerprint": fingerprint,
        "dry_run_review_clear_for_live": clear,
        "evidence_ready_for_owner_accept": evidence_ready,
        "missing_requirements": [] if clear else findings["missing_requirements"],
        "checks": findings["checks"],
        "latest_dry_run_summary": findings["latest_dry_run_summary"],
        "broker_truth_summary": findings["broker_truth_summary"],
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(clear, evidence_ready),
    }


def accept_live_order_dry_run_review(
    *,
    notes: str = "",
    confirm_owner_accept: bool = False,
    dry_run_audit: Optional[Mapping[str, Any]] = None,
    broker_truth_report: Optional[Mapping[str, Any]] = None,
    state_path: Path | str | None = None,
    audit_path: Path | str | None = None,
    dry_run_audit_path: Path | str | None = None,
) -> dict[str, Any]:
    if not confirm_owner_accept:
        raise LiveOrderDryRunReviewError("confirm_owner_accept=true is required to ACCEPT live-order dry-run review")
    report = build_live_order_dry_run_review(
        dry_run_audit=dry_run_audit,
        broker_truth_report=broker_truth_report,
        state_path=state_path,
        dry_run_audit_path=dry_run_audit_path,
    )
    if not report["evidence_ready_for_owner_accept"]:
        raise LiveOrderDryRunReviewError(
            "Cannot ACCEPT live-order dry-run review; missing: "
            + "; ".join(report["missing_requirements"])
        )
    payload = {
        "owner_review_status": STATUS_ACCEPT,
        "owner_accepted_at": utc_now().isoformat(),
        "accepted_fingerprint": report["current_fingerprint"],
        "notes": str(notes or "").strip(),
    }
    _write_json(payload, _state_path(state_path))
    _append_audit(
        {
            "action": "live_order_dry_run_review_accept",
            "timestamp": utc_now().isoformat(),
            "accepted_fingerprint": report["current_fingerprint"],
            "dry_run_order_id": report["latest_dry_run_summary"].get("order_id"),
            "dry_run_decision_ref": report["latest_dry_run_summary"].get("decision_ref"),
            "notes": payload["notes"],
        },
        _audit_path(audit_path),
    )
    return build_live_order_dry_run_review(
        dry_run_audit=dry_run_audit,
        broker_truth_report=broker_truth_report,
        state_path=state_path,
        dry_run_audit_path=dry_run_audit_path,
    )


def reset_live_order_dry_run_review(
    *,
    reason: str = "OWNER_RESET",
    state_path: Path | str | None = None,
    audit_path: Path | str | None = None,
) -> dict[str, Any]:
    payload = {
        "owner_review_status": STATUS_OPEN,
        "owner_accepted_at": None,
        "accepted_fingerprint": None,
        "notes": "",
    }
    _write_json(payload, _state_path(state_path))
    _append_audit(
        {
            "action": "live_order_dry_run_review_reset",
            "timestamp": utc_now().isoformat(),
            "reason": str(reason or "OWNER_RESET"),
        },
        _audit_path(audit_path),
    )
    return build_live_order_dry_run_review(state_path=state_path)


def is_live_order_dry_run_review_clear_for_live() -> bool:
    return bool(build_live_order_dry_run_review().get("dry_run_review_clear_for_live", False))


def _findings(
    dry_run_record: Mapping[str, Any],
    dry_run_payload: Mapping[str, Any],
    broker_truth: Mapping[str, Any],
    *,
    fresh_seconds: int,
) -> dict[str, Any]:
    dry_run_present = bool(dry_run_payload)
    dry_run_passed = str(dry_run_payload.get("status") or dry_run_record.get("status") or "") == STATUS_PASS
    broker_touched = bool(dry_run_payload.get("broker_touched", dry_run_record.get("broker_touched", False)))
    dry_run_fresh = _fresh_enough(dry_run_payload.get("generated_at") or dry_run_record.get("timestamp"), fresh_seconds=fresh_seconds)
    checks_list = dry_run_payload.get("checks") if isinstance(dry_run_payload.get("checks"), list) else []
    all_dry_run_checks_pass = bool(checks_list) and all(bool(check.get("passed", False)) for check in checks_list if isinstance(check, Mapping))
    live_gate_passed = any(
        isinstance(check, Mapping)
        and check.get("check_id") == "live_trading_gate"
        and bool(check.get("passed", False))
        for check in checks_list
    )

    truth_present = bool(broker_truth)
    truth_fresh = _fresh_enough(broker_truth.get("generated_at"), fresh_seconds=fresh_seconds)
    truth_identity_matches = broker_truth.get("mt5_account_identity_matches_config") is True
    truth_live_visible = (
        bool(broker_truth.get("mt5_connected"))
        and broker_truth.get("mt5_is_demo") is False
        and truth_identity_matches
    )
    truth_reconciled = str(broker_truth.get("overall_status") or "") != RECONCILIATION_FAILED

    checks = [
        _check("dry_run_present", dry_run_present, {"present": dry_run_present}, "Latest live-order dry-run audit is present." if dry_run_present else "No live-order dry-run audit is present."),
        _check("dry_run_passed", dry_run_passed, {"status": dry_run_payload.get("status") or dry_run_record.get("status")}, "Latest live-order dry run passed." if dry_run_passed else "Latest live-order dry run did not pass."),
        _check("dry_run_broker_not_touched", not broker_touched, {"broker_touched": broker_touched}, "Dry run did not touch a broker bridge." if not broker_touched else "Dry-run record says a broker was touched; refuse review."),
        _check("dry_run_fresh", dry_run_fresh, {"generated_at": dry_run_payload.get("generated_at"), "fresh_seconds": fresh_seconds}, "Dry-run evidence is fresh." if dry_run_fresh else "Dry-run evidence is missing or stale."),
        _check("dry_run_checks_all_pass", all_dry_run_checks_pass, {"check_count": len(checks_list)}, "All dry-run checks passed." if all_dry_run_checks_pass else "At least one dry-run check is missing or blocked."),
        _check("dry_run_live_gate_passed", live_gate_passed, {}, "Dry-run base live gate passed." if live_gate_passed else "Dry-run base live gate did not pass."),
        _check("broker_truth_present", truth_present, {"present": truth_present}, "Latest broker-truth report is present." if truth_present else "No broker-truth report is present."),
        _check("broker_truth_fresh", truth_fresh, {"generated_at": broker_truth.get("generated_at"), "fresh_seconds": fresh_seconds}, "Broker truth is fresh." if truth_fresh else "Broker truth is missing or stale."),
        _check(
            "live_account_visible",
            truth_live_visible,
            {
                "mt5_connected": broker_truth.get("mt5_connected"),
                "mt5_is_demo": broker_truth.get("mt5_is_demo"),
                "mt5_account": broker_truth.get("mt5_account"),
                "mt5_account_server": broker_truth.get("mt5_account_server"),
                "mt5_expected_account": broker_truth.get("mt5_expected_account"),
                "mt5_expected_server": broker_truth.get("mt5_expected_server"),
                "mt5_account_identity_matches_config": broker_truth.get("mt5_account_identity_matches_config"),
            },
            "The live MT5 account matches the configured owner login/server."
            if truth_live_visible
            else "A connected live MT5 account matching the configured owner login/server is not visible.",
        ),
        _check("broker_truth_reconciled", truth_reconciled, {"overall_status": broker_truth.get("overall_status")}, "Broker truth is not reporting reconciliation failure." if truth_reconciled else "Broker truth is reporting reconciliation failure."),
    ]
    missing = [check["check_id"] for check in checks if check["status"] != "OK"]
    return {
        "evidence_ready_for_owner_accept": not missing,
        "missing_requirements": missing,
        "checks": checks,
        "latest_dry_run_summary": {
            "present": dry_run_present,
            "audit_id": dry_run_record.get("audit_id"),
            "status": dry_run_payload.get("status") or dry_run_record.get("status"),
            "order_id": dry_run_payload.get("order_id") or dry_run_record.get("order_id"),
            "decision_ref": dry_run_payload.get("decision_ref") or dry_run_record.get("decision_ref"),
            "generated_at": dry_run_payload.get("generated_at"),
            "broker_touched": broker_touched,
            "would_reach_broker_if_executed": bool(dry_run_payload.get("would_reach_broker_if_executed", False)),
        },
        "broker_truth_summary": {
            "present": truth_present,
            "generated_at": broker_truth.get("generated_at"),
            "overall_status": broker_truth.get("overall_status"),
            "mt5_connected": broker_truth.get("mt5_connected"),
            "mt5_is_demo": broker_truth.get("mt5_is_demo"),
            "mt5_account": broker_truth.get("mt5_account"),
            "mt5_account_server": broker_truth.get("mt5_account_server"),
            "mt5_expected_account": broker_truth.get("mt5_expected_account"),
            "mt5_expected_server": broker_truth.get("mt5_expected_server"),
            "mt5_account_identity_matches_config": broker_truth.get("mt5_account_identity_matches_config"),
            "mt5_open_position_count": broker_truth.get("mt5_open_position_count"),
        },
    }


def _check(check_id: str, ok: bool, evidence: Mapping[str, Any], detail: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "OK" if ok else "MISSING",
        "evidence": dict(evidence),
        "detail": detail,
    }


def _fingerprint(
    dry_run_record: Mapping[str, Any],
    dry_run_payload: Mapping[str, Any],
    broker_truth: Mapping[str, Any],
) -> str:
    material = {
        "dry_run_audit_id": dry_run_record.get("audit_id"),
        "dry_run_status": dry_run_payload.get("status") or dry_run_record.get("status"),
        "dry_run_generated_at": dry_run_payload.get("generated_at"),
        "dry_run_order_id": dry_run_payload.get("order_id") or dry_run_record.get("order_id"),
        "dry_run_decision_ref": dry_run_payload.get("decision_ref") or dry_run_record.get("decision_ref"),
        "dry_run_intent": dry_run_payload.get("proposed_intent"),
        "dry_run_order": dry_run_payload.get("order_request"),
        "dry_run_checks": [
            {"check_id": c.get("check_id"), "passed": c.get("passed"), "status": c.get("status")}
            for c in dry_run_payload.get("checks", [])
            if isinstance(c, Mapping)
        ],
        "broker_truth_generated_at": broker_truth.get("generated_at"),
        "broker_truth_status": broker_truth.get("overall_status"),
        "mt5_connected": broker_truth.get("mt5_connected"),
        "mt5_is_demo": broker_truth.get("mt5_is_demo"),
        "mt5_account": broker_truth.get("mt5_account"),
        "mt5_account_server": broker_truth.get("mt5_account_server"),
        "mt5_expected_account": broker_truth.get("mt5_expected_account"),
        "mt5_expected_server": broker_truth.get("mt5_expected_server"),
        "mt5_account_identity_matches_config": broker_truth.get("mt5_account_identity_matches_config"),
        "mt5_open_position_count": broker_truth.get("mt5_open_position_count"),
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:24]


def _dry_run_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = record.get("payload") if isinstance(record, Mapping) else None
    return dict(payload) if isinstance(payload, Mapping) else {}


def _fresh_enough(value: Any, *, fresh_seconds: int) -> bool:
    if not value:
        return False
    try:
        generated = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return 0 <= (utc_now() - generated).total_seconds() <= max(1, int(fresh_seconds))
    except Exception:
        return False


def _next_action(clear: bool, evidence_ready: bool) -> str:
    if clear:
        return "Owner ACCEPT is current for the latest passing dry-run and fresh broker-truth evidence."
    if evidence_ready:
        return "Owner-review the passing dry-run and fresh broker-truth evidence, then confirm ACCEPT."
    return "Run a fresh passing live-order dry run against fresh live broker truth before owner ACCEPT."


def _latest_dry_run(path: Path | str | None) -> dict[str, Any]:
    target = Path(path) if path is not None else Path(DEFAULT_DRY_RUN_AUDIT_PATH)
    latest = LiveOrderDryRunAuditLog(target).latest()
    return latest if isinstance(latest, dict) else {}


def _latest_broker_truth() -> dict[str, Any]:
    try:
        from cas_forex.broker_truth_monitor import load_latest_broker_truth_monitor_report

        return load_latest_broker_truth_monitor_report()
    except Exception:
        return {}


def _load_state(path: Path | str | None) -> dict[str, Any]:
    target = _state_path(path)
    if not target.exists():
        return {"owner_review_status": STATUS_OPEN, "owner_accepted_at": None, "accepted_fingerprint": None, "notes": ""}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"owner_review_status": STATUS_OPEN, "owner_accepted_at": None, "accepted_fingerprint": None, "notes": ""}
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
