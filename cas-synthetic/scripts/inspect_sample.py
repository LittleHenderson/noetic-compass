#!/usr/bin/env python3
"""Pretty-print a few examples from a JSONL file for human review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Pretty-print sample examples")
    parser.add_argument("path", type=str)
    parser.add_argument("--n", type=int, default=5)
    parser.add_argument("--bucket", type=str, default=None, help="filter by bucket")
    args = parser.parse_args()

    shown = 0
    with open(args.path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ex = json.loads(line)
            if args.bucket and ex.get("_meta", {}).get("bucket") != args.bucket:
                continue
            print("-" * 60)
            print(json.dumps(ex, indent=2, ensure_ascii=False))
            shown += 1
            if shown >= args.n:
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
