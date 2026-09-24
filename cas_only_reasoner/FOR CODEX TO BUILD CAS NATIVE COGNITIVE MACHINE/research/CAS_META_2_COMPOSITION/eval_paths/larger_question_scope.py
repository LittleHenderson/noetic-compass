"""Larger-question path, pure half: which path a question takes, and how its answer is decoded and graded.

PLAIN SUMMARY.
* A question whose worlds all have 4 nodes or fewer takes the ORIGINAL path: the frozen slot compiler
  (`slots.py`) and the frozen checker (`checker.py`), exactly as before. Every historical course packet is of
  this kind, because the frozen 64-world training bank has at most 4 nodes per world.
* A question whose largest world has 5 or 6 nodes takes the LARGER path: the accepted slot compiler v2
  (`slots_v2.py`) and the accepted checker v2 (`checker_v2.py`, D-1 ACCEPTED at `7f85af1e`).
* A question that carries any world with 7 or more nodes is REFUSED, with the named reason
  `LARGER_PATH_REFUSED:WORLD_ABOVE_SIX_NODES`. So is a question that carries any node with in- or out-degree
  above 4 (`LARGER_PATH_REFUSED:DEGREE_ABOVE_READER_EXACT_RANGE`): Helm's degree features stop being exact there
  (`pointer_learner.py:1003-1022`, D-1 spec S5).
* The route is decided from EVERY world the packet's public source carries, not only the focus world. A
  7-node world anywhere in the bank refuses the question, whatever it asks.

WHAT THIS MODULE DOES NOT DO. It imports no torch and no learner, and it never changes a protected file. It does
not import `pointer_contract`, `pointer_inputs` or `pointer_learner`: importing those loads the frozen course.
`decode` turns caller-supplied scores into an answer; `grade` runs the checker. Grading is separate from
decoding, so no checker call can reach an inference step.

WHY MALFORMED PACKETS GO TO THE ORIGINAL PATH. `route` reads the packet before any validator does. If it cannot
count the worlds' nodes and edges, it returns ORIGINAL, and the original validators refuse the packet with their
own error codes, exactly as they did before this module existed.
"""
from __future__ import annotations

import ast
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from cas_meta2.typed_teaching import answers, answers_v2, checker, checker_v2, course, slots, slots_v2, source

SCHEMA = "claude.helm-larger-question-path/0.1"
GRADE_SCHEMA = "claude.helm-larger-question-grade/0.1"
ORIGINAL, LARGER = "ORIGINAL_PATH", "LARGER_PATH"
ORIGINAL_MAX_NODES = checker.MAX_ISOMORPHISM_NODES          # 4: the frozen checker and slot compiler bound
LARGER_MAX_NODES = checker_v2.MAX_ISOMORPHISM_NODES         # 6: the accepted checker v2 bound
TYPED_TEACHING = Path(checker.__file__).resolve().parent
POINTER_LEARNER_PATH = TYPED_TEACHING / "pointer_learner.py"


def _module_literal(path, name):
    """One module-level literal, read by `ast` so this pure module never imports the learner."""
    values = [node.value for node in ast.parse(Path(path).read_bytes(), str(path)).body
              if isinstance(node, ast.Assign) and len(node.targets) == 1
              and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name]
    if len(values) != 1:
        raise ValueError("LARGER_PATH_LITERAL:" + name)
    return ast.literal_eval(values[0])


# `pointer_learner.DEGREE_STEPS = 5` one-hot buckets 0..4, where 4 means "4 or more" (`pointer_learner.py:211`,
# `:1016-1017`). A degree of 5 or more is therefore read as 4. The torch half re-checks this against the imported
# learner at import time.
READER_EXACT_MAX_DEGREE = _module_literal(POINTER_LEARNER_PATH, "DEGREE_STEPS") - 1

# The two node bounds must agree with the two answer grammars and with each other.
if not (answers.MAX_PERMUTATION_NODES == ORIGINAL_MAX_NODES == 4
        and answers_v2.MAX_PERMUTATION_NODES == LARGER_MAX_NODES == 6
        and source.MAX_NODES == 10 and READER_EXACT_MAX_DEGREE == 4):
    raise ValueError("LARGER_PATH_BOUNDS_DISAGREE")

