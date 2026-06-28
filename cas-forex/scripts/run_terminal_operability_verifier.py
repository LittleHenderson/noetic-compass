"""CLI for CAS Forex terminal operability verification."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_forex.terminal_operability_verifier import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    build_terminal_operability_verifier_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build one CAS Forex terminal operability go/no-go report.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = build_terminal_operability_verifier_report(output_dir=args.output_dir)
    if args.summary_only:
        payload = {
            "artifact_paths": report.get("artifact_paths", {}),
            "go_no_go": report.get("go_no_go", {}),
            "next_action": report.get("next_action"),
            "operability_status": report.get("operability_status"),
            "summary": report.get("summary", {}),
        }
    else:
        payload = report
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
