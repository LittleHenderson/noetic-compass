"""Open-position stop-loss protection reporting.

This module is observational: it inspects position rows already read from a
broker/demo snapshot and reports whether every open position has a stop loss.
It never places, closes, or modifies orders.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from cas_forex.time_utils import utc_now

REPORT_KIND = "cas_forex_position_protection_report"
STATUS_CLEAR = "ALL_POSITIONS_PROTECTED"
STATUS_UNPROTECTED = "UNPROTECTED_POSITIONS"
STATUS_UNAVAILABLE = "POSITION_PROTECTION_UNAVAILABLE"
CLAIM_BOUNDARY = (
    "Position protection reporting is read-only. It inspects open-position stop-loss "
    "fields and does not place, close, modify, or authorize broker orders."
)


def _positive_number(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out > 0 else None


def _position_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    stop = _positive_number(row.get("stop_loss") if "stop_loss" in row else row.get("sl"))
    take_profit = _positive_number(row.get("take_profit") if "take_profit" in row else row.get("tp"))
    return {
        "ticket": row.get("ticket") or row.get("broker_ticket"),
        "symbol": str(row.get("symbol") or ""),
        "side": str(row.get("side") or row.get("direction") or ""),
        "lots": _positive_number(row.get("lots") if "lots" in row else row.get("volume")),
        "open_price": _positive_number(row.get("open_price") if "open_price" in row else row.get("price_open")),
        "current_price": _positive_number(row.get("current_price") if "current_price" in row else row.get("price_current")),
        "stop_loss": stop,
        "take_profit": take_profit,
        "protected_by_stop": stop is not None,
        "floating_pnl_usd": row.get("floating_pnl_usd") if "floating_pnl_usd" in row else row.get("profit"),
    }


def build_position_protection_report(
    positions: Sequence[Mapping[str, Any]] | None,
    *,
    connected: bool | None = True,
    source: str = "mt5_account_snapshot",
    detail: str | None = None,
) -> dict[str, Any]:
    """Return a serializable protection report for open positions."""

    generated_at = utc_now().isoformat()
    if connected is False:
        return {
            "report_kind": REPORT_KIND,
            "generated_at": generated_at,
            "source": source,
            "status": STATUS_UNAVAILABLE,
            "connected": False,
            "open_position_count": 0,
            "protected_position_count": 0,
            "unprotected_position_count": 0,
            "unprotected_positions": [],
            "protected_positions": [],
            "all_positions_protected": False,
            "requires_owner_attention": True,
            "detail": detail or "Position protection cannot be verified because the account snapshot is unavailable.",
            "claim_boundary": CLAIM_BOUNDARY,
        }

    rows = [_position_summary(row) for row in (positions or []) if isinstance(row, Mapping)]
    unprotected = [row for row in rows if not row["protected_by_stop"]]
    protected = [row for row in rows if row["protected_by_stop"]]
    status = STATUS_UNPROTECTED if unprotected else STATUS_CLEAR
    if unprotected:
        msg = (
            f"{len(unprotected)} open position(s) have no broker-side stop loss visible in the latest snapshot."
        )
    elif rows:
        msg = "Every open position has a broker-side stop loss visible in the latest snapshot."
    else:
        msg = "No open positions are visible in the latest snapshot."
    return {
        "report_kind": REPORT_KIND,
        "generated_at": generated_at,
        "source": source,
        "status": status,
        "connected": connected,
        "open_position_count": len(rows),
        "protected_position_count": len(protected),
        "unprotected_position_count": len(unprotected),
        "unprotected_positions": unprotected,
        "protected_positions": protected,
        "all_positions_protected": not unprotected,
        "requires_owner_attention": bool(unprotected),
        "detail": detail or msg,
        "claim_boundary": CLAIM_BOUNDARY,
    }
