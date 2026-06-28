"""Leak-free out-of-sample test of regime-switching: is there an edge?

This is the honest measurement the prior work was missing. The earlier
``run_switching_backtest.py`` routed with a HAND-SET map (``DEFAULT_ROUTING``,
seeded from a synthetic sim) applied IN-SAMPLE to the same real data it scored,
and the walk-forward harness labeled each test window's regime from the WHOLE
(future) test segment. Both leak.

Here every decision is causal and out-of-sample:

  * Routing (which strategy trades which regime) is LEARNED ON THE TRAIN WINDOW
    ONLY, by measuring each strategy's train return when routed into each
    detected regime, and keeping it only if it is net-positive after cost.
  * The TEST window is driven by the per-bar switcher (``make_regime_switching_signal``),
    which detects the regime from trailing closes only and routes per bar -- the
    same thing that would trade live. Trades begin only inside the test window
    (the train tail is warmup context).
  * Costs default to a realistic 2.0 points all-in (1 pip == 1 index point for
    index CFDs); we also report a cost sweep, because an edge that dies at 2.0p
    is not an edge.
  * SWITCH is compared against the best single strategy (also chosen on train),
    a RANDOM-ROUTING null (shuffled regime->strategy, repeated), and buy-hold.

The verdict is honest: if switching does not beat those baselines out-of-sample
after realistic cost with an adequate sample, it reports NO EDGE. A passing
result is a research candidate, never live permission.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

from cas_forex.backtest.engine import BacktestEngine
from cas_forex.forecast.strategies import (
    make_donchian_breakout_signal,
    make_low_vol_range_scalper_signal,
    make_mean_reversion_signal,
    make_sma_trend_signal,
    make_time_series_momentum_signal,
    make_trend_pullback_signal,
)
from cas_forex.regime_sim import REGIMES, detect_regime, make_regime_switching_signal
from cas_forex.walk_forward import split_walk_forward_ranges

# Realistic all-in round-trip cost. For index CFDs (US30/NAS100) the engine's
# "pip" is 1 index point, so this is ~2 points; for FX majors ~2 pips. This is
# the honesty floor -- the prior 1.0-1.5p defaults flattered every result.
DEFAULT_COST_PIPS = 2.0
DEFAULT_DETECT_WINDOW = 60
EDGE_CLAIM_BOUNDARY = (
    "Out-of-sample research result only. A positive result is a candidate edge "
    "to be re-tested on broker-grade data; live trading remains NOT LICENSED."
)


def build_sub_signals() -> Dict[str, Callable]:
    """The strategy menu the regime switch selects among (all causal)."""
    return {
        "breakout": make_donchian_breakout_signal(),
        "tsmom": make_time_series_momentum_signal(),
        "pullback": make_trend_pullback_signal(),
        "trend_sma": make_sma_trend_signal(),
        "meanrev": make_mean_reversion_signal(),
        "meanrev_tf": make_mean_reversion_signal(trend_filter=True),
        "range_scalper": make_low_vol_range_scalper_signal(),
    }


def _split_cost(cost_pips: float) -> tuple[float, float]:
    spread = min(cost_pips, 1.0)
    return spread, max(cost_pips - spread, 0.0)


def _run(
    candles: Sequence[dict],
    symbol: str,
    signal_fn: Callable,
    *,
    cost_pips: float,
    starting: float = 10_000.0,
    lots: float = 0.05,
    warmup: int = DEFAULT_DETECT_WINDOW,
) -> Dict[str, float]:
    """Run one signal through the backtest engine; return % metrics on equity."""
    spread, extra = _split_cost(cost_pips)
    engine = BacktestEngine(
        initial_balance=starting,
        position_size_lots=lots,
        spread_pips=spread,
        extra_cost_pips=extra,
        signal_fn=signal_fn,
    )
    result = engine.run(list(candles), symbol=symbol, warmup_bars=warmup)
    return {
        "return_pct": float(result.total_profit_account) / starting * 100.0,
        "max_dd_pct": float(result.max_drawdown_pct),
        "trades": int(result.total_trades),
        "pnl": float(result.total_profit_account),
    }


def _detect_kwargs(detect_window: int) -> Dict[str, Any]:
    return {"baseline": max(detect_window * 3, 180)}


def _train_regime_counts(train: Sequence[dict], detect_window: int) -> Dict[str, int]:
    closes = [float(c["close"]) for c in train]
    counts: Dict[str, int] = {}
    for i in range(detect_window, len(closes)):
        regime = detect_regime(closes[: i + 1], window=detect_window, **_detect_kwargs(detect_window))
        counts[regime] = counts.get(regime, 0) + 1
    return counts


def learn_routing_on_train(
    train: Sequence[dict],
    symbol: str,
    sub_signals: Dict[str, Callable],
    *,
    cost_pips: float,
    detect_window: int = DEFAULT_DETECT_WINDOW,
    min_regime_bars: int = 20,
    min_trades: int = 3,
) -> tuple[Dict[str, Optional[str]], Dict[str, int]]:
    """Learn regime->strategy ON TRAIN ONLY.

    For each regime that occurs often enough in train, route ONLY that regime to
    each candidate strategy in turn, measure train return, and keep the best
    strategy if it is net-positive after cost (else sit out). No test data is
    touched here.
    """
    counts = _train_regime_counts(train, detect_window)
    routing: Dict[str, Optional[str]] = {}
    for regime in REGIMES:
        if counts.get(regime, 0) < min_regime_bars:
            routing[regime] = None
            continue
        best_name: Optional[str] = None
        best_ret = 0.0  # strictly require a positive train edge in this regime
        for name, _fn in sub_signals.items():
            sig = make_regime_switching_signal(
                sub_signals, routing={regime: name}, detect_window=detect_window,
                **_detect_kwargs(detect_window),
            )
            res = _run(train, symbol, sig, cost_pips=cost_pips, warmup=detect_window)
            if res["trades"] >= min_trades and res["return_pct"] > best_ret:
                best_ret, best_name = res["return_pct"], name
        routing[regime] = best_name
    return routing, counts


def _best_single_on_train(
    train: Sequence[dict],
    symbol: str,
    sub_signals: Dict[str, Callable],
    *,
    cost_pips: float,
    detect_window: int,
) -> Optional[str]:
    """Pick the single best standalone strategy on train (also OOS-honest)."""
    best_name: Optional[str] = None
    best_ret = -1e18
    for name, fn in sub_signals.items():
        res = _run(train, symbol, fn, cost_pips=cost_pips, warmup=detect_window)
        if res["return_pct"] > best_ret:
            best_ret, best_name = res["return_pct"], name
    return best_name


@dataclass
class EdgeOOSReport:
    cost_pips: float
    windows: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    claim_boundary: str = EDGE_CLAIM_BOUNDARY


def evaluate_oos(
    candles_by_symbol: Dict[str, List[dict]],
    *,
    cost_pips: float = DEFAULT_COST_PIPS,
    train_bars: int = 504,
    test_bars: int = 126,
    step_bars: Optional[int] = None,
    detect_window: int = DEFAULT_DETECT_WINDOW,
    n_null: int = 20,
    seed: int = 7,
    sub_signals: Optional[Dict[str, Callable]] = None,
) -> EdgeOOSReport:
    """Walk-forward, leak-free OOS test of regime-switching vs baselines.

    ``sub_signals`` overrides the strategy menu the switch selects among (default:
    the 7 primitives). Pass the full condition_lab setting grid to test whether
    any tuned/assembled variant has OOS edge.
    """
    sub_signals = sub_signals or build_sub_signals()
    rng = np.random.default_rng(seed)
    ctx_bars = max(detect_window * 3, 180)
    windows: List[Dict[str, Any]] = []

    for symbol, candles in candles_by_symbol.items():
        ranges = split_walk_forward_ranges(
            len(candles), train_bars=train_bars, test_bars=test_bars, step_bars=step_bars
        )
        for wi, (ts, te, vs, ve) in enumerate(ranges):
            train = candles[ts:te]
            test = candles[vs:ve]
            routing, train_counts = learn_routing_on_train(
                train, symbol, sub_signals, cost_pips=cost_pips, detect_window=detect_window
            )
            ctx = train[-ctx_bars:]
            eval_candles = list(ctx) + list(test)
            warmup = len(ctx)

            switch_sig = make_regime_switching_signal(
                sub_signals, routing=routing, detect_window=detect_window, **_detect_kwargs(detect_window)
            )
            switch = _run(eval_candles, symbol, switch_sig, cost_pips=cost_pips, warmup=warmup)

            best_single = _best_single_on_train(
                train, symbol, sub_signals, cost_pips=cost_pips, detect_window=detect_window
            )
            single = (
                _run(eval_candles, symbol, sub_signals[best_single], cost_pips=cost_pips, warmup=warmup)
                if best_single else {"return_pct": 0.0, "max_dd_pct": 0.0, "trades": 0, "pnl": 0.0}
            )

            # Random-routing null: shuffle the learned regime->strategy assignment.
            learned_strats = sorted({v for v in routing.values() if v})
            pool = learned_strats or sorted(sub_signals)
            null_returns: List[float] = []
            for _ in range(n_null):
                rnd = {
                    reg: (pool[int(rng.integers(len(pool)))] if strat else None)
                    for reg, strat in routing.items()
                }
                rnd_sig = make_regime_switching_signal(
                    sub_signals, routing=rnd, detect_window=detect_window, **_detect_kwargs(detect_window)
                )
                null_returns.append(_run(eval_candles, symbol, rnd_sig, cost_pips=cost_pips, warmup=warmup)["return_pct"])

            buy_hold_pct = (float(test[-1]["close"]) / float(test[0]["close"]) - 1.0) * 100.0
            null_p90 = float(np.percentile(null_returns, 90)) if null_returns else 0.0
            windows.append({
                "symbol": symbol,
                "window_index": wi,
                "test_start": test[0].get("timestamp"),
                "test_end": test[-1].get("timestamp"),
                "switch_return_pct": round(switch["return_pct"], 4),
                "switch_max_dd_pct": round(switch["max_dd_pct"], 4),
                "switch_trades": switch["trades"],
                "best_single_name": best_single,
                "best_single_return_pct": round(single["return_pct"], 4),
                "null_mean_return_pct": round(float(np.mean(null_returns)) if null_returns else 0.0, 4),
                "null_p90_return_pct": round(null_p90, 4),
                "buy_hold_pct": round(buy_hold_pct, 4),
                "routing": {k: v for k, v in routing.items() if v},
                "sit_out_regimes": sorted(k for k, v in routing.items() if not v),
                "beats_single": switch["return_pct"] > single["return_pct"],
                "beats_null_p90": switch["return_pct"] > null_p90,
            })

    report = EdgeOOSReport(cost_pips=cost_pips, windows=windows)
    report.summary = _summarize(windows, cost_pips)
    return report


def _summarize(windows: List[Dict[str, Any]], cost_pips: float) -> Dict[str, Any]:
    if not windows:
        return {"verdict": "NO_DATA", "windows": 0}
    n = len(windows)
    sw = [w["switch_return_pct"] for w in windows]
    total = float(sum(sw))
    mean = float(np.mean(sw))
    positive_rate = sum(1 for x in sw if x > 0) / n
    total_trades = int(sum(w["switch_trades"] for w in windows))
    max_dd = float(max((w["switch_max_dd_pct"] for w in windows), default=0.0))
    beats_single_rate = sum(1 for w in windows if w["beats_single"]) / n
    beats_null_rate = sum(1 for w in windows if w["beats_null_p90"]) / n
    single_total = float(sum(w["best_single_return_pct"] for w in windows))
    null_total = float(sum(w["null_mean_return_pct"] for w in windows))

    # Honest edge bar: positive OOS, beats best-single and the null on net AND on
    # a majority of windows, enough windows and trades.
    edge = (
        n >= 8
        and total_trades >= 50
        and total > 0
        and mean > 0
        and positive_rate >= 0.5
        and total > single_total
        and total > null_total
        and beats_single_rate >= 0.5
        and beats_null_rate >= 0.5
    )
    verdict = "CANDIDATE_EDGE" if edge else "NO_EDGE"
    reasons: List[str] = []
    if n < 8:
        reasons.append(f"only {n} OOS windows (<8): not enough to claim anything")
    if total_trades < 50:
        reasons.append(f"only {total_trades} OOS trades (<50)")
    if total <= 0:
        reasons.append(f"switch total OOS return {total:.2f}% not positive")
    if total <= single_total:
        reasons.append(f"switch ({total:.2f}%) does not beat best single ({single_total:.2f}%)")
    if total <= null_total:
        reasons.append(f"switch ({total:.2f}%) does not beat random-routing null ({null_total:.2f}%)")
    if positive_rate < 0.5:
        reasons.append(f"positive-window rate {positive_rate:.0%} < 50%")
    return {
        "verdict": verdict,
        "cost_pips": cost_pips,
        "windows": n,
        "total_oos_trades": total_trades,
        "switch_total_return_pct": round(total, 4),
        "switch_mean_return_pct": round(mean, 4),
        "switch_positive_window_rate": round(positive_rate, 4),
        "switch_max_drawdown_pct": round(max_dd, 4),
        "best_single_total_return_pct": round(single_total, 4),
        "null_total_return_pct": round(null_total, 4),
        "beats_single_window_rate": round(beats_single_rate, 4),
        "beats_null_window_rate": round(beats_null_rate, 4),
        "not_edge_reasons": [] if verdict == "CANDIDATE_EDGE" else reasons,
        "claim_boundary": EDGE_CLAIM_BOUNDARY,
    }
