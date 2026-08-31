"""watchdog_main.py -- the SEPARATE watchdog process (GATE 1A.2 section 9).

Runs beside the campaign driver (started by infra/bootstrap.sh). Polls the
heartbeat; on staleness beyond the limit it requests termination itself, so an
abandoned campaign is terminated even if the driver never reaches `finally`.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exec.watchdog import Watchdog                      # noqa: E402
from exec.shutdown import ShutdownPath                  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--heartbeat", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--stale-limit-seconds", type=float, default=2.5 * 3600)
    ap.add_argument("--poll-seconds", type=float, default=60.0)
    ap.add_argument("--mode", required=True,
                    choices=["REAL", "SYNTHETIC_CONFORMANCE"])
    args = ap.parse_args()
    wd = Watchdog(Path(args.heartbeat), Path(args.evidence),
                  args.stale_limit_seconds)
    shutdown = ShutdownPath(args.mode, Path(args.evidence))
    while True:
        if not wd.poll_once(time.time()):
            shutdown.request_termination("WATCHDOG_STALE_HEARTBEAT")
            return 1
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
