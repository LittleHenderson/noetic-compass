"""Build the nested-lacunarity bias-state MAP across timeframes (CAS Forex piece b).

This is pure MEASUREMENT. For each cell = (symbol x timeframe x regime) it asks the
leak-free OOS harness whether ANY strategy clears the null, then rolls the gap/
non-gap flags up the nesting timeframe -> regime -> symbol. It does not pick
trades, size, tune, or grant live permission. With price-only signals the honest,
expected output is overall_gap_fraction == 1.0 (all gaps) - that IS the bias-state.

Two modes:
  --synthetic   (default)  no network; deterministic multi-regime synthetic grid.
  --real                   fetch each (symbol, timeframe) via yfinance, mirroring
                           scripts/run_edge_oos.py (H1 ~= 2y, D1 ~= 5y).

Run:
  python scripts/run_nested_lacunarity.py
  python scripts/run_nested_lacunarity.py --real --symbols US30 EUR/USD --timeframes H1 D1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.condition_lab import (
    default_real_period_for_timeframe,
    normalize_timeframe,
    yfinance_interval_for_timeframe,
)
from cas_forex.nested_lacunarity import (
    build_gap_map,
    build_synthetic_grid,
    serialize_nested_lacunarity_report,
)
from cas_forex.regime_sim import REGIMES
from cas_forex.time_utils import utc_now

# Canonical symbol -> yfinance ticker (mirrors scripts/run_edge_oos.py). Index
# proxies (^DJI / ^NDX) are the cash index, NOT the tradeable CFD; any non-gap
# result must be re-tested on broker candles before any claim.
SYMBOL_TICKERS = {
    "US30": "^DJI",
    "NAS100": "^NDX",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "USDCAD=X",
}


def fetch(symbol: str, ticker: str, period: str, interval: str) -> List[dict]:
    import yfinance as yf

    df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
    if df is None or df.empty:
        return []
    out: List[dict] = []
    for idx, row in df.iterrows():
        c = float(row["Close"])
        if c <= 0:
            continue
        out.append({
            "timestamp": idx.isoformat(),
            "open": float(row["Open"]), "high": float(row["High"]),
            "low": float(row["Low"]), "close": c,
            "volume": int(row.get("Volume", 0) or 0),
        })
    return out


def fetch_real_grid(symbols: List[str], timeframes: List[str], min_bars: int) -> Dict[str, Dict[str, List[dict]]]:
    grid: Dict[str, Dict[str, List[dict]]] = {}
    for sym in symbols:
        ticker = SYMBOL_TICKERS.get(sym, f"{sym.replace('/', '')}=X")
        for tf in timeframes:
            canonical = normalize_timeframe(tf)
            interval = yfinance_interval_for_timeframe(canonical)
            if interval is None:
                print(f"  ! {sym} {canonical}: no yfinance interval; skipping")
                continue
            period = default_real_period_for_timeframe(canonical)
            print(f"[fetch] {sym} {canonical} ({ticker} {interval} {period}) ...", flush=True)
            candles = fetch(sym, ticker, period, interval)
            if len(candles) >= min_bars:
                grid.setdefault(sym, {})[canonical] = candles
                print(f"  {len(candles)} bars  {candles[0]['timestamp'][:10]} -> {candles[-1]['timestamp'][:10]}")
            else:
                print(f"  ! only {len(candles)} bars (<{min_bars}); skipping")
    return grid


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--real", action="store_true", help="fetch real yfinance candles (default: synthetic, no network)")
    p.add_argument("--symbols", nargs="*", default=["EUR/USD", "US30"])
    p.add_argument("--timeframes", nargs="*", default=["H1", "D1"])
    p.add_argument("--regimes", nargs="*", default=list(REGIMES))
    p.add_argument("--costs", nargs="*", type=float, default=[1.0, 2.0, 3.0])
    p.add_argument("--train-bars", type=int, default=504)
    p.add_argument("--test-bars", type=int, default=126)
    p.add_argument("--detect-window", type=int, default=60)
    p.add_argument("--n-null", type=int, default=20)
    p.add_argument("--min-cell-trades", type=int, default=30)
    p.add_argument("--min-regime-bars", type=int, default=20)
    p.add_argument("--min-coherent-timeframes", type=int, default=2)
    p.add_argument("--bars-per-regime", type=int, default=320, help="synthetic only")
    p.add_argument("--seed-base", type=int, default=0, help="synthetic only")
    p.add_argument("--output-dir", default="evidence_runs/nested_lacunarity")
    args = p.parse_args()

    min_bars = args.train_bars + args.test_bars
    if args.real:
        grid = fetch_real_grid(args.symbols, args.timeframes, min_bars)
        if not grid:
            print("No usable real data fetched.")
            return 1
    else:
        print(f"[synthetic] {len(args.symbols)} symbols x {len(args.timeframes)} timeframes "
              f"x {len(args.regimes)} regimes; {args.bars_per_regime} bars/regime")
        grid = build_synthetic_grid(
            args.symbols, args.timeframes, args.regimes,
            bars_per_regime=args.bars_per_regime, seed_base=args.seed_base,
        )

    print("\n[run] building nested-lacunarity bias-state map ...", flush=True)
    report = build_gap_map(
        grid,
        regimes=args.regimes,
        costs=args.costs,
        train_bars=args.train_bars,
        test_bars=args.test_bars,
        detect_window=args.detect_window,
        n_null=args.n_null,
        min_cell_trades=args.min_cell_trades,
        min_regime_bars=args.min_regime_bars,
        min_coherent_timeframes=args.min_coherent_timeframes,
    )
    s = report.summary

    print("=" * 78)
    print(f"BIAS-STATE: {s['bias_state_verdict']}")
    print("-" * 78)
    print(f"  cells                 : {s['total_cells']}   gaps: {s['gap_cells']}   non-gaps: {s['non_gap_cells']}")
    print(f"  overall gap fraction  : {s['overall_gap_fraction']:.4f}")
    print(f"  fractal-coherent      : {s['fractal_coherent_count']}  (non-gap at >= "
          f"{args.min_coherent_timeframes} timeframes for one symbol x regime)")
    print(f"  worst timeframe (gap) : {s['worst_timeframe_by_gap_fraction']}")
    print(f"  best  timeframe (gap) : {s['best_timeframe_by_gap_fraction']}")
    print("  per-timeframe marginal gap fraction:")
    for tf, frac in s["timeframe_marginal_gap_fraction"].items():
        print(f"    tf::{tf:<5} {frac:.4f}")
    if report.non_gap_cells:
        print("  NON-GAP cells (research candidates only, NOT live permission):")
        for c in report.non_gap_cells:
            print(f"    {c.symbol} {c.timeframe} {c.regime}: verdict={c.verdict} "
                  f"trades={c.oos_trades} switch={c.switch_total_return_pct:.2f}%")
    if report.fractal_coherent_cells:
        print("  FRACTAL-COHERENT pockets:")
        for entry in report.fractal_coherent_cells:
            print(f"    {entry['symbol']} {entry['regime']}: timeframes={entry['timeframes']}")
    print("=" * 78)
    print("NOTE:", report.claim_boundary)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"nested-lacunarity-{utc_now().strftime('%Y%m%d%H%M%S')}"
    path = out_dir / f"{run_id}-report.json"
    path.write_text(
        json.dumps({
            "run_id": run_id,
            "mode": "real" if args.real else "synthetic",
            "symbols": list(grid),
            "timeframes": args.timeframes,
            "regimes": args.regimes,
            "train_bars": args.train_bars,
            "test_bars": args.test_bars,
            "report": serialize_nested_lacunarity_report(report),
        }, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
