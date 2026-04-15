#!/usr/bin/env python3
"""Generate synthetic CAS training data.

Each training triple contains:
  - cas_expression: a compiler-validated CAS expression
  - english_text: a natural English scenario matching the expression
  - scores: ground truth operator/domain/drive/lacunarity labels

Usage:
  python cas-native/data/generate_training_data.py --n 10000
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

# Add project root to path so we can import the compiler
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from api.notation.compiler import compile_expression  # noqa: E402
from cas_native_data.expression_generator import CASExpressionGenerator  # noqa: E402
from cas_native_data.english_generator import generate_english  # noqa: E402
from cas_native_data.score_extractor import extract_scores  # noqa: E402
from cas_native_data.validate_data import validate_dataset  # noqa: E402


# Alias the data package so imports work when running as script
import importlib
import types
_data_pkg_path = Path(__file__).resolve().parent
if "cas_native_data" not in sys.modules:
    pkg = types.ModuleType("cas_native_data")
    pkg.__file__ = str(_data_pkg_path / "__init__.py")
    pkg.__path__ = [str(_data_pkg_path)]
    sys.modules["cas_native_data"] = pkg
    # Import submodules
    for mod_name in ["expression_generator", "english_generator", "score_extractor", "validate_data"]:
        mod = importlib.import_module(f"cas_native_data.{mod_name}")
        setattr(pkg, mod_name, mod)
        sys.modules[f"cas_native_data.{mod_name}"] = mod


def generate_batch(
    n: int = 10000,
    output_path: str = "cas-native/data/training_data.jsonl",
    seed: int = 42,
) -> dict:
    """Generate n training triples and save as JSONL."""
    rng = random.Random(seed)
    generator = CASExpressionGenerator(compile_expression, seed=seed)
    eng_rng = random.Random(seed + 1)

    complexity_weights = {"simple": 0.3, "medium": 0.5, "complex": 0.2}
    complexities = list(complexity_weights.keys())
    weights = list(complexity_weights.values())

    generated = 0
    failed = 0
    t0 = time.monotonic()

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w", encoding="utf-8") as f:
        while generated < n:
            complexity = rng.choices(complexities, weights=weights, k=1)[0]

            result = generator.generate_and_validate(complexity=complexity)
            if result is None:
                failed += 1
                continue

            expression, compilation = result
            english = generate_english(expression, eng_rng)
            scores = extract_scores(expression, compilation)

            triple = {
                "id": f"syn_{generated:06d}",
                "cas_expression": expression,
                "english_text": english,
                "scores": scores,
                "complexity": complexity,
                "compilation": {
                    "valid": compilation.valid,
                    "tokens": len(compilation.tokens),
                    "bytecode": len(compilation.bytecode),
                },
            }

            f.write(json.dumps(triple, ensure_ascii=False) + "\n")
            generated += 1

            if generated % 1000 == 0:
                elapsed = time.monotonic() - t0
                print(f"  Generated {generated}/{n} ({failed} failed) [{elapsed:.1f}s]")

    elapsed = time.monotonic() - t0
    print(f"\nDone: {generated} triples, {failed} failures in {elapsed:.1f}s")
    print(f"Saved to {out}")

    # Validate
    print("\nRunning quality validation...")
    report = validate_dataset(out)
    print(f"  Valid compilations: {report.get('valid_rate', 0):.1%}")
    print(f"  Score consistency:  {report.get('score_consistency_rate', 0):.1%}")
    print(f"  Unique expressions: {report.get('unique_expressions', 0)}/{report.get('total', 0)}")
    print(f"  Duplicate rate:     {report.get('duplicate_rate', 0):.1%}")
    print(f"  Avg English length: {report.get('avg_english_length', 0)} words")
    if report.get("warnings"):
        for w in report["warnings"]:
            print(f"  WARNING: {w}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate CAS training data")
    parser.add_argument("--n", type=int, default=10000, help="Number of triples to generate")
    parser.add_argument("--output", type=str, default="cas-native/data/training_data.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate_batch(n=args.n, output_path=args.output, seed=args.seed)
