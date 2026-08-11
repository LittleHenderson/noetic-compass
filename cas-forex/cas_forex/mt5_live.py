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
from datetime import datetime, timezone
from typing import Any, Optional

from cas_forex.mt5_permissions import build_mt5_permission_state
from cas_forex.position_protection import build_position_protection_report
from cas_forex.pre_trade_money import (
    build_open_position_stop_risk,
    summarize_open_position_stop_risk,
)

_lock = threading.Lock()
_bridge: Any = None
_cache: Optional[dict[str, Any]] = None
_cache_expiry = 0.0
_TTL_SECONDS = 4.0
# When a read fails (MT5's IPC is flaky/unreachable), cache the failure longer so
# the UI poller can't hammer it with back-to-back slow connects.
_FAIL_TTL_SECONDS = 20.0
_MARKET_TICK_FRESH_MAX_AGE_SECONDS = 5 * 60.0
_CLAIM_BOUNDARY = (
    "MT5 terminal account snapshot is a read-only terminal mirror panel. It shows "
    "cached account and open-position state from the running MetaTrader 5 "
    "terminal. This panel itself does not submit trade actions. CAS AI and "
    "automation can still open, close, and manage trades through the MT5 "
    "bridge/verifier path for demo or the protected order-dispatch path for "
    "real money."
)
_MIRROR_SCOPE = "account + open positions from the running MT5 terminal"
_MIRROR_LABEL = "TERMINAL MIRROR"
_READ_ONLY_LABEL = "READ-ONLY MIRROR"
_WRITES_FROM_PANEL = "none from this panel"
_GENERIC_EXECUTION_PATH_NOTE = (
    "CAS AI and automation execute through the MT5 bridge/verifier path for demo "
    "and through the protected order-dispatch path for real money."
)


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
        "comment": str(getattr(p, "comment", "") or ""),
        "magic": getattr(p, "magic", None),
        "identifier": getattr(p, "identifier", None),
        "opened_at_epoch": getattr(p, "time", None),
    }


def _owner_risk_cap_pct() -> float | None:
    try:
        from cas_forex.ai_control_authority import get_authority

        value = get_authority().control.get("max_risk_pct_per_trade")
        cap = float(value)
        return cap if cap > 0 else None
    except Exception:
        return None


def _market_tick_report(
    mt5: Any,
    symbol: str,
    *,
    now: datetime,
) -> dict[str, Any]:
    """Describe the terminal's last real tick separately from account-read age."""

    from cas_forex.market_data.connector import (
        _mt5_symbol_open,
        forex_week_open,
        infer_mt5_future_server_offset_seconds,
    )

    report: dict[str, Any] = {
        "symbol": symbol,
        "status": "UNAVAILABLE",
        "tick_observed_at": None,
        "tick_age_seconds": None,
        "fresh": False,
        "market_open": False,
        "week_schedule_open": forex_week_open(now),
    }
    tick_reader = getattr(mt5, "symbol_info_tick", None)
    if not callable(tick_reader):
        report["detail"] = "MT5 symbol_info_tick is unavailable."
        return report
    try:
        tick = tick_reader(symbol)
    except Exception as exc:
        report["detail"] = f"MT5 tick read failed: {type(exc).__name__}: {exc}"
        return report
    if tick is None:
        report["detail"] = "MT5 returned no tick for this open-position symbol."
        return report

    try:
        time_msc = float(getattr(tick, "time_msc", 0.0) or 0.0)
        raw_epoch = time_msc / 1000.0 if time_msc > 0 else float(getattr(tick, "time", 0.0) or 0.0)
    except (TypeError, ValueError):
        raw_epoch = 0.0
    if raw_epoch <= 0:
        report["detail"] = "MT5 tick has no usable timestamp."
        return report

    offset_seconds = infer_mt5_future_server_offset_seconds(
        raw_epoch,
        now_epoch=now.timestamp(),
    )
    tick_at = datetime.fromtimestamp(raw_epoch - offset_seconds, tz=timezone.utc)
    age_seconds = (now - tick_at).total_seconds()
    try:
        bid = float(getattr(tick, "bid", 0.0) or 0.0)
        ask = float(getattr(tick, "ask", 0.0) or 0.0)
        last = float(getattr(tick, "last", 0.0) or 0.0)
    except (TypeError, ValueError):
        bid = ask = last = 0.0
    if bid <= 0 and ask <= 0 and last > 0:
        bid = last
        ask = last
    info_reader = getattr(mt5, "symbol_info", None)
    try:
        info = info_reader(symbol) if callable(info_reader) else None
    except Exception:
        info = None
    market_open = _mt5_symbol_open(
        mt5,
        info,
        bid,
        ask,
        timestamp=tick_at,
        now=now,
    )
    schedule_open = forex_week_open(now)
    if market_open:
        status = "FRESH"
        detail = "The terminal tick is current and the symbol is executable."
    elif not schedule_open:
        status = "MARKET_CLOSED"
        detail = "The weekly Forex session is closed; unchanged floating P&L can be expected."
    elif age_seconds > _MARKET_TICK_FRESH_MAX_AGE_SECONDS:
        status = "STALE"
        detail = "The weekly session is open, but the terminal tick is older than the freshness limit."
    elif age_seconds < -5.0:
        status = "FUTURE_CLOCK"
        detail = "The normalized terminal tick is materially ahead of the host clock."
    else:
        status = "NOT_EXECUTABLE"
        detail = "The tick is recent, but price or symbol trade-mode evidence is not executable."
    report.update(
        {
            "status": status,
            "tick_observed_at": tick_at.isoformat(),
            "tick_age_seconds": round(age_seconds, 3),
            "fresh": bool(market_open),
            "market_open": bool(market_open),
            "week_schedule_open": bool(schedule_open),
            "server_utc_offset_seconds": int(offset_seconds),
            "detail": detail,
        }
    )
    return report


