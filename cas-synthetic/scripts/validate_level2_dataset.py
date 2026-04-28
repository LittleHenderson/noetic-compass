#!/usr/bin/env python3
"""Validate a Level 2 JSONL dataset against the CAS notation compiler.

Per-example checks:
- Compile cas_expression via api/notation/compiler.compile_expression
- Track per-bucket valid/invalid counts
- Track Noetic / Domain / Drive / Register / Foundation coverage
- Detect duplicate cas_expression values
- Compute average expression length per bucket

Outputs:
- Prints a summary to stdout
- Writes JSON metrics to <output>_metrics.json next to the dataset

Usage:
    python cas-synthetic/scripts/validate_level2_dataset.py \
        cas-synthetic/data/level2_scaffold/level2_validation_1000.jsonl
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_COMPILER_PATH = (
    _REPO_ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "api"
    / "notation"
    / "compiler.py"
)


def _load_compiler():
    """Load the api.notation.compiler module from its absolute path.

    The hyphenated parent directory `noetic-compass-scaffold` is not a valid
    Python package name, so we load by file path via importlib. We must
    register the module in sys.modules before exec so that @dataclass
    machinery (which looks up cls.__module__ in sys.modules) works on
    Python 3.12+.
    """
    module_name = "cas_notation_compiler"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _COMPILER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load compiler from {_COMPILER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# --- Coverage extraction regexes (post-hoc on cas_expression strings) ---

# ^N where N is a digit 0-9 (Noetic)
_NOETIC_RE = re.compile(r"\^(\d)")
# ^N^D — domain letter (P/C/E/O) immediately following a Noetic+caret
_DOMAIN_RE = re.compile(r"\^\d\^([PCEO])")
# F_k or F{k} — drive index 1-7
_DRIVE_RE = re.compile(r"F[_{]?(\d)")
# |R or |⟨...⟩ — register letters T, A, f, E (lowercase f is canonical)
# Match a single register after a single pipe (avoid double pipes used elsewhere).
_REGISTER_RE = re.compile(r"\|([TAfE])(?![a-zA-Z])")
# Register set notation |⟨A,f,T⟩
_REGISTER_SET_RE = re.compile(r"\|⟨([^⟩]+)⟩")
# Foundation_k — meta-logic templates may reference Foundation indices
_FOUNDATION_RE = re.compile(r"Foundation[_]?(\d)")


def extract_coverage(expr: str) -> dict[str, set]:
    seen = {
        "noetics": set(),
        "domains": set(),
        "drives": set(),
        "registers": set(),
        "foundations": set(),
    }
    for m in _NOETIC_RE.finditer(expr):
        seen["noetics"].add(int(m.group(1)))
    for m in _DOMAIN_RE.finditer(expr):
        seen["domains"].add(m.group(1))
    for m in _DRIVE_RE.finditer(expr):
        seen["drives"].add(int(m.group(1)))
    for m in _REGISTER_RE.finditer(expr):
        seen["registers"].add(m.group(1))
    for m in _REGISTER_SET_RE.finditer(expr):
        for tok in m.group(1).split(","):
            tok = tok.strip()
            if tok in {"T", "A", "f", "E"}:
                seen["registers"].add(tok)
    for m in _FOUNDATION_RE.finditer(expr):
        try:
            seen["foundations"].add(int(m.group(1)))
        except ValueError:
            pass
    return seen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=str, help="JSONL dataset path")
    parser.add_argument(
        "--metrics-out",
        type=str,
        default=None,
        help="Where to write JSON metrics (default: <path>_metrics.json)",
    )
    args = parser.parse_args()

    dataset_path = Path(args.path)
    if not dataset_path.exists():
        print(f"ERROR: dataset not found: {dataset_path}", file=sys.stderr)
        return 2

    metrics_path = (
        Path(args.metrics_out)
        if args.metrics_out
        else dataset_path.with_name(dataset_path.stem + "_metrics.json")
    )

    # Load compiler
    compiler = _load_compiler()
    compile_expression = compiler.compile_expression

    # Load entries
    entries: list[dict] = []
    with open(dataset_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    total = len(entries)
    print(f"Loaded {total} entries from {dataset_path}")

    bucket_counts: Counter[str] = Counter()
    bucket_valid: Counter[str] = Counter()
    bucket_invalid: Counter[str] = Counter()
    bucket_expr_lengths: dict[str, list[int]] = defaultdict(list)
    expr_counter: Counter[str] = Counter()
    failures: list[dict] = []

    coverage_overall = {
        "noetics": set(),
        "domains": set(),
        "drives": set(),
        "registers": set(),
        "foundations": set(),
    }
    coverage_per_bucket: dict[str, dict[str, set]] = defaultdict(
        lambda: {
            "noetics": set(),
            "domains": set(),
            "drives": set(),
            "registers": set(),
            "foundations": set(),
        }
    )

    valid_count = 0
    invalid_count = 0

    for i, ex in enumerate(entries):
        bucket = ex.get("_meta", {}).get("bucket", "unknown")
        bucket_counts[bucket] += 1
        expr = ex.get("cas_expression", "")
        bucket_expr_lengths[bucket].append(len(expr))
        expr_counter[expr] += 1

        # Coverage extraction
        cov = extract_coverage(expr)
        for k, v in cov.items():
            coverage_overall[k] |= v
            coverage_per_bucket[bucket][k] |= v

        # Compile
        try:
            artifact = compile_expression(expr)
            ok = bool(artifact.valid)
            err = artifact.error
        except Exception as exc:  # pragma: no cover
            ok = False
            err = f"exception: {type(exc).__name__}: {exc}"

        if ok:
            valid_count += 1
            bucket_valid[bucket] += 1
        else:
            invalid_count += 1
            bucket_invalid[bucket] += 1
            failures.append(
                {
                    "index": i,
                    "bucket": bucket,
                    "cas_expression": expr,
                    "error": err,
                }
            )

    # Duplicate detection
    duplicates = {expr: c for expr, c in expr_counter.items() if c > 1}

    # Build metrics dict
    metrics = {
        "dataset_path": str(dataset_path),
        "total": total,
        "compilation": {
            "valid": valid_count,
            "invalid": invalid_count,
            "pass_rate": round(valid_count / total, 6) if total else 0.0,
        },
        "bucket_distribution": dict(bucket_counts),
        "bucket_valid": dict(bucket_valid),
        "bucket_invalid": dict(bucket_invalid),
        "bucket_pass_rate": {
            b: round(bucket_valid[b] / bucket_counts[b], 6)
            for b in bucket_counts
            if bucket_counts[b] > 0
        },
        "bucket_avg_expr_length": {
            b: round(sum(lst) / len(lst), 2) if lst else 0.0
            for b, lst in bucket_expr_lengths.items()
        },
        "duplicates": {
            "count": len(duplicates),
            "total_extra_copies": sum(c - 1 for c in duplicates.values()),
            "examples": dict(list(duplicates.items())[:10]),
        },
        "coverage_overall": {
            "noetics": sorted(coverage_overall["noetics"]),
            "domains": sorted(coverage_overall["domains"]),
            "drives": sorted(coverage_overall["drives"]),
            "registers": sorted(coverage_overall["registers"]),
            "foundations": sorted(coverage_overall["foundations"]),
        },
        "coverage_per_bucket": {
            b: {k: sorted(v) for k, v in c.items()}
            for b, c in coverage_per_bucket.items()
        },
        "compilation_failures": failures[:20],  # cap to first 20 for the artifact
        "compilation_failure_count_total": len(failures),
    }

    # Print summary
    print("\n=== Validation Summary ===")
    print(f"Total examples:             {total}")
    print(
        f"Compiled valid:             {valid_count} "
        f"({metrics['compilation']['pass_rate']*100:.2f}%)"
    )
    print(f"Compiled invalid:           {invalid_count}")
    print(f"Bucket distribution:        {metrics['bucket_distribution']}")
    print(f"Per-bucket pass rate:       {metrics['bucket_pass_rate']}")
    print(f"Per-bucket avg expr length: {metrics['bucket_avg_expr_length']}")
    print(
        f"Duplicates: {metrics['duplicates']['count']} unique exprs repeat; "
        f"{metrics['duplicates']['total_extra_copies']} extra copies"
    )
    print("\nCoverage (overall):")
    for k, v in metrics["coverage_overall"].items():
        print(f"  {k}: {v}")
    print("\nCoverage (per bucket):")
    for b, c in metrics["coverage_per_bucket"].items():
        print(f"  {b}: {c}")
    if failures:
        print(f"\nFirst {min(5, len(failures))} compilation failures:")
        for f in failures[:5]:
            print(f"  [{f['index']}] {f['bucket']}: {f['cas_expression'][:80]!r} -> {f['error']}")

    # Write metrics
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, "w", encoding="utf-8") as out:
        json.dump(metrics, out, indent=2, ensure_ascii=False)
    print(f"\nMetrics written to: {metrics_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
