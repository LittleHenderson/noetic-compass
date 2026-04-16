#!/usr/bin/env python3
"""Generate verified CAS training data with round-trip hallucination detection.

Pipeline:
  1. Generate random valid CAS expression → compiler validates
  2. Send to LLM provider → get natural English scenario
  3. Feed English back through signal analyzer → re-extract scores
  4. Compare re-extracted vs original → accept if 3/4 criteria match
  5. Rotate providers: Gemini generates, Claude verifies, etc.

Usage:
  python cas-native/data/generate_verified_data.py --n 1000 --providers openai,anthropic,google
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
import time
from pathlib import Path

# Ensure project root is importable
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

_data_dir = Path(__file__).resolve().parent
if str(_data_dir) not in sys.path:
    sys.path.insert(0, str(_data_dir))

from api.notation.compiler import compile_expression
from api.pipeline.text_signal_analyzer import analyze_text_signals
from expression_generator import CASExpressionGenerator
from score_extractor import extract_scores
from verifier import verify_round_trip
from llm_english_generator import LLMEnglishGenerator
from validate_data import validate_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("datagen")


async def generate_verified_batch(
    n: int = 1000,
    output_path: str = "cas-native/data/verified_training_data.jsonl",
    providers: list[str] | None = None,
    max_attempts_per_triple: int = 3,
    seed: int = 42,
) -> dict:
    """Generate n verified training triples with round-trip hallucination detection.

    Each triple:
    1. Random valid CAS expression (compiler-validated)
    2. LLM-generated English scenario
    3. Round-trip verified: English → signal analyzer → compare with original

    Provider rotation ensures diversity and reduces systematic bias.
    """
    rng = random.Random(seed)
    expr_gen = CASExpressionGenerator(compile_expression, seed=seed)
    llm_gen = LLMEnglishGenerator(providers=providers)

    complexities = ["simple", "medium", "complex"]
    weights = [0.3, 0.5, 0.2]

    accepted = 0
    rejected = 0
    total_attempts = 0
    provider_counts: dict[str, int] = {}

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.monotonic()

    with open(out, "w", encoding="utf-8") as f:
        while accepted < n:
            # 1. Generate random valid CAS expression
            complexity = rng.choices(complexities, weights=weights, k=1)[0]
            result = expr_gen.generate_and_validate(complexity=complexity)
            if result is None:
                continue

            expression, compilation = result
            scores = extract_scores(expression, compilation)

            # 2. Try LLM generation with round-trip verification
            verified = False
            for attempt in range(max_attempts_per_triple):
                total_attempts += 1
                try:
                    english, provider = await llm_gen.generate_async(expression)
                except RuntimeError as exc:
                    logger.warning("All providers failed for %s: %s", expression[:40], exc)
                    break

                # 3. Round-trip verification
                signals = analyze_text_signals(english)
                verification = verify_round_trip(
                    original_expression=expression,
                    signal_operator_scores=signals.operator_scores,
                    signal_domain_scores=signals.domain_scores,
                    signal_drive_scores=signals.drive_scores,
                )

                if verification.accepted:
                    triple = {
                        "id": f"ver_{accepted:06d}",
                        "cas_expression": expression,
                        "english_text": english,
                        "scores": scores,
                        "complexity": complexity,
                        "verification": {
                            "accepted": True,
                            "confidence": verification.confidence,
                            "matches": verification.matches,
                            "total": verification.total,
                            "provider": provider,
                            "attempt": attempt + 1,
                        },
                        "compilation": {
                            "valid": True,
                            "tokens": len(compilation.tokens),
                            "bytecode": len(compilation.bytecode),
                        },
                    }
                    f.write(json.dumps(triple, ensure_ascii=False) + "\n")
                    accepted += 1
                    verified = True
                    provider_counts[provider] = provider_counts.get(provider, 0) + 1
                    break
                else:
                    rejected += 1
                    if attempt == 0:
                        logger.debug(
                            "Rejected (%d/4 match): %s | %s",
                            verification.matches,
                            expression[:40],
                            "; ".join(verification.reasons[:2]),
                        )

            if accepted % 50 == 0 and accepted > 0:
                elapsed = time.monotonic() - t0
                rate = accepted / max(total_attempts, 1)
                logger.info(
                    "Accepted: %d/%d | Rejected: %d | Rate: %.0f%% | %.1fs",
                    accepted, n, rejected, rate * 100, elapsed,
                )

    elapsed = time.monotonic() - t0
    rate = accepted / max(total_attempts, 1)

    logger.info("=" * 60)
    logger.info("DONE: %d verified triples in %.1fs", accepted, elapsed)
    logger.info("Rejected: %d hallucinations caught", rejected)
    logger.info("Acceptance rate: %.1f%%", rate * 100)
    logger.info("Provider distribution: %s", provider_counts)

    # Run quality validation
    logger.info("Running quality validation...")
    report = validate_dataset(out)
    logger.info("Valid: %.0f%% | Consistent: %.0f%% | Duplicates: %.0f%%",
                report.get("valid_rate", 0) * 100,
                report.get("score_consistency_rate", 0) * 100,
                report.get("duplicate_rate", 0) * 100)
    if report.get("warnings"):
        for w in report["warnings"]:
            logger.warning(w)

    return {
        "accepted": accepted,
        "rejected": rejected,
        "total_attempts": total_attempts,
        "acceptance_rate": round(rate, 4),
        "provider_distribution": provider_counts,
        "elapsed_seconds": round(elapsed, 1),
        "validation": report,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate verified CAS training data")
    parser.add_argument("--n", type=int, default=1000, help="Number of verified triples to generate")
    parser.add_argument("--output", type=str, default="cas-native/data/verified_training_data.jsonl")
    parser.add_argument("--providers", type=str, default="openai,anthropic,google",
                        help="Comma-separated list of LLM providers to rotate")
    parser.add_argument("--max-attempts", type=int, default=3, help="Max LLM attempts per triple")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    providers = [p.strip() for p in args.providers.split(",")]

    report = asyncio.run(generate_verified_batch(
        n=args.n,
        output_path=args.output,
        providers=providers,
        max_attempts_per_triple=args.max_attempts,
        seed=args.seed,
    ))

    # Save report
    report_path = Path(args.output).with_suffix(".report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
