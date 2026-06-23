"""CAS FOREX condition lab.

Sweeps strategy settings across synthetic CAS-SDG regimes and/or real-data
condition slices. Each cell is classified by CJT operating region, nested
lacunarity maps the gaps, and RPM emits a route/no-trade table.

Examples:

  python scripts/run_condition_lab.py --source synthetic --symbols NAS100 US30

  python scripts/run_condition_lab.py --source real --symbols NAS100 US30 \
    --real-period 5y --segment-bars 420 --step-bars 60

This is research infrastructure only. It cannot unlock live trading.
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
    nested_lacunarity_by_axes,
    normalize_timeframe,
    rpm_route_table,
    run_real_condition_grid,
    run_synthetic_condition_grid,
    serialize_cell,
    yfinance_interval_for_timeframe,
)
from cas_forex.event_context import event_windows_from_macro_events, normalize_event_context
from cas_forex.instruments import yahoo_ticker
from cas_forex.regime_sim import REGIMES
from cas_forex.time_utils import utc_now
from cas_forex.verifier.macro_gate import StaticMacroCalendarProvider


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


def _print_top_cells(cells, limit: int = 12) -> None:
    ranked = sorted(cells, key=lambda c: c.score, reverse=True)
    print("\nTOP NON-GAP CELLS")
    print("-" * 140)
    print(f"{'source':9} {'symbol':7} {'tf':>5} {'scale':>7} {'event':18} {'regime':12} {'vol':>4} {'setting':24} {'ret%':>8} {'dd%':>7} {'trades':>7} {'region':>10} {'score':>8}")
    print("-" * 140)
    shown = 0
    for c in ranked:
        if c.is_gap:
            continue
        print(
            f"{c.source:9} {c.symbol:7} {c.timeframe:>5} {c.time_scale:>7} {c.event_context[:18]:18} {c.regime:12} {c.vol_mult:>4.1f} "
            f"{c.setting[:24]:24} {c.mean_return_pct:>8.2f} {c.mean_max_dd_pct:>7.2f} "
            f"{c.mean_trades:>7.1f} {c.region.value:>10} {c.score:>8.2f}"
        )
        shown += 1
        if shown >= limit:
            break


def _print_routes(routes: Dict[str, Dict[str, object]], limit: int = 20) -> None:
    route_count = sum(1 for r in routes.values() if r["action"] == "ROUTE")
    no_trade_count = len(routes) - route_count
    print("\nRPM ROUTE TABLE")
    print("-" * 110)
    print(f"routes={route_count}  no_trade={no_trade_count}  total_conditions={len(routes)}")
    print("-" * 110)
    shown = 0
    for key, route in routes.items():
        if route["action"] == "NO_TRADE":
            line = f"{key} -> NO_TRADE"
        else:
            line = (
                f"{key} -> {route['setting']} "
                f"(ret {route['mean_return_pct']}%, dd {route['mean_max_dd_pct']}%, "
                f"beta {route['beta']}, score {route['score']})"
            )
        print(line)
        shown += 1
        if shown >= limit:
            if len(routes) > limit:
                print(f"... {len(routes) - limit} more routes in JSON report")
            break


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["synthetic", "real", "both"], default="synthetic")
    parser.add_argument("--symbols", nargs="*", default=["NAS100", "US30"])
    parser.add_argument("--families", nargs="*", default=None,
                        help="Optional strategy families: trend_sma breakout meanrev range_scalper tsmom pullback")
    parser.add_argument("--settings", nargs="*", default=None,
                        help="Optional exact setting names from the registry")
    parser.add_argument("--regimes", nargs="*", default=REGIMES)
    parser.add_argument("--vol-mults", type=float, nargs="*", default=[0.5, 1.0, 2.0])
    parser.add_argument("--timeframes", nargs="*", default=["D1"],
                        help="CAS timeframes to nest: S1 S5 M1 M15 H1 H4 D1 W1 MN1 Y1")
    parser.add_argument("--event-contexts", nargs="*", default=["normal"],
                        help="Synthetic event contexts: normal pre_NFP post_NFP pre_CPI post_FOMC conflict_shock liquidity_thin")
    parser.add_argument("--real-event-source", choices=["none", "static_macro"], default="none",
                        help="Optional real-data event labeling source. static_macro uses the static 2026 seed calendar only.")
    parser.add_argument("--seeds", type=int, default=2)
    parser.add_argument("--bars", type=int, default=420)
    parser.add_argument("--real-period", default="auto")
    parser.add_argument("--real-interval", default="auto")
    parser.add_argument("--segment-bars", type=int, default=420)
    parser.add_argument("--step-bars", type=int, default=60)
    parser.add_argument("--starting-balance", type=float, default=10_000.0)
    parser.add_argument("--position-lots", type=float, default=0.05)
    parser.add_argument("--spread-pips", type=float, default=1.0)
    parser.add_argument("--extra-cost-pips", type=float, default=0.5)
    parser.add_argument("--rpm-min-trades", type=float, default=5.0)
    parser.add_argument("--rpm-max-dd", type=float, default=20.0)
    parser.add_argument("--rpm-min-return", type=float, default=0.0)
    parser.add_argument("--output-dir", default="evidence_runs/condition_lab")
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

    print("=" * 110)
    print("CAS FOREX CONDITION LAB")
    print("=" * 110)
    args.timeframes = [normalize_timeframe(timeframe) for timeframe in args.timeframes]
    args.event_contexts = [normalize_event_context(event_context) for event_context in args.event_contexts]
    print(f"source={args.source} symbols={args.symbols} settings={len(settings)} timeframes={args.timeframes} events={args.event_contexts}")
    print(f"cost={args.spread_pips + args.extra_cost_pips} movement-units | position_lots={args.position_lots}")
    print("NOTE: research stress map only. Live trading remains NOT LICENSED.")

    cells = []
    if args.source in ("synthetic", "both"):
        print("\n[synthetic] running CAS-SDG condition grid ...", flush=True)
        cells.extend(
            run_synthetic_condition_grid(
                symbols=args.symbols,
                settings=settings,
                regimes=args.regimes,
                vol_mults=args.vol_mults,
                timeframes=args.timeframes,
                event_contexts=args.event_contexts,
                seeds=args.seeds,
                bars=args.bars,
                starting_balance=args.starting_balance,
                position_lots=args.position_lots,
                spread_pips=args.spread_pips,
                extra_cost_pips=args.extra_cost_pips,
            )
        )
        print(f"[synthetic] cells={len(cells)}", flush=True)

    if args.source in ("real", "both"):
        print("\n[real] fetching and slicing real candles ...", flush=True)
        event_windows = None
        if args.real_event_source == "static_macro":
            event_windows = event_windows_from_macro_events(StaticMacroCalendarProvider().events())
            print(f"  event_source=static_macro windows={len(event_windows)}", flush=True)
        total_real_cells = 0
        for timeframe in args.timeframes:
            interval = args.real_interval if args.real_interval != "auto" else yfinance_interval_for_timeframe(timeframe)
            if interval is None:
                print(
                    f"  {timeframe}: skipped; Yahoo has no native interval. "
                    "Use broker tick data or an aggregation layer for real-data cells.",
                    flush=True,
                )
                continue
            period = args.real_period if args.real_period != "auto" else default_real_period_for_timeframe(timeframe)
            candles_by_symbol: Dict[str, List[dict]] = {}
            print(f"  timeframe={timeframe} interval={interval} period={period}", flush=True)
            for symbol in args.symbols:
                candles = fetch_real_candles(symbol, period, interval)
                print(f"    {symbol}: {len(candles)} bars", flush=True)
                if candles:
                    candles_by_symbol[symbol] = candles
            real_cells = run_real_condition_grid(
                candles_by_symbol=candles_by_symbol,
                settings=settings,
                timeframe=timeframe,
                event_windows=event_windows,
                segment_bars=args.segment_bars,
                step_bars=args.step_bars,
                starting_balance=args.starting_balance,
                position_lots=args.position_lots,
                spread_pips=args.spread_pips,
                extra_cost_pips=args.extra_cost_pips,
            )
            cells.extend(real_cells)
            total_real_cells += len(real_cells)
            print(f"  {timeframe}: cells={len(real_cells)}", flush=True)
        print(f"[real] cells={total_real_cells}", flush=True)

    lacunarity = nested_lacunarity_by_axes(cells)
    routes = rpm_route_table(
        cells,
        min_trades=args.rpm_min_trades,
        max_drawdown_pct=args.rpm_max_dd,
        min_return_pct=args.rpm_min_return,
    )

    print("\nNESTED LACUNARITY")
    print("-" * 110)
    print(f"overall_gap_fraction={lacunarity['overall']:.4f}")
    for key in sorted(k for k in lacunarity if k != "overall")[:24]:
        print(f"{key}: {lacunarity[key]:.4f}")
    if len(lacunarity) > 25:
        print(f"... {len(lacunarity) - 25} more lacunarity entries in JSON report")

    _print_top_cells(cells)
    _print_routes(routes)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"condition-lab-{utc_now().strftime('%Y%m%d%H%M%S')}"
    report = {
        "run_id": run_id,
        "generated_at": utc_now().isoformat(),
        "source": args.source,
        "symbols": args.symbols,
        "settings": [{"name": s.name, "family": s.family, "params": s.params} for s in settings],
        "arguments": vars(args),
        "cells": [serialize_cell(c) for c in cells],
        "nested_lacunarity": lacunarity,
        "rpm_routes": routes,
        "claim_boundary": "Research stress map only. Not a live trading authorization.",
    }
    path = out_dir / f"{run_id}-report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nreport written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
