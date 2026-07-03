"""Instrument metadata for CAS Forex.

The first CAS Forex build treated every symbol as an FX pair and measured all
price movement in "pips." Indices and gold need explicit point/tick economics,
so this module centralizes the conversion while keeping the old pip-facing API
available for existing code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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


def get_instrument(symbol: str) -> InstrumentSpec:
    try:
        return INSTRUMENT_SPECS[symbol]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported symbol '{symbol}'. Supported: {sorted(SUPPORTED_SYMBOLS)}"
        ) from exc


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
