"""Finite, checked input-binding lessons. Preparation is not delivered teaching.

The student chooses BIND0/1/2 for a fixed RUN A skeleton. This does not teach
or verify A's neural effect, general language, or unrestricted analogy use.
Formal cases precede rendering; the recovery checker reads public text/tags
without consulting the stored answer. All seven views stay in one split.
"""
from __future__ import annotations

from copy import deepcopy
import random
import re

from ..codec import canonical_sha256, validate_public
from ..features_v2 import LosslessPublicTokenizer

SCHEMA = "cas-meta2-teaching-cycle-data/1"
STAGES = ("name_function", "context", "analogy", "mapping", "decomposition",
          "recomposition", "reinforcement")
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
CASE_FIELDS = {"family_id", "split", "fixed_child", "requested_tag", "context",
               "observations", "wording", "target_binding"}


class TeachingDataError(ValueError):
    pass


def _require(condition, code):
    if not condition:
        raise TeachingDataError(code)


def _family_id(case):
    # Ignore surface/context changes: rewording one formal example cannot move it.
    return canonical_sha256({key: case[key] for key in
                             ("fixed_child", "requested_tag", "observations")})


def recover_binding(public):
    """Independent finite-language checker, not a student or gold lookup."""
    validate_public(public)
    requests = re.findall(r"Requested source: ([a-z]+ [a-z]+)\.", public["problem"])
    _require(len(requests) == 1, "REQUEST_NOT_UNIQUE")
    matches = [row["slot"] for row in public["observations"] if row["tag"] == requests[0]]
    _require(len(matches) == 1, "REQUEST_SOURCE_NOT_UNIQUE")
    return matches[0]


def _case_check(case):
    _require(type(case) is dict and set(case) == CASE_FIELDS, "CASE_FIELDS_INVALID")
    _require(case["split"] in SPLIT_COUNTS and case["fixed_child"] == "A", "CASE_SCOPE_INVALID")
    _require(type(case["wording"]) is int and 0 <= case["wording"] < 3, "WORDING_INVALID")
    _require(type(case["target_binding"]) is int and case["target_binding"] in (0, 1, 2), "TARGET_INVALID")
    _require(case["context"] in TRAIN_CONTEXTS + NEW_CONTEXTS, "CONTEXT_INVALID")
    _require(type(case["requested_tag"]) is str and case["requested_tag"] in TRAIN_TAGS + NEW_TAGS,
             "REQUEST_TAG_INVALID")
    validate_public({"problem": "Check.", "observations": case["observations"]})
    tags = [row["tag"] for row in case["observations"]]
    _require(len(set(tags)) == 3 and all(tag in TRAIN_TAGS + NEW_TAGS for tag in tags), "TAGS_INVALID")
    _require(case["family_id"] == _family_id(case), "FAMILY_ID_MISMATCH")
    matches = [row["slot"] for row in case["observations"] if row["tag"] == case["requested_tag"]]
    _require(matches == [case["target_binding"]], "FORMAL_TARGET_MISMATCH")


def make_public(case):
    """Unassisted problem and permitted observations; no answer, IDs or lesson."""
    _case_check(case)
    wording = (
        "Choose the observation that supplies child A's argument.",
        "Bind one observation to the input of child A.",
        "Select the source for the fixed child A call.",
    )[case["wording"]]
    public = {"problem": f"In the {case['context']}. {wording} Requested source: {case['requested_tag']}.",
              "observations": deepcopy(case["observations"])}
    _require(recover_binding(public) == case["target_binding"], "PUBLIC_RECOVERY_MISMATCH")
    return public


def _alignment(case):
    tag = case["requested_tag"]
    slot = case["target_binding"]
    return [
        {"role": "receiver", "technical": "child A argument", "context": "workplace receiver",
         "analogy": "parcel destination"},
        {"role": "source", "technical": tag, "context": f"container marked {tag}",
         "analogy": f"parcel marked {tag}"},
        {"role": "connection", "technical": f"slot {slot} supplies argument",
         "context": "marked container reaches receiver", "analogy": "addressed parcel reaches destination"},
    ]


