"""Worker-safe rendering of supplied lessons, without a task generator.

Only registered training cases should reach the training adapter. This module
has no curriculum seed, final split sizes, held-out vocabulary combinations,
or import of teacher-side data construction. Lexical bounds are structural;
the teacher-side dataset validator owns the finite curriculum membership rules.
The renderer and checker do not prove learning or independent neural reasoning.
"""
from __future__ import annotations

from copy import deepcopy
import re

from ..codec import canonical_sha256, validate_public
from ..features_v2 import LosslessPublicTokenizer

SCHEMA = "cas-meta2-teaching-cycle-data/1"
STAGES = ("name_function", "context", "analogy", "mapping", "decomposition",
          "recomposition", "reinforcement")
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


def _two_words(value):
    return type(value) is str and re.fullmatch(r"[a-z]{1,32} [a-z]{1,32}", value) is not None


def _case_check(case):
    _require(type(case) is dict and set(case) == CASE_FIELDS, "CASE_FIELDS_INVALID")
    _require(type(case["split"]) is str and re.fullmatch(r"[a-z_]{1,64}", case["split"]) is not None
             and case["fixed_child"] == "A", "CASE_SCOPE_INVALID")
    _require(type(case["wording"]) is int and 0 <= case["wording"] < 3, "WORDING_INVALID")
    _require(type(case["target_binding"]) is int and case["target_binding"] in (0, 1, 2), "TARGET_INVALID")
    _require(_two_words(case["context"]), "CONTEXT_INVALID")
    _require(_two_words(case["requested_tag"]), "REQUEST_TAG_INVALID")
    validate_public({"problem": "Check.", "observations": case["observations"]})
    tags = [row["tag"] for row in case["observations"]]
    _require(len(set(tags)) == 3 and all(_two_words(tag) for tag in tags), "TAGS_INVALID")
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


def fit_tokenizer(dataset):
    """Train-only union vocabulary shared by controls; no held-out text fitting."""
    training = []
    for case in dataset["splits"]["train"]:
        training.append(make_public(case))
        for curriculum in ("aligned", "ordinary"):
            for assistance in ("full", "faded", "none"):
                training.extend(row["public"] for row in make_cycle(case, assistance, curriculum))
    return LosslessPublicTokenizer.fit_train(training, max_length=512)
