#!/usr/bin/env python3
"""Human labeling CLI for CAS validation study.

Presents prompt-response pairs and collects human ratings for:
- 10 Cognitive Operators (CO-0 through CO-9, each 0-10)
- 4 Domain Coherence ratings (P/C/E/O, each 0-10)

Saves results to validation/human_labels.json.

Usage:
    python validation/human_labeling_tool.py --results validation/baseline_results.json
    python validation/human_labeling_tool.py --results validation/baseline_results.json --rater "Dr. Smith"
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LABELS_FILE = Path(__file__).parent / "human_labels.json"

OPERATOR_NAMES = [
    "CO-0 Identity", "CO-1 Reflection", "CO-2 Abstraction",
    "CO-3 Concretization", "CO-4 Integration", "CO-5 Differentiation",
    "CO-6 Unification", "CO-7 Transformation", "CO-8 Expansion",
    "CO-9 Contraction",
]

DOMAIN_NAMES = ["Principled", "Cognitive", "Evaluative", "Operational"]


def load_labels() -> list[dict]:
    if LABELS_FILE.exists():
        return json.loads(LABELS_FILE.read_text())
    return []


def save_labels(labels: list[dict]) -> None:
    LABELS_FILE.write_text(json.dumps(labels, indent=2))


def get_score(name: str) -> int:
    """Prompt for a score 0-10 with validation."""
    while True:
        raw = input(f"  {name} [0-10]: ").strip()
        if raw.lower() in ("q", "quit", "exit"):
            raise KeyboardInterrupt
        try:
            score = int(raw)
            if 0 <= score <= 10:
                return score
            print("    Score must be between 0 and 10.")
        except ValueError:
            print("    Please enter a number 0-10.")


def label_one(prompt: str, response: str, rater: str, item_index: int) -> dict:
    """Collect human ratings for a single prompt-response pair."""
    print(f"\n{'='*70}")
    print(f"Item {item_index + 1}")
    print(f"{'='*70}")
    print(f"\nPROMPT:\n{prompt[:500]}{'...' if len(prompt) > 500 else ''}")
    print(f"\nRESPONSE (first 800 chars):\n{response[:800]}{'...' if len(response) > 800 else ''}")
    print(f"\n{'-'*40}")
    print("Rate each Cognitive Operator (0=absent, 5=moderate, 10=excellent):")

    operator_scores = []
    for name in OPERATOR_NAMES:
        operator_scores.append(get_score(name))

    print(f"\n{'-'*40}")
    print("Rate Domain Coherence (0=incoherent, 5=moderate, 10=fully coherent):")

    domain_scores = []
    for name in DOMAIN_NAMES:
        domain_scores.append(get_score(name))

    return {
        "prompt": prompt,
        "rater": rater,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operator_scores": operator_scores,
        "domain_scores": domain_scores,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Human labeling tool for CAS validation")
    parser.add_argument(
        "--results", type=str, default="validation/baseline_results.json",
        help="Path to baseline_results.json from run_baseline_study.py",
    )
    parser.add_argument("--rater", type=str, default="anonymous", help="Rater identifier")
    parser.add_argument("--start", type=int, default=0, help="Start from item index")
    parser.add_argument("--count", type=int, default=10, help="Number of items to label")
    args = parser.parse_args()

    results_path = Path(args.results)
    if not results_path.exists():
        print(f"Results file not found: {results_path}")
        print("Run validation/run_baseline_study.py first to generate baseline results.")
        sys.exit(1)

    results = json.loads(results_path.read_text())
    items = results.get("results", [])
    if not items:
        print("No results found in the file.")
        sys.exit(1)

    labels = load_labels()
    end = min(args.start + args.count, len(items))

    print(f"\nCAS Human Labeling Tool")
    print(f"Rater: {args.rater}")
    print(f"Items: {args.start + 1} to {end} of {len(items)}")
    print(f"Labels file: {LABELS_FILE}")
    print("Type 'q' at any prompt to quit and save progress.\n")

    try:
        for i in range(args.start, end):
            item = items[i]
            prompt = item.get("prompt", "")
            response = item.get("llm_response", "")
            if not response:
                response = "(no LLM response recorded)"

            label = label_one(prompt, response, args.rater, i)
            label["item_index"] = i
            labels.append(label)
            save_labels(labels)
            print(f"  Saved. ({i + 1 - args.start}/{end - args.start} done)")

    except KeyboardInterrupt:
        print("\n\nSession interrupted. Progress saved.")

    save_labels(labels)
    print(f"\nTotal labels saved: {len(labels)} in {LABELS_FILE}")


if __name__ == "__main__":
    main()
