#!/usr/bin/env python3
"""Run a validation baseline study and archive the resulting artifact."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from api.validation.studies import (  # noqa: E402
    default_prompts_path,
    resolve_prompt_collection,
    run_and_archive_study,
)


def _print_summary(bundle: dict, *, archive_path: Path, output_path: Path | None) -> None:
    summary = bundle.get("summary", {})
    print("CAS Baseline Validation Study")
    print(f"Provider: {summary.get('provider')}")
    print(f"Study:    {summary.get('study_label')}")
    print(f"Prompts:  {summary.get('prompt_count')} from {summary.get('prompt_source')}")
    print(f"Status:   {summary.get('status')}")
    print(f"Success:  {summary.get('successes')}")
    print(f"Failures: {summary.get('failures')}")
    if "composite_mean" in summary:
        print(f"Composite mean: {summary.get('composite_mean')} (std={summary.get('composite_std')})")
    print(f"Archive:  {archive_path}")
    if output_path:
        print(f"Output:   {output_path}")


async def _main_async(args: argparse.Namespace) -> int:
    prompts_path = resolve_prompt_collection(args.prompts) if args.prompts else default_prompts_path()
    dials = [int(x.strip()) for x in args.dials.split(",")] if args.dials else None
    output_path = Path(args.output) if args.output else None
    result = await run_and_archive_study(
        provider=args.provider,
        count=args.count,
        prompts_path=prompts_path,
        output_path=output_path,
        dials=dials,
        model=args.model,
        scoring_mode=args.scoring_mode,
        scoring_provider=args.scoring_provider,
        scoring_model=args.scoring_model,
        study_label=args.label,
        update_default_output=not args.no_default_output,
    )
    bundle = result["bundle"]
    _print_summary(bundle, archive_path=result["archive_path"], output_path=result.get("output_path"))
    if args.print_json:
        print(json.dumps(bundle.get("summary", {}), indent=2))
    summary = bundle.get("summary", {})
    return 0 if summary.get("successes", 0) > 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CAS baseline validation study")
    parser.add_argument("--provider", default="mock", help="LLM provider (mock, openai, anthropic, google, xai, deepseek, qwen, meta)")
    parser.add_argument("--count", type=int, default=50, help="Number of prompts to run")
    parser.add_argument(
        "--prompts",
        default=str(default_prompts_path().relative_to(Path(__file__).resolve().parent.parent)),
        help="Prompt collection id or path (sample_prompts, augmented_library, ai_safety, ...)",
    )
    parser.add_argument("--output", default="validation/baseline_results.json", help="Write/update the canonical baseline output path")
    parser.add_argument("--label", default=None, help="Optional study label used in the archived artifact name")
    parser.add_argument("--model", default=None, help="Optional provider-specific model override")
    parser.add_argument("--scoring-mode", default="heuristic_fallback", choices=["heuristic_fallback", "secondary_llm", "self_reported"])
    parser.add_argument("--scoring-provider", default=None, help="Optional secondary scorer provider override")
    parser.add_argument("--scoring-model", default=None, help="Optional secondary scorer model override")
    parser.add_argument("--dials", type=str, default=None, help="Comma-separated dial values (e.g. 6,6,6,6,6,6,6,6,6,6)")
    parser.add_argument("--no-default-output", action="store_true", help="Archive the run without overwriting validation/baseline_results.json")
    parser.add_argument("--print-json", action="store_true", help="Print the summary JSON to stdout after the run")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_main_async(args)))


if __name__ == "__main__":
    main()
