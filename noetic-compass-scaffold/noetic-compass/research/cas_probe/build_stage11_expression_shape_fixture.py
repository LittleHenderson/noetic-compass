"""Build Stage 11 expression grammar-shape role-bound fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from build_stage6_role_bound_full import _bundles


_HERE = Path(__file__).resolve().parent
_DATE = "20260517"

_SHAPES: dict[str, dict[str, str]] = {
    "state_literal": {
        "plain": "one marked condition stands alone",
        "gloss": "one marked condition stands by itself without another relation attached",
    },
    "binary_composition": {
        "plain": "two marked conditions are linked into one relation",
        "gloss": "two marked conditions are linked together so the relation between them is the point",
    },
    "let_binding": {
        "plain": "a temporary name is introduced and later used",
        "gloss": "a temporary name is introduced first and then reused later inside the same record",
    },
    "recipe": {
        "plain": "a desired outcome is specified by weighted contributors",
        "gloss": "a desired outcome is built from required contributors with different amounts of influence",
    },
    "rpm_chain": {
        "plain": "a starting point advances through staged checkpoints",
        "gloss": "a starting point advances through staged checkpoints before a final pass is reached",
    },
    "fractal_sequence": {
        "plain": "a repeated pattern of moves is applied in order",
        "gloss": "a repeating pattern of moves is applied in order so each pass follows the previous one",
    },
    "cross_register_omega": {
        "plain": "one named outcome is viewed across different modes",
        "gloss": "one named outcome is carried across different modes of presentation without losing its identity",
    },
    "meta_logic_relation": {
        "plain": "a rule describes how another rule relates or follows",
        "gloss": "one rule speaks about how another rule relates, follows, or holds together",
    },
    "inversion": {
        "plain": "the usual direction is turned around",
        "gloss": "the usual direction is turned around so source and result exchange their roles",
    },
    "diagram_export": {
        "plain": "a named cluster is packaged for outside viewing",
        "gloss": "a named cluster is packaged as a reusable bundle for outside viewing",
    },
}
_SHAPE_LABELS = tuple(_SHAPES)
_SHAPE_TO_INDEX = {label: i for i, label in enumerate(_SHAPE_LABELS)}

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

_SAFE_REPLACEMENTS = (
    ("motion recipe", "motion plan"),
    ("recipe", "plan"),
    ("formula", "plan"),
    ("equation", "record"),
    ("diagram", "view"),
    ("export", "package"),
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
    labels = list(_SHAPE_LABELS)
    pairs: list[dict[str, Any]] = []
    for i, left in enumerate(labels):
        right = labels[(i + 1) % len(labels)]
        pairs.append({"pair_kind": f"shape_cycle_next_{left}_vs_{right}", "left": left, "right": right})
    for i in range(len(labels) // 2):
        left = labels[i]
        right = labels[i + len(labels) // 2]
        pairs.append({"pair_kind": f"shape_cross_half_{left}_vs_{right}", "left": left, "right": right})
    return pairs


def _safe_text(value: str) -> str:
    out = value
    for src, dst in _SAFE_REPLACEMENTS:
        out = re.sub(re.escape(src), dst, out, flags=re.IGNORECASE)
    return out


def _family_phrase(shape: str, bundle: dict[str, str], family: str) -> str:
    gloss = _SHAPES[shape]["gloss"]
    processor = _safe_text(bundle["processor"])
    construct = _safe_text(bundle["construct"])
    prior = _safe_text(bundle["prior"])
    carrier = _safe_text(bundle["carrier"])
    if family == "definition_compact":
        return f"the role where {gloss}"
    if family == "applied_human":
        return f"what the {processor} notices when {gloss} in the case"
    if family == "system_process":
        return f"the process signal showing how {gloss} inside {construct}"
    if family == "role_inverse_plain":
        return f"the selected aspect of {prior} where {gloss}"
    if family == "compressed_minimal":
        return f"{gloss}"
    if family == "long_embedded_clause":
        return (
            f"the role that remains active while {carrier} changes, because "
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
    forbidden_pattern = re.compile(
        r"\b(?:cas|tks|grammar|category|state literal|binary composition|let binding|recipe|rpm|fractal|cross register|omega|meta logic|inversion|diagram|export|expression|formula|equation)\b",
        re.IGNORECASE,
    )
    literal_pattern = re.compile(r"(?:\^|_|->|=>|[+\-/=<>])")
    return {
        "contains_literal_expression_symbol": bool(literal_pattern.search(text)),
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
                for focus_span, shape in (("A", left), ("B", right)):
                    english = f"{base_sentence} Focus: {focus_span}."
                    partner = right if focus_span == "A" else left
                    sample_id = (
                        f"s11_{mode}_{bundle['id']}_{pair['pair_kind']}_"
                        f"{family}_{shape}"
                    )
                    rows.append(
                        {
                            "sample_id": sample_id,
                            "dataset_version": f"stage11_expression_shapes_{mode}_v0",
                            "split": bundle["split"],
                            "contrast_bundle_id": bundle["id"],
                            "lexical_pack_id": bundle["lexical_pack_id"],
                            "template_id": f"{bundle['id']}_{pair['pair_kind']}_{family}_v01",
                            "counterfactual_pair_id": f"{bundle['id']}_{pair['pair_kind']}_{family}",
                            "pair_kind": pair["pair_kind"],
                            "paraphrase_family": family,
                            "surface_style": "role_bound_expression_shape_plain",
                            "english": english,
                            "base_sentence": base_sentence,
                            "focus_span": focus_span,
                            "shape_label": shape,
                            "shape_index": _SHAPE_TO_INDEX[shape],
                            "shape_plain": _SHAPES[shape]["plain"],
                            "shape_gloss": _SHAPES[shape]["gloss"],
                            "hard_contrast_shapes": [left, right],
                            "hard_contrast_labels": [_SHAPE_TO_INDEX[left], _SHAPE_TO_INDEX[right]],
                            "contrast_partner_shape": partner,
                            "anti_leak_flags": _anti_leak_flags(english),
                            "source_strategy": "codex_authored_expression_shape_role_bound_counterfactual_template",
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
    out_jsonl = _HERE / f"stage11_expression_shapes_{args.mode}_{_DATE}.jsonl"
    out_manifest = _HERE / f"stage11_expression_shapes_{args.mode}_manifest_{_DATE}.json"
    with out_jsonl.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    leak_counts = Counter()
    for row in rows:
        for key, value in row["anti_leak_flags"].items():
            if bool(value) and key != "counterbalanced_keyword_pack":
                leak_counts[key] += 1

    split_counts = Counter(str(row["split"]) for row in rows)
    label_counts = Counter(str(row["shape_label"]) for row in rows)
    family_counts = Counter(str(row["paraphrase_family"]) for row in rows)
    pair_kind_counts = Counter(str(row["pair_kind"]) for row in rows)
    manifest = {
        "schema_version": "stage11_expression_shape_fixture_manifest.v1",
        "mode": args.mode,
        "date": _DATE,
        "out_jsonl": out_jsonl.name,
        "out_jsonl_sha256": _sha256_of_file(out_jsonl),
        "n_rows": len(rows),
        "n_classes": len(label_counts),
        "shape_labels": list(_SHAPE_LABELS),
        "shape_metadata": _SHAPES,
        "split_counts": dict(sorted(split_counts.items())),
        "shape_counts": dict(sorted(label_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "pair_kind_counts": dict(sorted(pair_kind_counts.items())),
        "anti_leak_flag_counts": dict(sorted(leak_counts.items())),
        "position_definition": "ten existing Path D CAS expression grammar shapes",
        "source": "user-requested Stage 11 expression-shape ladder after Stage 10 five-operator result",
        "lessons_reused": [
            "role-bound same-sentence counterfactuals",
            "balanced labels",
            "explicit Focus marker",
            "literal expression/category leakage avoided in model-facing English",
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
