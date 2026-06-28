#!/usr/bin/env python3
"""Phase 3 driver: expand a Level 3 JSONL with free-form variants.

For each canonical Level 3 record, draws K (default 3) deterministic
free-form English variants of the user_prompt. Labels and CAS structure
are preserved byte-identically; only the ``user_prompt`` and a small
metadata block change.

Usage:

    python cas-synthetic/scripts/generate_freeform_corpus.py \\
        --input cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl \\
        --output cas-synthetic/data/level2_scaffold/level3_freeform_phase3.jsonl \\
        --variants-per-canonical 3 \\
        --seed 42

Flags:

    --limit          : process at most N input records (testing).
    --dry-run        : read input, build variants in memory, do not write.
    --progress-every : log every N output records (0 disables).
    --seed           : global seed; per-variant seeds are derived from
                       ``(record_id, variant_index, --seed)``.
    --variants-per-canonical : K, default 3.

This driver has NO API dependency — it uses only the rule-based
free_form generator. The full corpus run is a follow-on RunPod step;
a smoke run with ``--limit 50`` should complete in a few seconds on
local CPU.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# Make ``cas_synthetic`` importable when run by path.
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

from cas_synthetic.generator.free_form import expand_record


def _expand_one(
    record: dict[str, Any],
    *,
    k: int,
    global_seed: int,
) -> list[dict[str, Any]]:
    return expand_record(record, k=k, seed=global_seed)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 3 SDG driver: expand Level 3 conversational JSONL with K "
            "native free-form English variants per record (rule-based, no API)."
        )
    )
    parser.add_argument(
        "--input", required=True, help="Level 3 input JSONL path"
    )
    parser.add_argument(
        "--output", required=True, help="Free-form output JSONL path"
    )
    parser.add_argument(
        "--variants-per-canonical",
        type=int,
        default=3,
        help="K free-form variants to generate per canonical (default 3).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Global RNG seed (per-variant seeds are derived from this).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N input records (for smoke tests).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build variants in memory; do not write the output file.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1000,
        help="Print progress after this many output records (0 disables).",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.exists():
        print(f"ERROR: input not found: {input_path}", file=sys.stderr)
        return 2
    if args.variants_per_canonical < 1:
        print(
            "ERROR: --variants-per-canonical must be >= 1",
            file=sys.stderr,
        )
        return 2

    if not args.dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.monotonic()
    read = 0
    written = 0
    bucket_counts: dict[str, int] = {}

    out_handle = None
    try:
        if not args.dry_run:
            out_handle = open(output_path, "w", encoding="utf-8")

        with open(input_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if args.limit is not None and read >= args.limit:
                    break
                read += 1
                record = json.loads(line)
                variants = _expand_one(
                    record,
                    k=args.variants_per_canonical,
                    global_seed=args.seed,
                )
                bucket = str(record.get("bucket", "?"))
                bucket_counts[bucket] = bucket_counts.get(bucket, 0) + len(variants)
                for variant in variants:
                    if out_handle is not None:
                        out_handle.write(
                            json.dumps(variant, ensure_ascii=False) + "\n"
                        )
                    written += 1
                    if (
                        args.progress_every
                        and written % args.progress_every == 0
                    ):
                        print(
                            f"  wrote {written} variants from {read} canonicals"
                        )
    finally:
        if out_handle is not None:
            out_handle.close()

    report = {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "dry_run": bool(args.dry_run),
        "variants_per_canonical": args.variants_per_canonical,
        "seed": args.seed,
        "limit": args.limit,
        "read_records": read,
        "written_variants": written,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "expansion_method": "free_form_v1",
    }
    print("\n=== free-form Phase 3 expansion complete ===")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