def _lesson(case, stage, curriculum):
    if curriculum == "ordinary":
        return ("Input binding selects the observation named by the request. "
                "Read the request, compare the observation tags, and choose its slot.")
    prompts = {
        "name_function": "Input binding assigns the required source to child A's argument. Name the source and its role.",
        "context": "The workplace may change without changing the source. A changed requested tag can change the source. Which change matters?",
        "analogy": "An addressed parcel must reach its destination. Likewise the named observation must reach child A's argument. What is shared?",
        "mapping": "Technical, context, analogy: argument, receiver, destination; observation, marked container, marked parcel; binding, delivery, arrival. Keep each role matched one to one.",
        "decomposition": "Guided Noetic ^6: separate request, sources, slots and argument. Which dependency breaks if the named source is removed or another is substituted?",
        "recomposition": "Rebuild the process: read the request, locate the marked source, connect its slot to the argument, then call the fixed child.",
        "reinforcement": "The common rule is unchanged: the intended operation receives the required source in the required role. Repeat this connection across the views.",
    }
    return prompts[stage]


def make_cycle(case, assistance="full", curriculum="aligned"):
    """Seven planned training views; ordinary control is not a seven-stage cycle.

    Each rendered view reaches the existing public text input, not metadata alone.
    Full guidance includes worked answers. Faded guidance retains a source hint.
    No assistance keeps only the stage prompt and unassisted problem.
    """
    _case_check(case)
    _require(case["split"] == "train", "TEACHING_CYCLE_TRAIN_ONLY")
    _require(assistance in ("full", "faded", "none"), "ASSISTANCE_INVALID")
    _require(curriculum in ("aligned", "ordinary"), "CURRICULUM_INVALID")
    records = []
    for index, stage in enumerate(STAGES):
        public = make_public(case)
        lesson = _lesson(case, stage, curriculum)
        if assistance == "full":
            lesson += (f" Worked answer: BIND{case['target_binding']}. The tag {case['requested_tag']} "
                       f"is at slot {case['target_binding']}; that slot supplies the argument.")
            if curriculum == "aligned" and stage == "context":
                alternate = next(row for row in case["observations"] if row["slot"] != case["target_binding"])
                lesson += (f" Changing workplace keeps this binding. Changing the request to {alternate['tag']} "
                           f"instead requires slot {alternate['slot']}.")
            if curriculum == "aligned" and stage == "mapping":
                lesson += f" One-to-one source map: {case['requested_tag']} = marked container = marked parcel."
            if curriculum == "aligned" and stage == "decomposition":
                lesson += (" Removing the named source leaves no valid binding. A different tag breaks the "
                           "request-to-source link. The eight values are payload; the slot identifies its location.")
        elif assistance == "faded":
            lesson += f" Hint: match both words in {case['requested_tag']}, not a distractor."
        public["problem"] += " " + lesson
        _require(recover_binding(public) == case["target_binding"], "VIEW_RECOVERY_MISMATCH")
        records.append({"schema": SCHEMA, "family_id": case["family_id"], "split": case["split"],
            "curriculum": curriculum,
            "delivery_kind": "seven_stage_cycle" if curriculum == "aligned" else "ordinary_presentations",
            "stage": stage if curriculum == "aligned" else f"presentation_{index + 1}",
            "stage_index": index, "assistance": assistance, "public": public,
            "target_binding": case["target_binding"], "alignment": _alignment(case) if curriculum == "aligned" else []})
    return records


def validate_cycle(case, records):
    _require(type(records) is list and len(records) == 7, "CYCLE_INCOMPLETE")
    _require(all(type(row) is dict for row in records), "CYCLE_RECORD_INVALID")
    _require("curriculum" in records[0] and "assistance" in records[0], "CYCLE_RECORD_INVALID")
    expected = make_cycle(case, records[0]["assistance"], records[0]["curriculum"])
    # Recovery checks actual public meaning before canonical rendering comparison.
    for row in records:
        _require("public" in row and recover_binding(row["public"]) == case["target_binding"], "VIEW_RECOVERY_MISMATCH")
        _require(row.get("alignment") == (_alignment(case) if records[0]["curriculum"] == "aligned" else []),
                 "ALIGNMENT_MISMATCH")
    _require(records == expected, "CYCLE_VIEW_DRIFT")
    return True


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


def fit_tokenizer(dataset):
    """Train-only union vocabulary shared by controls; no held-out text fitting."""
    training = []
    for case in dataset["splits"]["train"]:
        training.append(make_public(case))
        for curriculum in ("aligned", "ordinary"):
            for assistance in ("full", "faded", "none"):
                training.extend(row["public"] for row in make_cycle(case, assistance, curriculum))
    return LosslessPublicTokenizer.fit_train(training, max_length=512)


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
