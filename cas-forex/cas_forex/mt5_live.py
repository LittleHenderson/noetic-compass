"""One persistent, cached, read-only MT5 connection for the live cockpit.

MT5's Python IPC is fragile under rapid connect/shutdown (it jams). So this module
keeps ONE attached connection for the whole process and serves brief-TTL cached
reads, instead of connecting per request. It is read-only: account snapshot +
open positions. It never places orders.

The bridge attaches to the owner's already-running, already-logged-in terminal
(see ``MT5Bridge._initialize``), so this surfaces the real connected demo/live
account exactly as the terminal shows it.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Optional

_lock = threading.Lock()
_bridge: Any = None
_cache: Optional[dict[str, Any]] = None
_cache_expiry = 0.0
_TTL_SECONDS = 4.0


def _get_bridge() -> Any:
    global _bridge
    from cas_forex.broker.mt5_bridge import MT5Bridge

    if _bridge is None:
        _bridge = MT5Bridge()
    return _bridge


def _position_dict(p: Any) -> dict[str, Any]:
    # MT5 position type: 0 = BUY (long), 1 = SELL (short).
    side = "LONG" if getattr(p, "type", 0) == 0 else "SHORT"
    return {
        "ticket": getattr(p, "ticket", None),
        "symbol": getattr(p, "symbol", ""),
        "side": side,
        "lots": float(getattr(p, "volume", 0.0)),
        "open_price": float(getattr(p, "price_open", 0.0)),
        "current_price": float(getattr(p, "price_current", 0.0)),
        "stop_loss": float(getattr(p, "sl", 0.0)) or None,
        "take_profit": float(getattr(p, "tp", 0.0)) or None,
        "floating_pnl_usd": float(getattr(p, "profit", 0.0)),
        "swap_usd": float(getattr(p, "swap", 0.0)),
    }


def _read_snapshot() -> dict[str, Any]:
    base = {"report_kind": "cas_forex_mt5_live_account"}
    bridge = _get_bridge()
    try:
        if not bridge.is_connected():
            bridge.connect()
        if not bridge.is_connected():
            return {
                **base,
                "connected": False,
                "detail": (
                    "MetaTrader 5 isn't reachable. Open the MT5 terminal, log into your "
                    "account, and make sure it shows a live connection (ticking prices)."
                ),
            }
        mt5 = bridge._mt5
        acc = mt5.account_info()
        term = mt5.terminal_info()
        positions = mt5.positions_get() or []
        demo = bridge.is_demo_account()
        if acc is None:
            return {**base, "connected": True, "detail": "Connected, but account info is unavailable."}
        return {
            **base,
            "connected": bool(term.connected) if term is not None else True,
            "is_demo": bool(demo),
            "account": {
                "login": int(getattr(acc, "login", 0)),
                "server": str(getattr(acc, "server", "")),
                "name": str(getattr(acc, "name", "")),
                "currency": str(getattr(acc, "currency", "USD")),
                "leverage": int(getattr(acc, "leverage", 0)),
                "balance_usd": float(getattr(acc, "balance", 0.0)),
                "equity_usd": float(getattr(acc, "equity", 0.0)),
                "margin_used_usd": float(getattr(acc, "margin", 0.0)),
                "free_margin_usd": float(getattr(acc, "margin_free", 0.0)),
                "floating_pnl_usd": float(getattr(acc, "profit", 0.0)),
            },
            "positions": [_position_dict(p) for p in positions],
            "open_position_count": len(positions),
            "algo_allowed": bool(getattr(term, "trade_allowed", False)) if term is not None else False,
            "note": (
                "Read-only, live from your MetaTrader 5 terminal. "
                + ("Demo account — paper-safe." if demo else "LIVE account — real money; orders still require owner authorization.")
            ),
        }
    except Exception as exc:  # never raise into a request; surface the reason
        return {**base, "connected": False, "error": f"{type(exc).__name__}: {exc}"}


def get_mt5_account_snapshot(force: bool = False) -> dict[str, Any]:
    """Cached live MT5 account + positions snapshot (one IPC read per ~4s)."""
    global _cache, _cache_expiry
    with _lock:
        now = time.monotonic()
        if _cache is not None and not force and now < _cache_expiry:
            out = dict(_cache)
            out["cached"] = True
            return out
        snap = _read_snapshot()
        _cache = snap
        _cache_expiry = now + _TTL_SECONDS
        out = dict(snap)
        out["cached"] = False
        return out
