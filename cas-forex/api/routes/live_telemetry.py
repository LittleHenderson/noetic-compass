"""HTTP route for the live trade telemetry panel.

Read-only aggregation of "what is currently open" the autonomous agent has
already produced via the existing evidence pipeline. The UI polls this on a
~2s interval to surface open positions, per-symbol floating P&L, and the
last update timestamp — purely observational, no proposals, no picks.

Source-selection priority (highest first):
  1. `mt5_demo_account_snapshot` / `mt5_live_account_snapshot` — the current
     cached terminal mirror used by dispatch and position management. This
     outranks older exported verifier evidence.
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
from api.route_cache import cache_first_payload, cached_payload_snapshot, store_cache_payload
from cas_forex.movement_stream import build_movement_source_truth_snapshot
from cas_forex.mt5_live import get_mt5_account_snapshot
from cas_forex.time_utils import utc_now

router = APIRouter()


# Staleness window: an evidence snapshot older than this is flagged stale.
_DEFAULT_STALENESS_WINDOW = timedelta(minutes=5)
# Do not add a minute-long HTTP cache on top of the MT5 mirror's four-second
# cache. The cockpit, chats, and briefing must converge on the same volatile
# account state while still avoiding one terminal IPC call per UI poll.
LIVE_TELEMETRY_CACHE_TTL_SECONDS = 4.0
_MT5_TELEMETRY_SOURCES = {
    "mt5_demo_account_snapshot",
    "mt5_live_account_snapshot",
    "mt5_terminal_api_verifier",  # Historical/test compatibility.
}


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


def _as_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


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


def _age_metrics(
    opened_at_iso: Any,
    *,
    reference_iso: Optional[str] = None,
) -> Tuple[Optional[int], Optional[float]]:
    opened = _parse_iso(opened_at_iso)
    if opened is None:
        return None, None
    reference = _parse_iso(reference_iso) if reference_iso else utc_now()
    if reference is None:
        reference = utc_now()
    age_seconds = max(0, int((reference - opened).total_seconds()))
    return age_seconds, round(age_seconds / 86400.0, 2)


def _normalize_mt5_position(
    raw: Mapping[str, Any],
    *,
    snapshot_iso: Optional[str] = None,
    is_demo: Optional[bool] = None,
) -> Dict[str, Any]:
    symbol = str(raw.get("symbol") or "").upper()
    direction = (
        _direction_from_side(raw.get("side"))
        if raw.get("side") is not None
        else _direction_from_mt5_type(raw.get("type"))
    )
    lots = _as_float(raw.get("lots", raw.get("volume")))
    entry = _as_float(raw.get("open_price", raw.get("price_open")))
    current = _as_float(raw.get("current_price", raw.get("price_current")))
    floating = _as_float(raw.get("floating_pnl_usd", raw.get("profit")))
    swap = _as_float(raw.get("swap_usd", raw.get("swap")))
    commission = _as_float(raw.get("commission_usd", raw.get("commission")))
    ticket = raw.get("ticket")
    opened_at_iso = raw.get("time_open_iso") or raw.get("opened_at_iso")
    age_seconds, age_days = _age_metrics(opened_at_iso, reference_iso=snapshot_iso)
    return {
        "symbol": symbol,
        "direction": direction,
        "lots": round(lots, 4),
        "entry_price": entry,
        "current_price": current,
        "floating_pnl": round(floating, 2),
        "swap": round(swap, 2),
        "commission": round(commission, 2),
        "net_open_pnl": round(floating + swap + commission, 2),
        "opened_at_iso": opened_at_iso,
        "broker_ticket": str(ticket) if ticket is not None else None,
        "stop_loss": raw.get("stop_loss", raw.get("sl")),
        "take_profit": raw.get("take_profit", raw.get("tp")),
        "risk_at_stop_usd": raw.get("risk_at_stop_usd"),
        "risk_at_stop_pct_equity": raw.get("risk_at_stop_pct_equity"),
        "remaining_to_stop_drawdown_usd": raw.get("remaining_to_stop_drawdown_usd"),
        "risk_cap_pct": raw.get("risk_cap_pct"),
        "risk_cap_breached": raw.get("risk_cap_breached"),
        "price_source": (
            "mt5_demo_account_snapshot"
            if is_demo is True
            else "mt5_live_account_snapshot"
            if is_demo is False
            else "mt5_terminal_api_verifier"
        ),
        "price_stale": False,
        "stale_reason": None,
        "age_seconds": age_seconds,
        "age_days": age_days,
        "position_source_label": (
            "MT5_DEMO_BROKER" if is_demo is True else "MT5_LIVE_BROKER"
        ),
    }


def _normalize_paper_position(raw: Mapping[str, Any]) -> Dict[str, Any]:
    symbol = str(raw.get("symbol") or "").upper()
    direction = _direction_from_side(raw.get("side"))
    lots = _as_float(raw.get("lot_size"))
    entry = _as_float(raw.get("open_price"))
    current = _as_float(raw.get("current_price"))
    floating = _as_float(raw.get("floating_pnl_usd"))
    swap = _as_float(raw.get("swap_usd"))
    commission = _as_float(raw.get("commission_usd"))
    ticket = raw.get("broker_ticket")
    opened_at_iso = raw.get("opened_at_iso") or raw.get("entry_time_iso")
    age_seconds = _as_int(raw.get("age_seconds"))
    age_days_raw = raw.get("age_days")
    try:
        age_days = float(age_days_raw) if age_days_raw is not None else None
    except (TypeError, ValueError):
        age_days = None
    return {
        "symbol": symbol,
        "direction": direction,
        "lots": round(lots, 4),
        "entry_price": entry,
        "current_price": current,
        "floating_pnl": round(floating, 2),
        "swap": round(swap, 2),
        "commission": round(commission, 2),
        "net_open_pnl": round(floating + swap + commission, 2),
        "opened_at_iso": opened_at_iso,
        "broker_ticket": str(ticket) if ticket else None,
        "price_source": str(raw.get("price_source") or "") or None,
        "price_stale": bool(raw.get("price_stale", False)),
        "stale_reason": str(raw.get("stale_reason") or "") or None,
        "age_seconds": age_seconds,
        "age_days": age_days,
        "position_source_label": str(raw.get("position_source_label") or "") or None,
    }


def _collect_from_mt5_terminal() -> Optional[Tuple[List[Dict[str, Any]], str, Dict[str, Any]]]:
    """Read the current MT5 account mirror, never an old verifier export."""
    try:
        report = get_mt5_account_snapshot()
    except Exception:
        return None
    if not isinstance(report, Mapping) or not report.get("connected"):
        return None
    raw_positions = report.get("positions")
    if not isinstance(raw_positions, list):
        return None
    last_update = report.get("snapshot_observed_at")
    last_update_iso = str(last_update) if last_update else _now_iso()
    is_demo = bool(report.get("is_demo"))
    account = report.get("account") if isinstance(report.get("account"), Mapping) else {}
    positions = [
        _normalize_mt5_position(p, snapshot_iso=last_update_iso, is_demo=is_demo)
        for p in raw_positions
        if isinstance(p, Mapping) and p.get("symbol")
    ]
    source = "mt5_demo_account_snapshot" if is_demo else "mt5_live_account_snapshot"
    return positions, last_update_iso, {
        "telemetry_source": source,
        "account_mode": "DEMO" if is_demo else "LIVE",
        "account_login": account.get("login"),
        "account_server": account.get("server"),
        "snapshot_cached": bool(report.get("cached")),
        "snapshot_age_seconds": report.get("snapshot_age_seconds"),
        "snapshot_fresh": report.get("snapshot_fresh"),
        "position_protection": report.get("position_protection"),
        "position_risk": report.get("position_risk"),
    }


def _movement_source_summary(stream: Mapping[str, Any]) -> Dict[str, Any]:
    canonical_truth = stream.get("movement_source_truth")
    if isinstance(canonical_truth, Mapping):
        return dict(canonical_truth)
    account = stream.get("account") if isinstance(stream.get("account"), Mapping) else {}
    last_update_iso = str(stream.get("timestamp") or account.get("timestamp") or "").strip() or None
    return build_movement_source_truth_snapshot(
        stream,
        telemetry_source="movement_stream",
        telemetry_stale=False,
        telemetry_last_update_iso=last_update_iso,
        movement_stream_present=True,
    )


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _movement_price_source_status(
    movement_source: Optional[Mapping[str, Any]],
) -> Optional[str]:
    if not isinstance(movement_source, Mapping):
        return None
    status = str(movement_source.get("price_source_status") or "").strip()
    return status or None


def _is_static_position(row: Mapping[str, Any]) -> bool:
    price_source = str(row.get("price_source") or "")
    return bool(
        row.get("price_stale")
        or price_source.startswith("paper_route_snapshot")
        or row.get("position_source_label") in {"PAPER_SIM_STATIC", "PAPER_SIM_BROKER_TICKET_STATIC"}
    )


def _append_stale_suffix(detail: str, stale: bool) -> str:
    if not stale:
        return detail
    return detail + " The latest telemetry snapshot is marked stale."


def _position_feed_truth(
    positions: List[Dict[str, Any]],
    *,
    source: str,
    stale: bool,
    last_update_iso: Optional[str],
    movement_source: Optional[Mapping[str, Any]],
    source_context: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    context = source_context if isinstance(source_context, Mapping) else {}
    price_source_status = _movement_price_source_status(movement_source)
    broker_ticket_position_count = sum(
        1 for row in positions if row.get("broker_ticket") is not None
    )
    static_position_count = sum(
        1 for row in positions if isinstance(row, Mapping) and _is_static_position(row)
    )
    if (
        source == "movement_stream"
        and price_source_status == "STATIC_SIMULATION_FALLBACK"
        and positions
    ):
        static_position_count = max(static_position_count, len(positions))

    if source in _MT5_TELEMETRY_SOURCES:
        account_mode = str(context.get("account_mode") or "").upper()
        label = (
            "MT5 DEMO"
            if account_mode == "DEMO"
            else "LIVE MT5"
            if source == "mt5_terminal_api_verifier" and not account_mode
            else "MT5 LIVE"
        )
        detail = _append_stale_suffix(
            (
                "Position rows are current MT5 demo broker positions from the connected terminal account mirror."
                if account_mode == "DEMO"
                else "Position rows in this panel are MT5 broker positions mirrored through the terminal verifier."
                if source == "mt5_terminal_api_verifier" and not account_mode
                else "Position rows are current MT5 live broker positions from the connected terminal account mirror."
            ),
            stale,
        )
    elif source == "movement_stream":
        backend_label = str(movement_source.get("position_feed_label") or "").strip() if isinstance(movement_source, Mapping) else ""
        backend_detail = str(movement_source.get("position_feed_detail") or "").strip() if isinstance(movement_source, Mapping) else ""
        label = backend_label or "SIM PROOF"
        if backend_detail:
            detail = backend_detail
        elif price_source_status == "STATIC_SIMULATION_FALLBACK":
            detail = (
                "Position rows in this panel are paper/demo simulator proof rows with static simulation fallback. "
                "These are not live MT5 terminal positions and floating P&L can sit at entry until provider/MT5 quotes are usable."
            )
        elif price_source_status == "MIXED_PROVIDER_AND_STATIC_FALLBACK":
            detail = (
                "Position rows in this panel are paper/demo simulator proof rows. "
                "Some rows are repriced and some remain static simulation; these are not live MT5 terminal positions."
            )
        elif price_source_status == "PROVIDER_ACTIVE":
            detail = (
                "Position rows in this panel are paper/demo simulator proof rows repriced by provider/MT5 fallback where available. "
                "These are not live MT5 terminal positions."
            )
        elif price_source_status == "CACHE_WARMING":
            detail = (
                "Position rows in this panel are paper/demo simulator proof rows while source truth is warming. "
                "These are not live MT5 terminal positions."
            )
        else:
            detail = "Position rows in this panel are paper/demo simulator proof rows, not live MT5 terminal positions."
        if broker_ticket_position_count:
            detail += (
                f" {broker_ticket_position_count} proof row(s) carry broker tickets, but the MT5 terminal verifier remains the broker-truth source."
            )
        detail = _append_stale_suffix(detail, stale)
    else:
        label = "NONE"
        detail = "No broker or paper/demo movement snapshot is feeding this panel right now."

    return {
        "telemetry_source": source,
        "telemetry_stale": stale,
        "telemetry_last_update_iso": last_update_iso,
        "price_source_status": price_source_status,
        "position_feed_label": label,
        "position_feed_detail": detail,
        "broker_ticket_position_count": broker_ticket_position_count,
        "static_position_count": static_position_count,
        "account_mode": context.get("account_mode"),
        "account_login": context.get("account_login"),
        "account_server": context.get("account_server"),
        "snapshot_cached": context.get("snapshot_cached"),
        "snapshot_age_seconds": context.get("snapshot_age_seconds"),
        "snapshot_fresh": context.get("snapshot_fresh"),
        "position_protection": context.get("position_protection"),
        "position_risk": context.get("position_risk"),
    }


def _movement_source_truth(
    positions: List[Dict[str, Any]],
    *,
    source: str,
    stale: bool,
    last_update_iso: Optional[str],
    movement_source: Optional[Mapping[str, Any]],
    source_truth: Optional[Mapping[str, Any]] = None,
    source_context: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    source_truth_map = source_truth if isinstance(source_truth, Mapping) else {}
    context = source_context if isinstance(source_context, Mapping) else {}
    movement_source_map = movement_source if isinstance(movement_source, Mapping) else {}
    price_source_status = _movement_price_source_status(movement_source_map)
    broker_ticket_position_count = int(source_truth_map.get("broker_ticket_position_count") or 0)
    static_position_count = int(source_truth_map.get("static_position_count") or 0)
    stale_price_position_count = 0
    provider_priced_simulator_position_count = 0
    source_label_counts: Dict[str, int] = {}

    for row in positions:
        if not isinstance(row, Mapping):
            continue
        source_label = str(row.get("position_source_label") or "").strip()
        if source_label:
            source_label_counts[source_label] = source_label_counts.get(source_label, 0) + 1
        price_source = str(row.get("price_source") or "")
        if price_source.startswith("provider_snapshot:") or price_source.startswith("operator_quote_override"):
            provider_priced_simulator_position_count += 1
        if bool(row.get("price_stale")):
            stale_price_position_count += 1

    if source == "movement_stream" and price_source_status == "STATIC_SIMULATION_FALLBACK" and positions:
        static_position_count = max(static_position_count, len(positions))

    configured_provider = str(
        movement_source_map.get("configured_market_data_provider")
        or movement_source_map.get("market_data_provider")
        or ""
    ).strip() or None
    provider_errors = (
        movement_source_map.get("provider_errors")
        if isinstance(movement_source_map.get("provider_errors"), Mapping)
        else None
    )
    provider_error_count = int(movement_source_map.get("provider_error_count") or 0)
    if provider_error_count <= 0 and isinstance(provider_errors, Mapping):
        provider_error_count = len(provider_errors)

    detail = str(
        source_truth_map.get("position_feed_detail")
        or movement_source_map.get("position_feed_detail")
        or ""
    ).strip()
    if not detail:
        detail = "No broker or paper/demo movement snapshot is feeding this panel right now."

    truth: Dict[str, Any] = dict(movement_source_map)
    truth.update({
        "movement_stream_present": source == "movement_stream",
        "telemetry_source": source,
        "telemetry_stale": stale,
        "telemetry_last_update_iso": last_update_iso,
        "price_source_status": price_source_status,
        "price_source_label": (
            str(movement_source_map.get("price_source_label"))
            if isinstance(movement_source_map.get("price_source_label"), str) and movement_source_map.get("price_source_label")
            else None
        ),
        "price_source_summary": (
            str(movement_source_map.get("price_source_summary"))
            if isinstance(movement_source_map.get("price_source_summary"), str) and movement_source_map.get("price_source_summary")
            else None
        ),
        "price_source_warning": (
            str(movement_source_map.get("price_source_warning"))
            if isinstance(movement_source_map.get("price_source_warning"), str) and movement_source_map.get("price_source_warning")
            else None
        ),
        "position_feed_label": str(source_truth_map.get("position_feed_label") or "NONE"),
        "position_feed_detail": detail,
        "static_simulation_active": bool(movement_source_map.get("static_simulation_active")) or static_position_count > 0,
        "open_position_count": len(positions),
        "broker_ticket_position_count": broker_ticket_position_count,
        "simulator_position_count": max(0, len(positions) - broker_ticket_position_count),
        "provider_priced_simulator_position_count": provider_priced_simulator_position_count,
        "static_simulator_position_count": static_position_count,
        "stale_price_position_count": stale_price_position_count,
        "static_position_count": static_position_count,
        "source_label_counts": source_label_counts,
        "configured_market_data_provider": configured_provider,
        "provider_usable_symbols": _string_list(movement_source_map.get("provider_usable_symbols")),
        "static_fallback_symbols": _string_list(movement_source_map.get("static_fallback_symbols")),
        "mt5_fallback_symbols": _string_list(movement_source_map.get("mt5_fallback_symbols")),
        "provider_stale_symbols": _string_list(movement_source_map.get("provider_stale_symbols")),
        "provider_freshness_max_age_seconds": movement_source_map.get("provider_freshness_max_age_seconds"),
        "provider_error_count": provider_error_count,
        "attention_required": bool(movement_source_map.get("attention_required")) or static_position_count > 0 or stale,
        "detail": detail,
        "local_detail": detail,
        "account_mode": context.get("account_mode"),
        "account_login": context.get("account_login"),
        "account_server": context.get("account_server"),
        "snapshot_cached": context.get("snapshot_cached"),
        "snapshot_age_seconds": context.get("snapshot_age_seconds"),
        "snapshot_fresh": context.get("snapshot_fresh"),
        "position_protection": context.get("position_protection"),
        "position_risk": context.get("position_risk"),
    })
    return truth


def _collect_from_movement_stream() -> Optional[Tuple[List[Dict[str, Any]], str, Dict[str, Any]]]:
    """Fall back to the paper/demo movement stream."""
    try:
        stream = data_module.movement_stream(use_provider_quotes=True)
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
    return positions, str(last_update) if last_update else _now_iso(), _movement_source_summary(stream)


def _empty_payload() -> Dict[str, Any]:
    detail = "No broker or paper/demo movement snapshot is feeding this panel right now."
    return {
        "as_of_iso": _now_iso(),
        "open_positions": [],
        "totals": {"open_position_count": 0, "total_floating_pnl": 0.0},
        "telemetry_source": "none",
        "telemetry_stale": True,
        "telemetry_last_update_iso": None,
        "price_source_status": None,
        "position_feed_label": "NONE",
        "position_feed_detail": detail,
        "broker_ticket_position_count": 0,
        "static_position_count": 0,
        "movement_source_truth": {
            "movement_stream_present": False,
            "telemetry_source": "none",
            "telemetry_stale": True,
            "telemetry_last_update_iso": None,
            "price_source_status": None,
            "price_source_label": None,
            "price_source_summary": None,
            "price_source_warning": None,
            "position_feed_label": "NONE",
            "position_feed_detail": detail,
            "static_simulation_active": False,
            "open_position_count": 0,
            "broker_ticket_position_count": 0,
            "simulator_position_count": 0,
            "provider_priced_simulator_position_count": 0,
            "static_simulator_position_count": 0,
            "stale_price_position_count": 0,
            "static_position_count": 0,
            "source_label_counts": {},
            "configured_market_data_provider": None,
            "provider_usable_symbols": [],
            "static_fallback_symbols": [],
            "mt5_fallback_symbols": [],
            "provider_stale_symbols": [],
            "provider_freshness_max_age_seconds": None,
            "provider_error_count": 0,
            "attention_required": False,
            "detail": detail,
            "local_detail": detail,
        },
        "data_freshness": {
            "source": "none",
            "stale": True,
            "last_update_iso": None,
            "movement_source": None,
        },
    }


def _build_payload(
    positions: List[Dict[str, Any]],
    source: str,
    last_update_iso: str,
    movement_source: Optional[Dict[str, Any]] = None,
    source_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    stale = _staleness(last_update_iso)
    gross_floating = round(
        sum(_as_float(p.get("floating_pnl")) for p in positions),
        2,
    )
    total_swap = round(sum(_as_float(p.get("swap")) for p in positions), 2)
    total_commission = round(sum(_as_float(p.get("commission")) for p in positions), 2)
    total_after_costs = round(gross_floating + total_swap + total_commission, 2)
    source_truth = _position_feed_truth(
        positions,
        source=source,
        stale=stale,
        last_update_iso=last_update_iso,
        movement_source=movement_source,
        source_context=source_context,
    )
    movement_truth = _movement_source_truth(
        positions,
        source=source,
        stale=stale,
        last_update_iso=last_update_iso,
        movement_source=movement_source,
        source_truth=source_truth,
        source_context=source_context,
    )
    return {
        "as_of_iso": _now_iso(),
        "open_positions": positions,
        "totals": {
            "open_position_count": len(positions),
            "gross_floating_pnl": gross_floating,
            "total_swap": total_swap,
            "total_commission": total_commission,
            "total_open_pnl_after_costs": total_after_costs,
            # Compatibility field now carries the account-relevant net open P&L.
            "total_floating_pnl": total_after_costs,
        },
        **source_truth,
        "movement_source_truth": movement_truth,
        "data_freshness": {
            "source": source,
            "stale": stale,
            "last_update_iso": last_update_iso,
            "movement_source": dict(movement_truth) if movement_source is not None else None,
            "account_mode": (source_context or {}).get("account_mode"),
        },
    }


def collect_live_telemetry() -> Dict[str, Any]:
    """Aggregate the latest evidence. Source-selection logic lives here so
    tests can drive it directly without lighting up the ASGI app."""
    mt5_result = _collect_from_mt5_terminal()
    if mt5_result is not None:
        positions, last_update_iso = mt5_result[0], mt5_result[1]
        source_context = mt5_result[2] if len(mt5_result) > 2 and isinstance(mt5_result[2], dict) else {}
        source = str(source_context.get("telemetry_source") or "mt5_terminal_api_verifier")
        return _build_payload(
            positions,
            source,
            last_update_iso,
            source_context=source_context,
        )

    paper_result = _collect_from_movement_stream()
    if paper_result is not None:
        positions = paper_result[0]
        last_update_iso = paper_result[1]
        movement_source = paper_result[2] if len(paper_result) > 2 else None
        return _build_payload(positions, "movement_stream", last_update_iso, movement_source)

    # Neither source produced positions — empty observational telemetry.
    return _empty_payload()


@router.get("")
@router.get("/")
async def get_live_telemetry() -> Dict[str, Any]:
    """Return a snapshot of currently open positions plus per-symbol
    floating P&L. Read-only telemetry; never proposes trades."""
    payload = cache_first_payload(
        "live_telemetry",
        builder=collect_live_telemetry,
        fallback=_empty_payload,
        ttl_seconds=LIVE_TELEMETRY_CACHE_TTL_SECONDS,
        # Returning the cold fallback would falsely present a connected account
        # as an authoritative zero-position account. Only the first read blocks;
        # established snapshots remain cache-first with background refreshes.
        block_on_cold=True,
    )
    if str(payload.get("telemetry_source") or "none") != "none":
        return payload

    # Startup prewarming can finish just before MT5 becomes reachable. Never
    # let that short-lived empty cache masquerade as broker truth once a source
    # is available; replace it synchronously on the first affected read.
    refreshed = collect_live_telemetry()
    if str(refreshed.get("telemetry_source") or "none") == "none":
        return payload
    store_cache_payload("live_telemetry", refreshed)
    return cached_payload_snapshot(
        "live_telemetry",
        ttl_seconds=LIVE_TELEMETRY_CACHE_TTL_SECONDS,
    ) or refreshed
