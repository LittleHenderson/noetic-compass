"""HTTP route for the live MetaTrader 5 account snapshot (read-only).

``GET /account`` returns the owner's connected MT5 account + open positions,
cached ~4s. It attaches to the running terminal and reads only — it never places
orders. ``POST /refresh`` forces a fresh read (bypassing the cache).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from cas_forex.mt5_live import get_mt5_account_snapshot

router = APIRouter()


# NOTE: these are sync (def, not async) on purpose — FastAPI runs sync handlers in
# a threadpool, so a slow/blocking MT5 IPC read never freezes the API event loop.
@router.get("/account")
def get_account() -> dict[str, Any]:
    """Live MT5 account + positions (cached ~4s)."""
    return get_mt5_account_snapshot()


@router.post("/refresh")
def post_refresh() -> dict[str, Any]:
    """Force a fresh read from the terminal (bypass the cache)."""
    return get_mt5_account_snapshot(force=True)
