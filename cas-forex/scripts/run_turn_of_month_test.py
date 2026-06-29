"""Turn-of-month drift test on US indices (rank-5 survivor) — the calendar-locked
forced-flow anomaly FX lacks (pension/401k inflows + fund rebalancing concentrate buy
pressure at month-end). Most-replicated equity calendar anomaly (Lakonishok-Smidt 1988,
McConnell-Xu 2008). Tested honestly, leak-free, with a permutation null + carry.

Window (canonical -1,+3): long from the close of the 2nd-to-last trading day of month M
through the close of the 3rd trading day of month M+1 (4 trading-day hold), flat else.

NULL (the timing test): for each month, relocate the same window to a RANDOM OTHER
within-month 4-day window; the real turn-of-month mean must beat the null p95. Because
every within-month window is also long-equity, this null HOLDS BETA FIXED — beating it
means the month-TURN timing is special, not just "stocks drift up".
GATE 2 (tradeable): net mean/window > 0 after a PROPORTIONAL spread (bps, not absolute
index points — points are meaningless across a 1927 S&P of ~17 and a 2026 one of ~5500)
plus long-CFD financing carry.
ERA SPLITS: a 1988-published anomaly may be arbitraged away. The modern sub-periods
(2000+, 2010+, 2016+) are the real out-of-sample test; the deep history only shows decay.

Multi-decade daily history via yfinance (period=max), frozen to data/external/ for reuse.
NEVER fabricates data. Run:
  python scripts/run_turn_of_month_test.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

TICKERS = {"US30": "^DJI", "NAS100": "^NDX", "SPX500": "^GSPC"}


def load_index(ticker: str, cache_dir: Path, refresh: bool):
    import pandas as pd

    cache = cache_dir / f"yf_{ticker.replace('^', 'idx_')}_d1_max.csv"
    if cache.exists() and not refresh:
        df = pd.read_csv(cache, parse_dates=["Date"])
    else:
        import yfinance as yf
        raw = yf.Ticker(ticker).history(period="max", interval="1d", auto_adjust=False)
        df = raw.reset_index()[["Date", "Close"]].copy()
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
        df.to_csv(cache, index=False)
    df = df.dropna(subset=["Close"])
    df = df[df["Close"] > 0].sort_values("Date").reset_index(drop=True)
    return [d.date() for d in df["Date"]], df["Close"].to_numpy(dtype=float)


def tom_windows(dates):
    """(entry_idx, exit_idx, month_key): entry = 2nd-to-last trading day of M,
    exit = 3rd trading day of M+1."""
    last_of_month = [i for i in range(len(dates) - 1)
                     if (dates[i].year, dates[i].month) != (dates[i + 1].year, dates[i + 1].month)]
    out = []
    for li in last_of_month:
        e, x = li - 1, li + 3
        if e >= 0 and x < len(dates):
            out.append((e, x, (dates[li].year, dates[li].month)))
    return out


def analyze(dates, closes, wins, month_idx, era_start, *, spread_bps, carry_rates, n_null, rng):
    ew = [(e, x, m) for (e, x, m) in wins if dates[e].year >= era_start]
    if len(ew) < 24:
        return None
    gross = np.array([closes[x] / closes[e] - 1.0 for e, x, _ in ew])
    cal_days = np.array([(dates[x] - dates[e]).days for e, x, _ in ew], dtype=float)
    real_mean = float(gross.mean())

    # NULL pools: per month, the 4-day-forward returns of every OTHER within-month start
    # (exclude the actual turn-of-month entry so the null is genuinely "other timing").
    tom_entries = {e for e, _, _ in ew}
    months = {m for _, _, m in ew}
    pools = {}
    for m in months:
        starts = [j for j in month_idx[m] if j + 4 < len(closes) and j not in tom_entries]
        if starts:
            pools[m] = np.array([closes[j + 4] / closes[j] - 1.0 for j in starts])
    win_months = [m for _, _, m in ew if m in pools]
    mat = np.empty((len(win_months), n_null))
    for i, m in enumerate(win_months):
        mat[i] = rng.choice(pools[m], size=n_null)
    null_means = mat.mean(axis=0)
    null_p95 = float(np.percentile(null_means, 95))
    emp_pct = float((null_means < real_mean).mean())  # empirical percentile of real vs null

    spread = spread_bps / 1e4
    net_by_rate = {f"{r:.2f}": round(100.0 * float((gross - spread - r * cal_days / 365.0).mean()), 5)
                   for r in carry_rates}
    return {
        "windows": len(ew), "first_year": dates[ew[0][0]].year,
        "gross_pct": round(100 * real_mean, 5), "win_rate": round(float((gross > 0).mean()), 4),
        "null_p95_pct": round(100 * null_p95, 5), "real_vs_null_pct": round(emp_pct, 4),
        "beats_timing_null": bool(real_mean > null_p95), "net_pct_by_carry": net_by_rate,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--carry-rates", type=float, nargs="+", default=[0.0, 0.05, 0.08])
    ap.add_argument("--spread-bps", type=float, default=2.0, help="proportional round-trip spread in basis points")
    ap.add_argument("--eras", type=int, nargs="+", default=[0, 2000, 2010, 2016])
    ap.add_argument("--n-null", type=int, default=2000)
    ap.add_argument("--output-dir", default="evidence_runs/turn_of_month")
    args = ap.parse_args()

    cache_dir = Path("data/external")
    rng = np.random.default_rng(7)
    report = {"window": "(-1,+3)", "spread_bps": args.spread_bps, "by_index": {}}

    print("=" * 98)
    print(f"TURN-OF-MONTH DRIFT (-1,+3) — long-only 4-day hold — spread {args.spread_bps}bps round-trip")
    print("beats_null = real gross beats the beta-controlled within-month relocation null p95 (2000 perms)")
    print("=" * 98)

    for label, ticker in TICKERS.items():
        dates, closes = load_index(ticker, cache_dir, args.refresh)
        month_idx = defaultdict(list)
        for i, d in enumerate(dates):
            month_idx[(d.year, d.month)].append(i)
        wins = tom_windows(dates)
        report["by_index"][label] = {"ticker": ticker, "history": f"{dates[0]} -> {dates[-1]}", "eras": {}}
        print(f"\n{label} ({ticker}, {dates[0]} -> {dates[-1]}):")
        print(f"  {'era':>8} {'N':>5} {'gross%':>9} {'win':>6} {'nullp95%':>9} {'real>null':>9}  net%/window @ carry 0/5/8%")
        for era in args.eras:
            r = analyze(dates, closes, wins, month_idx, era, spread_bps=args.spread_bps,
                        carry_rates=args.carry_rates, n_null=args.n_null, rng=rng)
            if r is None:
                continue
            report["by_index"][label]["eras"][str(era)] = r
            tag = f"{era}+" if era else "all"
            nb = r["net_pct_by_carry"]
            beats = "YES" if r["beats_timing_null"] else "no"
            print(f"  {tag:>8} {r['windows']:>5} {r['gross_pct']:>+9.4f} {r['win_rate']:>6.3f} "
                  f"{r['null_p95_pct']:>+9.4f} {beats:>9}  "
                  f"{nb['0.00']:+.4f}/{nb['0.05']:+.4f}/{nb['0.08']:+.4f}  (pctile {r['real_vs_null_pct']:.3f})")

    print("\n" + "-" * 98)
    print("EDGE requires, IN THE MODERN ERA (2010+/2016+): beats_timing_null=YES AND net>0 at ~5%/yr carry.")
    print("A signal that only works pre-2010 is a decayed/arbitraged anomaly, not a tradeable edge today.")
    print("=" * 98)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "turn-of-month-report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"report: {out_dir / 'turn-of-month-report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
