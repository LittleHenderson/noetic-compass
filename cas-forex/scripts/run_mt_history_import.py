"""Import an MT4/MT5 account-history export into CAS Forex research evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.mt_history_import import import_mt_history, write_mt_history_import_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("history_export", help="Path to MT4/MT5 CSV or HTML account-history export.")
    parser.add_argument("--output-dir", default="evidence_runs/mt_history_import")
    args = parser.parse_args()

    report = import_mt_history(args.history_export)
    report_path = write_mt_history_import_report(report, args.output_dir)
    print(json.dumps({"report_path": str(report_path), "report": report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

