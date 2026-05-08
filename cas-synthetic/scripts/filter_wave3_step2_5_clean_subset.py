"""Filter Wave 2.5 accepted records through the current validator stack.

Use this after a paid calibration run. The original accepted JSONL records
show what passed the validator stack at generation time; this script replays
the current validators against those records and writes:

* a clean JSONL with records that still pass
* a reject JSONL with records that now fail
* a summary manifest with per-category rates and failure reasons
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
V2_SCRIPT = REPO_ROOT / "cas-synthetic" / "scripts" / "generate_path_d_wave3_v2.py"


KNOWN_CATEGORIES = (
    "cross_register_omega",
    "binary_composition",
    "fractal_sequence",
    "meta_logic_relation",
    "state_literal",
    "diagram_export",
    "let_binding",
    "rpm_chain",
    "inversion",
    "recipe",
)


def _load_v2_module():
    name = "cas_synthetic_wave3_v2_filter"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, V2_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _infer_category(record: dict[str, Any]) -> str:
    cat = record.get("grammar_category")
    if cat:
        return str(cat)
    seed_id = str(record.get("seed_id", ""))
    if seed_id.startswith("seed_"):
        rest = seed_id[5:]
        for known in KNOWN_CATEGORIES:
            if rest.startswith(known + "_") or rest == known:
                return known
    return "unknown"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--rejects", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    v2 = _load_v2_module()
    checked_at = _now()

    total_by_cat: Counter[str] = Counter()
    clean_by_cat: Counter[str] = Counter()
    reject_by_cat: Counter[str] = Counter()
    failure_reasons: Counter[str] = Counter()
    validator_failures: Counter[str] = Counter()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.rejects.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)

    n_total = 0
    n_clean = 0
    n_reject = 0

    with (
        args.input.open("r", encoding="utf-8") as inp,
        args.out.open("w", encoding="utf-8") as clean_fp,
        args.rejects.open("w", encoding="utf-8") as reject_fp,
    ):
        for line in inp:
            line = line.strip()
            if not line:
                continue
            n_total += 1
            record = json.loads(line)
            cat = _infer_category(record)
            source_cas = record.get("source_cas") or record.get("expression")
            english = (
                record.get("english_description")
                or record.get("english_output")
                or record.get("raw_response")
                or ""
            )
            total_by_cat[cat] += 1
            results = v2.run_validators_for_cas_to_english(
                seed={"expression": source_cas, "grammar_category": cat},
                english_output=english,
            )
            failed = [r for r in results if not r.passed]
            if failed:
                n_reject += 1
                reject_by_cat[cat] += 1
                failed_reasons = {r.name: (r.reason or "unspecified") for r in failed}
                for name, reason in failed_reasons.items():
                    validator_failures[name] += 1
                    failure_reasons[reason] += 1
                out_record = dict(record)
                out_record["post_filter_checked_at"] = checked_at
                out_record["post_filter_validators_run"] = [r.name for r in results]
                out_record["post_filter_failed_reasons"] = failed_reasons
                reject_fp.write(json.dumps(out_record, ensure_ascii=False) + "\n")
                continue
            n_clean += 1
            clean_by_cat[cat] += 1
            out_record = dict(record)
            out_record["post_filter_checked_at"] = checked_at
            out_record["post_filter_validators_run"] = [r.name for r in results]
            out_record["post_filter_validators_passed"] = [
                r.name for r in results if r.passed
            ]
            clean_fp.write(json.dumps(out_record, ensure_ascii=False) + "\n")

    per_category = {}
    for cat in sorted(total_by_cat):
        total = total_by_cat[cat]
        clean = clean_by_cat[cat]
        rejected = reject_by_cat[cat]
        per_category[cat] = {
            "clean": clean,
            "rejected": rejected,
            "total": total,
            "clean_rate": round(clean / total, 4) if total else 0.0,
        }

    manifest = {
        "created_at": checked_at,
        "input": str(args.input),
        "outputs": {
            "clean": str(args.out),
            "rejects": str(args.rejects),
        },
        "counts": {
            "total": n_total,
            "clean": n_clean,
            "rejected": n_reject,
            "clean_rate": round(n_clean / n_total, 4) if n_total else 0.0,
        },
        "per_category": per_category,
        "validator_failures": dict(validator_failures.most_common()),
        "top_failure_reasons": [
            {"count": count, "reason": reason}
            for reason, count in failure_reasons.most_common(25)
        ],
    }
    args.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(manifest["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
