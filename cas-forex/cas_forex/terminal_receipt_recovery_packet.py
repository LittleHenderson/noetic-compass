"""Read-only recovery packet for terminal receipt reconciliation blockers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from cas_forex.agent_message_bus import DEFAULT_EVENT_LOG_PATH
from cas_forex.legacy_receipts_archive import archive_stale_receipts
from cas_forex.terminal_position_reconciliation import (
    load_latest_terminal_position_reconciliation_report,
)
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEGACY_SNAPSHOT_DIR = REPO_ROOT / "evidence_runs" / "legacy_receipts_archive"

REPORT_KIND = "cas_forex_terminal_receipt_recovery_packet"
ARCHIVE_ACTION_REPORT_KIND = "cas_forex_terminal_receipt_archive_action"
STATUS_CLEAR = "TERMINAL_RECEIPT_RECOVERY_CLEAR"
STATUS_WAITING_FOR_TERMINAL = "TERMINAL_RECEIPT_RECOVERY_WAITING_FOR_TERMINAL"
STATUS_ARCHIVE_PREVIEW_READY = "TERMINAL_RECEIPT_RECOVERY_ARCHIVE_PREVIEW_READY"
STATUS_BLOCKED = "TERMINAL_RECEIPT_RECOVERY_BLOCKED"
ARCHIVE_STATUS_DRY_RUN = "TERMINAL_RECEIPT_ARCHIVE_DRY_RUN"
ARCHIVE_STATUS_CONFIRM_REQUIRED = "TERMINAL_RECEIPT_ARCHIVE_CONFIRM_REQUIRED"
ARCHIVE_STATUS_EXECUTED = "TERMINAL_RECEIPT_ARCHIVE_EXECUTED"
ARCHIVE_STATUS_NO_ROWS = "TERMINAL_RECEIPT_ARCHIVE_NO_ROWS"
ARCHIVE_STATUS_ERROR = "TERMINAL_RECEIPT_ARCHIVE_ERROR"

CLAIM_BOUNDARY = (
    "Terminal receipt recovery packet is a read-only owner review packet for "
    "pending terminal receipt and position-reconciliation blockers. It may "
    "preview stale legacy receipt archive eligibility, but it does not archive "
    "rows, rewrite journals, ingest receipts, reconcile attempts, place orders, "
    "close positions, create broker ACCEPT, create owner ACCEPT, authorize live "
    "trading, deposit, withdraw, move bank/card money, automate payouts, or "
    "mark evidence LICENSED."
)

ARCHIVE_ACTION_CLAIM_BOUNDARY = (
    "Terminal receipt archive action is an owner-controlled local journal "
    "cleanup path for stale pending receipt rows. Dry-run is the default. "
    "Execution requires explicit owner archive confirmation, writes a snapshot "
    "before rewriting the local event journal, and does not ingest receipts, "
    "reconcile attempts, place orders, close positions, create broker ACCEPT, "
    "create owner ACCEPT, authorize live trading, deposit, withdraw, move "
    "bank/card money, automate payouts, or mark evidence LICENSED."
)


def build_terminal_receipt_recovery_packet(
    *,
    reconciliation_report: Mapping[str, Any] | None = None,
    event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH,
    legacy_snapshot_dir: Path | str = DEFAULT_LEGACY_SNAPSHOT_DIR,
    age_threshold_hours: float = 24.0,
) -> dict[str, Any]:
    """Build read-only recovery evidence for terminal receipt blockers."""

    report = dict(reconciliation_report) if reconciliation_report is not None else _latest_reconciliation()
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    pending_positions = [_pending_position_packet(row) for row in _pending_positions(report)]
    legacy_preview = _legacy_archive_preview(
        event_log_path=event_log_path,
        snapshot_dir=legacy_snapshot_dir,
        age_threshold_hours=age_threshold_hours,
    )

    active_lane = str(summary.get("active_execution_lane") or "mt4_mailbox")
    mt4_required = bool(summary.get("mt4_lane_required", True))
    pending_count = int(
        summary.get("active_pending_receipt_count")
        if summary.get("active_pending_receipt_count") is not None
        else (summary.get("pending_receipt_count") or len(pending_positions) or 0)
    )
    unmatched_count = int(
        summary.get("active_unmatched_open_position_count")
        if summary.get("active_unmatched_open_position_count") is not None
        else (summary.get("unmatched_open_position_count") or 0)
    )
    heartbeat_status = str(summary.get("heartbeat_status") or "MISSING")
    account_snapshot_present = bool(summary.get("account_snapshot_present", False))
    effective_heartbeat_status = heartbeat_status if mt4_required else "FRESH"
    effective_account_snapshot_present = account_snapshot_present or not mt4_required
    status = _status(
        pending_count=pending_count,
        unmatched_count=unmatched_count,
        heartbeat_status=effective_heartbeat_status,
        account_snapshot_present=effective_account_snapshot_present,
        legacy_preview_count=int(legacy_preview.get("pending_receipt_rows_archived") or 0),
    )
    missing = _missing_requirements(
        pending_count=pending_count,
        unmatched_count=unmatched_count,
        heartbeat_status=effective_heartbeat_status,
        account_snapshot_present=effective_account_snapshot_present,
    )

    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "terminal_reconciliation_clean_for_live": status == STATUS_CLEAR,
        "broker_touched": False,
        "journal_rewritten": False,
        "receipt_ingest_attempted": False,
        "attempt_finalized": False,
        "active_execution_lane": active_lane,
        "mt4_lane_required": mt4_required,
        "pending_receipt_count": pending_count,
        "pending_receipt_count_by_lane": dict(summary.get("pending_receipt_count_by_lane") or {}),
        "cas_receipt_pending_open_count": int(summary.get("cas_receipt_pending_open_count") or 0),
        "unmatched_open_position_count": unmatched_count,
        "terminal_open_position_count": int(summary.get("terminal_open_position_count") or 0),
        "heartbeat_status": heartbeat_status,
        "account_snapshot_present": account_snapshot_present,
        "active_lane_heartbeat_ready": effective_heartbeat_status == "FRESH",
        "active_lane_account_snapshot_ready": effective_account_snapshot_present,
        "mt4_history_export_verifier_status": summary.get("mt4_history_export_verifier_status"),
        "pending_positions": pending_positions,
        "legacy_archive_preview": legacy_preview,
        "missing_requirements": missing,
        "source_reconciliation": {
            "report_kind": report.get("report_kind"),
            "created_at": report.get("created_at"),
            "reconciliation_status": report.get("reconciliation_status"),
            "report_path": report.get("report_path") or ((report.get("artifact_paths") or {}).get("json") if isinstance(report.get("artifact_paths"), Mapping) else None),
        },
        "operator_commands": dict(report.get("operator_commands") or {}),
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(status, legacy_preview, pending_count),
    }


def run_terminal_receipt_archive_action(
    *,
    execute: bool = False,
    confirm_owner_archive: bool = False,
    notes: str = "",
    event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH,
    legacy_snapshot_dir: Path | str = DEFAULT_LEGACY_SNAPSHOT_DIR,
    age_threshold_hours: float = 24.0,
) -> dict[str, Any]:
    """Preview or owner-execute the stale legacy receipt archive."""

    requested_execute = bool(execute)
    owner_confirmed = bool(confirm_owner_archive)
    dry_run = not (requested_execute and owner_confirmed)

    result = archive_stale_receipts(
        journal_path=Path(event_log_path),
        snapshot_dir=Path(legacy_snapshot_dir),
        dry_run=dry_run,
        age_threshold_hours=age_threshold_hours,
    )
    archive_payload = result.to_dict()
    archived_count = int(archive_payload.get("pending_receipt_rows_archived") or 0)
    error_message = archive_payload.get("error_message")

    if error_message:
        status = ARCHIVE_STATUS_ERROR
    elif requested_execute and not owner_confirmed:
        status = ARCHIVE_STATUS_CONFIRM_REQUIRED
    elif dry_run:
        status = ARCHIVE_STATUS_DRY_RUN
    elif archived_count > 0:
        status = ARCHIVE_STATUS_EXECUTED
    else:
        status = ARCHIVE_STATUS_NO_ROWS

    journal_rewritten = (
        status == ARCHIVE_STATUS_EXECUTED
        and archived_count > 0
        and not bool(error_message)
        and not dry_run
    )

    return {
        "report_kind": ARCHIVE_ACTION_REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "requested_execute": requested_execute,
        "confirm_owner_archive": owner_confirmed,
        "dry_run": dry_run,
        "broker_touched": False,
        "journal_rewritten": journal_rewritten,
        "receipt_ingest_attempted": False,
        "attempt_finalized": False,
        "money_moved": False,
        "age_threshold_hours": float(age_threshold_hours),
        "notes_recorded": notes or "",
        "archive_result": archive_payload,
        "claim_boundary": ARCHIVE_ACTION_CLAIM_BOUNDARY,
        "next_action": _archive_action_next_action(status, archived_count),
    }


def _latest_reconciliation() -> dict[str, Any]:
    try:
        report = load_latest_terminal_position_reconciliation_report()
        return dict(report) if isinstance(report, Mapping) else {}
    except Exception:
        return {}


def _pending_positions(report: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = report.get("cas_open_positions")
    if isinstance(rows, list):
        return [
            dict(row)
            for row in rows
            if isinstance(row, Mapping) and bool(row.get("receipt_pending", False))
        ]
    unmatched = report.get("unmatched_open_positions")
    out: list[Mapping[str, Any]] = []
    if isinstance(unmatched, list):
        for item in unmatched:
            if not isinstance(item, Mapping) or item.get("reason") != "receipt_pending":
                continue
            position = item.get("position")
            if isinstance(position, Mapping):
                out.append(dict(position))
    return out


def _pending_position_packet(row: Mapping[str, Any]) -> dict[str, Any]:
    broker_mode = str(row.get("broker_mode") or "")
    lane = str(row.get("lane") or "")
    classification = "LEGACY_MT4_MAILBOX_PENDING" if lane == "mt4_mailbox" or "MT4" in broker_mode.upper() else "TERMINAL_RECEIPT_PENDING"
    return {
        "position_id": row.get("position_id"),
        "memory_id": row.get("memory_id"),
        "command_id": row.get("command_id"),
        "receipt_id": row.get("receipt_id"),
        "symbol": row.get("symbol"),
        "direction": row.get("direction"),
        "lots": row.get("lots"),
        "broker_mode": broker_mode,
        "lane": lane,
        "learning_status": row.get("learning_status"),
        "outcome_label": row.get("outcome_label"),
        "status": row.get("status"),
        "classification_status": classification,
        "requires_terminal_receipt_or_owner_archive_review": True,
        "archive_is_owner_execute_only": True,
    }


def _legacy_archive_preview(
    *,
    event_log_path: Path | str,
    snapshot_dir: Path | str,
    age_threshold_hours: float,
) -> dict[str, Any]:
    result = archive_stale_receipts(
        journal_path=Path(event_log_path),
        snapshot_dir=Path(snapshot_dir),
        dry_run=True,
        age_threshold_hours=age_threshold_hours,
    )
    payload = result.to_dict()
    payload["dry_run"] = True
    payload["execute_required_for_archive"] = True
    payload["claim_boundary"] = (
        "This is a dry-run preview only. Archiving requires an explicit owner "
        "execution of the legacy receipt archive tool and must preserve the "
        "snapshot-first audit trail."
    )
    return payload


def _status(
    *,
    pending_count: int,
    unmatched_count: int,
    heartbeat_status: str,
    account_snapshot_present: bool,
    legacy_preview_count: int,
) -> str:
    if pending_count == 0 and unmatched_count == 0 and heartbeat_status == "FRESH" and account_snapshot_present:
        return STATUS_CLEAR
    if legacy_preview_count > 0:
        return STATUS_ARCHIVE_PREVIEW_READY
    if pending_count > 0 or unmatched_count > 0:
        return STATUS_WAITING_FOR_TERMINAL
    return STATUS_BLOCKED


def _missing_requirements(
    *,
    pending_count: int,
    unmatched_count: int,
    heartbeat_status: str,
    account_snapshot_present: bool,
) -> list[str]:
    missing: list[str] = []
    if heartbeat_status != "FRESH":
        missing.append("terminal_heartbeat_fresh")
    if not account_snapshot_present:
        missing.append("terminal_account_snapshot_present")
    if pending_count > 0:
        missing.append("terminal_receipts_clear")
    if unmatched_count > 0:
        missing.append("terminal_open_positions_match")
    return missing


def _next_action(status: str, legacy_preview: Mapping[str, Any], pending_count: int) -> str:
    preview_count = int(legacy_preview.get("pending_receipt_rows_archived") or 0)
    if status == STATUS_CLEAR:
        return "Terminal receipt and position reconciliation is clean for live recovery."
    if preview_count > 0:
        return (
            "Owner-review the dry-run legacy archive preview, then execute the archive tool only if these stale paper/MT4 receipt rows should be moved to a snapshot before rebuilding memory and reconciliation."
        )
    if pending_count > 0:
        return "Open the terminal bridge, let pending command receipts land, run terminal receipt ingest, rebuild memory, then rerun terminal position reconciliation."
    return "Refresh terminal heartbeat/account snapshot evidence and rerun reconciliation."


def _archive_action_next_action(status: str, archived_count: int) -> str:
    if status == ARCHIVE_STATUS_CONFIRM_REQUIRED:
        return "Owner archive confirmation is required before stale receipt rows can be moved to a snapshot."
    if status == ARCHIVE_STATUS_DRY_RUN:
        if archived_count > 0:
            return "Review the dry-run archive count, then execute only if the owner wants these stale rows moved to a snapshot."
        return "No stale receipt rows are currently eligible for archive; refresh terminal receipts and reconciliation evidence."
    if status == ARCHIVE_STATUS_EXECUTED:
        return "Archive executed. Rebuild agent memory, rerun terminal receipt ingest if new receipts exist, then rerun terminal position reconciliation and live recovery."
    if status == ARCHIVE_STATUS_NO_ROWS:
        return "Archive execution found no eligible stale rows; refresh terminal heartbeat/account snapshot evidence and rerun reconciliation."
    return "Archive action failed or could not read the journal; inspect archive_result.error_message before any further recovery step."


__all__ = [
    "ARCHIVE_ACTION_REPORT_KIND",
    "REPORT_KIND",
    "build_terminal_receipt_recovery_packet",
    "run_terminal_receipt_archive_action",
]
