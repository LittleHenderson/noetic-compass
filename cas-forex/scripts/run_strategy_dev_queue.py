"""Build CAS Forex strategy-development work items."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.agent_memory import DEFAULT_OUTPUT_DIR as DEFAULT_MEMORY_DIR
from cas_forex.agent_research_queue import DEFAULT_OUTPUT_DIR as DEFAULT_RESEARCH_QUEUE_DIR
from cas_forex.strategy_dev_queue import DEFAULT_OUTPUT_DIR, build_strategy_dev_queue_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-queue-report-dir", type=Path, default=DEFAULT_RESEARCH_QUEUE_DIR)
    parser.add_argument("--memory-report-dir", type=Path, default=DEFAULT_MEMORY_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = build_strategy_dev_queue_report(
        research_queue_report_dir=args.research_queue_report_dir,
        memory_report_dir=args.memory_report_dir,
        output_dir=args.output_dir,
    )
    if args.summary_only:
        payload = {
            "queue_status": report["queue_status"],
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
