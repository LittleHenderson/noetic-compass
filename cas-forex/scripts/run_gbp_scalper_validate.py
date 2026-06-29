"""Stress-test the one thing that lit up: range_scalper on GBP/USD D1 (94% win, beats null,
but only 18 trades on free data). Before any claim, hammer it: longest available history
(more trades), walk-forward split, leave-one-out (is it one lucky trade?), and a parameter
jitter (is the edge knife-edge / overfit?). NEVER fabricates data.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

spec = importlib.util.spec_from_file_location("rst", str(ROOT / "scripts" / "run_range_scalper_test.py"))
rst = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rst)
from cas_forex.forecast.strategies import make_low_vol_range_scalper_signal
from cas_forex.instruments import price_unit_size

PIP = price_unit_size("GBP/USD")
RNG = np.random.default_rng(7)
SPREAD = 1.5
HOLD = 20


def null_p95(o, h, l, c, n_trades, *, n=1000):
    valid = np.arange(rst.atr_idx0(), len(c) - HOLD - 1)
    out = np.empty(n)
    for k in range(n):
        picks = RNG.choice(valid, size=min(n_trades, len(valid)), replace=False)
        ents = [(int(j), bool(RNG.random() < 0.5)) for j in picks]
        t = rst._null_trades(o, h, l, c, ents, pip=PIP, spread_pips=SPREAD, max_hold=HOLD)
        out[k] = t.sum() if len(t) else 0.0
    return float(np.percentile(out, 95))


def run(o, h, l, c, sig):
    tr, fired = rst.backtest(o, h, l, c, sig, pip=PIP, spread_pips=SPREAD, max_hold=HOLD)
    s = rst.stats(tr)
    if len(tr) >= 8:
        p95 = null_p95(o, h, l, c, len(tr))
        s["null_p95_pips"] = round(p95, 1)
        s["beats_null"] = bool(s.get("net_pips", -1) > p95)
    return tr, s


def main() -> int:
    sig = make_low_vol_range_scalper_signal(lookback=24, baseline=120, z_entry=1.2, sl_mult=2.0, tp_mult=0.8)
    print("=" * 92)
    print("GBP/USD RANGE-SCALPER STRESS TEST (spread 1.5p, the result that passed the null)")
    print("=" * 92)

    o, h, l, c = rst.load_yf("GBPUSD=X", "1d", "max")
    print(f"\n[1] LONGEST HISTORY — GBP/USD D1, {len(c)} bars")
    tr, s = run(o, h, l, c, sig)
    print(f"    {s}")

    print(f"\n[2] WALK-FORWARD — same rules, two halves (does it hold out-of-sample?)")
    mid = len(c) // 2
    for name, a, b in [("first half ", 0, mid), ("second half", mid, len(c))]:
        _, s2 = run(o[a:b], h[a:b], l[a:b], c[a:b], sig)
        print(f"    {name}: {s2}")

    print(f"\n[3] LEAVE-ONE-OUT — drop the single biggest winning trade (is it one lucky trade?)")
    if len(tr) > 3:
        loo = tr[tr != tr.max()]
        s3 = rst.stats(loo)
        print(f"    without top win: {s3}  (net was {round(float(tr.sum()),1)}p with {len(tr)} trades)")
        # also drop top 3
        thr = np.sort(tr)[-3] if len(tr) > 4 else tr.max()
        loo3 = tr[tr < thr]
        print(f"    without top 3 wins: {rst.stats(loo3)}")

    print(f"\n[4] PARAMETER JITTER — is the edge robust or knife-edge/overfit?")
    for lb, bl, z, sl, tp in [(24, 120, 1.2, 2.0, 0.8), (20, 120, 1.2, 2.0, 0.8), (28, 120, 1.2, 2.0, 0.8),
                              (24, 100, 1.2, 2.0, 0.8), (24, 120, 1.0, 2.0, 0.8), (24, 120, 1.5, 2.0, 0.8),
                              (24, 120, 1.2, 2.0, 1.0), (24, 120, 1.2, 1.5, 0.8)]:
        sj = make_low_vol_range_scalper_signal(lookback=lb, baseline=bl, z_entry=z, sl_mult=sl, tp_mult=tp)
        _, ss = run(o, h, l, c, sj)
        tag = f"lb{lb} bl{bl} z{z} sl{sl} tp{tp}"
        print(f"    {tag:<34}: trades={ss.get('trades')} win%={ss.get('win_rate')} "
              f"net={ss.get('net_pips')}p beats_null={ss.get('beats_null')}")
    print("=" * 92)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
