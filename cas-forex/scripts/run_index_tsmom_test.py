"""Index time-series momentum test — the ACTIVE research lead (tsmom_126_250_2_10 on
US30/NAS100/SPX, the strategy the Hugosway paper-proof is validating).

Honest question: is long-only index TSMOM a real EDGE (its timing beats a random-timing
null AND it improves risk-adjusted return over buy-and-hold, out-of-sample, after cost),
or is it just BETA with drawdown control? The lead's positive walk-forward numbers
(+1.89%, +31.6%) predate the null-control discipline; this applies it.

Rule: long when the trailing 126-day return > 0 (causal: decided on data through t-1),
flat otherwise; transaction cost charged on each flip. Compared per era against:
  (1) buy-and-hold (CAGR / max-drawdown / Sharpe), and
  (2) a RANDOM-TIMING null with the same fraction of days in-market (does the MOMENTUM
      timing beat being long on the same number of randomly-chosen days?).
EDGE only if it beats the random-timing null p95 in the modern era. Drawdown reduction
without beating the null is risk-management (real, valuable on a leveraged account), NOT
alpha — reported separately and honestly. NEVER fabricates data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

FILES = {"US30": "yf_idx_DJI_d1_max.csv", "NAS100": "yf_idx_NDX_d1_max.csv", "SPX500": "yf_idx_GSPC_d1_max.csv"}


def load(fname):
    import pandas as pd
    df = pd.read_csv(Path("data/external") / fname, parse_dates=["Date"]).dropna(subset=["Close"])
    df = df[df["Close"] > 0].sort_values("Date").reset_index(drop=True)
    return [d.date() for d in df["Date"]], df["Close"].to_numpy(dtype=float)


def perf(daily):
    eq = np.cumprod(1.0 + daily)
    n = len(daily)
    cagr = eq[-1] ** (252.0 / n) - 1.0 if n > 0 and eq[-1] > 0 else float("nan")
    peak = np.maximum.accumulate(eq)
    maxdd = float((eq / peak - 1.0).min())
    vol = daily.std() * np.sqrt(252)
    sharpe = (daily.mean() * 252) / vol if vol > 0 else 0.0
    return {"cagr_pct": round(100 * cagr, 2), "maxdd_pct": round(100 * maxdd, 2), "sharpe": round(sharpe, 3)}


def analyze(dates, closes, *, L=126, cost_bps=2.0, era_start=0, n_null=2000, rng=None):
    r = np.zeros(len(closes)); r[1:] = closes[1:] / closes[:-1] - 1.0
    sig = np.zeros(len(closes))
    for t in range(L + 1, len(closes)):
        sig[t] = 1.0 if (closes[t - 1] / closes[t - 1 - L] - 1.0) > 0 else 0.0
    flips = np.abs(np.diff(sig, prepend=sig[0]))
    strat_net = sig * r - flips * (cost_bps / 1e4)

    valid = np.zeros(len(closes), bool); valid[L + 1:] = True
    mask = valid & np.array([d.year >= era_start for d in dates])
    if mask.sum() < 252:
        return None
    r_e, sig_e, strat_e = r[mask], sig[mask], strat_net[mask]
    gross_e = sig_e * r_e
    f = float(sig_e.mean())

    # Random-timing null: same fraction of days long, randomly placed (gross, no flip cost).
    nlong = int(round(f * len(r_e)))
    idx = np.arange(len(r_e))
    null_means = np.empty(n_null)
    for k in range(n_null):
        pick = rng.choice(idx, size=nlong, replace=False)
        null_means[k] = r_e[pick].sum() / len(r_e)
    null_p95 = float(np.percentile(null_means, 95))
    ts_gross_mean = float(gross_e.mean())
    emp_pct = float((null_means < ts_gross_mean).mean())

    return {
        "n_days": int(mask.sum()), "first_year": dates[np.argmax(mask)].year, "long_frac": round(f, 3),
        "buy_hold": perf(r_e), "tsmom_net": perf(strat_e),
        "ts_gross_mean_bps": round(1e4 * ts_gross_mean, 3),
        "null_p95_bps": round(1e4 * null_p95, 3),
        "real_vs_null_pctile": round(emp_pct, 4),
        "beats_timing_null": bool(ts_gross_mean > null_p95),
    }


def main() -> int:
    rng = np.random.default_rng(7)
    eras = [0, 2000, 2010, 2016]
    report = {"strategy": "tsmom_126_250_2_10 (long when trailing 126d return>0)", "by_index": {}}
    print("=" * 100)
    print("INDEX TIME-SERIES MOMENTUM (the active proof lead) — long-only, 126d, 2bps/flip cost")
    print("beats_null = tsmom's in-market days beat a random-timing null (same days-in-market) p95")
    print("=" * 100)
    for label, fname in FILES.items():
        dates, closes = load(fname)
        report["by_index"][label] = {}
        print(f"\n{label} ({dates[0]} -> {dates[-1]}, {len(closes)} days):")
        print(f"  {'era':>6} {'days':>6} {'long%':>6} | {'BH cagr/maxDD/Sh':>22} | {'TSMOM cagr/maxDD/Sh':>24} | beats_null (pctile)")
        for era in eras:
            r = analyze(dates, closes, era_start=era, rng=rng)
            if r is None:
                continue
            report["by_index"][label][str(era)] = r
            bh, ts = r["buy_hold"], r["tsmom_net"]
            tag = f"{era}+" if era else "all"
            beats = "YES" if r["beats_timing_null"] else "no"
            print(f"  {tag:>6} {r['n_days']:>6} {r['long_frac']*100:>5.0f}% | "
                  f"{bh['cagr_pct']:>6.2f}/{bh['maxdd_pct']:>7.2f}/{bh['sharpe']:>5.2f}      | "
                  f"{ts['cagr_pct']:>6.2f}/{ts['maxdd_pct']:>7.2f}/{ts['sharpe']:>5.2f}        | "
                  f"{beats:>3} ({r['real_vs_null_pctile']:.3f})")
    print("\n" + "-" * 100)
    print("READ: 'beats_null=YES' = the momentum TIMING adds return over random days-in-market (alpha).")
    print("If beats_null=no but TSMOM maxDD is much smaller than BH, that's DRAWDOWN CONTROL (beta-")
    print("management) — real and valuable on a LEVERAGED account, but not an alpha edge. Modern eras decide.")
    print("=" * 100)
    out = Path("evidence_runs/index_tsmom"); out.mkdir(parents=True, exist_ok=True)
    (out / "index-tsmom-report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"report: {out / 'index-tsmom-report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
