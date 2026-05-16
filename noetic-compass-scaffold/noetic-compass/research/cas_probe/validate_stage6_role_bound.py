"""Validate Stage 6 role-bound noetic counterfactual fixtures.

The validator is intentionally stricter than the pilot needs. It is the
contract for scaling the pilot into the full v3 fixture.

Run from repo root:

    python noetic-compass-scaffold/noetic-compass/research/cas_probe/validate_stage6_role_bound.py \
      --input stage6_role_bound_pilot_20260516.jsonl \
      --out-report stage6_role_bound_pilot_validation_20260516.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_NOETIC_NAMES = {
    0: "Idea",
    1: "Mind",
    2: "Positive",
    3: "Negative",
    4: "Vibration",
    5: "Female",
    6: "Male",
    7: "Rhythm",
    8: "Above/Cause",
    9: "Below/Effect",
}

_REQUIRED_FIELDS = {
    "sample_id",
    "dataset_version",
    "split",
    "contrast_bundle_id",
    "lexical_pack_id",
    "template_id",
    "counterfactual_pair_id",
    "paraphrase_family",
    "surface_style",
    "english",
    "base_sentence",
    "noetic_label",
    "noetic_name",
    "canonical_noetic",
    "canonical_label",
    "cas_expression",
    "focus_span",
    "contrast_partner_label",
    "hard_contrast_labels",
    "semantic_role",
    "mapping_note",
    "anti_leak_flags",
    "source_strategy",
    "review_status",
    "confidence",
}

_FORBIDDEN_INPUT_PATTERNS = {
    "cas_notation": re.compile(r"(\^[0-9PCEO]|\bCO-[0-9]\b|[ΩΦΘ])"),
    "cas_word": re.compile(r"\b(CAS|noetic|operator|canonical_noetic|label)\b", re.IGNORECASE),
    "sexed_label_word": re.compile(r"\b(male|female)\b", re.IGNORECASE),
    "above_below_label_word": re.compile(r"\b(above|below)\b", re.IGNORECASE),
    "positive_negative_label_word": re.compile(r"\b(positive|negative)\b", re.IGNORECASE),
    "vibration_rhythm_label_word": re.compile(r"\b(vibration|rhythm)\b", re.IGNORECASE),
}

_LABELISH_TOKENS = {
    "idea",
    "mind",
    "cause",
    "effect",
    "trigger",
    "source",
    "result",
    "cue",
    "resonate",
    "impression",
    "repeat",
    "repeated",
    "loop",
    "cadence",
    "shaped",
    "built",
    "parts",
    "toward",
    "away",
}


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
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            row["_lineno"] = lineno
            rows.append(row)
    return rows


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def _char_ngrams(text: str, n: int = 5) -> set[str]:
    norm = _normalize_text(text)
    if len(norm) < n:
        return {norm} if norm else set()
    return {norm[i : i + n] for i in range(len(norm) - n + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _validate_schema(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    sample_ids: set[str] = set()
    for row in rows:
        sid = str(row.get("sample_id", ""))
        missing = sorted(_REQUIRED_FIELDS - set(row))
        if missing:
            errors.append({"kind": "missing_fields", "sample_id": sid, "missing": missing})
        if not sid:
            errors.append({"kind": "empty_sample_id", "lineno": row.get("_lineno")})
        elif sid in sample_ids:
            errors.append({"kind": "duplicate_sample_id", "sample_id": sid})
        sample_ids.add(sid)

        label = row.get("noetic_label")
        if label not in _NOETIC_NAMES:
            errors.append({"kind": "invalid_noetic_label", "sample_id": sid, "value": label})
            continue
        if row.get("noetic_name") != _NOETIC_NAMES[label]:
            errors.append(
                {
                    "kind": "noetic_name_mismatch",
                    "sample_id": sid,
                    "expected": _NOETIC_NAMES[label],
                    "actual": row.get("noetic_name"),
                }
            )
        if row.get("canonical_noetic") != label:
            errors.append({"kind": "canonical_noetic_mismatch", "sample_id": sid})
        if row.get("cas_expression") != f"^{label}":
            errors.append({"kind": "cas_expression_mismatch", "sample_id": sid})

        english = row.get("english")
        if not isinstance(english, str) or not english.strip():
            errors.append({"kind": "invalid_english", "sample_id": sid})
        focus = row.get("focus_span")
        if focus not in {"A", "B"}:
            errors.append({"kind": "invalid_focus_span", "sample_id": sid, "focus_span": focus})
        flags = row.get("anti_leak_flags")
        if not isinstance(flags, dict):
            errors.append({"kind": "invalid_anti_leak_flags", "sample_id": sid})
    return errors


def _validate_forbidden_input(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for row in rows:
        sid = str(row["sample_id"])
        english = str(row["english"])
        for kind, pattern in _FORBIDDEN_INPUT_PATTERNS.items():
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
        present_labelish = sorted(set(_tokens(english)) & _LABELISH_TOKENS)
        if present_labelish:
            warnings.append(
                {
                    "kind": "labelish_tokens_present",
                    "sample_id": sid,
                    "tokens": present_labelish,
                    "note": "warning only; token concentration audit decides whether these are counterbalanced",
                }
            )
    return errors, warnings


def _validate_counterfactual_pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_pair[str(row["counterfactual_pair_id"])].append(row)

    for pair_id, pair_rows in sorted(by_pair.items()):
        if len(pair_rows) != 2:
            errors.append({"kind": "counterfactual_pair_size", "pair_id": pair_id, "size": len(pair_rows)})
            continue
        a, b = pair_rows
        if a["base_sentence"] != b["base_sentence"]:
            errors.append({"kind": "counterfactual_base_sentence_mismatch", "pair_id": pair_id})
        if a["english"] == b["english"]:
            errors.append({"kind": "counterfactual_english_identical", "pair_id": pair_id})
        if {a["focus_span"], b["focus_span"]} != {"A", "B"}:
            errors.append(
                {
                    "kind": "counterfactual_focus_not_balanced",
                    "pair_id": pair_id,
                    "focuses": sorted([a["focus_span"], b["focus_span"]]),
                }
            )
        labels = sorted([int(a["noetic_label"]), int(b["noetic_label"])])
        hard_a = sorted(int(x) for x in a["hard_contrast_labels"])
        hard_b = sorted(int(x) for x in b["hard_contrast_labels"])
        if hard_a != labels or hard_b != labels:
            errors.append(
                {
                    "kind": "hard_contrast_labels_mismatch",
                    "pair_id": pair_id,
                    "labels": labels,
                    "hard_a": hard_a,
                    "hard_b": hard_b,
                }
            )
        if a["contrast_bundle_id"] != b["contrast_bundle_id"]:
            errors.append({"kind": "pair_crosses_bundle", "pair_id": pair_id})
    return errors


def _validate_split_isolation(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for key in ("contrast_bundle_id", "lexical_pack_id", "template_id"):
        split_by_key: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            split_by_key[str(row[key])].add(str(row["split"]))
        leaks = {k: sorted(v) for k, v in split_by_key.items() if len(v) > 1}
        if leaks:
            errors.append({"kind": "split_isolation_violation", "field": key, "leaks": leaks})
    return errors


def _validate_duplicates(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    norm_seen: dict[str, str] = {}
    ngrams_by_id: dict[str, set[str]] = {}
    text_by_id: dict[str, str] = {}
    split_by_id: dict[str, str] = {}
    for row in rows:
        sid = str(row["sample_id"])
        norm = _normalize_text(str(row["english"]))
        if norm in norm_seen:
            errors.append(
                {
                    "kind": "normalized_exact_duplicate",
                    "sample_id": sid,
                    "other_sample_id": norm_seen[norm],
                }
            )
        norm_seen[norm] = sid
        ngrams_by_id[sid] = _char_ngrams(str(row["english"]))
        text_by_id[sid] = str(row["english"])
        split_by_id[sid] = str(row["split"])

    ids = list(ngrams_by_id)
    for i, sid_a in enumerate(ids):
        for sid_b in ids[i + 1 :]:
            if split_by_id[sid_a] == split_by_id[sid_b]:
                continue
            jac = _jaccard(ngrams_by_id[sid_a], ngrams_by_id[sid_b])
            if jac >= 0.85:
                errors.append(
                    {
                        "kind": "near_duplicate_cross_split",
                        "sample_id": sid_a,
                        "other_sample_id": sid_b,
                        "char5_jaccard": round(jac, 4),
                    }
                )
            elif jac >= 0.75:
                warnings.append(
                    {
                        "kind": "near_duplicate_cross_split_review",
                        "sample_id": sid_a,
                        "other_sample_id": sid_b,
                        "char5_jaccard": round(jac, 4),
                    }
                )
    return errors, warnings


def _token_concentration(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    token_label_counts: dict[str, Counter[int]] = defaultdict(Counter)
    token_counts: Counter[str] = Counter()
    for row in rows:
        label = int(row["noetic_label"])
        for tok in set(_tokens(str(row["english"]))):
            token_counts[tok] += 1
            token_label_counts[tok][label] += 1

    audit_rows: list[dict[str, Any]] = []
    for tok, count in sorted(token_counts.items()):
        if count < 10:
            continue
        label_counts = token_label_counts[tok]
        ranked = label_counts.most_common()
        top_label, top_count = ranked[0]
        second_count = ranked[1][1] if len(ranked) > 1 else 0
        concentration = top_count / count
        entry = {
            "token": tok,
            "count": count,
            "top_label": top_label,
            "top_label_name": _NOETIC_NAMES[top_label],
            "top_label_count": top_count,
            "second_label_count": second_count,
            "top_tied": second_count == top_count,
            "concentration": round(concentration, 4),
            "label_counts": {str(k): v for k, v in sorted(label_counts.items())},
        }
        audit_rows.append(entry)
        if (
            concentration > 0.40
            and not entry["top_tied"]
            and tok not in {"a", "b", "focus", "the", "is", "and", "by", "from", "to", "it"}
        ):
            errors.append({"kind": "token_label_concentration_gt_40pct", **entry})
    if audit_rows:
        warnings.append({"kind": "token_concentration_audit", "tokens": audit_rows})
    return errors, warnings


def _metadata_baseline_proxy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for key in ("split", "contrast_bundle_id", "lexical_pack_id", "template_id", "focus_span"):
        by_value: dict[str, Counter[int]] = defaultdict(Counter)
        for row in rows:
            by_value[str(row[key])][int(row["noetic_label"])] += 1
        bad_values = []
        for value, counts in by_value.items():
            total = sum(counts.values())
            top_label, top_count = counts.most_common(1)[0]
            if total >= 4 and top_count / total > 0.40:
                bad_values.append(
                    {
                        "value": value,
                        "total": total,
                        "top_label": top_label,
                        "top_label_name": _NOETIC_NAMES[top_label],
                        "concentration": round(top_count / total, 4),
                    }
                )
        if bad_values:
            warnings.append(
                {
                    "kind": "metadata_concentration_review",
                    "field": key,
                    "values": bad_values,
                    "note": "pilot warning; full v3 should keep metadata-only baseline near chance",
                }
            )
    return warnings


def _distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    class_counts = Counter(int(row["noetic_label"]) for row in rows)
    split_counts = Counter(str(row["split"]) for row in rows)
    pair_counts = Counter(tuple(int(x) for x in sorted(row["hard_contrast_labels"])) for row in rows)
    focus_by_label: dict[int, Counter[str]] = defaultdict(Counter)
    for row in rows:
        focus_by_label[int(row["noetic_label"])][str(row["focus_span"])] += 1
    return {
        "n_records": len(rows),
        "n_bundles": len({row["contrast_bundle_id"] for row in rows}),
        "n_counterfactual_pairs": len({row["counterfactual_pair_id"] for row in rows}),
        "class_distribution": {str(k): class_counts[k] for k in sorted(class_counts)},
        "split_distribution": {k: split_counts[k] for k in sorted(split_counts)},
        "pair_distribution": {f"{a}_{b}": count for (a, b), count in sorted(pair_counts.items())},
        "focus_by_label": {
            str(label): {k: counts[k] for k in sorted(counts)}
            for label, counts in sorted(focus_by_label.items())
        },
    }


def validate(path: Path) -> dict[str, Any]:
    rows = _load_jsonl(path)
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    errors.extend(_validate_schema(rows))
    if not errors:
        forbidden_errors, forbidden_warnings = _validate_forbidden_input(rows)
        errors.extend(forbidden_errors)
        warnings.extend(forbidden_warnings)
        errors.extend(_validate_counterfactual_pairs(rows))
        errors.extend(_validate_split_isolation(rows))
        duplicate_errors, duplicate_warnings = _validate_duplicates(rows)
        errors.extend(duplicate_errors)
        warnings.extend(duplicate_warnings)
        concentration_errors, concentration_warnings = _token_concentration(rows)
        errors.extend(concentration_errors)
        warnings.extend(concentration_warnings)
        warnings.extend(_metadata_baseline_proxy(rows))

    return {
        "schema_version": "stage6_role_bound_validation.v1",
        "input_file": path.name,
        "input_sha256": _sha256_of_file(path),
        "status": "pass" if not errors else "fail",
        "distribution": _distribution(rows),
        "n_errors": len(errors),
        "errors": errors,
        "n_warnings": len(warnings),
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSONL fixture to validate")
    parser.add_argument("--out-report", default="", help="Optional JSON report path")
    args = parser.parse_args(argv)

    input_path = _resolve(args.input)
    report = validate(input_path)
    if args.out_report:
        out_report = _resolve(args.out_report)
        out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
