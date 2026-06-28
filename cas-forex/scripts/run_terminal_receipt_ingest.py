"""Ingest MT4/MT5 terminal receipt JSON into the CAS Forex agent journal."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.agent_message_bus import DEFAULT_EVENT_LOG_PATH
from cas_forex.terminal_receipt_ingest import (
    DEFAULT_MAILBOX_DIR,
    DEFAULT_OUTPUT_DIR,
    ingest_terminal_receipts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mailbox-dir", type=Path, default=DEFAULT_MAILBOX_DIR)
    parser.add_argument("--event-log-path", type=Path, default=DEFAULT_EVENT_LOG_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-report", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = ingest_terminal_receipts(
        mailbox_dir=args.mailbox_dir,
        event_log_path=args.event_log_path,
        output_dir=args.output_dir,
        write_report=not args.no_report,
    )
    payload = report["summary"] if args.summary_only else report
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
