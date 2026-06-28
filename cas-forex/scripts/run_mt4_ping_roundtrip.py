"""CLI for the CAS Forex MT4 ping roundtrip verifier."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_forex.mt4_ping_roundtrip import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    build_mt4_ping_roundtrip_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write one MT4 ping and wait for heartbeat/receipt evidence.")
    parser.add_argument("--mailbox-dir", type=Path, default=None, help="Activated MT4 mailbox, usually <MT4_DATA_DIR>\\MQL4\\Files\\CASForexMailbox.")
    parser.add_argument("--activation-report-dir", type=Path, default=None, help="Directory containing mt4-terminal-activation reports.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--wait-seconds", type=float, default=0.0)
    parser.add_argument("--poll-interval-seconds", type=float, default=0.25)
    parser.add_argument("--existing-command-id", default=None, help="Inspect an already-written ping command instead of writing a new one.")
    parser.add_argument("--no-write-ping", action="store_true", help="Do not write a new ping command.")
    parser.add_argument("--no-create-mailbox", action="store_true", help="Do not create mailbox folders before running.")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    kwargs = {
        "mailbox_dir": args.mailbox_dir,
        "output_dir": args.output_dir,
        "wait_seconds": args.wait_seconds,
        "poll_interval_seconds": args.poll_interval_seconds,
        "write_ping": not args.no_write_ping,
        "existing_command_id": args.existing_command_id,
        "create_mailbox": not args.no_create_mailbox,
    }
    if args.activation_report_dir is not None:
        kwargs["activation_report_dir"] = args.activation_report_dir

    report = build_mt4_ping_roundtrip_report(**kwargs)
    if args.summary_only:
        print(json.dumps(report["summary"], indent=2, sort_keys=True))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
