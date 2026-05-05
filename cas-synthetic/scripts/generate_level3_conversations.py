#!/usr/bin/env python3
"""Generate deterministic Level 3 conversational CAS records from Level 2 JSONL.

Usage:
    python cas-synthetic/scripts/generate_level3_conversations.py \
        --input cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl \
        --output cas-synthetic/data/level3_conversations.jsonl \
        --max-source-records 1000 \
        --variants-per-source 3 \
        --seed 42
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

# Make package importable when run from repo root by script path.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_CAS_SYNTHETIC = _REPO_ROOT / "cas-synthetic"
if "cas_synthetic" not in sys.modules:
    import types as _types

    pkg = _types.ModuleType("cas_synthetic")
    pkg.__file__ = str(_CAS_SYNTHETIC / "__init__.py")
    pkg.__path__ = [str(_CAS_SYNTHETIC)]
    sys.modules["cas_synthetic"] = pkg

from cas_synthetic.generator.conversational import Level3ConversationalGenerator


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Level 3 conversational CAS JSONL from Level 2 JSONL"
    )
    parser.add_argument("input_path", nargs="?", help="Level 2 input JSONL path")
    parser.add_argument("output_path", nargs="?", help="Level 3 output JSONL path")
    parser.add_argument("--input", dest="input_flag", help="Level 2 input JSONL path")
    parser.add_argument("--output", dest="output_flag", help="Level 3 output JSONL path")
    parser.add_argument(
        "--max-source-records",
        type=int,
        default=None,
        help="Maximum Level 2 source records to read",
    )
    parser.add_argument(
        "--start-source-record",
        type=int,
        default=0,
        help="Zero-based Level 2 source-record offset for deterministic held-out splits",
    )
    parser.add_argument(
        "--max-output-records",
        type=int,
        default=None,
        help="Maximum Level 3 output records to write after variant expansion",
    )
    parser.add_argument(
        "--variants-per-source",
        type=int,
        default=3,
        help="Conversational variants per Level 2 record; must be 1-5",
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument(
        "--style-id",
        action="append",
        default=None,
        help=(
            "Restrict generation to a Level 3 style id. May be passed more "
            "than once; useful for recoverable_translation-only datasets."
        ),
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1000,
        help="Print progress after this many output records; 0 disables progress",
    )
    parser.add_argument(
        "--include-invalid-sources",
        action="store_true",
        help=(
            "Wrap deliberate invalid Level 2 examples too. Default skips them "
            "because Level 3 positive conversations require compiler-valid CAS."
        ),
    )
    args = parser.parse_args()

    input_arg = args.input_flag or args.input_path
    output_arg = args.output_flag or args.output_path
    if not input_arg:
        parser.error("input path required via --input or positional input_path")
    if not output_arg:
        parser.error("output path required via --output or positional output_path")
    input_path = Path(input_arg)
    output_path = Path(output_arg)
    if not input_path.exists():
        print(f"ERROR: input dataset not found: {input_path}", file=sys.stderr)
        return 2

    generator = Level3ConversationalGenerator(
        seed=args.seed,
        variants_per_source=args.variants_per_source,
        style_ids=args.style_id,
    )

    t0 = time.monotonic()
    report = generator.generate_to_jsonl(
        input_path,
        output_path,
        max_source_records=args.max_source_records,
        start_source_record=args.start_source_record,
        max_output_records=args.max_output_records,
        variants_per_source=args.variants_per_source,
        progress_every=args.progress_every,
        include_invalid_sources=args.include_invalid_sources,
    )
    report["elapsed_seconds"] = round(time.monotonic() - t0, 2)

    print("\n=== Level 3 conversational generation complete ===")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
