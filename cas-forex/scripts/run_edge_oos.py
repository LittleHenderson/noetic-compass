"""Run the leak-free out-of-sample regime-switching edge test on REAL data.

Honest answer to: does switching strategies by detected regime have an
out-of-sample edge after realistic cost? Routing is learned on train only; the
per-bar causal switcher trades the held-out test window; SWITCH is measured vs
the best single strategy, a random-routing null, and buy-hold.

Run:  python scripts/run_edge_oos.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.edge_oos import evaluate_oos
from cas_forex.time_utils import utc_now

# Canonical symbol -> yfinance ticker. Indices use the cash-index proxy (^DJI /
# ^NDX); honest caveat: that is NOT the tradeable CFD (no spread/financing), so a
# positive result here must be re-tested on broker candles before any claim.
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
    out = []
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--period", default="5y")
    p.add_argument("--interval", default="1d")
    p.add_argument("--symbols", nargs="*", default=list(SYMBOL_TICKERS))
    p.add_argument("--costs", nargs="*", type=float, default=[1.0, 2.0, 3.0])
    p.add_argument("--train-bars", type=int, default=504)
    p.add_argument("--test-bars", type=int, default=126)
    p.add_argument("--detect-window", type=int, default=60)
    p.add_argument("--n-null", type=int, default=20)
    p.add_argument("--output-dir", default="evidence_runs/edge_oos")
    args = p.parse_args()

    data: Dict[str, List[dict]] = {}
    for sym in args.symbols:
        ticker = SYMBOL_TICKERS.get(sym, f"{sym.replace('/', '')}=X")
        print(f"[fetch] {sym} ({ticker}) ...", flush=True)
        candles = fetch(sym, ticker, args.period, args.interval)
        need = args.train_bars + args.test_bars
        if len(candles) >= need:
            data[sym] = candles
            print(f"  {len(candles)} bars  {candles[0]['timestamp'][:10]} -> {candles[-1]['timestamp'][:10]}")
        else:
            print(f"  ! only {len(candles)} bars (<{need}); skipping")
    if not data:
        print("No usable data fetched.")
        return 1

    all_reports = {}
    for cost in args.costs:
        print(f"\n[run] OOS evaluation at cost {cost}p ...", flush=True)
        report = evaluate_oos(
            data, cost_pips=cost, train_bars=args.train_bars, test_bars=args.test_bars,
            detect_window=args.detect_window, n_null=args.n_null,
        )
        s = report.summary
        all_reports[str(cost)] = {"summary": s, "windows": report.windows}
        print("=" * 78)
        print(f"COST {cost}p  ->  VERDICT: {s['verdict']}")
        print("-" * 78)
        print(f"  OOS windows           : {s['windows']}   total OOS trades: {s['total_oos_trades']}")
        print(f"  SWITCH total return   : {s['switch_total_return_pct']:>9.2f}%   "
              f"mean/window: {s['switch_mean_return_pct']:.2f}%   posrate: {s['switch_positive_window_rate']:.0%}")
        print(f"  best-single total     : {s['best_single_total_return_pct']:>9.2f}%   "
              f"(SWITCH beats single in {s['beats_single_window_rate']:.0%} of windows)")
        print(f"  random-null total     : {s['null_total_return_pct']:>9.2f}%   "
              f"(SWITCH beats null  in {s['beats_null_window_rate']:.0%} of windows)")
        print(f"  SWITCH max drawdown   : {s['switch_max_drawdown_pct']:.2f}%")
        if s["verdict"] != "CANDIDATE_EDGE":
            print("  not-edge reasons:")
            for r in s["not_edge_reasons"]:
                print(f"    - {r}")
    print("=" * 78)
    print("NOTE:", report.claim_boundary)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"edge-oos-{utc_now().strftime('%Y%m%d%H%M%S')}"
    path = out_dir / f"{run_id}-report.json"
    path.write_text(json.dumps({
        "run_id": run_id, "period": args.period, "interval": args.interval,
        "symbols": list(data), "train_bars": args.train_bars, "test_bars": args.test_bars,
        "reports_by_cost": all_reports,
    }, indent=2, default=str), encoding="utf-8")
    print(f"report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
