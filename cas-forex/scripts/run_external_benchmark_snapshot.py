"""Validate and print the current CAS Forex external benchmark snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.external_benchmark import DEFAULT_REPORT_PATH, load_external_benchmark_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Path to an external benchmark report JSON.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print only the normalized summary.",
    )
    args = parser.parse_args()

    report = load_external_benchmark_report(args.report)
    payload = report["summary"] if args.summary_only else report
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
