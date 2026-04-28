#!/usr/bin/env python3
"""Torch-free smoke check for Level 3 conversational CAS-Native ingestion."""

from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path
from typing import Sequence

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

_CAS_NATIVE_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _CAS_NATIVE_ROOT.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

if "cas_native" not in sys.modules:
    package = types.ModuleType("cas_native")
    package.__file__ = str(_CAS_NATIVE_ROOT / "__init__.py")
    package.__path__ = [str(_CAS_NATIVE_ROOT)]
    sys.modules["cas_native"] = package

from cas_native.training.level3_conversation_ingest import (
    score_payload,
    summarize_level3_ingestion,
)


def _load_jsonl(path: Path, max_records: int | None) -> list[dict]:
    records: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if max_records is not None and len(records) >= max_records:
                break
            line = line.strip()
            if not line:
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                records.append(value)
    return records


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=str, help="Level 3 conversational JSONL path")
    parser.add_argument("--max-records", type=int, default=512)
    args = parser.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        print(f"ERROR: dataset not found: {path}", file=sys.stderr)
        return 2

    records = _load_jsonl(path, None if args.max_records <= 0 else args.max_records)
    summary = summarize_level3_ingestion(records)
    print("\n=== CAS-Native Level 3 Ingestion Smoke ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if records:
        first_scores = score_payload(records[0])
        print("\nFirst normalized score keys:", sorted(first_scores.keys()))
        print("First operator target length:", len(first_scores.get("operator_scores", [])))
        print("First domain target length:", len(first_scores.get("domain_scores", [])))

    return 0 if summary["total"] > 0 and summary["invalid"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
