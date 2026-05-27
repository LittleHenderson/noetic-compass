"""Build a balanced source-derived TKS 40-Element scenario library.

The original Pythia Stage 9 fixture tested the user's TKS 40 Elements:

    4 legacy worlds/domains x 10 elements = 40 element slots.

This worker-side builder mirrors that source surface for large-model open-
weight replication. It emits current CAS labels (`operator x domain`) plus the
legacy A1-D10 code used by the original methodology. Prompt text avoids literal
class codes and framework names, but the compact source glosses are still
highly text-separable. Treat this v0 library as a source-derived
activation/readout fixture, not a final "CAS beats text" adversarial eval set.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Any


LEGACY_DOMAIN_TO_CAS_DOMAIN: dict[str, str] = {
    "A": "P",
    "B": "C",
    "C": "E",
    "D": "O",
}

LEGACY_DOMAIN_NAMES: dict[str, str] = {
    "A": "spiritual",
    "B": "mental",
    "C": "emotional",
    "D": "physical",
}

LEGACY_ELEMENT_TO_OPERATOR: dict[int, str] = {
    1: "^1",
    2: "^2",
    3: "^3",
    4: "^4",
    5: "^5",
    6: "^6",
    7: "^7",
    8: "^8",
    9: "^9",
    10: "^0",
}

LEGACY_ELEMENT_NAMES: dict[int, str] = {
    1: "mind",
    2: "positive",
    3: "negative",
    4: "vibration",
    5: "female",
    6: "male",
    7: "rhythm",
    8: "above",
    9: "below",
    10: "idea",
}


# Source-derived compact glosses ported from the original Stage 9 fixture on
# experiment/cas-probe-pythia. They are concise prompt material for the TKS
# A1-D10 definitions, not replacement ontology.
ELEMENT_GLOSSES: dict[str, dict[int, str]] = {
    "A": {
        1: "ultimate source-awareness, unseen purpose, and the soul's contact with what guides all causes",
        2: "a truth or virtue that quiets the soul and draws it closer to its highest aim",
        3: "a vice, fear, or harmful influence that troubles the soul and slows its growth",
        4: "subtle aetheric energy, aura, and purpose-frequency behind a thing",
        5: "the soul's receptive matrix for needed growth, nurture, and protection",
        6: "austere practices and trials that transmit discipline for the soul's growth",
        7: "the rise and fall of a life-journey, destiny pattern, or sacred timing",
        8: "inner meaning, initiation, esoteric reality, and high moral insight",
        9: "outer symbol, exoteric shell, shallow moral grasp, or empty appearance",
        10: "a purely unseen matter: true self, soul-state, or record of a thing",
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
        7: "music, motion, exercise, dance, routine, or timed physical sequence",
        8: "height, high grade, good material integrity, or high social position",
        9: "lower position, poor material integrity, low grade, or low social position",
        10: "dead matter or a thing existing entirely as a material object",
    },
}


TEMPLATES = (
    "A reviewer is auditing an answer. The relevant role is where {gloss}. What should the answer notice before deciding?",
    "A model is asked to advise a team. The case turns on {gloss}. The user needs that role handled without naming the taxonomy.",
    "During a safety review, the output is fluent but may miss the role where {gloss}. Identify what the answer should preserve.",
    "An evaluator sees two possible readings, but this row focuses on the one where {gloss}. What concern should be tracked?",
    "A deployment review asks whether the model understands the situation. The important signal is {gloss}. What should the answer account for?",
    "A user wants careful guidance. The hidden pressure point is {gloss}. Name the practical issue the answer should not skip.",
    "A policy analyst checks an answer before release. The selected role involves {gloss}. What would a strong response keep visible?",
    "A partner asks for help. The case is not about style; it depends on {gloss}. What should the model attend to?",
    "A model output is being scored. The intended signal is {gloss}. What does that signal imply for the response?",
    "An audit prompt asks what the model may overlook. The overlooked role is where {gloss}. What should be inspected?",
)


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--examples-per-class", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(examples_per_class=args.examples_per_class)
    validate_payload(payload, expected_per_class=args.examples_per_class)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[tks40] wrote {args.output}")
    print(f"[tks40] scenarios={len(payload['scenarios'])}")
    return 0


def build_payload(*, examples_per_class: int) -> dict[str, Any]:
    if examples_per_class < 3:
        raise ValueError("examples_per_class must be >= 3 so heldout splits are meaningful.")
    scenarios: list[dict[str, Any]] = []
    for legacy_domain in ("A", "B", "C", "D"):
        for legacy_element in range(1, 11):
            for variant in range(examples_per_class):
                scenarios.append(build_scenario(legacy_domain, legacy_element, variant))
    return {
        "schema_version": "cas_harness_tks40_scenario_library.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "generator": "live-trace-worker/scripts/build_tks40_scenarios.py",
        "axis": "element",
        "class_definition": "10 Noetics/operators x 4 Domains = 40 TKS Element classes",
        "source_profile": "source_derived_from_original_stage9_tks40_glosses",
        "original_method_reference": "research/cas_probe/build_stage9_elements_fixture.py on experiment/cas-probe-pythia",
        "examples_per_class": examples_per_class,
        "scenario_count": len(scenarios),
        "important_limit": (
            "Scenario source only. This is not a probe result, ablation result, "
            "verifier verdict, Evidence Packet, or final text-baseline adversary."
        ),
        "scenarios": scenarios,
    }


def build_scenario(legacy_domain: str, legacy_element: int, variant: int) -> dict[str, Any]:
    legacy_code = f"{legacy_domain}{legacy_element}"
    domain = LEGACY_DOMAIN_TO_CAS_DOMAIN[legacy_domain]
    operator = LEGACY_ELEMENT_TO_OPERATOR[legacy_element]
    element = f"{operator}|{domain}"
    gloss = ELEMENT_GLOSSES[legacy_domain][legacy_element]
    prompt = TEMPLATES[variant % len(TEMPLATES)].format(gloss=gloss)
    return {
        "id": f"tks40_{legacy_code}_{variant:02d}",
        "prompt": prompt,
        "expected_cas_axes": {
            "domain": domain,
            "operator": operator,
            "noetic": operator,
            "element": element,
        },
        "metadata": {
            "axis": "element",
            "legacy_element_code": legacy_code,
            "legacy_domain": legacy_domain,
            "legacy_domain_name": LEGACY_DOMAIN_NAMES[legacy_domain],
            "legacy_element": legacy_element,
            "legacy_element_name": LEGACY_ELEMENT_NAMES[legacy_element],
            "source_profile": "source_derived_from_original_stage9_tks40_glosses",
            "variant": variant,
            "prompt_sha256": sha256_text(prompt),
        },
    }


def validate_payload(payload: dict[str, Any], *, expected_per_class: int) -> None:
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("payload.scenarios must be a list")
    counts: Counter[str] = Counter()
    ids: set[str] = set()
    prompts: set[str] = set()
    for item in scenarios:
        axes = item.get("expected_cas_axes")
        if not isinstance(axes, dict):
            raise ValueError(f"missing expected_cas_axes for {item.get('id')}")
        domain = str(axes.get("domain") or "")
        operator = str(axes.get("operator") or "")
        element = str(axes.get("element") or "")
        if domain not in set(LEGACY_DOMAIN_TO_CAS_DOMAIN.values()):
            raise ValueError(f"bad domain for {item.get('id')}: {domain}")
        if operator not in set(LEGACY_ELEMENT_TO_OPERATOR.values()):
            raise ValueError(f"bad operator for {item.get('id')}: {operator}")
        if element != f"{operator}|{domain}":
            raise ValueError(f"bad element for {item.get('id')}: {element}")
        prompt = str(item.get("prompt") or "")
        if not prompt.strip():
            raise ValueError(f"empty prompt for {item.get('id')}")
        if _leaks_label(prompt):
            raise ValueError(f"prompt leaks framework/class label for {item.get('id')}")
        item_id = str(item.get("id"))
        if item_id in ids:
            raise ValueError(f"duplicate id: {item_id}")
        if prompt in prompts:
            raise ValueError(f"duplicate prompt: {item_id}")
        ids.add(item_id)
        prompts.add(prompt)
        counts[element] += 1
    expected = {
        f"{LEGACY_ELEMENT_TO_OPERATOR[element]}|{LEGACY_DOMAIN_TO_CAS_DOMAIN[domain]}"
        for domain in ("A", "B", "C", "D")
        for element in range(1, 11)
    }
    if set(counts) != expected:
        raise ValueError(f"element label set mismatch: {sorted(set(counts) ^ expected)}")
    bad_counts = {label: count for label, count in counts.items() if count != expected_per_class}
    if bad_counts:
        raise ValueError(f"unbalanced element counts: {bad_counts}")


def _leaks_label(prompt: str) -> bool:
    literal = re.compile(
        r"\b(?:A[1-9]|A10|B[1-9]|B10|C[1-9]|C10|D[1-9]|D10|CAS|TKS|noetic|element label)\b",
        re.IGNORECASE,
    )
    return bool(literal.search(prompt)) or any(token in prompt for token in ("^0", "^1", "^2", "^3", "^4", "^5", "^6", "^7", "^8", "^9"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
