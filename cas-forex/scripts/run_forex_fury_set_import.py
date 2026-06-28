"""Import owner-supplied Forex Fury set files into CAS Forex evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.forex_fury_sets import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SOURCE_DIR,
    build_forex_fury_set_import,
    write_forex_fury_set_import_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="Forex Fury package directory containing .set files and tester reports.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated CAS Forex import reports.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print a summary without writing report files.",
    )
    args = parser.parse_args()

    if args.summary_only:
        report = build_forex_fury_set_import(args.source_dir)
        print(json.dumps(report["summary"], indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    paths = write_forex_fury_set_import_report(args.source_dir, args.output_dir)
    print(json.dumps({key: str(value) for key, value in paths.items()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
