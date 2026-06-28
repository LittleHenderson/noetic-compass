#!/usr/bin/env python3
"""Generate deterministic CAS Transformer turn records.

Usage:
    python cas-synthetic/scripts/generate_cas_transformer_turns.py \
        --output cas-synthetic/data/cas_transformer_turns_1k.jsonl \
        --count 1000 \
        --seed 42
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
from cas_synthetic.validation.cas_transformer_recovery import RecoveryFidelityScorer


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate deterministic CAS Transformer turn JSONL records"
    )
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--count", type=int, default=1000, help="Number of records")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
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
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generator = CASTransformerTurnGenerator(seed=args.seed)
    scorer = RecoveryFidelityScorer()
    bucket_counts: Counter[str] = Counter()
    recovery_scores: list[float] = []
    recovery_failures = 0
    invalid = 0
    t0 = time.monotonic()

    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        for index, record in enumerate(generator.iter_records(args.count), start=1):
            errors = record.validate()
            if errors:
                invalid += 1
                raise RuntimeError(f"{record.id} failed validation: {errors}")
            recovery = scorer.score_record(record)
            recovery_scores.append(recovery.score)
            if not recovery.passed:
                recovery_failures += 1
                raise RuntimeError(
                    f"{record.id} failed recovery fidelity: {recovery.to_dict()}"
                )
            bucket_counts[str(record.provenance.get("bucket", "unknown"))] += 1
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
            if args.progress_every and index % args.progress_every == 0:
                print(f"wrote {index} records...")

    report = {
        "output": str(output_path),
        "count": args.count,
        "valid": args.count - invalid,
        "invalid": invalid,
        "seed": args.seed,
        "generator": generator.GENERATOR_VERSION,
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "recovery": {
            "checked": len(recovery_scores),
            "passed": len(recovery_scores) - recovery_failures,
            "failed": recovery_failures,
            "min_score": round(min(recovery_scores), 6) if recovery_scores else None,
            "mean_score": (
                round(sum(recovery_scores) / len(recovery_scores), 6)
                if recovery_scores
                else None
            ),
        },
        "elapsed_seconds": round(time.monotonic() - t0, 2),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
