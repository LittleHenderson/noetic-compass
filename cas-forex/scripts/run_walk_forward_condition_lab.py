"""Walk-forward test for CAS FOREX RPM condition routes.

Learns a route map on each training window, freezes it, then evaluates only the
next untouched test window. This is research-only evidence, not live permission.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.condition_lab import (
    build_strategy_settings,
    default_real_period_for_timeframe,
    normalize_timeframe,
    yfinance_interval_for_timeframe,
)
from cas_forex.event_context import event_windows_from_macro_events
from cas_forex.instruments import yahoo_ticker
from cas_forex.time_utils import utc_now
from cas_forex.verifier.macro_gate import StaticMacroCalendarProvider
from cas_forex.walk_forward import (
    evaluate_walk_forward_routes,
    serialize_walk_forward_report,
    summarize_walk_forward_windows,
)


def fetch_real_candles(symbol: str, period: str, interval: str) -> List[dict]:
    import yfinance as yf

    ticker = yf.Ticker(yahoo_ticker(symbol))
    df = ticker.history(period=period, interval=interval, auto_adjust=False)
    if df is None or df.empty:
        return []
    candles: List[dict] = []
    for idx, row in df.iterrows():
        close = float(row["Close"])
        if close <= 0:
            continue
        candles.append({
            "timestamp": idx.isoformat(),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": close,
            "volume": int(row.get("Volume", 0) or 0),
        })
    return candles


def _print_windows(windows, limit: int = 24) -> None:
    print("\nWALK-FORWARD WINDOWS")
    print("-" * 136)
    print(
        f"{'sym':7} {'tf':>4} {'idx':>3} {'test_start':19} {'test_end':19} "
        f"{'event':18} {'regime':12} {'vol':>4} {'route':26} {'ret%':>8} {'dd%':>7} {'trades':>7}"
    )
    print("-" * 136)
    for i, window in enumerate(windows[:limit]):
        route = window.setting if window.route_action == "ROUTE" else "NO_TRADE"
        print(
            f"{window.symbol:7} {window.timeframe:>4} {window.window_index:>3} "
            f"{str(window.test_start_timestamp or '')[:19]:19} {str(window.test_end_timestamp or '')[:19]:19} "
            f"{window.test_event_context[:18]:18} {window.test_regime:12} {window.test_vol_mult:>4.1f} {route[:26]:26} "
            f"{window.test_return_pct:>8.2f} {window.test_max_dd_pct:>7.2f} {window.test_trades:>7}"
        )
    if len(windows) > limit:
        print(f"... {len(windows) - limit} more windows in JSON report")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="*", default=["NAS100", "US30", "EUR/USD", "GBP/USD", "AUD/USD"])
    parser.add_argument("--families", nargs="*", default=None,
                        help="Optional strategy families: trend_sma breakout meanrev range_scalper tsmom pullback")
    parser.add_argument("--settings", nargs="*", default=["tsmom_252_500_2_8", "range_scalper_24_120"],
                        help="Exact setting names from the Condition Lab registry")
    parser.add_argument("--timeframes", nargs="*", default=["D1"])
    parser.add_argument("--event-source", choices=["none", "static_macro"], default="none",
                        help="Optional event-context labeling source. static_macro uses the static 2026 seed calendar only.")
    parser.add_argument("--period", default="auto")
    parser.add_argument("--interval", default="auto")
    parser.add_argument("--train-bars", type=int, default=756)
    parser.add_argument("--test-bars", type=int, default=126)
    parser.add_argument("--step-bars", type=int, default=None)
    parser.add_argument("--train-segment-bars", type=int, default=252)
    parser.add_argument("--train-step-bars", type=int, default=63)
    parser.add_argument("--starting-balance", type=float, default=10_000.0)
    parser.add_argument("--position-lots", type=float, default=0.05)
    parser.add_argument("--spread-pips", type=float, default=1.0)
    parser.add_argument("--extra-cost-pips", type=float, default=0.5)
    parser.add_argument("--rpm-min-trades", type=float, default=3.0)
    parser.add_argument("--rpm-max-dd", type=float, default=20.0)
    parser.add_argument("--rpm-min-return", type=float, default=0.0)
    parser.add_argument("--output-dir", default="evidence_runs/walk_forward_condition_lab")
    args = parser.parse_args()

    settings = build_strategy_settings()
    if args.families:
        wanted = set(args.families)
        settings = [s for s in settings if s.family in wanted]
    if args.settings:
        wanted = set(args.settings)
        settings = [s for s in settings if s.name in wanted]
    if not settings:
        raise SystemExit("No strategy settings selected.")

    timeframes = [normalize_timeframe(tf) for tf in args.timeframes]
    print("=" * 118)
    print("CAS FOREX WALK-FORWARD CONDITION LAB")
    print("=" * 118)
    print(f"symbols={args.symbols} settings={[s.name for s in settings]} timeframes={timeframes}")
    print(f"train_bars={args.train_bars} test_bars={args.test_bars} step_bars={args.step_bars or args.test_bars}")
    print("NOTE: research-only walk-forward evidence. Live trading remains NOT LICENSED.")

    all_reports = []
    all_windows = []
    fetch_meta = []
    event_windows = None
    if args.event_source == "static_macro":
        event_windows = event_windows_from_macro_events(StaticMacroCalendarProvider().events())
        print(f"event_source=static_macro windows={len(event_windows)}")
    for timeframe in timeframes:
        interval = args.interval if args.interval != "auto" else yfinance_interval_for_timeframe(timeframe)
        if interval is None:
            print(f"\n{timeframe}: skipped; no Yahoo interval. Use broker data or aggregation.", flush=True)
            continue
        period = args.period if args.period != "auto" else default_real_period_for_timeframe(timeframe)
        candles_by_symbol: Dict[str, List[dict]] = {}
        print(f"\n[fetch] timeframe={timeframe} interval={interval} period={period}", flush=True)
        for symbol in args.symbols:
            candles = fetch_real_candles(symbol, period, interval)
            print(f"  {symbol}: {len(candles)} bars", flush=True)
            fetch_meta.append({"symbol": symbol, "timeframe": timeframe, "interval": interval, "period": period, "bars": len(candles)})
            if candles:
                candles_by_symbol[symbol] = candles

        report = evaluate_walk_forward_routes(
            candles_by_symbol=candles_by_symbol,
            settings=settings,
            timeframe=timeframe,
            event_windows=event_windows,
            train_bars=args.train_bars,
            test_bars=args.test_bars,
            step_bars=args.step_bars,
            train_segment_bars=args.train_segment_bars,
            train_step_bars=args.train_step_bars,
            starting_balance=args.starting_balance,
            position_lots=args.position_lots,
            spread_pips=args.spread_pips,
            extra_cost_pips=args.extra_cost_pips,
            rpm_min_trades=args.rpm_min_trades,
            rpm_max_dd=args.rpm_max_dd,
            rpm_min_return=args.rpm_min_return,
        )
        all_reports.append((timeframe, report))
        all_windows.extend(report.windows)
        print(f"[{timeframe}] {report.summary}", flush=True)

    combined_summary = summarize_walk_forward_windows(all_windows, max_oos_drawdown_pct=args.rpm_max_dd)
    print("\nCOMBINED SUMMARY")
    print("-" * 118)
    print(json.dumps(combined_summary, indent=2))
    _print_windows(all_windows)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"walk-forward-{utc_now().strftime('%Y%m%d%H%M%S')}"
    report_json = {
        "run_id": run_id,
        "generated_at": utc_now().isoformat(),
        "arguments": vars(args),
        "fetch_meta": fetch_meta,
        "settings": [{"name": s.name, "family": s.family, "params": s.params} for s in settings],
        "combined_summary": combined_summary,
        "timeframe_reports": {
            timeframe: serialize_walk_forward_report(report)
            for timeframe, report in all_reports
        },
        "claim_boundary": "Research-only walk-forward result. Not a live trading authorization.",
    }
    path = out_dir / f"{run_id}-report.json"
    path.write_text(json.dumps(report_json, indent=2), encoding="utf-8")
    print(f"\nreport written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
