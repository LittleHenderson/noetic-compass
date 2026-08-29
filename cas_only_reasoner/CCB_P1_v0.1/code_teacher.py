"""THE PROGRAMMING SCHOOL, LIVE: a large model teaches the CNCM to
read, write, test, and repair Python. The teacher proposes code and
strategies; the COMPILER AND TESTS decide; the ladder promotes.
A teacher model can praise its own code until the fans spin loose -
the compiler remains unmoved.

Teacher inference is cloud GPU (AWS Bedrock) per the standing
never-CPU order. Per-run sealed outputs."""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from codeboard import (CodeStudent, ProcedureStore, SPECS,  # noqa: E402
                       algorithm_battery, static_gate, teach)
from codeboard.spec import SKILLS  # noqa: E402

TEACHER_MODEL = os.environ.get("CAS_TEACHER_MODEL",
                               "qwen.qwen3-32b-v1:0")
STORE_PATH = os.path.join(HERE, "fixtures", "code_procedures.json")

ORDER = ["read_and_trace", "sum_list", "reverse_string", "max_list",
         "count_matching", "contracts_testing", "debug_repair"]

DESCRIPTIONS = {
    "read_and_trace": (
        "READING AND TRACING code: executing a program by hand, one "
        "line at a time, tracking every variable"),
    "sum_list": (
        "writing sum_list(xs): return the sum of all integers in "
        "the list xs (0 for an empty list)"),
    "reverse_string": (
        "writing reverse_string(s): return the string s with its "
        "characters in reverse order"),
    "max_list": (
        "writing max_list(xs): return the largest integer in xs, "
        "or None for an empty list"),
    "count_matching": (
        "writing count_matching(xs, predicate_name): count how "
        "many integers in xs satisfy the named predicate - "
        "'positive' (x > 0), 'negative' (x < 0), 'even' "
        "(x % 2 == 0), 'odd' (x % 2 != 0)"),
    "contracts_testing": (
        "TESTING DISCIPLINE: why one passing example does not "
        "establish correctness; boundary cases, negative tests, "
        "and property checks"),
    "debug_repair": (
        "DEBUGGING METHOD: reproduce, trace, find the first state "
        "that differs from a known-good run, patch only that cause, "
        "rerun everything"),
}

SANDBOX_RULES = (
    "Sandbox rules: plain Python only - no imports, no print, no "
    "open, no eval/exec, no attributes starting with underscore, "
    "no global/nonlocal. Allowed builtins include len, range, abs, "
    "min, max, sum, sorted, enumerate, zip. ")


def extract_code(reply: str):
    text = re.sub(r"```(python)?", "", reply).strip().strip("`")
    index = text.find("def ")
    return text[index:].strip() if index >= 0 else None


