"""CLI for CAS Forex MT5 terminal API verification."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_forex.mt5_terminal_api_verifier import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    build_mt5_terminal_api_verifier_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify read-only MT5 terminal API/account access.")
    parser.add_argument("--mt5-path", type=Path, default=None)
    parser.add_argument("--date", default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = build_mt5_terminal_api_verifier_report(
        mt5_path=args.mt5_path,
        trading_date=args.date,
        output_dir=args.output_dir,
    )
    if args.summary_only:
        payload = {
            "artifact_paths": report.get("artifact_paths", {}),
            "next_action": report.get("next_action"),
            "summary": report.get("summary", {}),
            "verifier_status": report.get("verifier_status"),
        }
    else:
        payload = report
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
