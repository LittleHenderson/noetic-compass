"""Pure, independently checked two-condition training data.

This is a bounded experimental task carried by the existing four-symbol
DECOMPOSITION_SIGNAL output. It does not define new Noetic semantics or prove
native execution, persistence, repair, language understanding, or learning.
No file writes, tensor libraries, database connections, or provider calls occur.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from math import gcd
import random


SCHEMA = "cas-meta2-condition-skill-public/9"
REPORT_SCHEMA = "cas-meta2-condition-skill-data-validation/9"
DIRECTIONS = ("at_least", "at_most")
ALLOWED_DIRECTION_PAIRS = (
    ("at_least", "at_least"),
    ("at_least", "at_most"),
    ("at_most", "at_most"),
)
HELD_OUT_DIRECTION_PAIR = ("at_most", "at_least")
SPLITS = ("train", "validation", "test_instances", "test_direction_pair")
COUNTS = {"train": 1536, "validation": 384,
          "test_instances": 384, "test_direction_pair": 384}
PER_LABEL_PAIR = {"train": 128, "validation": 32,
                  "test_instances": 32, "test_direction_pair": 96}
MAX_GENERATION_ATTEMPTS = 250_000
VALUE_MIN, VALUE_MAX = -15, 15
LIMIT_MIN, LIMIT_MAX = -7, 7
MAX_MARGIN = 8
BOUNDARY = (
    "Pure input-dependent comparison targets and split/encoding checks only. "
    "No native execution, neural learning, persistence, repair, language "
    "understanding, CAS-specific advantage, or new Noetic semantics proved."
)


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _digest(value):
    return sha256(_canonical(value)).hexdigest()


def _checked_conditions(conditions):
    _require(type(conditions) is list and len(conditions) == 2, "CONDITION_COUNT")
    slots = []
    for row in conditions:
        _require(type(row) is dict and set(row) ==
                 {"slot", "value", "limit", "direction"}, "CONDITION_FIELDS")
        _require(type(row["slot"]) is int and row["slot"] in (1, 2), "CONDITION_SLOT")
        for key in ("value", "limit"):
            _require(type(row[key]) is int and VALUE_MIN <= row[key] <= VALUE_MAX,
                     "CONDITION_INTEGER_RANGE:" + key)
        _require(type(row["direction"]) is str and row["direction"] in DIRECTIONS,
                 "CONDITION_DIRECTION")
        slots.append(row["slot"])
    _require(sorted(slots) == [1, 2], "CONDITION_SLOTS_NOT_UNIQUE")
    return conditions


def _public(conditions):
    conditions = deepcopy(_checked_conditions(conditions))
    body = {"schema": SCHEMA, "conditions": conditions}
    return {**body, "task_id": "condition-" + _digest(body)}


def validate_public(public):
    """Reject target fields, unsupported types and an unbound public identity."""
    _require(type(public) is dict and set(public) ==
             {"schema", "task_id", "conditions"}, "PUBLIC_FIELDS")
    _require(public["schema"] == SCHEMA, "PUBLIC_SCHEMA")
    _checked_conditions(public["conditions"])
    body = {"schema": public["schema"], "conditions": public["conditions"]}
    _require(type(public["task_id"]) is str and
             public["task_id"] == "condition-" + _digest(body), "PUBLIC_IDENTITY")
    return public


def features(public):
    """Return only the original values, limits, slot tags and public queries.

    Physical row order is preserved. No target, difference, comparison result,
    split identity, task ID, or family ID enters these eight input features.
    All constants are exactly representable dyadic fractions.
    """
    validate_public(public)
    return [[row["value"] / 128, row["limit"] / 128, float(row["slot"]),
             0.5 if row["direction"] == "at_least" else -0.5]
            for row in public["conditions"]]


def oracle(public):
    """Independent teacher: compare the ORIGINAL integers, not features.

    Equality passes both directions. Bits are in semantic slot order, never
    physical row order. This does not inspect any model output.
    """
    validate_public(public)
    bits = [None, None]
    for row in public["conditions"]:
        if row["direction"] == "at_least":
            passes = row["value"] >= row["limit"]
        else:
            passes = row["value"] <= row["limit"]
        bits[row["slot"] - 1] = int(passes)
    index = bits[0] * 2 + bits[1]
    return {"class_index": index, "symbol": "L" + str(index), "bits": bits}


def condition_margins(public):
    """Pure per-condition margin classes for equality/unit-margin reporting.

    Equality (value == limit) and one-unit margin (|value - limit| == 1) are
    counted separately, matching the curriculum's reporting cells. This derives
    nothing from any model output or private target.
    """
    validate_public(public)
    return {"equality_conditions": sum(row["value"] == row["limit"]
                                       for row in public["conditions"]),
            "unit_margin_conditions": sum(abs(row["value"] - row["limit"]) == 1
                                          for row in public["conditions"])}


def direction_pair(public):
    validate_public(public)
    return tuple(row["direction"] for row in
                 sorted(public["conditions"], key=lambda row: row["slot"]))


def family_key(public):
    """Atomic family ignores direction, sign, slots and physical row order."""
    validate_public(public)
    return sorted([[row["limit"], abs(row["value"] - row["limit"])]
                   for row in public["conditions"]])


def family_id(public):
    return _digest(family_key(public))


def family_split(public):
    bucket = int(family_id(public), 16) % 10
    return ("train" if bucket <= 6 else
            {7: "validation", 8: "test_instances", 9: "test_direction_pair"}[bucket])


def _semantic_example_id(public):
    return _digest(sorted(public["conditions"], key=lambda row: row["slot"]))


def _generated_domain(public):
    return all(LIMIT_MIN <= row["limit"] <= LIMIT_MAX and
               abs(row["value"] - row["limit"]) <= MAX_MARGIN
               for row in public["conditions"])


def validate_task(task):
    _require(type(task) is dict and set(task) ==
             {"public", "target", "provenance"}, "TASK_FIELDS")
    public = validate_public(task["public"])
    _require(_generated_domain(public), "GENERATED_DOMAIN")
    target = task["target"]
    _require(type(target) is dict and set(target) ==
             {"class_index", "symbol", "bits"}, "TARGET_FIELDS")
    _require(type(target["class_index"]) is int and
             target["class_index"] in range(4), "TARGET_INDEX")
    _require(type(target["symbol"]) is str, "TARGET_SYMBOL")
    _require(type(target["bits"]) is list and len(target["bits"]) == 2 and
             all(type(bit) is int and bit in (0, 1) for bit in target["bits"]),
             "TARGET_BITS")
    _require(target == oracle(public), "INDEPENDENT_TARGET_MISMATCH")
    provenance = task["provenance"]
    _require(type(provenance) is dict and set(provenance) ==
             {"split", "family_id"}, "PROVENANCE_FIELDS")
    split = provenance["split"]
    _require(type(split) is str and split in SPLITS, "SPLIT_NAME")
    _require(provenance["family_id"] == family_id(public), "FAMILY_IDENTITY")
    _require(split == family_split(public), "FAMILY_BUCKET_MISMATCH")
    pairs = ((HELD_OUT_DIRECTION_PAIR,) if split == "test_direction_pair"
             else ALLOWED_DIRECTION_PAIRS)
    _require(direction_pair(public) in pairs, "DIRECTION_PAIR_SPLIT_LEAKAGE")
    return task


def controls(public):
    """Evaluator-only public variants; no private targets or training additions.

    Crossings reflect value about the unchanged limit, preserving its atomic
    family. A zero-margin equality stays unchanged, explicitly not a bit-flip
    control. Generated-domain bounds ensure every reflection remains in range.
    """
    validate_public(public)
    _require(_generated_domain(public), "CONTROL_REQUIRES_GENERATED_DOMAIN")
    rows = public["conditions"]
    result = {"physical_row_reverse": _public(list(reversed(rows)))}
    swapped = deepcopy(rows)
    for row in swapped:
        row["slot"] = 3 - row["slot"]
    result["slot_reassignment"] = _public(swapped)
    for slot in (1, 2):
        changed = deepcopy(rows)
        row = next(row for row in changed if row["slot"] == slot)
        row["direction"] = ("at_most" if row["direction"] == "at_least" else "at_least")
        result[f"direction_{slot}_reverse"] = _public(changed)
        changed = deepcopy(rows)
        row = next(row for row in changed if row["slot"] == slot)
        row["value"] = 2 * row["limit"] - row["value"]
        result[f"threshold_{slot}_crossing"] = _public(changed)
    _require(all(family_id(item) == family_id(public) for item in result.values()),
             "CONTROL_CHANGED_FAMILY")
    return result


def _centered_ray(row):
    """Exact positive-affine signature, conservatively ignoring LN epsilon."""
    total = sum(row)
    centered = tuple(4 * value - total for value in row)
    divisor = 0
    for value in centered:
        divisor = gcd(divisor, abs(value))
    _require(divisor > 0, "CONSTANT_ROW_ENCODING")
    # Do not remove the sign: LayerNorm is not invariant to negative scaling.
    return tuple(value // divisor for value in centered)


def representation_collision_check():
    """Enumerate ALL 3,844 allowed rows using integers only, not tensors.

    Uniqueness also excludes conflicting two-row multisets when semantic slot
    IDs travel with each row. This is not a floating-point or capacity test.
    """
    signatures, count, collisions, conflicts = {}, 0, 0, 0
    for slot in (1, 2):
        for direction in (-1, 1):
            for value in range(VALUE_MIN, VALUE_MAX + 1):
                for limit in range(VALUE_MIN, VALUE_MAX + 1):
                    signature = _centered_ray((value, limit, 128 * slot, 64 * direction))
                    meaning = (slot, direction, value, limit)
                    prior = signatures.get(signature)
                    if prior is not None:
                        collisions += 1
                        if prior != meaning:
                            conflicts += 1
                    else:
                        signatures[signature] = meaning
                    count += 1
    return {"method": "exact_integer_centered_positive_affine_ray",
            "row_count": count, "unique_signatures": len(signatures),
            "signature_collisions": collisions, "conflicting_row_meanings": conflicts,
            "neural_learnability_tested": False, "tensor_execution": False}


def validate_curriculum(curriculum):
    _require(type(curriculum) is dict and set(curriculum) == set(SPLITS), "CURRICULUM_SPLITS")
    task_ids, examples, family_owners, encoded_meanings = set(), set(), {}, {}
    split_reports = {}
    for split in SPLITS:
        tasks = curriculum[split]
        _require(type(tasks) is list and len(tasks) == COUNTS[split], "SPLIT_COUNT:" + split)
        labels, pairs, cells, families = Counter(), Counter(), Counter(), set()
        equality, near_boundary, rows_in_slot_order = 0, 0, 0
        pairs_expected = ((HELD_OUT_DIRECTION_PAIR,) if split == "test_direction_pair"
                          else ALLOWED_DIRECTION_PAIRS)
        for task in tasks:
            validate_task(task)
            public, target, provenance = task["public"], task["target"], task["provenance"]
            _require(provenance["split"] == split, "TASK_SPLIT_PLACEMENT")
            identity, example, family = public["task_id"], _semantic_example_id(public), family_id(public)
            _require(identity not in task_ids and example not in examples, "DUPLICATE_TASK")
            task_ids.add(identity)
            examples.add(example)
            _require(family not in family_owners or family_owners[family] == split,
                     "CROSS_SPLIT_FAMILY_LEAKAGE")
            family_owners[family] = split
            families.add(family)
            label, pair = target["class_index"], direction_pair(public)
            labels[label] += 1
            pairs[pair] += 1
            cells[(label, pair)] += 1
            numeric = features(public)
            signature = tuple(sorted(_centered_ray(tuple(round(value * 128) for value in row))
                                     for row in numeric))
            _require(signature not in encoded_meanings or encoded_meanings[signature] == label,
                     "CONFLICTING_ENCODED_TARGETS")
            encoded_meanings[signature] = label
            equality += sum(row["value"] == row["limit"] for row in public["conditions"])
            near_boundary += sum(abs(row["value"] - row["limit"]) == 1
                                 for row in public["conditions"])
            rows_in_slot_order += public["conditions"][0]["slot"] == 1
        _require(all(cells[(label, pair)] == PER_LABEL_PAIR[split]
                     for label in range(4) for pair in pairs_expected),
                 "UNBALANCED_LABEL_DIRECTION_CELLS:" + split)
        split_reports[split] = {
            "tasks": len(tasks), "conditions": 2 * len(tasks), "families": len(families),
            "label_counts": {str(label): labels[label] for label in range(4)},
            "direction_pair_counts": {"|".join(pair): pairs[pair] for pair in pairs_expected},
            "label_direction_pair_counts": {str(label) + ":" + "|".join(pair): cells[(label, pair)]
                                            for label in range(4) for pair in pairs_expected},
            "equality_conditions": equality, "unit_margin_conditions": near_boundary,
            "physical_slot_order_counts": {"1,2": rows_in_slot_order,
                                           "2,1": len(tasks) - rows_in_slot_order},
            "constant_class_correct": max(labels.values()),
            "constant_class_attempted": len(tasks), "constant_class_accuracy": 0.25,
            "evaluation_target": ("unseen ordered direction pair and fresh atomic families"
                                  if split == "test_direction_pair" else
                                  "fresh atomic families with familiar ordered direction pairs"),
        }
    collision = representation_collision_check()
    _require(collision["signature_collisions"] == 0 and collision["conflicting_row_meanings"] == 0,
             "ROW_REPRESENTATION_COLLISION")
    return {"schema": REPORT_SCHEMA, "total_tasks": len(task_ids),
            "total_families": len(family_owners), "splits": split_reports,
            "cross_split_family_overlap": 0, "duplicate_semantic_tasks": 0,
            "conflicting_encoded_targets": 0, "representation": collision,
            "curriculum_sha256": _digest(curriculum), "boundary": BOUNDARY,
            "native_execution": False, "neural_execution": False}


def build_curriculum(seed=9):
    """Construct targets first, surface rows second, independently check last.

    The fixed attempt ceiling prevents a pathological seed/configuration from
    generating indefinitely. This returns data in memory; it writes no files.
    """
    _require(type(seed) is int and 0 <= seed < 2 ** 32, "SEED_RANGE")
    rng = random.Random(seed)
    curriculum = {split: [] for split in SPLITS}
    examples, attempts = set(), 0
    for split in SPLITS:
        pairs = ((HELD_OUT_DIRECTION_PAIR,) if split == "test_direction_pair"
                 else ALLOWED_DIRECTION_PAIRS)
        for index in range(4):
            target = {"class_index": index, "symbol": "L" + str(index),
                      "bits": [index // 2, index % 2]}
            for pair in pairs:
                accepted = 0
                while accepted < PER_LABEL_PAIR[split]:
                    _require(attempts < MAX_GENERATION_ATTEMPTS, "GENERATION_ATTEMPT_LIMIT")
                    attempts += 1
                    rows = []
                    for slot, (direction, bit) in enumerate(zip(pair, target["bits"]), 1):
                        limit = rng.randint(LIMIT_MIN, LIMIT_MAX)
                        magnitude = rng.randint(0 if bit else 1, MAX_MARGIN)
                        sign = (1 if direction == "at_least" else -1) * (1 if bit else -1)
                        rows.append({"slot": slot, "value": limit + sign * magnitude,
                                     "limit": limit, "direction": direction})
                    rng.shuffle(rows)
                    public = _public(rows)
                    example = _semantic_example_id(public)
                    if family_split(public) != split or example in examples:
                        continue
                    task = {"public": public, "target": deepcopy(target),
                            "provenance": {"split": split, "family_id": family_id(public)}}
                    validate_task(task)
                    examples.add(example)
                    curriculum[split].append(task)
                    accepted += 1
        rng.shuffle(curriculum[split])
    validate_curriculum(curriculum)
    return curriculum
