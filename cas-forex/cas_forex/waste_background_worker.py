"""Process-isolated workers for heavy WASTE timers.

The API must stay responsive even while WASTE is reading broker-grade candles
or collecting paper evidence. Threading those loops inside the uvicorn process
can starve simple routes such as /health, so production/local UI starts route
through this tiny worker supervisor. Tests still use the in-process runners.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping

from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = REPO_ROOT / "runtime"
LOG_DIR = RUNTIME_DIR / "worker-logs"
STATE_PATH = RUNTIME_DIR / "waste-background-workers.json"

RUNNER_KIND = "waste_runner"
COLLECTOR_KIND = "paper_sample_collector"
BROKER_TRUTH_KIND = "broker_truth_monitor"
PROOF_RUNNER_KIND = "proof_auto_runner"


def use_in_process_workers_for_tests() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def start_waste_runner_worker(*, interval_seconds: int, confirm: bool = False) -> dict[str, Any]:
    if use_in_process_workers_for_tests():
        from cas_forex.waste_runner import start_runner

        return start_runner(interval_seconds, confirm=confirm)
    worker = _start_worker(
        RUNNER_KIND,
        [
            "runner",
            "--interval-seconds",
            str(int(interval_seconds)),
            *(["--confirm"] if confirm else []),
        ],
        config={"interval_seconds": int(interval_seconds), "confirm": bool(confirm)},
    )
    return _runner_route_status(worker)


def stop_waste_runner_worker() -> dict[str, Any]:
    if use_in_process_workers_for_tests():
        from cas_forex.waste_runner import stop_runner

        return stop_runner()
    try:
        from cas_forex.waste_runner import stop_runner

        local_status = stop_runner()
    except Exception as exc:  # pragma: no cover - defensive status only
        local_status = {
            "report_kind": "cas_forex_waste_runner",
            "status": "STOP_ERROR",
            "running": False,
            "last_error": f"{type(exc).__name__}: {exc}",
        }
    worker = _stop_worker(RUNNER_KIND)
    packet = dict(local_status)
    packet["running"] = False
    packet["status"] = "STOPPED"
    packet["external_worker"] = worker
    return packet


def overlay_waste_runner_status(status: Mapping[str, Any]) -> dict[str, Any]:
    packet = dict(status)
    worker = worker_status(RUNNER_KIND)
    packet["external_worker"] = worker
    supervisor: dict[str, Any] = {}
    try:
        from cas_forex.waste_runner_supervisor import (
            default_waste_runner_supervisor_store,
            process_owner_id,
        )

        supervisor = default_waste_runner_supervisor_store().build_status(
            owner_id=process_owner_id(),
            local_running=False,
        )
    except Exception:
        supervisor = {}
    lease = _mapping(supervisor.get("active_lease"))
    supervisor_running = bool(
        supervisor.get("desired_running")
        and supervisor.get("active_lease_is_fresh")
        and lease
    )
    if supervisor:
        packet["supervisor"] = supervisor
    if worker.get("running") or supervisor_running:
        durable_cycle = _mapping(packet.get("durable_cycle"))
        stage_trace = durable_cycle.get("stage_trace")
        if _int(packet.get("cycles_run"), 0) <= 0:
            packet["cycles_run"] = _int(durable_cycle.get("cycles_run"), 0)
        if not packet.get("last_decision") and durable_cycle.get("decision"):
            packet["last_decision"] = durable_cycle.get("decision")
        if not packet.get("last_reason") and durable_cycle.get("reason"):
            packet["last_reason"] = durable_cycle.get("reason")
        if not packet.get("last_run_iso") and durable_cycle.get("generated_at"):
            packet["last_run_iso"] = durable_cycle.get("generated_at")
        if not packet.get("started_at_iso") and worker.get("started_at"):
            packet["started_at_iso"] = worker.get("started_at")
        if _int(packet.get("interval_seconds"), 0) <= 0:
            config = _mapping(worker.get("config"))
            packet["interval_seconds"] = (
                _int(durable_cycle.get("interval_seconds"), _int(config.get("interval_seconds"), 0))
                or _int(lease.get("interval_seconds"), 0)
                or packet.get("interval_seconds")
            )
        if not packet.get("started_at_iso") and lease.get("acquired_at"):
            packet["started_at_iso"] = lease.get("acquired_at")
        if isinstance(stage_trace, list) and stage_trace:
            current_stage = str(packet.get("current_stage") or "").lower()
            if current_stage in {"", "idle", "stopped"}:
                packet["current_stage"] = stage_trace[-1]
        packet["running"] = True
        packet["status"] = "RUNNING"
        packet["worker_isolated"] = True
    return packet


def start_paper_sample_collector_worker(**kwargs: Any) -> dict[str, Any]:
    if use_in_process_workers_for_tests():
        from cas_forex.waste_paper_sample_collector import (
            start_waste_paper_sample_collector_scheduler,
        )

        return start_waste_paper_sample_collector_scheduler(**kwargs)
    args = ["collector", "--config-json", json.dumps(dict(kwargs), sort_keys=True, default=str)]
    worker = _start_worker(COLLECTOR_KIND, args, config=dict(kwargs))
    return _collector_route_status(worker)


def stop_paper_sample_collector_worker() -> dict[str, Any]:
    if use_in_process_workers_for_tests():
        from cas_forex.waste_paper_sample_collector import (
            stop_waste_paper_sample_collector_scheduler,
        )

        return stop_waste_paper_sample_collector_scheduler()
    try:
        from cas_forex.waste_paper_sample_collector import (
            stop_waste_paper_sample_collector_scheduler,
        )

        local_status = stop_waste_paper_sample_collector_scheduler()
    except Exception as exc:  # pragma: no cover - defensive status only
        local_status = {
            "report_kind": "cas_forex_waste_paper_sample_collector_scheduler",
            "status": "STOP_ERROR",
            "running": False,
            "last_error": f"{type(exc).__name__}: {exc}",
        }
    worker = _stop_worker(COLLECTOR_KIND)
    packet = dict(local_status)
    packet["running"] = False
    packet["status"] = "WASTE_PAPER_SAMPLE_COLLECTOR_STOPPED"
    packet["external_worker"] = worker
    return packet


def overlay_paper_sample_collector_status(status: Mapping[str, Any]) -> dict[str, Any]:
    packet = dict(status)
    worker = worker_status(COLLECTOR_KIND)
    packet["external_worker"] = worker
    if worker.get("running"):
        disk = _load_json_file(RUNTIME_DIR / "waste-paper-sample-collector-scheduler.json")
        for key in (
            "cycles_run",
            "started_at_iso",
            "last_run_iso",
            "last_error",
            "latest_run",
            "latest_collector_status",
            "sample_collection_complete",
            "market_data_ready",
            "confirmed_direction_count",
            "bound_outcome_count",
            "bound_outcomes_needed",
        ):
            if _is_empty_status_value(packet.get(key)) and key in disk:
                packet[key] = disk.get(key)
        if _is_empty_status_value(packet.get("interval_seconds")):
            config = _mapping(worker.get("config"))
            packet["interval_seconds"] = _int(
                disk.get("interval_seconds"),
                _int(config.get("interval_seconds"), 0),
            ) or packet.get("interval_seconds")
        if _is_empty_status_value(packet.get("started_at_iso")) and worker.get("started_at"):
            packet["started_at_iso"] = worker.get("started_at")
        if str(packet.get("next_action") or "").lower().startswith("start the paper sample"):
            packet["next_action"] = (
                "Paper sample collector scheduler is running in an isolated worker; "
                "wait for the next scheduled paper evidence pass or run one probe now."
            )
        packet["running"] = True
        packet["status"] = "WASTE_PAPER_SAMPLE_COLLECTOR_RUNNING"
        packet["worker_isolated"] = True
    return packet


def start_broker_truth_monitor_worker(*, interval_seconds: int) -> dict[str, Any]:
    if use_in_process_workers_for_tests():
        from cas_forex.broker_truth_monitor import start_monitor

        return start_monitor(interval_seconds)
    worker = _start_worker(
        BROKER_TRUTH_KIND,
        ["broker-truth-monitor", "--interval-seconds", str(int(interval_seconds))],
        config={"interval_seconds": int(interval_seconds)},
    )
    return _broker_truth_route_status(worker)


def stop_broker_truth_monitor_worker() -> dict[str, Any]:
    if use_in_process_workers_for_tests():
        from cas_forex.broker_truth_monitor import stop_monitor

        return stop_monitor()
    try:
        from cas_forex.broker_truth_monitor_supervisor import (
            default_broker_truth_monitor_supervisor_store,
            process_owner_id,
        )

        default_broker_truth_monitor_supervisor_store().request_stop(
            requested_by=process_owner_id(),
        )
    except Exception:
        pass
    worker = _stop_worker(BROKER_TRUTH_KIND)
    try:
        from cas_forex.broker_truth_monitor_supervisor import (
            default_broker_truth_monitor_supervisor_store,
            process_owner_id,
        )

        default_broker_truth_monitor_supervisor_store().recover_stale_or_requested(
            requested_by=process_owner_id(),
            confirm=True,
        )
    except Exception:
        pass
    packet = _broker_truth_route_status(worker)
    packet["running"] = False
    packet["status"] = "STOPPED"
    return packet


def overlay_broker_truth_monitor_status(status: Mapping[str, Any]) -> dict[str, Any]:
    packet = dict(status)
    worker = worker_status(BROKER_TRUTH_KIND)
    packet["external_worker"] = worker
    if worker.get("running"):
        config = _mapping(worker.get("config"))
        latest_report = packet.get("latest_report")
        if not isinstance(latest_report, Mapping):
            latest_report = _load_broker_truth_latest_report()
        if isinstance(latest_report, Mapping):
            packet["latest_report"] = latest_report
            packet["monitor_status"] = latest_report.get("monitor_status", packet.get("monitor_status"))
            packet["ready_for_live"] = _broker_truth_report_ready_for_live(latest_report)
        packet["running"] = True
        packet["status"] = "RUNNING"
        packet["worker_isolated"] = True
        if _is_empty_status_value(packet.get("interval_seconds")):
            packet["interval_seconds"] = _int(config.get("interval_seconds"), 0) or packet.get("interval_seconds")
        if _is_empty_status_value(packet.get("cycles_run")):
            packet["cycles_run"] = _int(worker.get("cycles_run"), 0)
        if _is_empty_status_value(packet.get("started_at_iso")) and worker.get("started_at"):
            packet["started_at_iso"] = worker.get("started_at")
        packet["claim_boundary"] = (
            packet.get("claim_boundary")
            or "Broker-truth monitor is read-only. It does not place orders, "
            "close positions, deposit, withdraw, move bank/card money, automate "
            "payouts, create broker ACCEPT, or authorize live trading."
        )
    return packet


def start_proof_auto_runner_worker(*, check_interval_seconds: int) -> dict[str, Any]:
    if use_in_process_workers_for_tests():
        from cas_forex.proof_runner import start_runner

        return start_runner(check_interval_seconds)
    worker = _start_worker(
        PROOF_RUNNER_KIND,
        ["proof-auto-runner", "--check-interval-seconds", str(int(check_interval_seconds))],
        config={"check_interval_seconds": int(check_interval_seconds)},
    )
    return _proof_runner_route_status(worker)


def stop_proof_auto_runner_worker() -> dict[str, Any]:
    if use_in_process_workers_for_tests():
        from cas_forex.proof_runner import stop_runner

        return stop_runner()
    try:
        from cas_forex.proof_runner import stop_runner

        local_status = stop_runner(persist_desired=False)
    except Exception as exc:  # pragma: no cover - defensive status only
        local_status = {
            "report_kind": "cas_forex_proof_runner",
            "status": "STOP_ERROR",
            "running": False,
            "last_error": f"{type(exc).__name__}: {exc}",
        }
    worker = _stop_worker(PROOF_RUNNER_KIND)
    packet = dict(local_status)
    packet["running"] = False
    packet["status"] = "STOPPED"
    packet["external_worker"] = worker
    packet["worker_isolated"] = True
    return packet


def proof_auto_runner_worker_status() -> dict[str, Any]:
    if use_in_process_workers_for_tests():
        from cas_forex.proof_runner import runner_status

        return runner_status()
    return _proof_runner_route_status(worker_status(PROOF_RUNNER_KIND))


def broker_truth_worker_fast_status() -> dict[str, Any]:
    """Compact broker-truth status for hot dashboard polling.

    The fast route must not read the full broker-truth report because the worker
    may be replacing it while MT5/terminal reconciliation is active. This packet
    is intentionally fail-closed and uses only the tiny worker supervisor record.
    """
    worker = worker_status(BROKER_TRUTH_KIND)
    config = _mapping(worker.get("config"))
    running = bool(worker.get("running"))
    return {
        "report_kind": "cas_forex_broker_truth_monitor_status_fast",
        "running": running,
        "status": "RUNNING" if running else "STOPPED",
        "interval_seconds": _int(worker.get("interval_seconds"), _int(config.get("interval_seconds"), 0)) or None,
        "cycles_run": _int(worker.get("cycles_run"), 0),
        "last_error": worker.get("last_error"),
        "started_at_iso": worker.get("started_at"),
        "monitor_status": worker.get("monitor_status") or (
            "BROKER_TRUTH_MONITOR_RUNNING" if running else "BROKER_TRUTH_MONITOR_UNAVAILABLE"
        ),
        "ready_for_live": False,
        "latest_report": None,
        "external_worker": worker,
        "worker_isolated": running,
        "claim_boundary": (
            "Fast broker-truth worker status is observational and fail-closed. "
            "It does not place orders, close positions, deposit, withdraw, move "
            "bank/card money, automate payouts, create broker ACCEPT, or authorize "
            "live trading."
        ),
    }


def worker_status(kind: str) -> dict[str, Any]:
    state = _load_state()
    record = _record_for(state, kind)
    if not record:
        return {
            "kind": kind,
            "configured": False,
            "running": False,
            "pid": None,
            "state_path": str(STATE_PATH),
        }
    pid = _int(record.get("pid"), 0)
    alive = _pid_alive(pid)
    packet = dict(record)
    packet.update(
        {
            "kind": kind,
            "configured": True,
            "running": alive,
            "pid": pid if pid > 0 else None,
            "priority_class": _process_priority_class(pid) if alive else None,
            "state_path": str(STATE_PATH),
            "checked_at": utc_now().isoformat(),
        }
    )
    return packet


def _start_worker(kind: str, worker_args: list[str], *, config: Mapping[str, Any]) -> dict[str, Any]:
    current = worker_status(kind)
    if current.get("running"):
        if _worker_priority_mismatch(kind, current):
            _stop_worker(kind)
        else:
            return current

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{kind}-{utc_now().strftime('%Y%m%d-%H%M%S')}.log"
    command = [sys.executable, "-m", "cas_forex.waste_background_worker", *worker_args]
    env = os.environ.copy()
    env["CAS_FOREX_BACKGROUND_WORKER"] = kind
    if kind == RUNNER_KIND:
        env["CAS_FOREX_WASTE_SCHEDULED_SNAPSHOT_WATCH"] = "1"
    creationflags = _worker_creationflags(kind)
    with log_path.open("ab") as log:
        process = subprocess.Popen(
            command,
            cwd=str(REPO_ROOT),
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            creationflags=creationflags,
        )
    record = {
        "kind": kind,
        "pid": process.pid,
        "status": "STARTING",
        "started_at": utc_now().isoformat(),
        "config": dict(config),
        "command": command,
        "log_path": str(log_path),
    }
    _save_record(kind, record)
    time.sleep(0.2)
    return worker_status(kind)


def _worker_creationflags(kind: str) -> int:
    if os.name != "nt":
        return 0
    flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if kind == BROKER_TRUTH_KIND:
        flags |= int(
            getattr(
                subprocess,
                "IDLE_PRIORITY_CLASS",
                getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0),
            )
        )
    elif kind in {RUNNER_KIND, COLLECTOR_KIND, PROOF_RUNNER_KIND}:
        flags |= int(getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
    return flags


def _worker_expected_priority_class(kind: str) -> int | None:
    if os.name != "nt":
        return None
    if kind == BROKER_TRUTH_KIND:
        return int(
            getattr(
                subprocess,
                "IDLE_PRIORITY_CLASS",
                getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0),
            )
        )
    if kind in {RUNNER_KIND, COLLECTOR_KIND, PROOF_RUNNER_KIND}:
        return int(getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
    return None


def _worker_priority_mismatch(kind: str, worker: Mapping[str, Any]) -> bool:
    expected = _worker_expected_priority_class(kind)
    if not expected:
        return False
    actual = _int(worker.get("priority_class"), 0)
    return actual > 0 and actual != expected


def _process_priority_class(pid: int) -> int | None:
    if os.name != "nt" or pid <= 0:
        return None
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x0400, False, int(pid))
        if not handle:
            return None
        try:
            priority = kernel32.GetPriorityClass(handle)
            return int(priority) if priority else None
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return None


def _stop_worker(kind: str) -> dict[str, Any]:
    current = worker_status(kind)
    pid = _int(current.get("pid"), 0)
    if current.get("running") and pid > 0:
        _terminate_pid(pid)
        time.sleep(0.5)
    record = dict(current)
    record.update(
        {
            "running": _pid_alive(pid),
            "status": "STOPPED",
            "stopped_at": utc_now().isoformat(),
        }
    )
    _save_record(kind, record)
    return worker_status(kind)


def _runner_route_status(worker: Mapping[str, Any]) -> dict[str, Any]:
    config = worker.get("config") if isinstance(worker.get("config"), Mapping) else {}
    return {
        "report_kind": "cas_forex_waste_runner",
        "running": bool(worker.get("running")),
        "status": "RUNNING" if worker.get("running") else "START_FAILED",
        "interval_seconds": config.get("interval_seconds"),
        "cycles_run": None,
        "mode": "PAPER",
        "external_worker": dict(worker),
        "worker_isolated": True,
        "paper_execution_sink": {
            "configured": True,
            "claim_boundary": (
                "WASTE worker start only launches the isolated paper-safe timer. "
                "Order dispatch still requires a fresh edge PASS and the normal "
                "order_dispatch gates before any broker bridge can be touched."
            ),
        },
    }


def _collector_route_status(worker: Mapping[str, Any]) -> dict[str, Any]:
    config = worker.get("config") if isinstance(worker.get("config"), Mapping) else {}
    return {
        "report_kind": "cas_forex_waste_paper_sample_collector_scheduler",
        "running": bool(worker.get("running")),
        "status": (
            "WASTE_PAPER_SAMPLE_COLLECTOR_RUNNING"
            if worker.get("running")
            else "WASTE_PAPER_SAMPLE_COLLECTOR_START_FAILED"
        ),
        "interval_seconds": config.get("interval_seconds"),
        "cycles_run": None,
        "latest_collector_status": None,
        "paper_only": True,
        "read_only_market_actions_only": True,
        "external_worker": dict(worker),
        "worker_isolated": True,
        "claim_boundary": (
            "Paper sample collector worker start only launches an isolated "
            "paper/demo evidence timer. It does not authorize live trading, "
            "dispatch orders, deposit, withdraw, or move bank/card funds."
        ),
    }


def _broker_truth_route_status(worker: Mapping[str, Any]) -> dict[str, Any]:
    config = worker.get("config") if isinstance(worker.get("config"), Mapping) else {}
    return {
        "report_kind": "cas_forex_broker_truth_monitor_status",
        "running": bool(worker.get("running")),
        "status": "RUNNING" if worker.get("running") else "START_FAILED",
        "interval_seconds": config.get("interval_seconds"),
        "cycles_run": worker.get("cycles_run"),
        "last_error": worker.get("last_error"),
        "started_at_iso": worker.get("started_at"),
        "monitor_status": worker.get("monitor_status") or "BROKER_TRUTH_MONITOR_UNAVAILABLE",
        "ready_for_live": False,
        "latest_report": _load_broker_truth_latest_report(),
        "external_worker": dict(worker),
        "worker_isolated": True,
        "claim_boundary": (
            "Broker-truth monitor worker start only launches an isolated "
            "read-only reconciliation timer. It does not place orders, close "
            "positions, deposit, withdraw, move bank/card money, automate payouts, "
            "create broker ACCEPT, or authorize live trading."
        ),
    }


def _proof_runner_route_status(worker: Mapping[str, Any]) -> dict[str, Any]:
    config = worker.get("config") if isinstance(worker.get("config"), Mapping) else {}
    try:
        from cas_forex.proof_runner import (
            DEFAULT_CHECK_INTERVAL_SECONDS,
            control_state,
            runner_status,
        )

        control = control_state()
        local = runner_status()
    except Exception:
        DEFAULT_CHECK_INTERVAL_SECONDS = 1800
        control = {}
        local = {}
    running = bool(worker.get("running"))
    interval = _int(
        worker.get("check_interval_seconds"),
        _int(config.get("check_interval_seconds"), _int(control.get("check_interval_seconds"), 0)),
    )
    if interval <= 0:
        interval = _int(local.get("check_interval_seconds"), DEFAULT_CHECK_INTERVAL_SECONDS)
    return {
        "report_kind": "cas_forex_proof_runner",
        "running": running,
        "desired_running": bool(control.get("desired_running", running)),
        "status": "RUNNING" if running else "STOPPED",
        "durable_control_state_path": control.get("durable_control_state_path")
        or local.get("durable_control_state_path"),
        "check_interval_seconds": interval,
        "last_check_iso": worker.get("last_check_iso") or local.get("last_check_iso"),
        "last_run_iso": worker.get("last_run_iso") or local.get("last_run_iso"),
        "last_recorded_date": worker.get("last_recorded_date") or local.get("last_recorded_date"),
        "last_status": worker.get("last_status") or local.get("last_status"),
        "last_detail": worker.get("last_detail") or local.get("last_detail"),
        "last_error": worker.get("last_error") or local.get("last_error"),
        "days_recorded_this_session": _int(
            worker.get("days_recorded_this_session"),
            _int(local.get("days_recorded_this_session"), 0),
        ),
        "started_at_iso": worker.get("started_at_iso") or worker.get("started_at") or local.get("started_at_iso"),
        "note": (
            "Runs the paper proof auto-runner in an isolated worker so proof "
            "checks cannot block API health or dashboard polling."
        ),
        "external_worker": dict(worker),
        "worker_isolated": True,
        "claim_boundary": (
            "Proof auto-runner only records broker-verified paper proof days. "
            "It does not authorize live trading, broker ACCEPT, deposits, "
            "withdrawals, bank/card movement, payouts, or LICENSED status."
        ),
    }


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _save_record(kind: str, record: Mapping[str, Any]) -> None:
    state = _load_state()
    state[kind] = dict(record)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, indent=2, sort_keys=True, default=str)
    last_error: OSError | None = None
    for attempt in range(10):
        tmp = STATE_PATH.with_name(f"{STATE_PATH.name}.{os.getpid()}.{time.time_ns()}.tmp")
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(tmp, STATE_PATH)
            return
        except OSError as exc:
            last_error = exc
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            time.sleep(0.05 * (attempt + 1))
    if last_error is not None:
        return


def _record_for(state: Mapping[str, Any], kind: str) -> dict[str, Any] | None:
    record = state.get(kind)
    return dict(record) if isinstance(record, Mapping) else None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        return _windows_pid_alive(pid)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _windows_pid_alive(pid: int) -> bool:
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, int(pid))
        if not handle:
            return False
        exit_code = ctypes.c_ulong()
        try:
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == 259
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return False


def _terminate_pid(pid: int) -> None:
    if pid <= 0:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return _mapping(payload)


def _is_empty_status_value(value: Any) -> bool:
    return value is None or value == "" or value == 0 or value == []


def _load_broker_truth_latest_report() -> dict[str, Any] | None:
    try:
        from cas_forex.broker_truth_monitor import load_latest_broker_truth_monitor_report

        return load_latest_broker_truth_monitor_report()
    except Exception:
        return None


def _broker_truth_report_ready_for_live(report: Mapping[str, Any]) -> bool:
    try:
        from cas_forex.broker_truth_monitor import _report_ready_for_live

        return bool(_report_ready_for_live(report))
    except Exception:
        return False


def _run_runner(args: argparse.Namespace) -> int:
    from cas_forex.waste_runner import runner_status, start_runner, stop_runner

    status = start_runner(args.interval_seconds, confirm=bool(args.confirm))
    _save_record(
        RUNNER_KIND,
        {
            **worker_status(RUNNER_KIND),
            "pid": os.getpid(),
            "status": status.get("status"),
            "started_at": utc_now().isoformat(),
            "config": {"interval_seconds": args.interval_seconds, "confirm": bool(args.confirm)},
        },
    )
    try:
        while True:
            time.sleep(1.0)
            current = runner_status()
            if not current.get("running"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        stop_runner()
        record = worker_status(RUNNER_KIND)
        record["status"] = "STOPPED"
        record["running"] = False
        record["stopped_at"] = utc_now().isoformat()
        _save_record(RUNNER_KIND, record)
    return 0


def _run_collector(args: argparse.Namespace) -> int:
    from cas_forex.waste_paper_sample_collector import (
        start_waste_paper_sample_collector_scheduler,
        stop_waste_paper_sample_collector_scheduler,
        waste_paper_sample_collector_scheduler_status,
    )

    config = json.loads(args.config_json)
    status = start_waste_paper_sample_collector_scheduler(**config)
    _save_record(
        COLLECTOR_KIND,
        {
            **worker_status(COLLECTOR_KIND),
            "pid": os.getpid(),
            "status": status.get("status"),
            "started_at": utc_now().isoformat(),
            "config": config,
        },
    )
    try:
        while True:
            time.sleep(1.0)
            current = waste_paper_sample_collector_scheduler_status()
            if not current.get("running"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        stop_waste_paper_sample_collector_scheduler()
        record = worker_status(COLLECTOR_KIND)
        record["status"] = "STOPPED"
        record["running"] = False
        record["stopped_at"] = utc_now().isoformat()
        _save_record(COLLECTOR_KIND, record)
    return 0


def _run_broker_truth_monitor(args: argparse.Namespace) -> int:
    from cas_forex.broker_truth_monitor import monitor_status, start_monitor, stop_monitor

    status = start_monitor(args.interval_seconds)
    _save_record(
        BROKER_TRUTH_KIND,
        {
            **worker_status(BROKER_TRUTH_KIND),
            "pid": os.getpid(),
            "status": status.get("status"),
            "started_at": utc_now().isoformat(),
            "config": {"interval_seconds": args.interval_seconds},
            "cycles_run": status.get("cycles_run", 0),
            "monitor_status": status.get("monitor_status"),
            "last_error": status.get("last_error"),
        },
    )
    try:
        while True:
            time.sleep(1.0)
            current = monitor_status()
            record = worker_status(BROKER_TRUTH_KIND)
            record["pid"] = os.getpid()
            record["running"] = bool(current.get("running"))
            record["status"] = current.get("status")
            record["cycles_run"] = current.get("cycles_run")
            record["monitor_status"] = current.get("monitor_status")
            record["last_error"] = current.get("last_error")
            record["interval_seconds"] = current.get("interval_seconds")
            record["started_at"] = current.get("started_at_iso") or record.get("started_at")
            record["config"] = {"interval_seconds": args.interval_seconds}
            _save_record(BROKER_TRUTH_KIND, record)
            if not current.get("running"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        stop_monitor()
        record = worker_status(BROKER_TRUTH_KIND)
        record["status"] = "STOPPED"
        record["running"] = False
        record["stopped_at"] = utc_now().isoformat()
        _save_record(BROKER_TRUTH_KIND, record)
    return 0


def _run_proof_auto_runner(args: argparse.Namespace) -> int:
    from cas_forex.proof_runner import runner_status, start_runner, stop_runner

    status = start_runner(args.check_interval_seconds, persist_desired=False)
    _save_record(
        PROOF_RUNNER_KIND,
        {
            **worker_status(PROOF_RUNNER_KIND),
            "pid": os.getpid(),
            "status": status.get("status") or ("RUNNING" if status.get("running") else "STOPPED"),
            "started_at": utc_now().isoformat(),
            "config": {"check_interval_seconds": args.check_interval_seconds},
            "check_interval_seconds": status.get("check_interval_seconds"),
            "last_check_iso": status.get("last_check_iso"),
            "last_run_iso": status.get("last_run_iso"),
            "last_recorded_date": status.get("last_recorded_date"),
            "last_status": status.get("last_status"),
            "last_detail": status.get("last_detail"),
            "last_error": status.get("last_error"),
            "days_recorded_this_session": status.get("days_recorded_this_session"),
        },
    )
    try:
        while True:
            time.sleep(1.0)
            current = runner_status()
            record = worker_status(PROOF_RUNNER_KIND)
            record["pid"] = os.getpid()
            record["running"] = bool(current.get("running"))
            record["status"] = "RUNNING" if current.get("running") else "STOPPED"
            record["check_interval_seconds"] = current.get("check_interval_seconds")
            record["last_check_iso"] = current.get("last_check_iso")
            record["last_run_iso"] = current.get("last_run_iso")
            record["last_recorded_date"] = current.get("last_recorded_date")
            record["last_status"] = current.get("last_status")
            record["last_detail"] = current.get("last_detail")
            record["last_error"] = current.get("last_error")
            record["days_recorded_this_session"] = current.get("days_recorded_this_session")
            record["started_at"] = current.get("started_at_iso") or record.get("started_at")
            record["config"] = {"check_interval_seconds": args.check_interval_seconds}
            _save_record(PROOF_RUNNER_KIND, record)
            if not current.get("running"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        stop_runner(persist_desired=False)
        record = worker_status(PROOF_RUNNER_KIND)
        record["status"] = "STOPPED"
        record["running"] = False
        record["stopped_at"] = utc_now().isoformat()
        _save_record(PROOF_RUNNER_KIND, record)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CAS Forex WASTE background worker")
    sub = parser.add_subparsers(dest="command", required=True)
    runner = sub.add_parser("runner")
    runner.add_argument("--interval-seconds", type=int, required=True)
    runner.add_argument("--confirm", action="store_true")
    collector = sub.add_parser("collector")
    collector.add_argument("--config-json", required=True)
    broker_truth = sub.add_parser("broker-truth-monitor")
    broker_truth.add_argument("--interval-seconds", type=int, required=True)
    proof = sub.add_parser("proof-auto-runner")
    proof.add_argument("--check-interval-seconds", type=int, required=True)
    args = parser.parse_args(argv)
    if args.command == "runner":
        return _run_runner(args)
    if args.command == "collector":
        return _run_collector(args)
    if args.command == "broker-truth-monitor":
        return _run_broker_truth_monitor(args)
    if args.command == "proof-auto-runner":
        return _run_proof_auto_runner(args)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
