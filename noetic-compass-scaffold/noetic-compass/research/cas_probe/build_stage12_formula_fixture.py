"""Build Stage 12 compiler-validated equation/formula role-bound fixture."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from build_stage6_role_bound_full import _bundles


_HERE = Path(__file__).resolve().parent
_NOETIC_ROOT = _HERE.parents[1]
_DATE = "20260517"

_MEMBER = chr(0x2208)
_SUBSET_EQ = chr(0x2286)
_UNION = chr(0x222A)
_INTERSECTION = chr(0x2229)
_SET_MINUS = chr(0x2216)

_FORMULAS: dict[str, dict[str, str]] = {
    "relation_dependency": {
        "plain": "one condition points forward to a later dependent condition",
        "gloss": "one condition points forward to a later condition that depends on it",
    },
    "typed_program": {
        "plain": "a named value and typed reusable action are declared and then used",
        "gloss": "a named starting value is saved, a reusable typed action is declared, and that action is then used",
    },
    "production_recipe": {
        "plain": "a named outcome is built from weighted requirements",
        "gloss": "a named outcome is built from weighted requirements and possible side results",
    },
    "yield_query": {
        "plain": "a request asks for expected actual or efficient amount",
        "gloss": "a request asks for the expected actual or efficient amount of a named outcome",
    },
    "state_vector": {
        "plain": "one profile records several weighted activations",
        "gloss": "one profile records several weighted signals at the same time",
    },
    "emergent_register_assignment": {
        "plain": "several modes of one pattern fuse into a named result",
        "gloss": "several modes of the same pattern are fused under one result name",
    },
    "membership_assertion": {
        "plain": "one item is checked for belonging inside an allowed collection",
        "gloss": "one item is checked for belonging inside an allowed collection",
    },
    "cardinality_assertion": {
        "plain": "a collection is checked against an exact count",
        "gloss": "a collection is checked against an exact count",
    },
    "set_operation_formula": {
        "plain": "finite collections are combined or overlapped",
        "gloss": "two finite collections are combined or overlapped to form another collection",
    },
    "cover_partition_formula": {
        "plain": "collections are checked for complete reach or clean separation",
        "gloss": "several collections are checked against a whole universe for complete reach or clean separation",
    },
}
_FORMULA_LABELS = tuple(_FORMULAS)
_FORMULA_TO_INDEX = {label: i for i, label in enumerate(_FORMULA_LABELS)}

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


def _load_compile_expression():
    if str(_NOETIC_ROOT) not in sys.path:
        sys.path.insert(0, str(_NOETIC_ROOT))
    module = importlib.import_module("api.notation")
    compile_expression = getattr(module, "compile_expression")
    if not callable(compile_expression):
        raise RuntimeError("api.notation.compile_expression is not callable")
    return compile_expression


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return cleaned or "target"


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
    labels = list(_FORMULA_LABELS)
    pairs: list[dict[str, Any]] = []
    for i, left in enumerate(labels):
        right = labels[(i + 1) % len(labels)]
        pairs.append({"pair_kind": f"formula_cycle_next_{left}_vs_{right}", "left": left, "right": right})
    for i in range(len(labels) // 2):
        left = labels[i]
        right = labels[i + len(labels) // 2]
        pairs.append({"pair_kind": f"formula_cross_half_{left}_vs_{right}", "left": left, "right": right})
    return pairs


def _state(noetic: int, domain: str, drive: int | None = None, register: str | None = None) -> str:
    out = f"^{noetic}^{domain}"
    if drive is not None:
        out += f"_{{F{drive}}}"
    if register is not None:
        out += f"|{register}"
    return out


def _formula_expression(label: str, bundle: dict[str, str], variant: int) -> str:
    noetic_a = (variant % 9) + 1
    noetic_b = ((variant + 3) % 9) + 1
    drive_a = (variant % 7) + 1
    drive_b = ((variant + 2) % 7) + 1
    register_a = ("T", "A", "f", "E")[variant % 4]
    register_b = ("A", "f", "E", "T")[(variant + 1) % 4]
    target = _slug(f"{bundle['lexical_pack_id']}_{variant}")[:40]
    if label == "relation_dependency":
        descents = (("P", "C"), ("C", "E"), ("E", "O"))
        source_domain, target_domain = descents[variant % len(descents)]
        return f"{_state(noetic_a, source_domain, drive_a, register_a)} -> {_state(noetic_b, target_domain, drive_b, register_b)}"
    if label == "typed_program":
        return (
            f"let base: state[C] = {_state(noetic_a, 'C', drive_a, register_a)}; "
            "fn bridge(x: state[C], y: state[E]): relation = x -> y; "
            f"bridge(base, {_state(noetic_b, 'E', drive_b, register_b)})"
        )
    if label == "production_recipe":
        return (
            f"Theta(Omega_{target}) = "
            f"1*{_state(noetic_a, 'C', drive_a, register_a)} + "
            f"0.7*{_state(noetic_b, 'C', drive_b, register_b)} -> Omega_{target}"
        )
    if label == "yield_query":
        query = ("Y_T", "Y_A", "eta")[variant % 3]
        return f"{query}(Omega_{target})"
    if label == "state_vector":
        c = 3 + (variant % 5)
        d = 4 + (variant % 4)
        e = 2 + (variant % 6)
        return f"S = {{F_{drive_a}: {c}, F_{drive_b}: {d}, {_state(noetic_a, 'C', None, register_a)}: {e}}}"
    if label == "emergent_register_assignment":
        domain = ("P", "C", "E", "O")[variant % 4]
        return f"({_state(noetic_a, domain, None, 'A')} * {_state(noetic_a, domain, None, 'f')}) = fused_{target}"
    if label == "membership_assertion":
        cases = (
            f"{_state(noetic_a, 'P')} {_MEMBER} States",
            f"F_1|T {_MEMBER} Foundation_1",
            f"P {_MEMBER} Domains",
            f"T {_MEMBER} Registers",
        )
        return cases[variant % len(cases)]
    if label == "cardinality_assertion":
        cases = ("|States| = 40", "|Noetics| = 10", "|Domains| = 4", "|Foundation_1| = 4")
        return cases[variant % len(cases)]
    if label == "set_operation_formula":
        ops = (_UNION, _INTERSECTION, _SET_MINUS)
        op = ops[variant % len(ops)]
        return f"NoeticCluster{{^2, ^7}} {op} NoeticCluster{{^7, ^8}}"
    if label == "cover_partition_formula":
        args = ", ".join(f"Foundation_{i}" for i in range(1, 8))
        fn = "CoverOf" if variant % 2 == 0 else "PartitionOf"
        return f"{fn}(SubFoundations, {args})"
    raise ValueError(f"unknown formula label {label!r}")


def _family_phrase(label: str, bundle: dict[str, str], family: str) -> str:
    gloss = _FORMULAS[label]["gloss"]
    processor = bundle["processor"]
    construct = bundle["construct"]
    prior = bundle["prior"]
    carrier = bundle["carrier"]
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
            f"the role that remains active while {carrier} changes because "
            f"{gloss} before the record settles"
        )
    if family == "counter_alias_hard_negative":
        return f"not the neighboring role but the aspect where {gloss}"
    raise ValueError(f"unknown family {family!r}")


def _sentence(left: str, right: str, family: str) -> str:
    if family == "long_embedded_clause":
        return f"A is {left}; while the record unfolds, B is {right}, and the focus chooses only one role."
    return f"A is {left}; B is {right}."


def _anti_leak_flags(text: str) -> dict[str, bool]:
    forbidden_pattern = re.compile(
        r"\b(?:cas|tks|formula|equation|grammar|category|relation dependency|typed program|production recipe|yield query|state vector|emergent register|membership assertion|cardinality assertion|set operation|cover partition)\b",
        re.IGNORECASE,
    )
    literal_pattern = re.compile(r"(?:\^|_|->|=>|[+\-/=<>*{}])")
    return {
        "contains_literal_formula_symbol": bool(literal_pattern.search(text)),
        "contains_framework_or_label_word": bool(forbidden_pattern.search(text)),
        "counterbalanced_keyword_pack": True,
    }


def _compile_metadata(expression: str, compile_expression: Any) -> dict[str, Any]:
    artifact = compile_expression(expression)
    if not getattr(artifact, "valid", False):
        raise ValueError(f"compiler rejected {expression!r}: {getattr(artifact, 'error', None)}")
    payload = artifact.to_dict()
    result = payload.get("result") or {}
    diagram = artifact.diagram()
    return {
        "valid": True,
        "result_kind": str(result.get("kind", "unknown")),
        "diagram_available": isinstance(diagram, dict) and bool(diagram.get("nodes")),
        "diagram_layouts": list(diagram.get("layouts", [])) if isinstance(diagram, dict) else [],
    }


def build_rows(mode: str) -> list[dict[str, Any]]:
    compile_expression = _load_compile_expression()
    compile_cache: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for bundle_index, bundle in enumerate(_selected_bundles(mode)):
        families = list(_CORE_FAMILIES)
        if bundle["split"] == "test":
            families.extend(_TEST_ONLY_FAMILIES)
        for pair_index, pair in enumerate(_pair_schedule()):
            left = str(pair["left"])
            right = str(pair["right"])
            for family_index, family in enumerate(families):
                left_phrase = _family_phrase(left, bundle, family)
                right_phrase = _family_phrase(right, bundle, family)
                base_sentence = _sentence(left_phrase, right_phrase, family)
                for focus_span, label in (("A", left), ("B", right)):
                    variant = bundle_index * 1000 + pair_index * 20 + family_index * 2 + (0 if focus_span == "A" else 1)
                    expression = _formula_expression(label, bundle, variant)
                    if expression not in compile_cache:
                        compile_cache[expression] = _compile_metadata(expression, compile_expression)
                    english = f"{base_sentence} Focus: {focus_span}."
                    partner = right if focus_span == "A" else left
                    sample_id = (
                        f"s12_{mode}_{bundle['id']}_{pair['pair_kind']}_"
                        f"{family}_{label}"
                    )
                    rows.append(
                        {
                            "sample_id": sample_id,
                            "dataset_version": f"stage12_equations_formulas_{mode}_v0",
                            "split": bundle["split"],
                            "contrast_bundle_id": bundle["id"],
                            "lexical_pack_id": bundle["lexical_pack_id"],
                            "template_id": f"{bundle['id']}_{pair['pair_kind']}_{family}_v01",
                            "counterfactual_pair_id": f"{bundle['id']}_{pair['pair_kind']}_{family}",
                            "pair_kind": pair["pair_kind"],
                            "paraphrase_family": family,
                            "surface_style": "role_bound_compiler_validated_formula_plain",
                            "english": english,
                            "base_sentence": base_sentence,
                            "focus_span": focus_span,
                            "formula_label": label,
                            "formula_index": _FORMULA_TO_INDEX[label],
                            "formula_plain": _FORMULAS[label]["plain"],
                            "formula_gloss": _FORMULAS[label]["gloss"],
                            "cas_formula": expression,
                            "compiler": compile_cache[expression],
                            "hard_contrast_formulas": [left, right],
                            "hard_contrast_labels": [_FORMULA_TO_INDEX[left], _FORMULA_TO_INDEX[right]],
                            "contrast_partner_formula": partner,
                            "anti_leak_flags": _anti_leak_flags(english),
                            "source_strategy": "codex_authored_compiler_validated_formula_role_bound_counterfactual_template",
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
    out_jsonl = _HERE / f"stage12_equations_formulas_{args.mode}_{_DATE}.jsonl"
    out_manifest = _HERE / f"stage12_equations_formulas_{args.mode}_manifest_{_DATE}.json"
    with out_jsonl.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    leak_counts = Counter()
    for row in rows:
        for key, value in row["anti_leak_flags"].items():
            if bool(value) and key != "counterbalanced_keyword_pack":
                leak_counts[key] += 1

    split_counts = Counter(str(row["split"]) for row in rows)
    label_counts = Counter(str(row["formula_label"]) for row in rows)
    family_counts = Counter(str(row["paraphrase_family"]) for row in rows)
    pair_kind_counts = Counter(str(row["pair_kind"]) for row in rows)
    compiler_kinds = Counter(str(row["compiler"]["result_kind"]) for row in rows)
    manifest = {
        "schema_version": "stage12_equations_formulas_fixture_manifest.v1",
        "mode": args.mode,
        "date": _DATE,
        "out_jsonl": out_jsonl.name,
        "out_jsonl_sha256": _sha256_of_file(out_jsonl),
        "n_rows": len(rows),
        "n_classes": len(label_counts),
        "formula_labels": list(_FORMULA_LABELS),
        "formula_metadata": _FORMULAS,
        "split_counts": dict(sorted(split_counts.items())),
        "formula_counts": dict(sorted(label_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "pair_kind_counts": dict(sorted(pair_kind_counts.items())),
        "compiler_result_kind_counts": dict(sorted(compiler_kinds.items())),
        "anti_leak_flag_counts": dict(sorted(leak_counts.items())),
        "position_definition": "ten compiler-validated CAS equation/formula families",
        "source": "user-requested Stage 12 formulas/equations ladder after Stage 11 expression-shape pass",
        "lessons_reused": [
            "role-bound same-sentence counterfactuals",
            "balanced labels",
            "explicit Focus marker",
            "compiler validation stored in metadata",
            "raw formula/CAS symbols withheld from model-facing English",
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