# LF-normalised sha256 (CRLF -> LF) of every protected file this path calls, taken at builder parent `ec80730c`.
# The three v2 pins equal the D-1 ACCEPTED anchors (`D1_ACCEPTANCE_RESULT.md`). If any file moves, the path must
# be re-reviewed, so `verify_source_pins` fails closed.
PROTECTED_SOURCE_LF_SHA256 = {
    "pointer_learner.py": "2ebb1b086953002272d18e75d397bb233b75f62442d073487ebade2e93487781",
    "pointer_inputs.py": "ba920d9e65e20b96dd0614a7131a80b9b87dd9918cb07d94ec5ebb4b628d0ecd",
    "pointer_contract.py": "70be7ae7b7b3dbefd6a5d168b04ab7394718d7456a264614236d31b0c9c09b3d",
    "slots.py": "3d79db262708264dcd77cd7fb0296e7683849b5967b82d72fd3c51ab85f74487",
    "slots_v2.py": "7b9c2c3a0aca938acf0979aa7d74f1fea422726333926f079a5f8e06f5e7d2fb",
    "answers.py": "4d4cf21b65914c5b6878b58a52ab3cfe2f8864b319a3bb5ad1b95c6780686e5c",
    "answers_v2.py": "b0bdabfcfac656e4071f192d9bda8ff7dec8b88baf077f29131d8f94497d1bb5",
    "checker.py": "57ac0a9f78c46999fac444fc974d3c1b718435b583cbc48701be74c56efa971e",
    "checker_v2.py": "d24d8276955bacbe626ebe6293efe7b64c2cf36544100b60175f6d0ab80e6258",
    "source.py": "13c265e576dd027362611ca0956ac9f1e6285945cb7e626cef9270c2d08a9337",
    "course.py": "cbb1b5aea97567f21cb15ca2def5332ea3175abd10e8a6a48b9e3edd9e0e41e6",
    "focal.py": "cd2761b5c5dced4af5e4acc0a6b55a384555b2cb9bb3b90442f8673d1754e70a",
}
D1_ACCEPTED_LF_SHA256 = {
    "checker_v2.py": "d24d8276955bacbe626ebe6293efe7b64c2cf36544100b60175f6d0ab80e6258",
    "answers_v2.py": "b0bdabfcfac656e4071f192d9bda8ff7dec8b88baf077f29131d8f94497d1bb5",
    "slots_v2.py": "7b9c2c3a0aca938acf0979aa7d74f1fea422726333926f079a5f8e06f5e7d2fb",
}
# Checker errors that mean "outside the checker's bounded scope", not "malformed question".
GRADER_SCOPE_CODES = ("TYPED_CHECKER_ISOMORPHISM_BOUND", "TYPED_CHECKER_TARGET_SET_BOUND",
                      "TYPED_CHECKER_TARGET_BYTES")
REFUSAL_CODES = ("WORLD_ABOVE_SIX_NODES", "DEGREE_ABOVE_READER_EXACT_RANGE", "GRADER_OUT_OF_SCOPE",
                 "INFERENCE_ONLY", "SOURCE_DRIFT")

