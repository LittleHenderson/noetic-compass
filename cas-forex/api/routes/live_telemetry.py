"""HTTP route for the live trade telemetry panel.

Read-only aggregation of "what is currently open" the autonomous agent has
already produced via the existing evidence pipeline. The UI polls this on a
~2s interval to surface open positions, per-symbol floating P&L, and the
last update timestamp — purely observational, no proposals, no picks.

Source-selection priority (highest first):
  1. `mt5_terminal_api_verifier` — the most authoritative real terminal
     snapshot, when present. Reports raw broker positions (ticket, volume,
     price_open, price_current, profit).
  2. `movement_stream` — the paper/demo telemetry that the dashboard
     already aggregates from the account ledger plus the latest
     proposal/risk evidence. Used when no real terminal verification is
     available yet.
  3. `none` — no live evidence at all. Endpoint returns an empty
     open-position list and `data_freshness.stale: true`. NEVER fabricated.

The endpoint NEVER invents prices, ticket counts, or PnL when no evidence
exists, and it has no opinion on whether the operator should trade.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple

from fastapi import APIRouter, HTTPException

from api import data as data_module
from cas_forex.time_utils import utc_now

router = APIRouter()


# Staleness window: an evidence snapshot older than this is flagged stale.
_DEFAULT_STALENESS_WINDOW = timedelta(minutes=5)


def _now_iso() -> str:
    return utc_now().isoformat()


def _direction_from_mt5_type(raw: Any) -> str:
    """MT5 `type` is 0 = BUY, 1 = SELL. Be permissive — also accept string
    forms like "BUY"/"SELL"/"LONG"/"SHORT" so we tolerate upstream shape
    drift without faking a direction."""
    if isinstance(raw, str):
        token = raw.strip().upper()
        if token in {"BUY", "LONG", "0"}:
            return "BUY"
        if token in {"SELL", "SHORT", "1"}:
            return "SELL"
    if isinstance(raw, bool):
        return "BUY" if raw is False else "SELL"
    if isinstance(raw, (int, float)):
        return "BUY" if int(raw) == 0 else "SELL"
    return "BUY"


def _direction_from_side(raw: Any) -> str:
    """Movement-stream paper positions use `side: LONG|SHORT`."""
    if isinstance(raw, str):
        token = raw.strip().upper()
        if token in {"LONG", "BUY"}:
            return "BUY"
        if token in {"SHORT", "SELL"}:
            return "SELL"
    return "BUY"


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_iso(value: Any) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    try:
        # tolerate `Z` suffix
        token = value.replace("Z", "+00:00") if value.endswith("Z") else value
        parsed = datetime.fromisoformat(token)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _staleness(last_update_iso: Optional[str]) -> bool:
    if not last_update_iso:
        return True
    parsed = _parse_iso(last_update_iso)
    if parsed is None:
        return True
    return (utc_now() - parsed) > _DEFAULT_STALENESS_WINDOW


def _normalize_mt5_position(raw: Mapping[str, Any]) -> Dict[str, Any]:
    symbol = str(raw.get("symbol") or "").upper()
    direction = _direction_from_mt5_type(raw.get("type"))
    lots = _as_float(raw.get("volume"))
    entry = _as_float(raw.get("price_open"))
    current = _as_float(raw.get("price_current"))
    floating = _as_float(raw.get("profit"))
    ticket = raw.get("ticket")
    return {
        "symbol": symbol,
        "direction": direction,
        "lots": round(lots, 4),
        "entry_price": entry,
        "current_price": current,
        "floating_pnl": round(floating, 2),
        "opened_at_iso": raw.get("time_open_iso") or raw.get("opened_at_iso"),
        "broker_ticket": str(ticket) if ticket is not None else None,
    }


def _normalize_paper_position(raw: Mapping[str, Any]) -> Dict[str, Any]:
    symbol = str(raw.get("symbol") or "").upper()
    direction = _direction_from_side(raw.get("side"))
    lots = _as_float(raw.get("lot_size"))
    entry = _as_float(raw.get("open_price"))
    current = _as_float(raw.get("current_price"))
    floating = _as_float(raw.get("floating_pnl_usd"))
    ticket = raw.get("broker_ticket")
    return {
        "symbol": symbol,
        "direction": direction,
        "lots": round(lots, 4),
        "entry_price": entry,
        "current_price": current,
        "floating_pnl": round(floating, 2),
        "opened_at_iso": raw.get("opened_at_iso") or raw.get("entry_time_iso"),
        "broker_ticket": str(ticket) if ticket else None,
    }


def _collect_from_mt5_terminal() -> Optional[Tuple[List[Dict[str, Any]], str]]:
    """Try the MT5 terminal API verifier first — those are the closest
    thing the system has to real broker positions. Returns
    (positions, last_update_iso) or None if no usable evidence."""
    try:
        report = data_module.mt5_terminal_api_verifier_latest()
    except HTTPException:
        return None
    except Exception:
        return None
    if not isinstance(report, Mapping):
        return None
    snapshot = report.get("terminal_snapshot")
    if not isinstance(snapshot, Mapping):
        return None
    raw_positions = snapshot.get("positions")
    if not isinstance(raw_positions, list):
        return None
    positions = [
        _normalize_mt5_position(p)
        for p in raw_positions
        if isinstance(p, Mapping) and p.get("symbol")
    ]
    last_update = (
        report.get("created_at")
        or (report.get("probe") or {}).get("trading_date")
        or report.get("trading_date")
    )
    return positions, str(last_update) if last_update else _now_iso()


def _collect_from_movement_stream() -> Optional[Tuple[List[Dict[str, Any]], str]]:
    """Fall back to the paper/demo movement stream."""
    try:
        stream = data_module.movement_stream()
    except HTTPException:
        return None
    except Exception:
        return None
    if not isinstance(stream, Mapping):
        return None
    raw_positions = stream.get("positions")
    if not isinstance(raw_positions, list):
        return None
    positions = [
        _normalize_paper_position(p)
        for p in raw_positions
        if isinstance(p, Mapping) and p.get("symbol")
    ]
    last_update = stream.get("timestamp") or (stream.get("account") or {}).get(
        "timestamp"
    )
    return positions, str(last_update) if last_update else _now_iso()


def _empty_payload() -> Dict[str, Any]:
    return {
        "as_of_iso": _now_iso(),
        "open_positions": [],
        "totals": {"open_position_count": 0, "total_floating_pnl": 0.0},
        "data_freshness": {
            "source": "none",
            "stale": True,
            "last_update_iso": None,
        },
    }


def _build_payload(
    positions: List[Dict[str, Any]],
    source: str,
    last_update_iso: str,
) -> Dict[str, Any]:
    total = round(
        sum(_as_float(p.get("floating_pnl")) for p in positions),
        2,
    )
    return {
        "as_of_iso": _now_iso(),
        "open_positions": positions,
        "totals": {
            "open_position_count": len(positions),
            "total_floating_pnl": total,
        },
        "data_freshness": {
            "source": source,
            "stale": _staleness(last_update_iso),
            "last_update_iso": last_update_iso,
        },
    }


def collect_live_telemetry() -> Dict[str, Any]:
    """Aggregate the latest evidence. Source-selection logic lives here so
    tests can drive it directly without lighting up the ASGI app."""
    mt5_result = _collect_from_mt5_terminal()
    if mt5_result is not None and mt5_result[0]:
        positions, last_update_iso = mt5_result
        return _build_payload(positions, "mt5_terminal_api_verifier", last_update_iso)

    paper_result = _collect_from_movement_stream()
    if paper_result is not None and paper_result[0]:
        positions, last_update_iso = paper_result
        return _build_payload(positions, "movement_stream", last_update_iso)

    # Neither source produced positions — empty observational telemetry.
    return _empty_payload()


@router.get("")
@router.get("/")
async def get_live_telemetry() -> Dict[str, Any]:
    """Return a snapshot of currently open positions plus per-symbol
    floating P&L. Read-only telemetry; never proposes trades."""
    return collect_live_telemetry()
