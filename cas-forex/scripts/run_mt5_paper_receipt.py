"""Probe MT5 demo/paper account state and optionally append a paper-proof receipt."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.paper_broker_adapter import MT5DemoPaperReceiptAdapter
from cas_forex.paper_proof import (
    append_paper_proof_day,
    build_index_tsmom_126_paper_proof_plan,
    summarize_paper_proof,
    write_paper_proof_plan,
    write_paper_proof_status,
)
from cas_forex.time_utils import utc_now


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lead-id",
        default="index_tsmom_126_d1",
        choices=["index_tsmom_126_d1"],
        help="Paper-proof plan to probe.",
    )
    parser.add_argument(
        "--date",
        help="Trading date to verify, YYYY-MM-DD. Defaults to today UTC.",
    )
    parser.add_argument(
        "--output-dir",
        default="evidence_runs/index_tsmom_126_paper_proof",
    )
    parser.add_argument(
        "--append-if-verified",
        action="store_true",
        help="Append the MT5 demo receipt to the proof ledger only when API-verified.",
    )
    args = parser.parse_args()

    plan = build_index_tsmom_126_paper_proof_plan()
    out_dir = Path(args.output_dir)
    write_paper_proof_plan(plan, out_dir)
    trading_date = date.fromisoformat(args.date) if args.date else utc_now().date()
    adapter = MT5DemoPaperReceiptAdapter()
    probe = adapter.probe(plan, trading_date)
    appended = None
    if args.append_if_verified and probe.status == "BROKER_API_VERIFIED" and probe.receipt:
        appended = append_paper_proof_day(
            plan,
            out_dir,
            trading_date=trading_date,
            broker_receipt=probe.receipt,
            allow_api_verified_receipt=True,
        )
    report = summarize_paper_proof(plan, out_dir)
    status_path = write_paper_proof_status(plan, out_dir, report)
    probe_path = out_dir / f"{plan.plan_id}-mt5-demo-probe-{utc_now().strftime('%Y%m%d%H%M%S')}.json"
    payload = {
        "probe": probe.__dict__,
        "appended": appended,
        "paper_status": str(status_path),
        "report": report.model_dump(mode="json"),
    }
    probe_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"probe_path": str(probe_path), **payload}, indent=2))
    return 0 if probe.status in {"BROKER_API_VERIFIED", "UNAVAILABLE", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
