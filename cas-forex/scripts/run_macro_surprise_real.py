"""Real macro-surprise test: does a US macro surprise predict the EUR/USD move?

Feeds REAL point-in-time economic-calendar data (Forex Factory: consensus Forecast
+ Actual + release date) through the null-tested macro-surprise cell. Uses a DAILY
event-study (release-day EUR/USD return vs prior close) because the calendar's
intraday timestamps are unreliable (many 00:00 markers); the reliable field is the
release DATE. Honest caveats are printed with the verdict.

NEVER fabricates data. The calendar CSV must be supplied (downloaded separately).

Run:
  python scripts/run_macro_surprise_real.py --calendar-csv <path-to-forex_factory_cache.csv>
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.instruments import price_unit_size
from cas_forex.macro_surprise import evaluate_surprise_return_pairs
import numpy as np


def parse_value(raw: str) -> Optional[float]:
    """Parse '228K', '5.2B', '3.1%', '-50K', '1,234' -> float; '' -> None."""
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "").replace("%", "")
    if not s or s in {"-", "N/A"}:
        return None
    mult = 1.0
    if s[-1:] in "KkMmBbTt":
        mult = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}[s[-1].lower()]
        s = s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return None


def load_events(csv_path: str, currency: str) -> Dict[str, List[dict]]:
    """Return {event_name: [{date, surprise_raw}]} for standard-direction high-impact events."""
    by_event: Dict[str, List[dict]] = defaultdict(list)
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row.get("Currency") or "").strip() != currency:
                continue
            if "high impact" not in (row.get("Impact") or "").lower():
                continue
            detail = (row.get("Detail") or "").lower()
            # Standard direction only: actual > forecast is bullish for the currency.
            if "greater than 'forecast' is good" not in detail:
                continue
            actual = parse_value(row.get("Actual"))
            forecast = parse_value(row.get("Forecast"))
            if actual is None or forecast is None:
                continue
            dt = (row.get("DateTime") or "").strip()
            day = dt[:10]  # reliable: the release DATE (ignore unreliable intraday time)
            try:
                date.fromisoformat(day)
            except ValueError:
                continue
            by_event[(row.get("Event") or "").strip()].append({
                "date": day, "surprise_raw": actual - forecast,
            })
    return by_event


def causal_zscore(values: List[float], min_history: int = 6) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for i in range(len(values)):
        prior = values[:i]
        if len(prior) < min_history:
            out.append(None)
            continue
        mu, sd = float(np.mean(prior)), float(np.std(prior))
        out.append((values[i] - mu) / sd if sd > 0 else 0.0)
    return out


def fetch_daily_closes(ticker: str, period: str = "5y") -> List[tuple]:
    import yfinance as yf
    df = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
    out = []
    for idx, row in df.iterrows():
        c = float(row["Close"])
        if c > 0:
            out.append((idx.date().isoformat(), c))
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--calendar-csv", required=True)
    p.add_argument("--currency", default="USD")
    p.add_argument("--fx-symbol", default="EUR/USD")
    p.add_argument("--fx-ticker", default="EURUSD=X")
    p.add_argument("--cost-pips", type=float, default=1.0)
    p.add_argument("--n-null", type=int, default=500)
    p.add_argument("--min-history", type=int, default=6)
    p.add_argument("--output-dir", default="evidence_runs/macro_surprise")
    args = p.parse_args()

    print(f"[load] calendar {args.calendar_csv} ...", flush=True)
    by_event = load_events(args.calendar_csv, args.currency)
    print(f"  {len(by_event)} standard-direction high-impact {args.currency} event types")

    print(f"[fetch] {args.fx_symbol} ({args.fx_ticker}) daily ...", flush=True)
    closes = fetch_daily_closes(args.fx_ticker)
    if len(closes) < 50:
        print("  insufficient FX data."); return 1
    dates = [d for d, _ in closes]
    close_by_date = {d: c for d, c in closes}
    prior_close = {dates[i]: closes[i - 1][1] for i in range(1, len(closes))}
    fx_start, fx_end = dates[0], dates[-1]
    print(f"  {len(closes)} daily bars  {fx_start} -> {fx_end}")

    pip = price_unit_size(args.fx_symbol)
    # Per-indicator causal z-score, then pool the (surprise_z, release-day return) pairs.
    pooled = []  # (date, surprise_z, ret, cost_ret)
    per_event_counts = {}
    for event, rows in by_event.items():
        rows = sorted(rows, key=lambda r: r["date"])
        zs = causal_zscore([r["surprise_raw"] for r in rows], min_history=args.min_history)
        kept = 0
        for r, z in zip(rows, zs):
            if z is None:
                continue
            d = r["date"]
            if d not in close_by_date or d not in prior_close:
                continue  # release day not in FX history (weekend/holiday/out of range)
            entry = prior_close[d]
            ret = close_by_date[d] / entry - 1.0  # release-day move (contains the reaction)
            cost_ret = (args.cost_pips * pip) / entry if entry > 0 else 0.0
            pooled.append((d, float(z), float(ret), float(cost_ret)))
            kept += 1
        if kept:
            per_event_counts[event] = kept

    pooled.sort(key=lambda x: x[0])
    usable = [{"surprise": z, "ret": ret, "cost_ret": cr} for _, z, ret, cr in pooled]
    print(f"\n[pool] {len(usable)} usable (surprise, release-day-move) pairs across "
          f"{len(per_event_counts)} indicators, overlapping {fx_start}..{fx_end}")
    top = sorted(per_event_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    for ev, n in top:
        print(f"    {n:4d}  {ev}")

    rep = evaluate_surprise_return_pairs(
        usable, symbol=args.fx_symbol, horizon_bars=1, cost_pips=args.cost_pips,
        n_null=args.n_null, min_test_events=8, min_history=args.min_history,
    )
    s = rep.summary
    print("\n" + "=" * 78)
    print(f"REAL MACRO-SURPRISE -> {args.fx_symbol}  ::  VERDICT: {s['verdict']}")
    print("-" * 78)
    for k in ("usable_events", "train_events", "test_events", "learned_sign",
              "hit_rate", "net_return_pct", "null_mean_return_pct", "null_p95_return_pct",
              "beats_null_p95", "reason"):
        if k in s:
            print(f"  {k:22}: {s[k]}")
    for r in s.get("not_edge_reasons", []):
        print(f"    - {r}")
    print("-" * 78)
    print("CAVEATS: daily release-day return (contains same-day non-release noise);")
    print("Forex Factory consensus+actual, standard-direction US high-impact only;")
    print("EUR/USD = yfinance indicative mid (no real spread). NOT LICENSED.")
    print("=" * 78)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "macro-surprise-real-report.json"
    path.write_text(json.dumps({
        "fx_symbol": args.fx_symbol, "currency": args.currency,
        "fx_window": [fx_start, fx_end], "usable_pairs": len(usable),
        "per_event_counts": per_event_counts, "summary": s,
    }, indent=2, default=str), encoding="utf-8")
    print(f"report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