# What each question kind does at 5 and 6 nodes. `tests/test_larger_question_path_static.py` checks every
# COMPILES / REFUSES / GRADES word here against the committed fixtures, so this table cannot drift silently.
KIND_SCOPE = {
    "role_set": {"rules": list(answers.RULES["role_set"]),
                 "old_slot_compiler_at_5_6": "COMPILES", "old_checker_at_5_6": "GRADES",
                 "checker_v2_at_5_6": "GRADES", "checker_v2_versus_frozen": "IDENTICAL_CODE_PATH",
                 "d1_acceptance_coverage": "NOT_EXERCISED_BY_D1",
                 "answer_slots": "6 role slots, ABSENT/PRESENT; independent of node count"},
    "definition": {"rules": list(answers.RULES["definition"]),
                   "old_slot_compiler_at_5_6": "COMPILES", "old_checker_at_5_6": "GRADES",
                   "checker_v2_at_5_6": "GRADES", "checker_v2_versus_frozen": "IDENTICAL_CODE_PATH",
                   "d1_acceptance_coverage": "NOT_EXERCISED_BY_D1",
                   "answer_slots": "whole: one of N0..N(n-1); kind_ref and function_ref: one of W0..W64"},
    "context": {"rules": list(answers.RULES["context"]),
                "old_slot_compiler_at_5_6": "COMPILES", "old_checker_at_5_6": "GRADES",
                "checker_v2_at_5_6": "GRADES", "checker_v2_versus_frozen": "IDENTICAL_CODE_PATH",
                "d1_acceptance_coverage": "NOT_EXERCISED_BY_D1",
                "answer_slots": "setting_ref: one of W0..W64; one ABSENT/PRESENT slot per focus node (3 are primary)"},
    "analogy": {"rules": list(answers.RULES["analogy"]),
                "old_slot_compiler_at_5_6": "COMPILES",
                "old_checker_at_5_6": "REFUSES_TYPED_CHECKER_ISOMORPHISM_BOUND",
                "checker_v2_at_5_6": "GRADES_IF_FOCUS_AND_EVERY_BANK_WORLD_AT_MOST_6",
                "checker_v2_versus_frozen": "BOUND_RAISED_FROM_4_TO_6",
                "d1_acceptance_coverage": "A3_A5_A6_AT_5_AND_6_NODES",
                "answer_slots": "world_id: NO_MATCH or one of the bank's W aliases (at most 64 bank worlds)"},
    "correspondence": {"rules": list(answers.RULES["correspondence"]),
                       "old_slot_compiler_at_5_6": "REFUSES_TYPED_PERMUTATION_BOUND",
                       "old_checker_at_5_6": "REFUSES_TYPED_CHECKER_ISOMORPHISM_BOUND",
                       "checker_v2_at_5_6": "GRADES_IF_AT_MOST_64_VALID_MAPPINGS",
                       "checker_v2_versus_frozen": "BOUND_RAISED_FROM_4_TO_6",
                       "d1_acceptance_coverage": "A3_AT_5_AND_6_NODES",
                       "answer_slots": ("mode NO_MATCH/MAPPING plus one mapping_target slot per focus node over the "
                                        "target's N aliases; decoded over all 1 + n! complete assignments "
                                        "(121 at 5 nodes, 721 at 6)")},
    "parts": {"rules": list(answers.RULES["parts"]),
              "old_slot_compiler_at_5_6": "COMPILES", "old_checker_at_5_6": "GRADES",
              "checker_v2_at_5_6": "GRADES", "checker_v2_versus_frozen": "IDENTICAL_CODE_PATH",
              "d1_acceptance_coverage": "X_HSET1A_AT_3_TO_5_NODES_ONLY",
              "answer_slots": "one ABSENT/PRESENT slot per focus node"},
    "edge_account": {"rules": list(answers.RULES["edge_account"]),
                     "old_slot_compiler_at_5_6": "COMPILES", "old_checker_at_5_6": "GRADES",
                     "checker_v2_at_5_6": "GRADES", "checker_v2_versus_frozen": "IDENTICAL_CODE_PATH",
                     "d1_acceptance_coverage": "X_HSET1A_AT_3_TO_5_NODES_ONLY",
                     "answer_slots": "one ABSENT/PRESENT slot per ordered node pair: 25 at 5 nodes, 36 at 6 (cap 100)"},
    "reach": {"rules": list(answers.RULES["reach"]),
              "old_slot_compiler_at_5_6": "COMPILES", "old_checker_at_5_6": "GRADES",
              "checker_v2_at_5_6": "GRADES", "checker_v2_versus_frozen": "IDENTICAL_CODE_PATH",
              "d1_acceptance_coverage": "X_HSET1A_AT_3_TO_5_NODES_ONLY",
              "answer_slots": "one slot: ABSENT, DIRECT, or VIA_N0..VIA_N(n-1)"},
}
if set(KIND_SCOPE) != set(answers.RULES):
    raise ValueError("LARGER_PATH_KIND_TABLE")


class LargerPathRefusal(ValueError):
    """A named, deliberate refusal. `code` is one of `REFUSAL_CODES`."""

    def __init__(self, code, detail=""):
        if code not in REFUSAL_CODES:
            raise ValueError("LARGER_PATH_UNKNOWN_REFUSAL:" + str(code))
        self.code = code
        self.detail = detail
        super().__init__("LARGER_PATH_REFUSED:" + code + (":" + detail if detail else ""))


def lf_sha256(path):
    return sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def verify_source_pins():
    """Fail closed if any protected file differs from the bytes this path was built and reviewed against."""
    observed = {name: lf_sha256(TYPED_TEACHING / name) for name in PROTECTED_SOURCE_LF_SHA256}
    for name, expected in PROTECTED_SOURCE_LF_SHA256.items():
        if observed[name] != expected:
            raise LargerPathRefusal("SOURCE_DRIFT", name)
    for name, expected in D1_ACCEPTED_LF_SHA256.items():
        if observed[name] != expected:
            raise LargerPathRefusal("SOURCE_DRIFT", "D1_ANCHOR:" + name)
    return observed


