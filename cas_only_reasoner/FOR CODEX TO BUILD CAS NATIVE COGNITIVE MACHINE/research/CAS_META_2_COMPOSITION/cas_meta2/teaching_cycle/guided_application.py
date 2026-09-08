"""Version 2 teaching: a solved demonstration, then a separate application.

Version 1 material remains unchanged. The public demonstration answer is not
the practice label: its independent slot permutation can preserve or change
that label. Only the actual observations determine the supervised practice
target. No task generator, held-out data, model or provider is imported here.
"""
from __future__ import annotations

from copy import deepcopy
from itertools import permutations
import re

from ..codec import canonical_sha256, validate_public
from ..features_v2 import LosslessPublicTokenizer
from . import lesson_contract as v1

SCHEMA = "cas-meta2-guided-application/2"
DEMONSTRATION_SCHEMA = "cas-meta2-worked-binding-demo/2"
STAGES = v1.STAGES
TeachingDataError = v1.TeachingDataError
make_public = v1.make_public
recover_binding = v1.recover_binding
_require = v1._require
_PERMUTATIONS = tuple(permutations((0, 1, 2)))


def _demonstration(case):
    """Select layout only from permitted numbers, not the target or family ID."""
    rows = sorted(case["observations"], key=lambda row: row["slot"])
    numeric_digest = canonical_sha256([row["values"] for row in rows])
    permutation = _PERMUTATIONS[int(numeric_digest, 16) % len(_PERMUTATIONS)]
    observations = [{"slot": slot, "tag": rows[source]["tag"]}
                    for slot, source in enumerate(permutation)]
    binding = next(row["slot"] for row in observations if row["tag"] == case["requested_tag"])
    return {"schema": DEMONSTRATION_SCHEMA, "fixed_child": "A",
            "numeric_layout_sha256": numeric_digest, "source_permutation": list(permutation),
            "requested_tag": case["requested_tag"], "observations": observations,
            "target_binding": binding}


def validate_demonstration(demonstration):
    """Check the typed miniature problem independently of its claimed answer."""
    _require(type(demonstration) is dict and set(demonstration) ==
             {"schema", "fixed_child", "numeric_layout_sha256", "source_permutation",
              "requested_tag", "observations", "target_binding"}, "DEMONSTRATION_FIELDS_INVALID")
    _require(demonstration["schema"] == DEMONSTRATION_SCHEMA
             and demonstration["fixed_child"] == "A", "DEMONSTRATION_SCOPE_INVALID")
    digest = demonstration["numeric_layout_sha256"]
    _require(type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
             "DEMONSTRATION_DIGEST_INVALID")
    permutation = demonstration["source_permutation"]
    _require(type(permutation) is list and len(permutation) == 3
             and all(type(slot) is int for slot in permutation)
             and sorted(permutation) == [0, 1, 2], "DEMONSTRATION_PERMUTATION_INVALID")
    rows = demonstration["observations"]
    _require(type(rows) is list and len(rows) == 3, "DEMONSTRATION_OBSERVATIONS_INVALID")
    _require(all(type(row) is dict and set(row) == {"slot", "tag"}
                 and type(row["slot"]) is int and row["slot"] in (0, 1, 2)
                 and v1._two_words(row["tag"]) for row in rows), "DEMONSTRATION_OBSERVATION_INVALID")
    _require(sorted(row["slot"] for row in rows) == [0, 1, 2]
             and len({row["tag"] for row in rows}) == 3, "DEMONSTRATION_SOURCE_NOT_UNIQUE")
    _require(v1._two_words(demonstration["requested_tag"]), "DEMONSTRATION_REQUEST_INVALID")
    matches = [row["slot"] for row in rows if row["tag"] == demonstration["requested_tag"]]
    _require(type(demonstration["target_binding"]) is int
             and matches == [demonstration["target_binding"]], "DEMONSTRATION_TARGET_MISMATCH")
    return True


