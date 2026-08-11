"""Continuous broker-truth reconciliation monitor for CAS Forex.

Live money needs more than a manual emergency stop. This module runs a read-only
broker/terminal truth check on a timer so partial fills, stop-outs, orphaned
positions, stale terminal evidence, and CAS-vs-terminal mismatches are visible
while the system is operating.

The monitor never places orders, closes positions, deposits, withdraws, moves
bank/card money, automates payouts, or authorizes a real-money capability. It
only records evidence and provides a fresh reconciliation report that runtime
gates and auto-halt can consume fail-closed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Mapping, Optional

from cas_forex.account_reconciliation import (
    RECONCILED,
    RECONCILED_WITH_WARNINGS,
    RECONCILIATION_FAILED,
    STATUS_MISMATCH,
    STATUS_OK,
    STATUS_UNVERIFIABLE,
)
from cas_forex.auto_halt import activate_auto_halt, is_auto_halt_active
from cas_forex.broker_truth_monitor_supervisor import (
    BrokerTruthMonitorSupervisorConflict,
    BrokerTruthMonitorSupervisorStore,
    default_broker_truth_monitor_supervisor_store,
    process_owner_id,
)
from cas_forex.critical_notifications import (
    build_unprotected_position_event,
    emit_critical_notification,
)
from cas_forex.mt5_account_identity import evaluate_mt5_account_identity
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_MT5_DEPS = REPO_ROOT / ".mt5deps"
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "broker-truth-monitor-state.json"
DEFAULT_REPORT_DIR = REPO_ROOT / "evidence_runs" / "broker_truth_monitor"

MIN_INTERVAL_SECONDS = 5
DEFAULT_INTERVAL_SECONDS = 120
MAX_INTERVAL_SECONDS = 86_400
DEFAULT_FRESH_FOR_LIVE_SECONDS = 120

REPORT_KIND = "cas_forex_broker_truth_monitor"
STATUS_RUNNING = "BROKER_TRUTH_MONITOR_RUNNING"
STATUS_STOPPED = "BROKER_TRUTH_MONITOR_STOPPED"
STATUS_RECONCILED = "BROKER_TRUTH_RECONCILED"
STATUS_WARNINGS = "BROKER_TRUTH_RECONCILED_WITH_WARNINGS"
STATUS_FAILED = "BROKER_TRUTH_RECONCILIATION_FAILED"
STATUS_UNAVAILABLE = "BROKER_TRUTH_MONITOR_UNAVAILABLE"

TERMINAL_READY_STATUSES = {
    "TERMINAL_POSITION_RECONCILIATION_READY_OPEN_POSITIONS",
    "TERMINAL_POSITION_RECONCILIATION_READY_FLAT",
}
TERMINAL_MISMATCH_STATUSES = {
    "TERMINAL_POSITION_RECONCILIATION_MISMATCH",
}

CLAIM_BOUNDARY = (
    "Broker-truth monitor is read-only reconciliation. It reads MT5/terminal "
    "account and position evidence, writes audit reports, and can keep live "
    "runtime gates fail-closed when evidence is stale or contradictory. It does "
    "not place orders, close positions, deposit, withdraw, move bank/card money, "
    "automate payouts, create broker ACCEPT, or authorize live trading."
)


class BrokerTruthMonitorError(ValueError):
    """Raised when a broker-truth monitor report cannot be loaded or validated."""


class _MonitorState:
    def __init__(self) -> None:
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.interval = DEFAULT_INTERVAL_SECONDS
        self.cycles_run = 0
        self.last_error = ""
        self.started_at_iso = ""
        self.last_report: Optional[dict[str, Any]] = None
        self.supervisor_store: BrokerTruthMonitorSupervisorStore = default_broker_truth_monitor_supervisor_store()
        self.owner_id: str = process_owner_id()


_state = _MonitorState()
_lock = threading.Lock()


def set_monitor_supervisor_for_tests(
    store: BrokerTruthMonitorSupervisorStore | None = None,
    *,
    owner_id: str | None = None,
) -> None:
    """Inject/restore supervisor state for tests without touching runtime files."""
    with _lock:
        _state.supervisor_store = store or default_broker_truth_monitor_supervisor_store()
        _state.owner_id = owner_id or process_owner_id()


def run_broker_truth_check(
    *,
    mt5_snapshot: Optional[Mapping[str, Any]] = None,
    terminal_reconciliation_report: Optional[Mapping[str, Any]] = None,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    fresh_for_live_seconds: int = DEFAULT_FRESH_FOR_LIVE_SECONDS,
    write_state: bool = True,
    write_report: bool = True,
    state_path: Path | str | None = None,
    report_dir: Path | str = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    """Run one read-only broker-truth check and persist the latest report."""

    previous_report = _latest_report_for_transition_check(state_path=state_path)
    snapshot = dict(mt5_snapshot) if mt5_snapshot is not None else _read_mt5_snapshot()
    terminal_report, terminal_error = _terminal_reconciliation(
        terminal_reconciliation_report,
        active_execution_lane="mt5_direct",
    )
    report = build_broker_truth_monitor_report(
        mt5_snapshot=snapshot,
        terminal_reconciliation_report=terminal_report,
        terminal_error=terminal_error,
        interval_seconds=interval_seconds,
        fresh_for_live_seconds=fresh_for_live_seconds,
    )
    report.update(_continuous_monitor_fail_closed_actions(report, previous_report=previous_report))
    if write_report:
        report["artifact_paths"] = {
            key: str(value)
            for key, value in write_broker_truth_monitor_report(report, report_dir=report_dir).items()
        }
    if write_state:
        save_latest_broker_truth_monitor_report(report, state_path=state_path)
    with _lock:
        _state.last_report = report
    return report


def build_broker_truth_monitor_report(
    *,
    mt5_snapshot: Mapping[str, Any],
    terminal_reconciliation_report: Optional[Mapping[str, Any]] = None,
    terminal_error: Optional[str] = None,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    fresh_for_live_seconds: int = DEFAULT_FRESH_FOR_LIVE_SECONDS,
) -> dict[str, Any]:
    """Compose a monitor report from direct MT5 and terminal-reconciliation evidence."""

    generated_at = utc_now().isoformat()
    interval = _clamp_interval(interval_seconds)
    fresh_for_live = max(MIN_INTERVAL_SECONDS, int(fresh_for_live_seconds))
    terminal = dict(terminal_reconciliation_report or {})
    terminal_status = str(terminal.get("reconciliation_status") or "")
    terminal_summary = terminal.get("summary") if isinstance(terminal.get("summary"), Mapping) else {}
    classified_unmatched = (
        terminal.get("classified_unmatched_open_positions")
        if isinstance(terminal.get("classified_unmatched_open_positions"), list)
        else []
    )
    mt5_connected = bool(mt5_snapshot.get("connected", False))
    mt5_is_demo = bool(mt5_snapshot.get("is_demo", True)) if mt5_connected else None
    mt5_open_positions = int(mt5_snapshot.get("open_position_count", 0) or 0)
    mt5_position_rows = mt5_snapshot.get("positions") if isinstance(mt5_snapshot.get("positions"), list) else None
    mt5_account_snapshot = (
        dict(mt5_snapshot.get("account"))
        if isinstance(mt5_snapshot.get("account"), Mapping)
        else {}
    )
    account_identity = evaluate_mt5_account_identity(mt5_snapshot)
    position_protection = mt5_snapshot.get("position_protection") if isinstance(mt5_snapshot.get("position_protection"), Mapping) else {}
    position_protection_status = str(position_protection.get("status") or "")
    unprotected_position_count = int(position_protection.get("unprotected_position_count", 0) or 0)
    position_protection_detail = str(position_protection.get("detail") or "").strip()

    checks = [
        _check(
            "mt5_snapshot_read",
            STATUS_OK if mt5_connected else STATUS_UNVERIFIABLE,
            {"connected": mt5_connected, "diagnostic": mt5_snapshot.get("diagnostic"), "error": mt5_snapshot.get("error")},
            "Direct MT5 account snapshot is readable.",
            "MT5 account snapshot is connected and readable."
            if mt5_connected
            else f"MT5 account snapshot is not readable: {mt5_snapshot.get('detail') or mt5_snapshot.get('error') or 'unavailable'}.",
        ),
        _check(
            "mt5_live_account_visible",
            STATUS_OK if mt5_connected and mt5_is_demo is False else STATUS_UNVERIFIABLE,
            {"connected": mt5_connected, "is_demo": mt5_is_demo},
            "A connected live MT5 account is visible for live-money truth.",
            "Connected MT5 account reports LIVE mode."
            if mt5_connected and mt5_is_demo is False
                else "No connected live MT5 account is visible; live-money truth is not yet directly observable.",
        ),
        _mt5_account_identity_check(account_identity, connected=mt5_connected),
        _terminal_check(terminal_status, terminal_error, terminal_summary),
        _check(
            "live_open_positions_crosscheck",
            _live_open_position_status(
                mt5_connected,
                mt5_is_demo,
                mt5_open_positions,
                terminal_summary,
                mt5_position_rows=mt5_position_rows,
            ),
            {
                "mt5_open_positions": mt5_open_positions,
                "mt5_position_rows": len(mt5_position_rows) if mt5_position_rows is not None else None,
                "terminal_open_positions": terminal_summary.get("terminal_open_position_count"),
                "unmatched_open_positions": terminal_summary.get("unmatched_open_position_count"),
            },
            "Live open positions are cross-checked against terminal reconciliation.",
            _live_open_position_detail(
                mt5_connected,
                mt5_is_demo,
                mt5_open_positions,
                terminal_summary,
                mt5_position_rows=mt5_position_rows,
            ),
        ),
        _position_protection_check(
            mt5_connected=mt5_connected,
            mt5_is_demo=mt5_is_demo,
            mt5_open_positions=mt5_open_positions,
            position_protection=position_protection,
        ),
        _check(
            "monitor_freshness_recorded",
            STATUS_OK,
            {"generated_at": generated_at, "fresh_for_live_seconds": fresh_for_live},
            "Monitor report has a current timestamp for runtime-gate freshness.",
            "This broker-truth report was generated now and persisted as the latest monitor state.",
        ),
    ]
    mismatch_count = sum(1 for check in checks if check["status"] == STATUS_MISMATCH)
    unverifiable_count = sum(1 for check in checks if check["status"] == STATUS_UNVERIFIABLE)
    if mismatch_count:
        overall = RECONCILIATION_FAILED
        monitor_status = STATUS_FAILED
    elif unverifiable_count:
        overall = RECONCILED_WITH_WARNINGS
        monitor_status = STATUS_WARNINGS
    else:
        overall = RECONCILED
        monitor_status = STATUS_RECONCILED

    return {
        "report_kind": REPORT_KIND,
        "generated_at": generated_at,
        "monitor_status": monitor_status,
        "overall_status": overall,
        "checks_total": len(checks),
        "checks_ok": sum(1 for check in checks if check["status"] == STATUS_OK),
        "checks_mismatch": mismatch_count,
        "checks_unverifiable": unverifiable_count,
        "running_status": STATUS_RUNNING if _is_running() else STATUS_STOPPED,
        "interval_seconds": interval,
        "fresh_for_live_seconds": fresh_for_live,
        "mt5_connected": mt5_connected,
        "mt5_is_demo": mt5_is_demo,
        "mt5_account": mt5_account_snapshot.get("login"),
        "mt5_account_server": mt5_account_snapshot.get("server"),
        "mt5_expected_account": account_identity.get("expected_login"),
        "mt5_expected_server": account_identity.get("expected_server"),
        "mt5_account_identity_configured": account_identity.get("configured"),
        "mt5_account_identity_observable": account_identity.get("observable"),
        "mt5_account_identity_matches_config": account_identity.get("matches"),
        "mt5_account_identity_mismatch_fields": account_identity.get("mismatch_fields"),
        "mt5_account_currency": mt5_account_snapshot.get("currency"),
        "mt5_balance_usd": mt5_account_snapshot.get("balance_usd"),
        "mt5_equity_usd": mt5_account_snapshot.get("equity_usd"),
        "mt5_margin_used_usd": mt5_account_snapshot.get("margin_used_usd"),
        "mt5_free_margin_usd": mt5_account_snapshot.get("free_margin_usd"),
        "mt5_account_money_snapshot": mt5_account_snapshot or None,
        "mt5_open_position_count": mt5_open_positions,
        "position_protection_status": position_protection_status or None,
        "position_protection_open_position_count": int(position_protection.get("open_position_count", mt5_open_positions) or 0),
        "position_protection_unprotected_position_count": unprotected_position_count,
        "position_protection_requires_owner_attention": bool(position_protection.get("requires_owner_attention", False)),
        "position_protection_detail": position_protection_detail or None,
        "position_protection_unprotected_preview": _compact_unprotected_position_preview(
            position_protection.get("unprotected_positions")
            if isinstance(position_protection.get("unprotected_positions"), list)
            else []
        ),
        "terminal_reconciliation_status": terminal_status or None,
        "terminal_unmatched_open_position_count": int(terminal_summary.get("unmatched_open_position_count", 0) or 0),
        "terminal_unattributed_open_position_count": int(
            terminal_summary.get("terminal_unattributed_open_position_count", 0) or 0
        ),
        "terminal_memory_gap_open_position_count": int(
            terminal_summary.get("terminal_memory_gap_open_position_count", 0) or 0
        ),
        "cas_memory_only_open_position_count": int(
            terminal_summary.get("cas_memory_only_open_position_count", 0) or 0
        ),
        "cas_receipt_pending_open_position_count": int(
            terminal_summary.get("cas_receipt_pending_open_position_count", 0) or 0
        ),
        "terminal_unmatched_history_count": int(terminal_summary.get("unmatched_history_count", 0) or 0),
        "terminal_unattributed_history_count": int(
            terminal_summary.get("unmatched_unattributed_history_count", 0) or 0
        ),
        "terminal_attributed_history_memory_gap_count": int(
            terminal_summary.get("unmatched_attributed_history_memory_gap_count", 0) or 0
        ),
        "terminal_pending_receipt_count": int(terminal_summary.get("pending_receipt_count", 0) or 0),
        "terminal_receipt_mismatch_count": int(terminal_summary.get("receipt_mismatch_count", 0) or 0),
        "terminal_account_snapshot_present": bool(terminal_summary.get("account_snapshot_present", False)),
        "terminal_unmatched_open_position_preview": _compact_unmatched_position_preview(classified_unmatched),
        "terminal_unmatched_history_preview": _compact_unmatched_history_preview(
            terminal.get("classified_unmatched_history_records")
            if isinstance(terminal.get("classified_unmatched_history_records"), list)
            else []
        ),
        "checks": checks,
        "latest_terminal_reconciliation": terminal or None,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(
            overall,
            mt5_connected,
            mt5_is_demo,
            position_protection_status,
            unprotected_position_count,
            terminal_status,
            terminal_summary,
            account_identity,
        ),
    }


def write_broker_truth_monitor_report(
    report: Mapping[str, Any],
    *,
    report_dir: Path | str = DEFAULT_REPORT_DIR,
) -> dict[str, Path]:
    validate_broker_truth_monitor_report(report)
    target_dir = Path(report_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"broker-truth-monitor-{stamp}-report.json"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return {"json": json_path}


def save_latest_broker_truth_monitor_report(
    report: Mapping[str, Any],
    *,
    state_path: Path | str | None = None,
) -> Path:
    validate_broker_truth_monitor_report(report)
    target = Path(state_path) if state_path is not None else Path(DEFAULT_STATE_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(dict(report), indent=2, sort_keys=True, default=str)
    _write_json_state_atomic(target, payload)
    return target


def _write_json_state_atomic(target: Path, payload: str) -> None:
    last_error: PermissionError | None = None
    for attempt in range(5):
        tmp = target.with_name(
            f"{target.name}.{os.getpid()}.{threading.get_ident()}.{time.time_ns()}.tmp"
        )
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(tmp, target)
            return
        except PermissionError as exc:
            last_error = exc
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            time.sleep(0.05 * (attempt + 1))
    if last_error is not None:
        raise last_error


def load_latest_broker_truth_monitor_report(
    *,
    state_path: Path | str | None = None,
) -> dict[str, Any]:
    target = Path(state_path) if state_path is not None else Path(DEFAULT_STATE_PATH)
    if not target.exists():
        raise BrokerTruthMonitorError(f"No broker-truth monitor state found at {target}")
    try:
        report = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BrokerTruthMonitorError(f"Broker-truth monitor state is unreadable: {exc}") from exc
    validate_broker_truth_monitor_report(report)
    return report


def latest_reconciliation_report() -> Optional[dict[str, Any]]:
    """Return the latest auto-halt-compatible reconciliation report, if present."""

    try:
        return load_latest_broker_truth_monitor_report()
    except BrokerTruthMonitorError:
        return None


def broker_truth_monitor_ready_for_live(
    *,
    state_path: Path | str | None = None,
    max_age_seconds: int | None = None,
) -> bool:
    """Whether the latest monitor report is fresh enough for live trading."""

    try:
        report = load_latest_broker_truth_monitor_report(state_path=state_path)
    except BrokerTruthMonitorError:
        return False
    if report.get("overall_status") == RECONCILIATION_FAILED:
        return False
    return _report_ready_for_live(report, max_age_seconds=max_age_seconds)


def monitor_status() -> dict[str, Any]:
    with _lock:
        return _status_locked(load_from_disk=True)


def monitor_fast_status() -> dict[str, Any]:
    """Compact broker-truth status for UI polling.

    The full ``monitor_status`` keeps the complete latest reconciliation packet.
    Dashboard only needs a few labels, so this returns a small observational
    digest while preserving the same fail-closed readiness boundary.
    """
    with _lock:
        running = _is_running_locked()
        latest_report = _state.last_report
        interval = _state.interval
        cycles_run = _state.cycles_run
        last_error = _state.last_error or None
        started_at_iso = _state.started_at_iso or None
        supervisor = _state.supervisor_store.build_status(
            owner_id=_state.owner_id,
            local_running=running,
        )
    if latest_report is None:
        try:
            latest_report = load_latest_broker_truth_monitor_report()
        except BrokerTruthMonitorError:
            latest_report = None
    latest_status = (
        latest_report.get("monitor_status")
        if isinstance(latest_report, Mapping)
        else STATUS_UNAVAILABLE
    )
    return {
        "report_kind": "cas_forex_broker_truth_monitor_status_fast",
        "running": running,
        "status": "RUNNING" if running else "STOPPED",
        "interval_seconds": interval,
        "cycles_run": cycles_run,
        "last_error": last_error,
        "started_at_iso": started_at_iso,
        "monitor_status": latest_status,
        "ready_for_live": _report_ready_for_live(latest_report) if latest_report else False,
        "latest_report": _compact_broker_truth_report(latest_report),
        "supervisor": supervisor,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def start_monitor(interval_seconds: int = DEFAULT_INTERVAL_SECONDS) -> dict[str, Any]:
    from cas_forex.time_utils import utc_now as _now

    with _lock:
        _state.interval = _clamp_interval(interval_seconds)
        if _is_running_locked():
            renewed, _ = _state.supervisor_store.renew(
                owner_id=_state.owner_id,
                interval_seconds=_state.interval,
            )
            if not renewed:
                _state.last_error = "Supervisor lease conflict; local broker-truth monitor should stop."
                _state.stop_event.set()
            return _status_locked(load_from_disk=False)
        try:
            _state.supervisor_store.acquire(
                owner_id=_state.owner_id,
                interval_seconds=_state.interval,
            )
        except BrokerTruthMonitorSupervisorConflict as exc:
            _state.last_error = str(exc)
            status = _status_locked(load_from_disk=False)
            status["status"] = "SUPERVISOR_CONFLICT"
            status["detail"] = (
                "Another fresh broker-truth monitor owner already holds the durable "
                "lease; this process did not start a duplicate read-only monitor loop."
            )
            return status
        if not _is_running_locked():
            _state.stop_event.clear()
            _state.started_at_iso = _now().isoformat()
            _state.thread = threading.Thread(target=_run, name="cas-broker-truth-monitor", daemon=True)
            _state.thread.start()
        return _status_locked(load_from_disk=False)


def stop_monitor() -> dict[str, Any]:
    with _lock:
        _state.supervisor_store.request_stop(requested_by=_state.owner_id)
    with _lock:
        _state.stop_event.set()
        thread = _state.thread
    if thread and thread.is_alive():
        thread.join(timeout=3.0)
    with _lock:
        _state.thread = None
        _state.supervisor_store.release(owner_id=_state.owner_id)
        return _status_locked(load_from_disk=False)


def validate_broker_truth_monitor_report(report: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "generated_at",
        "monitor_status",
        "overall_status",
        "checks",
        "mt5_connected",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(report)
    if missing:
        raise BrokerTruthMonitorError(f"broker-truth monitor report missing fields: {sorted(missing)}")
    if report.get("report_kind") != REPORT_KIND:
        raise BrokerTruthMonitorError("unexpected broker-truth monitor report kind")
    if "does not place orders" not in str(report.get("claim_boundary", "")):
        raise BrokerTruthMonitorError("broker-truth monitor claim boundary must preserve read-only operation")
    if not isinstance(report.get("checks"), list):
        raise BrokerTruthMonitorError("checks must be a list")


def _status_locked(*, load_from_disk: bool) -> dict[str, Any]:
    running = _is_running_locked()
    latest_report = _state.last_report
    if latest_report is None and load_from_disk:
        try:
            latest_report = load_latest_broker_truth_monitor_report()
        except BrokerTruthMonitorError:
            latest_report = None
    latest_status = (
        latest_report.get("monitor_status")
        if isinstance(latest_report, Mapping)
        else STATUS_UNAVAILABLE
    )
    supervisor = _state.supervisor_store.build_status(
        owner_id=_state.owner_id,
        local_running=running,
    )
    return {
        "report_kind": "cas_forex_broker_truth_monitor_status",
        "running": running,
        "status": "RUNNING" if running else "STOPPED",
        "interval_seconds": _state.interval,
        "cycles_run": _state.cycles_run,
        "last_error": _state.last_error or None,
        "started_at_iso": _state.started_at_iso or None,
        "monitor_status": latest_status,
        "ready_for_live": _report_ready_for_live(latest_report) if latest_report else False,
        "latest_report": latest_report,
        "supervisor": supervisor,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _compact_broker_truth_report(report: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(report, Mapping):
        return None
    return {
        "report_kind": report.get("report_kind"),
        "generated_at": report.get("generated_at"),
        "monitor_status": report.get("monitor_status"),
        "overall_status": report.get("overall_status"),
        "running_status": report.get("running_status"),
        "mt5_connected": report.get("mt5_connected"),
        "mt5_is_demo": report.get("mt5_is_demo"),
        "mt5_account": report.get("mt5_account"),
        "mt5_account_server": report.get("mt5_account_server"),
        "mt5_expected_account": report.get("mt5_expected_account"),
        "mt5_expected_server": report.get("mt5_expected_server"),
        "mt5_account_identity_configured": report.get("mt5_account_identity_configured"),
        "mt5_account_identity_observable": report.get("mt5_account_identity_observable"),
        "mt5_account_identity_matches_config": report.get("mt5_account_identity_matches_config"),
        "mt5_account_identity_mismatch_fields": report.get("mt5_account_identity_mismatch_fields"),
        "mt5_account_currency": report.get("mt5_account_currency"),
        "mt5_balance_usd": report.get("mt5_balance_usd"),
        "mt5_equity_usd": report.get("mt5_equity_usd"),
        "mt5_margin_used_usd": report.get("mt5_margin_used_usd"),
        "mt5_free_margin_usd": report.get("mt5_free_margin_usd"),
        "mt5_open_position_count": report.get("mt5_open_position_count"),
        "position_protection_status": report.get("position_protection_status"),
        "position_protection_open_position_count": report.get("position_protection_open_position_count"),
        "position_protection_unprotected_position_count": report.get("position_protection_unprotected_position_count"),
        "position_protection_requires_owner_attention": report.get("position_protection_requires_owner_attention"),
        "position_protection_detail": report.get("position_protection_detail"),
        "position_protection_unprotected_preview": report.get("position_protection_unprotected_preview"),
        "auto_halt_latched_from_monitor": report.get("auto_halt_latched_from_monitor"),
        "monitor_auto_halt_reason_ids": report.get("monitor_auto_halt_reason_ids"),
        "terminal_reconciliation_status": report.get("terminal_reconciliation_status"),
        "terminal_unmatched_open_position_count": report.get("terminal_unmatched_open_position_count"),
        "terminal_unattributed_open_position_count": report.get("terminal_unattributed_open_position_count"),
        "terminal_memory_gap_open_position_count": report.get("terminal_memory_gap_open_position_count"),
        "cas_memory_only_open_position_count": report.get("cas_memory_only_open_position_count"),
        "cas_receipt_pending_open_position_count": report.get("cas_receipt_pending_open_position_count"),
        "terminal_unmatched_history_count": report.get("terminal_unmatched_history_count"),
        "terminal_unattributed_history_count": report.get("terminal_unattributed_history_count"),
        "terminal_attributed_history_memory_gap_count": report.get("terminal_attributed_history_memory_gap_count"),
        "terminal_pending_receipt_count": report.get("terminal_pending_receipt_count"),
        "terminal_receipt_mismatch_count": report.get("terminal_receipt_mismatch_count"),
        "terminal_account_snapshot_present": report.get("terminal_account_snapshot_present"),
        "terminal_unmatched_open_position_preview": report.get("terminal_unmatched_open_position_preview"),
        "terminal_unmatched_history_preview": report.get("terminal_unmatched_history_preview"),
        "fresh_for_live_seconds": report.get("fresh_for_live_seconds"),
        "next_action": report.get("next_action"),
    }


def _run() -> None:
    try:
        while not _state.stop_event.is_set():
            if _state.supervisor_store.should_stop(owner_id=_state.owner_id):
                with _lock:
                    _state.last_error = "Supervisor requested broker-truth monitor stop."
                break
            renewed, _ = _state.supervisor_store.renew(
                owner_id=_state.owner_id,
                interval_seconds=_state.interval,
            )
            if not renewed:
                with _lock:
                    _state.last_error = "Supervisor lease conflict; stopping this local broker-truth monitor."
                break
            try:
                report = run_broker_truth_check(interval_seconds=_state.interval)
                with _lock:
                    _state.cycles_run += 1
                    _state.last_report = report
                    _state.last_error = ""
            except Exception as exc:  # one bad read must not kill the monitor thread
                with _lock:
                    _state.last_error = f"{type(exc).__name__}: {exc}"
            _state.stop_event.wait(max(MIN_INTERVAL_SECONDS, _state.interval))
    finally:
        _state.supervisor_store.release(owner_id=_state.owner_id)


def _read_mt5_snapshot() -> dict[str, Any]:
    code = "\n".join(
        [
            "import json",
            "from cas_forex.config import config",
            "try:",
            "    from cas_forex.mt5_market_data_diagnostic import build_mt5_terminal_locator",
            "    locator = build_mt5_terminal_locator()",
            "    if (not getattr(config, 'mt5_path', None)) and locator.get('preferred_path_exists'):",
            "        config.mt5_path = str(locator.get('preferred_path') or '')",
            "except Exception:",
            "    pass",
            "config.mt5_login = 0",
            "config.mt5_password = ''",
            "config.mt5_server = ''",
            "from cas_forex.mt5_live import get_mt5_account_snapshot",
            "snapshot = get_mt5_account_snapshot(force=True)",
            "print(json.dumps(snapshot, default=str))",
        ]
    )
    try:
        completed = subprocess.run(
            [*_mt5_snapshot_python_command(), "-c", code],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            creationflags=_mt5_probe_creationflags(),
        )
    except subprocess.TimeoutExpired:
        return {
            "report_kind": "cas_forex_mt5_live_account",
            "connected": False,
            "diagnostic": "subprocess_timeout",
            "detail": "MT5 read timed out in the isolated broker-truth monitor subprocess.",
        }
    except Exception as exc:
        return {
            "report_kind": "cas_forex_mt5_live_account",
            "connected": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    if completed.returncode != 0:
        return {
            "report_kind": "cas_forex_mt5_live_account",
            "connected": False,
            "diagnostic": "subprocess_error",
            "detail": (completed.stderr or completed.stdout or "MT5 subprocess failed.").strip()[:1000],
        }
    try:
        line = next(line for line in reversed(completed.stdout.splitlines()) if line.strip())
        return json.loads(line)
    except Exception as exc:
        return {
            "report_kind": "cas_forex_mt5_live_account",
            "connected": False,
            "diagnostic": "subprocess_parse_error",
            "detail": f"{type(exc).__name__}: {exc}",
        }


def _mt5_snapshot_python_command() -> list[str]:
    configured = os.environ.get("CAS_FOREX_MT5_PYTHON")
    if configured:
        return [configured]
    local_core = LOCAL_MT5_DEPS / "MetaTrader5"
    has_cp312_mt5 = bool(list(local_core.glob("_core.cp312*.pyd")))
    if has_cp312_mt5 and sys.version_info[:2] != (3, 12) and shutil.which("py"):
        return ["py", "-3.12"]
    return [sys.executable]


def _mt5_probe_creationflags() -> int:
    if os.name != "nt":
        return 0
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) | int(
        getattr(
            subprocess,
            "IDLE_PRIORITY_CLASS",
            getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0),
        )
    )


def _terminal_reconciliation(
    provided: Optional[Mapping[str, Any]],
    *,
    active_execution_lane: str = "mt5_direct",
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    if provided is not None:
        return dict(provided), None
    try:
        from cas_forex.terminal_position_reconciliation import build_terminal_position_reconciliation_report

        return build_terminal_position_reconciliation_report(
            active_execution_lane=active_execution_lane,
            write_report=True,
        ), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _terminal_check(
    status: str,
    terminal_error: Optional[str],
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    if terminal_error:
        return _check(
            "terminal_position_reconciliation",
            STATUS_UNVERIFIABLE,
            {"error": terminal_error},
            "Terminal position reconciliation report is available.",
            f"Terminal position reconciliation could not run: {terminal_error}.",
        )
    if status in TERMINAL_MISMATCH_STATUSES:
        check_status = STATUS_MISMATCH
    elif status in TERMINAL_READY_STATUSES:
        check_status = STATUS_OK
    else:
        check_status = STATUS_UNVERIFIABLE
    return _check(
        "terminal_position_reconciliation",
        check_status,
        {
            "status": status or None,
            "unmatched": summary.get("unmatched_open_position_count"),
            "unmatched_history": summary.get("unmatched_history_count"),
            "unattributed_history": summary.get("unmatched_unattributed_history_count"),
            "pending": summary.get("pending_receipt_count"),
        },
        "CAS memory and terminal position evidence reconcile.",
        _terminal_detail(status, summary),
    )


def _position_protection_check(
    *,
    mt5_connected: bool,
    mt5_is_demo: Optional[bool],
    mt5_open_positions: int,
    position_protection: Mapping[str, Any],
) -> dict[str, Any]:
    if not mt5_connected:
        return _check(
            "live_position_stop_loss_protection",
            STATUS_UNVERIFIABLE,
            {"unprotected_position_count": None, "open_position_count": None},
            "Live open positions have broker-visible stop-loss protection.",
            "MT5 is not connected, so live stop-loss protection cannot be verified.",
        )
    if mt5_is_demo is not False:
        return _check(
            "live_position_stop_loss_protection",
            STATUS_UNVERIFIABLE,
            {"unprotected_position_count": None, "open_position_count": mt5_open_positions},
            "Live open positions have broker-visible stop-loss protection.",
            "MT5 is connected to demo/paper or mode is unknown; live stop-loss protection is not evaluated here.",
        )
    if not position_protection:
        return _check(
            "live_position_stop_loss_protection",
            STATUS_UNVERIFIABLE,
            {"unprotected_position_count": None, "open_position_count": mt5_open_positions},
            "Live open positions have broker-visible stop-loss protection.",
            "MT5 live snapshot did not include a position-protection report.",
        )

    status = str(position_protection.get("status") or "")
    unprotected = int(position_protection.get("unprotected_position_count", 0) or 0)
    open_count = int(position_protection.get("open_position_count", mt5_open_positions) or 0)
    detail = str(position_protection.get("detail") or "").strip()
    if status == "POSITION_PROTECTION_UNAVAILABLE" or position_protection.get("connected") is False:
        return _check(
            "live_position_stop_loss_protection",
            STATUS_UNVERIFIABLE,
            {"unprotected_position_count": None, "open_position_count": open_count},
            "Live open positions have broker-visible stop-loss protection.",
            detail or "Live stop-loss protection report is unavailable.",
        )
    if unprotected > 0:
        return _check(
            "live_position_stop_loss_protection",
            STATUS_MISMATCH,
            {"unprotected_position_count": unprotected, "open_position_count": open_count},
            "Live open positions have broker-visible stop-loss protection.",
            detail or f"Live MT5 snapshot shows {unprotected} open position(s) without visible broker-side stop loss.",
        )
    return _check(
        "live_position_stop_loss_protection",
        STATUS_OK,
        {"unprotected_position_count": 0, "open_position_count": open_count},
        "Live open positions have broker-visible stop-loss protection.",
        detail or f"Live MT5 snapshot shows 0 unprotected positions across {open_count} open.",
    )


def _live_open_position_status(
    mt5_connected: bool,
    mt5_is_demo: Optional[bool],
    mt5_open_positions: int,
    terminal_summary: Mapping[str, Any],
    *,
    mt5_position_rows: Optional[list[Any]] = None,
) -> str:
    if not mt5_connected or mt5_is_demo is not False:
        return STATUS_UNVERIFIABLE
    active_mt5_lane = str(terminal_summary.get("active_execution_lane") or "") == "mt5_demo"
    unmatched = int(
        terminal_summary.get(
            "active_unmatched_open_position_count" if active_mt5_lane else "unmatched_open_position_count",
            0,
        )
        or 0
    )
    if unmatched > 0:
        return STATUS_MISMATCH
    if active_mt5_lane:
        if mt5_position_rows is None:
            return STATUS_UNVERIFIABLE
        return STATUS_OK if len(mt5_position_rows) == int(mt5_open_positions) else STATUS_MISMATCH
    terminal_count = terminal_summary.get("terminal_open_position_count")
    if terminal_count is None:
        return STATUS_UNVERIFIABLE
    try:
        if int(terminal_count) != int(mt5_open_positions):
            return STATUS_MISMATCH
    except (TypeError, ValueError):
        return STATUS_UNVERIFIABLE
    return STATUS_OK


def _live_open_position_detail(
    mt5_connected: bool,
    mt5_is_demo: Optional[bool],
    mt5_open_positions: int,
    terminal_summary: Mapping[str, Any],
    *,
    mt5_position_rows: Optional[list[Any]] = None,
) -> str:
    if not mt5_connected:
        return "MT5 is not connected, so live open positions are not directly observable."
    if mt5_is_demo is not False:
        return "MT5 is connected to demo/paper or mode is unknown; no live open-position crosscheck is possible."
    active_mt5_lane = str(terminal_summary.get("active_execution_lane") or "") == "mt5_demo"
    unmatched = int(
        terminal_summary.get(
            "active_unmatched_open_position_count" if active_mt5_lane else "unmatched_open_position_count",
            0,
        )
        or 0
    )
    if unmatched > 0:
        unattributed = int(terminal_summary.get("terminal_unattributed_open_position_count", 0) or 0)
        memory_gap = int(terminal_summary.get("terminal_memory_gap_open_position_count", 0) or 0)
        if unattributed > 0:
            return (
                f"Terminal reconciliation reports {unmatched} unmatched open position(s), including "
                f"{unattributed} broker-visible position(s) CAS cannot attribute."
            )
        if memory_gap > 0:
            return (
                f"Terminal reconciliation reports {unmatched} unmatched open position(s), including "
                f"{memory_gap} broker-visible position(s) that carry CAS identifiers but are missing from joined memory."
            )
        return f"Terminal reconciliation reports {unmatched} unmatched open position(s)."
    if active_mt5_lane:
        if mt5_position_rows is None:
            return "Direct MT5 position rows are unavailable, so the broker position count cannot be internally cross-checked."
        if len(mt5_position_rows) != int(mt5_open_positions):
            return (
                f"Direct MT5 snapshot count is {mt5_open_positions}, but the snapshot contains "
                f"{len(mt5_position_rows)} position row(s)."
            )
        return (
            f"Direct MT5 snapshot count and position rows agree at {mt5_open_positions}; "
            "inactive MT4 mailbox counts are not used for MT5 readiness."
        )
    return f"Live MT5 open position count is {mt5_open_positions}; terminal reconciliation has no unmatched open positions."


def _terminal_detail(status: str, summary: Mapping[str, Any]) -> str:
    if status in TERMINAL_READY_STATUSES:
        return "Terminal position reconciliation is ready and reports no mismatch."
    if status in TERMINAL_MISMATCH_STATUSES:
        unattributed_history = int(summary.get("unmatched_unattributed_history_count", 0) or 0)
        unattributed_open = int(summary.get("terminal_unattributed_open_position_count", 0) or 0)
        if unattributed_open > 0:
            return "Terminal position reconciliation reports broker-visible open positions CAS cannot attribute."
        if unattributed_history > 0:
            return "Terminal position reconciliation reports broker closed-history rows CAS cannot attribute."
        return "Terminal position reconciliation reports a CAS-vs-terminal mismatch."
    if not status:
        return "No terminal position reconciliation report is available."
    return f"Terminal position reconciliation status is {status}; treat as live-readiness warning until resolved."


def _check(check_id: str, status: str, value: Any, description: str, detail: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": status,
        "value": value,
        "description": description,
        "detail": detail,
        "trips_auto_halt": status == STATUS_MISMATCH,
    }


def _mt5_account_identity_check(
    identity: Mapping[str, Any],
    *,
    connected: bool,
) -> dict[str, Any]:
    evidence = {
        "configured": bool(identity.get("configured")),
        "observable": bool(identity.get("observable")),
        "expected_login": identity.get("expected_login"),
        "expected_server": identity.get("expected_server"),
        "actual_login": identity.get("actual_login"),
        "actual_server": identity.get("actual_server"),
        "matches": identity.get("matches"),
        "mismatch_fields": list(identity.get("mismatch_fields") or []),
    }
    if not connected:
        status = STATUS_UNVERIFIABLE
        detail = "MT5 is disconnected, so the configured account identity cannot be verified."
    elif not identity.get("configured"):
        status = STATUS_UNVERIFIABLE
        detail = "Configured mt5_login and mt5_server are required to bind broker truth to the owner-approved account."
    elif not identity.get("observable"):
        status = STATUS_UNVERIFIABLE
        detail = "MT5 is connected, but its account login/server identity is not fully observable."
    elif identity.get("matches") is True:
        status = STATUS_OK
        detail = (
            f"Connected MT5 login {identity.get('actual_login')} on server "
            f"{identity.get('actual_server')} exactly matches the configured owner account."
        )
    else:
        status = STATUS_MISMATCH
        detail = (
            f"Wrong MT5 account: connected login {identity.get('actual_login')} on server "
            f"{identity.get('actual_server') or 'unknown'} does not match configured login "
            f"{identity.get('expected_login')} on server {identity.get('expected_server') or 'unknown'}."
        )
    return _check(
        "mt5_account_identity_matches_config",
        status,
        evidence,
        "Connected MT5 login and server match the configured owner-approved account.",
        detail,
    )


def _next_action(
    overall: str,
    mt5_connected: bool,
    mt5_is_demo: Optional[bool],
    position_protection_status: str,
    unprotected_position_count: int,
    terminal_status: str,
    terminal_summary: Mapping[str, Any],
    account_identity: Mapping[str, Any],
) -> str:
    if mt5_connected and account_identity.get("matches") is False:
        return (
            f"Keep CAS fail-closed: MT5 is connected to login {account_identity.get('actual_login')} "
            f"on {account_identity.get('actual_server') or 'unknown'}, but CAS is configured for login "
            f"{account_identity.get('expected_login')} on {account_identity.get('expected_server') or 'unknown'}. "
            "Log the Risen terminal into the configured owner account and rerun broker truth."
        )
    if not account_identity.get("configured"):
        return "Configure the owner-approved MT5 login and server before broker truth can unlock live execution."
    if mt5_connected and not account_identity.get("observable"):
        return "Keep CAS fail-closed until MT5 exposes the connected account login and server identity."
    if overall == RECONCILIATION_FAILED:
        if position_protection_status == "UNPROTECTED_POSITIONS" or unprotected_position_count > 0:
            return (
                "Keep CAS in paper/fail-closed mode and add broker-side stop loss protection to every live open position "
                "before allowing further automated exposure."
            )
        if int(terminal_summary.get("terminal_unattributed_open_position_count", 0) or 0) > 0:
            return (
                "Keep CAS in paper/fail-closed mode and owner-review unmatched broker-visible positions that CAS cannot attribute before allowing another live cycle."
            )
        if int(terminal_summary.get("terminal_memory_gap_open_position_count", 0) or 0) > 0:
            return (
                "Keep CAS in paper/fail-closed mode, run receipt/history ingest, rebuild memory, and rerun broker truth before allowing another live cycle."
            )
        if int(terminal_summary.get("unmatched_unattributed_history_count", 0) or 0) > 0:
            return (
                "Keep CAS in paper/fail-closed mode and owner-review unmatched broker closed-history rows that CAS cannot attribute before allowing another live cycle."
            )
        if int(terminal_summary.get("unmatched_attributed_history_memory_gap_count", 0) or 0) > 0:
            return (
                "Keep CAS in paper/fail-closed mode, rerun terminal history ingest, rebuild memory, and rerun broker truth before allowing another live cycle."
            )
        return "Keep CAS in paper/fail-closed mode and inspect broker-truth mismatches before allowing another live cycle."
    if not mt5_connected:
        return "Open/log into MetaTrader, then keep broker-truth monitoring running before any live-money scaling."
    if mt5_is_demo is not False:
        return "Broker-truth monitoring is running on demo/paper evidence; live gate still needs a connected live account."
    if terminal_status not in TERMINAL_READY_STATUSES:
        return "Live account is visible, but terminal reconciliation is not fully ready; resolve warnings before scaling."
    return "Broker truth is fresh and live-visible; keep the monitor running during any owner-authorized live session."


def _continuous_monitor_fail_closed_actions(
    report: Mapping[str, Any],
    *,
    previous_report: Mapping[str, Any] | None,
) -> dict[str, Any]:
    live_visible = bool(report.get("mt5_connected")) and report.get("mt5_is_demo") is False
    mismatched_checks = [
        check
        for check in (report.get("checks") or [])
        if isinstance(check, Mapping) and str(check.get("status") or "") == STATUS_MISMATCH
    ]
    mismatch_reason_ids = [str(check.get("check_id") or "").strip() for check in mismatched_checks if str(check.get("check_id") or "").strip()]

    identity_mismatch_checks = [
        check
        for check in mismatched_checks
        if str(check.get("check_id") or "") == "mt5_account_identity_matches_config"
    ]
    latch_checks = mismatched_checks if live_visible else identity_mismatch_checks
    auto_halt_latched = False
    if latch_checks and not is_auto_halt_active():
        activate_auto_halt(
            [str(check.get("check_id") or "") for check in latch_checks],
            [
                {
                    "check_id": check_id,
                    "status": "TRIPPED",
                    "metric": check.get("value"),
                    "threshold": "MISMATCH_FREE",
                    "detail": str(check.get("detail") or ""),
                    "trips_halt": True,
                    "source": "broker_truth_monitor",
                    "source_report_kind": report.get("report_kind"),
                }
                for check in latch_checks
                for check_id in [str(check.get("check_id") or "").strip()]
                if check_id
            ],
        )
        auto_halt_latched = True

    status = str(report.get("position_protection_status") or "")
    unprotected_count = int(report.get("position_protection_unprotected_position_count", 0) or 0)
    if status != "UNPROTECTED_POSITIONS" or unprotected_count <= 0:
        return {
            "auto_halt_latched_from_monitor": auto_halt_latched,
            "monitor_auto_halt_reason_ids": mismatch_reason_ids,
            "position_protection_notification_emitted": False,
        }

    previous_unprotected = 0
    if isinstance(previous_report, Mapping):
        previous_unprotected = int(previous_report.get("position_protection_unprotected_position_count", 0) or 0)

    notification_emitted = False
    if previous_unprotected <= 0:
        notification_audit = emit_critical_notification(
            build_unprotected_position_event(
                {
                    "status": status,
                    "source": "broker_truth_monitor",
                    "open_position_count": report.get("position_protection_open_position_count"),
                    "unprotected_position_count": unprotected_count,
                    "unprotected_positions": report.get("position_protection_unprotected_preview") or [],
                }
            ),
            source="broker_truth_monitor.position_protection",
        )
        notification_emitted = True
        return {
            "auto_halt_latched_from_monitor": auto_halt_latched,
            "monitor_auto_halt_reason_ids": mismatch_reason_ids,
            "position_protection_notification_emitted": notification_emitted,
            "position_protection_notification_audit": notification_audit,
        }

    return {
        "auto_halt_latched_from_monitor": auto_halt_latched,
        "monitor_auto_halt_reason_ids": mismatch_reason_ids,
        "position_protection_notification_emitted": notification_emitted,
    }


def _latest_report_for_transition_check(
    *,
    state_path: Path | str | None = None,
) -> Mapping[str, Any] | None:
    if state_path is not None:
        try:
            return load_latest_broker_truth_monitor_report(state_path=state_path)
        except BrokerTruthMonitorError:
            return None
    with _lock:
        if isinstance(_state.last_report, Mapping):
            return dict(_state.last_report)
    try:
        return load_latest_broker_truth_monitor_report(state_path=state_path)
    except BrokerTruthMonitorError:
        return None


def _compact_unmatched_position_preview(rows: list[Any]) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for row in rows[:3]:
        if not isinstance(row, Mapping):
            continue
        position = row.get("position") if isinstance(row.get("position"), Mapping) else {}
        preview.append(
            {
                "side": row.get("side"),
                "reason": row.get("reason"),
                "classification_status": row.get("classification_status"),
                "classification_detail": row.get("classification_detail"),
                "symbol": position.get("symbol"),
                "direction": position.get("direction"),
                "lots": position.get("lots"),
                "broker_ticket": position.get("broker_ticket"),
                "command_id": position.get("command_id"),
                "receipt_id": position.get("receipt_id"),
            }
        )
    return preview


def _compact_unmatched_history_preview(rows: list[Any]) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for row in rows[:3]:
        if not isinstance(row, Mapping):
            continue
        preview.append(
            {
                "classification_status": row.get("classification_status"),
                "classification_detail": row.get("classification_detail"),
                "symbol": row.get("symbol"),
                "direction": row.get("direction"),
                "lots": row.get("lots"),
                "broker_ticket": row.get("broker_ticket"),
                "command_id": row.get("command_id"),
                "receipt_id": row.get("receipt_id"),
                "closed_at": row.get("closed_at"),
                "profit_loss_account": row.get("profit_loss_account"),
            }
        )
    return preview


def _compact_unprotected_position_preview(rows: list[Any]) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for row in rows[:3]:
        if not isinstance(row, Mapping):
            continue
        preview.append(
            {
                "ticket": row.get("ticket"),
                "symbol": row.get("symbol"),
                "side": row.get("side"),
                "lots": row.get("lots"),
                "open_price": row.get("open_price"),
                "current_price": row.get("current_price"),
                "stop_loss": row.get("stop_loss"),
                "take_profit": row.get("take_profit"),
                "floating_pnl_usd": row.get("floating_pnl_usd"),
            }
        )
    return preview


def _clamp_interval(value: int) -> int:
    return max(MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, int(value)))


def _is_running() -> bool:
    with _lock:
        return _is_running_locked()


def _is_running_locked() -> bool:
    return bool(_state.thread and _state.thread.is_alive())


def _is_report_fresh(report: Mapping[str, Any], *, max_age_seconds: int | None = None) -> bool:
    generated = report.get("generated_at")
    if not generated:
        return False
    try:
        from datetime import datetime

        generated_dt = datetime.fromisoformat(str(generated).replace("Z", "+00:00"))
        age = (utc_now() - generated_dt).total_seconds()
    except Exception:
        return False
    limit = max_age_seconds
    if limit is None:
        limit = int(report.get("fresh_for_live_seconds", DEFAULT_FRESH_FOR_LIVE_SECONDS) or DEFAULT_FRESH_FOR_LIVE_SECONDS)
    return 0 <= age <= int(limit)


def _report_ready_for_live(report: Mapping[str, Any], *, max_age_seconds: int | None = None) -> bool:
    if report.get("overall_status") == RECONCILIATION_FAILED:
        return False
    if not bool(report.get("mt5_connected")) or report.get("mt5_is_demo") is not False:
        return False
    if report.get("mt5_account_identity_matches_config") is not True:
        return False
    return _is_report_fresh(report, max_age_seconds=max_age_seconds)