def packet_shape(packet):
    """`{world_count, max_nodes, max_degree}` over EVERY world in the packet's public source, or None.

    None means the packet is too malformed to count; the caller then leaves it to the original validators.
    Reads node lists and `contains` edges only. Reads no query, no answer and no support.
    """
    if type(packet) is not dict or type(packet.get("source")) is not dict:
        return None
    worlds = packet["source"].get("worlds")
    if type(worlds) is not list or not worlds:
        return None
    max_nodes = max_degree = 0
    for world in worlds:
        if type(world) is not dict or type(world.get("nodes")) is not list or type(world.get("contains")) is not list:
            return None
        max_nodes = max(max_nodes, len(world["nodes"]))
        in_degree, out_degree = Counter(), Counter()
        for edge in world["contains"]:
            if type(edge) is not dict or type(edge.get("source")) is not str or type(edge.get("target")) is not str:
                return None
            out_degree[edge["source"]] += 1
            in_degree[edge["target"]] += 1
        max_degree = max([max_degree, *in_degree.values(), *out_degree.values()])
    return {"world_count": len(worlds), "max_nodes": max_nodes, "max_degree": max_degree}


def route(packet):
    """ORIGINAL, LARGER, or a raised `LargerPathRefusal`. Decided before any compile, forward or grade."""
    shape = packet_shape(packet)
    if shape is None or shape["max_nodes"] <= ORIGINAL_MAX_NODES:
        return ORIGINAL
    if shape["max_nodes"] > LARGER_MAX_NODES:
        raise LargerPathRefusal("WORLD_ABOVE_SIX_NODES", "max_nodes=%d" % shape["max_nodes"])
    if shape["max_degree"] > READER_EXACT_MAX_DEGREE:
        raise LargerPathRefusal("DEGREE_ABOVE_READER_EXACT_RANGE", "max_degree=%d" % shape["max_degree"])
    return LARGER


def slot_module(path):
    """The frozen slot compiler for ORIGINAL, the accepted v2 compiler for LARGER. Nothing else."""
    if path == ORIGINAL:
        return slots
    if path == LARGER:
        return slots_v2
    raise ValueError("LARGER_PATH_ROUTE:" + str(path))


def checker_module(path):
    """The frozen checker (scorer of record for history) for ORIGINAL; the accepted checker v2 for LARGER."""
    if path == ORIGINAL:
        return checker
    if path == LARGER:
        return checker_v2
    raise ValueError("LARGER_PATH_ROUTE:" + str(path))


def compile_plan(packet):
    """`(route, plan)`. The plan comes from the frozen compiler on ORIGINAL and from slots v2 on LARGER."""
    path = route(packet)
    return path, slot_module(path).compile_slots(packet)


def decode(packet, scores):
    """`(route, decisions, answer)` from `{slot_id: {symbol: score}}`, with the route's own decoder."""
    path = route(packet)
    module = slot_module(path)
    decisions = module.score_decisions(packet, scores)
    return path, decisions, module.assemble_answer(packet, decisions)


def grade(packet, answer):
    """Grade one decoded answer. NEVER called by the inference path.

    ORIGINAL questions are graded by the frozen checker, which stays the scorer of record for every historical
    result. LARGER questions are graded by checker v2. A checker bound (more than 6 nodes, more than 64 valid
    answers, an oversized target) becomes `LargerPathRefusal("GRADER_OUT_OF_SCOPE", <checker code>)`.
    """
    path = route(packet)
    module = checker_module(path)
    checked = course.validate_model_packet(packet)
    public, query = checked["source"], checked["record"]["query"]
    try:
        check = module.check_answer(public, query, answer)
    except module.SemanticCheckError as error:
        if str(error) in GRADER_SCOPE_CODES:
            raise LargerPathRefusal("GRADER_OUT_OF_SCOPE", str(error)) from error
        raise
    return {"schema": GRADE_SCHEMA, "route": path, "checker_module": module.__name__,
            "checker_profile_digest": check["checker_profile_digest"], "correct": check["correct"],
            "admissible_answer_count": check["admissible_answer_count"], "check": deepcopy(check)}


def target(packet):
    """The route's checker target for one packet. For tests and reports only; never used at inference."""
    path = route(packet)
    checked = course.validate_model_packet(packet)
    return checker_module(path).derive_target(checked["source"], checked["record"]["query"])
