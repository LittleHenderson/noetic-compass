"""Money management for CAS Forex — position sizing + breakeven principal-lock.

This module is the AMPLIFY layer of the adaptive loop. It does NOT create an
edge and it does NOT decide direction. Given an already-authorized setup (a
PASS edge token decided upstream in STRATEGIZE/TEST), it answers two honest
money questions:

  1. How many lots express a fixed dollar risk for THIS instrument's economics?
     (``position_size`` / ``expected_loss_usd``)
  2. When is the floating profit large enough that we can move the stop to the
     entry price and guarantee we cannot lose principal on the trade?
     (``breakeven_lock``)

Mathematical honesty (non-negotiable):

  * Position sizing converts a *risk budget* into lots. Risking more on a
    zero-or-negative-expectancy signal still loses money in expectation —
    sizing changes the variance and the bet size, never the sign of the edge.
  * The breakeven lock protects principal and caps downside on a trade that has
    already run in our favour. It does NOT add expectancy: moving the stop to
    breakeven can only reduce the trade's remaining upside-vs-downside, it can
    never manufacture a positive edge that the entry did not have.

Both functions are pure and standalone. They use the real instrument economics
in :mod:`cas_forex.instruments` so an FX pair, an index CFD and gold are all
sized correctly off the same call.
"""

from __future__ import annotations

from cas_forex.instruments import (
    get_instrument,
    pip_value_per_lot,
    price_unit_size,
)

__all__ = [
    "value_per_price_unit_per_lot",
    "position_size",
    "expected_loss_usd",
    "breakeven_lock",
]


def _price_distance(symbol: str, a: float, b: float) -> float:
    """Absolute price distance, quantised to the instrument's price precision.

    Raw float subtraction of broker prices (e.g. 1.1050 - 1.1000) carries IEEE
    representational noise that can make a clean 50-pip stop read as 49.99999...
    pips. Rounding the distance to the symbol's quoted precision removes that
    noise so sizing and the R-multiple trigger use the price the broker shows.
    """

    precision = get_instrument(symbol).price_precision
    return round(abs(float(a) - float(b)), precision)


def value_per_price_unit_per_lot(symbol: str, price: float) -> float:
    """USD value of a 1.0 price-unit move (e.g. 1.00 on an index, 1.0 in price
    terms on EUR/USD) for one standard lot of ``symbol``.

    ``pip_value_per_lot`` returns the value of one *movement unit* (a pip for
    FX, a point for an index, a dollar-point for gold). Dividing by the size of
    that movement unit in raw price terms (``price_unit_size``) normalises every
    instrument to "USD per 1.0 of raw price per lot", which is what stop
    distances measured in raw price need.
    """

    unit = price_unit_size(symbol)
    if unit <= 0:
        raise ValueError(f"Non-positive price unit for symbol {symbol!r}: {unit}")
    return pip_value_per_lot(symbol, price) / unit


def position_size(
    equity: float,
    risk_budget_usd: float,
    entry: float,
    stop_loss: float,
    symbol: str,
    *,
    max_lots: float = 100.0,
    min_lots: float = 0.0,
    lot_step: float = 0.01,
) -> float:
    """Lots that express ``risk_budget_usd`` of loss if price hits ``stop_loss``.

    ``lots = risk_budget_usd / (stop_distance_in_raw_price * value_per_raw_price_unit_per_lot)``

    The result is rounded down to ``lot_step`` (so realised risk never exceeds
    the budget), clamped to ``[min_lots, max_lots]`` and never negative. A zero
    stop distance, non-positive risk budget or non-positive equity yields
    ``0.0`` — there is no honest lot size for those inputs.

    ``equity`` is accepted so callers can pass account state directly and so the
    function can refuse to size when there is no capital; sizing itself is driven
    by the explicit ``risk_budget_usd`` (the caller's risk gate owns the policy
    of how that budget relates to equity).
    """

    if equity <= 0 or risk_budget_usd <= 0:
        return 0.0

    stop_distance = _price_distance(symbol, entry, stop_loss)
    if stop_distance <= 0:
        return 0.0

    value_per_unit = value_per_price_unit_per_lot(symbol, float(entry))
    if value_per_unit <= 0:
        return 0.0

    risk_per_lot = stop_distance * value_per_unit
    if risk_per_lot <= 0:
        return 0.0

    raw_lots = risk_budget_usd / risk_per_lot

    if lot_step > 0:
        # Floor to the step so the realised dollar risk stays at or under budget.
        steps = int(raw_lots / lot_step)
        lots = steps * lot_step
    else:
        lots = raw_lots

    lots = max(min_lots, min(lots, max_lots))
    if lots < 0:
        lots = 0.0
    return round(lots, 4)


def expected_loss_usd(
    lots: float,
    entry: float,
    stop_loss: float,
    symbol: str,
) -> float:
    """USD loss realised if ``lots`` of ``symbol`` are stopped out at ``stop_loss``.

    This is the truth the risk gate must see: it is the realised dollar risk of
    the sized position, independent of the requested budget (rounding to a lot
    step makes the two differ). Always non-negative.
    """

    if lots <= 0:
        return 0.0
    stop_distance = _price_distance(symbol, entry, stop_loss)
    if stop_distance <= 0:
        return 0.0
    value_per_unit = value_per_price_unit_per_lot(symbol, float(entry))
    return round(stop_distance * value_per_unit * float(lots), 2)


def breakeven_lock(
    entry: float,
    current: float,
    direction: str,
    stop_loss: float,
    *,
    lock_trigger_r: float = 1.0,
) -> float | None:
    """Move the stop to the entry price once the trade is up ``lock_trigger_r`` R.

    Initial risk R is ``|entry - stop_loss|``. Once floating profit (in raw
    price, in the trade's favour) reaches ``lock_trigger_r * R``, this returns a
    new stop equal to ``entry`` — i.e. "close at the initial principal", the
    trade can no longer lose money. Before that threshold (or if the trade is
    under water) it returns ``None`` and the original stop should stand.

    HONESTY: this protects principal and caps downside on a trade that has
    already moved in our favour. It does NOT add expectancy — a breakeven stop
    can only remove downside that already existed; it cannot create a positive
    edge the entry did not have.

    Direction is ``'LONG'`` or ``'SHORT'`` (case-insensitive; ``BUY``/``SELL``
    accepted). An unknown direction or a non-positive initial risk yields
    ``None`` — there is nothing to honestly lock.
    """

    initial_risk = abs(float(entry) - float(stop_loss))
    if initial_risk <= 0:
        return None
    trigger = lock_trigger_r * initial_risk

    side = str(direction).strip().upper()
    if side in {"LONG", "BUY"}:
        floating_profit = float(current) - float(entry)
    elif side in {"SHORT", "SELL"}:
        floating_profit = float(entry) - float(current)
    else:
        return None

    # Relative epsilon absorbs IEEE float noise in price subtraction so that a
    # trade exactly at +NR locks rather than reading as a hair short of it.
    tol = 1e-9 * max(1.0, abs(float(entry)))
    if floating_profit >= trigger - tol:
        return float(entry)
    return None
