#!/usr/bin/env python3
"""End-to-end Level 2 generation: produces 10K examples in the canonical
30/25/15/20/10 mix.

Usage:
    python -m cas_synthetic.scripts.generate_level2 --n 10000 \
        --output cas-synthetic/data/level2_scaffold/level2_10k.jsonl \
        --seed 42

Flags:
    --n             target example count (default 10000)
    --output        output JSONL path
    --seed          RNG seed (default 42)
    --resume-from   resume at index N, append to file
    --workers       0 = sequential; >0 = multiprocessing pool (Level 2 sequential default)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Make package importable when run from repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import importlib.util

# Load cas_synthetic as a package-alias so "from cas_synthetic..." works.
_CAS_SYNTHETIC = _REPO_ROOT / "cas-synthetic"
if "cas_synthetic" not in sys.modules:
    import types as _types

    pkg = _types.ModuleType("cas_synthetic")
    pkg.__file__ = str(_CAS_SYNTHETIC / "__init__.py")
    pkg.__path__ = [str(_CAS_SYNTHETIC)]
    sys.modules["cas_synthetic"] = pkg

from cas_synthetic.mix_controller import Level2MixController, Level2MixConfig
from cas_synthetic.llm_interface import get_default_provider


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Level 2 CAS synthetic dataset")
    parser.add_argument("--n", type=int, default=10000)
    parser.add_argument(
        "--output",
        type=str,
        default=str(_CAS_SYNTHETIC / "data" / "level2_scaffold" / "level2_10k.jsonl"),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--resume-from", type=int, default=0)
    parser.add_argument("--workers", type=int, default=0, help="0 = sequential")
    args = parser.parse_args()

    provider = get_default_provider()
    if provider is None:
        print("WARN: no LLM provider credentials found; template-only generation.")
    else:
        print(f"Using LLM provider: {provider.NAME}")

    config = Level2MixConfig(seed=args.seed, llm_provider=provider)
    controller = Level2MixController(config=config)

    target_buckets = controller.bucket_sizes(args.n)
    print(f"Target buckets for n={args.n}: {target_buckets}")

    t0 = time.monotonic()
    report = controller.generate_to_jsonl(
        args.output, n=args.n, resume_from=args.resume_from
    )
    elapsed = time.monotonic() - t0
    report["elapsed_seconds"] = round(elapsed, 2)

    print("\n=== Generation complete ===")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
