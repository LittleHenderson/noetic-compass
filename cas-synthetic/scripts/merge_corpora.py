"""Merge multiple Level 3 JSONL corpora into one combined training file.

Concatenates 1+ input JSONL files with joint-key deduplication on
(id, source_level2_id, cas_expression). Preserves order: earlier inputs
take precedence on collisions.

Usage:
    python cas-synthetic/scripts/merge_corpora.py \\
        --input cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl \\
        --input cas-synthetic/data/level2_scaffold/lever3_paired_freeform_5k_2026_05_04.jsonl \\
        --input cas-synthetic/data/level2_scaffold/level3_freeform_phase3.jsonl \\
        --input cas-synthetic/data/level2_scaffold/level3_meta_logic_balanced_2026_05_04.jsonl \\
        --output cas-synthetic/data/level2_scaffold/level3_combined_v1.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_num, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                sys.stderr.write(f"[warn] {path}:{line_num} skipping malformed line: {e}\n")
    return records


def joint_key(record: dict) -> tuple:
    return (
        str(record.get("id", "")),
        str(record.get("source_level2_id", "")),
        str(record.get("cas_expression", "")),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", required=True, type=Path,
                        help="Input JSONL file (repeatable; processed in order)")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dedupe-key", choices=("joint", "id"), default="joint",
                        help="Deduplication key — joint=(id, source_level2_id, cas_expression), id=id only")
    args = parser.parse_args()

    seen: set[tuple] = set()
    seen_ids: set[str] = set()
    duplicates_dropped = 0
    per_input_kept: dict[str, int] = {}

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", encoding="utf-8") as out:
        for input_path in args.input:
            if not input_path.exists():
                sys.stderr.write(f"[error] input not found: {input_path}\n")
                return 1
            kept = 0
            records = load_jsonl(input_path)
            for record in records:
                key: tuple
                if args.dedupe_key == "joint":
                    key = joint_key(record)
                    if key in seen:
                        duplicates_dropped += 1
                        continue
                    seen.add(key)
                else:
                    rid = str(record.get("id", ""))
                    if rid in seen_ids:
                        duplicates_dropped += 1
                        continue
                    seen_ids.add(rid)
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                kept += 1
            per_input_kept[input_path.name] = kept

    print(f"merged into {args.output}")
    for name, n in per_input_kept.items():
        print(f"  {name}: {n} kept")
    print(f"duplicates dropped: {duplicates_dropped}")
    print(f"total records: {sum(per_input_kept.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
