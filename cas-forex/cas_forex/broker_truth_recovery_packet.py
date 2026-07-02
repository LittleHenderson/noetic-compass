"""Compact owner recovery packet for broker-truth live blockers."""

from __future__ import annotations

from typing import Any, Mapping

from cas_forex.account_reconciliation import RECONCILED
from cas_forex.broker_truth_monitor import monitor_status
from cas_forex.time_utils import utc_now

REPORT_KIND = "cas_forex_broker_truth_recovery_packet"
STATUS_CLEAR = "BROKER_TRUTH_RECOVERY_CLEAR"
STATUS_BLOCKED = "BROKER_TRUTH_RECOVERY_BLOCKED"
STATUS_UNAVAILABLE = "BROKER_TRUTH_RECOVERY_UNAVAILABLE"

CLAIM_BOUNDARY = (
    "Broker-truth recovery packet is a read-only owner review summary of the "
    "latest broker-truth monitor report. It does not read or write broker "
    "orders itself, place orders, close positions, create broker ACCEPT, create "
    "owner ACCEPT, authorize live trading, reconcile unresolved attempts, mint "
    "edge tokens, deposit, withdraw, move bank/card money, automate payouts, or "
    "mark evidence LICENSED."
)


def build_broker_truth_recovery_packet(
    *,
    monitor_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact fail-closed owner packet from broker-truth monitor status."""

    state = dict(monitor_state) if monitor_state is not None else _monitor_status()
    latest = state.get("latest_report") if isinstance(state.get("latest_report"), Mapping) else None
    blockers = _blockers(state, latest)
    status = STATUS_CLEAR if not blockers else (STATUS_BLOCKED if latest else STATUS_UNAVAILABLE)

    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "broker_truth_clear_for_live_recovery": status == STATUS_CLEAR,
        "broker_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "money_moved": False,
        "monitor_summary": _monitor_summary(state, latest),
        "blockers": blockers,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(blockers, latest),
    }


def _monitor_status() -> dict[str, Any]:
    try:
        return dict(monitor_status())
    except Exception as exc:
        return {"monitor_status": "unavailable", "error": f"{type(exc).__name__}: {exc}"}


def _monitor_summary(
    state: Mapping[str, Any],
    latest: Mapping[str, Any] | None,
) -> dict[str, Any]:
    latest = latest or {}
    return {
        "monitor_running": bool(state.get("running", False)),
        "monitor_status": state.get("monitor_status") or latest.get("monitor_status"),
        "ready_for_live": bool(state.get("ready_for_live", False)),
        "latest_generated_at": latest.get("generated_at"),
        "overall_status": latest.get("overall_status"),
        "mt5_connected": latest.get("mt5_connected"),
        "mt5_is_demo": latest.get("mt5_is_demo"),
        "mt5_open_position_count": latest.get("mt5_open_position_count"),
        "terminal_reconciliation_status": latest.get("terminal_reconciliation_status"),
        "terminal_pending_receipt_count": latest.get("terminal_pending_receipt_count"),
        "terminal_unmatched_open_position_count": latest.get("terminal_unmatched_open_position_count"),
        "terminal_receipt_mismatch_count": latest.get("terminal_receipt_mismatch_count"),
        "terminal_account_snapshot_present": latest.get("terminal_account_snapshot_present"),
    }


def _blockers(
    state: Mapping[str, Any],
    latest: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if latest is None:
        return [
            _blocker(
                "broker_truth_report_present",
                False,
                state.get("monitor_status") or "unavailable",
                "Run the read-only broker-truth check so CAS Forex has current broker/terminal evidence.",
            )
        ]

    blockers: list[dict[str, Any]] = []
    _add_blocker(
        blockers,
        "broker_truth_ready_for_live",
        bool(state.get("ready_for_live", False)),
        state.get("ready_for_live", False),
        "Broker truth is not ready for live gates.",
    )
    _add_blocker(
        blockers,
        "broker_truth_reconciled",
        latest.get("overall_status") == RECONCILED,
        latest.get("overall_status"),
        "Broker truth is not fully RECONCILED.",
    )
    _add_blocker(
        blockers,
        "mt5_live_account_visible",
        bool(latest.get("mt5_connected")) and latest.get("mt5_is_demo") is False,
        {"connected": latest.get("mt5_connected"), "is_demo": latest.get("mt5_is_demo")},
        "A connected live MT5 account is not visible.",
    )
    _add_blocker(
        blockers,
        "terminal_account_snapshot_present",
        bool(latest.get("terminal_account_snapshot_present", False)),
        latest.get("terminal_account_snapshot_present"),
        "Terminal account snapshot is missing.",
    )
    _add_blocker(
        blockers,
        "terminal_pending_receipts_clear",
        _int(latest.get("terminal_pending_receipt_count")) == 0,
        latest.get("terminal_pending_receipt_count"),
        "Terminal receipt lifecycle still has pending rows.",
    )
    _add_blocker(
        blockers,
        "terminal_open_positions_match",
        _int(latest.get("terminal_unmatched_open_position_count")) == 0,
        latest.get("terminal_unmatched_open_position_count"),
        "CAS open-position memory does not match terminal open-position evidence.",
    )
    _add_blocker(
        blockers,
        "terminal_receipt_mismatches_clear",
        _int(latest.get("terminal_receipt_mismatch_count")) == 0,
        latest.get("terminal_receipt_mismatch_count"),
        "Terminal receipt mismatches are still present.",
    )
    return blockers


def _add_blocker(
    out: list[dict[str, Any]],
    blocker_id: str,
    clear: bool,
    value: Any,
    detail: str,
) -> None:
    if clear:
        return
    out.append(_blocker(blocker_id, False, value, detail))


def _blocker(blocker_id: str, clear: bool, value: Any, detail: str) -> dict[str, Any]:
    return {
        "blocker_id": blocker_id,
        "clear": bool(clear),
        "value": value,
        "detail": detail,
    }


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _next_action(blockers: list[Mapping[str, Any]], latest: Mapping[str, Any] | None) -> str:
    if latest is None:
        return "Run Broker Truth from Settings Live Recovery so CAS Forex can read the latest broker/terminal truth."
    ids = {str(blocker.get("blocker_id")) for blocker in blockers}
    if "mt5_live_account_visible" in ids:
        return "Connect the owner-approved live MT5 account, then run Broker Truth again; demo truth cannot unlock live-money gates."
    if "terminal_pending_receipts_clear" in ids or "terminal_open_positions_match" in ids:
        return "Use terminal receipt archive/refresh only when owner-reviewed, then rerun Broker Truth and Live Recovery."
    if blockers:
        return "Clear the listed broker-truth blockers, then rerun Broker Truth before any live/payout progression."
    return "Broker truth is clear for the live-recovery layer; continue with live recovery and unresolved attempt review."


__all__ = ["REPORT_KIND", "build_broker_truth_recovery_packet"]
