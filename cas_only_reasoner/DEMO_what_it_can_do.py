"""RUN IT YOURSELF:  python DEMO_what_it_can_do.py

Raw demonstration of what the CNCM actually does - math, programming,
and language - loaded live from the promoted stores on disk. No model
at runtime; pure Python. Every result below is computed on the spot,
not printed from a saved file.

NOTE (honest): the last two LANGUAGE turns currently print 'None' -
that is a real known bug in the negated-passive / passive-question
reply text, left in so this demo shows the machine as it truly is.
"""
import difflib
import os
import sys

LANE = os.path.dirname(os.path.abspath(__file__))
for sub in ("CCB_M1_v0.1", "CAS_MATH_LADDER_v0.1", "CCB_P1_v0.1",
            "CAS_CORTEX_v0.1", "CCB_L1_v0.1", "CCB_D1_v0.1"):
    sys.path.insert(0, os.path.join(LANE, sub))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def line(text=""):
    print(text)


# ============================================================ MATH
line("=" * 64)
line("MATHEMATICS  (24 skills it was taught, loaded from disk)")
line("=" * 64)
from mathschool import SkillStore, Student

mstore = SkillStore.load(os.path.join(
    LANE, "CAS_MATH_LADDER_v0.1", "fixtures", "math_skills.json"))
ms = Student(mstore)

line("\n[1] solve an equation (verified by substituting the answer "
     "back in):")
r = ms.solve({"exercise_id": "1", "skill_id": "x", "kind": "solve",
              "equation": "5 * (x + 4) = 45", "variable": "x",
              "expected": None})
line(f"    5*(x + 4) = 45   ->  x = {r['answer']}   "
     f"[{r.get('verified_by')}]")

line("\n[2] differentiate a polynomial (graded vs an independent "
     "re-derivation):")
r = ms.solve({"exercise_id": "2", "skill_id": "x",
              "kind": "derivative", "expr": "4 * x^3 + 2 * x^2 + 7",
              "variable": "x", "expected_equal_to": ""})
line(f"    d/dx (4x^3 + 2x^2 + 7)  =  {r['answer_expr']}")

line("\n[3] a definite integral (it re-differentiates to check "
     "itself, or refuses):")
r = ms.solve({"exercise_id": "3", "skill_id": "x", "kind": "integral",
              "expr": "3 * x^2", "variable": "x", "a": "0", "b": "2",
              "expected": None})
line(f"    integral of 3x^2 from 0 to 2  =  {r['answer']}   "
     f"[{r.get('verified_by')}]")

line("\n[4] DISCOVER + PROVE new identities, and REFUTE false ones "
     "with exact counterexamples:")
r = ms.solve({"exercise_id": "4", "skill_id": "x",
              "kind": "discovery_round", "seed": 999, "budget": 40,
              "min_proved": 1, "min_refuted": 2,
              "expected": "discovery_verified"})
for item in r["proved"][:4]:
    line(f"    PROVED : {item['claim']}")
w = r["refuted"][0]
line(f"    REFUTED: {w['claim']}   (counterexample "
     f"{w['witness'].get('point')} -> {w['witness'].get('left')} "
     f"!= {w['witness'].get('right')})")

line("\n[5] capability honesty - a math student that never learned "
     "addition:")
r = Student(SkillStore()).solve(
    {"exercise_id": "5", "skill_id": "addition", "kind": "arith",
     "op": "add", "a": "3", "b": "4", "expected": None})
line(f"    asked 3+4  ->  {r['status']}: {r['detail']}")


# ============================================================ CODE
line("\n" + "=" * 64)
line("PROGRAMMING  (7 Python skills it was taught, loaded from disk)")
line("=" * 64)
from codeboard import (CodeStudent, ProcedureStore, SPECS,
                       TRANSFER_SPECS, algorithm_battery,
                       make_mutants, run, static_gate)

cstore = ProcedureStore.load(os.path.join(
    LANE, "CCB_P1_v0.1", "fixtures", "code_procedures.json"))
cs = CodeStudent(cstore)

line("\n[1] WRITE a function from a contract it never saw (a renamed "
     "spec), then RUN it:")
impl = cs.implement("count_matching", TRANSFER_SPECS["count_matching"])
for ln in impl["code"].strip().splitlines():
    line(f"      {ln}")
out = run(impl["code"], "tally_kind", [[1, -2, 3, -4, 5], "negative"])
line(f"    running tally_kind([1,-2,3,-4,5], 'negative')  ->  "
     f"{out['value']}   [{out['status']}]")

line("\n[2] DEBUG: inject a bug into its own code; it finds the first "
     "bad state and repairs it:")
code = cstore.get("count_matching")["formal"]["code"]
bug = make_mutants("count_matching", code, count=1)[0]
line("    the injected bug (unified diff, one line changed):")
for d in difflib.unified_diff(code.splitlines(), bug.splitlines(),
                              lineterm="", n=0):
    if d.startswith(("+", "-")) and not d.startswith(("+++", "---")):
        line(f"      {d.rstrip()}")


def battery(candidate):
    return algorithm_battery("count_matching", candidate,
                             SPECS["count_matching"])


res = cs.diagnose_and_repair("count_matching", bug,
                             [[1, -2, 3], "positive"], battery)
diag = res["diagnosis"]
line(f"    it found the fault: step {diag['first_bad_step']}, line "
     f"{diag['line']}, variable '{diag['variable']}' = "
     f"{diag['got']} but should be {diag['reference']}")
line(f"    it repaired it: changed line(s) {res['changed_lines']}, "
     f"verified by {res['verified_by']}")

line("\n[3] the SANDBOX refuses dangerous code BEFORE running it:")
escape = ("def f():\n"
          "    box = {}\n"
          "    def g():\n"
          "        yield box['fr'].gi_frame\n"
          "    return 1\n")
line(f"    a frame-walk escape attempt  ->  refused: "
     f"{static_gate(escape)[0][:58]}")
file_write = "def f():\n    return open('x', 'w')\n"
line(f"    a file write  ->  {run(file_write, 'f', [])['status']}")


# ============================================================ LANGUAGE
line("\n" + "=" * 64)
line("LANGUAGE + REASONING  (36 sentence shapes, ~30 words)")
line("=" * 64)
from cortex.router import HybridRouter

router = HybridRouter(mode="NATIVE_ONLY")
script = [
    "every cat is an animal.",
    "milo is a cat.",
    "is milo an animal?",
    "the cat chases the dog.",
    "actually, the cat chases the fox.",
    "what does the cat chase?",
    "the fox is not chased by the cat.",   # <- the known None bug
    "is the fox chased by the cat?",        # <- the known None bug
]
line()
for sentence in script:
    answer = router.turn(sentence)["answer"]
    reply = answer.get("text") or answer.get("acknowledgment")
    line(f"    you>     {sentence}")
    line(f"    machine> {reply}")
