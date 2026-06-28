"""Run one CAS Forex agent workflow paper/demo cycle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.agent_state import (
    DEFAULT_MAILBOX_DIR,
    DEFAULT_OUTPUT_DIR,
    TERMINAL_LANE_MT4_MAILBOX,
    TERMINAL_LANE_MT5_DEMO,
    run_agent_workflow_cycle,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--mailbox-dir", type=Path, default=DEFAULT_MAILBOX_DIR)
    parser.add_argument("--trigger-source", default="MANUAL_CLI")
    parser.add_argument("--no-terminal-commands", action="store_true")
    parser.add_argument(
        "--terminal-lane",
        choices=[TERMINAL_LANE_MT4_MAILBOX, TERMINAL_LANE_MT5_DEMO],
        default=TERMINAL_LANE_MT4_MAILBOX,
    )
    parser.add_argument("--mt5-path", type=Path, default=None)
    parser.add_argument("--execute-mt5-demo-order", action="store_true")
    parser.add_argument("--confirm-mt5-demo-order", action="store_true")
    parser.add_argument("--no-mt5-deal-history", action="store_true")
    parser.add_argument("--mt5-future-minutes", type=int, default=120)
    parser.add_argument("--mt5-use-process-guard", action="store_true")
    parser.add_argument("--mt5-guard-timeout-seconds", type=int, default=120)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = run_agent_workflow_cycle(
        output_dir=args.output_dir,
        mailbox_dir=args.mailbox_dir,
        trigger_source=args.trigger_source,
        write_terminal_commands=not args.no_terminal_commands,
        terminal_lane=args.terminal_lane,
        mt5_path=args.mt5_path,
        execute_mt5_demo_order=args.execute_mt5_demo_order,
        confirm_mt5_demo_order=args.confirm_mt5_demo_order,
        run_mt5_deal_history=not args.no_mt5_deal_history,
        mt5_future_minutes=args.mt5_future_minutes,
        mt5_use_process_guard=args.mt5_use_process_guard,
        mt5_guard_timeout_seconds=args.mt5_guard_timeout_seconds,
    )
    if args.summary_only:
        payload = {
            "cycle_id": report["cycle_id"],
            "summary": report["summary"],
            "execution_mode": report["execution_mode"],
            "mt5_execution_loop": report.get("mt5_execution_loop"),
            "artifact_paths": report.get("artifact_paths", {}),
        }
    else:
        payload = report
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
