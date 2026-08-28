"""CCB-M1 v0.1 demonstration: evaluate, prove, refute, learn."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json

from cas_math.m1 import CCB_M1

ROOT = os.path.dirname(os.path.abspath(__file__))


def load_fixture(name):
    with open(os.path.join(ROOT, "fixtures", name), "r",
              encoding="utf-8") as fh:
        return json.load(fh)


def main():
    print("CCB-M1 v0.1 - the Mathematical Learning and Proof Board")
    print("=" * 64)

    arith = load_fixture("arithmetic_tasks.json")
    m1a = CCB_M1({"revision": 1, "ruleset": {"axioms": [], "procedures": []}})
    print("Exact arithmetic (1/3 stays 1/3):")
    for task in arith["tasks"]:
        result = m1a.evaluate(task)
        mark = "PASS" if result["passed"] else "FAIL"
        print(f"  {mark}  {task['task_id']:<12} -> {result['value']}")

    ident = load_fixture("identity_tasks.json")
    m1i = CCB_M1(ident)
    print()
    print("Identities (checker is the sole authority):")
    for task in ident["tasks"]:
        result = m1i.verify_identity(task, ident)
        mark = "PASS" if result["passed"] else "FAIL"
        proof = "steps=" + str(len(result["steps"]))
        print(f"  {mark}  {task['task_id']:<22} {result['outcome']['verdict']:<10} {proof}")

    conj = load_fixture("conjecture_tasks.json")
    m1c = CCB_M1({"revision": 1, "ruleset": {"axioms": [], "procedures": []}})
    print()
    print("Counterexamples:")
    for task in conj["tasks"]:
        result = m1c.refute(task)
        mark = "PASS" if result["passed"] else "FAIL"
        if result["found"]:
            detail = (f"point {result['point']} -> "
                      f"{result['left_value']} vs {result['right_value']}")
        else:
            detail = result.get("note", "no counterexample")
        print(f"  {mark}  {task['task_id']:<24} {detail}")

    mistake = load_fixture("mistake_package.json")
    m1m = CCB_M1(mistake)
    cycle = m1m.mistake_cycle(mistake["mistake_task"])
    print()
    print("Learning from a mathematical mistake:")
    print(f"  attempt: {cycle['attempt_outcome']['verdict']} at step "
          f"{cycle['attempt_outcome']['first_invalid_step']} "
          f"({cycle['fault']['guilty_rule']})")
    for decision in cycle["decisions"]:
        print(f"  {decision['verdict']:<12} replace {decision['repair']['rule_id']} "
              f"with {decision['repair']['replacement']}")
    corrected = m1m.verify_identity(m1m.package["held_out"][0], m1m.package)
    print(f"  corrected proof: {corrected['outcome']['verdict']} "
          f"with {len(corrected['steps'])} step(s)")


if __name__ == "__main__":
    main()
