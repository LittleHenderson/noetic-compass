"""Nested lacunarity across timeframes - the bias-state MAP (CAS Forex piece b).

WHAT THIS IS (and is NOT)
-------------------------
This module MEASURES. It does not trade, size, tune, or grant live permission and
it cannot manufacture directional edge. It fills a grid of cells

    cell = (symbol x TIMEFRAME x regime)

with one MEASURED verdict per cell, answering exactly one question:

    "Does ANY strategy in the menu clear the leak-free OOS null in this
     (symbol x timeframe x regime) pocket, or is this a lacuna (a gap)?"

The gap/non-gap verdict is produced by ``cas_forex.edge_oos.evaluate_oos`` USED
UNCHANGED, so the anti-leakage of that harness (routing learned on train only,
per-bar causal switching on test, random-routing null, cost sweep, buy-hold) is
inherited verbatim. We add only a CAUSAL regime restriction on top of the same
``detect_regime`` the harness already trusts - restricting to one regime adds NO
future information.

Then lacunarity (the gap fraction) is rolled up the nesting

    timeframe  ->  regime  ->  symbol

using ``regime_sim.lacunarity`` as the single source of truth for every fraction.

HONEST EXPECTATION
------------------
This session established that the strategy layer has NO out-of-sample edge: every
strategy is a fixed function of trailing price, and switching/tuning cannot create
skill. So with price-only signals the honest, expected outcome is:

    overall_gap_fraction == 1.0      (every cell is a gap)
    non_gap_cells        == []
    fractal_coherent     == []
    bias_state_verdict   == "ALL_GAPS ..."

The module REPORTS that truthfully. An all-gaps map IS the bias-state; it is never
massaged toward a non-gap. If a real signal with genuine OOS price-skill or
genuinely new information were ever introduced, this same map would show - without
special-casing - exactly where it does and does not survive the leak-free null.

THE CARDINAL-SIN GUARD (anti-lookahead, multi-timeframe)
--------------------------------------------------------
The one place multi-timeframe leakage can enter is mixing a higher-TF bar that is
still FORMING (not yet closed) at lower-TF decision time into the lower-TF
decision. ``TimeframeAlignedView`` makes that structurally impossible: it exposes
ONLY ``closed_higher_bars(decision_time)`` which returns bars with
``close_time <= decision_time`` via ``bisect_right`` on a presorted close-time
array. There is no public method that returns a still-forming bar; the lower-TF
code never holds the raw higher-TF list. The default per-cell path is single-TF
and thus leak-free by construction; the aligned view is the mandatory gateway for
any future cross-TF extension and is locked in by a dedicated regression test.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Sequence

from cas_forex.condition_lab import (
    normalize_timeframe,
    time_scale_for_timeframe,
    timeframe_bar_days,
    timeframe_vol_scale,
)
from cas_forex.edge_oos import (
    DEFAULT_DETECT_WINDOW,
    EDGE_CLAIM_BOUNDARY,
    build_sub_signals,
    evaluate_oos,
)
from cas_forex.edge_oos import _detect_kwargs as _edge_detect_kwargs
from cas_forex.regime_sim import (
    REGIMES,
    detect_regime,
    generate_regime_candles,
    lacunarity,
)

# ---------------------------------------------------------------------------
# Cell + report dataclasses
# ---------------------------------------------------------------------------


@dataclass
class TFCellResult:
    """One (symbol x timeframe x regime) cell's MEASURED gap verdict."""

    symbol: str
    timeframe: str          # canonical, e.g. 'D1'
    time_scale: str         # 'minute'|'hour'|'day'|... from time_scale_for_timeframe
    regime: str             # one of regime_sim.REGIMES
    is_gap: bool
    verdict: str            # 'CANDIDATE_EDGE'|'NO_EDGE'|'NO_DATA'
    cost_pips_tested: float
    oos_windows: int
    oos_trades: int
    switch_total_return_pct: float
    best_single_total_return_pct: float
    null_total_return_pct: float
    beats_single_window_rate: float
    beats_null_window_rate: float
    regime_detected_bars: int
    gap_reason: str
    claim_boundary: str = EDGE_CLAIM_BOUNDARY


