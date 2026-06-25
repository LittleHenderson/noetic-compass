"""CLI launcher for the legacy MT4 RECEIPT_PENDING archive tool.

Default behavior is DRY RUN — the operator sees how many stale rows WOULD
be archived without any file modification. To actually archive, the operator
must pass `--execute`.

Usage:
    py -3.12 -m scripts.run_legacy_receipts_archive            # preview
    py -3.12 -m scripts.run_legacy_receipts_archive --execute  # archive
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running directly via `python scripts/run_legacy_receipts_archive.py`.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.legacy_receipts_archive import archive_stale_receipts  # noqa: E402


DEFAULT_JOURNAL_PATH = "evidence_runs/agent_workflow_queue/agent-events.jsonl"
DEFAULT_SNAPSHOT_DIR = "evidence_runs/legacy_receipts_archive/"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Archive stale legacy MT4 RECEIPT_PENDING rows from the agent "
            "events journal. Dry run by default."
        )
    )
    parser.add_argument(
        "--journal-path",
        default=DEFAULT_JOURNAL_PATH,
        help=f"Path to the agent events journal (default: {DEFAULT_JOURNAL_PATH}).",
    )
    parser.add_argument(
        "--snapshot-dir",
        default=DEFAULT_SNAPSHOT_DIR,
        help=f"Directory for snapshot files (default: {DEFAULT_SNAPSHOT_DIR}).",
    )
    parser.add_argument(
        "--age-hours",
        type=float,
        default=24.0,
        help="Stale-age threshold in hours (default: 24.0).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually archive. Without this flag the run is dry_run.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print only the result JSON (no banner).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    result = archive_stale_receipts(
        journal_path=Path(args.journal_path),
        snapshot_dir=Path(args.snapshot_dir),
        dry_run=not args.execute,
        age_threshold_hours=args.age_hours,
    )

    payload = result.to_dict()
    if args.summary_only:
        print(json.dumps(payload, sort_keys=True))
    else:
        banner = "DRY RUN (preview only)" if result.dry_run else "EXECUTED"
        print(f"# legacy receipts archive — {banner}")
        print(json.dumps(payload, indent=2, sort_keys=True))

    if result.error_message:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
