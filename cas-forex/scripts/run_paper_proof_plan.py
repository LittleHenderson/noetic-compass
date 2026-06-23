"""Start or append a CAS FOREX lead-specific paper-proof ledger."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.paper_proof import (
    build_index_tsmom_126_paper_proof_plan,
    append_paper_proof_day,
    paper_broker_receipt_template,
    summarize_paper_proof,
    write_paper_proof_plan,
    write_paper_proof_status,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lead-id",
        default="index_tsmom_126_d1",
        choices=["index_tsmom_126_d1"],
        help="Paper-proof plan to run.",
    )
    parser.add_argument(
        "--output-dir",
        default="evidence_runs/index_tsmom_126_paper_proof",
        help="Directory for the plan, ledger, and status report.",
    )
    parser.add_argument(
        "--append-day",
        action="store_true",
        help="Append one weekday paper-proof heartbeat for the selected lead.",
    )
    parser.add_argument("--date", help="Trading date to append, YYYY-MM-DD. Defaults to today UTC.")
    parser.add_argument("--orders-attempted", type=int, default=0)
    parser.add_argument("--orders-paper-executed", type=int, default=0)
    parser.add_argument("--broker-mode", default="PAPER_PLAN_ONLY")
    parser.add_argument(
        "--broker-receipt",
        help=(
            "JSON receipt from a paper/demo broker export. The CLI hash-binds and validates it, "
            "but does not mark it API-verified."
        ),
    )
    parser.add_argument(
        "--write-receipt-template",
        help="Write a broker/demo receipt template JSON for the selected date and exit after status refresh.",
    )
    args = parser.parse_args()

    plan = build_index_tsmom_126_paper_proof_plan()
    out_dir = Path(args.output_dir)
    plan_path = write_paper_proof_plan(plan, out_dir)
    trading_date = date.fromisoformat(args.date) if args.date else None
    receipt_template_path = None
    if args.write_receipt_template:
        template = paper_broker_receipt_template(plan, trading_date=trading_date)
        receipt_template_path = Path(args.write_receipt_template)
        receipt_template_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_template_path.write_text(json.dumps(template, indent=2), encoding="utf-8")

    appended = None
    broker_receipt = None
    if args.broker_receipt:
        broker_receipt = json.loads(Path(args.broker_receipt).read_text(encoding="utf-8"))
    if args.append_day or broker_receipt is not None:
        appended = append_paper_proof_day(
            plan,
            out_dir,
            trading_date=trading_date,
            orders_attempted=args.orders_attempted,
            orders_paper_executed=args.orders_paper_executed,
            broker_mode=args.broker_mode,
            broker_receipt=broker_receipt,
        )

    report = summarize_paper_proof(plan, out_dir)
    status_path = write_paper_proof_status(plan, out_dir, report)
    print(
        json.dumps(
            {
                "plan": str(plan_path),
                "status": str(status_path),
                "receipt_template": str(receipt_template_path) if receipt_template_path else None,
                "appended": appended,
                "report": report.model_dump(mode="json"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
