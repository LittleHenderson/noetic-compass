"""Owner-controlled terminal receipt recovery refresh sequence."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from cas_forex.agent_message_bus import DEFAULT_EVENT_LOG_PATH
from cas_forex.live_recovery import build_live_recovery_report
from cas_forex.terminal_position_reconciliation import (
    DEFAULT_OUTPUT_DIR as DEFAULT_RECONCILIATION_OUTPUT_DIR,
)
from cas_forex.terminal_position_reconciliation import (
    build_terminal_position_reconciliation_report,
    load_latest_terminal_position_reconciliation_report,
)
from cas_forex.terminal_receipt_recovery_packet import build_terminal_receipt_recovery_packet
from cas_forex.terminal_receipt_watcher import (
    DEFAULT_OUTPUT_DIR as DEFAULT_WATCHER_OUTPUT_DIR,
)
from cas_forex.terminal_receipt_watcher import build_terminal_receipt_watcher_report
from cas_forex.terminal_receipt_ingest import DEFAULT_MAILBOX_DIR
from cas_forex.terminal_history_ingest import DEFAULT_SOURCE_DIR as DEFAULT_HISTORY_SOURCE_DIR
from cas_forex.time_utils import utc_now

REPORT_KIND = "cas_forex_terminal_receipt_recovery_refresh"
STATUS_DRY_RUN = "TERMINAL_RECEIPT_RECOVERY_REFRESH_DRY_RUN"
STATUS_CONFIRM_REQUIRED = "TERMINAL_RECEIPT_RECOVERY_REFRESH_CONFIRM_REQUIRED"
STATUS_RAN = "TERMINAL_RECEIPT_RECOVERY_REFRESH_RAN"
STATUS_FAILED = "TERMINAL_RECEIPT_RECOVERY_REFRESH_FAILED"

CLAIM_BOUNDARY = (
    "Terminal receipt recovery refresh is an owner-controlled local evidence "
    "rebuild sequence. It can force the terminal receipt watcher refresh chain, "
    "rebuild terminal position reconciliation, rebuild the terminal receipt "
    "recovery packet, and rebuild live recovery status. It does not place "
    "orders, close positions, create broker ACCEPT, create owner ACCEPT, "
    "authorize live trading, finalize unresolved order attempts, deposit, "
    "withdraw, move bank/card money, automate payouts, or mark evidence "
    "LICENSED."
)


def run_terminal_receipt_recovery_refresh(
    *,
    execute: bool = False,
    confirm_owner_refresh: bool = False,
    notes: str = "",
    mailbox_dir: Path | str = DEFAULT_MAILBOX_DIR,
    history_source_paths: Optional[Sequence[Path | str]] = None,
    event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH,
    watcher_output_dir: Path | str = DEFAULT_WATCHER_OUTPUT_DIR,
    chain_output_root: Optional[Path | str] = None,
    reconciliation_output_dir: Path | str = DEFAULT_RECONCILIATION_OUTPUT_DIR,
    current_recovery_packet: Mapping[str, Any] | None = None,
    current_live_recovery: Mapping[str, Any] | None = None,
    active_execution_lane: str | None = None,
) -> dict[str, Any]:
    """Plan or owner-run the local receipt recovery refresh sequence."""

    requested_execute = bool(execute)
    owner_confirmed = bool(confirm_owner_refresh)
    dry_run = not (requested_execute and owner_confirmed)
    status = (
        STATUS_CONFIRM_REQUIRED
        if requested_execute and not owner_confirmed
        else STATUS_DRY_RUN
    )
    steps = _planned_steps()
    reports: dict[str, Any] = {}

    if dry_run:
        reports.update(_current_reports(
            recovery_packet=current_recovery_packet,
            live_recovery=current_live_recovery,
        ))
        return _action_payload(
            status=status,
            requested_execute=requested_execute,
            owner_confirmed=owner_confirmed,
            dry_run=True,
            notes=notes,
            steps=steps,
            reports=reports,
        )

    steps = []
    watcher_report = _run_step(
        steps,
        "terminal_receipt_watcher_force_run",
        lambda: build_terminal_receipt_watcher_report(
            mailbox_dir=mailbox_dir,
            history_source_paths=history_source_paths or [DEFAULT_HISTORY_SOURCE_DIR],
            event_log_path=event_log_path,
            output_dir=watcher_output_dir,
            chain_output_root=chain_output_root,
            run_chain=True,
            force_run=True,
        ),
        "watch_status",
    )
    if watcher_report is not None:
        reports["terminal_receipt_watcher"] = _report_ref(watcher_report, "watch_status")

    reconciliation_report = None
    if watcher_report is not None:
        reconciliation_report = _run_step(
            steps,
            "terminal_position_reconciliation",
            lambda: build_terminal_position_reconciliation_report(
                active_execution_lane=active_execution_lane or _configured_execution_lane(),
                output_dir=reconciliation_output_dir,
                write_report=True,
            ),
            "reconciliation_status",
        )
        if reconciliation_report is not None:
            reports["terminal_position_reconciliation"] = _report_ref(
                reconciliation_report,
                "reconciliation_status",
            )

    recovery_packet = None
    if reconciliation_report is not None:
        recovery_packet = _run_step(
            steps,
            "terminal_receipt_recovery_packet",
            lambda: build_terminal_receipt_recovery_packet(
                reconciliation_report=reconciliation_report,
            ),
            "status",
        )
        if recovery_packet is not None:
            reports["terminal_receipt_recovery_packet"] = _report_ref(
                recovery_packet,
                "status",
            )

    live_recovery = _run_step(
        steps,
        "live_recovery_status",
        build_live_recovery_report,
        "recovery_status",
    )
    if live_recovery is not None:
        reports["live_recovery"] = _report_ref(live_recovery, "recovery_status")

    failed = any(step.get("status") == "FAILED" for step in steps)
    return _action_payload(
        status=STATUS_FAILED if failed else STATUS_RAN,
        requested_execute=requested_execute,
        owner_confirmed=owner_confirmed,
        dry_run=False,
        notes=notes,
        steps=steps,
        reports=reports,
    )


def _configured_execution_lane() -> str:
    try:
        from cas_forex.config import config

        return "mt5_direct" if bool(getattr(config, "prefer_mt5", False)) else "mt4_mailbox"
    except Exception:
        return "mt4_mailbox"


def _planned_steps() -> list[dict[str, Any]]:
    return [
        _step("terminal_receipt_watcher_force_run", "PLANNED", None, "Force receipt/history watcher chain."),
        _step("terminal_position_reconciliation", "PLANNED", None, "Rebuild position reconciliation from refreshed evidence."),
        _step("terminal_receipt_recovery_packet", "PLANNED", None, "Rebuild owner receipt recovery packet."),
        _step("live_recovery_status", "PLANNED", None, "Rebuild live recovery status from latest evidence."),
    ]


def _current_reports(
    *,
    recovery_packet: Mapping[str, Any] | None,
    live_recovery: Mapping[str, Any] | None,
) -> dict[str, Any]:
    reports: dict[str, Any] = {}
    packet = dict(recovery_packet) if recovery_packet is not None else _safe_current_recovery_packet()
    recovery = dict(live_recovery) if live_recovery is not None else _safe_live_recovery()
    if packet:
        reports["terminal_receipt_recovery_packet"] = _report_ref(packet, "status")
    if recovery:
        reports["live_recovery"] = _report_ref(recovery, "recovery_status")
    return reports


def _safe_current_recovery_packet() -> dict[str, Any]:
    try:
        reconciliation = load_latest_terminal_position_reconciliation_report()
        return build_terminal_receipt_recovery_packet(reconciliation_report=reconciliation)
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def _safe_live_recovery() -> dict[str, Any]:
    try:
        return build_live_recovery_report()
    except Exception as exc:
        return {"recovery_status": "unavailable", "error": str(exc)}


def _run_step(
    steps: list[dict[str, Any]],
    name: str,
    call: Callable[[], Mapping[str, Any]],
    status_key: str,
) -> dict[str, Any] | None:
    try:
        report = dict(call())
    except Exception as exc:
        steps.append(_step(name, "FAILED", None, str(exc)))
        return None
    status_label = report.get(status_key)
    steps.append(_step(name, "COMPLETE", status_label, "Step completed."))
    return report


def _step(name: str, status: str, status_label: Any, detail: str) -> dict[str, Any]:
    return {
        "step": name,
        "status": status,
        "status_label": status_label,
        "detail": detail,
    }


def _report_ref(report: Mapping[str, Any], status_key: str) -> dict[str, Any]:
    artifacts = report.get("artifact_paths") if isinstance(report.get("artifact_paths"), Mapping) else {}
    return {
        "report_kind": report.get("report_kind"),
        "status": report.get(status_key),
        "report_path": report.get("report_path") or artifacts.get("json"),
        "summary": dict(report.get("summary") or {}),
        "next_action": report.get("next_action"),
    }


def _action_payload(
    *,
    status: str,
    requested_execute: bool,
    owner_confirmed: bool,
    dry_run: bool,
    notes: str,
    steps: list[dict[str, Any]],
    reports: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "requested_execute": requested_execute,
        "confirm_owner_refresh": owner_confirmed,
        "dry_run": dry_run,
        "broker_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "money_moved": False,
        "notes_recorded": notes or "",
        "steps": steps,
        "reports": dict(reports),
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(status),
    }


def _next_action(status: str) -> str:
    if status == STATUS_CONFIRM_REQUIRED:
        return "Owner refresh confirmation is required before the local evidence refresh chain can run."
    if status == STATUS_DRY_RUN:
        return "Review the planned local evidence refresh chain; run it only after owner confirmation."
    if status == STATUS_RAN:
        return "Refresh chain ran. Review terminal receipt recovery, live recovery, and unresolved order-attempt packets before any live-money progression."
    return "Refresh chain failed; inspect the failed step detail before retrying or clearing recovery gates."


__all__ = [
    "REPORT_KIND",
    "run_terminal_receipt_recovery_refresh",
]
