"""Refresh the read-only CAS Forex spec context snapshot.

Examples:
  python scripts/refresh_spec_context.py
  python scripts/refresh_spec_context.py --source path/to/spec.xlsx
  python scripts/refresh_spec_context.py --source https://docs.google.com/spreadsheets/d/.../edit
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cas_forex.spec_context import DEFAULT_SNAPSHOT_DIR, write_snapshot


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=None,
        help=(
            "Local .xlsx/.md/.json source or Google Sheets URL. Defaults to "
            "CAS_FOREX_SPEC_CONTEXT_SOURCE or the newest spec workbook under outputs/."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_SNAPSHOT_DIR),
        help="Directory for spec_context.json, spec_context.md, and operator_constitution.md.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable status JSON.")
    return parser


def _summary(snapshot: dict[str, Any]) -> str:
    paths = snapshot.get("written_paths") if isinstance(snapshot.get("written_paths"), dict) else {}
    source = snapshot.get("source") if isinstance(snapshot.get("source"), dict) else {}
    return "\n".join(
        [
            "CAS Forex spec context refreshed",
            f"Version: {snapshot.get('version')}",
            f"Generated: {snapshot.get('generated_at')}",
            f"Source: {source.get('path_or_url')}",
            f"Source SHA-256: {source.get('sha256')}",
            f"Snapshot SHA-256: {snapshot.get('snapshot_hash_sha256')}",
            f"Sheets: {len(snapshot.get('sheets') or [])}",
            f"JSON: {paths.get('json')}",
            f"Markdown: {paths.get('markdown')}",
            f"Operator constitution: {paths.get('operator_constitution')}",
        ]
    )


def main() -> int:
    args = _parser().parse_args()
    snapshot = write_snapshot(args.source, output_dir=Path(args.output_dir))
    if args.json:
        print(
            json.dumps(
                {
                    "report_kind": "cas_forex_spec_context_refresh",
                    "version": snapshot.get("version"),
                    "generated_at": snapshot.get("generated_at"),
                    "source": snapshot.get("source"),
                    "snapshot_hash_sha256": snapshot.get("snapshot_hash_sha256"),
                    "sheet_count": len(snapshot.get("sheets") or []),
                    "written_paths": snapshot.get("written_paths"),
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(_summary(snapshot))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
