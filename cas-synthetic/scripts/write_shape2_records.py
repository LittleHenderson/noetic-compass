#!/usr/bin/env python3
"""Write Shape 2 transition records from deterministic CAS Transformer turns.

This is the v0 offline writer for the Shape 2 data engine. Live service
integration can call Shape2RecordWriter directly once accepted transitions come
from the service instead of the deterministic turn generator.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_CAS_SYNTHETIC = _REPO_ROOT / "cas-synthetic"
if "cas_synthetic" not in sys.modules:
    import types as _types

    pkg = _types.ModuleType("cas_synthetic")
    pkg.__file__ = str(_CAS_SYNTHETIC / "__init__.py")
    pkg.__path__ = [str(_CAS_SYNTHETIC)]
    sys.modules["cas_synthetic"] = pkg

from cas_synthetic.generator.cas_transformer import CASTransformerTurnGenerator
from cas_synthetic.schemas.shape2 import SHAPE2_SCHEMA_VERSION, Shape2RecordWriter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write Shape 2 transition-capture JSONL records"
    )
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--count", type=int, default=1000, help="Number of records")
    parser.add_argument("--seed", type=int, default=42, help="Generator seed")
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1000,
        help="Print progress after this many records; 0 disables progress",
    )
    args = parser.parse_args()

    if args.count < 0:
        parser.error("--count must be non-negative")

    output_path = Path(args.output)
    if output_path.exists():
        output_path.unlink()

    generator = CASTransformerTurnGenerator(seed=args.seed)
    writer = Shape2RecordWriter(output_path)
    bucket_counts: Counter[str] = Counter()
    rf_scores: list[float] = []
    t0 = time.monotonic()

    for index, turn_record in enumerate(generator.iter_records(args.count), start=1):
        shape2_record = writer.write_from_turn(turn_record)
        rf_scores.append(shape2_record.rf_score)
        bucket_counts[str(turn_record.provenance.get("bucket", "unknown"))] += 1
        if args.progress_every and index % args.progress_every == 0:
            print(f"wrote {index} Shape 2 records...")

    report = {
        "schema_version": SHAPE2_SCHEMA_VERSION,
        "output": str(output_path),
        "count": args.count,
        "seed": args.seed,
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "rf_score": {
            "min": round(min(rf_scores), 6) if rf_scores else None,
            "mean": round(sum(rf_scores) / len(rf_scores), 6) if rf_scores else None,
        },
        "elapsed_seconds": round(time.monotonic() - t0, 2),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

