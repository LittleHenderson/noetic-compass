"""Run the daily CAS FOREX paper-proof bundle."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.config import config
from cas_forex.paper_daily_bundle import daily_bundle_payload, run_daily_paper_bundle
from cas_forex.paper_proof import build_index_tsmom_126_paper_proof_plan
from cas_forex.time_utils import utc_now


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lead-id",
        default="index_tsmom_126_d1",
        choices=["index_tsmom_126_d1"],
        help="Paper-proof lead to run.",
    )
    parser.add_argument("--date", help="Trading date, YYYY-MM-DD. Defaults to today UTC.")
    parser.add_argument(
        "--output-dir",
        default="evidence_runs/index_tsmom_126_paper_proof",
    )
    parser.add_argument("--account-equity", type=float, default=5_000.0)
    parser.add_argument("--max-risk-pct", type=float, default=config.max_risk_per_trade_pct)
    parser.add_argument("--daily-risk-pct", type=float, default=1.0)
    parser.add_argument("--max-paper-attempts", type=int, default=None)
    parser.add_argument(
        "--no-mt5",
        action="store_true",
        help="Skip MT5 demo receipt collection for this bundle run.",
    )
    parser.add_argument(
        "--no-append",
        action="store_true",
        help="Evaluate available steps without appending Evidence Packets.",
    )
    parser.add_argument(
        "--allow-duplicate-date",
        action="store_true",
        help="Do not skip existing same-date receipt/decision/risk records.",
    )
    args = parser.parse_args()

    plan = build_index_tsmom_126_paper_proof_plan()
    trading_date = date.fromisoformat(args.date) if args.date else utc_now().date()
    bundle = run_daily_paper_bundle(
        plan,
        Path(args.output_dir),
        trading_date=trading_date,
        append_records=not args.no_append,
        collect_mt5_receipt=not args.no_mt5,
        skip_existing=not args.allow_duplicate_date,
        account_equity=args.account_equity,
        max_risk_per_trade_pct=args.max_risk_pct,
        daily_risk_budget_pct=args.daily_risk_pct,
        max_paper_attempts=args.max_paper_attempts,
    )
    print(json.dumps(daily_bundle_payload(bundle), indent=2))
    return 0 if bundle.completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
