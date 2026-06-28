#!/usr/bin/env python3
"""Expand a Level 3 JSONL with K demographic-tonal variants per record.

For each record in the input JSONL, draw K (profile, tone) pairs via
deterministic stratified sampling and emit K rewritten records into
the output JSONL. Labels and CAS structure are preserved; only the
``user_prompt`` and a small set of metadata fields change.

Usage:

    python cas-synthetic/scripts/expand_jsonl_demographic_tonal.py \
        --input cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl \
        --output cas-synthetic/data/level2_scaffold/level3_recoverable_demographic_K4.jsonl \
        --variants-per-canonical 4 \
        --seed 42

Flags:

    --limit          : process at most N input records (testing)
    --dry-run        : read input, build variants in memory, do not write
    --progress-every : log every N output records
    --seed           : global seed; per-record seeds are derived from
                       (record_id, profile, tone, --seed)
    --variants-per-canonical : K, default 4
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

# Make the cas_synthetic package importable when run by path.
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

from cas_synthetic.generator.demographic_tonal_axes import (
    ALL_PROFILE_TONE_PAIRS,
    stratified_sample,
)
from cas_synthetic.generator.demographic_tonal_rewrite import rewrite_record


def _per_record_seed(record_id: str, global_seed: int) -> int:
    """Derive a deterministic per-record seed for stratified sampling."""
    h = hashlib.sha1(
        f"{global_seed}|{record_id}".encode("utf-8")
    ).hexdigest()
    return int(h[:12], 16)


def _expand_one(
    record: dict[str, Any],
    *,
    k: int,
    global_seed: int,
) -> list[dict[str, Any]]:
    """Return K demographic-tonal variants for one canonical record."""
    record_id = str(record.get("id") or record.get("source_level2_id") or "")
    sample_seed = _per_record_seed(record_id, global_seed)
    pairs = stratified_sample(
        ALL_PROFILE_TONE_PAIRS, k=k, seed=sample_seed
    )
    variants: list[dict[str, Any]] = []
    for profile_code, tone_code in pairs:
        variant = rewrite_record(
            record,
            profile_code=profile_code,
            tone_code=tone_code,
        )
        variant_id_seed = hashlib.sha1(
            f"{record_id}|{profile_code}|{tone_code}|{global_seed}".encode("utf-8")
        ).hexdigest()[:12]
        variant["id"] = f"l3conv-dt-{variant_id_seed}"
        variants.append(variant)
    return variants


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Expand a Level 3 conversational JSONL with K demographic-tonal "
            "variants per record."
        )
    )
    parser.add_argument(
        "--input", required=True, help="Level 3 input JSONL path"
    )
    parser.add_argument(
        "--output", required=True, help="Demographic-tonal output JSONL path"
    )
    parser.add_argument(
        "--variants-per-canonical",
        type=int,
        default=4,
        help="K demographic-tonal variants to draw per canonical (default 4)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Global RNG seed (per-record seeds are derived from this).",
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
    if args.variants_per_canonical > len(ALL_PROFILE_TONE_PAIRS):
        print(
            f"ERROR: --variants-per-canonical {args.variants_per_canonical} "
            f"exceeds available pool of {len(ALL_PROFILE_TONE_PAIRS)} "
            f"(profile, tone) pairs",
            file=sys.stderr,
        )
        return 2

    if not args.dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.monotonic()
    read = 0
    written = 0
    profile_counts: dict[str, int] = {}
    tone_counts: dict[str, int] = {}
    pair_counts: dict[str, int] = {}

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
                for variant in variants:
                    profile = variant.get("demographic_profile", "?")
                    tone = variant.get("tonal_register", "?")
                    profile_counts[profile] = profile_counts.get(profile, 0) + 1
                    tone_counts[tone] = tone_counts.get(tone, 0) + 1
                    pair_key = f"{profile}|{tone}"
                    pair_counts[pair_key] = pair_counts.get(pair_key, 0) + 1
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
        "profile_counts": dict(sorted(profile_counts.items())),
        "tone_counts": dict(sorted(tone_counts.items())),
        "pair_counts": dict(sorted(pair_counts.items())),
    }
    print("\n=== demographic-tonal expansion complete ===")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