@dataclass
class NestedLacunarityReport:
    """The full bias-state map payload."""

    cells: List[TFCellResult]
    gap_fraction_per_level: Dict[str, float]
    non_gap_cells: List[TFCellResult]
    fractal_coherent_cells: List[Dict[str, Any]]
    summary: Dict[str, Any]
    claim_boundary: str = EDGE_CLAIM_BOUNDARY


# ---------------------------------------------------------------------------
# Anti-lookahead TF-alignment guard (the cardinal-sin guard)
# ---------------------------------------------------------------------------


def _parse_timestamp(value: Any) -> datetime:
    """Parse a candle timestamp (ISO string or datetime) into a datetime.

    The repo's synthetic candles use 'YYYY-MM-DDTHH:MM:SS'; real (yfinance)
    candles use ISO-8601 with offset. Both are accepted.
    """
    if isinstance(value, datetime):
        return value
    s = str(value)
    # datetime.fromisoformat handles offsets on 3.11+; fall back gracefully.
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        # Trim a trailing 'Z' (UTC) if present, then retry.
        if s.endswith("Z"):
            return datetime.fromisoformat(s[:-1])
        raise


def timeframe_duration(timeframe: str) -> timedelta:
    """Real wall-clock duration of one bar of ``timeframe`` (a timedelta).

    Derived from ``condition_lab.timeframe_bar_days`` (trading-day length) scaled
    to seconds. Used to compute a bar's CLOSE time = open_time + duration. This is
    the same notion of bar length the synthetic grid advances timestamps by, so
    close-times are well-ordered across timeframes.
    """
    days = timeframe_bar_days(timeframe)
    return timedelta(seconds=days * 86_400.0)


class TimeframeAlignedView:
    """Leak-free view of a higher-timeframe series for lower-TF decisions.

    A higher-TF bar is identified in this repo by its OPEN time (the candle's
    ``timestamp``). The bar is only CLOSED at ``open_time + tf_duration``. This
    view stores, per higher-TF bar, ``close_time = open_time + duration`` in a
    SORTED array, and exposes ONLY :meth:`closed_higher_bars`, which returns the
    bars whose ``close_time <= lower_decision_time`` (found via ``bisect_right``).

    A still-forming higher-TF bar (``close_time > decision_time``) is UNREACHABLE
    through this API: there is no method that returns it, and the raw higher-TF
    list is held under a name-mangled private attribute, never exposed. This makes
    mixing a forming higher-TF bar into a lower-TF decision structurally
    impossible, not merely discouraged.
    """

    def __init__(self, higher_tf: str, higher_candles: Sequence[dict]) -> None:
        self.higher_tf = normalize_timeframe(higher_tf)
        duration = timeframe_duration(self.higher_tf)
        # Build (close_time, bar) pairs sorted by close_time. The raw list and the
        # close-time index are PRIVATE (name-mangled) - the only public read path
        # is closed_higher_bars(), which always filters to closed bars.
        pairs = []
        for bar in higher_candles:
            open_time = _parse_timestamp(bar.get("timestamp"))
            close_time = open_time + duration
            pairs.append((close_time, bar))
        pairs.sort(key=lambda p: p[0])
        self.__close_times: List[datetime] = [p[0] for p in pairs]
        self.__bars: List[dict] = [p[1] for p in pairs]

    @staticmethod
    def bar_close_time(open_timestamp: Any, timeframe: str) -> datetime:
        """Close time of a bar = its open time + the timeframe's real duration."""
        return _parse_timestamp(open_timestamp) + timeframe_duration(timeframe)

    def closed_higher_bars(self, lower_decision_time: datetime) -> List[dict]:
        """Higher-TF bars CLOSED at or before ``lower_decision_time``.

        Strict-closed boundary: a higher-TF bar that closes EXACTLY at the
        decision instant is included (it is closed); one that closes any later is
        excluded (it is still forming). Implemented with ``bisect_right`` on the
        presorted close-time array - O(log n), and structurally unable to return a
        forming bar because forming bars sit beyond the bisect cut.
        """
        if not isinstance(lower_decision_time, datetime):
            lower_decision_time = _parse_timestamp(lower_decision_time)
        cut = bisect.bisect_right(self.__close_times, lower_decision_time)
        return list(self.__bars[:cut])


