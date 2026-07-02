"""Durable process-ownership lease for the WASTE runner.

The WASTE runner is a timed loop that can eventually place live orders after all
owner gates and edge/risk gates pass. In a multi-worker API, a process-local
"global runner" is not enough: two workers could each believe they own the loop.

This module keeps a small durable lease under ``runtime/``. It does not start
threads, place orders, authorize live trading, mint edge tokens, or move money.
It only records which process is allowed to own the timed WASTE runner and lets
other workers request a stop that the owner observes on its next heartbeat.
"""

from __future__ import annotations

import contextlib
import json
import os
import socket
import uuid
from pathlib import Path
from typing import Any, Iterator, Mapping

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "waste-runner-supervisor.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "waste-runner-supervisor-audit.jsonl"
DEFAULT_LEASE_SECONDS = 180

REPORT_KIND = "cas_forex_waste_runner_supervisor"
STATUS_LEASE_ACQUIRED = "LEASE_ACQUIRED"
STATUS_LEASE_RENEWED = "LEASE_RENEWED"
STATUS_STOP_REQUESTED = "STOP_REQUESTED"
STATUS_LEASE_RELEASED = "LEASE_RELEASED"
STATUS_RECOVERY_CLEARED = "RECOVERY_CLEARED"
STATUS_RECOVERY_REFUSED = "RECOVERY_REFUSED"
STATUS_SUPERVISOR_CONFLICT = "SUPERVISOR_CONFLICT"

CLAIM_BOUNDARY = (
    "WASTE runner supervisor records durable loop ownership so multiple API "
    "workers cannot all claim the timed trading loop. It does not authorize live "
    "trading, mint edge tokens, place orders, deposit, withdraw, transfer funds, "
    "or override owner gates."
)

_PROCESS_OWNER_ID = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:12]}"


class WasteRunnerSupervisorConflict(RuntimeError):
    """Raised when another fresh owner already holds the WASTE runner lease."""

    def __init__(self, lease: Mapping[str, Any]) -> None:
        self.lease = dict(lease)
        super().__init__(
            f"WASTE runner lease is held by {lease.get('owner_id')} until {lease.get('expires_at')}"
        )


