"""In-memory heartbeat of the WASTE loop's current stage.

The loop (via its runner) calls ``record`` each tick with the stage it is in; the
cockpit polls ``snapshot`` (through ``/api/forex/waste-loop/stage``) to drive the live
AI-activity indicator. HONEST BY CONSTRUCTION: if no tick has landed within
``stale_after_s``, ``running`` is False and the stage collapses to 'idle' — the
indicator then shows OFFLINE, never invented activity. This is a process-local status
mirror, not a source of truth; it places no trade and gates nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

VALID_STAGES = (
    "idle", "watch", "analyze", "strategize", "test",
    "execute", "compound", "locked", "no_trade", "blocked",
)
_STALE_AFTER_S = 12.0


@dataclass
class _Beat:
    stage: str = "idle"
    detail: Optional[str] = None
    symbol: Optional[str] = None
    updated_at: Optional[str] = None  # ISO-8601 UTC
    stage_trace: list[str] = field(default_factory=list)


_BEAT = _Beat()


def record(stage: str, *, detail: Optional[str] = None, symbol: Optional[str] = None) -> None:
    """Stamp the loop's current stage. Unknown stages collapse to 'idle'."""
    s = str(stage).strip().lower()
    if s not in VALID_STAGES:
        s = "idle"
    if s == "watch" or not _BEAT.stage_trace:
        _BEAT.stage_trace = [s]
    elif _BEAT.stage_trace[-1] != s:
        _BEAT.stage_trace.append(s)
        _BEAT.stage_trace = _BEAT.stage_trace[-12:]
    _BEAT.stage = s
    _BEAT.detail = detail
    _BEAT.symbol = symbol
    _BEAT.updated_at = datetime.now(timezone.utc).isoformat()


def reset() -> None:
    """Clear the heartbeat (tests / shutdown) — collapses to idle/offline."""
    global _BEAT
    _BEAT = _Beat()


def snapshot(*, stale_after_s: float = _STALE_AFTER_S) -> Dict[str, Any]:
    """Current heartbeat. ``running`` is True only if a tick landed within
    ``stale_after_s``; otherwise stage is forced to 'idle' (OFFLINE)."""
    now = datetime.now(timezone.utc)
    age: Optional[float] = None
    running = False
    if _BEAT.updated_at:
        try:
            t = datetime.fromisoformat(_BEAT.updated_at)
            age = (now - t).total_seconds()
            running = 0.0 <= age <= float(stale_after_s)
        except (ValueError, TypeError):
            running = False
    return {
        "report_kind": "waste_loop_stage",
        "stage": _BEAT.stage if running else "idle",
        "running": running,
        "detail": _BEAT.detail if running else None,
        "symbol": _BEAT.symbol if running else None,
        "updated_at": _BEAT.updated_at,
        "age_seconds": round(age, 2) if age is not None else None,
        "stage_trace": list(_BEAT.stage_trace) if running else [],
    }