def _worked_text(demonstration):
    placements = " ".join(f"Demonstration slot {row['slot']}: {row['tag']}."
                          for row in demonstration["observations"])
    return (" Worked demonstration, separate from practice. " + placements
        + f" Demonstration request: {demonstration['requested_tag']}."
        + f" Worked demonstration answer: BIND{demonstration['target_binding']}."
        + " Match the request tag to its marked source; that demonstration slot supplies A's argument."
        + " Removing that source leaves no valid choice; substituting another tag breaks the match."
        + " Changing workplace alone changes nothing. End demonstration."
        + " Apply the same rule to the actual observations, whose slot order can differ."
        + " Your training target concerns those actual observations.")


def recover_demonstration(public):
    """Recover the solved public demonstration without reading record metadata."""
    validate_public(public)
    problem = public["problem"]
    placements = re.findall(r"Demonstration slot ([012]): ([a-z]+ [a-z]+)\.", problem)
    requests = re.findall(r"Demonstration request: ([a-z]+ [a-z]+)\.", problem)
    answers = re.findall(r"Worked demonstration answer: BIND([012])\.", problem)
    _require(len(placements) == 3 and sorted(slot for slot, _ in placements) == ["0", "1", "2"]
             and len({tag for _, tag in placements}) == 3, "PUBLIC_DEMONSTRATION_PLACEMENTS_INVALID")
    _require(len(requests) == 1 and len(answers) == 1, "PUBLIC_DEMONSTRATION_REQUEST_OR_ANSWER_INVALID")
    matches = [int(slot) for slot, tag in placements if tag == requests[0]]
    _require(matches == [int(answers[0])], "PUBLIC_DEMONSTRATION_ANSWER_MISMATCH")
    return {"requested_tag": requests[0], "observations": [
        {"slot": int(slot), "tag": tag} for slot, tag in placements], "target_binding": matches[0]}


def make_cycle(case, assistance="full", curriculum="aligned"):
    _require(assistance in ("full", "faded", "none"), "ASSISTANCE_INVALID")
    records = v1.make_cycle(case, assistance="none", curriculum=curriculum)
    demo = _demonstration(case) if assistance == "full" else None
    if demo is not None:
        validate_demonstration(demo)
    for record in records:
        record.update(schema=SCHEMA, assistance=assistance, demonstration=deepcopy(demo))
        if assistance == "full":
            record["public"]["problem"] += _worked_text(demo)
        elif assistance == "faded":
            record["public"]["problem"] += (
                " Role hint: match the requested source to the actual observation tag,"
                " then connect that row's slot to child A's argument.")
        _require(recover_binding(record["public"]) == record["target_binding"], "PRACTICE_RECOVERY_MISMATCH")
    return records


def validate_cycle(case, records):
    _require(type(records) is list and len(records) == 7
             and all(type(row) is dict for row in records), "CYCLE_INCOMPLETE")
    _require("assistance" in records[0] and "curriculum" in records[0], "CYCLE_RECORD_INVALID")
    for record in records:
        _require("public" in record and recover_binding(record["public"]) == case["target_binding"],
                 "PRACTICE_RECOVERY_MISMATCH")
        if record.get("assistance") == "full":
            demo = record.get("demonstration")
            validate_demonstration(demo)
            recovered = recover_demonstration(record["public"])
            _require(recovered == {key: demo[key] for key in recovered}, "DEMONSTRATION_PUBLIC_METADATA_MISMATCH")
        else:
            _require(record.get("demonstration") is None, "UNSOLVED_STAGE_HAS_DEMONSTRATION")
            _require("BIND" not in record["public"]["problem"], "PRACTICE_ANSWER_IN_UNSOLVED_STAGE")
    _require(records == make_cycle(case, records[0]["assistance"], records[0]["curriculum"]),
             "GUIDED_APPLICATION_VIEW_DRIFT")
    return True


def fit_tokenizer(training_cases):
    """Prepare a shared train-only vocabulary; these rows are not delivered lessons."""
    _require(type(training_cases) is list and training_cases, "TRAINING_CASES_REQUIRED")
    training = []
    for case in training_cases:
        _require(type(case) is dict and case.get("split") == "train", "TRAINING_CASE_REQUIRED")
        training.append(make_public(case))
        for curriculum in ("aligned", "ordinary"):
            for assistance in ("full", "faded", "none"):
                training.extend(record["public"] for record in make_cycle(case, assistance, curriculum))
    return LosslessPublicTokenizer.fit_train(training, max_length=512)
