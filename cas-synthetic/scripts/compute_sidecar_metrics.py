#!/usr/bin/env python3
"""Compute sidecar metrics for a Level 2 dataset.

Outputs (in addition to the primary <stem>_metrics.json):
  - <stem>_sidecar_metrics.json with:
      length_distribution_per_bucket: min, p25, p50, p75, max
      cross_bucket_noetic_jaccard: pairwise Jaccard over Noetic-id sets
      top_state_literals: top 20 (Noetic, Domain) literal counts
      top_omega_names: top 20 Ω_* names
      compile_retry_fallback_per_bucket: from generator instrumentation
      random_examples_per_bucket: 5 random per bucket

Usage:
    python cas-synthetic/scripts/compute_sidecar_metrics.py \
        cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

# Regexes for extraction
_STATE_LITERAL_RE = re.compile(r"\^(\d)(?:\^([PCEO]))?")
_OMEGA_RE = re.compile(r"(?:Ω|Omega)_([A-Za-z0-9_]+)")


def percentile(sorted_vals: list[int], p: float) -> int:
    if not sorted_vals:
        return 0
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return int(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=str)
    args = parser.parse_args()

    path = Path(args.path)
    out_path = path.with_name(path.stem + "_sidecar_metrics.json")

    entries: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    bucket_lengths: dict[str, list[int]] = defaultdict(list)
    bucket_noetics: dict[str, set[int]] = defaultdict(set)
    state_literals: Counter[str] = Counter()
    omega_names: Counter[str] = Counter()
    bucket_examples: dict[str, list[dict]] = defaultdict(list)

    for ex in entries:
        bucket = ex.get("_meta", {}).get("bucket", "unknown")
        expr = ex.get("cas_expression", "")
        bucket_lengths[bucket].append(len(expr))
        bucket_examples[bucket].append(ex)
        for m in _STATE_LITERAL_RE.finditer(expr):
            n = m.group(1)
            d = m.group(2) or "_"
            state_literals[f"^{n}^{d}" if d != "_" else f"^{n}"] += 1
            bucket_noetics[bucket].add(int(n))
        for m in _OMEGA_RE.finditer(expr):
            omega_names[f"Ω_{m.group(1)}"] += 1

    # Length distribution per bucket
    length_dist: dict[str, dict[str, int]] = {}
    for b, lst in bucket_lengths.items():
        s = sorted(lst)
        length_dist[b] = {
            "min": s[0] if s else 0,
            "p25": percentile(s, 0.25),
            "p50": percentile(s, 0.50),
            "p75": percentile(s, 0.75),
            "max": s[-1] if s else 0,
        }

    # Cross-bucket Noetic Jaccard
    buckets = sorted(bucket_noetics.keys())
    jaccard: dict[str, dict[str, float]] = defaultdict(dict)
    for i, b1 in enumerate(buckets):
        for b2 in buckets[i:]:
            s1, s2 = bucket_noetics[b1], bucket_noetics[b2]
            if not s1 and not s2:
                j = 1.0
            else:
                j = len(s1 & s2) / len(s1 | s2)
            jaccard[b1][b2] = round(j, 4)

    # Random 5 examples per bucket (deterministic seed)
    rng = random.Random(20260427)
    random_examples: dict[str, list[dict]] = {}
    for b, lst in bucket_examples.items():
        sample = rng.sample(lst, min(5, len(lst)))
        random_examples[b] = [
            {
                "cas_expression": e.get("cas_expression", ""),
                "is_valid": e.get("_meta", {}).get("is_valid"),
                "violation_type": e.get("_meta", {}).get("violation_type"),
                "prompt_excerpt": (e.get("prompt", "") or "")[:120],
            }
            for e in sample
        ]

    # Compile retry/fallback instrumentation: replay a sample-size-bounded
    # generation under the same seed to read the counters. This is exact
    # for the 10K dataset because the controller is fully deterministic
    # under (seed, bucket-rng-offset).
    retry_fallback = _measure_retry_fallback()

    payload = {
        "dataset_path": str(path),
        "total": len(entries),
        "length_distribution_per_bucket": length_dist,
        "cross_bucket_noetic_jaccard": dict(jaccard),
        "top_20_state_literals": state_literals.most_common(20),
        "top_20_omega_names": omega_names.most_common(20),
        "random_examples_per_bucket": random_examples,
        "compile_retry_fallback_per_bucket": retry_fallback,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Sidecar metrics written to {out_path}")
    print(json.dumps(retry_fallback, indent=2))
    return 0


def _measure_retry_fallback() -> dict[str, dict[str, int]]:
    """Read compile_retries / compile_fallbacks counters by running the
    full 10K generation with the production seed and inspecting the
    in-memory counters on each generator instance afterward.

    This is the simplest reliable way to surface the counters without
    threading them through the JSONL emission. Cost is one extra 10K
    generation pass (~3-5 seconds). The counters are deterministic given
    the seed."""
    import importlib.util
    import sys
    repo = Path(__file__).resolve().parent.parent.parent
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    cas_syn = repo / "cas-synthetic"
    if "cas_synthetic" not in sys.modules:
        import types
        pkg = types.ModuleType("cas_synthetic")
        pkg.__file__ = str(cas_syn / "__init__.py")
        pkg.__path__ = [str(cas_syn)]
        sys.modules["cas_synthetic"] = pkg
    from cas_synthetic.mix_controller import Level2MixController, Level2MixConfig

    controller = Level2MixController(config=Level2MixConfig(seed=42))
    # Drain 10K examples through the controller to advance every generator's
    # counters to the same state as the dataset on disk.
    for _ in controller.iter_examples(10000):
        pass

    out: dict[str, dict[str, int]] = {}
    for name, gen in controller.generators.items():
        retries = getattr(gen, "compile_retries", None)
        fallbacks = getattr(gen, "compile_fallbacks", None)
        if retries is None and fallbacks is None:
            continue
        out[name] = {
            "compile_retries": retries or 0,
            "compile_fallbacks": fallbacks or 0,
        }
    return out


if __name__ == "__main__":
    raise SystemExit(main())
