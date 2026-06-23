"""Show the next due CAS FOREX daily paper-proof bundle."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.paper_daily_schedule import (
    evaluate_daily_paper_schedule,
    write_daily_paper_schedule_status,
)
from cas_forex.paper_proof import build_index_tsmom_126_paper_proof_plan
from cas_forex.time_utils import utc_now


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lead-id",
        default="index_tsmom_126_d1",
        choices=["index_tsmom_126_d1"],
        help="Paper-proof lead to inspect.",
    )
    parser.add_argument("--date", help="As-of date, YYYY-MM-DD. Defaults to today UTC.")
    parser.add_argument(
        "--output-dir",
        default="evidence_runs/index_tsmom_126_paper_proof",
    )
    parser.add_argument("--account-equity", type=float, default=5_000.0)
    parser.add_argument("--max-risk-pct", type=float, default=0.5)
    parser.add_argument("--daily-risk-pct", type=float, default=1.0)
    parser.add_argument("--ui-min-daily-bundles", type=int, default=5)
    args = parser.parse_args()

    plan = build_index_tsmom_126_paper_proof_plan()
    as_of = date.fromisoformat(args.date) if args.date else utc_now().date()
    schedule = evaluate_daily_paper_schedule(
        plan,
        Path(args.output_dir),
        as_of_date=as_of,
        account_equity=args.account_equity,
        max_risk_pct=args.max_risk_pct,
        daily_risk_pct=args.daily_risk_pct,
        ui_min_daily_bundles=args.ui_min_daily_bundles,
    )
    status_path = write_daily_paper_schedule_status(plan, args.output_dir, schedule)
    print(json.dumps({"status": str(status_path), "schedule": asdict(schedule)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
