"""Restore operator-critical state from a backup ZIP (dry-run by default).

By default this command previews the restore (dry-run). The destructive
write only happens when --execute is passed explicitly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.backup_restore import (
    evaluate_restore,
    execute_restore,
    result_to_dict,
)


def _split_only_files(value: str | None) -> list[str] | None:
    if value is None:
        return None
    items = [s.strip() for s in value.split(",") if s.strip()]
    return items or None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repo root (defaults to cas-forex/).",
    )
    parser.add_argument(
        "--snapshot-path",
        type=Path,
        required=True,
        help="Path to the backup ZIP to restore from.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the restore (DESTRUCTIVE). Default is dry-run.",
    )
    parser.add_argument(
        "--only-files",
        type=str,
        default=None,
        help="Comma-separated relative paths to limit the restore scope.",
    )
    args = parser.parse_args()

    only_files = _split_only_files(args.only_files)

    if args.execute:
        result = execute_restore(
            snapshot_path=args.snapshot_path,
            repo_root=args.repo_root,
            only_files=only_files,
        )
    else:
        result = evaluate_restore(
            snapshot_path=args.snapshot_path,
            repo_root=args.repo_root,
        )

    print(json.dumps(result_to_dict(result), indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
