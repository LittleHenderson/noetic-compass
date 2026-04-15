#!/usr/bin/env python3
"""Seed validation/evidence_log.json from baseline study + human labels.

This produces actual evidence entries from the current validation artifacts:
- scorer agreement cases derived from machine vs human-panel item means
- benchmark suite runs derived from baseline_results summary
- false positive / false negative cases derived from tier disagreement
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.validation.evidence import build_evidence_summary, seed_evidence_from_artifacts


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed validation evidence log from existing artifacts")
    parser.add_argument("--baseline", default="validation/baseline_results.json")
    parser.add_argument("--labels", default="validation/human_labels.json")
    parser.add_argument("--output", default="validation/evidence_log.json")
    parser.add_argument("--append", action="store_true", help="Append instead of replacing the evidence log")
    args = parser.parse_args()

    store = seed_evidence_from_artifacts(
        baseline_path=Path(args.baseline),
        labels_path=Path(args.labels),
        path=Path(args.output),
        replace=not args.append,
    )
    summary = build_evidence_summary(store)
    print("Seeded validation evidence log:")
    print(f"  scorer_agreement: {summary['scorer_agreement']['count']}")
    print(f"  benchmark_suites: {summary['benchmark_suites']['count']}")
    print(f"  error_cases: {summary['error_cases']['count']}")


if __name__ == "__main__":
    main()
