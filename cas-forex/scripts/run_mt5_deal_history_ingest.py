"""Run the CAS Forex MT5 closed-deal history ingest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.agent_memory import DEFAULT_OUTPUT_DIR as DEFAULT_MEMORY_DIR
from cas_forex.mt5_deal_history_ingest import (
    DEFAULT_OUTPUT_DIR,
    build_mt5_deal_history_ingest_report,
)
from cas_forex.terminal_history_ingest import (
    DEFAULT_OUTPUT_DIR as DEFAULT_TERMINAL_HISTORY_OUTPUT_DIR,
    DEFAULT_SOURCE_DIR as DEFAULT_TERMINAL_HISTORY_EXPORT_DIR,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mt5-path", type=Path)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--days-back", type=int, default=7)
    parser.add_argument("--future-minutes", type=int, default=120)
    parser.add_argument("--symbol")
    parser.add_argument("--ticket")
    parser.add_argument("--memory-report-dir", type=Path, default=DEFAULT_MEMORY_DIR)
    parser.add_argument("--terminal-history-output-dir", type=Path, default=DEFAULT_TERMINAL_HISTORY_OUTPUT_DIR)
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_TERMINAL_HISTORY_EXPORT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-terminal-history-ingest", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = build_mt5_deal_history_ingest_report(
        mt5_path=args.mt5_path,
        start=args.start,
        end=args.end,
        days_back=args.days_back,
        future_minutes=args.future_minutes,
        symbol=args.symbol,
        ticket=args.ticket,
        memory_report_dir=args.memory_report_dir,
        terminal_history_output_dir=args.terminal_history_output_dir,
        export_dir=args.export_dir,
        output_dir=args.output_dir,
        run_terminal_history_ingest=not args.skip_terminal_history_ingest,
    )
    if args.summary_only:
        payload = {
            "ingest_status": report["ingest_status"],
            "summary": report["summary"],
            "history_export_path": report.get("history_export_path"),
            "artifact_paths": report.get("artifact_paths", {}),
            "next_action": report["next_action"],
        }
    else:
        payload = report
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
