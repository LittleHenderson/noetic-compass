"""CLI for the CAS Forex MT4 terminal session verifier."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_forex.agent_message_bus import DEFAULT_EVENT_LOG_PATH  # noqa: E402
from cas_forex.mt4_terminal_activation import DEFAULT_EA_SOURCE_PATH  # noqa: E402
from cas_forex.mt4_terminal_session_verifier import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    build_mt4_terminal_session_verifier_report,
)
from cas_forex.terminal_history_ingest import DEFAULT_SOURCE_DIR as DEFAULT_HISTORY_SOURCE_DIR  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run activation + ping + supervisor + watcher refresh checks for MT4.")
    parser.add_argument("--terminal-data-dir", type=Path, default=None)
    parser.add_argument("--mailbox-dir", type=Path, default=None)
    parser.add_argument("--search-root", action="append", type=Path, default=[])
    parser.add_argument("--ea-source-path", type=Path, default=DEFAULT_EA_SOURCE_PATH)
    parser.add_argument("--mailbox-root", default="CASForexMailbox")
    parser.add_argument("--use-common-files", action="store_true")
    parser.add_argument("--install", action="store_true", help="Copy CASForexBridgeEA.mq4 into MQL4\\Experts when an MT4 data folder is selected.")
    parser.add_argument("--no-create-mailbox", action="store_true")
    parser.add_argument("--wait-seconds", type=float, default=0.0)
    parser.add_argument("--poll-interval-seconds", type=float, default=0.25)
    parser.add_argument("--existing-command-id", default=None)
    parser.add_argument("--no-write-ping", action="store_true")
    parser.add_argument("--no-refresh-chain", action="store_true")
    parser.add_argument("--no-force-refresh-chain", action="store_true")
    parser.add_argument("--history-source", action="append", type=Path, default=[])
    parser.add_argument("--event-log-path", type=Path, default=DEFAULT_EVENT_LOG_PATH)
    parser.add_argument("--chain-output-root", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--child-output-root", type=Path, default=None)
    parser.add_argument("--now", default=None)
    parser.add_argument("--no-child-reports", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    history_sources = args.history_source or [DEFAULT_HISTORY_SOURCE_DIR]
    report = build_mt4_terminal_session_verifier_report(
        terminal_data_dir=args.terminal_data_dir,
        mailbox_dir=args.mailbox_dir,
        search_roots=args.search_root or None,
        ea_source_path=args.ea_source_path,
        mailbox_root=args.mailbox_root,
        use_common_files=args.use_common_files,
        install_ea=args.install,
        create_mailbox=not args.no_create_mailbox,
        wait_seconds=args.wait_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
        write_ping=not args.no_write_ping,
        existing_command_id=args.existing_command_id,
        run_refresh_chain=not args.no_refresh_chain,
        force_refresh_chain=not args.no_force_refresh_chain,
        history_source_paths=history_sources,
        event_log_path=args.event_log_path,
        chain_output_root=args.chain_output_root,
        output_dir=args.output_dir,
        child_output_root=args.child_output_root,
        now=args.now,
        write_child_reports=not args.no_child_reports,
    )
    if args.summary_only:
        payload = {
            "artifact_paths": report.get("artifact_paths", {}),
            "child_reports": report.get("child_reports", {}),
            "next_action": report.get("next_action"),
            "session_status": report.get("session_status"),
            "summary": report.get("summary", {}),
        }
    else:
        payload = report
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
