"""Regime-switching backtest on REAL data.

Detects the market regime each bar and routes to the strategy the simulator says
fits that regime (or sits out where there's no validated edge), then compares the
SWITCHED system against every single strategy on the same real 5y data.

Answers: does switching strategies by detected condition beat any one strategy?

Run:  python scripts/run_switching_backtest.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.backtest.engine import BacktestEngine
from cas_forex.forecast.strategies import (
    make_donchian_breakout_signal,
    make_mean_reversion_signal,
    make_sma_trend_signal,
)
from cas_forex.regime_sim import DEFAULT_ROUTING, make_regime_switching_signal
from cas_forex.time_utils import utc_now

SYMBOLS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]


def fetch_real_candles(symbol: str, period: str, interval: str) -> List[dict]:
    import yfinance as yf
    df = yf.Ticker(f"{symbol.replace('/', '')}=X").history(
        period=period, interval=interval, auto_adjust=False)
    if df is None or df.empty:
        return []
    out = []
    for idx, row in df.iterrows():
        c = float(row["Close"])
        if c <= 0:
            continue
        out.append({"timestamp": idx.isoformat(), "open": float(row["Open"]),
                    "high": float(row["High"]), "low": float(row["Low"]),
                    "close": c, "volume": int(row.get("Volume", 0) or 0)})
    return out


def run_strategy(candles, symbol, signal_fn, starting, lots, spread, extra):
    engine = BacktestEngine(
        initial_balance=starting, position_size_lots=lots,
        spread_pips=spread, extra_cost_pips=extra, signal_fn=signal_fn,
    )
    return engine.run(candles, symbol=symbol, warmup_bars=60)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--period", default="5y")
    p.add_argument("--interval", default="1d")
    p.add_argument("--symbols", nargs="*", default=SYMBOLS)
    p.add_argument("--starting-balance", type=float, default=10000.0)
    p.add_argument("--position-lots", type=float, default=0.05)
    p.add_argument("--spread-pips", type=float, default=1.0)
    p.add_argument("--extra-cost-pips", type=float, default=0.5)
    # detector tuning
    p.add_argument("--detect-window", type=int, default=60)
    p.add_argument("--er-trend", type=float, default=0.35,
                   help="efficiency-ratio threshold for calling a trend (lower = more trends)")
    p.add_argument("--hi-vol", type=float, default=1.5)
    p.add_argument("--lo-vol", type=float, default=0.6)
    p.add_argument("--shock-z", type=float, default=4.0)
    p.add_argument("--output-dir", default="evidence_runs/switching")
    args = p.parse_args()

    sub_signals = {
        "breakout": make_donchian_breakout_signal(),
        "meanrev": make_mean_reversion_signal(),
        "trend_sma": make_sma_trend_signal(),
    }
    switch_signal = make_regime_switching_signal(
        sub_signals, routing=DEFAULT_ROUTING,
        detect_window=args.detect_window, baseline=max(args.detect_window * 3, 180),
        er_trend=args.er_trend, hi_vol=args.hi_vol, lo_vol=args.lo_vol,
        shock_z=args.shock_z,
    )

    strategies = {
        "trend_sma": make_sma_trend_signal(),
        "meanrev": make_mean_reversion_signal(),
        "meanrev_tf": make_mean_reversion_signal(trend_filter=True),
        "breakout": make_donchian_breakout_signal(),
        "SWITCH": switch_signal,
    }

    # Fetch once, reuse for every strategy.
    data: Dict[str, List[dict]] = {}
    for sym in args.symbols:
        print(f"[fetch] {sym} ...", flush=True)
        candles = fetch_real_candles(sym, args.period, args.interval)
        if len(candles) >= 120:
            data[sym] = candles
            print(f"  {len(candles)} bars {candles[0]['timestamp'][:10]} -> {candles[-1]['timestamp'][:10]}")
        else:
            print(f"  ! only {len(candles)} bars; skipping")
    if not data:
        print("No data.")
        return 1

    results: Dict[str, dict] = {}
    for name, fn in strategies.items():
        pnl = dd = trades = 0.0
        n = 0
        for sym, candles in data.items():
            r = run_strategy(candles, sym, fn, args.starting_balance,
                             args.position_lots, args.spread_pips, args.extra_cost_pips)
            pnl += r.total_profit_account
            dd += r.max_drawdown_pct
            trades += r.total_trades
            n += 1
        results[name] = {"pnl": round(pnl, 2), "avg_dd": round(dd / max(n, 1), 2),
                         "trades": int(trades)}

    cost = args.spread_pips + args.extra_cost_pips
    print("\n" + "=" * 70)
    print(f"REGIME-SWITCHING vs SINGLE STRATEGIES  (real {args.period} {args.interval}, "
          f"cost {cost}p, ${args.starting_balance:,.0f}/symbol)")
    print("=" * 70)
    print(f"{'strategy':14}{'portfolio P&L':>16}{'avg maxDD%':>12}{'trades':>9}")
    print("-" * 70)
    for name in strategies:
        rr = results[name]
        star = "  <-- switched" if name == "SWITCH" else ""
        print(f"{name:14}{('$' + format(rr['pnl'], ',.2f')):>16}{rr['avg_dd']:>12}{rr['trades']:>9}{star}")
    print("-" * 70)

    # Regime distribution for the switched system.
    counts = dict(switch_signal.regime_counts)
    total_calls = sum(v for k, v in counts.items() if not k.startswith("__"))
    print("\nSWITCH regime distribution (across all symbols/bars):")
    for regime in ["trend_up", "trend_down", "range", "high_vol", "low_vol", "vol_cluster", "shock"]:
        cnt = counts.get(regime, 0)
        routed = DEFAULT_ROUTING.get(regime) or "SIT OUT"
        pct = (cnt / total_calls * 100) if total_calls else 0
        print(f"  {regime:12} {cnt:>6} ({pct:4.1f}%) -> {routed}")
    print(f"  sit-outs (vol_cluster): {counts.get('__sit_out__', 0)}   "
          f"sub-strategy no-signal: {counts.get('__no_signal__', 0)}")

    best = max(results, key=lambda k: results[k]["pnl"])
    print(f"\nBest by P&L: {best} (${results[best]['pnl']:,.2f})")
    print("NOTE: real data, in-sample routing from synthetic sim; not OOS-validated. NOT LICENSED.")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"switch-{utc_now().strftime('%Y%m%d%H%M%S')}"
    (out_dir / f"{run_id}-report.json").write_text(json.dumps({
        "run_id": run_id, "results": results, "regime_counts": counts,
        "routing": DEFAULT_ROUTING, "cost_pips": cost,
    }, indent=2, default=str), encoding="utf-8")
    print(f"report: {out_dir / f'{run_id}-report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