def _summarize_market_ticks(rows: list[dict[str, Any]]) -> dict[str, Any]:
    reports = [dict(row) for row in rows if isinstance(row, dict)]
    available = [row for row in reports if row.get("tick_observed_at")]
    fresh_count = sum(1 for row in reports if row.get("fresh") is True)
    stale_count = max(0, len(reports) - fresh_count)
    latest = min(
        available,
        key=lambda row: float(row.get("tick_age_seconds") or 0.0),
        default={},
    )
    oldest = max(
        available,
        key=lambda row: float(row.get("tick_age_seconds") or 0.0),
        default={},
    )
    if not reports:
        status = "NO_OPEN_POSITIONS"
        detail = "No open positions require terminal-tick freshness evidence."
    elif fresh_count == len(reports):
        status = "FRESH"
        detail = "Every open-position symbol has a current executable MT5 tick."
    elif available and all(row.get("status") == "MARKET_CLOSED" for row in reports):
        status = "MARKET_CLOSED"
        detail = "The account snapshot is current, but the weekly market is closed and floating P&L may remain unchanged."
    elif not available:
        status = "UNAVAILABLE"
        detail = "No open-position symbol has a usable MT5 tick timestamp."
    else:
        status = "STALE_OR_PARTIAL"
        detail = "One or more open-position symbols lacks a current executable MT5 tick; displayed price and floating P&L may be stale."
    return {
        "report_kind": "cas_forex_mt5_open_position_tick_freshness",
        "status": status,
        "symbol_count": len(reports),
        "fresh_symbol_count": fresh_count,
        "stale_or_unavailable_symbol_count": stale_count,
        "last_tick_observed_at": latest.get("tick_observed_at"),
        "last_tick_age_seconds": latest.get("tick_age_seconds"),
        "oldest_tick_observed_at": oldest.get("tick_observed_at"),
        "oldest_tick_age_seconds": oldest.get("tick_age_seconds"),
        "all_open_position_ticks_fresh": bool(reports) and fresh_count == len(reports),
        "any_market_open": any(row.get("market_open") is True for row in reports),
        "freshness_limit_seconds": _MARKET_TICK_FRESH_MAX_AGE_SECONDS,
        "symbols": reports,
        "detail": detail,
        "claim_boundary": (
            "Account snapshot age proves when CAS last read MT5. Tick age proves when "
            "MT5 last received a market price for each open-position symbol. A fresh "
            "account read can legitimately contain an old tick while the market is closed."
        ),
    }


