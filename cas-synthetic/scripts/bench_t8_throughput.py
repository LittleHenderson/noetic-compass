#!/usr/bin/env python3
"""Phase 1 T8 throughput benchmark for the conversational SDG generator.

Wraps Level3ConversationalGenerator with cold-cache wall-clock timing,
tracemalloc-based peak Python allocation, and a coarse split between
pure-generation cost (templating + record assembly) and serialization +
file-write cost.

The Level 3 conversational generator does NOT call the live CAS compiler
in the hot path -- it relies on cached source.metadata.is_valid produced at
Level 2 build time -- so "compiler/validator overhead" cannot be separately
measured from this script. That is recorded as N/A in the benchmark output
with explanation.

Usage:
    py -3.12 cas-synthetic/scripts/bench_t8_throughput.py \\
        --input cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl \\
        --output cas-synthetic/data/level2_scaffold/_bench/bench_run.jsonl \\
        --max-source-records 1000 --variants-per-source 5 \\
        --style-id recoverable_translation \\
        --json-summary cas-synthetic/data/level2_scaffold/_bench/bench_summary.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import tracemalloc
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

from cas_synthetic.generator.conversational import Level3ConversationalGenerator


def _measure_pure_generation(
    generator: Level3ConversationalGenerator,
    input_path: Path,
    *,
    max_source_records: int,
    variants_per_source: int,
    include_invalid_sources: bool,
) -> tuple[float, int]:
    """Drive the generator without writing output. Returns (seconds, n_records)."""
    n = 0
    t0 = time.monotonic()
    for _record in generator.iter_jsonl(
        input_path,
        max_source_records=max_source_records,
        variants_per_source=variants_per_source,
        include_invalid_sources=include_invalid_sources,
    ):
        n += 1
    return time.monotonic() - t0, n


def main() -> int:
    parser = argparse.ArgumentParser(description="T8 throughput benchmark")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-source-records", type=int, required=True)
    parser.add_argument("--variants-per-source", type=int, default=5)
    parser.add_argument("--style-id", action="append", default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--include-invalid-sources", action="store_true")
    parser.add_argument(
        "--json-summary",
        default=None,
        help="Optional path to write a JSON summary of measurements.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.exists():
        print(f"ERROR: input not found: {input_path}", file=sys.stderr)
        return 2

    print(f"[bench] input={input_path}")
    print(f"[bench] output={output_path}")
    print(
        f"[bench] sources={args.max_source_records} "
        f"variants={args.variants_per_source} styles={args.style_id}"
    )

    # Phase A: full pipeline (generation + JSONL serialize + file write).
    generator_full = Level3ConversationalGenerator(
        seed=args.seed,
        variants_per_source=args.variants_per_source,
        style_ids=args.style_id,
    )
    tracemalloc.start()
    t0 = time.monotonic()
    report = generator_full.generate_to_jsonl(
        input_path,
        output_path,
        max_source_records=args.max_source_records,
        variants_per_source=args.variants_per_source,
        progress_every=0,
        include_invalid_sources=args.include_invalid_sources,
    )
    full_seconds = time.monotonic() - t0
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    # Generator reports the count under "written".
    n_full = int(report.get("written", report.get("output_records_written", 0)))

    # Phase B: pure generation (consume iterator without writing output).
    generator_pure = Level3ConversationalGenerator(
        seed=args.seed,
        variants_per_source=args.variants_per_source,
        style_ids=args.style_id,
    )
    pure_seconds, n_pure = _measure_pure_generation(
        generator_pure,
        input_path,
        max_source_records=args.max_source_records,
        variants_per_source=args.variants_per_source,
        include_invalid_sources=args.include_invalid_sources,
    )

    output_size_bytes = output_path.stat().st_size if output_path.exists() else 0

    rps_full = n_full / full_seconds if full_seconds > 0 else 0.0
    rps_pure = n_pure / pure_seconds if pure_seconds > 0 else 0.0
    serialize_seconds = max(full_seconds - pure_seconds, 0.0)
    serialize_pct = (
        (serialize_seconds / full_seconds * 100.0) if full_seconds > 0 else 0.0
    )

    summary = {
        "input": str(input_path),
        "output": str(output_path),
        "max_source_records": args.max_source_records,
        "variants_per_source": args.variants_per_source,
        "style_ids": args.style_id,
        "seed": args.seed,
        "full_pipeline": {
            "seconds": round(full_seconds, 3),
            "records_written": n_full,
            "records_per_second": round(rps_full, 2),
            "peak_python_mem_mb": round(peak_bytes / 1024 / 1024, 2),
            "output_size_mb": round(output_size_bytes / 1024 / 1024, 3),
        },
        "pure_generation": {
            "seconds": round(pure_seconds, 3),
            "records_yielded": n_pure,
            "records_per_second": round(rps_pure, 2),
        },
        "serialization_overhead": {
            "seconds": round(serialize_seconds, 3),
            "percent_of_full": round(serialize_pct, 1),
            "note": "delta = full_pipeline - pure_generation; covers JSON serialization + file writes",
        },
        "compiler_overhead": {
            "seconds": None,
            "note": (
                "Level3ConversationalGenerator does not call the live CAS compiler "
                "in the hot path. It uses pre-computed Level 2 source.metadata.is_valid "
                "to skip invalid sources. Compiler/validator cost is paid at Level 2 "
                "scaffold build time, not Level 3 conversational generation time."
            ),
        },
        "report_from_generator": report,
    }

    print("\n=== T8 throughput benchmark ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if args.json_summary:
        Path(args.json_summary).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_summary).write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\n[bench] summary written to {args.json_summary}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
