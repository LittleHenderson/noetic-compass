"""CCB-P1: typed ProgramSpecs, the CODE ladder graph, the EXAMINER's
reference implementations (our channel - never the student's or the
teacher's), and seeded exam generation.

Channels: DEV (visible machinery), PROTECTED (the examiner's seed,
never in any teacher prompt), RETENTION (after the process
boundary), TRANSFER (renamed signatures / shifted parameters)."""

from __future__ import annotations

import random
from typing import Callable, Dict, List

DEV_SEED = 3301
PROTECTED_SEED = 77007        # the examiner's channel
RETENTION_SEED = 515151
TRANSFER_SEED = 616161

SKILLS: Dict[str, Dict] = {
    "read_and_trace": {"level": "CODE-L0", "kind": "tracing",
                       "prerequisites": []},
    "sum_list": {"level": "CODE-L1", "kind": "algorithm",
                 "prerequisites": ["read_and_trace"]},
    "reverse_string": {"level": "CODE-L1", "kind": "algorithm",
                       "prerequisites": ["read_and_trace"]},
    "max_list": {"level": "CODE-L2", "kind": "algorithm",
                 "prerequisites": ["sum_list"]},
    "count_matching": {"level": "CODE-L2", "kind": "algorithm",
                       "prerequisites": ["max_list"]},
    "contracts_testing": {"level": "CODE-L3", "kind": "testing",
                          "prerequisites": ["sum_list",
                                            "reverse_string"]},
    "debug_repair": {"level": "CODE-L4", "kind": "repair",
                     "prerequisites": ["contracts_testing",
                                       "count_matching"]},
}


def missing_prerequisites(skill_id: str,
                          promoted: List[str]) -> List[str]:
    seen: List[str] = []

    def walk(current: str) -> None:
        for prerequisite in SKILLS[current]["prerequisites"]:
            walk(prerequisite)
            if prerequisite not in promoted \
                    and prerequisite not in seen:
                seen.append(prerequisite)

    walk(skill_id)
    return seen


# ------------------------------------------------------ typed specs
def validate_spec(spec: Dict) -> List[str]:
    defects = []
    for field in ("spec_id", "function_name", "params", "returns",
                  "description"):
        if spec.get(field) in (None, "", []):
            defects.append(f"spec missing {field!r}")
    for param in spec.get("params", []):
        if not isinstance(param, dict) or "name" not in param \
                or "type" not in param:
            defects.append(f"bad param {param!r}")
    if not isinstance(spec.get("public_examples"), list) \
            or len(spec.get("public_examples", [])) < 2:
        defects.append("spec needs at least 2 public_examples")
    for example in spec.get("public_examples", []):
        if not isinstance(example, dict) or "args" not in example \
                or "expected" not in example:
            defects.append(f"bad example {example!r}")
    return defects


# ---------------------------------- the EXAMINER's references (ours)
_PREDICATES = {
    "positive": lambda x: x > 0,
    "negative": lambda x: x < 0,
    "even": lambda x: x % 2 == 0,
    "odd": lambda x: x % 2 != 0,
}


def _ref_sum_list(xs):
    return sum(xs)


def _ref_reverse_string(s):
    return s[::-1]


def _ref_max_list(xs):
    return max(xs) if xs else None


def _ref_count_matching(xs, predicate_name):
    return sum(1 for x in xs if _PREDICATES[predicate_name](x))


REFERENCES: Dict[str, Callable] = {
    "sum_list": _ref_sum_list,
    "reverse_string": _ref_reverse_string,
    "max_list": _ref_max_list,
    "count_matching": _ref_count_matching,
}

SPECS: Dict[str, Dict] = {
    "sum_list": {
        "spec_id": "S_sum_list", "function_name": "sum_list",
        "params": [{"name": "xs", "type": "list[int]"}],
        "returns": "int",
        "description": "return the sum of all integers in xs "
                       "(0 for an empty list)",
        "public_examples": [
            {"args": [[1, 2, 3]], "expected": 6},
            {"args": [[]], "expected": 0}],
    },
    "reverse_string": {
        "spec_id": "S_reverse_string",
        "function_name": "reverse_string",
        "params": [{"name": "s", "type": "str"}], "returns": "str",
        "description": "return s with its characters in reverse "
                       "order",
        "public_examples": [
            {"args": ["abc"], "expected": "cba"},
            {"args": [""], "expected": ""}],
    },
    "max_list": {
        "spec_id": "S_max_list", "function_name": "max_list",
        "params": [{"name": "xs", "type": "list[int]"}],
        "returns": "int|None",
        "description": "return the largest integer in xs, or None "
                       "for an empty list",
        "public_examples": [
            {"args": [[3, 1, 2]], "expected": 3},
            {"args": [[]], "expected": None}],
    },
    "count_matching": {
        "spec_id": "S_count_matching",
        "function_name": "count_matching",
        "params": [{"name": "xs", "type": "list[int]"},
                   {"name": "predicate_name", "type": "str"}],
        "returns": "int",
        "description": "return how many integers in xs satisfy the "
                       "named predicate (positive, negative, even, "
                       "odd)",
        "public_examples": [
            {"args": [[1, -2, 3], "positive"], "expected": 2},
            {"args": [[], "even"], "expected": 0}],
    },
}

