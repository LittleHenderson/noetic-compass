"""Create an operator-critical state snapshot as a single ZIP backup."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.backup_restore import (
    DEFAULT_BACKUP_FILES,
    create_backup,
    manifest_to_dict,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repo root (defaults to cas-forex/).",
    )
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        required=True,
        help="Directory to write the snapshot ZIP into.",
    )
    parser.add_argument(
        "--patterns",
        nargs="*",
        default=list(DEFAULT_BACKUP_FILES),
        help="Glob patterns to back up (defaults to DEFAULT_BACKUP_FILES).",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print a compact summary instead of the full manifest.",
    )
    args = parser.parse_args()

    manifest = create_backup(
        repo_root=args.repo_root,
        snapshot_dir=args.snapshot_dir,
        file_patterns=tuple(args.patterns),
    )

    payload = manifest_to_dict(manifest)
    if args.summary_only:
        payload = {
            "snapshot_id": manifest.snapshot_id,
            "created_at_iso": manifest.created_at_iso,
            "snapshot_path": manifest.snapshot_path,
            "file_count": manifest.file_count,
            "total_bytes": manifest.total_bytes,
        }
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
