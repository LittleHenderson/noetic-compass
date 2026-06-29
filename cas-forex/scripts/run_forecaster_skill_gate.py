"""Forecaster skill-gate — fill the empty chronos_signal slot the app shows.

The one signal class never tested here: a real PRETRAINED forecaster (Chronos-Bolt), not
a fixed rule. Question, asked straight: does it have genuine next-bar DIRECTIONAL skill,
out-of-sample, that beats a shuffled-label null? If yes, it is the first real fuel — it
drops into the existing forecast harness as chronos_signal and everything downstream
(sizing, compounding, the proof) finally has something true to run on. If no, we close it
and move on. No fabrication: causal context only, held-out tail, the sacred null.

Tested on EUR/USD (resampled from your real HistData M1) + US30/NAS100/SPX (D1).
PASS = directional hit-rate beats the shuffled-label null p95 AND Brier beats the base rate.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass


def load_series():
    import pandas as pd
    from cas_forex.macro_intraday import load_histdata_m1

    series = {}
    files = sorted(glob.glob("data/external/*EURUSD*M1*.csv"))
    if files:
        candles = load_histdata_m1(files)
        df = pd.DataFrame(candles)
        df["ts"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("ts")
        for tf, rule in (("D1", "1D"), ("H1", "1h")):
            close = df["close"].resample(rule).last().dropna()
            series[f"EURUSD_{tf}"] = close.to_numpy(dtype=float)
    for label, fn in (("US30", "yf_idx_DJI_d1_max.csv"),
                      ("NAS100", "yf_idx_NDX_d1_max.csv"),
                      ("SPX500", "yf_idx_GSPC_d1_max.csv")):
        p = Path("data/external") / fn
        if p.exists():
            dfx = pd.read_csv(p).dropna(subset=["Close"])
            series[f"{label}_D1"] = dfx["Close"].to_numpy(dtype=float)
    return series


def directional_skill(closes, pipe, *, ctx, tail, batch, n_null, rng):
    import torch

    n = len(closes)
    start = max(ctx, n - tail)
    idxs = list(range(start, n))  # predict closes[i] from closes[:i] (strictly causal)
    qlevels = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    pred_up, realized_up, p_up = [], [], []
    for b0 in range(0, len(idxs), batch):
        chunk = idxs[b0:b0 + batch]
        contexts = [torch.tensor(closes[max(0, i - ctx):i], dtype=torch.float32) for i in chunk]
        q, _mean = pipe.predict_quantiles(contexts, prediction_length=1, quantile_levels=qlevels)
        qn = q[:, 0, :].detach().cpu().numpy()
        for j, i in enumerate(chunk):
            last, nxt = closes[i - 1], closes[i]
            qv = np.sort(qn[j])
            pred_up.append(1 if qv[4] > last else 0)        # median forecast vs last close
            realized_up.append(1 if nxt > last else 0)
            if last <= qv[0]:
                pu = 1.0
            elif last >= qv[-1]:
                pu = 0.0
            else:
                pu = 1.0 - float(np.interp(last, qv, qlevels))  # P(next > last) from the forecast CDF
            p_up.append(pu)
    pred_up = np.array(pred_up); realized_up = np.array(realized_up); p_up = np.array(p_up)
    hit = float((pred_up == realized_up).mean())
    base = float(realized_up.mean())
    brier = float(((p_up - realized_up) ** 2).mean())
    brier_base = float(((base - realized_up) ** 2).mean())
    null = np.array([(pred_up == rng.permutation(realized_up)).mean() for _ in range(n_null)])
    p95 = float(np.percentile(null, 95))
    return {
        "n": int(len(pred_up)), "hit": round(hit, 4), "base_rate": round(base, 4),
        "null_p95": round(p95, 4), "beats_null": bool(hit > p95),
        "brier": round(brier, 5), "brier_base": round(brier_base, 5),
        "brier_better_than_base": bool(brier < brier_base),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="amazon/chronos-bolt-small")
    ap.add_argument("--ctx", type=int, default=256)
    ap.add_argument("--tail", type=int, default=1200)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--n-null", type=int, default=2000)
    args = ap.parse_args()

    import torch
    from chronos import BaseChronosPipeline

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[load] {args.model} on {dev} ...", flush=True)
    pipe = BaseChronosPipeline.from_pretrained(args.model, device_map=dev, torch_dtype=torch.float32)
    rng = np.random.default_rng(7)
    series = load_series()
    print(f"[data] {len(series)} series: {list(series)}", flush=True)

    print("=" * 96)
    print(f"FORECASTER SKILL-GATE (Chronos-Bolt) — next-bar direction, OOS tail={args.tail}, ctx={args.ctx}")
    print("PASS = hit-rate beats shuffled-label null p95 AND Brier beats base-rate (calibrated edge)")
    print("=" * 96)
    print(f"  {'series':>12} {'N':>5} {'hit':>7} {'base':>7} {'nullp95':>8} {'beats':>6} {'brier':>9} {'vs_base':>8}")
    report = {}
    for name, closes in series.items():
        if len(closes) < args.ctx + 50:
            continue
        r = directional_skill(closes, pipe, ctx=args.ctx, tail=args.tail, batch=args.batch,
                              n_null=args.n_null, rng=rng)
        report[name] = r
        print(f"  {name:>12} {r['n']:>5} {r['hit']:>7.3f} {r['base_rate']:>7.3f} {r['null_p95']:>8.3f} "
              f"{('YES' if r['beats_null'] else 'no'):>6} {r['brier']:>9.4f} "
              f"{('better' if r['brier_better_than_base'] else 'worse'):>8}", flush=True)
    print("=" * 96)
    any_edge = any(r["beats_null"] and r["brier_better_than_base"] for r in report.values())
    print("VERDICT: " + ("a series shows real next-bar skill — investigate + cost-test before any claim."
                         if any_edge else
                         "NO real next-bar directional skill on any series (the expected, honest result)."))
    out = Path("evidence_runs/forecaster"); out.mkdir(parents=True, exist_ok=True)
    (out / "forecaster-skill-gate-report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"report: {out / 'forecaster-skill-gate-report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
