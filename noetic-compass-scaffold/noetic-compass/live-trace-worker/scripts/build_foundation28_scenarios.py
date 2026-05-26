"""Build a balanced source-derived Foundation-28 scenario library.

Foundation-28 is the 7 Drive x 4 Register axis used by the original Pythia
Foundation readout. This script creates a concrete open-weight probe dataset
source without embedding class codes in the prompt text. It mirrors the
original Stage 7 TKS Foundation surface, where legacy worlds 1a-7d map onto
CAS drive/register labels F1|T through F7|E.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any


DRIVES: dict[str, dict[str, str]] = {
    "F1": {
        "name": "Unity",
        "concern": "inclusion, protection, belonging, and what should stay connected",
    },
    "F2": {
        "name": "Wisdom",
        "concern": "facts, context, uncertainty, judgment, and what should be understood first",
    },
    "F3": {
        "name": "Vitality",
        "concern": "harm, safety, health, resilience, energy, and survival",
    },
    "F4": {
        "name": "Connection",
        "concern": "trust, empathy, relationship damage, social pressure, and repair",
    },
    "F5": {
        "name": "Agency",
        "concern": "choice, consent, responsibility, control, and power",
    },
    "F6": {
        "name": "Structure",
        "concern": "rules, boundaries, safeguards, constraints, and reliable order",
    },
    "F7": {
        "name": "Purpose",
        "concern": "larger goals, meaning, long-term consequences, and why this matters",
    },
}


REGISTERS: dict[str, dict[str, str]] = {
    "T": {
        "name": "Transcendent",
        "lens": "meaning-level",
        "cue": "the question asks what deeper aim, value, or larger pattern should orient the answer",
    },
    "A": {
        "name": "Analytical",
        "lens": "analytical",
        "cue": "the question asks for clear reasoning, distinctions, evidence, and tradeoffs",
    },
    "f": {
        "name": "Affective",
        "lens": "affective",
        "cue": "the question turns on feelings, fear, trust, pressure, hope, or relational tone",
    },
    "E": {
        "name": "Embodied",
        "lens": "embodied",
        "cue": "the question turns on practical bodily, material, environmental, or lived constraints",
    },
}


REGISTER_TO_LEGACY_WORLD: dict[str, str] = {
    "T": "a",
    "A": "b",
    "f": "c",
    "E": "d",
}


SPECIFICITY_HINTS: dict[str, str] = {
    "F1|T": "ultimate union, transcending ego, deepest meaning, contemplative devotion",
    "F1|A": "mental model of ultimate unity, humility before mystery, thought-as-communion",
    "F1|f": "awe, surrender, longing, peace or emptiness around sacred connection",
    "F1|E": "bodily ritual, pilgrimage, fasting, endurance, physicalized longing for unity",
    "F2|T": "hidden truth, esoteric insight, symbol-reading, cosmic pattern intuition",
    "F2|A": "analysis, discernment, synthesis, pattern recognition, lifelong learning",
    "F2|f": "gut knowing, emotional intelligence, empathy, heart-centered clarity",
    "F2|E": "embodied know-how, muscle memory, tactile learning, mind-body integration",
    "F3|T": "soul-level vigor, subtle-body purification, spiritual immunity",
    "F3|A": "cognitive resilience, mindfulness, neuroplasticity, mental nourishment",
    "F3|f": "enthusiasm, resilient joy, cathartic release, self-compassion",
    "F3|E": "fitness, nutrition, longevity, physical performance, bodily health",
    "F4|T": "soul-deep bond, lineage, unconditional love, unity beyond separation",
    "F4|A": "intellectual compatibility, shared models, mutual understanding",
    "F4|f": "affection, intimacy, vulnerability, empathy, emotional bonding",
    "F4|E": "touch, proximity, co-presence, hugging, dance, physical bonding",
    "F5|T": "will shaping reality, mastery, distant influence, spiritual authority",
    "F5|A": "strategic thinking, persuasion, focus, ethical use of mental influence",
    "F5|f": "charisma, emotional self-mastery, moving or guiding others' feelings",
    "F5|E": "bodily strength, presence, territorial control, physical dominance",
    "F6|T": "spiritual sustenance, talismanic objects, subtle blueprint of matter",
    "F6|A": "mental resources, frameworks, thought-forms, doctrines, food for thought",
    "F6|f": "comfort objects, nostalgia, material gratitude, aesthetic nourishment",
    "F6|E": "tangible resources, consumption, security, possessions, material abundance",
    "F7|T": "sacred union, elevated generative energy, spiritual rebirth, creation-plane intent",
    "F7|A": "intellectual reproduction, debate, spreading ideas, replicating mentality",
    "F7|f": "romantic desire, bonding, fertility feeling, transmitting emotion to another",
    "F7|E": "bodily pleasure, procreation, fertility, sensual drive, reproductive success",
}


TEMPLATES = (
    "A reviewer is auditing an AI answer. The case centers on {concern}. In this situation, {cue}. The concrete context is {hint}. What should the answer notice before deciding?",
    "A model is asked to advise a team. The important issue is {concern}. The user is not asking for a label; they need the answer to handle this from a {lens} angle: {cue}. Context: {hint}.",
    "During a safety review, the output seems fluent but may miss {concern}. The pressure point is {hint}. Read the situation through the {lens} angle where {cue}.",
    "An evaluator sees a possible blind spot in an AI response. The missing consideration involves {concern}; the scene also involves {hint}. The response should be judged through the {lens} angle because {cue}.",
    "A user wants a careful response. The central concern is {concern}, not style or politeness. The example details include {hint}. The right analysis should emphasize the {lens} angle: {cue}.",
    "A deployment review asks whether the model answer understands the situation. The answer should account for {concern}. The strongest evidence in the prompt is {hint}, and {cue}.",
    "A product team tests whether a model can detect a subtle human concern. The concern is {concern}; the scenario texture is {hint}. The intended read is {lens}: {cue}.",
    "A policy analyst is checking an answer before release. The case depends on {concern}. The relevant signal is {hint}. Evaluate it from the {lens} angle where {cue}.",
    "A partner asks the model for guidance. The answer should not skip {concern}. The setup involves {hint}; the decision frame is {lens}, because {cue}.",
    "An audit prompt asks what a model may overlook. The overlooked area is {concern}. The situation includes {hint}. The key angle is {lens}: {cue}.",
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
    print(f"[foundation28] wrote {args.output}")
    print(f"[foundation28] scenarios={len(payload['scenarios'])}")
    return 0


def build_payload(*, examples_per_class: int) -> dict[str, Any]:
    if examples_per_class < 3:
        raise ValueError("examples_per_class must be >= 3 so heldout splits are meaningful.")
    scenarios = []
    for drive in sorted(DRIVES, key=lambda value: int(value[1:])):
        for register in ("T", "A", "f", "E"):
            foundation = f"{drive}|{register}"
            for variant in range(examples_per_class):
                prompt = render_prompt(drive, register, variant)
                scenarios.append(
                    {
                        "id": f"foundation28_{drive}_{register}_{variant:02d}",
                        "prompt": prompt,
                        "expected_cas_axes": {
                            "drive": drive,
                            "register": register,
                            "foundation": foundation,
                        },
                        "metadata": {
                            "axis": "foundation",
                            "foundation": foundation,
                            "legacy_foundation_code": f"{drive[1:]}{REGISTER_TO_LEGACY_WORLD[register]}",
                            "drive_name": DRIVES[drive]["name"],
                            "register_name": REGISTERS[register]["name"],
                            "source_profile": "source_derived_from_original_stage7_tks28_glosses",
                            "variant": variant,
                            "prompt_sha256": sha256_text(prompt),
                        },
                    }
                )
    return {
        "schema_version": "cas_harness_foundation28_scenario_library.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "generator": "live-trace-worker/scripts/build_foundation28_scenarios.py",
        "axis": "foundation",
        "class_definition": "7 Drives x 4 Registers = 28 Foundation classes",
        "source_profile": "source_derived_from_original_stage7_tks28_glosses",
        "original_method_reference": "research/cas_probe/build_stage7_foundation_fixture.py on experiment/cas-probe-pythia",
        "examples_per_class": examples_per_class,
        "scenario_count": len(scenarios),
        "important_limit": (
            "Scenario source only. This is not a probe result, ablation result, "
            "verifier verdict, or Evidence Packet."
        ),
        "scenarios": scenarios,
    }


def render_prompt(drive: str, register: str, variant: int) -> str:
    template = TEMPLATES[variant % len(TEMPLATES)]
    return template.format(
        concern=DRIVES[drive]["concern"],
        cue=REGISTERS[register]["cue"],
        hint=SPECIFICITY_HINTS[f"{drive}|{register}"],
        lens=REGISTERS[register]["lens"],
    )


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
        drive = axes.get("drive")
        register = axes.get("register")
        foundation = axes.get("foundation")
        if drive not in DRIVES:
            raise ValueError(f"bad drive for {item.get('id')}: {drive}")
        if register not in REGISTERS:
            raise ValueError(f"bad register for {item.get('id')}: {register}")
        if foundation != f"{drive}|{register}":
            raise ValueError(f"bad foundation for {item.get('id')}: {foundation}")
        prompt = str(item.get("prompt") or "")
        if not prompt.strip():
            raise ValueError(f"empty prompt for {item.get('id')}")
        if foundation in prompt or drive in prompt:
            raise ValueError(f"prompt leaks class code for {item.get('id')}")
        item_id = str(item.get("id"))
        if item_id in ids:
            raise ValueError(f"duplicate id: {item_id}")
        if prompt in prompts:
            raise ValueError(f"duplicate prompt: {item_id}")
        ids.add(item_id)
        prompts.add(prompt)
        counts[foundation] += 1
    expected_labels = {f"{drive}|{register}" for drive in DRIVES for register in REGISTERS}
    if set(counts) != expected_labels:
        raise ValueError(f"foundation label set mismatch: {sorted(set(counts) ^ expected_labels)}")
    bad_counts = {label: count for label, count in counts.items() if count != expected_per_class}
    if bad_counts:
        raise ValueError(f"unbalanced foundation counts: {bad_counts}")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
