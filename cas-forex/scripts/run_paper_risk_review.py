"""Review paper-route candidates against the CAS FOREX paper risk budget."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.config import config
from cas_forex.paper_decision import summarize_paper_route_decisions
from cas_forex.paper_proof import build_index_tsmom_126_paper_proof_plan
from cas_forex.paper_risk import (
    append_paper_risk_review,
    review_paper_risk_budget,
    summarize_paper_risk_reviews,
    write_paper_risk_status,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lead-id",
        default="index_tsmom_126_d1",
        choices=["index_tsmom_126_d1"],
        help="Paper-proof lead to risk-review.",
    )
    parser.add_argument(
        "--output-dir",
        default="evidence_runs/index_tsmom_126_paper_proof",
    )
    parser.add_argument("--account-equity", type=float, default=5_000.0)
    parser.add_argument(
        "--max-risk-pct",
        type=float,
        default=config.max_risk_per_trade_pct,
        help="Maximum paper risk per routed attempt as percent of account equity.",
    )
    parser.add_argument(
        "--daily-risk-pct",
        type=float,
        default=1.0,
        help="Maximum total paper risk for this review date as percent of account equity.",
    )
    parser.add_argument(
        "--max-paper-attempts",
        type=int,
        default=None,
        help="Maximum paper attempts allowed for the date. Defaults to the proof plan.",
    )
    parser.add_argument("--existing-attempts", type=int, default=0)
    parser.add_argument("--min-lot", type=float, default=0.01)
    parser.add_argument("--lot-step", type=float, default=0.01)
    parser.add_argument(
        "--max-position-lots",
        type=float,
        default=config.max_position_lots,
    )
    parser.add_argument(
        "--append-review",
        action="store_true",
        help="Append the risk review to the paper-risk evidence chain.",
    )
    args = parser.parse_args()

    plan = build_index_tsmom_126_paper_proof_plan()
    out_dir = Path(args.output_dir)
    decision_summary = summarize_paper_route_decisions(plan, out_dir)
    latest_decision = decision_summary.get("latest_decision")
    if not latest_decision:
        print(
            json.dumps(
                {
                    "error": "NO_PAPER_DECISION_FOUND",
                    "message": "Run scripts/run_paper_route_decision.py --append-decision first.",
                    "decision_summary": decision_summary,
                },
                indent=2,
            )
        )
        return 2

    review = review_paper_risk_budget(
        plan,
        latest_decision,
        account_equity=args.account_equity,
        max_risk_per_trade_pct=args.max_risk_pct,
        daily_risk_budget_pct=args.daily_risk_pct,
        max_paper_attempts=args.max_paper_attempts,
        existing_attempts=args.existing_attempts,
        min_lot=args.min_lot,
        lot_step=args.lot_step,
        max_position_lots=args.max_position_lots,
    )
    appended = append_paper_risk_review(review, out_dir) if args.append_review else None
    status_path = write_paper_risk_status(plan, out_dir)
    summary = summarize_paper_risk_reviews(plan, out_dir)
    print(
        json.dumps(
            {
                "status": str(status_path),
                "review": review,
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
