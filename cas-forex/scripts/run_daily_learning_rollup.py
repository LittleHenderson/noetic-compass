"""Build the CAS Forex daily learning rollup."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.daily_learning_rollup import DEFAULT_OUTPUT_DIR, build_daily_learning_rollup_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trading-date", default=None)
    parser.add_argument("--day-index", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = build_daily_learning_rollup_report(
        trading_date=args.trading_date,
        day_index=args.day_index,
        output_dir=args.output_dir,
    )
    if args.summary_only:
        payload = {
            "rollup_status": report["rollup_status"],
            "trading_date": report["trading_date"],
            "day_index": report["day_index"],
            "summary": report["summary"],
            "artifact_paths": report.get("artifact_paths", {}),
            "next_action": report["next_action"],
        }
    else:
        payload = report
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