# ---------------------------------------------------------------------------
# Causal regime gating of sub-signals
# ---------------------------------------------------------------------------


def make_regime_gated_sub_signals(
    sub_signals: Dict[str, Callable],
    cell_regime: str,
    *,
    detect_window: int = DEFAULT_DETECT_WINDOW,
) -> Dict[str, Callable]:
    """Wrap each sub-signal so it only fires when the CAUSALLY detected regime
    (from trailing closes only) equals ``cell_regime``; otherwise it sits out.

    The detector is ``regime_sim.detect_regime(closes[:t+1], window=detect_window,
    **_detect_kwargs)`` - exactly the causal detector ``edge_oos`` already trusts.
    Restricting to one regime adds NO future information: the gate reads only the
    closes the harness already hands the signal (which the backtest engine builds
    as ``candles[:i+1]`` - trailing only). No future or whole-segment label is
    ever consulted.
    """
    detect_kwargs = _edge_detect_kwargs(detect_window)

    def _gate(fn: Callable) -> Callable:
        def gated(closes: List[float]):
            # ANTI-LEAKAGE: the gate sees only trailing closes. The engine passes
            # closes ending at the current bar; we never index forward.
            if len(closes) < detect_window:
                return None
            regime = detect_regime(closes, window=detect_window, **detect_kwargs)
            if regime != cell_regime:
                return None
            return fn(closes)

        return gated

    return {name: _gate(fn) for name, fn in sub_signals.items()}


def _causal_regime_detected_bars(
    candles: Sequence[dict],
    cell_regime: str,
    *,
    detect_window: int,
) -> int:
    """Count bars whose CAUSAL detected regime == cell_regime (trailing closes).

    This is the same trailing-closes-only scan ``edge_oos`` uses to count train
    regimes; here it gives the honest ``min_regime_bars`` gate for a cell. No
    future label is used: ``detect_regime(closes[:i+1])`` only.
    """
    closes = [float(c["close"]) for c in candles]
    detect_kwargs = _edge_detect_kwargs(detect_window)
    count = 0
    for i in range(detect_window, len(closes)):
        # closes[: i + 1] is strictly trailing - ends at the current bar i.
        if detect_regime(closes[: i + 1], window=detect_window, **detect_kwargs) == cell_regime:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Per-cell OOS decision (gap vs non-gap), leak-free
# ---------------------------------------------------------------------------


