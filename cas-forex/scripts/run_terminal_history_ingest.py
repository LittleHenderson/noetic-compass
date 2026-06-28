"""Normalize MT4/MT5 close-history exports and join them to CAS memory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.agent_memory import DEFAULT_OUTPUT_DIR as DEFAULT_MEMORY_DIR
from cas_forex.terminal_history_ingest import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SOURCE_DIR,
    ingest_terminal_history,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", type=Path, default=[])
    parser.add_argument("--source-dir", type=Path, default=None)
    parser.add_argument("--memory-report-dir", type=Path, default=DEFAULT_MEMORY_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    sources = list(args.source)
    if args.source_dir is not None:
        sources.append(args.source_dir)
    elif not sources:
        sources.append(DEFAULT_SOURCE_DIR)

    report = ingest_terminal_history(
        source_paths=sources,
        memory_report_dir=args.memory_report_dir,
        output_dir=args.output_dir,
    )
    if args.summary_only:
        payload = {
            "ingest_status": report["ingest_status"],
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
