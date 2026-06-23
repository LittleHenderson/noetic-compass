"""Evaluate and optionally append the daily CAS FOREX paper route decision."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.paper_decision import (
    append_paper_route_decision,
    evaluate_paper_route_decision,
    summarize_paper_route_decisions,
    write_paper_route_decision_status,
)
from cas_forex.paper_proof import build_index_tsmom_126_paper_proof_plan
from cas_forex.time_utils import utc_now


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lead-id",
        default="index_tsmom_126_d1",
        choices=["index_tsmom_126_d1"],
        help="Paper-proof lead to evaluate.",
    )
    parser.add_argument("--date", help="Trading date, YYYY-MM-DD. Defaults to today UTC.")
    parser.add_argument(
        "--output-dir",
        default="evidence_runs/index_tsmom_126_paper_proof",
    )
    parser.add_argument(
        "--append-decision",
        action="store_true",
        help="Append the route/no-trade decision to the paper-decision evidence chain.",
    )
    args = parser.parse_args()

    plan = build_index_tsmom_126_paper_proof_plan()
    out_dir = Path(args.output_dir)
    trading_date = date.fromisoformat(args.date) if args.date else utc_now().date()
    decision = evaluate_paper_route_decision(plan, trading_date=trading_date)
    appended = append_paper_route_decision(decision, out_dir) if args.append_decision else None
    status_path = write_paper_route_decision_status(plan, out_dir)
    summary = summarize_paper_route_decisions(plan, out_dir)
    print(
        json.dumps(
            {
                "status": str(status_path),
                "decision": decision.__dict__,
                "appended": appended,
                "summary": summary,
            },
            indent=2,
            default=lambda value: value.__dict__,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
