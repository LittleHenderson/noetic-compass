"""watchdog.py -- termination must not depend on the training process reaching
`finally` (GATE 1A.2 section 9 + 1A.2R section 3).

The driver writes a heartbeat file with REAL epoch time every step; this SEPARATE
process polls it. Fixes (audit): (1) it does NOT terminate before the first
heartbeat exists -- a startup grace covers the window between watchdog launch and
the driver's first beat; (2) the heartbeat clock domain is REAL epoch on both
sides (the driver's REAL clock is time.time); (3) the stale limit is the SIGNED
per-job cap, read from watchdog_config.json (written by the driver after the
execution approval is verified), not a hardcoded constant.
"""
from __future__ import annotations

import json
from pathlib import Path


class Watchdog:
    def __init__(self, heartbeat_path: Path, evidence_dir: Path,
                 stale_limit_seconds: float, startup_grace_seconds: float = 300.0,
                 launched_at: float = None):
        self.heartbeat_path = Path(heartbeat_path)
        self.evidence_dir = Path(evidence_dir)
        self.stale_limit_seconds = float(stale_limit_seconds)
        self.startup_grace_seconds = float(startup_grace_seconds)
        self._launched_at = launched_at
        self._seen_heartbeat = False
        self.terminated = False

    def beat(self, now: float) -> None:
        self.heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
        with self.heartbeat_path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"t": now}) + "\n")

    def poll_once(self, now: float) -> bool:
        """True if the campaign is alive; on staleness, request termination.
        Before the first heartbeat is seen, staleness fires ONLY after the
        startup grace elapses (audit fix: no immediate pre-heartbeat kill)."""
        if self._launched_at is None:
            self._launched_at = now
        try:
            last = json.loads(
                self.heartbeat_path.read_text(encoding="utf-8"))["t"]
            self._seen_heartbeat = True
        except (OSError, ValueError, KeyError):
            last = None
        if last is None:
            # no heartbeat yet: alive until the startup grace elapses
            if (now - self._launched_at) <= self.startup_grace_seconds:
                return True
            reason, detail = "WATCHDOG_NO_HEARTBEAT_AFTER_GRACE", None
        elif (now - last) <= self.stale_limit_seconds:
            return True
        else:
            reason, detail = "WATCHDOG_STALE_HEARTBEAT", last
        marker = self.evidence_dir / "WATCHDOG_TERMINATION.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        with marker.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"reason": reason, "last_beat": detail, "now": now,
                                 "stale_limit_seconds": self.stale_limit_seconds},
                                indent=2) + "\n")
        self.terminated = True
        return False
