"""Shared cooldown for MetaTrader5 terminal handshakes.

``mt5.initialize()`` blocks for the full connect timeout (8s here, 60s by
MetaTrader's default) whenever no terminal is reachable. Seven modules call it
independently -- the bridge, the market-data connector, the process guard, the
terminal/paper verifiers, the deal-history ingest, and the paper broker adapter
-- so a single dashboard aggregation attempted the handshake 24 times and spent
208 seconds waiting on a terminal that was not running. That is what made the
API test suite unusable.

This module records one process-wide "the terminal was unreachable at T" fact so
the remaining callers fail fast until the cooldown expires.

SAFETY: the guard can only ever make a connect attempt return False sooner. It
never reports a connection that does not exist, so every fail-closed check built
on top of it (``will_execute_real_order``, ``is_demo_account``, the live-trading
gate) keeps its existing meaning. A caller that must ignore the cooldown -- an
owner-triggered reconnect, a deliberate terminal probe -- passes ``force=True``.
"""

from __future__ import annotations

import threading
import time
from typing import Any

# Long enough to collapse a burst of attempts inside one aggregation, short
# enough that a terminal the owner just started is picked up promptly.
MT5_INIT_FAILURE_COOLDOWN_SECONDS = 30.0

_failed_at: float | None = None
_lock = threading.Lock()


def in_cooldown() -> bool:
    """True when a recent handshake failed and the cooldown has not expired."""
    with _lock:
        failed_at = _failed_at
    if failed_at is None:
        return False
    return (time.monotonic() - failed_at) < MT5_INIT_FAILURE_COOLDOWN_SECONDS


def record_result(connected: bool) -> None:
    """Record a handshake outcome. Success clears the cooldown."""
    global _failed_at
    with _lock:
        _failed_at = None if connected else time.monotonic()


def reset() -> None:
    """Clear the cooldown so the next attempt retries immediately."""
    global _failed_at
    with _lock:
        _failed_at = None


def guarded_initialize(mt5: Any, *, force: bool = False, **kwargs: Any) -> bool:
    """Call ``mt5.initialize(**kwargs)`` unless a recent attempt already failed.

    Returns False without touching the terminal while in cooldown. Any exception
    from the MetaTrader5 module is recorded as a failure and re-raised, so
    callers keep whatever error handling they already have.
    """
    if not force and in_cooldown():
        return False
    try:
        result = bool(mt5.initialize(**kwargs))
    except Exception:
        record_result(False)
        raise
    record_result(result)
    return result
