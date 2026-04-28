#!/usr/bin/env python3
"""Run the manual-review quality gate for Level 3 conversational SDG JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import types as _types

if "cas_synthetic" not in sys.modules:
    pkg = _types.ModuleType("cas_synthetic")
    pkg.__file__ = str(_REPO_ROOT / "cas-synthetic" / "__init__.py")
    pkg.__path__ = [str(_REPO_ROOT / "cas-synthetic")]
    sys.modules["cas_synthetic"] = pkg

from cas_synthetic.validation.level3_review_gate import (
    Level3ReviewThresholds,
    result_to_jsonable,
    review_jsonl,
    write_review_markdown,
)


def _print_summary(result) -> None:
    print("\n=== Level 3 Conversational Review Gate ===")
    print(f"Status:              {'PASS' if result.ok else 'FAIL'}")
    print(f"Total records:       {result.total}")
    print(f"Unique prompts:      {result.metrics.get('unique_user_prompts')} "
          f"({result.metrics.get('prompt_unique_ratio')})")
    print(f"Unique responses:    {result.metrics.get('unique_assistant_responses')} "
          f"({result.metrics.get('response_unique_ratio')})")
    print(f"Short prompts:       {result.metrics.get('short_prompt_count')}")
    print(f"Short responses:     {result.metrics.get('short_response_count')}")
    print(
        "Missing CAS in response: "
        f"{result.metrics.get('missing_expression_in_response')}"
    )
    print(f"Bucket counts:       {result.metrics.get('bucket_counts')}")

    if result.failures:
        print("\nFailures:")
        for failure in result.failures:
            print(f"  - {failure}")
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=str, help="Level 3 conversational JSONL path")
    parser.add_argument("--sample-output", type=str, help="Optional Markdown sample report path")
    parser.add_argument("--json-output", type=str, help="Optional JSON metrics output path")
    parser.add_argument("--sample-per-bucket", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-prompt-unique-ratio", type=float, default=0.25)
    parser.add_argument("--min-response-unique-ratio", type=float, default=0.90)
    parser.add_argument("--min-bucket-prompt-unique-ratio", type=float, default=0.20)
    parser.add_argument("--max-short-prompt-fraction", type=float, default=0.02)
    parser.add_argument("--max-short-response-fraction", type=float, default=0.02)
    parser.add_argument("--min-prompt-words", type=int, default=6)
    parser.add_argument("--min-response-words", type=int, default=12)
    parser.add_argument(
        "--allow-missing-cas-in-response",
        action="store_true",
        help="Do not fail when assistant_response omits the exact cas_expression.",
    )
    args = parser.parse_args(argv)

    dataset_path = Path(args.path)
    if not dataset_path.exists():
        print(f"ERROR: dataset not found: {dataset_path}", file=sys.stderr)
        return 2

    thresholds = Level3ReviewThresholds(
        min_prompt_unique_ratio=args.min_prompt_unique_ratio,
        min_response_unique_ratio=args.min_response_unique_ratio,
        min_bucket_prompt_unique_ratio=args.min_bucket_prompt_unique_ratio,
        max_short_prompt_fraction=args.max_short_prompt_fraction,
        max_short_response_fraction=args.max_short_response_fraction,
        min_prompt_words=args.min_prompt_words,
        min_response_words=args.min_response_words,
        require_cas_expression_in_response=not args.allow_missing_cas_in_response,
    )
    result = review_jsonl(
        dataset_path,
        thresholds=thresholds,
        sample_per_bucket=args.sample_per_bucket,
        seed=args.seed,
    )

    if args.sample_output:
        write_review_markdown(result, args.sample_output)
    if args.json_output:
        out_path = Path(args.json_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(result_to_jsonable(result), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    _print_summary(result)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
