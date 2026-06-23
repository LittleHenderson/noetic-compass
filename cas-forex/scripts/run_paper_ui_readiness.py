"""Evaluate CAS FOREX proof-cockpit multi-day proof maturity."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.paper_proof import build_index_tsmom_126_paper_proof_plan
from cas_forex.paper_ui_readiness import (
    evaluate_paper_ui_readiness,
    write_paper_ui_readiness_status,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lead-id",
        default="index_tsmom_126_d1",
        choices=["index_tsmom_126_d1"],
        help="Paper-proof lead to evaluate.",
    )
    parser.add_argument(
        "--output-dir",
        default="evidence_runs/index_tsmom_126_paper_proof",
    )
    parser.add_argument(
        "--min-daily-bundles",
        type=int,
        default=5,
        help="Minimum complete daily paper bundles before multi-day proof maturity.",
    )
    args = parser.parse_args()

    plan = build_index_tsmom_126_paper_proof_plan()
    report = evaluate_paper_ui_readiness(
        plan,
        Path(args.output_dir),
        min_daily_bundles_for_ui=args.min_daily_bundles,
    )
    status_path = write_paper_ui_readiness_status(plan, args.output_dir, report)
    payload = {"status": str(status_path), "report": asdict(report)}
    print(json.dumps(payload, indent=2))
    return 0 if report.readiness_status == "READY_FOR_PROOF_COCKPIT_UI_UX" else 1


if __name__ == "__main__":
    raise SystemExit(main())
