#!/usr/bin/env python3
"""Validate an existing JSONL dataset against schema + Rust + composite."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import types as _types
if "cas_synthetic" not in sys.modules:
    pkg = _types.ModuleType("cas_synthetic")
    pkg.__file__ = str(_REPO_ROOT / "cas-synthetic" / "__init__.py")
    pkg.__path__ = [str(_REPO_ROOT / "cas-synthetic")]
    sys.modules["cas_synthetic"] = pkg

from cas_synthetic.validation import (
    SchemaValidator,
    CompositeValidator,
    RustValidator,
    RustValidatorUnavailable,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a CAS synthetic JSONL dataset")
    parser.add_argument("path", type=str)
    parser.add_argument("--strict-schema", action="store_true")
    args = parser.parse_args()

    entries: list[dict] = []
    with open(args.path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    print(f"Loaded {len(entries)} examples from {args.path}")

    schema = SchemaValidator(strict=False)
    composite = CompositeValidator()
    try:
        rust = RustValidator()
    except RustValidatorUnavailable as exc:
        print(f"WARN: Rust validator unavailable ({exc}); skipping Rule 4 checks.")
        rust = None

    schema_failures = 0
    composite_failures = 0
    bucket_counts: Counter[str] = Counter()
    violation_counts: Counter[str] = Counter()

    rust_results = (
        rust.evaluate_rule_four(entries)
        if rust is not None
        else [{"applicable": False, "is_valid": True, "distance": 0.0, "rust_kind": "n/a"}] * len(entries)
    )

    rule_four_violations_correctly_labeled = 0
    rule_four_total_applicable = 0

    for ex, rf in zip(entries, rust_results):
        errs = schema.validate(ex)
        if errs:
            schema_failures += 1
        report = composite.validate(ex, rust_rule_four=rf)
        if not report.ok:
            composite_failures += 1
        bucket = ex.get("_meta", {}).get("bucket", "unknown")
        bucket_counts[bucket] += 1
        vtype = ex.get("_meta", {}).get("violation_type")
        if vtype:
            violation_counts[vtype] += 1
        if rf["applicable"]:
            rule_four_total_applicable += 1
            meta_valid = ex.get("_meta", {}).get("is_valid", True)
            if rf["is_valid"] == meta_valid:
                rule_four_violations_correctly_labeled += 1

    print("\n=== Validation Report ===")
    print(f"Schema OK:    {len(entries) - schema_failures} / {len(entries)}")
    print(f"Composite OK: {len(entries) - composite_failures} / {len(entries)}")
    print(f"Bucket counts: {dict(bucket_counts)}")
    print(f"Violation counts: {dict(violation_counts)}")
    print(
        f"Rule 4 applicable: {rule_four_total_applicable}  "
        f"correctly-labeled agreement: {rule_four_violations_correctly_labeled}/{rule_four_total_applicable}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
