#!/usr/bin/env python3
"""Driver: generate balanced meta_logic Level 3 conversational records.

Wraps :mod:`cas_synthetic.generator.meta_logic_balanced` and the existing
:class:`Level3ConversationalGenerator` so the output JSONL shape matches the
records in ``cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl``.

Usage:
    python cas-synthetic/scripts/generate_balanced_meta_logic.py \\
        --output cas-synthetic/data/level2_scaffold/level3_meta_logic_balanced_2026_05_04.jsonl \\
        --records-per-constructor 60 \\
        --seed 42

Pure stdlib; no external API calls.
"""

from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path
from typing import Any, Iterable, Iterator

# ---------------------------------------------------------------------------
# Make the cas_synthetic package importable when run from repo root.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_CAS_SYNTHETIC = _REPO_ROOT / "cas-synthetic"
if "cas_synthetic" not in sys.modules:
    pkg = types.ModuleType("cas_synthetic")
    pkg.__file__ = str(_CAS_SYNTHETIC / "__init__.py")
    pkg.__path__ = [str(_CAS_SYNTHETIC)]
    sys.modules["cas_synthetic"] = pkg

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


from cas_synthetic.generator.conversational import Level3ConversationalGenerator
from cas_synthetic.generator.meta_logic_balanced import (
    CONSTRUCTOR_NAMES,
    Level2Source,
    MetaLogicBalancedGenerator,
)


def iter_balanced_records(
    *,
    records_per_constructor: int,
    seed: int,
    style_id: str = "recoverable_translation",
    variants_per_source: int = 1,
    only_constructor: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield Level 3 conversational records, balanced across constructors.

    Each Level 2 source produced by :class:`MetaLogicBalancedGenerator` is
    handed to :class:`Level3ConversationalGenerator.iter_source_record`. By
    default only the ``recoverable_translation`` style is used so the output
    shape matches existing meta_logic records in the held-out eval slice.
    """

    base_gen = MetaLogicBalancedGenerator(seed=seed)
    conv_gen = Level3ConversationalGenerator(
        seed=seed,
        variants_per_source=variants_per_source,
        style_ids=[style_id],
    )

    constructors = (
        [only_constructor] if only_constructor is not None else list(CONSTRUCTOR_NAMES)
    )
    record_index = 0
    for constructor in constructors:
        for src in base_gen.iter_constructor(constructor, records_per_constructor):
            src_dict = src.to_dict()
            for ex in conv_gen.iter_source_record(
                src_dict,
                source_index=record_index,
                source_line=record_index + 1,
                source_path="meta_logic_balanced_inline",
                variants_per_source=variants_per_source,
            ):
                out = ex.to_dict()
                # Tack on a small balanced-cohort marker so downstream tools
                # can identify the provenance without depending on filename.
                out.setdefault("provenance", {})
                out["provenance"]["balanced_cohort"] = True
                out["provenance"]["balanced_constructor"] = constructor
                out["provenance"]["balanced_arity"] = src.arity
                out["provenance"]["balanced_composition_kind"] = src.composition_kind
                yield out
            record_index += 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate balanced meta_logic Level 3 conversational records.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSONL path (will be created; parent dirs created as needed)",
    )
    parser.add_argument(
        "--records-per-constructor",
        type=int,
        default=60,
        help="Number of records per constructor (default: 60). Total = 8 * value.",
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42).")
    parser.add_argument(
        "--variants-per-source",
        type=int,
        default=1,
        help="Conversational variants per generated source (default: 1).",
    )
    parser.add_argument(
        "--style-id",
        default="recoverable_translation",
        help="Level 3 conversational style id (default: recoverable_translation).",
    )
    parser.add_argument(
        "--only-constructor",
        choices=CONSTRUCTOR_NAMES,
        default=None,
        help="If set, generate only this single constructor type.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="If set, write at most this many records to the output (smoke runs).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and validate without writing the output file.",
    )
    args = parser.parse_args(argv)

    if args.records_per_constructor <= 0:
        parser.error("--records-per-constructor must be positive")
    if args.variants_per_source < 1 or args.variants_per_source > 5:
        parser.error("--variants-per-source must be in [1, 5]")

    out_path = Path(args.output)
    if not args.dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    counts_by_constructor: dict[str, int] = {name: 0 for name in CONSTRUCTOR_NAMES}
    arity_by_constructor: dict[str, list[int]] = {name: [] for name in CONSTRUCTOR_NAMES}

    out_handle = None if args.dry_run else open(out_path, "w", encoding="utf-8")
    try:
        for record in iter_balanced_records(
            records_per_constructor=args.records_per_constructor,
            seed=args.seed,
            style_id=args.style_id,
            variants_per_source=args.variants_per_source,
            only_constructor=args.only_constructor,
        ):
            constructor = record.get("provenance", {}).get("balanced_constructor", "unknown")
            arity = record.get("provenance", {}).get("balanced_arity", 0)
            counts_by_constructor[constructor] = counts_by_constructor.get(constructor, 0) + 1
            arity_by_constructor.setdefault(constructor, []).append(arity)
            if out_handle is not None:
                out_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
            if args.limit is not None and written >= args.limit:
                break
    finally:
        if out_handle is not None:
            out_handle.close()

    print(f"meta_logic_balanced: wrote {written} records to {out_path}")
    print("Per-constructor counts:")
    for name in CONSTRUCTOR_NAMES:
        arities = arity_by_constructor.get(name, [])
        if arities:
            mn, mx = min(arities), max(arities)
            mean = sum(arities) / len(arities)
            print(f"  {name:18s}: {counts_by_constructor.get(name, 0):4d} (arity min={mn}, max={mx}, mean={mean:.2f})")
        else:
            print(f"  {name:18s}: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
