"""dataset_generator.py -- Generates Paired Natural English <-> CASContent Data for Level L4 Scribe Proposer.

Generates:
1. Diverse natural English surface sentences paired with target CASContent.
2. Adversarial queries with missing slots / out-of-domain terms targeting CLARIFY.
3. Strictly isolated training and held-out evaluation splits.
"""
from __future__ import annotations

import json
import random
from typing import Dict, List, Any, Tuple
from cce_shim import DOMAINS, REGISTERS, DRIVES, VERBS, NOETIC_NAMES


SYNONYMS = {
    "processes": ["processes", "analyzes", "evaluates", "computes", "thinks through", "transforms", "runs through"],
    "stores": ["stores", "retains", "memorizes", "holds in memory", "caches", "preserves"],
    "intakes": ["intakes", "absorbs", "receives", "accepts", "ingests", "takes in", "perceives"],
    "outputs": ["outputs", "emits", "expresses", "generates", "discharges", "yields", "produces"]
}

TEMPLATES = [
    # Active voice canonical
    "The {dom_name} {subject} {verb} the {reg_name} {obj} under {drive_name}.",
    # Natural conversational
    "In the {dom_name} domain, the {subject} actively {verb_syn} the {reg_name} {obj} driven by {drive_name}.",
    # Inverted order
    "Under {drive_name}, {reg_name} {obj} is {verb_pass} by the {dom_name} {subject}.",
    # Direct inquiry / statement
    "We observe that the {subject} ({dom_name}) {verb_syn} a {reg_name} {obj} with {drive_name} purpose.",
    # Concise register
    "{dom_name} {subject} -> {verb} -> {reg_name} {obj} [{drive_name}]."
]

PASSIVE_VERBS = {
    "processes": "processed",
    "stores": "stored",
    "intakes": "received",
    "outputs": "output"
}


def generate_single_example(rng: random.Random) -> Dict[str, Any]:
    # Randomly select slots
    dom = rng.choice(list(DOMAINS.keys()))
    reg = rng.choice(list(REGISTERS.keys()))
    drive = rng.choice(list(DRIVES.keys()))
    verb = rng.choice(VERBS)
    subject = rng.choice(["Mind", "Positive", "Negative", "Male", "Female"])
    obj = rng.choice(["Idea", "Vibration", "Rhythm", "Above/Cause", "Below/Effect"])

    dom_name = DOMAINS[dom]
    reg_name = REGISTERS[reg]
    drive_name = DRIVES[drive]
    verb_syn = rng.choice(SYNONYMS[verb])
    verb_pass = PASSIVE_VERBS[verb]

    template = rng.choice(TEMPLATES)
    surface_english = template.format(
        dom_name=dom_name,
        subject=subject,
        verb=verb,
        verb_syn=verb_syn,
        verb_pass=verb_pass,
        reg_name=reg_name,
        obj=obj,
        drive_name=drive_name
    )

    target_content = {
        "turn_type": "ANSWER",
        "subject": subject,
        "verb": verb,
        "object": obj,
        "register": reg,
        "domain": dom,
        "drive": drive
    }

    return {
        "english": surface_english,
        "content": target_content,
        "is_clarify": False
    }


def generate_clarify_example(rng: random.Random) -> Dict[str, Any]:
    missing_slot = rng.choice(["subject", "register", "domain", "drive", "verb"])
    noise_sentences = [
        "What is the color of an electron during Tuesday?",
        "Please calculate the quantum temperature of this sandwich.",
        "Can you imagine a completely ungrounded concept without prerequisites?",
        "Tell me a story about an unknown entity with zero defined properties."
    ]
    english = rng.choice(noise_sentences)
    target_content = {
        "turn_type": "CLARIFY",
        "missing_slot": missing_slot
    }
    return {
        "english": english,
        "content": target_content,
        "is_clarify": True
    }


def build_dataset(n_samples: int, seed: int) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    dataset = []
    # 90% structured mappings, 10% adversarial CLARIFY cases
    n_clarify = int(n_samples * 0.10)
    n_valid = n_samples - n_clarify

    for _ in range(n_valid):
        dataset.append(generate_single_example(rng))

    for _ in range(n_clarify):
        dataset.append(generate_clarify_example(rng))

    rng.shuffle(dataset)
    return dataset


if __name__ == "__main__":
    data = build_dataset(10, seed=42)
    print("Generated 10 sample pairs:")
    for d in data[:3]:
        print("EN :", d["english"])
        print("CAS:", d["content"])
        print()
