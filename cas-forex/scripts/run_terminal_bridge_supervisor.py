"""Inspect MT4/MT5 bridge heartbeat, mailbox, receipts, history, and account snapshot state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.agent_message_bus import DEFAULT_EVENT_LOG_PATH
from cas_forex.agent_state import DEFAULT_MAILBOX_DIR
from cas_forex.terminal_bridge_supervisor import DEFAULT_OUTPUT_DIR, build_terminal_bridge_supervisor_report
from cas_forex.terminal_history_ingest import DEFAULT_SOURCE_DIR as DEFAULT_HISTORY_SOURCE_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mailbox-dir", type=Path, default=DEFAULT_MAILBOX_DIR)
    parser.add_argument("--history-source", action="append", type=Path, default=[])
    parser.add_argument("--event-log-path", type=Path, default=DEFAULT_EVENT_LOG_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--now", default=None)
    parser.add_argument("--heartbeat-stale-seconds", type=int, default=180)
    parser.add_argument("--receipt-stale-seconds", type=int, default=900)
    parser.add_argument("--history-stale-seconds", type=int, default=86400)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = build_terminal_bridge_supervisor_report(
        mailbox_dir=args.mailbox_dir,
        history_source_paths=args.history_source or [DEFAULT_HISTORY_SOURCE_DIR],
        event_log_path=args.event_log_path,
        output_dir=args.output_dir,
        now=args.now,
        heartbeat_stale_seconds=args.heartbeat_stale_seconds,
        receipt_stale_seconds=args.receipt_stale_seconds,
        history_stale_seconds=args.history_stale_seconds,
    )
    if args.summary_only:
        payload = {
            "artifact_paths": report.get("artifact_paths", {}),
            "as_of": report.get("as_of"),
            "next_action": report.get("next_action"),
            "summary": report.get("summary", {}),
            "supervisor_status": report.get("supervisor_status"),
        }
    else:
        payload = report
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
