"""Run the full condition_lab 13-setting grid through the leak-free OOS test.

Answers the owner's question empirically (not by argument): do any of the
assembled/tuned strategy settings the system can build -- or a switch that selects
among all 13 on train -- have an out-of-sample edge? Same honest harness:
walk-forward, realistic cost, random null, trades begin only in the held-out test.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.condition_lab import build_strategy_settings
from cas_forex.edge_oos import _run, evaluate_oos
from cas_forex.walk_forward import split_walk_forward_ranges
from scripts.run_edge_oos import SYMBOL_TICKERS, fetch

COST = 2.0
TRAIN_BARS = 504
TEST_BARS = 126
CTX = 180


def standalone_oos(data: Dict[str, List[dict]], settings) -> List[dict]:
    """Each setting traded standalone, summed over all held-out test windows."""
    rows = []
    for s in settings:
        fn = s.make_signal()
        total = 0.0
        wins = 0
        nwin = 0
        trades = 0
        for symbol, candles in data.items():
            for ts, te, vs, ve in split_walk_forward_ranges(
                len(candles), train_bars=TRAIN_BARS, test_bars=TEST_BARS
            ):
                ctx = candles[max(0, te - CTX):te]
                res = _run(list(ctx) + candles[vs:ve], symbol, fn, cost_pips=COST, warmup=len(ctx))
                total += res["return_pct"]
                trades += res["trades"]
                nwin += 1
                wins += 1 if res["return_pct"] > 0 else 0
        rows.append({
            "setting": s.name, "family": s.family,
            "oos_total_return_pct": round(total, 2),
            "positive_window_rate": round(wins / nwin, 3) if nwin else 0.0,
            "oos_trades": trades,
        })
    return sorted(rows, key=lambda r: r["oos_total_return_pct"], reverse=True)


def main() -> int:
    settings = build_strategy_settings()
    data: Dict[str, List[dict]] = {}
    for sym in SYMBOL_TICKERS:
        candles = fetch(sym, SYMBOL_TICKERS[sym], "5y", "1d")
        if len(candles) >= TRAIN_BARS + TEST_BARS:
            data[sym] = candles
            print(f"[fetch] {sym}: {len(candles)} bars", flush=True)
    if not data:
        print("No data.")
        return 1

    print(f"\n=== (A) each of {len(settings)} condition_lab settings, STANDALONE OOS (cost {COST}p) ===")
    rows = standalone_oos(data, settings)
    print(f"{'setting':24}{'family':14}{'OOS total %':>12}{'pos-win%':>10}{'trades':>8}")
    print("-" * 70)
    any_pos = False
    for r in rows:
        flag = "  <- positive" if r["oos_total_return_pct"] > 0 else ""
        any_pos = any_pos or r["oos_total_return_pct"] > 0
        print(f"{r['setting']:24}{r['family']:14}{r['oos_total_return_pct']:>12.2f}"
              f"{r['positive_window_rate']*100:>9.0f}%{r['oos_trades']:>8}{flag}")
    print("-" * 70)
    print(f"any setting OOS-positive standalone? {any_pos}")

    print(f"\n=== (B) SWITCH selecting among all {len(settings)} settings on train, OOS vs null ===", flush=True)
    menu = {s.name: s.make_signal() for s in settings}
    report = evaluate_oos(
        data, cost_pips=COST, train_bars=TRAIN_BARS, test_bars=TEST_BARS, n_null=10, sub_signals=menu
    )
    s = report.summary
    print(f"VERDICT: {s['verdict']}")
    print(f"  SWITCH total {s['switch_total_return_pct']}%  best-single {s['best_single_total_return_pct']}%  "
          f"null {s['null_total_return_pct']}%  beats-null {s['beats_null_window_rate']:.0%} of windows")
    for r in s.get("not_edge_reasons", []):
        print(f"  - {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