def _read_snapshot() -> dict[str, Any]:
    observed_at = datetime.now(timezone.utc)
    base = {
        "report_kind": "cas_forex_mt5_live_account",
        "snapshot_observed_at": observed_at.isoformat(),
        **_mirror_surface_contract(execution_path_note=_GENERIC_EXECUTION_PATH_NOTE),
    }
    bridge = _get_bridge()
    try:
        if not bridge.is_connected():
            bridge.connect()
        if not bridge.is_connected():
            mt5 = getattr(bridge, "_mt5", None)
            if mt5 is None:
                # The package never imported in THIS process.
                return {
                    **base,
                    "connected": False,
                    "detail": "The MetaTrader5 Python package isn't importable in the API process.",
                    "diagnostic": "import_failed",
                }
            last_error = None
            try:
                last_error = mt5.last_error()
            except Exception:
                pass
            return {
                **base,
                "connected": False,
                "detail": (
                    "MetaTrader 5 isn't reachable. Open the MT5 terminal, log into your "
                    "account, and make sure it shows a live connection (ticking prices)."
                ),
                "diagnostic": "ipc",
                "last_error": list(last_error) if isinstance(last_error, tuple) else last_error,
            }
        mt5 = bridge._mt5
        acc = mt5.account_info()
        term = mt5.terminal_info()
        positions = mt5.positions_get() or []
        demo = bridge.is_demo_account()
        if acc is None:
            return {**base, "connected": True, "detail": "Connected, but account info is unavailable."}
        permission_state = build_mt5_permission_state(term, acc, is_demo=demo)
        account_payload = {
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
        }
        risk_account_snapshot = {
            "balance": account_payload["balance_usd"],
            "equity": account_payload["equity_usd"],
            "margin": account_payload["margin_used_usd"],
            "margin_free": account_payload["free_margin_usd"],
            "leverage": account_payload["leverage"],
        }
        risk_cap_pct = _owner_risk_cap_pct()
        position_rows = [_position_dict(p) for p in positions]
        tick_reports: list[dict[str, Any]] = []
        for row in position_rows:
            tick_report = _market_tick_report(
                mt5,
                str(row.get("symbol") or ""),
                now=observed_at,
            )
            tick_reports.append(tick_report)
            row["market_tick_observed_at"] = tick_report.get("tick_observed_at")
            row["market_tick_age_seconds"] = tick_report.get("tick_age_seconds")
            row["market_tick_fresh"] = tick_report.get("fresh")
            row["market_open"] = tick_report.get("market_open")
            row["market_tick_status"] = tick_report.get("status")
            stop_risk = build_open_position_stop_risk(
                symbol=str(row.get("symbol") or ""),
                direction=row.get("side"),
                lots=row.get("lots"),
                open_price=row.get("open_price"),
                current_price=row.get("current_price"),
                stop_loss=row.get("stop_loss"),
                take_profit=row.get("take_profit"),
                account_snapshot=risk_account_snapshot,
                bridge=bridge,
                risk_cap_pct=risk_cap_pct,
            )
            row["stop_risk"] = stop_risk
            for key in (
                "risk_at_stop_usd",
                "risk_at_stop_pct_equity",
                "remaining_to_stop_drawdown_usd",
                "remaining_to_stop_drawdown_pct_equity",
                "stop_locked_profit_usd",
                "risk_cap_pct",
                "risk_cap_breached",
                "risk_basis",
                "risk_economics_source",
            ):
                row[key] = stop_risk.get(key)
        position_risk = summarize_open_position_stop_risk(
            position_rows,
            risk_cap_pct=risk_cap_pct,
        )
        protection_state = build_position_protection_report(
            position_rows,
            connected=bool(term.connected) if term is not None else True,
            source="mt5_live_account_snapshot",
        )
        return {
            **base,
            "connected": bool(term.connected) if term is not None else True,
            "is_demo": bool(demo),
            "account": account_payload,
            "positions": position_rows,
            "open_position_count": len(positions),
            "algo_allowed": bool(permission_state.get("terminal_algo_trading_enabled")),
            "permission_state": permission_state,
            "position_protection": protection_state,
            "position_risk": position_risk,
            "market_tick": _summarize_market_ticks(tick_reports),
            "execution_path_note": (
                "CAS AI and automation execute through the MT5 bridge/verifier path for demo/paper."
                if demo
                else "CAS AI and automation execute through the protected order-dispatch path for real money once owner live authority is armed."
            ),
            "note": (
                "Terminal mirror from your MetaTrader 5 account. This panel is observational only. "
                + (
                    "CAS AI and automation handle demo/paper trade actions through the MT5 bridge/verifier path."
                    if demo
                    else "CAS AI and automation handle real-money trade actions through the protected order-dispatch path once owner live authority is armed."
                )
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
            return _with_snapshot_freshness(_cache, cached=True)
        snap = _read_snapshot()
        _cache = snap
        # Back off longer when down, so a flaky terminal can't freeze the poller.
        _cache_expiry = now + (_TTL_SECONDS if snap.get("connected") else _FAIL_TTL_SECONDS)
        return _with_snapshot_freshness(snap, cached=False)


def _with_snapshot_freshness(snapshot: dict[str, Any], *, cached: bool) -> dict[str, Any]:
    out = dict(snapshot)
    observed_at = out.get("snapshot_observed_at")
    age_seconds: float | None = None
    if isinstance(observed_at, str) and observed_at:
        try:
            parsed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            age_seconds = max(0.0, (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds())
        except ValueError:
            age_seconds = None
    out["cached"] = bool(cached)
    out["snapshot_age_seconds"] = round(age_seconds, 3) if age_seconds is not None else None
    out["snapshot_fresh"] = bool(out.get("connected")) and age_seconds is not None and age_seconds <= _FAIL_TTL_SECONDS
    out["snapshot_cache_ttl_seconds"] = _TTL_SECONDS if out.get("connected") else _FAIL_TTL_SECONDS
    return out


def get_mt5_permission_snapshot(force: bool = False) -> dict[str, Any]:
    """Return the MT5 order-send permission view without position-table noise."""

    snapshot = get_mt5_account_snapshot(force=force)
    account = snapshot.get("account") if isinstance(snapshot.get("account"), dict) else {}
    permission_state = snapshot.get("permission_state")
    if not isinstance(permission_state, dict):
        detail = str(snapshot.get("detail") or snapshot.get("error") or "MT5 account snapshot is unavailable.")
        permission_state = {
            "report_kind": "cas_forex_mt5_permission_state",
            "status": "MT5_ACCOUNT_UNAVAILABLE",
            "permission_label": "MT5 UNAVAILABLE",
            "can_submit_order_send": False,
            "terminal_connected": bool(snapshot.get("connected")) if "connected" in snapshot else None,
            "terminal_trade_allowed": None,
            "terminal_algo_trading_enabled": None,
            "terminal_tradeapi_disabled": None,
            "account_trade_allowed": None,
            "account_expert_trading_allowed": None,
            "account_trade_mode": None,
            "blockers": [detail],
            "plain_english": f"MT5 permission state is unavailable: {detail}",
        }
    return {
        "report_kind": "cas_forex_mt5_permission_diagnostics",
        **_mirror_surface_contract(execution_path_note=snapshot.get("execution_path_note")),
        "connected": bool(snapshot.get("connected")),
        "cached": bool(snapshot.get("cached")),
        "is_demo": snapshot.get("is_demo"),
        "account": {
            "login": account.get("login"),
            "server": account.get("server"),
            "currency": account.get("currency"),
        },
        "permission_state": permission_state,
        "detail": snapshot.get("detail"),
        "error": snapshot.get("error"),
        "claim_boundary": (
            "MT5 permission diagnostics are read-only terminal/account introspection. "
            "This endpoint does not submit trade actions, does not authorize CAS live trading by itself, and does not call order_send."
        ),
    }


def get_mt5_position_protection_snapshot(force: bool = False) -> dict[str, Any]:
    """Return a compact MT5 open-position stop-loss protection report."""

    snapshot = get_mt5_account_snapshot(force=force)
    protection = snapshot.get("position_protection")
    if isinstance(protection, dict):
        return {
            **_mirror_surface_contract(execution_path_note=snapshot.get("execution_path_note")),
            **dict(protection),
        }
    positions = snapshot.get("positions") if isinstance(snapshot.get("positions"), list) else []
    return {
        **_mirror_surface_contract(execution_path_note=snapshot.get("execution_path_note")),
        **build_position_protection_report(
        [row for row in positions if isinstance(row, dict)],
        connected=bool(snapshot.get("connected")) if "connected" in snapshot else False,
        source="mt5_position_protection_snapshot",
        detail=str(snapshot.get("detail") or snapshot.get("error") or ""),
    ),
    }


def _mirror_surface_contract(*, execution_path_note: Any = None) -> dict[str, Any]:
    return {
        "claim_boundary": _CLAIM_BOUNDARY,
        "mirror_scope": _MIRROR_SCOPE,
        "mirror_label": _MIRROR_LABEL,
        "read_only_label": _READ_ONLY_LABEL,
        "writes_from_panel": _WRITES_FROM_PANEL,
        "observational_only": True,
        "execution_path_note": str(execution_path_note or _GENERIC_EXECUTION_PATH_NOTE),
    }
