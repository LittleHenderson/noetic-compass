"""Evaluate CAS Forex session autowake events and optionally run a paper/demo cycle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.agent_state import (
    DEFAULT_MAILBOX_DIR,
    DEFAULT_OUTPUT_DIR as DEFAULT_CYCLE_OUTPUT_DIR,
    TERMINAL_LANE_MT4_MAILBOX,
    TERMINAL_LANE_MT5_DEMO,
)
from cas_forex.session_autowake_runner import (
    DEFAULT_OUTPUT_DIR,
    build_session_autowake_report,
    run_session_autowake_loop,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--now", default=None, help="ISO timestamp override, e.g. 2026-06-24T13:00:00+00:00")
    parser.add_argument("--execute-cycle", action="store_true", help="Run one paper/demo agent cycle when a wake event is due")
    parser.add_argument("--no-terminal-commands", action="store_true", help="When executing, skip terminal mailbox command writes")
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
    parser.add_argument("--loop", action="store_true", help="Run a bounded loop instead of one evaluation")
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--interval-seconds", type=float, default=60.0)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--cycle-output-dir", type=Path, default=DEFAULT_CYCLE_OUTPUT_DIR)
    parser.add_argument("--mailbox-dir", type=Path, default=DEFAULT_MAILBOX_DIR)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    if args.loop:
        reports = run_session_autowake_loop(
            iterations=args.iterations,
            interval_seconds=args.interval_seconds,
            execute_cycle=args.execute_cycle,
            write_terminal_commands=not args.no_terminal_commands,
            output_dir=args.output_dir,
            cycle_output_dir=args.cycle_output_dir,
            mailbox_dir=args.mailbox_dir,
            terminal_lane=args.terminal_lane,
            mt5_path=args.mt5_path,
            execute_mt5_demo_order=args.execute_mt5_demo_order,
            confirm_mt5_demo_order=args.confirm_mt5_demo_order,
            run_mt5_deal_history=not args.no_mt5_deal_history,
            mt5_future_minutes=args.mt5_future_minutes,
        )
        report = reports[-1]
    else:
        report = build_session_autowake_report(
            now=args.now,
            execute_cycle=args.execute_cycle,
            write_terminal_commands=not args.no_terminal_commands,
            output_dir=args.output_dir,
            cycle_output_dir=args.cycle_output_dir,
            mailbox_dir=args.mailbox_dir,
            terminal_lane=args.terminal_lane,
            mt5_path=args.mt5_path,
            execute_mt5_demo_order=args.execute_mt5_demo_order,
            confirm_mt5_demo_order=args.confirm_mt5_demo_order,
            run_mt5_deal_history=not args.no_mt5_deal_history,
            mt5_future_minutes=args.mt5_future_minutes,
        )
    if args.summary_only:
        payload = {
            "autowake_status": report["autowake_status"],
            "as_of": report["as_of"],
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
