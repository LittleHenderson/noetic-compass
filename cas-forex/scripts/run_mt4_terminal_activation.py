"""Discover/stage MT4 terminal activation for CAS Forex."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.mt4_terminal_activation import (  # noqa: E402
    DEFAULT_EA_SOURCE_PATH,
    DEFAULT_MAILBOX_ROOT,
    DEFAULT_OUTPUT_DIR,
    build_mt4_terminal_activation_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terminal-data-dir", type=Path, default=None)
    parser.add_argument("--search-root", action="append", type=Path, default=[])
    parser.add_argument("--ea-source-path", type=Path, default=DEFAULT_EA_SOURCE_PATH)
    parser.add_argument("--mailbox-root", default=DEFAULT_MAILBOX_ROOT)
    parser.add_argument("--use-common-files", action="store_true")
    parser.add_argument("--install", action="store_true", help="Copy CASForexBridgeEA.mq4 into MQL4/Experts.")
    parser.add_argument("--no-create-mailbox", action="store_true", help="Do not create MQL4/Files mailbox folders.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = build_mt4_terminal_activation_report(
        terminal_data_dir=args.terminal_data_dir,
        search_roots=args.search_root or None,
        ea_source_path=args.ea_source_path,
        mailbox_root=args.mailbox_root,
        use_common_files=args.use_common_files,
        install_ea=args.install,
        create_mailbox=not args.no_create_mailbox,
        output_dir=args.output_dir,
    )
    if args.summary_only:
        payload = {
            "activation_status": report.get("activation_status"),
            "artifact_paths": report.get("artifact_paths", {}),
            "next_action": report.get("next_action"),
            "path_alignment": report.get("path_alignment"),
            "selected_terminal": report.get("selected_terminal"),
            "summary": report.get("summary", {}),
        }
    else:
        payload = report
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
