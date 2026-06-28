"""CLI for CAS Forex terminal position reconciliation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_forex.terminal_position_reconciliation import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    build_terminal_position_reconciliation_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile CAS Forex memory against terminal position evidence.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = build_terminal_position_reconciliation_report(output_dir=args.output_dir)
    if args.summary_only:
        payload = {
            "artifact_paths": report.get("artifact_paths", {}),
            "next_action": report.get("next_action"),
            "reconciliation_status": report.get("reconciliation_status"),
            "summary": report.get("summary", {}),
        }
    else:
        payload = report
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
