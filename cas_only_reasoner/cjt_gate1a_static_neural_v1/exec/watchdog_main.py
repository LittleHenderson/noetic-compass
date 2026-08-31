"""watchdog_main.py -- the SEPARATE watchdog process (GATE 1A.2 s.9 + 1A.2R s.3).

Runs beside the campaign driver (started by infra/bootstrap.sh). Polls the
heartbeat on the REAL epoch clock; does NOT terminate before the first heartbeat
during a startup grace; reads the SIGNED per-job cap from watchdog_config.json
(written by the driver after the execution approval verifies) as its stale
limit; and on staleness both requests EC2 termination AND durably marks the
protected campaign burned (if a protected lock is active) so no protected token
is left RUNNING behind an abandoned instance.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exec.watchdog import Watchdog                      # noqa: E402
from exec.shutdown import ShutdownPath                  # noqa: E402


def _read_signed_cap(config_path: Path, default: float) -> float:
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        return float(cfg["stale_limit_seconds"])
    except (OSError, ValueError, KeyError):
        return default


def _burn_abandoned_protected(config_path: Path):
    """If the driver recorded an active AWS protected lock, mark it burned."""
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        lock = cfg.get("aws_protected_lock")
        if not lock:
            return
        from exec.protected_lock import AwsProtectedLock, ProtectedLockViolation
        awl = AwsProtectedLock(lock["table_name"], lock["region"])
        if awl.state(lock["campaign_id"]) == "PROTECTED_RUNNING":
            try:
                awl.burn(lock["campaign_id"],
                         final_state_reason="WATCHDOG_ABANDONED",
                         result_or_failure_sha256="0" * 64)
            except ProtectedLockViolation:
                pass
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--heartbeat", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--config", default=None,
                    help="watchdog_config.json (signed cap + protected lock)")
    ap.add_argument("--startup-grace-seconds", type=float, default=300.0)
    ap.add_argument("--poll-seconds", type=float, default=60.0)
    ap.add_argument("--mode", required=True,
                    choices=["REAL", "SYNTHETIC_CONFORMANCE"])
    args = ap.parse_args()
    config_path = Path(args.config) if args.config \
        else Path(args.evidence) / "watchdog_config.json"
    shutdown = ShutdownPath(args.mode, Path(args.evidence))
    launched_at = time.time()
    while True:
        stale = _read_signed_cap(config_path, default=2.5 * 3600)
        wd = Watchdog(Path(args.heartbeat), Path(args.evidence), stale,
                      startup_grace_seconds=args.startup_grace_seconds,
                      launched_at=launched_at)
        if not wd.poll_once(time.time()):
            _burn_abandoned_protected(config_path)
            shutdown.request_termination("WATCHDOG_TERMINATION")
            return 1
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
