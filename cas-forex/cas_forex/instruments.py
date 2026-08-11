"""Instrument metadata for CAS Forex.

The first CAS Forex build treated every symbol as an FX pair and measured all
price movement in "pips." Indices and gold need explicit point/tick economics,
so this module centralizes the conversion while keeping the old pip-facing API
available for existing code.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class InstrumentSpec:
    symbol: str
    asset_class: str
    unit_name: str
    price_unit: float
    contract_size: float
    default_mid: float
    price_precision: int
    yahoo_ticker: str
    mt5_symbol: str
    point_value_per_lot: Optional[float] = None

    @property
    def unit_multiplier(self) -> float:
        return 1.0 / self.price_unit


@dataclass(frozen=True)
class BrokerSymbolResolution:
    """Broker symbol selected for a canonical CAS instrument."""

    canonical_symbol: str
    selected_symbol: Optional[str]
    configured_candidates: tuple[str, ...]
    tried_candidates: tuple[str, ...]
    discovered_candidates: tuple[str, ...]
    resolution_source: str
    status: str
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "canonical_symbol": self.canonical_symbol,
            "configured_candidates": list(self.configured_candidates),
            "tried_candidates": list(self.tried_candidates),
            "discovered_candidates": list(self.discovered_candidates),
            "selected_symbol": self.selected_symbol,
            "resolution_source": self.resolution_source,
            "status": self.status,
            "detail": self.detail,
        }


def _fx(symbol: str, default_mid: float, price_unit: float = 0.0001) -> InstrumentSpec:
    return InstrumentSpec(
        symbol=symbol,
        asset_class="FX",
        unit_name="pip",
        price_unit=price_unit,
        contract_size=100_000.0,
        default_mid=default_mid,
        price_precision=3 if symbol.endswith("/JPY") else 5,
        yahoo_ticker=f"{symbol.replace('/', '')}=X",
        mt5_symbol=symbol.replace("/", ""),
    )


INSTRUMENT_SPECS = {
    "EUR/USD": _fx("EUR/USD", 1.10),
    "GBP/USD": _fx("GBP/USD", 1.27),
    "USD/JPY": _fx("USD/JPY", 145.0, price_unit=0.01),
    "AUD/USD": _fx("AUD/USD", 0.66),
    "USD/CAD": _fx("USD/CAD", 1.36),
    "AUD/CAD": _fx("AUD/CAD", 0.90),
    "GBP/AUD": _fx("GBP/AUD", 1.92),
    # --- Scout universe: more majors + crosses for the operator to watch and
    # promote/demote by realized profit. price_unit + pip math come from _fx;
    # JPY crosses use the 0.01 pip. A symbol the broker/feed doesn't serve simply
    # returns no candles and is skipped — safe to include broadly. ---
    "EUR/GBP": _fx("EUR/GBP", 0.85),
    "EUR/JPY": _fx("EUR/JPY", 160.0, price_unit=0.01),
    "GBP/JPY": _fx("GBP/JPY", 185.0, price_unit=0.01),
    "AUD/JPY": _fx("AUD/JPY", 96.0, price_unit=0.01),
    "NZD/USD": _fx("NZD/USD", 0.60),
    "USD/CHF": _fx("USD/CHF", 0.88),
    "EUR/AUD": _fx("EUR/AUD", 1.62),
    "EUR/CAD": _fx("EUR/CAD", 1.48),
    # Broker-specific CFD economics vary. These defaults are research-grade
    # placeholders: one lot = 1 currency unit per index point.
    "NAS100": InstrumentSpec(
        symbol="NAS100",
        asset_class="INDEX_CFD",
        unit_name="point",
        price_unit=1.0,
        contract_size=1.0,
        default_mid=19_500.0,
        price_precision=2,
        yahoo_ticker="^NDX",
        mt5_symbol="NAS100",
        point_value_per_lot=1.0,
    ),
    "US30": InstrumentSpec(
        symbol="US30",
        asset_class="INDEX_CFD",
        unit_name="point",
        price_unit=1.0,
        contract_size=1.0,
        default_mid=39_000.0,
        price_precision=2,
        yahoo_ticker="^DJI",
        mt5_symbol="US30",
        point_value_per_lot=1.0,
    ),
    "SPX500": InstrumentSpec(
        symbol="SPX500",
        asset_class="INDEX_CFD",
        unit_name="point",
        price_unit=1.0,
        contract_size=1.0,
        default_mid=5_500.0,
        price_precision=2,
        yahoo_ticker="^GSPC",
        mt5_symbol="SPX500",
        point_value_per_lot=1.0,
    ),
    # One standard XAU/USD lot is commonly 100 troy ounces; this uses $1 price
    # movement as the research "point" so P&L stays readable.
    "XAU/USD": InstrumentSpec(
        symbol="XAU/USD",
        asset_class="METAL_CFD",
        unit_name="dollar_point",
        price_unit=1.0,
        contract_size=100.0,
        default_mid=2_300.0,
        price_precision=2,
        yahoo_ticker="GC=F",
        mt5_symbol="XAUUSD",
        point_value_per_lot=100.0,
    ),
}

SUPPORTED_SYMBOLS = frozenset(INSTRUMENT_SPECS)

_COMMON_BROKER_SUFFIXES = {
    "M",
    "MICRO",
    "MINI",
    "PRO",
    "RAW",
    "ECN",
    "STD",
    "STANDARD",
    "CASH",
    "I",
    "R",
}

_EXTRA_BROKER_ALIASES = {
    "NAS100": ("NAS100", "USTEC", "US100", "NAS100.cash", "USTEC.cash", "NAS100m", "NAS100.i"),
    "US30": ("US30", "DJ30", "WS30", "DOW", "US30.cash", "DJ30.cash", "US30m", "US30.i"),
    "SPX500": ("SPX500", "SP500", "US500", "SPX500.cash", "US500.cash", "SPX500m"),
    "XAU/USD": ("XAUUSD", "XAU/USD", "GOLD", "XAUUSD.cash", "XAUUSDm"),
}


def symbol_key(value: str) -> str:
    """Stable comparison key for broker symbols with slashes/suffix separators."""
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _canonical_alias_map() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for canonical, spec in INSTRUMENT_SPECS.items():
        base_values = {
            canonical,
            canonical.replace("/", ""),
            spec.mt5_symbol,
        }
        for value in base_values:
            aliases[symbol_key(value)] = canonical
        for value in _EXTRA_BROKER_ALIASES.get(canonical, ()):
            aliases[symbol_key(value)] = canonical
    return aliases


_CANONICAL_ALIAS_MAP = _canonical_alias_map()


def get_instrument(symbol: str) -> InstrumentSpec:
    symbol = canonical_symbol(symbol)
    try:
        return INSTRUMENT_SPECS[symbol]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported symbol '{symbol}'. Supported: {sorted(SUPPORTED_SYMBOLS)}"
        ) from exc


def canonical_symbol(symbol: str) -> str:
    """Return the CAS canonical symbol for user, broker, or MT5-style input."""
    raw = str(symbol or "").strip()
    if raw in INSTRUMENT_SPECS:
        return raw
    key = symbol_key(raw)
    if key in _CANONICAL_ALIAS_MAP:
        return _CANONICAL_ALIAS_MAP[key]

    # Broker suffixes can be attached to any known alias, not only the primary
    # MT5 symbol (for example US500m or USTECraw).
    for suffix in sorted(_COMMON_BROKER_SUFFIXES, key=len, reverse=True):
        if key.endswith(suffix):
            alias_key = key[: -len(suffix)]
            if alias_key in _CANONICAL_ALIAS_MAP:
                return _CANONICAL_ALIAS_MAP[alias_key]

    for canonical, spec in sorted(
        INSTRUMENT_SPECS.items(),
        key=lambda item: len(symbol_key(item[1].mt5_symbol)),
        reverse=True,
    ):
        base = symbol_key(spec.mt5_symbol)
        if key == base:
            return canonical
        if key.startswith(base):
            suffix = key[len(base):]
            if suffix in _COMMON_BROKER_SUFFIXES:
                return canonical

    raise ValueError(
        f"Unsupported symbol '{symbol}'. Supported: {sorted(SUPPORTED_SYMBOLS)}"
    )


def canonical_or_normalized_symbol(symbol: Any) -> str:
    """Return one stable identity for supported aliases and unknown symbols.

    Supported broker aliases collapse to the canonical CAS instrument. Unknown
    symbols remain usable as a punctuation-free comparison key instead of
    raising, which keeps historical evidence readable without silently merging
    it into a different supported market.
    """

    raw = str(symbol or "").strip()
    if raw:
        try:
            return canonical_symbol(raw)
        except ValueError:
            pass
    return symbol_key(raw) or "UNKNOWN"


def pip_multiplier(symbol: str) -> float:
    """Backward-compatible movement multiplier.

    For FX this is true pips. For indices/gold it returns research points.
    """
    return get_instrument(symbol).unit_multiplier


def price_unit_size(symbol: str) -> float:
    return get_instrument(symbol).price_unit


def yahoo_ticker(symbol: str) -> str:
    return get_instrument(symbol).yahoo_ticker


def broker_symbol(symbol: str) -> str:
    return get_instrument(symbol).mt5_symbol


def broker_symbol_aliases(symbol: str) -> tuple[str, ...]:
    canonical = canonical_symbol(symbol)
    spec = get_instrument(canonical)
    base = spec.mt5_symbol
    values = [
        canonical,
        canonical.replace("/", ""),
        base,
        f"{base}m",
        f"{base}.m",
    ]
    values.extend(_EXTRA_BROKER_ALIASES.get(canonical, ()))
    return tuple(_dedupe(values))


def configured_broker_symbol_candidates(
    symbol: str,
    overrides: str | Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    parsed = parse_broker_symbol_overrides(overrides)
    if not parsed:
        return ()
    canonical = canonical_symbol(symbol)
    spec = get_instrument(canonical)
    keys = (
        str(symbol or "").strip(),
        str(symbol or "").strip().upper(),
        symbol_key(str(symbol or "")),
        canonical,
        canonical.upper(),
        symbol_key(canonical),
        spec.mt5_symbol,
        spec.mt5_symbol.upper(),
        symbol_key(spec.mt5_symbol),
    )
    for key in keys:
        values = parsed.get(key)
        if values:
            return values
    return ()


def broker_symbol_candidates(
    symbol: str,
    overrides: str | Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    canonical = canonical_symbol(symbol)
    configured = configured_broker_symbol_candidates(canonical, overrides)
    spec = get_instrument(canonical)
    return tuple(
        _dedupe(
            [
                *configured,
                spec.mt5_symbol,
                canonical,
                canonical.replace("/", ""),
                *broker_symbol_aliases(canonical),
            ]
        )
    )


def parse_broker_symbol_overrides(
    overrides: str | Mapping[str, Any] | None,
) -> dict[str, tuple[str, ...]]:
    if not overrides:
        return {}
    if isinstance(overrides, Mapping):
        raw_items = overrides.items()
    else:
        raw = str(overrides or "").strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = _parse_symbol_override_pairs(raw)
        if not isinstance(parsed, Mapping):
            return {}
        raw_items = parsed.items()

    out: dict[str, tuple[str, ...]] = {}
    for key, value in raw_items:
        names = _candidate_tuple(value)
        raw_key = str(key or "").strip()
        if not raw_key or not names:
            continue
        for lookup_key in (raw_key, raw_key.upper(), symbol_key(raw_key)):
            if lookup_key:
                out[lookup_key] = names
        try:
            canonical = canonical_symbol(raw_key)
        except ValueError:
            continue
        spec = get_instrument(canonical)
        for lookup_key in (
            canonical,
            canonical.upper(),
            symbol_key(canonical),
            spec.mt5_symbol,
            spec.mt5_symbol.upper(),
            symbol_key(spec.mt5_symbol),
        ):
            if lookup_key:
                out[lookup_key] = names
    return out


def resolve_broker_symbol(
    symbol: str,
    *,
    broker: Any = None,
    overrides: str | Mapping[str, Any] | None = None,
    select: bool = True,
) -> BrokerSymbolResolution:
    """Resolve a CAS symbol to the actual visible broker/MT5 symbol.

    Owner overrides are tried first, then the static CAS default, then broker
    Market Watch discovery. With no broker API available, this returns the
    static first candidate so non-MT5 callers stay deterministic.
    """
    canonical = canonical_symbol(symbol)
    configured = configured_broker_symbol_candidates(canonical, overrides)
    static_candidates = list(broker_symbol_candidates(canonical, overrides))
    symbol_info = getattr(broker, "symbol_info", None) if broker is not None else None
    if broker is None or not callable(symbol_info):
        selected = static_candidates[0] if static_candidates else broker_symbol(canonical)
        return BrokerSymbolResolution(
            canonical_symbol=canonical,
            selected_symbol=selected,
            configured_candidates=configured,
            tried_candidates=tuple(static_candidates[:40]),
            discovered_candidates=(),
            resolution_source="STATIC_FALLBACK",
            status="RESOLVED",
            detail="No broker symbol_info API was available; using the static CAS broker symbol.",
        )

    tried: list[str] = []
    for candidate in static_candidates:
        tried.append(candidate)
        if _broker_symbol_available(broker, candidate, select=select):
            return BrokerSymbolResolution(
                canonical_symbol=canonical,
                selected_symbol=candidate,
                configured_candidates=configured,
                tried_candidates=tuple(tried[:40]),
                discovered_candidates=(),
                resolution_source="STATIC_OR_OWNER_OVERRIDE",
                status="RESOLVED",
            )

    discovered = discover_broker_symbol_candidates(canonical, broker)
    for candidate in discovered:
        if candidate in tried:
            continue
        tried.append(candidate)
        if _broker_symbol_available(broker, candidate, select=select):
            return BrokerSymbolResolution(
                canonical_symbol=canonical,
                selected_symbol=candidate,
                configured_candidates=configured,
                tried_candidates=tuple(tried[:40]),
                discovered_candidates=tuple(discovered[:40]),
                resolution_source="BROKER_SYMBOL_DISCOVERY",
                status="RESOLVED",
            )

    return BrokerSymbolResolution(
        canonical_symbol=canonical,
        selected_symbol=None,
        configured_candidates=configured,
        tried_candidates=tuple(tried[:40]),
        discovered_candidates=tuple(discovered[:40]),
        resolution_source="UNRESOLVED",
        status="UNRESOLVED",
        detail=(
            f"No visible MT5 symbol was found for {canonical}. Set "
            "CAS_FOREX_MT5_SYMBOL_OVERRIDES or make the broker symbol visible in Market Watch."
        ),
    )


def discover_broker_symbol_candidates(symbol: str, broker: Any) -> tuple[str, ...]:
    symbols_get = getattr(broker, "symbols_get", None)
    if not callable(symbols_get):
        return ()
    found: list[str] = []
    for pattern in symbol_discovery_patterns(symbol):
        try:
            rows = symbols_get(pattern)
        except Exception:
            rows = None
        found.extend(_symbol_name(row) for row in (rows or []))
    if not found:
        try:
            rows = symbols_get()
        except Exception:
            rows = None
        found.extend(
            name
            for name in (_symbol_name(row) for row in (rows or []))
            if symbol_name_matches(symbol, name)
        )
    return tuple(rank_symbol_candidates(symbol, found))


def symbol_discovery_patterns(symbol: str) -> tuple[str, ...]:
    key = symbol_key(symbol)
    if key == "NAS100":
        return ("*NAS*", "*USTEC*", "*US100*")
    if key == "US30":
        return ("*US30*", "*DJ30*", "*WS30*", "*DOW*")
    if key == "SPX500":
        return ("*SPX*", "*SP500*", "*US500*")
    if key == "XAUUSD":
        return ("*XAU*", "*GOLD*")
    return (f"*{key}*", f"*{str(symbol or '').replace('/', '')}*")


def rank_symbol_candidates(symbol: str, names: Sequence[str]) -> list[str]:
    clean_target = symbol_key(symbol)

    def score(name: str) -> tuple[int, int, str]:
        clean = symbol_key(name)
        if clean == clean_target:
            bucket = 0
        elif clean.startswith(clean_target) or clean_target in clean:
            bucket = 1
        elif symbol_name_matches(symbol, name):
            bucket = 2
        else:
            bucket = 9
        return bucket, len(str(name or "")), str(name or "")

    return [name for name in sorted(_dedupe(names), key=score) if name]


def symbol_name_matches(symbol: str, name: str) -> bool:
    clean_name = symbol_key(name)
    clean_symbol = symbol_key(symbol)
    if clean_symbol and (clean_symbol in clean_name or clean_name in clean_symbol):
        return True
    try:
        aliases = broker_symbol_aliases(symbol)
    except ValueError:
        aliases = ()
    return any(symbol_key(alias) in clean_name for alias in aliases)


def _broker_symbol_available(broker: Any, mt5_symbol: str, *, select: bool) -> bool:
    if not mt5_symbol:
        return False
    if select:
        selector = getattr(broker, "symbol_select", None)
        if callable(selector):
            try:
                selector(mt5_symbol, True)
            except Exception:
                pass
    try:
        return broker.symbol_info(mt5_symbol) is not None
    except Exception:
        return False


def _parse_symbol_override_pairs(raw: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for pair in re.split(r"[;\n]", raw):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        names = [item.strip() for item in value.split("|") if item.strip()]
        if key.strip() and names:
            out[key.strip()] = names
    return out


def _candidate_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(_dedupe([item.strip() for item in re.split(r"[|,]", value) if item.strip()]))
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return tuple(_dedupe([str(item).strip() for item in value if str(item).strip()]))
    return ()


def _symbol_name(row: Any) -> str:
    if row is None:
        return ""
    if isinstance(row, str):
        return row
    if isinstance(row, Mapping):
        return str(row.get("name") or row.get("symbol") or "")
    return str(getattr(row, "name", "") or getattr(row, "symbol", "") or "")


def _dedupe(values: Sequence[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def default_mid(symbol: str) -> float:
    return get_instrument(symbol).default_mid


def round_price(symbol: str, price: float) -> float:
    return round(price, get_instrument(symbol).price_precision)


def pip_value_per_lot(symbol: str, price: float) -> float:
    """USD value of one movement unit for one lot."""
    spec = get_instrument(symbol)
    if spec.point_value_per_lot is not None:
        return spec.point_value_per_lot
    if symbol.endswith("/USD"):
        return spec.contract_size * spec.price_unit
    if symbol.startswith("USD/"):
        return (spec.contract_size * spec.price_unit) / max(price, 1e-9)
    return spec.contract_size * spec.price_unit


def usd_notional(symbol: str, price: float, lots: float) -> float:
    """Approximate USD notional for margin/risk accounting."""
    spec = get_instrument(symbol)
    units = spec.contract_size * lots
    if spec.asset_class != "FX":
        return units * price
    if symbol.startswith("USD/"):
        return units
    if symbol.endswith("/USD"):
        return units * price
    return units * price
