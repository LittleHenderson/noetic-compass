"""watchdog_main.py -- the SEPARATE watchdog process (GATE 1A.2 s.9 + 1A.2R s.3
+ 1A.2R.2A + 1A.2R.2B).

Runs beside the campaign driver (started by infra/bootstrap.sh). Polls the
heartbeat on the REAL epoch clock; does NOT terminate before the first heartbeat
during a startup grace; derives its stale limit from the SIGNED per-job cap in
watchdog_config.json (the config authority, exec/watchdog_config.py); and on
staleness both requests EC2 termination AND durably marks the protected campaign
burned (if a protected lock is active).

FAIL-CLOSED TOTALITY (1A.2R.2B): the configuration read+validation happens
INSIDE the emergency boundary, so a malformed configuration envelope (array,
null, scalar, wrong keys, list-valued limit, NaN/infinity) can never cause the
watchdog to exit before requesting termination. In REAL mode there is NO
unsigned default -- a missing/malformed config fails closed. Every ordinary
configuration or poll failure produces a marker + termination request + nonzero
exit; the watchdog process never disappears silently.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exec.watchdog import Watchdog                      # noqa: E402
from exec.watchdog_config import load_config, stale_limit_of  # noqa: E402
from exec.shutdown import ShutdownPath                  # noqa: E402


def _write_termination_marker(evidence_dir: Path, reason: str, detail=None) -> None:
    marker = evidence_dir / "WATCHDOG_TERMINATION.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    payload = {"reason": reason}
    if detail is not None:
        payload["detail"] = detail
    with marker.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(payload, indent=2) + "\n")


def _burn_abandoned_protected(config: dict):
    """If the config records an active AWS protected lock, mark it burned."""
    try:
        lock = config.get("aws_protected_lock") if isinstance(config, dict) else None
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
    evidence = Path(args.evidence)
    shutdown = ShutdownPath(args.mode, evidence)
    launched_at = time.time()
    while True:
        # THE ENTIRE loop body -- config read+validation AND the poll -- is inside
        # the fail-closed boundary (1A.2R.2B): nothing runs before the try.
        config = None
        try:
            config = load_config(config_path, args.mode)   # REAL: no default
            stale = stale_limit_of(config)
            wd = Watchdog(Path(args.heartbeat), evidence, stale,
                          startup_grace_seconds=args.startup_grace_seconds,
                          launched_at=launched_at)
            alive = wd.poll_once(time.time())
        except Exception as exc:                        # noqa: BLE001
            _write_termination_marker(evidence, "WATCHDOG_INTERNAL_ERROR",
                                      type(exc).__name__)
            _burn_abandoned_protected(config)
            shutdown.request_termination("WATCHDOG_INTERNAL_ERROR")
            return 2
        if not alive:
            _burn_abandoned_protected(config)
            shutdown.request_termination("WATCHDOG_TERMINATION")
            return 1
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