class WasteRunnerSupervisorStore:
    def __init__(
        self,
        state_path: Path | str = DEFAULT_STATE_PATH,
        audit_path: Path | str = DEFAULT_AUDIT_PATH,
        *,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> None:
        self.state_path = Path(state_path)
        self.audit_path = Path(audit_path)
        self.lock_path = self.state_path.with_suffix(self.state_path.suffix + ".lock")
        self.lease_seconds = max(0, int(lease_seconds))

    def acquire(
        self,
        *,
        owner_id: str,
        interval_seconds: int,
        mode: str,
    ) -> dict[str, Any]:
        owner = _clean_owner(owner_id)
        now = utc_now()
        with self._locked_payload() as payload:
            lease = _lease(payload)
            if lease and _lease_active(lease, now) and lease.get("owner_id") != owner:
                self._audit_locked(STATUS_SUPERVISOR_CONFLICT, {"requested_owner_id": owner, "active_lease": lease})
                raise WasteRunnerSupervisorConflict(lease)
            record = self._lease_record(
                owner_id=owner,
                status=STATUS_LEASE_ACQUIRED,
                interval_seconds=interval_seconds,
                mode=mode,
                now=now,
                previous_lease=lease,
            )
            payload.update(
                {
                    "report_kind": REPORT_KIND,
                    "updated_at": now.isoformat(),
                    "desired_running": True,
                    "lease": record,
                    "stop_requested_at": None,
                    "stop_requested_by": None,
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
            self._save_payload(payload)
            self._audit_locked(STATUS_LEASE_ACQUIRED, record)
            return dict(record)

    def renew(
        self,
        *,
        owner_id: str,
        interval_seconds: int,
        mode: str,
    ) -> tuple[bool, dict[str, Any]]:
        owner = _clean_owner(owner_id)
        now = utc_now()
        with self._locked_payload() as payload:
            lease = _lease(payload)
            if lease and lease.get("owner_id") != owner and _lease_active(lease, now):
                return False, self.build_status(owner_id=owner, local_running=True)
            record = self._lease_record(
                owner_id=owner,
                status=STATUS_LEASE_RENEWED,
                interval_seconds=interval_seconds,
                mode=mode,
                now=now,
                previous_lease=lease,
            )
            payload.update(
                {
                    "report_kind": REPORT_KIND,
                    "updated_at": now.isoformat(),
                    "desired_running": True,
                    "lease": record,
                    "stop_requested_at": None,
                    "stop_requested_by": None,
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
            self._save_payload(payload)
            self._audit_locked(STATUS_LEASE_RENEWED, record)
            return True, dict(record)

    def request_stop(self, *, requested_by: str) -> dict[str, Any]:
        requester = _clean_owner(requested_by)
        now = utc_now()
        with self._locked_payload() as payload:
            lease = _lease(payload)
            payload.update(
                {
                    "report_kind": REPORT_KIND,
                    "updated_at": now.isoformat(),
                    "desired_running": False,
                    "stop_requested_at": now.isoformat(),
                    "stop_requested_by": requester,
                    "lease": lease,
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
            self._save_payload(payload)
            record = {
                "status": STATUS_STOP_REQUESTED,
                "requested_by": requester,
                "active_lease": lease,
                "timestamp": now.isoformat(),
            }
            self._audit_locked(STATUS_STOP_REQUESTED, record)
            return self.build_status(owner_id=requester, local_running=False)

    def release(self, *, owner_id: str) -> dict[str, Any]:
        owner = _clean_owner(owner_id)
        now = utc_now()
        with self._locked_payload() as payload:
            lease = _lease(payload)
            if lease and lease.get("owner_id") == owner:
                payload.update(
                    {
                        "report_kind": REPORT_KIND,
                        "updated_at": now.isoformat(),
                        "desired_running": False,
                        "lease": None,
                        "released_at": now.isoformat(),
                        "released_by": owner,
                        "claim_boundary": CLAIM_BOUNDARY,
                    }
                )
                self._save_payload(payload)
                self._audit_locked(
                    STATUS_LEASE_RELEASED,
                    {"owner_id": owner, "released_at": now.isoformat(), "previous_lease": lease},
                )
            return self.build_status(owner_id=owner, local_running=False)

    def recover_stale_or_requested(self, *, requested_by: str, confirm: bool = False) -> dict[str, Any]:
        """Clear a stale or stop-requested lease after explicit owner confirmation.

        A fresh active lease with desired_running=True is refused; the owner should
        use stop first and let the owning runner halt. This method does not stop a
        process or authorize a new runner. It only clears durable supervisor state
        that is already stale or explicitly stop-requested.
        """
        requester = _clean_owner(requested_by)
        now = utc_now()
        with self._locked_payload() as payload:
            lease = _lease(payload)
            active_fresh = bool(lease and _lease_active(lease, now))
            stop_requested = bool(payload.get("desired_running") is False and lease)
            can_clear = bool(lease) and (stop_requested or not active_fresh)
            if not confirm:
                record = {
                    "status": "CONFIRM_REQUIRED",
                    "requested_by": requester,
                    "active_lease": lease,
                    "can_clear": can_clear,
                    "reason": "confirm=true is required before clearing a WASTE runner supervisor lease.",
                    "timestamp": now.isoformat(),
                }
                self._audit_locked(STATUS_RECOVERY_REFUSED, record)
                status = self.build_status(owner_id=requester, local_running=False)
                status["status"] = "CONFIRM_REQUIRED"
                status["recovery"] = record
                return status
            if not can_clear:
                reason = (
                    "Fresh active WASTE runner lease is still desired-running; request stop first."
                    if active_fresh and lease
                    else "No stale or stop-requested WASTE runner lease is present."
                )
                record = {
                    "status": STATUS_RECOVERY_REFUSED,
                    "requested_by": requester,
                    "active_lease": lease,
                    "can_clear": False,
                    "reason": reason,
                    "timestamp": now.isoformat(),
                }
                self._audit_locked(STATUS_RECOVERY_REFUSED, record)
                status = self.build_status(owner_id=requester, local_running=False)
                status["status"] = STATUS_RECOVERY_REFUSED
                status["recovery"] = record
                return status

            record = {
                "status": STATUS_RECOVERY_CLEARED,
                "requested_by": requester,
                "cleared_at": now.isoformat(),
                "cleared_lease": lease,
                "reason": "Cleared stale or stop-requested WASTE runner supervisor lease.",
            }
            payload.update(
                {
                    "report_kind": REPORT_KIND,
                    "updated_at": now.isoformat(),
                    "desired_running": False,
                    "lease": None,
                    "recovered_at": now.isoformat(),
                    "recovered_by": requester,
                    "recovery_reason": record["reason"],
                    "stop_requested_at": payload.get("stop_requested_at"),
                    "stop_requested_by": payload.get("stop_requested_by"),
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
            self._save_payload(payload)
            self._audit_locked(STATUS_RECOVERY_CLEARED, record)
            status = self.build_status(owner_id=requester, local_running=False)
            status["status"] = STATUS_RECOVERY_CLEARED
            status["recovery"] = record
            return status

    def should_stop(self, *, owner_id: str) -> bool:
        owner = _clean_owner(owner_id)
        payload = self._load_payload()
        lease = _lease(payload)
        if payload.get("desired_running") is False:
            return True
        if lease and lease.get("owner_id") != owner and _lease_active(lease, utc_now()):
            return True
        return False

    def build_status(self, *, owner_id: str | None = None, local_running: bool = False) -> dict[str, Any]:
        payload = self._load_payload()
        lease = _lease(payload)
        now = utc_now()
        active_fresh = bool(lease and _lease_active(lease, now))
        owner = _clean_owner(owner_id) if owner_id else process_owner_id()
        owned_by_this_process = bool(active_fresh and lease and lease.get("owner_id") == owner)
        return {
            "report_kind": REPORT_KIND,
            "generated_at": now.isoformat(),
            "desired_running": bool(payload.get("desired_running", False)),
            "active_lease": lease,
            "active_lease_is_fresh": active_fresh,
            "owned_by_this_process": owned_by_this_process,
            "local_owner_id": owner,
            "local_running": bool(local_running),
            "stop_requested_at": payload.get("stop_requested_at"),
            "stop_requested_by": payload.get("stop_requested_by"),
            "state_path": str(self.state_path),
            "audit_path": str(self.audit_path),
            "claim_boundary": CLAIM_BOUNDARY,
            "next_action": _next_action(payload, lease, active_fresh, owned_by_this_process),
        }

    def _lease_record(
        self,
        *,
        owner_id: str,
        status: str,
        interval_seconds: int,
        mode: str,
        now: Any,
        previous_lease: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "lease_id": stable_ledger_id("waste-runner-lease", owner_id, str(now.timestamp())),
            "owner_id": owner_id,
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "status": status,
            "mode": str(mode or "PAPER").upper(),
            "interval_seconds": int(interval_seconds),
            "acquired_at": (previous_lease or {}).get("acquired_at") or now.isoformat(),
            "last_heartbeat_at": now.isoformat(),
            "expires_at": _expires_at(now, self.lease_seconds).isoformat(),
            "lease_seconds": self.lease_seconds,
            "claim_boundary": CLAIM_BOUNDARY,
        }

    @contextlib.contextmanager
    def _locked_payload(self) -> Iterator[dict[str, Any]]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            _lock_file(handle)
            try:
                yield self._load_payload()
            finally:
                _unlock_file(handle)

    def _load_payload(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {
                "report_kind": REPORT_KIND,
                "desired_running": False,
                "lease": None,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {
                "report_kind": REPORT_KIND,
                "desired_running": False,
                "lease": None,
                "claim_boundary": CLAIM_BOUNDARY,
                "state_unreadable": True,
            }
        return dict(payload) if isinstance(payload, Mapping) else {}

    def _save_payload(self, payload: Mapping[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")
        tmp.replace(self.state_path)

    def _audit_locked(self, action: str, payload: Mapping[str, Any]) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "audit_id": stable_ledger_id(
                "waste-runner-supervisor-audit",
                action,
                utc_now().isoformat(),
                json.dumps(payload, sort_keys=True, default=str),
            ),
            "action": action,
            "timestamp": utc_now().isoformat(),
            "payload": dict(payload),
        }
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")


def process_owner_id() -> str:
    return _PROCESS_OWNER_ID


def default_waste_runner_supervisor_store() -> WasteRunnerSupervisorStore:
    return WasteRunnerSupervisorStore(DEFAULT_STATE_PATH, DEFAULT_AUDIT_PATH)


def build_waste_runner_supervisor_status() -> dict[str, Any]:
    return default_waste_runner_supervisor_store().build_status()


def _lease(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    lease = payload.get("lease") if isinstance(payload, Mapping) else None
    return dict(lease) if isinstance(lease, Mapping) else None


def _lease_expired(lease: Mapping[str, Any], now: Any) -> bool:
    expires = lease.get("expires_at")
    if not expires:
        return True
    try:
        from datetime import datetime

        expires_at = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
        return expires_at <= now
    except Exception:
        return True


def _lease_active(lease: Mapping[str, Any], now: Any) -> bool:
    return not _lease_expired(lease, now) and _process_is_alive(lease.get("pid"))


def _process_is_alive(raw_pid: Any) -> bool:
    try:
        pid = int(raw_pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        try:
            import ctypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                return False
            try:
                code = ctypes.c_ulong()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return True
                return code.value == 259  # STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _expires_at(now: Any, lease_seconds: int) -> Any:
    from datetime import timedelta

    return now + timedelta(seconds=max(0, int(lease_seconds)))


def _clean_owner(owner_id: str) -> str:
    owner = str(owner_id or "").strip()
    if not owner:
        raise ValueError("owner_id is required for WASTE runner supervisor lease")
    return owner


def _next_action(
    payload: Mapping[str, Any],
    lease: Mapping[str, Any] | None,
    active_fresh: bool,
    owned_by_this_process: bool,
) -> str:
    if payload.get("desired_running") is False and lease and active_fresh:
        return "Stop has been requested; the owning WASTE runner should halt on its next supervisor check."
    if active_fresh and owned_by_this_process:
        return "This process owns the WASTE runner lease; keep renewing while the timed loop runs."
    if active_fresh:
        return "Another process owns the WASTE runner lease; do not start a duplicate timed loop."
    if lease:
        return "The previous WASTE runner lease is stale; a new owner may acquire it before starting."
    return "No WASTE runner lease is active."


def _lock_file(handle: Any) -> None:
    try:
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
    except ImportError:  # pragma: no cover - non-Windows fallback
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _unlock_file(handle: Any) -> None:
    try:
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    except ImportError:  # pragma: no cover - non-Windows fallback
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