def evaluate_cell_oos(
    symbol: str,
    candles: Sequence[dict],
    regime: str,
    timeframe: str,
    *,
    costs: Sequence[float] = (1.0, 2.0, 3.0),
    train_bars: int = 504,
    test_bars: int = 126,
    detect_window: int = DEFAULT_DETECT_WINDOW,
    n_null: int = 20,
    min_cell_trades: int = 30,
    min_regime_bars: int = 20,
    sub_signals: Optional[Dict[str, Callable]] = None,
) -> TFCellResult:
    """Decide gap/non-gap for one (symbol, timeframe, regime) cell, leak-free.

    The decision reuses ``edge_oos.evaluate_oos`` UNCHANGED, with the strategy
    menu REGIME-GATED causally (``make_regime_gated_sub_signals``) so the per-bar
    switcher only trades when the causally detected regime equals ``cell_regime``,
    sitting out otherwise. A cell is NON-GAP iff ALL of:

      * verdict == "CANDIDATE_EDGE" at the STRICTEST (highest) cost in the sweep,
      * total_oos_trades >= min_cell_trades,
      * the regime actually occurred enough (causal detected bars >= min_regime_bars).

    Otherwise GAP, with a precise ``gap_reason``. NO_DATA (too few windows) -> GAP
    with reason "insufficient_history". This upgrades the old single-in-sample
    ``regime_sim.cell_is_gap`` test to the full leak-free OOS null.
    """
    canonical_tf = normalize_timeframe(timeframe)
    time_scale = time_scale_for_timeframe(canonical_tf)
    base_menu = sub_signals or build_sub_signals()

    # Honest min_regime_bars gate (causal): does this regime even occur enough?
    regime_bars = _causal_regime_detected_bars(
        candles, regime, detect_window=detect_window
    )

    # Strictest cost is the honesty floor: an edge that dies at higher cost is a
    # gap. Evaluate the verdict at the strictest cost; we also record it.
    strictest_cost = float(max(costs)) if costs else 0.0

    gated_menu = make_regime_gated_sub_signals(
        base_menu, regime, detect_window=detect_window
    )

    report = evaluate_oos(
        {symbol: list(candles)},
        cost_pips=strictest_cost,
        train_bars=train_bars,
        test_bars=test_bars,
        detect_window=detect_window,
        n_null=n_null,
        sub_signals=gated_menu,
    )
    s = report.summary
    verdict = str(s.get("verdict", "NO_DATA"))
    oos_windows = int(s.get("windows", 0) or 0)
    oos_trades = int(s.get("total_oos_trades", 0) or 0)

    # Decide gap/non-gap with a precise reason. STRICT: a cell is non-gap only
    # when the leak-free null is cleared AND the sample is adequate AND the regime
    # genuinely occurred. Everything else is an honest gap.
    is_gap = True
    gap_reason = ""
    if verdict == "NO_DATA":
        gap_reason = "insufficient_history"
    elif regime_bars < min_regime_bars:
        gap_reason = "insufficient_regime_bars"
    elif oos_trades < min_cell_trades:
        gap_reason = "insufficient_trades"
    elif verdict != "CANDIDATE_EDGE":
        gap_reason = "no_oos_edge"
    else:
        # Cleared the leak-free null at the strictest cost with an adequate sample
        # and the regime actually occurred - the only path to NON-GAP.
        is_gap = False
        gap_reason = ""

    return TFCellResult(
        symbol=symbol,
        timeframe=canonical_tf,
        time_scale=time_scale,
        regime=regime,
        is_gap=is_gap,
        verdict=verdict,
        cost_pips_tested=strictest_cost,
        oos_windows=oos_windows,
        oos_trades=oos_trades,
        switch_total_return_pct=float(s.get("switch_total_return_pct", 0.0) or 0.0),
        best_single_total_return_pct=float(s.get("best_single_total_return_pct", 0.0) or 0.0),
        null_total_return_pct=float(s.get("null_total_return_pct", 0.0) or 0.0),
        beats_single_window_rate=float(s.get("beats_single_window_rate", 0.0) or 0.0),
        beats_null_window_rate=float(s.get("beats_null_window_rate", 0.0) or 0.0),
        regime_detected_bars=regime_bars,
        gap_reason=gap_reason,
    )


# ---------------------------------------------------------------------------
# Nesting / roll-up: timeframe -> regime -> symbol
# ---------------------------------------------------------------------------


def nested_lacunarity_tf(cells: Sequence[TFCellResult]) -> Dict[str, float]:
    """Gap-fractions rolled up the nesting timeframe -> regime -> symbol.

    Keys:
      * "overall"                                       - all cells
      * "symbol::{s}"                                   - per symbol
      * "symbol::{s}::regime::{r}"                      - per symbol x regime
      * "symbol::{s}::regime::{r}::tf::{tf}"  (leaf)    - innermost nest
      * "tf::{tf}"                            (marginal)- per timeframe across all

    Every fraction is computed by ``regime_sim.lacunarity`` (the single source of
    truth: sum(is_gap)/n). The marginal ``tf::{tf}`` answers "is the gap worse at
    fast or slow timeframes?".
    """
    cells = list(cells)
    out: Dict[str, float] = {"overall": lacunarity(cells)}

    symbols = sorted({c.symbol for c in cells})
    regimes = sorted({c.regime for c in cells})
    timeframes = sorted({c.timeframe for c in cells})

    for s in symbols:
        s_cells = [c for c in cells if c.symbol == s]
        out[f"symbol::{s}"] = lacunarity(s_cells)
        for r in regimes:
            sr_cells = [c for c in s_cells if c.regime == r]
            if not sr_cells:
                continue
            out[f"symbol::{s}::regime::{r}"] = lacunarity(sr_cells)
            for tf in timeframes:
                leaf = [c for c in sr_cells if c.timeframe == tf]
                if leaf:
                    out[f"symbol::{s}::regime::{r}::tf::{tf}"] = lacunarity(leaf)

    # Marginal gap-fraction per timeframe across all symbols/regimes.
    for tf in timeframes:
        tf_cells = [c for c in cells if c.timeframe == tf]
        if tf_cells:
            out[f"tf::{tf}"] = lacunarity(tf_cells)

    return out


