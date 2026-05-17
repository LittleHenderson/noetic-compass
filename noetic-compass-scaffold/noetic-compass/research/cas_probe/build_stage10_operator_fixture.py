"""Build Stage 10 five-operator role-bound fixture.

Stage 10 tests the five CAS generative operations after the Stage 9
40-Element pass. Model-facing English avoids literal operator symbols and
framework names. Metadata keeps the operator labels/symbols for audit.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from build_stage6_role_bound_full import _bundles


_HERE = Path(__file__).resolve().parent
_DATE = "20260517"

_OPERATORS: dict[str, dict[str, str]] = {
    "multiply_integrate": {
        "symbol": "x",
        "plain": "parts become one working whole",
        "gloss": "separate pieces are bound into one functioning whole while their roles remain inside it",
    },
    "divide_ratio": {
        "symbol": "/",
        "plain": "one thing is measured against another",
        "gloss": "one share is compared against another so the relation between them becomes the point",
    },
    "compose_sequence": {
        "symbol": "o",
        "plain": "one result becomes the next starting point",
        "gloss": "the outcome of one pass becomes the starting condition for the next pass",
    },
    "add_copresence": {
        "symbol": "+",
        "plain": "distinct things stay present together",
        "gloss": "two distinct items remain side by side in the same scene without becoming one thing",
    },
    "subtract_remove": {
        "symbol": "-",
        "plain": "one thing is taken out",
        "gloss": "one item is taken out so the remaining situation changes around its absence",
    },
}
_OPERATOR_LABELS = tuple(_OPERATORS)
_OPERATOR_TO_INDEX = {label: i for i, label in enumerate(_OPERATOR_LABELS)}

_CORE_FAMILIES = (
    "definition_compact",
    "applied_human",
    "system_process",
    "role_inverse_plain",
)
_TEST_ONLY_FAMILIES = (
    "compressed_minimal",
    "long_embedded_clause",
    "counter_alias_hard_negative",
)


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _selected_bundles(mode: str) -> list[dict[str, str]]:
    bundles = _bundles()
    if mode == "full":
        return bundles
    if mode != "pilot":
        raise ValueError(f"unsupported mode: {mode}")
    train = [b for b in bundles if b["split"] == "train"][:4]
    val = [b for b in bundles if b["split"] == "val"][:2]
    test = [b for b in bundles if b["split"] == "test"][:4]
    return train + val + test


def _pair_schedule() -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for left, right in itertools.combinations(_OPERATOR_LABELS, 2):
        pairs.append(
            {
                "pair_kind": f"operator_pair_{left}_vs_{right}",
                "left": left,
                "right": right,
            }
        )
    return pairs


def _family_phrase(operator: str, bundle: dict[str, str], family: str) -> str:
    gloss = _OPERATORS[operator]["gloss"]
    if family == "definition_compact":
        return f"the role where {gloss}"
    if family == "applied_human":
        return f"what the {bundle['processor']} notices when {gloss} in the case"
    if family == "system_process":
        return f"the process signal showing how {gloss} inside {bundle['construct']}"
    if family == "role_inverse_plain":
        return f"the selected aspect of {bundle['prior']} where {gloss}"
    if family == "compressed_minimal":
        return f"{gloss}"
    if family == "long_embedded_clause":
        return (
            f"the role that remains active while {bundle['carrier']} changes, because "
            f"{gloss} before the record settles"
        )
    if family == "counter_alias_hard_negative":
        return f"not the neighboring role, but the aspect where {gloss}"
    raise ValueError(f"unknown family {family!r}")


def _sentence(left: str, right: str, family: str) -> str:
    if family == "long_embedded_clause":
        return f"A is {left}; while the record unfolds, B is {right}, and the focus chooses only one role."
    return f"A is {left}; B is {right}."


def _anti_leak_flags(text: str) -> dict[str, bool]:
    literal_tokens = ["+", "-", "/"]
    forbidden_pattern = re.compile(
        r"\b(?:cas|tks|operator|multiply|multiplication|divide|division|compose|composition|addition|subtraction)\b",
        re.IGNORECASE,
    )
    return {
        "contains_literal_operator_symbol": any(token in text for token in literal_tokens),
        "contains_framework_or_label_word": bool(forbidden_pattern.search(text)),
        "counterbalanced_keyword_pack": True,
    }


def build_rows(mode: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bundle in _selected_bundles(mode):
        families = list(_CORE_FAMILIES)
        if bundle["split"] == "test":
            families.extend(_TEST_ONLY_FAMILIES)
        for pair in _pair_schedule():
            left = str(pair["left"])
            right = str(pair["right"])
            for family in families:
                left_phrase = _family_phrase(left, bundle, family)
                right_phrase = _family_phrase(right, bundle, family)
                base_sentence = _sentence(left_phrase, right_phrase, family)
                for focus_span, operator in (("A", left), ("B", right)):
                    english = f"{base_sentence} Focus: {focus_span}."
                    partner = right if focus_span == "A" else left
                    sample_id = (
                        f"s10_{mode}_{bundle['id']}_{pair['pair_kind']}_"
                        f"{family}_{operator}"
                    )
                    rows.append(
                        {
                            "sample_id": sample_id,
                            "dataset_version": f"stage10_operators_{mode}_v0",
                            "split": bundle["split"],
                            "contrast_bundle_id": bundle["id"],
                            "lexical_pack_id": bundle["lexical_pack_id"],
                            "template_id": f"{bundle['id']}_{pair['pair_kind']}_{family}_v01",
                            "counterfactual_pair_id": f"{bundle['id']}_{pair['pair_kind']}_{family}",
                            "pair_kind": pair["pair_kind"],
                            "paraphrase_family": family,
                            "surface_style": "role_bound_five_operator_plain",
                            "english": english,
                            "base_sentence": base_sentence,
                            "focus_span": focus_span,
                            "operator_label": operator,
                            "operator_index": _OPERATOR_TO_INDEX[operator],
                            "operator_symbol": _OPERATORS[operator]["symbol"],
                            "operator_plain": _OPERATORS[operator]["plain"],
                            "operator_gloss": _OPERATORS[operator]["gloss"],
                            "hard_contrast_operators": [left, right],
                            "hard_contrast_labels": [_OPERATOR_TO_INDEX[left], _OPERATOR_TO_INDEX[right]],
                            "contrast_partner_operator": partner,
                            "anti_leak_flags": _anti_leak_flags(english),
                            "source_strategy": "codex_authored_five_operator_role_bound_counterfactual_template",
                            "review_status": "locked_fixture_pending_blind_review",
                            "confidence": "fixture_locked_unreviewed",
                        }
                    )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["pilot", "full"], default="full")
    args = parser.parse_args(argv)

    rows = build_rows(str(args.mode))
    out_jsonl = _HERE / f"stage10_operators_{args.mode}_{_DATE}.jsonl"
    out_manifest = _HERE / f"stage10_operators_{args.mode}_manifest_{_DATE}.json"
    with out_jsonl.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    leak_counts = Counter()
    for row in rows:
        for key, value in row["anti_leak_flags"].items():
            if bool(value) and key != "counterbalanced_keyword_pack":
                leak_counts[key] += 1

    split_counts = Counter(str(row["split"]) for row in rows)
    label_counts = Counter(str(row["operator_label"]) for row in rows)
    family_counts = Counter(str(row["paraphrase_family"]) for row in rows)
    manifest = {
        "schema_version": "stage10_operator_fixture_manifest.v1",
        "mode": args.mode,
        "date": _DATE,
        "out_jsonl": out_jsonl.name,
        "out_jsonl_sha256": _sha256_of_file(out_jsonl),
        "n_rows": len(rows),
        "n_classes": len(label_counts),
        "operator_labels": list(_OPERATOR_LABELS),
        "operator_metadata": _OPERATORS,
        "split_counts": dict(sorted(split_counts.items())),
        "operator_counts": dict(sorted(label_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "anti_leak_flag_counts": dict(sorted(leak_counts.items())),
        "position_definition": "five CAS generative operations: integration, ratio, sequence, co-presence, removal",
        "source": "user-requested Stage 10 CAS operator ladder after Stage 9 original-TKS 40 Elements pass",
        "lessons_reused": [
            "role-bound same-sentence counterfactuals",
            "balanced labels",
            "explicit Focus marker",
            "literal symbol and framework leakage avoided in model-facing English",
            "text and metadata baselines required before any harness claim",
        ],
    }
    out_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if leak_counts:
        raise SystemExit(f"model-facing leakage detected: {dict(leak_counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
