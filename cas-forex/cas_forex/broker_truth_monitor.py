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
from cas_forex.broker_truth_monitor_supervisor import (
    BrokerTruthMonitorSupervisorConflict,
    BrokerTruthMonitorSupervisorStore,
    default_broker_truth_monitor_supervisor_store,
    process_owner_id,
)
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

    snapshot = dict(mt5_snapshot) if mt5_snapshot is not None else _read_mt5_snapshot()
    terminal_report, terminal_error = _terminal_reconciliation(terminal_reconciliation_report)
    report = build_broker_truth_monitor_report(
        mt5_snapshot=snapshot,
        terminal_reconciliation_report=terminal_report,
        terminal_error=terminal_error,
        interval_seconds=interval_seconds,
        fresh_for_live_seconds=fresh_for_live_seconds,
    )
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
    mt5_connected = bool(mt5_snapshot.get("connected", False))
    mt5_is_demo = bool(mt5_snapshot.get("is_demo", True)) if mt5_connected else None
    mt5_open_positions = int(mt5_snapshot.get("open_position_count", 0) or 0)

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
        _terminal_check(terminal_status, terminal_error, terminal_summary),
        _check(
            "live_open_positions_crosscheck",
            _live_open_position_status(mt5_connected, mt5_is_demo, mt5_open_positions, terminal_summary),
            {
                "mt5_open_positions": mt5_open_positions,
                "terminal_open_positions": terminal_summary.get("terminal_open_position_count"),
                "unmatched_open_positions": terminal_summary.get("unmatched_open_position_count"),
            },
            "Live open positions are cross-checked against terminal reconciliation.",
            _live_open_position_detail(mt5_connected, mt5_is_demo, mt5_open_positions, terminal_summary),
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
        "mt5_open_position_count": mt5_open_positions,
        "terminal_reconciliation_status": terminal_status or None,
        "terminal_unmatched_open_position_count": int(terminal_summary.get("unmatched_open_position_count", 0) or 0),
        "terminal_pending_receipt_count": int(terminal_summary.get("pending_receipt_count", 0) or 0),
        "terminal_receipt_mismatch_count": int(terminal_summary.get("receipt_mismatch_count", 0) or 0),
        "terminal_account_snapshot_present": bool(terminal_summary.get("account_snapshot_present", False)),
        "checks": checks,
        "latest_terminal_reconciliation": terminal or None,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(overall, mt5_connected, mt5_is_demo, terminal_status),
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
        "mt5_open_position_count": report.get("mt5_open_position_count"),
        "terminal_reconciliation_status": report.get("terminal_reconciliation_status"),
        "terminal_unmatched_open_position_count": report.get("terminal_unmatched_open_position_count"),
        "terminal_pending_receipt_count": report.get("terminal_pending_receipt_count"),
        "terminal_receipt_mismatch_count": report.get("terminal_receipt_mismatch_count"),
        "terminal_account_snapshot_present": report.get("terminal_account_snapshot_present"),
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
            "print(json.dumps(get_mt5_account_snapshot(force=True), default=str))",
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
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    if provided is not None:
        return dict(provided), None
    try:
        from cas_forex.terminal_position_reconciliation import build_terminal_position_reconciliation_report

        return build_terminal_position_reconciliation_report(write_report=True), None
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
            "pending": summary.get("pending_receipt_count"),
        },
        "CAS memory and terminal position evidence reconcile.",
        _terminal_detail(status),
    )


def _live_open_position_status(
    mt5_connected: bool,
    mt5_is_demo: Optional[bool],
    mt5_open_positions: int,
    terminal_summary: Mapping[str, Any],
) -> str:
    if not mt5_connected or mt5_is_demo is not False:
        return STATUS_UNVERIFIABLE
    unmatched = int(terminal_summary.get("unmatched_open_position_count", 0) or 0)
    if unmatched > 0:
        return STATUS_MISMATCH
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
) -> str:
    if not mt5_connected:
        return "MT5 is not connected, so live open positions are not directly observable."
    if mt5_is_demo is not False:
        return "MT5 is connected to demo/paper or mode is unknown; no live open-position crosscheck is possible."
    unmatched = int(terminal_summary.get("unmatched_open_position_count", 0) or 0)
    if unmatched > 0:
        return f"Terminal reconciliation reports {unmatched} unmatched open position(s)."
    return f"Live MT5 open position count is {mt5_open_positions}; terminal reconciliation has no unmatched open positions."


def _terminal_detail(status: str) -> str:
    if status in TERMINAL_READY_STATUSES:
        return "Terminal position reconciliation is ready and reports no mismatch."
    if status in TERMINAL_MISMATCH_STATUSES:
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


def _next_action(overall: str, mt5_connected: bool, mt5_is_demo: Optional[bool], terminal_status: str) -> str:
    if overall == RECONCILIATION_FAILED:
        return "Keep CAS in paper/fail-closed mode and inspect broker-truth mismatches before allowing another live cycle."
    if not mt5_connected:
        return "Open/log into MetaTrader, then keep broker-truth monitoring running before any live-money scaling."
    if mt5_is_demo is not False:
        return "Broker-truth monitoring is running on demo/paper evidence; live gate still needs a connected live account."
    if terminal_status not in TERMINAL_READY_STATUSES:
        return "Live account is visible, but terminal reconciliation is not fully ready; resolve warnings before scaling."
    return "Broker truth is fresh and live-visible; keep the monitor running during any owner-authorized live session."


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
    return _is_report_fresh(report, max_age_seconds=max_age_seconds)
