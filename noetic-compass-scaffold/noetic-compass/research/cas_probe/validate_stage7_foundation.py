"""Validate Stage 7 original-TKS foundation fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_FOUNDATIONS = {f"F{drive}{register}" for drive in range(1, 8) for register in ("T", "A", "f", "E")}
_REQUIRED_FIELDS = {
    "sample_id",
    "dataset_version",
    "split",
    "contrast_bundle_id",
    "lexical_pack_id",
    "template_id",
    "counterfactual_pair_id",
    "pair_kind",
    "paraphrase_family",
    "surface_style",
    "english",
    "base_sentence",
    "focus_span",
    "foundation_label",
    "foundation_drive",
    "foundation_register",
    "tks_foundation_code",
    "tks_foundation_name",
    "tks_world_name",
    "foundation_expression",
    "cas_expression",
    "contrast_partner_foundation",
    "hard_contrast_foundations",
    "mapping_note",
    "anti_leak_flags",
    "source_strategy",
    "review_status",
    "confidence",
}
_FORBIDDEN_PATTERNS = {
    "cas_drive_notation": re.compile(r"\bF[1-7]\b|F_[1-7]|\|[TAfE]\b"),
    "cas_word": re.compile(r"\b(CAS|foundation|drive|register)\b", re.IGNORECASE),
    "drive_name": re.compile(
        (
            r"\b(desire to be and be with god|wisdom, insight, and knowledge|"
            r"life, vitality, and health|companionship, love, and friendship|"
            r"worldly power, influence, and control|material food and things|"
            r"lust, sex, and reproduction)\b"
        ),
        re.IGNORECASE,
    ),
    "register_name": re.compile(
        r"\b(Transcendent|Analytical|Affective|Embodied|Spiritual|Mental|Emotional|Physical)\b",
        re.IGNORECASE,
    ),
}
_TKS_WORLD_SUFFIX = {"T": "a", "A": "b", "f": "c", "E": "d"}


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            row["_lineno"] = lineno
            rows.append(row)
    return rows


def validate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        sid = str(row.get("sample_id", ""))
        missing = sorted(_REQUIRED_FIELDS - set(row))
        if missing:
            errors.append({"kind": "missing_fields", "sample_id": sid, "missing": missing})
        if not sid:
            errors.append({"kind": "empty_sample_id", "lineno": row.get("_lineno")})
        elif sid in seen_ids:
            errors.append({"kind": "duplicate_sample_id", "sample_id": sid})
        seen_ids.add(sid)

        label = str(row.get("foundation_label", ""))
        if label not in _FOUNDATIONS:
            errors.append({"kind": "invalid_foundation_label", "sample_id": sid, "label": label})
        drive = row.get("foundation_drive")
        register = row.get("foundation_register")
        if label in _FOUNDATIONS:
            expected = f"F{drive}{register}"
            if label != expected:
                errors.append(
                    {"kind": "foundation_axis_mismatch", "sample_id": sid, "expected": expected, "actual": label}
                )
            if row.get("cas_expression") != f"F{drive}|{register}":
                errors.append({"kind": "cas_expression_mismatch", "sample_id": sid})
            if row.get("tks_foundation_code") != f"{drive}{_TKS_WORLD_SUFFIX.get(str(register), '?')}":
                errors.append({"kind": "tks_foundation_code_mismatch", "sample_id": sid})

        focus = row.get("focus_span")
        if focus not in {"A", "B"}:
            errors.append({"kind": "invalid_focus_span", "sample_id": sid, "focus_span": focus})
        english = str(row.get("english", ""))
        if f"Focus: {focus}." not in english:
            errors.append({"kind": "missing_focus_marker", "sample_id": sid})
        if "A is " not in english or "B is " not in english:
            errors.append({"kind": "missing_role_markers", "sample_id": sid})

        for kind, pattern in _FORBIDDEN_PATTERNS.items():
            match = pattern.search(english)
            if match:
                errors.append(
                    {
                        "kind": "forbidden_input_token",
                        "sample_id": sid,
                        "pattern": kind,
                        "match": match.group(0),
                    }
                )

        flags = row.get("anti_leak_flags")
        if not isinstance(flags, dict):
            errors.append({"kind": "invalid_anti_leak_flags", "sample_id": sid})
        else:
            for flag in ("contains_cas_notation", "contains_drive_name", "contains_register_name"):
                if flags.get(flag):
                    errors.append({"kind": "anti_leak_flag_true", "sample_id": sid, "flag": flag})

        pair_key = f"{row.get('counterfactual_pair_id')}::{row.get('paraphrase_family')}"
        by_pair[pair_key].append(row)

    for pair_key, pair_rows in by_pair.items():
        if len(pair_rows) != 2:
            errors.append({"kind": "pair_row_count_not_two", "pair_key": pair_key, "count": len(pair_rows)})
            continue
        focuses = sorted(str(row["focus_span"]) for row in pair_rows)
        if focuses != ["A", "B"]:
            errors.append({"kind": "pair_focus_mismatch", "pair_key": pair_key, "focuses": focuses})
        labels = sorted(str(row["foundation_label"]) for row in pair_rows)
        hard_sets = {tuple(sorted(row["hard_contrast_foundations"])) for row in pair_rows}
        if len(hard_sets) != 1 or tuple(labels) != next(iter(hard_sets)):
            errors.append({"kind": "hard_contrast_mismatch", "pair_key": pair_key, "labels": labels})

    foundation_counts = Counter(str(row.get("foundation_label")) for row in rows)
    if set(foundation_counts) != _FOUNDATIONS:
        errors.append(
            {
                "kind": "foundation_coverage_mismatch",
                "missing": sorted(_FOUNDATIONS - set(foundation_counts)),
                "extra": sorted(set(foundation_counts) - _FOUNDATIONS),
            }
        )
    if foundation_counts:
        values = list(foundation_counts.values())
        if min(values) != max(values):
            warnings.append(
                {
                    "kind": "foundation_counts_not_equal",
                    "min": min(values),
                    "max": max(values),
                }
            )

    return {
        "errors": errors,
        "warnings": warnings,
        "n_errors": len(errors),
        "n_warnings": len(warnings),
        "n_rows": len(rows),
        "foundation_counts": dict(sorted(foundation_counts.items())),
        "split_counts": dict(sorted(Counter(str(row.get("split")) for row in rows).items())),
        "pair_kind_counts": dict(sorted(Counter(str(row.get("pair_kind")) for row in rows).items())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out-report", required=True)
    args = parser.parse_args(argv)

    input_path = _resolve(args.input)
    out_path = _resolve(args.out_report)
    rows = _load_jsonl(input_path)
    report = validate(rows)
    report.update(
        {
            "schema_version": "stage7_foundation_validation.v1",
            "input_file": input_path.name,
            "input_sha256": _sha256_of_file(input_path),
            "position_definition": "7 original TKS foundations x 4 worlds/registers = 28 positions",
        }
    )
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("n_rows", "n_errors", "n_warnings")}, indent=2))
    print(f"report written: {out_path}")
    return 1 if report["n_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
