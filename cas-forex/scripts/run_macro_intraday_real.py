"""Real intraday macro-surprise test: does a US macro surprise predict the EUR/USD
move in the minutes AFTER the print, at M1 resolution?

This is the higher-resolution rerun of the daily test (which found a faint
sub-significance tilt). It feeds:
  * REAL point-in-time surprises  — Forex Factory calendar (consensus Forecast + Actual
    + release DATE; standard-direction US high-impact events only), and
  * REAL broker-grade M1 bars     — HistData ASCII M1 EUR/USD archives the operator
    supplies in data/external/ (NOT yfinance — its M1 is only ~7 days),
through the leak-free OOS + shuffled-surprise null core. Release instants are assigned
from the canonical DST-correct schedule (the calendar's scraped intraday times are
unreliable; the schedule is not). The HistData EST-no-DST timestamps and the ET-with-DST
releases are BOTH converted to true UTC before alignment (the timezone trap).

NEVER fabricates data. The verdict is the PRE-REGISTERED PRIMARY window; secondary
windows are reported as exploratory robustness, never as the headline.

Get the data (one-time, free, no scraping):
  1. M1 bars  : HistData.com -> "Free Forex Historical Data" -> ASCII -> M1 (1 Minute Bar)
                -> EUR/USD -> download each year's ZIP, unzip the DAT_ASCII_*_M1_*.csv into
                data/external/  (the operator supplies these; do not auto-scrape HistData).
  2. Calendar : curl -sL -o data/external/ff_calendar.csv \
                "https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar/resolve/main/forex_factory_cache.csv"

Run:
  python scripts/run_macro_intraday_real.py --m1-glob "data/external/*EURUSD*M1*.csv"
  python scripts/run_macro_intraday_real.py --self-test     # synthetic harness check (no data)
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Never crash on a strict Windows console when printing the report.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

from cas_forex import macro_intraday as mi


def parse_value(raw: Optional[str]) -> Optional[float]:
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
        value = float(s) * mult
    except ValueError:
        return None
    # Reject 'inf'/'nan' (float() accepts them) so a garbage cell can never silently
    # shape the verdict — it is dropped and counted, not coerced into a surprise.
    return value if math.isfinite(value) else None


def load_calendar(csv_path: str, currency: str) -> Dict[str, List[dict]]:
    """{indicator: [{date, surprise_raw}]} for standard-direction high-impact events."""
    by_event: Dict[str, List[dict]] = defaultdict(list)
    with open(csv_path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (row.get("Currency") or "").strip() != currency:
                continue
            if "high impact" not in (row.get("Impact") or "").lower():
                continue
            # Standard direction only: actual > forecast is bullish for the currency,
            # so a single learned sign is valid across the pooled indicators.
            if "greater than 'forecast' is good" not in (row.get("Detail") or "").lower():
                continue
            actual = parse_value(row.get("Actual"))
            forecast = parse_value(row.get("Forecast"))
            if actual is None or forecast is None:
                continue
            # The release DATE is the reliable field. The cache stores DateTime in a
            # fixed +03:30/+04:30 wall clock with 00:00 placeholders for un-timed events,
            # but the DATE portion equals the true US release date (verified 24/24 against
            # published NFP dates). So the date is SLICED, never timezone-converted
            # (converting the 00:00 placeholder instant would wrongly shift it back a day);
            # release_utc() then stamps the canonical ET release time onto that date.
            day = (row.get("DateTime") or "").strip()[:10]
            try:
                date.fromisoformat(day)
            except ValueError:
                continue
            by_event[(row.get("Event") or "").strip()].append(
                {"date": day, "surprise_raw": actual - forecast}
            )
    return by_event


def _print_window(tag: str, s: dict) -> None:
    w = s.get("window", {})
    verdict = s.get("verdict")
    if "hit_rate" not in s:  # UNDERPOWERED / degenerate summary has no metric fields
        print(f"  [{tag}] {w.get('label','')}: verdict={verdict}  "
              f"usable={s.get('usable_events')} test={s.get('test_events')}  "
              f"reason={s.get('reason')}")
        return
    print(f"  [{tag}] {w.get('label','')}: verdict={verdict}  "
          f"usable={s.get('usable_events')} test={s.get('test_events')}  "
          f"hit={s.get('hit_rate')}  net%={s.get('net_return_pct')}  "
          f"null_p95%={s.get('null_p95_return_pct')}  beats_null={s.get('beats_null_p95')}")
    for r in s.get("not_edge_reasons", []) or []:
        print(f"        - {r}")


def run_self_test() -> int:
    print("SELF-TEST (HARNESS-VALIDATION-ONLY - synthetic data, NOT a market result):")
    for mode, expect in (("signal", "CANDIDATE_EDGE"), ("noise", "NO_SKILL")):
        lines, cal = mi.synthetic_histdata_and_calendar(mode=mode, n_events=90, seed=2)
        candles = mi.load_histdata_m1([], lines=lines)
        rep = mi.run_intraday_macro_test(cal, candles, symbol="EUR/USD", secondary=(),
                                         n_null=400, seed=5)
        v = rep.primary["verdict"]
        ok = "OK" if v == expect else "FAIL"
        print(f"  mode={mode:6} -> {v:14} (expected {expect})  [{ok}]")
        _print_window(mode, rep.primary)
    print("Self-test proves the pipeline has power + discipline and aligns timezones.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--calendar-csv", default="data/external/ff_calendar.csv")
    p.add_argument("--m1-glob", default="data/external/*EURUSD*M1*.csv",
                   help="glob for HistData ASCII M1 EUR/USD CSVs supplied by the operator")
    p.add_argument("--currency", default="USD")
    p.add_argument("--fx-symbol", default="EUR/USD")
    p.add_argument("--n-null", type=int, default=500)
    p.add_argument("--min-history", type=int, default=6)
    p.add_argument("--output-dir", default="evidence_runs/macro_intraday")
    p.add_argument("--self-test", action="store_true",
                   help="run the synthetic power/discipline check and exit (no real data needed)")
    args = p.parse_args()

    if args.self_test:
        return run_self_test()

    m1_files = sorted(glob.glob(args.m1_glob))
    if not m1_files:
        print(f"[pending] No M1 files matched {args.m1_glob!r}.")
        print("This test needs broker-grade 1-minute EUR/USD bars (years of them).")
        print("Drop HistData ASCII M1 EUR/USD CSVs into data/external/ and re-run, e.g.:")
        print("  data/external/DAT_ASCII_EURUSD_M1_2022.csv  (one per year)")
        print("Then: python scripts/run_macro_intraday_real.py --m1-glob \"data/external/*EURUSD*M1*.csv\"")
        print("(Sanity-check the wiring now with: --self-test)")
        return 2

    if not Path(args.calendar_csv).exists():
        print(f"[pending] Calendar not found at {args.calendar_csv}. Download it (no scraping):")
        print('  curl -sL -o data/external/ff_calendar.csv '
              '"https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar/resolve/main/forex_factory_cache.csv"')
        return 2

    print(f"[load] calendar {args.calendar_csv} ...", flush=True)
    by_event = load_calendar(args.calendar_csv, args.currency)
    n_known = sum(1 for ev in by_event if mi.release_et_time(ev) is not None)
    print(f"  {len(by_event)} standard-direction high-impact {args.currency} indicators "
          f"({n_known} with a known release time)")

    print(f"[load] {len(m1_files)} HistData M1 file(s) ...", flush=True)
    candles = mi.load_histdata_m1(m1_files)
    if len(candles) < 1000:
        print(f"  only {len(candles)} M1 bars loaded — too few; check the files.")
        return 1
    print(f"  {len(candles)} M1 bars  {candles[0]['timestamp']} -> {candles[-1]['timestamp']}")

    rep = mi.run_intraday_macro_test(
        by_event, candles, symbol=args.fx_symbol,
        n_null=args.n_null, min_history=args.min_history,
    )

    print("\n" + "=" * 80)
    print(f"REAL INTRADAY MACRO-SURPRISE -> {args.fx_symbol}   (M1 post-release reaction)")
    print("-" * 80)
    print("PRIMARY (the verdict — pre-registered, most generous reasonable window):")
    _print_window("PRIMARY", rep.primary)
    print("\nSECONDARY (exploratory robustness — NOT the verdict, never cherry-picked):")
    for s in rep.secondary:
        _print_window("explore", s)
    print("\nPER-INDICATOR (in-sample descriptive — is the verdict broad or NFP/CPI-driven?):")
    for ev, st in sorted(rep.per_indicator.items(), key=lambda kv: -kv[1]["events"])[:20]:
        print(f"  {st['events']:4d}  raw_hit={st['raw_hit_rate']:.3f}  "
              f"mean_aligned%={st['mean_aligned_move_pct']:+.4f}  {ev}")
    print("-" * 80)
    print(f"skipped/collapsed: {rep.primary.get('skipped', {})}")
    print("CAVEATS: HistData EUR/USD M1 is interbank-ish (no real broker spread); the "
          "PRIMARY uses a news-realistic 2-pip round-trip. Surprise = Actual-Forecast, US "
          "standard-direction high-impact only; co-released indicators are collapsed to one "
          "window. Verdict = PRIMARY: beat the shuffled-null p95 (directional skill, cost held "
          "fixed) AND net>0 after cost. The pooled verdict is an NFP/CPI-dominated mixture.")
    print(mi.INTRADAY_CLAIM_BOUNDARY)
    print("=" * 80)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "macro-intraday-real-report.json"
    path.write_text(json.dumps({
        "fx_symbol": args.fx_symbol, "currency": args.currency,
        "m1_window": [candles[0]["timestamp"], candles[-1]["timestamp"]],
        "m1_bars": len(candles), "m1_files": m1_files,
        "indicators": len(by_event), "indicators_with_known_time": n_known,
        "primary": rep.primary, "secondary": rep.secondary,
        "per_indicator": rep.per_indicator,
        "claim_boundary": rep.claim_boundary,
    }, indent=2, default=str), encoding="utf-8")
    print(f"report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
