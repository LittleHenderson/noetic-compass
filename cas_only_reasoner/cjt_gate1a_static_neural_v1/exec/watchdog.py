"""watchdog.py -- termination must not depend on the training process reaching
`finally` (GATE 1A.2 section 9).

The driver writes a heartbeat file every step; this SEPARATE process polls it.
If the heartbeat goes stale past the signed per-job cap (plus grace), or the
campaign exceeds its signed wall-clock ceiling, the watchdog itself requests
termination through the registered shutdown path and records
WATCHDOG_TERMINATION.json. Synthetic conformance drives poll_once() directly
with a fake clock to prove the abandoned-campaign path fires.
"""
from __future__ import annotations

import json
from pathlib import Path


class Watchdog:
    def __init__(self, heartbeat_path: Path, evidence_dir: Path,
                 stale_limit_seconds: float, clock=None):
        self.heartbeat_path = Path(heartbeat_path)
        self.evidence_dir = Path(evidence_dir)
        self.stale_limit_seconds = float(stale_limit_seconds)
        self._clock = clock                     # injectable for conformance
        self.terminated = False

    def beat(self, now: float) -> None:
        self.heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
        with self.heartbeat_path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"t": now}) + "\n")

    def poll_once(self, now: float) -> bool:
        """True if the campaign is alive; on staleness, request termination."""
        try:
            last = json.loads(
                self.heartbeat_path.read_text(encoding="utf-8"))["t"]
        except (OSError, ValueError, KeyError):
            last = None
        if last is not None and (now - last) <= self.stale_limit_seconds:
            return True
        marker = self.evidence_dir / "WATCHDOG_TERMINATION.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        with marker.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"reason": "WATCHDOG_STALE_HEARTBEAT",
                                 "last_beat": last, "now": now,
                                 "stale_limit_seconds": self.stale_limit_seconds},
                                indent=2) + "\n")
        self.terminated = True
        return False
