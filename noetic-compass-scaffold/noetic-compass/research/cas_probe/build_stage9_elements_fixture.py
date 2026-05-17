"""Build Stage 9 original-TKS 40 Elements role-bound fixture.

Stage 9 tests the user's original 40 Elements passage:

    4 worlds/domains x 10 noetics = 40 element slots.

The fixture follows the Stage 6/7 lesson: each row contains two possible
roles in the same sentence and an explicit Focus marker. The model-facing
English avoids literal labels such as A1, Spiritual Mind, CAS, TKS, or
noetic notation. Metadata keeps those mappings for audit.
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

_DOMAINS = ("A", "B", "C", "D")
_DOMAIN_TO_REGISTER = {"A": "T", "B": "A", "C": "f", "D": "E"}
_DOMAIN_NAMES = {
    "A": "Spiritual",
    "B": "Mental",
    "C": "Emotional",
    "D": "Physical",
}
_REGISTER_NAMES = {
    "T": "Transcendent",
    "A": "Analytical",
    "f": "Affective",
    "E": "Embodied",
}
_NOETIC_NAMES = {
    1: "Mind",
    2: "Positive",
    3: "Negative",
    4: "Vibration",
    5: "Female",
    6: "Male",
    7: "Rhythm",
    8: "Above/Cause",
    9: "Below/Effect",
    10: "Idea",
}
_TKS_TO_CAS_NOETIC = {10: "^0", **{i: f"^{i}" for i in range(1, 10)}}

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

_ELEMENT_GLOSSES: dict[str, dict[int, str]] = {
    "A": {
        1: "ultimate source-awareness, unseen purpose, and the soul's contact with what guides all causes",
        2: "a truth or virtue that quiets the soul and draws it closer to its highest aim",
        3: "a vice, fear, or harmful influence that troubles the soul and slows its growth",
        4: "subtle aetheric energy, aura, and purpose-frequency behind a thing",
        5: "the soul's receptive womb for needed growth, nurture, and protection",
        6: "austere practices and trials that transmit discipline for the soul's growth",
        7: "the rise and fall of a life-journey, destiny pattern, or sacred timing",
        8: "inner meaning, initiation, esoteric reality, and high moral insight",
        9: "outer symbol, exoteric shell, shallow moral grasp, or empty appearance",
        10: "a purely unseen matter: true self, soul-state, or akashic record of a thing",
    },
    "B": {
        1: "ego, memory, past experience, and analytical processing that reaches conclusions",
        2: "clarity, sanity, optimism, benevolence, and enlightened thought",
        3: "confusion, indecision, dissonance, pessimism, or malicious thought",
        4: "brainwave-like resonance and the unique psychic signature of a thought",
        5: "imaginative openness, right-brain creativity, and subconscious receptivity",
        6: "left-brain logic, criticism, rigidity, and conscious analysis",
        7: "recurring thought pattern, ego-state transition, or frequency of a thought",
        8: "complex comprehension, contemplation of important matters, and brilliant intelligence",
        9: "limited comprehension, menial concern, or simplistic pondering",
        10: "a thought-content that exists only as an inner mental object",
    },
    "C": {
        1: "awareness of one's own or another's feelings and sorting decisions by feeling",
        2: "joy, calm, love, fellowship, and pleasurable feeling",
        3: "sadness, anger, resentment, contempt, loneliness, hate, or mixed pain",
        4: "felt ambiance, mood-energy, and the aura carried by a person, place, or event",
        5: "compassion, sympathy, acceptance, sensuality, and receptive feeling",
        6: "aggression, pride, dominance, and forceful feeling",
        7: "mood swing, feeling-sequence, or emotional roller-coaster pattern",
        8: "healed resolve and control over lower feelings after deep insight",
        9: "being overwhelmed and driven by feeling rather than holding it",
        10: "the lingering felt sheath or ambiance of an idea, like a dream-scent after waking",
    },
    "D": {
        1: "brain, body, cellular hardware, or machine substrate hosting awareness",
        2: "well-fit parts that complement each other and function according to design",
        3: "misplaced parts, disorder, disease, dysfunction, or broken symmetry",
        4: "light, sound, radiation, heat, electromagnetism, or particle oscillation",
        5: "receiver, womb, receptacle, or facilitator that accepts and nurtures a seed",
        6: "transmitter, appendage, seed-deliverer, or outward projecting part",
        7: "music, motion, exercise, dance, sex, routine, or timed physical sequence",
        8: "height, high grade, good material integrity, or high social position",
        9: "lower position, poor material integrity, low grade, or low social position",
        10: "dead matter or a thing existing entirely as a material object",
    },
}


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _element_id(domain: str, noetic: int) -> str:
    return f"{domain}{noetic}"


def _all_elements() -> list[tuple[str, int]]:
    return [(domain, noetic) for domain in _DOMAINS for noetic in range(1, 11)]


def _pair_schedule() -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for domain in _DOMAINS:
        for noetic in range(1, 11):
            nxt = 1 if noetic == 10 else noetic + 1
            pairs.append(
                {
                    "pair_kind": f"same_domain_noetic_cycle_{domain}",
                    "left": (domain, noetic),
                    "right": (domain, nxt),
                }
            )
    domain_cycles = (("A", "B"), ("B", "C"), ("C", "D"), ("D", "A"))
    for noetic in range(1, 11):
        for left_domain, right_domain in domain_cycles:
            pairs.append(
                {
                    "pair_kind": f"same_noetic_domain_cycle_{noetic}",
                    "left": (left_domain, noetic),
                    "right": (right_domain, noetic),
                }
            )
    return pairs


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


def _family_phrase(element: tuple[str, int], bundle: dict[str, str], family: str) -> str:
    domain, noetic = element
    gloss = _ELEMENT_GLOSSES[domain][noetic]
    if family == "definition_compact":
        return f"the role where {gloss}"
    if family == "applied_human":
        return f"what the {bundle['processor']} notices when {gloss} shapes the case"
    if family == "system_process":
        return f"the process signal showing {gloss} inside {bundle['construct']}"
    if family == "role_inverse_plain":
        return f"the selected aspect of {bundle['prior']} where {gloss}"
    if family == "compressed_minimal":
        return f"{gloss}"
    if family == "long_embedded_clause":
        return (
            f"the role that remains present while {bundle['carrier']} changes, because "
            f"{gloss} keeps steering how the situation is understood"
        )
    if family == "counter_alias_hard_negative":
        return f"not the neighboring role, but the aspect where {gloss}"
    raise ValueError(f"unknown family {family!r}")


def _sentence(left: str, right: str, family: str) -> str:
    if family == "long_embedded_clause":
        return f"A is {left}; while the record unfolds, B is {right}, and the focus chooses only one role."
    return f"A is {left}; B is {right}."


def _anti_leak_flags(text: str) -> dict[str, bool]:
    lowered = text.lower()
    literal_tokens = ["A1", "A2", "A3", "B1", "B2", "C1", "D1", "^0", "^1", "^2", "^3", "^4", "^5", "^6", "^7", "^8", "^9"]
    forbidden_words = ("cas", "tks", "noetic", "element label")
    return {
        "contains_literal_element_code": any(token in text for token in literal_tokens),
        "contains_framework_word": any(word in lowered for word in forbidden_words),
        "counterbalanced_keyword_pack": True,
    }


def build_rows(mode: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    schedule = _pair_schedule()
    for bundle in _selected_bundles(mode):
        families = list(_CORE_FAMILIES)
        if bundle["split"] == "test":
            families.extend(_TEST_ONLY_FAMILIES)
        for pair in schedule:
            left = pair["left"]
            right = pair["right"]
            left_id = _element_id(*left)
            right_id = _element_id(*right)
            for family in families:
                left_phrase = _family_phrase(left, bundle, family)
                right_phrase = _family_phrase(right, bundle, family)
                base_sentence = _sentence(left_phrase, right_phrase, family)
                for focus_span, element in (("A", left), ("B", right)):
                    domain, noetic = element
                    element_label = _element_id(domain, noetic)
                    register = _DOMAIN_TO_REGISTER[domain]
                    english = f"{base_sentence} Focus: {focus_span}."
                    sample_id = (
                        f"s9_{mode}_{bundle['id']}_{pair['pair_kind']}_"
                        f"{left_id}_{right_id}_{family}_{element_label}"
                    )
                    rows.append(
                        {
                            "sample_id": sample_id,
                            "dataset_version": f"stage9_elements_{mode}_v0",
                            "split": bundle["split"],
                            "contrast_bundle_id": bundle["id"],
                            "lexical_pack_id": bundle["lexical_pack_id"],
                            "template_id": f"{bundle['id']}_{pair['pair_kind']}_{left_id}_{right_id}_{family}_v01",
                            "counterfactual_pair_id": f"{bundle['id']}_{pair['pair_kind']}_{left_id}_{right_id}_{family}",
                            "pair_kind": pair["pair_kind"],
                            "paraphrase_family": family,
                            "surface_style": "role_bound_tks_40_elements_plain",
                            "english": english,
                            "base_sentence": base_sentence,
                            "focus_span": focus_span,
                            "element_label": element_label,
                            "element_domain": domain,
                            "element_domain_name": _DOMAIN_NAMES[domain],
                            "element_register": register,
                            "element_register_name": _REGISTER_NAMES[register],
                            "element_noetic_tks": noetic,
                            "element_noetic_name": _NOETIC_NAMES[noetic],
                            "element_cas_noetic": _TKS_TO_CAS_NOETIC[noetic],
                            "element_gloss": _ELEMENT_GLOSSES[domain][noetic],
                            "hard_contrast_elements": [left_id, right_id],
                            "contrast_partner_element": right_id if focus_span == "A" else left_id,
                            "anti_leak_flags": _anti_leak_flags(english),
                            "source_strategy": "codex_authored_original_tks_40_element_role_bound_counterfactual_template",
                            "review_status": "locked_fixture_pending_blind_review",
                            "confidence": "fixture_locked_unreviewed",
                        }
                    )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["pilot", "full"], default="pilot")
    args = parser.parse_args(argv)

    rows = build_rows(str(args.mode))
    out_jsonl = _HERE / f"stage9_elements_{args.mode}_{_DATE}.jsonl"
    out_manifest = _HERE / f"stage9_elements_{args.mode}_manifest_{_DATE}.json"
    with out_jsonl.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    split_counts = Counter(str(row["split"]) for row in rows)
    label_counts = Counter(str(row["element_label"]) for row in rows)
    domain_counts = Counter(str(row["element_domain"]) for row in rows)
    noetic_counts = Counter(str(row["element_noetic_tks"]) for row in rows)
    pair_kind_counts = Counter(str(row["pair_kind"]) for row in rows)
    manifest = {
        "schema_version": "stage9_elements_fixture_manifest.v1",
        "mode": args.mode,
        "date": _DATE,
        "out_jsonl": out_jsonl.name,
        "out_jsonl_sha256": _sha256_of_file(out_jsonl),
        "n_rows": len(rows),
        "n_elements": len(label_counts),
        "split_counts": dict(sorted(split_counts.items())),
        "element_counts": dict(sorted(label_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
        "noetic_counts": dict(sorted(noetic_counts.items())),
        "pair_kind_counts": dict(sorted(pair_kind_counts.items())),
        "position_definition": "4 original TKS worlds/domains x 10 noetics = 40 elements",
        "source": "user-provided original TKS 40 Elements passage in chat on 2026-05-17",
        "lessons_reused": [
            "role-bound same-sentence counterfactuals",
            "balanced labels",
            "explicit Focus marker",
            "literal label leakage avoided in model-facing English",
            "text and metadata baselines required before any harness claim",
        ],
    }
    out_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
