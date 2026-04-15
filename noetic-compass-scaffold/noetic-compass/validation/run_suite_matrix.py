#!/usr/bin/env python3
"""Run a matrix of validation studies across multiple prompt collections."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from api.validation.studies import available_prompt_collections, run_suite_matrix  # noqa: E402


async def _main_async(args: argparse.Namespace) -> int:
    suites = [item.strip() for item in args.suites.split(",")] if args.suites else None
    dials = [int(x.strip()) for x in args.dials.split(",")] if args.dials else None
    result = await run_suite_matrix(
        provider=args.provider,
        suite_ids=suites,
        count_per_suite=args.count_per_suite,
        dials=dials,
        model=args.model,
        scoring_mode=args.scoring_mode,
        scoring_provider=args.scoring_provider,
        scoring_model=args.scoring_model,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["failed_count"] == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a validation suite matrix")
    parser.add_argument("--provider", default="mock")
    parser.add_argument("--count-per-suite", type=int, default=5)
    parser.add_argument("--suites", default=None, help="Comma-separated prompt collection ids. Omit to run all standard collections.")
    parser.add_argument("--model", default=None)
    parser.add_argument("--scoring-mode", default="heuristic_fallback", choices=["heuristic_fallback", "secondary_llm", "self_reported"])
    parser.add_argument("--scoring-provider", default=None)
    parser.add_argument("--scoring-model", default=None)
    parser.add_argument("--dials", default=None)
    parser.add_argument("--list", action="store_true", help="List available prompt collection ids and exit")
    args = parser.parse_args()

    if args.list:
        print(json.dumps(available_prompt_collections(), indent=2))
        raise SystemExit(0)

    raise SystemExit(asyncio.run(_main_async(args)))


if __name__ == "__main__":
    main()
