"""Teacher-side construction and split validation; exclude from training workers.

Worker-safe rendering lives in lesson_contract. These re-exports preserve the
existing preparation API and the exact prepared cases and lesson bytes.
"""
from __future__ import annotations

import random

from .lesson_contract import (
    SCHEMA, STAGES, CASE_FIELDS, TeachingDataError, _require, _family_id,
    _case_check, recover_binding, make_public, make_cycle, validate_cycle,
    fit_tokenizer,
)

SPLIT_COUNTS = {"train": 256, "development": 64, "test_fresh": 64,
                "test_context": 64, "test_names": 64}
COLORS = ("amber", "blue", "green", "violet")
SHAPES = ("circle", "square", "triangle", "star")
TRAIN_TAGS = tuple(f"{color} {shape}" for color, shape in zip(COLORS, SHAPES))
NEW_TAGS = tuple(f"{color} {shape}" for color in COLORS for shape in SHAPES
                 if f"{color} {shape}" not in TRAIN_TAGS)
TRAIN_CONTEXTS = ("school workshop", "harbor kitchen", "garden station", "market studio")
NEW_CONTEXTS = ("school kitchen", "harbor workshop", "garden studio", "market station")
EVALUATION_TARGETS = {
    "train": "Teaching only; known tags and context combinations.",
    "development": "Fresh numeric instances; readiness/checkpoint selection, not mastery.",
    "test_fresh": "Fresh numeric instances of familiar task forms, tags and contexts.",
    "test_context": "Unseen irrelevant context combinations made from known words.",
    "test_names": "Unseen color-plus-shape tag combinations made from known words.",
}


def build_dataset(seed=20260908):
    _require(type(seed) is int and 0 <= seed < 2**63, "SEED_INVALID")
    rng = random.Random(seed)
    splits = {}
    for split, count in SPLIT_COUNTS.items():
        tags = NEW_TAGS if split == "test_names" else TRAIN_TAGS
        contexts = NEW_CONTEXTS if split == "test_context" else TRAIN_CONTEXTS
        bindings = [index % 3 for index in range(count)]
        rng.shuffle(bindings)
        cases = []
        for index, binding in enumerate(bindings):
            chosen = rng.sample(tags, 3)
            observations = [{"slot": slot, "tag": chosen[slot],
                "values": [rng.randint(-8192, 8192) / 8192.0 for _ in range(8)]} for slot in range(3)]
            case = {"split": split, "fixed_child": "A", "requested_tag": chosen[binding],
                    "context": contexts[index % len(contexts)], "observations": observations,
                    "wording": index % 3, "target_binding": binding}
            case["family_id"] = _family_id(case)
            cases.append(case)
        splits[split] = cases
    dataset = {"schema": SCHEMA, "status": "PLANNED_NOT_DELIVERED", "seed": seed,
               "counts": dict(SPLIT_COUNTS), "evaluation_targets": dict(EVALUATION_TARGETS), "splits": splits}
    validate_dataset(dataset)
    return dataset



def validate_dataset(dataset):
    _require(type(dataset) is dict and set(dataset) ==
             {"schema", "status", "seed", "counts", "evaluation_targets", "splits"}, "DATASET_FIELDS_INVALID")
    _require(dataset["schema"] == SCHEMA and dataset["status"] == "PLANNED_NOT_DELIVERED", "DATASET_STATUS_INVALID")
    _require(type(dataset["seed"]) is int and 0 <= dataset["seed"] < 2**63, "SEED_INVALID")
    _require(dataset["counts"] == SPLIT_COUNTS and dataset["evaluation_targets"] == EVALUATION_TARGETS,
             "SPLIT_DECLARATION_DRIFT")
    _require(type(dataset["splits"]) is dict and set(dataset["splits"]) == set(SPLIT_COUNTS), "SPLITS_INVALID")
    seen = set()
    for split, count in SPLIT_COUNTS.items():
        cases = dataset["splits"][split]
        _require(type(cases) is list and len(cases) == count, "SPLIT_COUNT_MISMATCH")
        balance = [0, 0, 0]
        for case in cases:
            _case_check(case)
            _require(case["split"] == split, "SPLIT_CASE_MISMATCH")
            _require(case["family_id"] not in seen, "FORMAL_FAMILY_LEAKAGE")
            seen.add(case["family_id"])
            _require(case["context"] in (NEW_CONTEXTS if split == "test_context" else TRAIN_CONTEXTS), "CONTEXT_SPLIT_LEAKAGE")
            _require(all(row["tag"] in (NEW_TAGS if split == "test_names" else TRAIN_TAGS)
                         for row in case["observations"]), "NAME_SPLIT_LEAKAGE")
            balance[case["target_binding"]] += 1
            make_public(case)
        _require(max(balance) - min(balance) <= 1, "BINDING_BALANCE_INVALID")
    return True
