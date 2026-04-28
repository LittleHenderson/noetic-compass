#!/usr/bin/env python3
"""Validate a Level 3 conversational SDG JSONL dataset."""

from __future__ import annotations

import argparse
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

from cas_synthetic.validation.level3_conversation_validator import (
    CompilerUnavailableError,
    Level3ConversationValidator,
    Level3ValidationSummary,
)


def _print_summary(summary: Level3ValidationSummary, max_errors: int) -> None:
    print("\n=== Level 3 Conversation Validation ===")
    print(f"Total records:      {summary.total}")
    print(f"Valid records:      {summary.valid}")
    print(f"Invalid records:    {summary.invalid}")
    print(f"Compiler checked:   {summary.compiler_checked}")
    print(f"Compiler skipped:   {summary.compiler_skipped}")
    print(f"Bucket counts:      {dict(summary.bucket_counts)}")

    if not summary.issues:
        return

    shown = min(max_errors, len(summary.issues))
    print(f"\nFirst {shown} invalid record(s):")
    for issue in summary.issues[:shown]:
        record_id = f" id={issue.record_id}" if issue.record_id else ""
        print(f"  line {issue.line_number}{record_id}:")
        for error in issue.errors:
            print(f"    - {error}")
    if len(summary.issues) > shown:
        print(f"  ... {len(summary.issues) - shown} more invalid record(s) omitted")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=str, help="Level 3 conversational JSONL path")
    parser.add_argument(
        "--skip-compiler",
        action="store_true",
        help="Skip api.notation.compile_expression checks when the compiler is unavailable.",
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        default=20,
        help="Maximum invalid records to print (default: 20).",
    )
    args = parser.parse_args(argv)

    dataset_path = Path(args.path)
    if not dataset_path.exists():
        print(f"ERROR: dataset not found: {dataset_path}", file=sys.stderr)
        return 2

    try:
        validator = Level3ConversationValidator(skip_compiler=args.skip_compiler)
    except CompilerUnavailableError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    summary = validator.validate_jsonl(dataset_path)
    _print_summary(summary, max_errors=max(args.max_errors, 0))
    return 0 if summary.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