def make_validators(skill_id):
    kind = SKILLS[skill_id]["kind"]

    def valid_explanation(value):
        if not isinstance(value, str) or not value.strip():
            return "must be a non-empty plain-English explanation"
        if len(value) > 500:
            return "keep it under 500 characters"
        return None

    def valid_strategy(value):
        return valid_explanation(value)

    def valid_implementation(value):
        if not isinstance(value, str) or "def " not in value:
            return ("must be a python function definition starting "
                    "with 'def'")
        gate = static_gate(value)
        if gate:
            return gate[0]
        ok, detail = algorithm_battery(skill_id, value,
                                       SPECS[skill_id])
        if not ok:
            return (f"the code FAILS the battery at stage "
                    f"{detail.get('stage')}: args="
                    f"{detail.get('args')} expected="
                    f"{detail.get('expected')} got="
                    f"{detail.get('got')}"
                    f"{detail.get('detail', '')}")
        return None

    def valid_bug(value):
        if not isinstance(value, str) or "def " not in value:
            return ("must be a python function definition starting "
                    "with 'def'")
        gate = static_gate(value)
        if gate:
            return gate[0]
        ok, _ = algorithm_battery(skill_id, value, SPECS[skill_id])
        if ok:
            return ("this 'bug' PASSES every test - a common bug "
                    "must actually be defective (change exactly one "
                    "small thing so at least one test fails)")
        return None

    fields = [("explanation",
               "Give a one-or-two sentence plain-English "
               "explanation of the concept for a beginner (plain "
               "text).", valid_explanation, "text")]
    if kind == "algorithm":
        spec = SPECS[skill_id]
        signature = (f"def {spec['function_name']}("
                     + ", ".join(p["name"]
                                 for p in spec["params"]) + "):")
        fields.append((
            "implementation",
            f"{SANDBOX_RULES}Write ONLY the python function "
            f"(no prose): {signature} - "
            f"{spec['description']}. Examples: "
            + "; ".join(f"{spec['function_name']}"
                        f"({', '.join(map(repr, e['args']))}) == "
                        f"{e['expected']!r}"
                        for e in spec["public_examples"]),
            valid_implementation, "code"))
        fields.append((
            "common_bug",
            f"{SANDBOX_RULES}Write ONLY a BUGGY variant of the same "
            f"function (a realistic learner mistake - off-by-one, "
            f"wrong initial value, wrong operator) that FAILS at "
            f"least one test.",
            valid_bug, "code"))
    else:
        fields.append((
            "strategy",
            "Describe the method step by step in plain English "
            "(plain text, one short paragraph).",
            valid_strategy, "text"))
    return fields


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    import boto3
    region = os.environ.get("AWS_REGION", "us-west-2")
    runtime = boto3.Session().client("bedrock-runtime",
                                     region_name=region)
    print(f"code teacher {TEACHER_MODEL} via AWS Bedrock ({region})")

    def ask(question, seed=None):
        response = runtime.converse(
            modelId=TEACHER_MODEL,
            system=[{"text": "You are a programming teacher for an "
                             "exact symbolic student. Answer with "
                             "ONLY what is asked - no extra prose, "
                             "no code fences."}],
            messages=[{"role": "user",
                       "content": [{"text": question}]}],
            inferenceConfig={"maxTokens": 700,
                             "temperature": 0.0 if seed is None
                             else 0.7})
        text = response["output"]["message"]["content"][-1]["text"]
        return re.sub(r"<think>.*?</think>", "", text,
                      flags=re.DOTALL).strip()

    only = os.environ.get("CAS_TARGETS")
    for skill_id in ORDER:
        if only and skill_id not in only.split(","):
            continue
        store = ProcedureStore.load(STORE_PATH)
        if skill_id in store.procedures:
            print(f"\n=== {skill_id}: already PROMOTED - skipping")
            continue
        print(f"\n=== TEACHING {skill_id} "
              f"({SKILLS[skill_id]['level']}) ===")
        if SKILLS[skill_id]["kind"] == "algorithm":
            before = CodeStudent(store).implement(skill_id,
                                                  SPECS[skill_id])
        else:
            before = {"status": "CANNOT_MISSING_SKILL"}
        print(f"  BEFORE: {before['status']}")

        packet = {"lesson_id": f"CODE_{skill_id}",
                  "skill_id": skill_id,
                  "teacher_model": TEACHER_MODEL,
                  "teacher_revision": f"bedrock:{region}",
                  "provenance":
                      "schema_constrained_field_elicitation"}
        log = []
        failed = None
        context = f"Concept: {DESCRIPTIONS[skill_id]}. "
        for field, question, validator, shape in \
                make_validators(skill_id):
            accepted = None
            for attempt in range(1, 5):
                q = context + question if attempt == 1 else (
                    context + question + " Your previous answer "
                    f"was rejected: {log[-1]['defect']}")
                reply = ask(q, seed=None if attempt == 1
                            else attempt)
                if shape == "code":
                    value = extract_code(reply)
                    defect = ("no function definition found"
                              if value is None else validator(value))
                else:
                    value = reply.strip().strip('"')
                    defect = validator(value)
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
                                f"code_lesson_{skill_id}.json")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        if failed:
            json.dump({"skill_id": skill_id,
                       "verdict": f"ELICITATION_FAILED_{failed}",
                       "log": log},
                      open(out_path, "w", encoding="utf-8"),
                      indent=1, sort_keys=True)
            print(f"  ELICITATION_FAILED_{failed} - stopping the "
                  f"chain")
            break

        episode = teach(packet, STORE_PATH)
        print(f"  LADDER: {episode['verdict']}")
        after = None
        if episode["verdict"] == "PROMOTED":
            fresh = CodeStudent(ProcedureStore.load(STORE_PATH))
            if SKILLS[skill_id]["kind"] == "algorithm":
                after = fresh.implement(skill_id, SPECS[skill_id])
            else:
                after = {"status": "SOLVED",
                         "detail": "capability gate open"}
            print(f"  AFTER:  {after['status']}")
        json.dump({"skill_id": skill_id, "packet": packet,
                   "episode": episode, "before": before,
                   "after": after, "log": log},
                  open(out_path, "w", encoding="utf-8"),
                  indent=1, sort_keys=True, default=str)
        print(f"  sealed: {out_path}")
        if episode["verdict"] != "PROMOTED":
            print("  stopping the chain")
            break


if __name__ == "__main__":
    main()