def find_fractal_coherent_cells(
    cells: Sequence[TFCellResult],
    *,
    min_timeframes: int = 2,
) -> List[Dict[str, Any]]:
    """(symbol, regime) pairs that are NON-GAP at >= ``min_timeframes`` distinct TFs.

    These are the robust pockets: an edge that survives the leak-free null at
    multiple scales is far less likely to be a single-scale fluke. Each entry
    lists which timeframes cleared. Expected EMPTY for price-only signals - and
    that emptiness is the honest headline.
    """
    by_pair: Dict[tuple, set] = {}
    for c in cells:
        if c.is_gap:
            continue
        by_pair.setdefault((c.symbol, c.regime), set()).add(c.timeframe)

    out: List[Dict[str, Any]] = []
    for (symbol, regime), tfs in sorted(by_pair.items()):
        if len(tfs) >= min_timeframes:
            out.append(
                {
                    "symbol": symbol,
                    "regime": regime,
                    "timeframes": sorted(tfs),
                    "n_timeframes": len(tfs),
                }
            )
    return out


def _summarize_map(
    cells: Sequence[TFCellResult],
    levels: Dict[str, float],
    fractal_coherent: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    cells = list(cells)
    total = len(cells)
    gap_cells = sum(1 for c in cells if c.is_gap)
    non_gap = total - gap_cells
    overall = levels.get("overall", lacunarity(cells))

    # Worst/best timeframe by marginal gap-fraction.
    tf_marginals = {
        k[len("tf::"):]: v for k, v in levels.items() if k.startswith("tf::")
    }
    worst_tf = max(tf_marginals, key=tf_marginals.get) if tf_marginals else None
    best_tf = min(tf_marginals, key=tf_marginals.get) if tf_marginals else None

    if total == 0:
        bias_state = "NO_DATA - no cells evaluated"
    elif overall >= 1.0:
        bias_state = (
            "ALL_GAPS - no measured edge anywhere "
            "(honest expected result for price-only signals)"
        )
    else:
        bias_state = (
            "PARTIAL_COVERAGE - see non_gap_cells "
            "(research candidates only, NOT live permission)"
        )

    return {
        "total_cells": total,
        "gap_cells": gap_cells,
        "non_gap_cells": non_gap,
        "fractal_coherent_count": len(fractal_coherent),
        "overall_gap_fraction": round(float(overall), 6),
        "worst_timeframe_by_gap_fraction": worst_tf,
        "best_timeframe_by_gap_fraction": best_tf,
        "timeframe_marginal_gap_fraction": {
            tf: round(float(v), 6) for tf, v in sorted(tf_marginals.items())
        },
        "bias_state_verdict": bias_state,
        "claim_boundary": EDGE_CLAIM_BOUNDARY,
    }


# ---------------------------------------------------------------------------
# Full gap-map build
# ---------------------------------------------------------------------------


def build_gap_map(
    candles_by_symbol_tf: Dict[str, Dict[str, List[dict]]],
    *,
    regimes: Sequence[str] = tuple(REGIMES),
    costs: Sequence[float] = (1.0, 2.0, 3.0),
    train_bars: int = 504,
    test_bars: int = 126,
    detect_window: int = DEFAULT_DETECT_WINDOW,
    n_null: int = 20,
    min_cell_trades: int = 30,
    min_regime_bars: int = 20,
    min_coherent_timeframes: int = 2,
) -> NestedLacunarityReport:
    """Build the bias-state map over cells=(symbol x timeframe x regime).

    For each (symbol, timeframe) series and each regime, decide gap/non-gap via
    the leak-free ``evaluate_cell_oos``; roll up nested lacunarity
    (timeframe -> regime -> symbol); surface the non-gap cells and the
    fractal-coherent (symbol, regime) pairs. With price-only signals the honest
    expectation - reported, never massaged - is overall_gap_fraction == 1.0 and
    empty non_gap / fractal_coherent lists.
    """
    cells: List[TFCellResult] = []
    for symbol, tf_map in candles_by_symbol_tf.items():
        for timeframe, candles in tf_map.items():
            for regime in regimes:
                cells.append(
                    evaluate_cell_oos(
                        symbol,
                        candles,
                        regime,
                        timeframe,
                        costs=costs,
                        train_bars=train_bars,
                        test_bars=test_bars,
                        detect_window=detect_window,
                        n_null=n_null,
                        min_cell_trades=min_cell_trades,
                        min_regime_bars=min_regime_bars,
                    )
                )

    levels = nested_lacunarity_tf(cells)
    non_gap_cells = [c for c in cells if not c.is_gap]
    fractal_coherent = find_fractal_coherent_cells(
        cells, min_timeframes=min_coherent_timeframes
    )
    summary = _summarize_map(cells, levels, fractal_coherent)

    # HONESTY INVARIANT: a non-gap claim must be backed by a real non-gap cell.
    # This module never invents coverage; if everything is a gap, that is the
    # truthful bias-state and these lists stay empty.
    assert summary["non_gap_cells"] == len(non_gap_cells)
    assert (summary["overall_gap_fraction"] >= 1.0) == (len(non_gap_cells) == 0)

    return NestedLacunarityReport(
        cells=cells,
        gap_fraction_per_level=levels,
        non_gap_cells=non_gap_cells,
        fractal_coherent_cells=fractal_coherent,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Synthetic grid (no network) for tests / offline runs
# ---------------------------------------------------------------------------


def build_synthetic_grid(
    symbols: Sequence[str],
    timeframes: Sequence[str],
    regimes: Sequence[str],
    *,
    bars_per_regime: int = 220,
    seed_base: int = 0,
) -> Dict[str, Dict[str, List[dict]]]:
    """Deterministic multi-regime synthetic grid. No network.

    For each (symbol, timeframe), concatenate seeded blocks of several regimes so
    the causal detector sees regime transitions (which makes the per-cell regime
    filter meaningful). Per-TF volatility is scaled by ``timeframe_vol_scale(tf)``
    (the exact pattern used in condition_lab), and synthetic timestamps ADVANCE by
    the timeframe's real duration so ``TimeframeAlignedView`` has correct,
    well-ordered close-times across timeframes.
    """
    grid: Dict[str, Dict[str, List[dict]]] = {}
    for si, symbol in enumerate(symbols):
        grid[symbol] = {}
        for ti, timeframe in enumerate(timeframes):
            canonical_tf = normalize_timeframe(timeframe)
            tf_scale = timeframe_vol_scale(canonical_tf)
            duration = timeframe_duration(canonical_tf)
            # Anchor each timeframe at a stable epoch start, then advance by the
            # bar's real duration so close-times are monotone and comparable.
            t = datetime(2020, 1, 1, 0, 0, 0)
            series: List[dict] = []
            base_price: Optional[float] = None
            for ri, regime in enumerate(regimes):
                seed = (
                    seed_base
                    + si * 1_000_003
                    + ti * 10_007
                    + ri * 101
                )
                block = generate_regime_candles(
                    regime,
                    symbol=symbol,
                    bars=bars_per_regime,
                    seed=seed,
                    vol_mult=tf_scale,
                    base=base_price,
                )
                for bar in block:
                    series.append(
                        {
                            "timestamp": t.isoformat(),
                            "open": bar["open"],
                            "high": bar["high"],
                            "low": bar["low"],
                            "close": bar["close"],
                            "volume": bar["volume"],
                        }
                    )
                    t = t + duration
                # Continue the next regime from the last close for continuity.
                if series:
                    base_price = float(series[-1]["close"])
            grid[symbol][canonical_tf] = series
    return grid


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def serialize_cell(cell: TFCellResult) -> Dict[str, Any]:
    return dict(cell.__dict__)


def serialize_nested_lacunarity_report(report: NestedLacunarityReport) -> Dict[str, Any]:
    """JSON-serializable view of the full bias-state map."""
    return {
        "cells": [serialize_cell(c) for c in report.cells],
        "gap_fraction_per_level": dict(report.gap_fraction_per_level),
        "non_gap_cells": [serialize_cell(c) for c in report.non_gap_cells],
        "fractal_coherent_cells": [dict(d) for d in report.fractal_coherent_cells],
        "summary": dict(report.summary),
        "claim_boundary": report.claim_boundary,
    }
