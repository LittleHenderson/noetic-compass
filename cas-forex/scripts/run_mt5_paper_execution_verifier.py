"""Run the CAS Forex MT5 paper/demo execution verifier."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.mt5_paper_execution_verifier import (
    DEFAULT_OUTPUT_DIR,
    build_mt5_paper_execution_verifier_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mt5-path", type=Path)
    parser.add_argument("--date")
    parser.add_argument("--symbol", default="EUR/USD")
    parser.add_argument("--direction", choices=["LONG", "SHORT"], default="LONG")
    parser.add_argument("--volume", type=float, default=0.01)
    parser.add_argument("--stop-loss", type=float)
    parser.add_argument("--take-profit", type=float)
    parser.add_argument("--execute-demo-order", action="store_true")
    parser.add_argument("--confirm-demo-order", action="store_true")
    parser.add_argument("--keep-open", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = build_mt5_paper_execution_verifier_report(
        mt5_path=args.mt5_path,
        trading_date=args.date,
        symbol=args.symbol,
        direction=args.direction,
        volume=args.volume,
        stop_loss=args.stop_loss,
        take_profit=args.take_profit,
        execute_demo_order=args.execute_demo_order,
        confirm_demo_order=args.confirm_demo_order,
        close_after_send=not args.keep_open,
        output_dir=args.output_dir,
    )
    if args.summary_only:
        print(json.dumps(report["summary"] | {"verifier_status": report["verifier_status"]}, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(report.get("artifact_paths", {}), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
