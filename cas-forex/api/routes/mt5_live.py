"""HTTP route for the live MetaTrader 5 account snapshot (read-only).

``GET /account`` returns the owner's connected MT5 account + open positions,
cached ~4s. It attaches to the running terminal and reads only — it never places
orders. ``POST /refresh`` forces a fresh read (bypassing the cache).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from cas_forex.broker_symbol_diagnostics import build_broker_symbol_diagnostics
from cas_forex.mt5_live import (
    get_mt5_account_snapshot,
    get_mt5_permission_snapshot,
    get_mt5_position_protection_snapshot,
)

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


@router.get("/symbol-diagnostics")
def get_symbol_diagnostics(symbols: str | None = None) -> dict[str, Any]:
    """Read-only broker symbol resolution and MT5 contract constraints."""
    requested = [item.strip() for item in str(symbols or "").split(",") if item.strip()] or None
    try:
        return build_broker_symbol_diagnostics(requested)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/permissions")
def get_permissions(force: bool = False) -> dict[str, Any]:
    """Read-only MT5 terminal/account order-send permission diagnostics."""
    return get_mt5_permission_snapshot(force=force)


@router.get("/protection")
def get_position_protection(force: bool = False, notify: bool = False) -> dict[str, Any]:
    """Read-only MT5 open-position stop-loss protection diagnostics."""
    report = get_mt5_position_protection_snapshot(force=force)
    if notify and report.get("requires_owner_attention"):
        from cas_forex.critical_notifications import (
            build_unprotected_position_event,
            emit_critical_notification,
        )

        audit = emit_critical_notification(
            build_unprotected_position_event(report),
            source="api.mt5_live.protection",
        )
        report["notification_audit"] = audit
    return report