# renamed-signature TRANSFER specs (structural transfer channel)
TRANSFER_SPECS: Dict[str, Dict] = {
    "sum_list": {
        "spec_id": "T_total_scores", "function_name": "total_scores",
        "params": [{"name": "scores", "type": "list[int]"}],
        "returns": "int",
        "description": "return the total of all scores",
        "public_examples": [
            {"args": [[2, 5]], "expected": 7},
            {"args": [[]], "expected": 0}],
    },
    "reverse_string": {
        "spec_id": "T_mirror_word", "function_name": "mirror_word",
        "params": [{"name": "word", "type": "str"}],
        "returns": "str",
        "description": "return the mirrored word",
        "public_examples": [
            {"args": ["pit"], "expected": "tip"},
            {"args": ["a"], "expected": "a"}],
    },
    "max_list": {
        "spec_id": "T_highest_mark", "function_name": "highest_mark",
        "params": [{"name": "marks", "type": "list[int]"}],
        "returns": "int|None",
        "description": "return the highest mark, or None if there "
                       "are no marks",
        "public_examples": [
            {"args": [[4, 9, 1]], "expected": 9},
            {"args": [[]], "expected": None}],
    },
    "count_matching": {
        "spec_id": "T_tally_kind", "function_name": "tally_kind",
        "params": [{"name": "values", "type": "list[int]"},
                   {"name": "kind", "type": "str"}],
        "returns": "int",
        "description": "count the values of the named kind",
        "public_examples": [
            {"args": [[2, 4, 5], "even"], "expected": 2},
            {"args": [[-1, 3], "negative"], "expected": 1}],
    },
}


# ----------------------------------------------- seeded exam inputs
def _rng(seed: int, skill_id: str) -> random.Random:
    return random.Random(f"{seed}:{skill_id}")


def exam_inputs(skill_id: str, seed: int,
                count: int) -> List[List]:
    rng = _rng(seed, skill_id)
    inputs: List[List] = []
    for index in range(count):
        if skill_id in ("sum_list", "max_list"):
            xs = [rng.randint(-20, 20)
                  for _ in range(rng.randint(0, 8))]
            inputs.append([xs])
        elif skill_id == "reverse_string":
            length = rng.randint(0, 8)
            inputs.append(["".join(rng.choice("abcdexyz")
                                   for _ in range(length))])
        elif skill_id == "count_matching":
            xs = [rng.randint(-9, 9)
                  for _ in range(rng.randint(0, 7))]
            inputs.append([xs, rng.choice(sorted(_PREDICATES))])
        else:
            raise KeyError(skill_id)
    return inputs


def boundary_inputs(skill_id: str) -> List[List]:
    if skill_id in ("sum_list", "max_list"):
        return [[[]], [[0]], [[-1]], [[-5, 5]], [[7, 7, 7]]]
    if skill_id == "reverse_string":
        return [[""], ["a"], ["aa"], ["ab"]]
    if skill_id == "count_matching":
        return [[[], "even"], [[0], "even"], [[0], "positive"],
                [[-1, 0, 1], "odd"]]
    raise KeyError(skill_id)


def property_checks(skill_id: str, run_fn) -> List[str]:
    """Property tests over seeded data; run_fn(args)->(ok, value).
    Returns typed failures (empty = all properties hold)."""
    rng = _rng(424242, skill_id)
    failures = []
    for _ in range(6):
        if skill_id == "sum_list":
            xs = [rng.randint(-9, 9) for _ in range(rng.randint(0, 5))]
            ys = [rng.randint(-9, 9) for _ in range(rng.randint(0, 5))]
            ok1, a = run_fn([xs])
            ok2, b = run_fn([ys])
            ok3, c = run_fn([xs + ys])
            if not (ok1 and ok2 and ok3) or a + b != c:
                failures.append(f"additivity fails on {xs}/{ys}")
        elif skill_id == "reverse_string":
            s = "".join(rng.choice("abcd")
                        for _ in range(rng.randint(0, 6)))
            ok1, once = run_fn([s])
            ok2, twice = (run_fn([once]) if ok1 else (False, None))
            if not (ok1 and ok2) or twice != s:
                failures.append(f"involution fails on {s!r}")
        elif skill_id == "max_list":
            xs = [rng.randint(-9, 9)
                  for _ in range(rng.randint(1, 6))]
            ok, value = run_fn([xs])
            if not ok or value not in xs \
                    or any(x > value for x in xs):
                failures.append(f"max law fails on {xs}")
        elif skill_id == "count_matching":
            xs = [rng.randint(-9, 9)
                  for _ in range(rng.randint(0, 6))]
            ok1, evens = run_fn([xs, "even"])
            ok2, odds = run_fn([xs, "odd"])
            if not (ok1 and ok2) or evens + odds != len(xs):
                failures.append(f"partition law fails on {xs}")
    return failures


# ---------------------------------------- CODE-L0 trace exam corpus
TRACE_PROGRAMS = [
    {"code": ("def f(n):\n"
              "    total = 0\n"
              "    for i in range(n):\n"
              "        total = total + i\n"
              "    return total\n"),
     "fname": "f", "inputs": [[3], [5], [0], [7]]},
    {"code": ("def f(xs):\n"
              "    best = 0\n"
              "    for x in xs:\n"
              "        if x > best:\n"
              "            best = x\n"
              "    return best\n"),
     "fname": "f", "inputs": [[[2, 9, 4]], [[1]], [[]]]},
    {"code": ("def f(s):\n"
              "    out = ''\n"
              "    for ch in s:\n"
              "        out = ch + out\n"
              "    return out\n"),
     "fname": "f", "inputs": [["abc"], ["xy"], [""]]},
]
