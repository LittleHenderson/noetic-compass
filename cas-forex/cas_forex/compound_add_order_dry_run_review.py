"""Owner review gate for passing compound-add dry-run evidence.

The compound-add dry run proves that one exact pyramid/add order would clear
the add-specific context checks plus the normal live-order gates without
touching a broker. This module records the owner's explicit ACCEPT of that
exact add fingerprint before a future pyramid dispatch path can use it.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional

from cas_forex.account_reconciliation import RECONCILIATION_FAILED
from cas_forex.live_order_dry_run import (
    COMPOUND_ADD_REPORT_KIND,
    DEFAULT_COMPOUND_ADD_AUDIT_PATH as DEFAULT_DRY_RUN_AUDIT_PATH,
    STATUS_PASS,
    LiveOrderDryRunAuditLog,
)
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "compound-add-order-dry-run-review.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "compound-add-order-dry-run-review-audit.jsonl"

REPORT_KIND = "cas_forex_compound_add_order_dry_run_review"
STATUS_OPEN = "OPEN"
STATUS_ACCEPT = "ACCEPT"
DEFAULT_FRESH_SECONDS = 300

CLAIM_BOUNDARY = (
    "Compound-add dry-run review is an owner ACCEPT gate tied to the latest "
    "passing compound-add dry-run evidence and fresh live broker-truth/open-"
    "position evidence. It does not place add orders, close positions, create "
    "broker ACCEPT, deposit, withdraw, move bank/card money, automate payouts, "
    "mint edge tokens, or authorize live trading by itself."
)


class CompoundAddOrderDryRunReviewError(ValueError):
    """Raised when compound-add review cannot be accepted or loaded."""


def build_compound_add_order_dry_run_review(
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
        "compound_add_dry_run_review_clear_for_dispatch": clear,
        "evidence_ready_for_owner_accept": evidence_ready,
        "missing_requirements": [] if clear else findings["missing_requirements"],
        "checks": findings["checks"],
        "latest_compound_add_summary": findings["latest_compound_add_summary"],
        "broker_truth_summary": findings["broker_truth_summary"],
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(clear, evidence_ready),
    }


def accept_compound_add_order_dry_run_review(
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
        raise CompoundAddOrderDryRunReviewError(
            "confirm_owner_accept=true is required to ACCEPT compound-add dry-run review"
        )
    report = build_compound_add_order_dry_run_review(
        dry_run_audit=dry_run_audit,
        broker_truth_report=broker_truth_report,
        state_path=state_path,
        dry_run_audit_path=dry_run_audit_path,
    )
    if not report["evidence_ready_for_owner_accept"]:
        raise CompoundAddOrderDryRunReviewError(
            "Cannot ACCEPT compound-add dry-run review; missing: "
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
            "action": "compound_add_order_dry_run_review_accept",
            "timestamp": utc_now().isoformat(),
            "accepted_fingerprint": report["current_fingerprint"],
            "add_order_id": report["latest_compound_add_summary"].get("order_id"),
            "add_decision_ref": report["latest_compound_add_summary"].get("decision_ref"),
            "parent_order_id": report["latest_compound_add_summary"].get("parent_order_id"),
            "parent_decision_ref": report["latest_compound_add_summary"].get("parent_decision_ref"),
            "broker_ticket": report["latest_compound_add_summary"].get("broker_ticket"),
            "notes": payload["notes"],
        },
        _audit_path(audit_path),
    )
    return build_compound_add_order_dry_run_review(
        dry_run_audit=dry_run_audit,
        broker_truth_report=broker_truth_report,
        state_path=state_path,
        dry_run_audit_path=dry_run_audit_path,
    )


def reset_compound_add_order_dry_run_review(
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
            "action": "compound_add_order_dry_run_review_reset",
            "timestamp": utc_now().isoformat(),
            "reason": str(reason or "OWNER_RESET"),
        },
        _audit_path(audit_path),
    )
    return build_compound_add_order_dry_run_review(state_path=state_path)


def is_compound_add_order_dry_run_review_clear_for_dispatch() -> bool:
    return bool(
        build_compound_add_order_dry_run_review().get(
            "compound_add_dry_run_review_clear_for_dispatch",
            False,
        )
    )


def require_current_compound_add_order_dry_run_review(
    order: Any,
    *,
    dry_run_audit_path: Path | str | None = None,
    broker_truth_report: Optional[Mapping[str, Any]] = None,
    state_path: Path | str | None = None,
) -> dict[str, Any]:
    """Raise unless owner ACCEPT is current for this exact add order.

    This is the dispatch-time lock. The review can only become clear from the
    latest passing compound-add dry run plus fresh broker-position truth; this
    function also compares the order about to hit the broker bridge against that
    accepted dry-run order geometry.
    """

    report = build_compound_add_order_dry_run_review(
        dry_run_audit_path=dry_run_audit_path,
        broker_truth_report=broker_truth_report,
        state_path=state_path,
    )
    if not bool(report.get("compound_add_dry_run_review_clear_for_dispatch", False)):
        missing = "; ".join(report.get("missing_requirements") or ["owner ACCEPT is not current"])
        raise CompoundAddOrderDryRunReviewError(
            "Compound-add owner ACCEPT is not current for dispatch; missing: " + missing
        )
    dry_run_record = _latest_dry_run(dry_run_audit_path)
    dry_run_payload = _dry_run_payload(dry_run_record)
    mismatches = _order_mismatches(order, dry_run_payload)
    if mismatches:
        raise CompoundAddOrderDryRunReviewError(
            "Compound-add order does not match owner-accepted dry-run: "
            + "; ".join(mismatches)
        )
    return report


def _findings(
    dry_run_record: Mapping[str, Any],
    dry_run_payload: Mapping[str, Any],
    broker_truth: Mapping[str, Any],
    *,
    fresh_seconds: int,
) -> dict[str, Any]:
    dry_run_present = bool(dry_run_payload)
    dry_run_kind_ok = str(dry_run_payload.get("report_kind") or "") == COMPOUND_ADD_REPORT_KIND
    dry_run_passed = str(dry_run_payload.get("status") or dry_run_record.get("status") or "") == STATUS_PASS
    broker_touched = bool(dry_run_payload.get("broker_touched", dry_run_record.get("broker_touched", False)))
    dry_run_fresh = _fresh_enough(dry_run_payload.get("generated_at") or dry_run_record.get("timestamp"), fresh_seconds=fresh_seconds)
    checks_list = dry_run_payload.get("checks") if isinstance(dry_run_payload.get("checks"), list) else []
    all_dry_run_checks_pass = bool(checks_list) and all(
        bool(check.get("passed", False)) for check in checks_list if isinstance(check, Mapping)
    )
    compound_context = dry_run_payload.get("compound_context")
    compound_context = compound_context if isinstance(compound_context, Mapping) else {}
    compound_decision = compound_context.get("compound_decision")
    compound_decision = compound_decision if isinstance(compound_decision, Mapping) else {}
    compound_decision_add = str(compound_decision.get("action") or "").upper() == "ADD"
    parent_reference_present = bool(dry_run_payload.get("parent_order_id") or dry_run_payload.get("broker_ticket"))
    base_live_passed = isinstance(dry_run_payload.get("base_live_order_dry_run"), Mapping) and str(
        dry_run_payload["base_live_order_dry_run"].get("status") or ""
    ) == STATUS_PASS
    edge_passed = _dry_run_check_passed(checks_list, "edge_pass_token")
    broker_truth_position_passed = _dry_run_check_passed(checks_list, "broker_truth_position")

    truth_present = bool(broker_truth)
    truth_fresh = _fresh_enough(broker_truth.get("generated_at"), fresh_seconds=fresh_seconds)
    truth_identity_matches = broker_truth.get("mt5_account_identity_matches_config") is True
    truth_live_visible = (
        bool(broker_truth.get("mt5_connected"))
        and broker_truth.get("mt5_is_demo") is False
        and truth_identity_matches
    )
    truth_reconciled = str(broker_truth.get("overall_status") or "") != RECONCILIATION_FAILED
    open_position_count = _int_value(broker_truth.get("mt5_open_position_count"))
    unmatched_positions = _int_value(broker_truth.get("terminal_unmatched_open_position_count"))
    receipt_mismatches = _int_value(broker_truth.get("terminal_receipt_mismatch_count"))
    pending_receipts = _int_value(broker_truth.get("terminal_pending_receipt_count"))
    live_open_position_visible = open_position_count is not None and open_position_count >= 1
    no_open_position_mismatch = (unmatched_positions or 0) == 0 and (receipt_mismatches or 0) == 0
    no_pending_receipts = (pending_receipts or 0) == 0

    checks = [
        _check("compound_add_dry_run_present", dry_run_present, {"present": dry_run_present}, "Latest compound-add dry-run audit is present." if dry_run_present else "No compound-add dry-run audit is present."),
        _check("compound_add_report_kind", dry_run_kind_ok, {"report_kind": dry_run_payload.get("report_kind")}, "Latest dry-run record is a compound-add report." if dry_run_kind_ok else "Latest dry-run record is not a compound-add report."),
        _check("compound_add_dry_run_passed", dry_run_passed, {"status": dry_run_payload.get("status") or dry_run_record.get("status")}, "Latest compound-add dry run passed." if dry_run_passed else "Latest compound-add dry run did not pass."),
        _check("compound_add_broker_not_touched", not broker_touched, {"broker_touched": broker_touched}, "Compound-add dry run did not touch a broker bridge." if not broker_touched else "Dry-run record says a broker was touched; refuse review."),
        _check("compound_add_dry_run_fresh", dry_run_fresh, {"generated_at": dry_run_payload.get("generated_at"), "fresh_seconds": fresh_seconds}, "Compound-add dry-run evidence is fresh." if dry_run_fresh else "Compound-add dry-run evidence is missing or stale."),
        _check("compound_add_checks_all_pass", all_dry_run_checks_pass, {"check_count": len(checks_list)}, "All compound-add dry-run checks passed." if all_dry_run_checks_pass else "At least one compound-add dry-run check is missing or blocked."),
        _check("compound_governor_add", compound_decision_add, {"compound_decision": compound_decision}, "Compound governor selected ADD for this exact add." if compound_decision_add else "Compound governor did not select ADD for this exact add."),
        _check("parent_position_reference", parent_reference_present, {"parent_order_id": dry_run_payload.get("parent_order_id"), "broker_ticket": dry_run_payload.get("broker_ticket")}, "Parent position reference is present." if parent_reference_present else "Parent position reference is missing."),
        _check("broker_truth_position_check_passed", broker_truth_position_passed, {}, "Compound dry-run broker-truth parent check passed." if broker_truth_position_passed else "Compound dry-run broker-truth parent check did not pass."),
        _check("fresh_add_edge_passed", edge_passed, {}, "Fresh add-edge PASS check passed." if edge_passed else "Fresh add-edge PASS check did not pass."),
        _check("base_live_order_dry_run_passed", base_live_passed, {"base_status": (dry_run_payload.get("base_live_order_dry_run") or {}).get("status") if isinstance(dry_run_payload.get("base_live_order_dry_run"), Mapping) else None}, "Base live-order dry-run gates passed." if base_live_passed else "Base live-order dry-run gates did not pass."),
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
        _check("live_open_parent_position_visible", live_open_position_visible, {"mt5_open_position_count": open_position_count}, "At least one live open position is visible for parent add context." if live_open_position_visible else "No live open parent position is visible."),
        _check("no_open_position_mismatch", no_open_position_mismatch, {"unmatched_open_positions": unmatched_positions, "terminal_receipt_mismatch_count": receipt_mismatches}, "No open-position or receipt mismatch is reported." if no_open_position_mismatch else "Broker truth reports open-position or receipt mismatch."),
        _check("no_pending_receipts", no_pending_receipts, {"terminal_pending_receipt_count": pending_receipts}, "No pending terminal receipts are reported." if no_pending_receipts else "Pending terminal receipts remain unresolved."),
    ]
    missing = [check["check_id"] for check in checks if check["status"] != "OK"]
    return {
        "evidence_ready_for_owner_accept": not missing,
        "missing_requirements": missing,
        "checks": checks,
        "latest_compound_add_summary": {
            "present": dry_run_present,
            "audit_id": dry_run_record.get("audit_id"),
            "status": dry_run_payload.get("status") or dry_run_record.get("status"),
            "order_id": dry_run_payload.get("order_id") or dry_run_record.get("order_id"),
            "decision_ref": dry_run_payload.get("decision_ref") or dry_run_record.get("decision_ref"),
            "parent_order_id": dry_run_payload.get("parent_order_id"),
            "parent_decision_ref": dry_run_payload.get("parent_decision_ref"),
            "broker_ticket": dry_run_payload.get("broker_ticket"),
            "generated_at": dry_run_payload.get("generated_at"),
            "broker_touched": broker_touched,
            "would_reach_broker_if_executed": bool(dry_run_payload.get("would_reach_broker_if_executed", False)),
            "compound_decision": compound_decision,
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
            "terminal_unmatched_open_position_count": broker_truth.get("terminal_unmatched_open_position_count"),
            "terminal_pending_receipt_count": broker_truth.get("terminal_pending_receipt_count"),
            "terminal_receipt_mismatch_count": broker_truth.get("terminal_receipt_mismatch_count"),
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
        "dry_run_report_kind": dry_run_payload.get("report_kind"),
        "dry_run_status": dry_run_payload.get("status") or dry_run_record.get("status"),
        "dry_run_generated_at": dry_run_payload.get("generated_at"),
        "add_order_id": dry_run_payload.get("order_id") or dry_run_record.get("order_id"),
        "add_decision_ref": dry_run_payload.get("decision_ref") or dry_run_record.get("decision_ref"),
        "parent_order_id": dry_run_payload.get("parent_order_id"),
        "parent_decision_ref": dry_run_payload.get("parent_decision_ref"),
        "broker_ticket": dry_run_payload.get("broker_ticket"),
        "compound_context": dry_run_payload.get("compound_context"),
        "proposed_intent": dry_run_payload.get("proposed_intent"),
        "order_request": dry_run_payload.get("order_request"),
        "checks": [
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
        "terminal_unmatched_open_position_count": broker_truth.get("terminal_unmatched_open_position_count"),
        "terminal_pending_receipt_count": broker_truth.get("terminal_pending_receipt_count"),
        "terminal_receipt_mismatch_count": broker_truth.get("terminal_receipt_mismatch_count"),
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:24]


def _dry_run_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = record.get("payload") if isinstance(record, Mapping) else None
    return dict(payload) if isinstance(payload, Mapping) else {}


def _dry_run_check_passed(checks: Any, check_id: str) -> bool:
    if not isinstance(checks, list):
        return False
    return any(
        isinstance(check, Mapping)
        and check.get("check_id") == check_id
        and bool(check.get("passed", False))
        for check in checks
    )


def _order_mismatches(order: Any, dry_run_payload: Mapping[str, Any]) -> list[str]:
    expected = dry_run_payload.get("order_request")
    if not isinstance(expected, Mapping):
        return ["accepted dry-run order_request is missing"]
    actual = _order_payload(order)
    checks = [
        ("order_id", _text_value(actual.get("order_id")), _text_value(expected.get("order_id"))),
        ("decision_ref", _text_value(actual.get("decision_ref")), _text_value(expected.get("decision_ref"))),
        ("symbol", _text_value(actual.get("symbol")).upper(), _text_value(expected.get("symbol")).upper()),
        ("direction", _text_value(actual.get("direction")).upper(), _text_value(expected.get("direction")).upper()),
        ("comment", _text_value(actual.get("comment")), _text_value(expected.get("comment"))),
    ]
    mismatches = [
        f"{name} actual={actual_value!r} expected={expected_value!r}"
        for name, actual_value, expected_value in checks
        if actual_value != expected_value
    ]
    for name in ("volume", "price", "stop_loss", "take_profit"):
        actual_float = _float_value(actual.get(name))
        expected_float = _float_value(expected.get(name))
        if actual_float is None or expected_float is None or abs(actual_float - expected_float) > 1e-9:
            mismatches.append(f"{name} actual={actual_float!r} expected={expected_float!r}")
    return mismatches


def _order_payload(order: Any) -> dict[str, Any]:
    if isinstance(order, Mapping):
        payload = dict(order)
    elif hasattr(order, "model_dump"):
        payload = order.model_dump(mode="json")
    else:
        payload = {
            "order_id": getattr(order, "order_id", None),
            "decision_ref": getattr(order, "decision_ref", None),
            "symbol": getattr(order, "symbol", None),
            "direction": getattr(order, "direction", None),
            "volume": getattr(order, "volume", None),
            "price": getattr(order, "price", None),
            "stop_loss": getattr(order, "stop_loss", None),
            "take_profit": getattr(order, "take_profit", None),
            "comment": getattr(order, "comment", None),
        }
    direction = payload.get("direction")
    payload["direction"] = getattr(direction, "value", direction)
    return payload


def _text_value(value: Any) -> str:
    return str(value or "")


def _float_value(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fresh_enough(value: Any, *, fresh_seconds: int) -> bool:
    if not value:
        return False
    try:
        generated = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return 0 <= (utc_now() - generated).total_seconds() <= max(1, int(fresh_seconds))
    except Exception:
        return False


def _int_value(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _next_action(clear: bool, evidence_ready: bool) -> str:
    if clear:
        return "Owner ACCEPT is current for the latest passing compound-add dry-run and fresh broker-position evidence."
    if evidence_ready:
        return "Owner-review the passing compound-add dry-run and fresh broker-position evidence, then confirm ACCEPT."
    return "Run a fresh passing compound-add dry run against fresh live broker-position truth before owner ACCEPT."


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
