"""Run the CAS Forex leveraged income backsolve.

This is paper-only research. It does not approve a broker, place live trades,
or authorize deposits/withdrawals.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.leverage_backsolve import (
    AIAutonomyMode,
    LIVE_MONEY_BOUNDARY,
    MAX_USER_CONCURRENT_TRADES,
    run_income_backsolve,
    write_backsolve_reports,
)


DEFAULT_EVIDENCE_REPORT = (
    "evidence_runs/index_tsmom_h1_d1_go/walk-forward-20260622054921-report.json"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-report", default=DEFAULT_EVIDENCE_REPORT)
    parser.add_argument("--seed-capital", type=float, default=5_000.0)
    parser.add_argument("--monthly-targets", nargs="*", type=float, default=[5_000.0, 12_000.0])
    parser.add_argument("--symbols", nargs="*", default=["US30", "NAS100"])
    parser.add_argument(
        "--strategies",
        nargs="*",
        default=["tsmom_126_250_2_10", "tsmom_252_500_2_8"],
    )
    parser.add_argument("--timeframes", nargs="*", default=["D1"])
    parser.add_argument(
        "--max-loss-caps",
        nargs="+",
        type=float,
        default=[10.0, 15.0],
        help="Any positive account-loss cap percentage(s) the owner wants to test.",
    )
    parser.add_argument(
        "--max-open-trades",
        type=int,
        default=MAX_USER_CONCURRENT_TRADES,
        help=f"Highest concurrent-trade count to test. Maximum {MAX_USER_CONCURRENT_TRADES}.",
    )
    parser.add_argument(
        "--concurrent-trade-grid",
        nargs="*",
        type=int,
        default=None,
        help="Optional explicit concurrency grid. Defaults to every value from 1 through --max-open-trades.",
    )
    parser.add_argument(
        "--ai-autonomy-mode",
        choices=[mode.value for mode in AIAutonomyMode],
        default=AIAutonomyMode.USER_MANUAL.value,
    )
    parser.add_argument(
        "--lot-grid",
        nargs="*",
        type=float,
        default=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
    )
    parser.add_argument("--output-dir", default="evidence_runs/leverage_income_backsolve")
    args = parser.parse_args()

    if args.max_open_trades < 1 or args.max_open_trades > MAX_USER_CONCURRENT_TRADES:
        raise SystemExit(f"--max-open-trades must be between 1 and {MAX_USER_CONCURRENT_TRADES}")
    concurrency_grid = args.concurrent_trade_grid or list(range(1, args.max_open_trades + 1))

    report = run_income_backsolve(
        evidence_report_path=args.evidence_report,
        seed_capital=args.seed_capital,
        monthly_targets=args.monthly_targets,
        symbols=args.symbols,
        strategies=args.strategies,
        timeframes=args.timeframes,
        concurrent_trade_grid=concurrency_grid,
        lot_grid=args.lot_grid,
        max_loss_cap_pcts=args.max_loss_caps,
        ai_autonomy_mode=args.ai_autonomy_mode,
    )
    paths = write_backsolve_reports(report, args.output_dir)

    print("=" * 100)
    print("CAS FOREX LEVERAGED INCOME BACKSOLVE")
    print("=" * 100)
    print(LIVE_MONEY_BOUNDARY)
    print()
    print(json.dumps({
        "run_id": report["run_id"],
        "scenario_count": report["scenario_count"],
        "viable_scenario_count": report["viable_scenario_count"],
        "ai_autonomy": report["ai_autonomy"],
        "target_summaries": report["target_summaries"],
        "reports": paths,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
