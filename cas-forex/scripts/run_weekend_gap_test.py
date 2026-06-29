"""Weekend-gap fade test — rank-1 survivor of the edge-research team, with a CONFLICT to
settle: one screener saw a real gross reversion (74-83% fill); another ran it and got
NO_SKILL even at zero cost. This resolves it directly on the on-disk HistData M1.

Hypothesis: the EUR/USD Sunday-open gap (Sunday-open minus Friday-close) over-shoots on
near-zero weekend liquidity and reverts when London arrives, so FADING the gap predicts
the move in the hours after the weekly open. Tested with the SAME sacred null core
(macro_surprise.evaluate_surprise_return_pairs): surprise = causal z of the signed gap,
ret = the forward return from entry (first liquid bar a few min after the open), null =
1000-perm shuffle of the gap<->forward-move link. Cost is the pre-registered decision
variable (the whole verdict turns on the achievable weekend-open spread).

Leak-free: gap z uses only PRIOR weekends; the forward return uses only bars AT/AFTER the
open; the sign is learned on TRAIN weekends and applied to strictly-later TEST weekends.
NEVER fabricates data. Run:
  python scripts/run_weekend_gap_test.py
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

from cas_forex.instruments import price_unit_size
from cas_forex.macro_intraday import causal_zscore, intraday_window_return, load_histdata_m1
from cas_forex.macro_surprise import _parse_time, evaluate_surprise_return_pairs


def find_weekend_open_indices(candles, min_gap_hours: float = 40.0):
    """Indices of the first bar AFTER each weekend gap (Sunday open).

    A weekend gap is a >= ~40h hole (the FX week is Fri 17:00 ET -> Sun 17:00 ET = 48h);
    the 40h floor captures weekends and excludes single-day (~24h) holiday gaps.
    """
    out = []
    prev_t = _parse_time(candles[0]["timestamp"])
    for i in range(1, len(candles)):
        t = _parse_time(candles[i]["timestamp"])
        if (t - prev_t).total_seconds() >= min_gap_hours * 3600:
            out.append(i)
        prev_t = t
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m1-glob", default="data/external/*EURUSD*M1*.csv")
    ap.add_argument("--symbol", default="EUR/USD")
    ap.add_argument("--entry-offset-min", type=int, default=5)
    ap.add_argument("--horizons-min", type=int, nargs="+", default=[60, 240, 360])
    ap.add_argument("--cost-pips", type=float, nargs="+", default=[0.0, 2.0, 2.5, 3.0, 4.0, 6.0])
    ap.add_argument("--n-null", type=int, default=1000)
    ap.add_argument("--output-dir", default="evidence_runs/weekend_gap")
    args = ap.parse_args()

    files = sorted(glob.glob(args.m1_glob))
    if not files:
        print(f"[pending] no M1 files matched {args.m1_glob!r}")
        return 2
    candles = load_histdata_m1(files)
    print(f"[load] {len(candles)} M1 bars  {candles[0]['timestamp']} -> {candles[-1]['timestamp']}")
    times_sec = [_parse_time(c["timestamp"]).timestamp() for c in candles]
    closes = [float(c["close"]) for c in candles]
    pip = price_unit_size(args.symbol)

    open_idxs = find_weekend_open_indices(candles)
    weekends = []
    for oi in open_idxs:
        weekends.append({
            "open_instant": _parse_time(candles[oi]["timestamp"]),
            "gap": closes[oi] - closes[oi - 1],   # Sunday-open minus Friday-close
            "fri_close": closes[oi - 1],
        })
    print(f"[gaps] {len(weekends)} weekend gaps detected  "
          f"(mean |gap| = {1e4 * (sum(abs(w['gap']) for w in weekends) / max(len(weekends),1)):.1f} pips)")

    gap_z = causal_zscore([w["gap"] for w in weekends], min_history=8)  # prior weekends only

    out_report = {"symbol": args.symbol, "n_weekends": len(weekends), "entry_offset_min": args.entry_offset_min, "horizons": {}}
    for H in args.horizons_min:
        rows, fades_aligned, n = [], 0, 0
        for w, z in zip(weekends, gap_z):
            if z is None:
                continue
            win = intraday_window_return(times_sec, closes, w["open_instant"],
                                         entry_offset_min=args.entry_offset_min, horizon_min=H, max_gap_min=30)
            if win is None:
                continue
            entry, ret = win
            rows.append({"surprise": float(z), "ret": float(ret), "entry": float(entry)})
            # descriptive: did the gap FADE (price move opposite the gap sign)?
            if (w["gap"] > 0 and ret < 0) or (w["gap"] < 0 and ret > 0):
                fades_aligned += 1
            n += 1
        gross_fade = fades_aligned / n if n else 0.0
        print(f"\n=== horizon {H:>3} min :: {n} usable weekends :: gross fade-aligned {gross_fade:.3f} "
              f"(>0.5 = gaps tend to revert) ===")
        h_rows = {"usable": n, "gross_fade_aligned": round(gross_fade, 4), "by_cost": {}}
        for cost in args.cost_pips:
            usable = [{"surprise": r["surprise"], "ret": r["ret"],
                       "cost_ret": (cost * pip) / r["entry"] if r["entry"] > 0 else 0.0} for r in rows]
            rep = evaluate_surprise_return_pairs(usable, symbol=args.symbol, horizon_bars=H, cost_pips=cost,
                                                 n_null=args.n_null, min_test_events=8, seed=11)
            s = rep.summary
            flag = "  <-- EDGE" if s.get("verdict") == "CANDIDATE_EDGE" else ""
            print(f"  cost {cost:>4.1f}p: {s.get('verdict'):<14} hit={s.get('hit_rate')} "
                  f"net%={s.get('net_return_pct')} null_p95%={s.get('null_p95_return_pct')} "
                  f"beats_null={s.get('beats_null_p95')}{flag}")
            h_rows["by_cost"][str(cost)] = {k: s.get(k) for k in
                ("verdict", "hit_rate", "net_return_pct", "null_p95_return_pct", "beats_null_p95", "test_events")}
        out_report["horizons"][str(H)] = h_rows

    # Pre-registered decision: PRIMARY = 6h horizon at >= 3.0 pip realistic weekend spread.
    primary = out_report["horizons"].get("360", {}).get("by_cost", {}).get("3.0", {})
    verdict = "CANDIDATE_EDGE" if primary.get("verdict") == "CANDIDATE_EDGE" else "NO_SKILL"
    print("\n" + "=" * 78)
    print(f"WEEKEND-GAP FADE -> {args.symbol}  ::  PRIMARY (6h, 3.0p) VERDICT: {verdict}")
    print("Decision rule (pre-registered): EDGE only if it beats the shuffled null p95 AND is")
    print("net-positive at >= 3.0 pip effective weekend-open spread. HistData M1 is interbank-")
    print("ish (generous); real retail weekend spreads run 3-8 pips, so this is the optimistic case.")
    print("=" * 78)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "weekend-gap-report.json").write_text(json.dumps(out_report, indent=2, default=str), encoding="utf-8")
    print(f"report: {out_dir / 'weekend-gap-report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
