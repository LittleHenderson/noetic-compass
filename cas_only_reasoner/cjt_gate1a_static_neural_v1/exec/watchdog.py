"""watchdog.py -- termination must not depend on the training process reaching
`finally` (GATE 1A.2 s.9 + 1A.2R s.3 + 1A.2R.2 + 1A.2R.2A).

The driver writes a heartbeat file with REAL epoch time every step; this SEPARATE
process polls it. Fail-closed laws:
- no termination before the first heartbeat during a startup grace;
- one REAL epoch clock domain on both sides;
- the stale limit is DERIVED from the SIGNED per-job cap of the signature-
  verified execution approval (exec/watchdog_authority.py, GATE 1A.2R.2C);
- an IMPOSSIBLE FUTURE heartbeat (beyond now + MAX_FUTURE_HEARTBEAT_SKEW_SECONDS)
  is refused, so a future-valued clock cannot extend the ceiling (1A.2R.2);
- a MALFORMED heartbeat value (non-numeric, bool, NaN, infinity, negative) is
  refused as WATCHDOG_INVALID_HEARTBEAT rather than escaping as a raw TypeError
  from the numeric comparison (1A.2R.2A). The parser rejects NaN/infinity too.
Every refusal writes a termination marker, requests termination via the caller,
and returns False -- the watchdog process never disappears silently.
"""
from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path

MAX_FUTURE_HEARTBEAT_SKEW_SECONDS = 5.0


class WatchdogError(RuntimeError):
    pass


def is_valid_timestamp(v) -> bool:
    """A heartbeat/observed-now value must be a finite, NON-BOOL, NON-NEGATIVE
    int/float. NaN/infinity/strings/lists/dicts/bools/negatives are invalid --
    so the numeric comparison in poll_once can never raise a TypeError and a
    non-numeric heartbeat can never read as fresh. (An impossible FUTURE numeric
    heartbeat is still caught separately by the future-skew rule.)"""
    if isinstance(v, bool) or type(v) not in (int, float):
        return False
    return math.isfinite(v) and float(v) >= 0.0


def _reject_non_finite(x):
    raise WatchdogError(f"INVALID_HEARTBEAT_JSON_CONSTANT: {x}")


class Watchdog:
    def __init__(self, heartbeat_path: Path, evidence_dir: Path,
                 stale_limit_seconds: float, startup_grace_seconds: float = 300.0,
                 launched_at: float = None):
        self.heartbeat_path = Path(heartbeat_path)
        self.evidence_dir = Path(evidence_dir)
        for name, val in (("stale_limit_seconds", stale_limit_seconds),
                          ("startup_grace_seconds", startup_grace_seconds)):
            if isinstance(val, bool) or type(val) not in (int, float) \
                    or not math.isfinite(val) or val < 0:
                raise WatchdogError(f"INVALID_{name.upper()}: {val!r}")
        self.stale_limit_seconds = float(stale_limit_seconds)
        self.startup_grace_seconds = float(startup_grace_seconds)
        self._launched_at = launched_at
        self._seen_heartbeat = False
        self.terminated = False

    def beat(self, now: float) -> None:
        # a heartbeat is written only with a VALID timestamp; a bad clock is
        # caught here (defense in depth) rather than poisoning the file. The
        # write is ATOMIC (temp file + os.replace, GATE 1A.2R.2B), so a reader
        # never observes a partially written envelope.
        if not is_valid_timestamp(now):
            raise WatchdogError(f"INVALID_HEARTBEAT_VALUE: {now!r}")
        self.heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps({"t": now}) + "\n"
        fd, tmp = tempfile.mkstemp(dir=str(self.heartbeat_path.parent),
                                   prefix=".hb-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(body)
            os.replace(tmp, self.heartbeat_path)       # atomic on the same fs
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _terminate(self, reason, detail, now):
        marker = self.evidence_dir / "WATCHDOG_TERMINATION.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        with marker.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(
                {"reason": reason, "heartbeat_timestamp": detail,
                 "observed_now": now,
                 "allowed_future_skew_seconds": MAX_FUTURE_HEARTBEAT_SKEW_SECONDS,
                 "stale_limit_seconds": self.stale_limit_seconds},
                indent=2) + "\n")
        self.terminated = True
        return False

    def poll_once(self, now: float) -> bool:
        """True if the campaign is alive; on any refusal, request termination.
        Cases: invalid observed-now, no heartbeat yet (startup grace), fresh,
        stale, impossible-future, and MALFORMED heartbeat -- the last four all
        fail closed with a marker; nothing escapes as a raw exception."""
        if not is_valid_timestamp(now):
            return self._terminate("WATCHDOG_INVALID_OBSERVED_NOW", None, None)
        if self._launched_at is None:
            self._launched_at = now
        raw = None
        try:
            raw = json.loads(
                self.heartbeat_path.read_text(encoding="utf-8"),
                parse_constant=_reject_non_finite)      # NaN/Infinity -> refuse
            # ENVELOPE TOTALITY (GATE 1A.2R.2B): the top level must be a dict
            # with a "t" key; a top-level array/null/scalar is a malformed
            # envelope, not "no heartbeat yet"
            if not isinstance(raw, dict) or "t" not in raw:
                raise WatchdogError("MALFORMED_HEARTBEAT_ENVELOPE")
            last = raw["t"]
            self._seen_heartbeat = True
        except (OSError, ValueError, KeyError, TypeError, WatchdogError):
            last = None
            # a heartbeat FILE that exists but is malformed/non-finite/wrong
            # envelope is an attack, not "no heartbeat yet": fail closed
            if self.heartbeat_path.is_file() and not _empty(self.heartbeat_path):
                return self._terminate("WATCHDOG_INVALID_HEARTBEAT",
                                       "<unparseable>", now)
        if last is None:
            if (now - self._launched_at) <= self.startup_grace_seconds:
                return True
            return self._terminate("WATCHDOG_NO_HEARTBEAT_AFTER_GRACE", None, now)
        if not is_valid_timestamp(last):
            # parsed but non-numeric / bool / out-of-domain: never fresh
            return self._terminate("WATCHDOG_INVALID_HEARTBEAT",
                                   _safe(last), now)
        if last > now + MAX_FUTURE_HEARTBEAT_SKEW_SECONDS:
            return self._terminate("WATCHDOG_FUTURE_HEARTBEAT", last, now)
        if (now - last) <= self.stale_limit_seconds:
            return True
        return self._terminate("WATCHDOG_STALE_HEARTBEAT", last, now)


def _empty(path: Path) -> bool:
    try:
        return path.stat().st_size == 0
    except OSError:
        return True


def _safe(v):
    """A JSON-serializable, size-bounded representation of an invalid value."""
    try:
        return json.loads(json.dumps(v))[:200] if isinstance(v, str) else \
            (v if type(v) in (int, float, bool) or v is None else str(type(v)))
    except Exception:
        return "<unrepresentable>"
