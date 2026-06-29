"""Honest real-data test of the agent-built RANGE SCALPER (range_scalper_24_120) — the
strategy with the best logged numbers (+$2,686, 93.6% win rate on GBP/USD, PF 14.6).

Those numbers were on Yahoo DAILY proxy data with no real spread and never validated.
This gives the strategy a fair shot on real broker-grade data with real cost + the null:
event-driven backtest of make_low_vol_range_scalper_signal with its real ATR stops
(sl 2.0x / tp 0.8x ATR, the high-win-rate small-target profile), intrabar SL/TP fills,
a spread cost ladder, and a random-entry null (same trade count + same ATR risk profile).
EDGE = net-positive after realistic spread AND beats the random-entry null p95.

EUR/USD uses your REAL HistData M1 (resampled); GBP/USD & AUD/USD use yfinance D1 (the
instruments the original 93% claim was on). NEVER fabricates data.
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

from cas_forex.schemas.forecast import Direction
from cas_forex.forecast.strategies import make_low_vol_range_scalper_signal
from cas_forex.instruments import price_unit_size


def _resample_ohlc(candles, rule):
    import pandas as pd
    df = pd.DataFrame(candles)
    df["ts"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("ts")
    o = df["open"].resample(rule).first()
    h = df["high"].resample(rule).max()
    l = df["low"].resample(rule).min()
    c = df["close"].resample(rule).last()
    out = pd.concat([o, h, l, c], axis=1).dropna()
    out.columns = ["open", "high", "low", "close"]
    return out


def load_eurusd(tf_rule):
    from cas_forex.macro_intraday import load_histdata_m1
    files = sorted(glob.glob("data/external/*EURUSD*M1*.csv"))
    if not files:
        return None
    df = _resample_ohlc(load_histdata_m1(files), tf_rule)
    return df["open"].to_numpy(float), df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)


def load_yf(ticker, interval="1d", period="5y"):
    import yfinance as yf
    df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False).dropna()
    df = df[df["Close"] > 0]
    return (df["Open"].to_numpy(float), df["High"].to_numpy(float),
            df["Low"].to_numpy(float), df["Close"].to_numpy(float))


def _atr(h, l, c, i, period=14):
    trs = []
    for k in range(max(1, i - period + 1), i + 1):
        trs.append(max(h[k] - l[k], abs(h[k] - c[k - 1]), abs(l[k] - c[k - 1])))
    return float(np.mean(trs)) if trs else 0.0


def backtest(o, h, l, c, signal, *, pip, spread_pips, max_hold, atr_period=14, entries=None):
    """Event-driven backtest. If `entries` is given (list of (i, is_long)), it forces those
    entries (used for the random null); else it follows the signal. Returns trade pnl in pips."""
    n = len(c)
    trades = []
    fired = []
    pos = None
    i = atr_period + 1
    while i < n:
        if pos is None:
            go = None
            if entries is None:
                sig = signal(list(c[:i + 1]))
                if sig:
                    direction = sig[0]
                    sl_mult, tp_mult = (sig[2], sig[3]) if len(sig) >= 4 else (2.0, 0.8)
                    go = (direction == Direction.LONG, sl_mult, tp_mult)
            i += 1
            if go is not None:
                is_long, sl_mult, tp_mult = go
                a = _atr(h, l, c, i - 1, atr_period)
                if a <= 0:
                    continue
                entry = c[i - 1]
                sl = entry - sl_mult * a if is_long else entry + sl_mult * a
                tp = entry + tp_mult * a if is_long else entry - tp_mult * a
                pos = {"entry": entry, "sl": sl, "tp": tp, "long": is_long, "open_i": i - 1}
                fired.append((i - 1, is_long, sl_mult, tp_mult, a))
            continue
        # manage open position on bar i (check SL before TP = conservative)
        exit_px = None
        if pos["long"]:
            if l[i] <= pos["sl"]:
                exit_px = pos["sl"]
            elif h[i] >= pos["tp"]:
                exit_px = pos["tp"]
        else:
            if h[i] >= pos["sl"]:
                exit_px = pos["sl"]
            elif l[i] <= pos["tp"]:
                exit_px = pos["tp"]
        if exit_px is None and (i - pos["open_i"]) >= max_hold:
            exit_px = c[i]
        if exit_px is not None:
            sgn = 1.0 if pos["long"] else -1.0
            pnl_pips = sgn * (exit_px - pos["entry"]) / pip - spread_pips
            trades.append(pnl_pips)
            pos = None
        i += 1
    return np.array(trades), fired


def stats(trades):
    if len(trades) == 0:
        return {"trades": 0}
    wins = trades[trades > 0]
    losses = trades[trades < 0]
    pf = (wins.sum() / -losses.sum()) if losses.sum() < 0 else float("inf")
    return {
        "trades": int(len(trades)), "net_pips": round(float(trades.sum()), 1),
        "win_rate": round(float((trades > 0).mean()), 4),
        "profit_factor": round(float(pf), 2) if np.isfinite(pf) else None,
        "avg_pips": round(float(trades.mean()), 3),
    }


def run_symbol(label, ohlc, *, pip, spread_list, max_hold, n_null, rng):
    o, h, l, c = ohlc
    signal = make_low_vol_range_scalper_signal(lookback=24, baseline=120, z_entry=1.2,
                                               sl_mult=2.0, tp_mult=0.8)
    print(f"\n{label}  ({len(c)} bars)")
    # Real signal at each spread.
    base_trades, fired = backtest(o, h, l, c, signal, pip=pip, spread_pips=0.0, max_hold=max_hold)
    if len(base_trades) < 10:
        print(f"  only {len(base_trades)} signals — too few to judge."); return None
    out = {"bars": len(c), "by_spread": {}}
    for sp in spread_list:
        tr, _ = backtest(o, h, l, c, signal, pip=pip, spread_pips=sp, max_hold=max_hold)
        s = stats(tr)
        # Random-entry null at THIS spread: same #trades, random bars, random dir, same ATR risk profile.
        n_tr = len(fired)
        null_net = np.empty(n_null)
        valid_i = np.arange(atr_idx0(), len(c) - max_hold - 1)
        for k in range(n_null):
            picks = rng.choice(valid_i, size=min(n_tr, len(valid_i)), replace=False)
            ents = [(int(j), bool(rng.random() < 0.5)) for j in picks]
            ntr = _null_trades(o, h, l, c, ents, pip=pip, spread_pips=sp, max_hold=max_hold)
            null_net[k] = ntr.sum() if len(ntr) else 0.0
        p95 = float(np.percentile(null_net, 95))
        s["null_p95_pips"] = round(p95, 1)
        s["beats_null"] = bool(s.get("net_pips", -1) > p95)
        out["by_spread"][str(sp)] = s
        flag = "  <-- EDGE" if (s.get("net_pips", -1) > 0 and s["beats_null"]) else ""
        print(f"  spread {sp:>3.1f}p: trades={s['trades']:>4} win%={s['win_rate']:.3f} "
              f"PF={s['profit_factor']} net={s['net_pips']:>8.1f}p null_p95={s['null_p95_pips']:>7.1f}p "
              f"beats_null={s['beats_null']}{flag}")
    return out


_ATR_PERIOD = 14


def atr_idx0():
    return _ATR_PERIOD + 2


def _null_trades(o, h, l, c, entries, *, pip, spread_pips, max_hold, atr_period=14):
    trades = []
    for j, is_long in entries:
        a = _atr(h, l, c, j, atr_period)
        if a <= 0:
            continue
        entry = c[j]
        sl = entry - 2.0 * a if is_long else entry + 2.0 * a
        tp = entry + 0.8 * a if is_long else entry - 0.8 * a
        exit_px = None
        for i in range(j + 1, min(j + 1 + max_hold, len(c))):
            if is_long:
                if l[i] <= sl:
                    exit_px = sl; break
                if h[i] >= tp:
                    exit_px = tp; break
            else:
                if h[i] >= sl:
                    exit_px = sl; break
                if l[i] <= tp:
                    exit_px = tp; break
        if exit_px is None:
            exit_px = c[min(j + max_hold, len(c) - 1)]
        sgn = 1.0 if is_long else -1.0
        trades.append(sgn * (exit_px - entry) / pip - spread_pips)
    return np.array(trades)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-null", type=int, default=500)
    ap.add_argument("--max-hold", type=int, default=20)
    args = ap.parse_args()
    rng = np.random.default_rng(7)
    pip = price_unit_size("EUR/USD")
    spreads = [0.0, 1.0, 1.5, 2.0]
    report = {}
    print("=" * 100)
    print("RANGE SCALPER (range_scalper_24_120) — real-data test with intrabar ATR stops + random-entry null")
    print("sl 2.0x / tp 0.8x ATR (high-win-rate small-target profile). EDGE = net>0 after spread AND beats null p95.")
    print("=" * 100)

    # EUR/USD real HistData, multiple timeframes.
    for tf, rule in (("EURUSD_D1", "1D"), ("EURUSD_H1", "1h"), ("EURUSD_M15", "15min")):
        ohlc = load_eurusd(rule)
        if ohlc:
            r = run_symbol(tf, ohlc, pip=pip, spread_list=spreads, max_hold=args.max_hold, n_null=args.n_null, rng=rng)
            if r:
                report[tf] = r
    # GBP/USD & AUD/USD D1 (the original 93% claim instruments) via yfinance.
    for label, tk in (("GBPUSD_D1", "GBPUSD=X"), ("AUDUSD_D1", "AUDUSD=X")):
        try:
            ohlc = load_yf(tk, "1d", "5y")
        except Exception as exc:
            print(f"\n{label}: fetch failed ({exc})"); continue
        r = run_symbol(label, ohlc, pip=price_unit_size("GBP/USD"), spread_list=spreads,
                       max_hold=args.max_hold, n_null=args.n_null, rng=rng)
        if r:
            report[label] = r

    print("\n" + "=" * 100)
    any_edge = any(s.get("net_pips", -1) > 0 and s.get("beats_null")
                   for r in report.values() for s in r["by_spread"].values())
    print("VERDICT: " + ("a config shows net-positive AND beats the null — dig in + validate before any claim."
                         if any_edge else
                         "no config is net-positive AND beats the random-entry null after real spread."))
    out = Path("evidence_runs/range_scalper_realtest"); out.mkdir(parents=True, exist_ok=True)
    (out / "range-scalper-realtest-report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"report: {out / 'range-scalper-realtest-report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
