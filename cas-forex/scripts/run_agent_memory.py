"""Build CAS Forex agent outcome-memory rows from the event journal."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.agent_memory import DEFAULT_OUTPUT_DIR, build_agent_memory_report
from cas_forex.agent_message_bus import DEFAULT_EVENT_LOG_PATH
from cas_forex.terminal_history_ingest import DEFAULT_OUTPUT_DIR as DEFAULT_TERMINAL_HISTORY_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-log-path", type=Path, default=DEFAULT_EVENT_LOG_PATH)
    parser.add_argument("--terminal-history-report-dir", type=Path, default=DEFAULT_TERMINAL_HISTORY_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = build_agent_memory_report(
        event_log_path=args.event_log_path,
        terminal_history_report_dir=args.terminal_history_report_dir,
        output_dir=args.output_dir,
    )
    if args.summary_only:
        payload = {
            "memory_status": report["memory_status"],
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
