"""THE MATHEMATICS SCHOOL, LIVE: a large model teaches the CNCM
mathematics from quantity grounding to linear equations through
schema-constrained field elicitation; the twelve-step exact ladder
examines; the teacher's eloquence grants nothing.

Teacher inference is cloud GPU (AWS Bedrock) per the standing
never-CPU order. Every lesson attempt - pass or fail - seals to a
per-run file (the overwrite bug stays dead).
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(LANE, "CCB_M1_v0.1"))

from mathschool import (SkillStore, Student, attack_equation,  # noqa: E402
                        teach, verify_identity)
from mathschool.graph import SKILLS  # noqa: E402
from mathschool.mathir import MathParseError, parse_equation  # noqa: E402

TEACHER_MODEL = os.environ.get("CAS_TEACHER_MODEL",
                               "qwen.qwen3-32b-v1:0")
STORE_PATH = os.path.join(HERE, "fixtures", "math_skills.json")

PROBES = {
    "quantity_grounding": {"kind": "scene_count",
                           "scene": ["block"] * 3, "expected": "3"},
    "counting_order": {"kind": "successor", "n": 6, "expected": "7"},
    "integer_comparison": {"kind": "compare", "a": "5", "b": "3",
                           "expected": "greater"},
    "addition": {"kind": "arith", "op": "add", "a": "3", "b": "4",
                 "expected": "7"},
    "subtraction": {"kind": "arith", "op": "sub", "a": "9", "b": "4",
                    "expected": "5"},
    "multiplication": {"kind": "arith", "op": "mul", "a": "3",
                       "b": "4", "expected": "12"},
    "division": {"kind": "arith", "op": "div", "a": "12", "b": "4",
                 "expected": "3"},
    "fractions": {"kind": "arith", "op": "add", "a": "1/2",
                  "b": "1/4", "expected": "3/4"},
    "algebra_distribute": {"kind": "expand", "expr": "2 * (x + 3)",
                           "expected_equal_to": "2 * x + 6"},
    "linear_equations": {"kind": "solve",
                         "equation": "2 * (x + 3) = 14",
                         "variable": "x", "expected": "4"},
}

DESCRIPTIONS = {
    "quantity_grounding": (
        "QUANTITY: that a collection of objects has an exact count. "
        "Give simple TRUE numeric equations about combining small "
        "counts (like '1 + 1 = 2')"),
    "counting_order": (
        "COUNTING ORDER: each number has a successor, one more. "
        "Give TRUE equations of the form 'n + 1 = m'"),
    "integer_comparison": (
        "INTEGER COMPARISON: numbers are equal, greater, or less. "
        "Give TRUE equations (equalities that hold, e.g. '3 = 3' or "
        "'0 - 2 = -2')"),
    "addition": (
        "ADDITION of whole numbers. Give TRUE addition equations "
        "like '3 + 4 = 7'"),
    "subtraction": (
        "SUBTRACTION of whole numbers. Give TRUE subtraction "
        "equations like '9 - 4 = 5'"),
    "multiplication": (
        "MULTIPLICATION of whole numbers. Give TRUE multiplication "
        "equations like '3 * 4 = 12'"),
    "division": (
        "DIVISION as the inverse of multiplication. This syntax has "
        "NO '/' operator between expressions - express division "
        "facts as multiplication ('12 = 4 * 3') or with fraction "
        "literals ('10 * 1/2 = 5')"),
    "fractions": (
        "FRACTIONS: exact parts written p/q. Give TRUE fraction "
        "equations like '1/2 + 1/4 = 3/4'"),
    "algebra_distribute": (
        "DISTRIBUTION of multiplication over addition. The formal "
        "rule uses metavariables a, b, c"),
    "linear_equations": (
        "SOLVING LINEAR EQUATIONS like '2 * (x + 3) = 14' by "
        "expanding and isolating the unknown. For the common "
        "mistake, give ONE single false equation with ONE '=' sign "
        "(for example the wrong intermediate 'x + 3 = 14' from "
        "dividing only one side) - never a chain with '=>'"),
}


def _valid_explanation(value):
    if not isinstance(value, str) or not value.strip():
        return "must be a non-empty plain-English string"
    if len(value) > 400:
        return "keep the explanation under 400 characters"
    return None


def _valid_examples(value):
    if not isinstance(value, list) or len(value) < 2 \
            or not all(isinstance(v, str) for v in value):
        return "must be a JSON list of at least 2 equation strings"
    for example in value:
        try:
            parse_equation(example)
        except MathParseError as exc:
            return (f"{example!r} does not parse: {exc}. Use only "
                    f"integers, fractions like 1/2, + - * ^ ( ) and "
                    f"one '='")
        holds, witness = verify_identity(example)
        if not holds:
            return (f"{example!r} is FALSE - the exact checker "
                    f"refutes it (witness: {witness}). Every worked "
                    f"example must be exactly true")
    return None


def _valid_mistake(value):
    if not isinstance(value, str):
        return "must be one equation string"
    try:
        parse_equation(value)
    except MathParseError as exc:
        return f"{value!r} does not parse: {exc}"
    witness = attack_equation(value)
    if witness is None or "error" in witness:
        return (f"{value!r} is actually TRUE - a common mistake must "
                f"be a FALSE equation the checker can refute")
    return None


def _valid_rule(value):
    if not isinstance(value, str):
        return "must be one identity string over metavariables a,b,c"
    try:
        parse_equation(value)
    except MathParseError as exc:
        return f"does not parse: {exc}"
    holds, witness = verify_identity(value)
    if not holds:
        return (f"the rule is NOT an identity - counterexample: "
                f"{witness}")
    return None


def _valid_equation_examples(value):
    from fractions import Fraction

    from mathschool.mathir import eval_at, parse_expr
    if not isinstance(value, list) or len(value) < 2:
        return ("must be a JSON list of at least 2 objects like "
                '{"equation": "2 * (x + 3) = 14", "variable": "x", '
                '"solution": "4"}')
    for example in value:
        if not isinstance(example, dict) or not all(
                k in example for k in ("equation", "variable",
                                       "solution")):
            return (f"{example!r} must be an object with equation, "
                    f"variable, solution")
        try:
            lhs, rhs = parse_equation(example["equation"])
            solution_value = eval_at(
                parse_expr(str(example["solution"])), {})
            point = {example["variable"]: solution_value}
            if eval_at(lhs, point) != eval_at(rhs, point):
                return (f"{example['equation']!r} is NOT satisfied "
                        f"by {example['variable']} = "
                        f"{example['solution']} - the exact checker "
                        f"refutes this example")
        except MathParseError as exc:
            return f"{example!r} does not parse: {exc}"
        except Exception as exc:
            return f"{example!r}: {exc}"
    return None


def _valid_method(value):
    allowed = ("expand", "collect", "isolate")
    if not isinstance(value, list) or not value \
            or any(v not in allowed for v in value):
        return (f"must be a JSON list of steps from {allowed}, in "
                f"order (an equation like 2 * (x + 3) = 14 needs "
                f"'expand' then 'isolate')")
    return None


STRING_FIELDS = ("explanation", "common_mistake", "formal_rule")


def fields_for(skill_id):
    kind = SKILLS[skill_id]["kind"]
    fields = [
        ("explanation",
         "Give a one-or-two sentence plain-English explanation of "
         "the concept for a beginner (plain text, no JSON).",
         _valid_explanation),
        ("worked_examples",
         'Give ONLY a JSON list of 2-4 equation strings, e.g. '
         '["3 + 4 = 7", "5 + 6 = 11"]. Every equation must be '
         "EXACTLY true.",
         _valid_examples),
        ("common_mistake",
         "Give ONLY one FALSE equation (plain text, one line) "
         "showing the most common learner mistake for this concept, "
         "e.g. 3 + 4 = 12",
         _valid_mistake),
    ]
    if kind == "rewrite_rule":
        fields.insert(1, (
            "formal_rule",
            "Give ONLY the formal identity over metavariables as "
            "plain text on one line, e.g. "
            "a * (b + c) = a * b + a * c",
            _valid_rule))
    if kind == "equation_solving":
        fields.insert(1, (
            "method",
            'Give ONLY a JSON list of method steps from ["expand", '
            '"collect", "isolate"], in the order they apply.',
            _valid_method))
        fields[2] = (
            "worked_examples",
            "Give ONLY a JSON list of 2-3 solved-equation objects, "
            'each like {"equation": "2 * (x + 3) = 14", "variable": '
            '"x", "solution": "4"}. The solution must satisfy the '
            "equation exactly.",
            _valid_equation_examples)
    return fields


def _string_candidates(reply):
    cleaned = re.sub(r"```(json)?", "", reply).strip()
    yield cleaned.strip().strip('"').strip()
    parsed = extract_json(cleaned)

    def walk(node):
        if isinstance(node, str):
            yield node
        elif isinstance(node, dict):
            for value in node.values():
                yield from walk(value)
        elif isinstance(node, list):
            for item in node:
                yield from walk(item)

    if parsed is not None:
        yield from walk(parsed)
    for line in cleaned.splitlines():
        line = line.strip().strip('",').strip()
        line = re.sub(r'^[\w"]+\s*:\s*', "", line).strip('"')
        if line:
            yield line
            # a wrong DERIVATION chain ('a = b => c = d') carries the
            # erroneous step as a segment - each segment is a
            # candidate (live finding: the teacher's mistake came as
            # a full worked-wrong chain)
            for segment in line.split("=>"):
                segment = segment.strip().strip('",').strip()
                if segment and segment != line:
                    yield segment


def _best_string_candidate(reply, validator):
    """The first candidate the VALIDATOR accepts; else the cleaned
    whole reply (so the defect message shows what was received)."""
    fallback = None
    for candidate in _string_candidates(reply):
        if fallback is None:
            fallback = candidate
        if validator(candidate) is None:
            return candidate
    return fallback if fallback is not None else reply.strip()


def extract_json(text):
    text = re.sub(r"```(json)?", "", text).strip()
    for start in range(len(text)):
        if text[start] in "[{\"":
            for end in range(len(text), start, -1):
                try:
                    return json.loads(text[start:end])
                except Exception:
                    continue
    try:
        return json.loads(text)
    except Exception:
        return None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    import boto3
    region = os.environ.get("AWS_REGION", "us-west-2")
    runtime = boto3.Session().client("bedrock-runtime",
                                     region_name=region)
    print(f"math teacher {TEACHER_MODEL} via AWS Bedrock ({region})")

    def ask(question, seed=None):
        response = runtime.converse(
            modelId=TEACHER_MODEL,
            system=[{"text": "You are a mathematics teacher for an "
                             "exact symbolic student. Answer with "
                             "ONLY the JSON asked for - no prose, no "
                             "code fences."}],
            messages=[{"role": "user", "content": [{"text": question}]}],
            inferenceConfig={"maxTokens": 700,
                             "temperature": 0.0 if seed is None
                             else 0.7})
        text = response["output"]["message"]["content"][-1]["text"]
        return re.sub(r"<think>.*?</think>", "", text,
                      flags=re.DOTALL).strip()

    only = os.environ.get("CAS_TARGETS")
    order = [s for s in ("quantity_grounding", "counting_order",
                         "integer_comparison", "addition",
                         "subtraction", "multiplication", "division",
                         "fractions", "algebra_distribute",
                         "linear_equations")
             if not only or s in only.split(",")]

    for skill_id in order:
        store = SkillStore.load(STORE_PATH)
        if skill_id in store.skills:
            print(f"\n=== {skill_id}: already PROMOTED - skipping "
                  f"(re-teaching quarantines by law) ===")
            continue
        print(f"\n=== TEACHING {skill_id} "
              f"({SKILLS[skill_id]['level']}) ===")
        probe = dict(PROBES[skill_id],
                     exercise_id=f"probe:{skill_id}",
                     skill_id=skill_id)
        before = Student(store).solve(probe)
        print(f"  BEFORE: probe -> {before['status']}")

        packet = {"lesson_id": f"MATH_{skill_id}",
                  "skill_id": skill_id,
                  "teacher_model": TEACHER_MODEL,
                  "teacher_revision": f"bedrock:{region}",
                  "provenance":
                      "schema_constrained_field_elicitation"}
        log = []
        failed = None
        context = (f"Concept: {DESCRIPTIONS[skill_id]}. Allowed "
                   f"syntax: integers, fractions like 1/2, "
                   f"variables, + - * ^ ( ), one '=' per equation. ")
        for field, question, validator in fields_for(skill_id):
            accepted = None
            for attempt in range(1, 5):
                q = context + question if attempt == 1 else (
                    context + question + " Your previous answer was "
                    f"rejected: {log[-1]['defect']}")
                reply = ask(q, seed=None if attempt == 1 else attempt)
                if field in STRING_FIELDS:
                    # plain-text fields: teachers over-answer (round-2
                    # finding: a fenced JSON blob carrying every field
                    # at once). The VALIDATOR picks the compliant
                    # candidate from the reply - schema discipline
                    # unchanged, extraction made robust.
                    value = _best_string_candidate(reply, validator)
                else:
                    value = extract_json(reply)
                defect = ("no JSON found" if value is None
                          else validator(value))
                log.append({"field": field, "attempt": attempt,
                            "defect": defect, "raw": reply[:200]})
                print(f"  {field} attempt {attempt}: "
                      f"{'OK' if defect is None else defect}")
                if defect is None:
                    accepted = value
                    break
            if accepted is None:
                failed = field
                break
            packet[field] = accepted

        out_path = os.path.join(HERE, "output",
                                f"math_lesson_{skill_id}.json")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        if failed:
            json.dump({"skill_id": skill_id,
                       "verdict": f"ELICITATION_FAILED_{failed}",
                       "log": log},
                      open(out_path, "w", encoding="utf-8"),
                      indent=1, sort_keys=True)
            print(f"  ELICITATION_FAILED_{failed}")
            print("  stopping the chain - downstream skills need "
                  "this prerequisite")
            break

        episode = teach(packet, STORE_PATH)
        print(f"  LADDER: {episode['verdict']}")
        after = None
        if episode["verdict"] == "PROMOTED":
            after = Student(SkillStore.load(STORE_PATH)).solve(probe)
            print(f"  AFTER:  probe -> {after['status']} "
                  f"answer={after.get('answer') or after.get('answer_expr')}")
        json.dump({"skill_id": skill_id, "packet": packet,
                   "episode": episode, "before": before,
                   "after": after, "log": log},
                  open(out_path, "w", encoding="utf-8"),
                  indent=1, sort_keys=True, default=str)
        print(f"  sealed: {out_path}")
        if episode["verdict"] != "PROMOTED":
            print("  stopping the chain - the prerequisite graph "
                  "blocks everything downstream")
            break


if __name__ == "__main__":
    main()
