"""Single-owner process topology for CAS Forex autonomous runtime state."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, BinaryIO

from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OWNER_LOCK_PATH = REPO_ROOT / "runtime" / "api-runtime-owner.lock"
DEFAULT_STATUS_PATH = REPO_ROOT / "runtime" / "api-runtime-topology.json"
REPORT_KIND = "cas_forex_runtime_topology"
SUPPORTED_API_WORKERS = 1

PROCESS_LOCAL_COMPONENTS = (
    "ai_operator_runner",
    "dispatch_loop",
    "proof_auto_runner",
    "dashboard_cache",
    "route_cache",
    "mt5_terminal_ipc_cache",
)

CLAIM_BOUNDARY = (
    "CAS Forex currently supports one stateful API owner process. LAN and phone "
    "clients may share that process. A second API process and multiple Uvicorn "
    "workers are refused because autonomous loops and hot caches are process-local; "
    "pretending otherwise can duplicate actions or return contradictory state."
)


class RuntimeTopologyError(ValueError):
    pass


_guard = threading.RLock()
_owner_handle: BinaryIO | None = None
_owner_lock_path: Path | None = None


def validate_api_worker_count(workers: int) -> int:
    count = int(workers)
    if count != SUPPORTED_API_WORKERS:
        raise RuntimeTopologyError(
            "CAS Forex requires exactly one stateful API worker. LAN/mobile clients "
            "do not require extra API workers. Use --workers 1; scale only after "
            "Operator/dispatch/control state is moved to a shared external runtime."
        )
    return count


def acquire_runtime_owner(
    lock_path: Path | str = DEFAULT_OWNER_LOCK_PATH,
) -> bool:
    global _owner_handle, _owner_lock_path
    path = Path(lock_path)
    with _guard:
        if _owner_handle is not None:
            return True
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("a+b")
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        try:
            _lock_nonblocking(handle)
        except OSError:
            handle.close()
            return False
        payload = {
            "pid": os.getpid(),
            "acquired_at": utc_now().isoformat(),
        }
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps(payload, sort_keys=True).encode("utf-8"))
        handle.flush()
        _owner_handle = handle
        _owner_lock_path = path
        return True


def require_runtime_owner(
    lock_path: Path | str = DEFAULT_OWNER_LOCK_PATH,
) -> None:
    if acquire_runtime_owner(lock_path):
        return
    raise RuntimeTopologyError(
        "Another CAS Forex API process already owns the autonomous runtime. "
        "This process is refusing startup so it cannot expose a contradictory "
        "control plane or duplicate Operator, dispatch, or proof-loop actions."
    )


def release_runtime_owner() -> None:
    global _owner_handle, _owner_lock_path
    with _guard:
        handle = _owner_handle
        _owner_handle = None
        _owner_lock_path = None
    if handle is None:
        return
    try:
        _unlock(handle)
    finally:
        handle.close()


def is_runtime_owner() -> bool:
    with _guard:
        return _owner_handle is not None


def build_runtime_topology_status(
    *,
    worker_count: int | None = None,
    host: str | None = None,
    port: int | None = None,
    lifecycle: str = "RUNNING",
) -> dict[str, Any]:
    workers = _resolved_worker_count(worker_count)
    owner = is_runtime_owner()
    supported = workers == SUPPORTED_API_WORKERS
    ready = supported and owner and lifecycle.upper() == "RUNNING"
    if lifecycle.upper() == "STOPPED":
        status = "STOPPED"
    elif not supported:
        status = "UNSUPPORTED_MULTI_WORKER"
    elif owner:
        status = "SINGLE_OWNER_READY"
    else:
        status = "RUNTIME_OWNER_UNAVAILABLE"
    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "claim_status": "ACCEPT" if ready else "FLAG_FOR_HUMAN_REVIEW",
        "lifecycle": lifecycle.upper(),
        "api_worker_count": workers,
        "supported_api_worker_count": SUPPORTED_API_WORKERS,
        "runtime_owner": owner,
        "runtime_owner_pid": os.getpid() if owner else None,
        "process_pid": os.getpid(),
        "host": host or os.environ.get("CAS_FOREX_API_HOST") or None,
        "port": port or _optional_int(os.environ.get("CAS_FOREX_API_PORT")),
        "event_loop_policy": os.environ.get("CAS_FOREX_API_EVENT_LOOP") or "unavailable",
        "owner_lock_path": str(_owner_lock_path or DEFAULT_OWNER_LOCK_PATH),
        "process_local_components": list(PROCESS_LOCAL_COMPONENTS),
        "stateful_control_plane_enabled": ready,
        "lan_phone_supported": supported,
        "multi_worker_supported": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": (
            "Runtime topology is coherent: one API process owns autonomous state."
            if ready
            else "Stop duplicate API processes and relaunch with scripts/run_api_server.py --workers 1."
        ),
    }


def write_runtime_topology_status(
    *,
    status_path: Path | str = DEFAULT_STATUS_PATH,
    worker_count: int | None = None,
    host: str | None = None,
    port: int | None = None,
    lifecycle: str = "RUNNING",
) -> dict[str, Any]:
    packet = build_runtime_topology_status(
        worker_count=worker_count,
        host=host,
        port=port,
        lifecycle=lifecycle,
    )
    path = Path(status_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
    return packet


def load_runtime_topology_status(
    status_path: Path | str = DEFAULT_STATUS_PATH,
) -> dict[str, Any]:
    path = Path(status_path)
    if not path.exists():
        return build_runtime_topology_status()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return build_runtime_topology_status()
    return dict(payload) if isinstance(payload, dict) else build_runtime_topology_status()


def _resolved_worker_count(value: int | None) -> int:
    if value is not None:
        return int(value)
    raw = os.environ.get("CAS_FOREX_API_EFFECTIVE_WORKERS") or "1"
    try:
        return int(raw)
    except ValueError:
        return 0


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _lock_nonblocking(handle: BinaryIO) -> None:
    try:
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except ImportError:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(handle: BinaryIO) -> None:
    try:
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    except ImportError:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
