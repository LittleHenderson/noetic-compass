"""HTTP route for the multi-timeframe runtime selector.

Thin REST layer over `MultiTimeframeRuntime`. The runtime is the shared
source of truth for "which timeframes are active for which symbol"; this
route is what the UI selector posts/queries against and what a future
concurrent-monitor loop reads at boot time.

The runtime instance is a process-singleton (`_RUNTIME`) so all routes,
the bot, and the monitor share state. Single-threaded uvicorn is the
expected deployment; if the server moves to multi-worker, this should
move behind a file-backed or Redis-backed store. Today the runtime is
pure in-memory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, HTTPException

from cas_forex.multi_timeframe_runtime import (
    CANONICAL_TIMEFRAMES,
    MultiTimeframeRuntime,
    UnknownTimeframeError,
)

router = APIRouter()


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "multi-timeframe-runtime.json"

_RUNTIME = MultiTimeframeRuntime(DEFAULT_STATE_PATH)


def get_runtime() -> MultiTimeframeRuntime:
    """Process-singleton accessor; tests can substitute via
    ``timeframes.set_runtime_for_testing(...)``."""
    return _RUNTIME


def set_runtime_for_testing(runtime: MultiTimeframeRuntime) -> None:
    """Replace the process-singleton runtime. Tests only."""
    global _RUNTIME
    _RUNTIME = runtime


def _selection_payload(symbol: str) -> Dict[str, object]:
    selection = get_runtime().selection_for(symbol)
    return {
        "symbol": selection.symbol,
        "active_timeframes": sorted(selection.active_timeframes),
    }


@router.get("/canonical")
async def get_canonical_timeframes() -> Dict[str, List[str]]:
    """List the canonical timeframe vocabulary. UI selector reads this so
    the choices stay in sync with the runtime's accepted set."""
    return {"canonical_timeframes": sorted(CANONICAL_TIMEFRAMES)}


@router.get("")
@router.get("/")
async def list_active() -> Dict[str, object]:
    """Snapshot of every symbol with at least one active timeframe."""
    snapshot = get_runtime().all_active()
    return {
        "symbols": [
            {"symbol": symbol, "active_timeframes": sorted(tfs)}
            for symbol, tfs in sorted(snapshot.items())
        ]
    }


@router.get("/{symbol}")
async def get_symbol_selection(symbol: str) -> Dict[str, object]:
    """Return the active-timeframe selection for one symbol (empty list
    when the symbol has no active TFs — not a 404, the symbol is just
    not yet active)."""
    return _selection_payload(symbol)


@router.post("/{symbol}/{timeframe}")
async def activate_timeframe(symbol: str, timeframe: str) -> Dict[str, object]:
    """Activate ``timeframe`` for ``symbol``. Idempotent (re-activating an
    already-active TF is a 200, not an error). 400 on unknown timeframe."""
    try:
        get_runtime().activate(symbol, timeframe)
    except UnknownTimeframeError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unknown_timeframe",
                "message": str(exc),
                "canonical_timeframes": sorted(CANONICAL_TIMEFRAMES),
            },
        ) from exc
    return _selection_payload(symbol)


@router.delete("/{symbol}/{timeframe}")
async def deactivate_timeframe(symbol: str, timeframe: str) -> Dict[str, object]:
    """Deactivate ``timeframe`` for ``symbol``. Idempotent. 400 on
    unknown timeframe."""
    try:
        get_runtime().deactivate(symbol, timeframe)
    except UnknownTimeframeError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unknown_timeframe",
                "message": str(exc),
                "canonical_timeframes": sorted(CANONICAL_TIMEFRAMES),
            },
        ) from exc
    return _selection_payload(symbol)
