"""Build Stage 7 original-TKS foundation role-bound fixtures.

Stage 7 tests the 28 Foundations as original TKS foundation positions mapped
onto CAS Drive x Register notation:

    7 original foundations x 4 worlds/registers = 28 positions.

The local PDF source supplied by the user ("28 fOUNDATIONS 1.0.pdf") names
the four columns as Spiritual, Mental, Emotional, and Physical. In CAS v7.5
notation these map to T, A, f, and E respectively. The English fixture avoids
the literal column names so a plain text baseline cannot win only by reading
the label words.

The fixture intentionally reuses the Stage 6 role-bound lesson:

    same sentence, two candidate roles, explicit Focus: A/B marker.

This script builds data only. It does not capture activations, train probes,
or support a scientific claim by itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from build_stage6_role_bound_full import _bundles


_HERE = Path(__file__).resolve().parent
_DATE = "20260517"

_DRIVE_NAMES = {
    1: "Desire to be and be with God",
    2: "Wisdom, insight, and knowledge",
    3: "Life, vitality, and health",
    4: "Companionship, love, and friendship",
    5: "Worldly power, influence, and control",
    6: "Material food and things",
    7: "Lust, sex, and reproduction",
}
_REGISTERS = ("T", "A", "f", "E")
_REGISTER_NAMES = {
    "T": "Transcendent",
    "A": "Analytical",
    "f": "Affective",
    "E": "Embodied",
}
_TKS_WORLD_NAMES = {
    "T": "Spiritual",
    "A": "Mental",
    "f": "Emotional",
    "E": "Physical",
}
_TKS_WORLD_SUFFIX = {"T": "a", "A": "b", "f": "c", "E": "d"}

_CORE_FAMILIES = (
    "role_inverse_minimal",
    "no_alias_plain",
    "concrete_human",
    "system_process",
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


def _foundation_id(drive: int, register: str) -> str:
    return f"F{drive}{register}"


def _foundation_expression(drive: int, register: str) -> str:
    return f"F{drive}|{register}"


def _tks_code(drive: int, register: str) -> str:
    return f"{drive}{_TKS_WORLD_SUFFIX[register]}"


def _all_foundations() -> list[tuple[int, str]]:
    return [(drive, register) for drive in range(1, 8) for register in _REGISTERS]


def _pair_schedule() -> list[dict[str, Any]]:
    """Return balanced pair schedule.

    Each foundation appears once in same-drive register contrasts and twice in
    same-register drive-cycle contrasts, so every foundation appears three
    times per lexical bundle before focus duplication.
    """

    pairs: list[dict[str, Any]] = []
    for drive in range(1, 8):
        pairs.append(
            {
                "pair_kind": "same_drive_register_T_A",
                "left": (drive, "T"),
                "right": (drive, "A"),
            }
        )
        pairs.append(
            {
                "pair_kind": "same_drive_register_f_E",
                "left": (drive, "f"),
                "right": (drive, "E"),
            }
        )
    for register in _REGISTERS:
        for drive in range(1, 8):
            next_drive = 1 if drive == 7 else drive + 1
            pairs.append(
                {
                    "pair_kind": f"same_register_drive_cycle_{register}",
                    "left": (drive, register),
                    "right": (next_drive, register),
                }
            )
    return pairs


def _drive_core(drive: int, bundle: dict[str, str]) -> str:
    if drive == 1:
        return f"the pull toward ultimate source and belonging inside the {bundle['construct']}"
    if drive == 2:
        return f"the search for insight from {bundle['prior']} about what should be trusted"
    if drive == 3:
        return f"the living capacity in {bundle['toward']} staying healthy and active"
    if drive == 4:
        return f"the bond of care between {bundle['processor']} and {bundle['carrier']} keeping the case joined"
    if drive == 5:
        return f"the push to shape {bundle['result']} and guide what happens next"
    if drive == 6:
        return f"the need for usable resources in {bundle['parts']} that sustain the work"
    if drive == 7:
        return f"the generative urge that carries {bundle['result']} toward continuation"
    raise ValueError(f"unknown drive: {drive}")


def _register_frame(register: str, core: str, bundle: dict[str, str], family: str) -> str:
    if register == "T":
        variants = {
            "role_inverse_minimal": f"the sacred-orientation view of {core}",
            "no_alias_plain": f"the ultimate-purpose frame that keeps {core} visible",
            "concrete_human": f"the prayer-like attention the {bundle['processor']} keeps over {core}",
            "system_process": f"the highest-level orientation that keeps {core} visible across the process",
            "compressed_minimal": f"the sacred-purpose view of {core}",
            "long_embedded_clause": f"the ultimate-source view that remains present while the details of {core} keep shifting",
            "counter_alias_hard_negative": f"not a step-by-step checklist but the sacred-purpose view of {core}",
        }
    elif register == "A":
        variants = {
            "role_inverse_minimal": f"the thought-model check of {core}",
            "no_alias_plain": f"the explicit reasoning pass that tests {core}",
            "concrete_human": f"the line-by-line review the {bundle['processor']} makes of {core}",
            "system_process": f"the sequential logic that tests {core} against the record",
            "compressed_minimal": f"the reasoning check of {core}",
            "long_embedded_clause": f"the careful thought path that keeps asking whether {core} still follows",
            "counter_alias_hard_negative": f"not a vague overview but the reasoning check of {core}",
        }
    elif register == "f":
        variants = {
            "role_inverse_minimal": f"the heart-pressure around {core}",
            "no_alias_plain": f"the value-toned pull that makes {core} feel important",
            "concrete_human": f"the charged reaction the {bundle['processor']} has around {core}",
            "system_process": f"the preference-weighted signal that makes {core} matter in the flow",
            "compressed_minimal": f"the felt weight of {core}",
            "long_embedded_clause": f"the heart-level pressure that keeps returning whenever {core} comes into view",
            "counter_alias_hard_negative": f"not a cold checklist but the felt pressure around {core}",
        }
    elif register == "E":
        variants = {
            "role_inverse_minimal": f"the body-level contact with {core}",
            "no_alias_plain": f"the concrete handling that puts {core} into contact with the situation",
            "concrete_human": f"the bodily move the {bundle['processor']} makes around {core}",
            "system_process": f"the material operation that puts {core} into the workflow",
            "compressed_minimal": f"the concrete handling of {core}",
            "long_embedded_clause": f"the hands-on moment where {core} has to be handled in the actual situation",
            "counter_alias_hard_negative": f"not an abstract idea but the concrete handling of {core}",
        }
    else:
        raise ValueError(f"unknown register: {register}")
    return variants[family]


def _role_phrase(foundation: tuple[int, str], bundle: dict[str, str], family: str) -> str:
    drive, register = foundation
    return _register_frame(register, _drive_core(drive, bundle), bundle, family)


def _sentence(left: str, right: str, family: str) -> str:
    if family == "compressed_minimal":
        return f"A is {left}; B is {right}."
    if family == "long_embedded_clause":
        return (
            f"A is {left}; while the case continues, B is {right}, and both remain "
            "available until one role is selected."
        )
    if family == "counter_alias_hard_negative":
        return f"A is {left}; B is {right}."
    return f"A is {left}; B is {right}."


def _anti_leak_flags(text: str) -> dict[str, bool]:
    lowered = text.lower()
    world_names = {name.lower() for name in _TKS_WORLD_NAMES.values()}
    register_names = {name.lower() for name in _REGISTER_NAMES.values()}
    return {
        "contains_cas_notation": any(token in text for token in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "|T", "|A", "|f", "|E")),
        "contains_drive_name": any(name.lower() in lowered for name in _DRIVE_NAMES.values()),
        "contains_register_name": any(name.lower() in lowered for name in register_names | world_names),
        "counterbalanced_keyword_pack": True,
    }


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


def build_rows(mode: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    schedule = _pair_schedule()
    for bundle in _selected_bundles(mode):
        families = list(_CORE_FAMILIES)
        if bundle["split"] == "test":
            families.extend(_TEST_ONLY_FAMILIES)
        for pair_i, pair in enumerate(schedule, start=1):
            left = pair["left"]
            right = pair["right"]
            left_id = _foundation_id(*left)
            right_id = _foundation_id(*right)
            for family in families:
                left_phrase = _role_phrase(left, bundle, family)
                right_phrase = _role_phrase(right, bundle, family)
                base_sentence = _sentence(left_phrase, right_phrase, family)
                for focus_span, foundation in (("A", left), ("B", right)):
                    drive, register = foundation
                    foundation_id = _foundation_id(drive, register)
                    english = f"{base_sentence} Focus: {focus_span}."
                    sample_id = (
                        f"stage7_{mode}_{bundle['id']}_{pair['pair_kind']}_"
                        f"{left_id}_{right_id}_{family}_{foundation_id}"
                    )
                    rows.append(
                        {
                            "sample_id": sample_id,
                            "dataset_version": f"stage7_foundation_{mode}_v0",
                            "split": bundle["split"],
                            "contrast_bundle_id": bundle["id"],
                            "lexical_pack_id": bundle["lexical_pack_id"],
                            "template_id": f"{bundle['id']}_{pair['pair_kind']}_{left_id}_{right_id}_{family}_v01",
                            "counterfactual_pair_id": f"{bundle['id']}_{pair['pair_kind']}_{left_id}_{right_id}_{family}",
                            "pair_kind": pair["pair_kind"],
                            "paraphrase_family": family,
                            "surface_style": "role_bound_foundation_plain",
                            "english": english,
                            "base_sentence": base_sentence,
                            "focus_span": focus_span,
                            "foundation_label": foundation_id,
                            "foundation_drive": drive,
                            "foundation_register": register,
                            "foundation_drive_name": _DRIVE_NAMES[drive],
                            "foundation_register_name": _REGISTER_NAMES[register],
                            "tks_foundation_code": _tks_code(drive, register),
                            "tks_foundation_name": f"{_TKS_WORLD_NAMES[register]} {_DRIVE_NAMES[drive]}",
                            "tks_world_name": _TKS_WORLD_NAMES[register],
                            "foundation_expression": _foundation_expression(drive, register),
                            "cas_expression": _foundation_expression(drive, register),
                            "contrast_partner_foundation": right_id if focus_span == "A" else left_id,
                            "hard_contrast_foundations": [left_id, right_id],
                            "mapping_note": (
                                f"Focus {focus_span} selects {foundation_id}: "
                                f"drive F{drive} operating in register {register}."
                            ),
                            "anti_leak_flags": _anti_leak_flags(english),
                            "source_strategy": "codex_authored_original_tks_foundation_role_bound_counterfactual_template",
                            "review_status": "locked_fixture_pending_blind_review",
                            "confidence": "fixture_locked_unreviewed",
                        }
                    )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["pilot", "full"], default="pilot")
    args = parser.parse_args(argv)

    mode = str(args.mode)
    out_jsonl = _HERE / f"stage7_foundation_{mode}_{_DATE}.jsonl"
    out_manifest = _HERE / f"stage7_foundation_{mode}_manifest_{_DATE}.json"
    rows = build_rows(mode)
    with out_jsonl.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    split_counts = Counter(str(row["split"]) for row in rows)
    foundation_counts = Counter(str(row["foundation_label"]) for row in rows)
    pair_kind_counts = Counter(str(row["pair_kind"]) for row in rows)
    manifest = {
        "schema_version": "stage7_foundation_fixture_manifest.v1",
        "mode": mode,
        "date": _DATE,
        "out_jsonl": out_jsonl.name,
        "out_jsonl_sha256": _sha256_of_file(out_jsonl),
        "n_rows": len(rows),
        "n_foundations": len(foundation_counts),
        "split_counts": dict(sorted(split_counts.items())),
        "foundation_counts": dict(sorted(foundation_counts.items())),
        "pair_kind_counts": dict(sorted(pair_kind_counts.items())),
        "position_definition": "7 original TKS foundations x 4 worlds/registers = 28 positions",
        "source": (
            "local PDF: C:/Users/wakil/Downloads/Everthing-Tootra-TKS/"
            "28 fOUNDATIONS 1.0.pdf; CAS map cross-checked against "
            "docs/reference/tks_28_foundations_translation_key.md"
        ),
        "lessons_from_stage6": [
            "same-sentence role-bound counterfactuals",
            "balanced labels",
            "explicit Focus marker",
            "no scientific claim from fixture alone",
            "text baselines required before ablation",
            "generation tests deferred until readout and readout-causality pass",
        ],
    }
    out_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
