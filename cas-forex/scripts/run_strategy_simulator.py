"""CAS Forex strategy-condition simulator.

Plays every strategy across every market REGIME (and volatility level), classifies
each cell into a CJT operating region with a gain (beta), and builds the nested
LACUNARITY map (where we have no validated edge) plus the RPM routing seed
(best strategy per regime). This is the "switch strategy/settings by condition"
engine the user asked for.

Run:  python scripts/run_strategy_simulator.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from cas_forex.backtest.engine import BacktestEngine
from cas_forex.forecast.strategies import (
    make_donchian_breakout_signal,
    make_mean_reversion_signal,
)
from cas_forex.regime_sim import (
    REGIMES,
    CellResult,
    best_strategy_per_regime,
    cell_is_gap,
    classify_region,
    generate_regime_candles,
    nested_lacunarity,
)
from cas_forex.schemas.cjt import CjtRegion
from cas_forex.time_utils import utc_now


def build_strategies() -> Dict[str, object]:
    """name -> signal_fn (None = built-in SMA trend)."""
    return {
        "trend_sma": None,
        "meanrev": make_mean_reversion_signal(),
        "meanrev_tf": make_mean_reversion_signal(trend_filter=True),
        "breakout": make_donchian_breakout_signal(),
    }


_REGION_TAG = {
    CjtRegion.CUTOFF: "cut",
    CjtRegion.ACTIVE: "ACT",
    CjtRegion.SATURATION: "sat",
    CjtRegion.BREAKDOWN: "BRK",
    CjtRegion.UNKNOWN: "?",
}


def run_cell(strategy_name, signal_fn, regime, vol_mult, seeds, bars,
             symbol, spread_pips, extra_cost_pips, starting_balance, position_lots):
    rets, dds, trades, wins = [], [], [], []
    for s in range(seeds):
        seed = hash((strategy_name, regime, round(vol_mult, 3), s)) % (2**32)
        candles = generate_regime_candles(regime, symbol=symbol, bars=bars,
                                           seed=seed, vol_mult=vol_mult)
        engine = BacktestEngine(
            initial_balance=starting_balance, position_size_lots=position_lots,
            spread_pips=spread_pips, extra_cost_pips=extra_cost_pips,
            signal_fn=signal_fn,
        )
        r = engine.run(candles, symbol=symbol, warmup_bars=min(60, max(50, bars // 8)))
        ret = (r.ending_balance - r.starting_balance) / max(r.starting_balance, 1) * 100
        rets.append(ret)
        dds.append(r.max_drawdown_pct)
        trades.append(r.total_trades)
        wins.append(r.win_rate)
    mean_ret = float(np.mean(rets))
    mean_dd = float(np.mean(dds))
    mean_tr = float(np.mean(trades))
    region, beta = classify_region(mean_ret, mean_dd, mean_tr)
    return CellResult(
        strategy=strategy_name, regime=regime, vol_mult=vol_mult,
        mean_return_pct=round(mean_ret, 3), mean_max_dd_pct=round(mean_dd, 2),
        mean_trades=round(mean_tr, 1), win_rate=round(float(np.mean(wins)), 4),
        region=region, beta=round(beta, 4),
        is_gap=cell_is_gap(region, mean_ret),
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=5)
    p.add_argument("--bars", type=int, default=400)
    p.add_argument("--symbol", default="EUR/USD")
    p.add_argument("--vol-mults", type=float, nargs="*", default=[0.5, 1.0, 2.0])
    p.add_argument("--spread-pips", type=float, default=1.0)
    p.add_argument("--extra-cost-pips", type=float, default=0.5)
    p.add_argument("--starting-balance", type=float, default=10000.0)
    p.add_argument("--position-lots", type=float, default=0.05)
    p.add_argument("--output-dir", default="evidence_runs/simulator")
    args = p.parse_args()

    strategies = build_strategies()
    cells: List[CellResult] = []
    total = len(strategies) * len(REGIMES) * len(args.vol_mults)
    done = 0
    for name, fn in strategies.items():
        for regime in REGIMES:
            for vm in args.vol_mults:
                cells.append(run_cell(
                    name, fn, regime, vm, args.seeds, args.bars, args.symbol,
                    args.spread_pips, args.extra_cost_pips,
                    args.starting_balance, args.position_lots,
                ))
                done += 1
        print(f"  swept {name}: {done}/{total} cells", flush=True)

    # ---- Matrix at vol_mult = 1.0 ----
    base_vm = 1.0 if 1.0 in args.vol_mults else args.vol_mults[len(args.vol_mults) // 2]
    base_cells = [c for c in cells if c.vol_mult == base_vm]
    print("\n" + "=" * 84)
    print(f"CAS FOREX STRATEGY x REGIME SIMULATOR  (vol={base_vm}, cost={args.spread_pips + args.extra_cost_pips}p, "
          f"seeds={args.seeds})")
    print("=" * 84)
    header = f"{'strategy':12}" + "".join(f"{r[:9]:>11}" for r in REGIMES)
    print(header)
    print("-" * 84)
    for name in strategies:
        row = f"{name:12}"
        for regime in REGIMES:
            c = next((x for x in base_cells if x.strategy == name and x.regime == regime), None)
            if c is None:
                row += f"{'-':>11}"
            else:
                row += f"{_REGION_TAG[c.region] + f'{c.mean_return_pct:+.1f}':>11}"
        print(row)
    print("-" * 84)
    print("cells: ACT=active  cut=cutoff(no trades)  sat=saturation  BRK=breakdown(deep DD); number = mean return%")

    # ---- Nested lacunarity ----
    nl = nested_lacunarity(cells)
    print("\nLACUNARITY (fraction of cells with NO validated edge; 0=full coverage, 1=all gaps)")
    print(f"  overall: {nl['overall']:.2f}")
    for name in strategies:
        line = f"  {name:12} all-vol {nl.get(f'strategy::{name}', 1.0):.2f}"
        for vm in args.vol_mults:
            line += f" | vol{vm}={nl.get(f'strategy::{name}::vol::{vm}', 1.0):.2f}"
        print(line)

    # ---- RPM routing seed: best strategy per regime ----
    routing = best_strategy_per_regime(base_cells)
    print("\nRPM ROUTING SEED (best non-gap strategy per regime; None = lacuna, do not trade):")
    for regime, strat in routing.items():
        print(f"  {regime:12} -> {strat if strat else 'NONE (no validated edge)'}")

    # ---- Report ----
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"sim-{utc_now().strftime('%Y%m%d%H%M%S')}"
    report = {
        "run_id": run_id,
        "symbol": args.symbol,
        "seeds": args.seeds,
        "bars": args.bars,
        "vol_mults": args.vol_mults,
        "round_trip_cost_pips": args.spread_pips + args.extra_cost_pips,
        "cells": [vars(c) | {"region": c.region.value} for c in cells],
        "lacunarity": nl,
        "rpm_routing_seed": routing,
        "note": ("Synthetic regimes characterize strategy BEHAVIOR under assumed "
                 "conditions; not proof of live edge. Read as a stress map."),
    }
    path = out_dir / f"{run_id}-report.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nreport written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
