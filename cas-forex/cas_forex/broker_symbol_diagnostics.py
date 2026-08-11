"""Read-only broker symbol and MT5 contract diagnostics."""

from __future__ import annotations

from typing import Any, Iterable, Optional

from cas_forex.config import config
from cas_forex.instruments import (
    SUPPORTED_SYMBOLS,
    broker_symbol_candidates,
    canonical_symbol,
    resolve_broker_symbol,
)
from cas_forex.time_utils import utc_now


def build_broker_symbol_diagnostics(
    symbols: Optional[Iterable[str]] = None,
    *,
    bridge: Any = None,
) -> dict[str, Any]:
    """Report how CAS symbols map to the connected MT5 broker contract.

    This is read-only. It may attach to a running MT5 terminal to call
    ``symbol_info`` / ``symbols_get`` / ``symbol_select`` but never calls
    ``order_send`` or changes trading authority.
    """
    resolved_symbols = _requested_symbols(symbols)
    mt5_bridge = bridge
    if mt5_bridge is None:
        from cas_forex.broker.mt5_bridge import MT5Bridge

        mt5_bridge = MT5Bridge()
    connected = _safe_connect(mt5_bridge)
    mt5 = getattr(mt5_bridge, "_mt5", None) if connected else None
    overrides = getattr(config, "mt5_symbol_overrides", "")

    rows = [
        _symbol_diagnostic(symbol, mt5=mt5, overrides=overrides, connected=connected)
        for symbol in resolved_symbols
    ]
    unresolved = [row["canonical_symbol"] for row in rows if row.get("status") != "RESOLVED"]
    attention = bool(unresolved) or not connected
    return {
        "report_kind": "cas_forex_broker_symbol_diagnostics",
        "generated_at_iso": utc_now().isoformat(),
        "status": "OK" if not attention else "ATTENTION",
        "mt5_connected": bool(connected),
        "symbols_requested": list(resolved_symbols),
        "unresolved_symbols": unresolved,
        "mt5_symbol_overrides_configured": bool(str(overrides or "").strip()),
        "symbols": rows,
        "claim_boundary": (
            "Broker symbol diagnostics are read-only MT5 symbol/contract checks. "
            "They do not place orders, authorize live trading, change risk limits, "
            "deposit, withdraw, or move funds."
        ),
    }


def _symbol_diagnostic(
    symbol: str,
    *,
    mt5: Any,
    overrides: str,
    connected: bool,
) -> dict[str, Any]:
    canonical = canonical_symbol(symbol)
    resolution = resolve_broker_symbol(
        canonical,
        broker=mt5,
        overrides=overrides,
        select=connected,
    )
    info = _safe_symbol_info(mt5, resolution.selected_symbol) if mt5 and resolution.selected_symbol else None
    contract = _contract_snapshot(info)
    candidates = broker_symbol_candidates(canonical, overrides)
    return {
        **resolution.as_dict(),
        "canonical_symbol": canonical,
        "static_candidates": list(candidates),
        "contract": contract,
        "broker_contract_constraints": _constraint_summary(contract),
        "diagnostic_status": _diagnostic_status(resolution.status, connected, contract),
    }


def _requested_symbols(symbols: Optional[Iterable[str]]) -> tuple[str, ...]:
    if symbols is None:
        return tuple(sorted(SUPPORTED_SYMBOLS))
    out: list[str] = []
    seen: set[str] = set()
    for value in symbols:
        for part in str(value or "").split(","):
            raw = part.strip()
            if not raw:
                continue
            canonical = canonical_symbol(raw)
            if canonical not in seen:
                seen.add(canonical)
                out.append(canonical)
    return tuple(out or sorted(SUPPORTED_SYMBOLS))


def _safe_connect(bridge: Any) -> bool:
    try:
        connect = getattr(bridge, "connect", None)
        if callable(connect):
            return bool(connect())
        is_connected = getattr(bridge, "is_connected", None)
        return bool(is_connected()) if callable(is_connected) else False
    except Exception:
        return False


def _safe_symbol_info(mt5: Any, symbol: Optional[str]) -> Any:
    if not mt5 or not symbol:
        return None
    try:
        return mt5.symbol_info(symbol)
    except Exception:
        return None


def _contract_snapshot(info: Any) -> dict[str, Any]:
    if info is None:
        return {}
    fields = (
        "name",
        "path",
        "description",
        "trade_mode",
        "digits",
        "point",
        "volume_min",
        "volume_max",
        "volume_step",
        "volume_limit",
        "trade_contract_size",
        "trade_tick_size",
        "trade_tick_value",
        "trade_stops_level",
        "trade_freeze_level",
        "currency_base",
        "currency_profit",
        "currency_margin",
        "margin_initial",
        "margin_maintenance",
        "filling_mode",
    )
    return {field: _jsonable(getattr(info, field, None)) for field in fields if getattr(info, field, None) is not None}


def _constraint_summary(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "min_lot": contract.get("volume_min"),
        "max_lot": contract.get("volume_max"),
        "lot_step": contract.get("volume_step"),
        "stop_level_points": contract.get("trade_stops_level"),
        "freeze_level_points": contract.get("trade_freeze_level"),
        "point": contract.get("point"),
        "digits": contract.get("digits"),
        "contract_size": contract.get("trade_contract_size"),
        "tick_size": contract.get("trade_tick_size"),
        "tick_value": contract.get("trade_tick_value"),
    }


def _diagnostic_status(resolution_status: str, connected: bool, contract: dict[str, Any]) -> str:
    if resolution_status != "RESOLVED":
        return "UNRESOLVED"
    if not connected:
        return "STATIC_ONLY_MT5_DISCONNECTED"
    if not contract:
        return "RESOLVED_NO_CONTRACT_INFO"
    return "RESOLVED_WITH_CONTRACT"


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)
