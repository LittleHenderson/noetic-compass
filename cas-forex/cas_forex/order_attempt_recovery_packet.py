"""Owner-facing recovery packet for unresolved real order attempts.

The live gate must stay blocked while a real broker attempt is unresolved. This
module makes the blocker actionable by packaging the exact unresolved rows, the
latest broker-truth checks, and whether owner reconciliation is currently safe
to attempt. It is read-only and never clears audit rows.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from cas_forex.account_reconciliation import RECONCILIATION_FAILED
from cas_forex.order_attempt_audit import build_order_attempt_audit_status
from cas_forex.time_utils import utc_now

REPORT_KIND = "cas_forex_order_attempt_recovery_packet"
STATUS_CLEAR = "NO_UNRESOLVED_REAL_ATTEMPTS"
STATUS_READY = "READY_TO_RECONCILE_UNRESOLVED_ATTEMPTS"
STATUS_BLOCKED = "RECOVERY_PACKET_BLOCKED"
DEFAULT_FRESH_SECONDS = 180

CLAIM_BOUNDARY = (
    "Order-attempt recovery packet is a read-only owner review packet for "
    "unresolved real broker-attempt audit rows. It does not finalize attempts, "
    "retry orders, place orders, close positions, create broker ACCEPT, create "
    "owner ACCEPT, authorize live trading, deposit, withdraw, move bank/card "
    "money, automate payouts, or mark evidence LICENSED."
)


def build_order_attempt_recovery_packet(
    *,
    order_attempt_status: Mapping[str, Any] | None = None,
    broker_truth_report: Mapping[str, Any] | None = None,
    fresh_seconds: int = DEFAULT_FRESH_SECONDS,
) -> dict[str, Any]:
    """Return an owner-action packet without changing audit or broker state."""

    attempts = dict(order_attempt_status) if order_attempt_status is not None else build_order_attempt_audit_status()
    truth = dict(broker_truth_report) if broker_truth_report is not None else _latest_broker_truth()
    unresolved = _unresolved_attempts(attempts)
    truth_checks = _broker_truth_checks(truth, fresh_seconds=fresh_seconds)
    blocking_truth_checks = [check["check_id"] for check in truth_checks if check["status"] != "OK"]
    truth_clean_for_reconcile = not blocking_truth_checks
    unresolved_count = len(unresolved)
    can_reconcile = unresolved_count > 0 and truth_clean_for_reconcile
    status = STATUS_CLEAR if unresolved_count == 0 else (STATUS_READY if can_reconcile else STATUS_BLOCKED)

    classified = [_attempt_packet(row) for row in unresolved]
    synthetic_like_count = sum(1 for row in classified if row["classification_status"] == "SYNTHETIC_TEST_LIKE")
    broker_review_count = unresolved_count - synthetic_like_count

    missing = list(blocking_truth_checks)
    if unresolved_count == 0:
        missing = []
    elif not can_reconcile:
        missing.append("owner_reconcile_waiting_on_clean_broker_truth")

    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "can_reconcile_unresolved_attempts": can_reconcile,
        "broker_touched": False,
        "dispatched_to_bridge": False,
        "attempt_finalized": False,
        "unresolved_real_attempt_count": unresolved_count,
        "synthetic_test_like_count": synthetic_like_count,
        "broker_review_required_count": broker_review_count,
        "missing_requirements": list(dict.fromkeys(missing)),
        "broker_truth_checks": truth_checks,
        "broker_truth_summary": _broker_truth_summary(truth),
        "unresolved_real_attempts": classified,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(status, blocking_truth_checks, synthetic_like_count),
    }


def _unresolved_attempts(status: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = status.get("unresolved_real_attempts")
    if not isinstance(rows, list):
        return []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _attempt_packet(row: Mapping[str, Any]) -> dict[str, Any]:
    bridge = str(row.get("bridge_name") or "")
    order_id = str(row.get("order_id") or "")
    decision_ref = str(row.get("decision_ref") or "")
    source = str(row.get("source") or "")
    mode = str(row.get("mode") or "")
    reasons: list[str] = []
    if bridge.startswith("_") or "fake" in bridge.lower():
        reasons.append("bridge_name_is_test_like")
    if order_id.startswith(("ord-1", "compound-add-1", "waste-add-dref-test")):
        reasons.append("order_id_matches_test_fixture_pattern")
    if decision_ref.startswith(("dec-1", "compound-add-ref-1", "dref-test-")):
        reasons.append("decision_ref_matches_test_fixture_pattern")
    if source in {"test_crash_window", "waste_compound_add_handoff"} and "fake" in bridge.lower():
        reasons.append("source_bridge_pair_is_test_like")

    classification = "SYNTHETIC_TEST_LIKE" if reasons else "BROKER_REVIEW_REQUIRED"
    return {
        "attempt_id": row.get("attempt_id"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "source": source,
        "mode": mode,
        "bridge_name": bridge,
        "order_id": order_id,
        "decision_ref": decision_ref,
        "symbol": row.get("symbol"),
        "direction": row.get("direction"),
        "volume": row.get("volume"),
        "result_finalized": bool(row.get("result_finalized", False)),
        "dispatched_to_bridge": bool(row.get("dispatched_to_bridge", False)),
        "result_status": row.get("result_status"),
        "result_reason": row.get("result_reason"),
        "is_real_attempt": bool(row.get("is_real_attempt", False)),
        "bridge_touch_unknown": bool(row.get("bridge_touch_unknown", False)),
        "requires_owner_review_before_retry": bool(row.get("requires_owner_review_before_retry", False)),
        "last_dispatch_error": row.get("last_dispatch_error"),
        "execution_provenance": row.get("execution_provenance"),
        "classification_status": classification,
        "classification_reasons": reasons,
        "requires_owner_terminal_review": True,
        "owner_reconcile_route": "/api/forex/order-dispatch/audit/reconcile-unresolved",
        "claim_boundary": row.get("claim_boundary"),
    }


def _broker_truth_checks(truth: Mapping[str, Any], *, fresh_seconds: int) -> list[dict[str, Any]]:
    truth_present = bool(truth)
    fresh = _fresh_enough(truth.get("generated_at"), fresh_seconds=fresh_seconds)
    live_visible = (
        bool(truth.get("mt5_connected"))
        and truth.get("mt5_is_demo") is False
        and truth.get("mt5_account_identity_matches_config") is True
    )
    failed = str(truth.get("overall_status") or "") == RECONCILIATION_FAILED
    unmatched = _int(truth.get("terminal_unmatched_open_position_count"), 0)
    pending = _int(truth.get("terminal_pending_receipt_count"), 0)
    mismatch = _int(truth.get("terminal_receipt_mismatch_count"), 0)
    clean = truth_present and not failed and unmatched == 0 and pending == 0 and mismatch == 0
    return [
        _check(
            "broker_truth_present",
            truth_present,
            {"present": truth_present},
            "Latest broker-truth report is present." if truth_present else "No broker-truth report is present.",
        ),
        _check(
            "broker_truth_fresh",
            fresh,
            {"generated_at": truth.get("generated_at"), "fresh_seconds": fresh_seconds},
            "Broker truth is fresh enough for owner reconciliation."
            if fresh
            else "Broker truth is missing or stale.",
        ),
        _check(
            "live_account_visible",
            live_visible,
            {
                "mt5_connected": truth.get("mt5_connected"),
                "mt5_is_demo": truth.get("mt5_is_demo"),
                "mt5_account": truth.get("mt5_account"),
                "mt5_account_server": truth.get("mt5_account_server"),
                "mt5_expected_account": truth.get("mt5_expected_account"),
                "mt5_expected_server": truth.get("mt5_expected_server"),
                "mt5_account_identity_matches_config": truth.get("mt5_account_identity_matches_config"),
            },
            "A connected live MT5 account matching the configured owner login/server is visible."
            if live_visible
            else "A connected live MT5 account matching the configured owner login/server is not visible.",
        ),
        _check(
            "position_reconciliation_clean",
            clean,
            {
                "overall_status": truth.get("overall_status"),
                "unmatched": unmatched,
                "pending": pending,
                "receipt_mismatch": mismatch,
            },
            "Broker truth and terminal reconciliation are clean."
            if clean
            else "Broker truth is failed, pending, unmatched, or unavailable.",
        ),
    ]


def _broker_truth_summary(truth: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "present": bool(truth),
        "generated_at": truth.get("generated_at"),
        "overall_status": truth.get("overall_status"),
        "mt5_connected": truth.get("mt5_connected"),
        "mt5_is_demo": truth.get("mt5_is_demo"),
        "mt5_account": truth.get("mt5_account"),
        "mt5_account_server": truth.get("mt5_account_server"),
        "mt5_expected_account": truth.get("mt5_expected_account"),
        "mt5_expected_server": truth.get("mt5_expected_server"),
        "mt5_account_identity_matches_config": truth.get("mt5_account_identity_matches_config"),
        "mt5_open_position_count": truth.get("mt5_open_position_count"),
        "terminal_unmatched_open_position_count": truth.get("terminal_unmatched_open_position_count"),
        "terminal_unattributed_open_position_count": truth.get("terminal_unattributed_open_position_count"),
        "terminal_memory_gap_open_position_count": truth.get("terminal_memory_gap_open_position_count"),
        "cas_memory_only_open_position_count": truth.get("cas_memory_only_open_position_count"),
        "cas_receipt_pending_open_position_count": truth.get("cas_receipt_pending_open_position_count"),
        "terminal_unmatched_history_count": truth.get("terminal_unmatched_history_count"),
        "terminal_unattributed_history_count": truth.get("terminal_unattributed_history_count"),
        "terminal_attributed_history_memory_gap_count": truth.get("terminal_attributed_history_memory_gap_count"),
        "terminal_pending_receipt_count": truth.get("terminal_pending_receipt_count"),
        "terminal_receipt_mismatch_count": truth.get("terminal_receipt_mismatch_count"),
        "terminal_unmatched_open_position_preview": list(truth.get("terminal_unmatched_open_position_preview") or [])[:3],
        "terminal_unmatched_history_preview": list(truth.get("terminal_unmatched_history_preview") or [])[:3],
    }


def _check(check_id: str, ok: bool, evidence: Mapping[str, Any], detail: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "OK" if ok else "MISSING",
        "evidence": dict(evidence),
        "detail": detail,
    }


def _fresh_enough(value: Any, *, fresh_seconds: int) -> bool:
    if not value:
        return False
    try:
        generated = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return (utc_now() - generated).total_seconds() <= max(1, int(fresh_seconds))
    except Exception:
        return False


def _latest_broker_truth() -> dict[str, Any]:
    try:
        from cas_forex.broker_truth_monitor import load_latest_broker_truth_monitor_report

        report = load_latest_broker_truth_monitor_report()
        return dict(report) if isinstance(report, Mapping) else {}
    except Exception:
        return {}


def _next_action(status: str, blocking_truth_checks: list[str], synthetic_count: int) -> str:
    if status == STATUS_CLEAR:
        return "No unresolved real order-attempt rows are open."
    if blocking_truth_checks:
        return (
            "Refresh broker truth from the terminal and resolve position/receipt reconciliation before owner-reconciling unresolved attempts."
        )
    if synthetic_count:
        return (
            "Owner-review the test-like unresolved attempts against clean broker truth, then reconcile each exact attempt if no real broker order exists."
        )
    return "Owner-review each unresolved real attempt against clean broker truth before retrying or allowing live pilot promotion."


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)
