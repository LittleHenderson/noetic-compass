"""CLI for the CAS Forex MT4 closed-history export verifier."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_forex.mt4_history_export_verifier import (  # noqa: E402
    DEFAULT_EA_SOURCE_PATH,
    DEFAULT_INGEST_OUTPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    build_mt4_history_export_verifier_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify MT4 closed-history exporter output and ingest compatibility.")
    parser.add_argument("--terminal-data-dir", type=Path, default=None)
    parser.add_argument("--mailbox-dir", type=Path, default=None)
    parser.add_argument("--history-export-path", type=Path, default=None)
    parser.add_argument("--status-path", type=Path, default=None)
    parser.add_argument("--ea-source-path", type=Path, default=DEFAULT_EA_SOURCE_PATH)
    parser.add_argument("--memory-report-dir", type=Path, default=None)
    parser.add_argument("--no-ingest", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--ingest-output-dir", type=Path, default=DEFAULT_INGEST_OUTPUT_DIR)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = build_mt4_history_export_verifier_report(
        terminal_data_dir=args.terminal_data_dir,
        mailbox_dir=args.mailbox_dir,
        history_export_path=args.history_export_path,
        status_path=args.status_path,
        ea_source_path=args.ea_source_path,
        memory_report_dir=args.memory_report_dir,
        run_ingest=not args.no_ingest,
        output_dir=args.output_dir,
        ingest_output_dir=args.ingest_output_dir,
    )
    if args.summary_only:
        payload = {
            "artifact_paths": report.get("artifact_paths", {}),
            "next_action": report.get("next_action"),
            "verifier_status": report.get("verifier_status"),
            "summary": report.get("summary", {}),
        }
    else:
        payload = report
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
