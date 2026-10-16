"""Prove the appendix-F candidate rule against the runtime's LIVE oracle, in two processes.

WHY TWO PROCESSES
-----------------
The recipe brain refuses to share a process with torch, and `native_task.py` imports torch at line 13.
So the brain side and the oracle side each run in their own interpreter and their answer lists are
compared afterwards. This is the process boundary the design already has to cross, used here as a
test rig rather than as the design.

WHAT IS BEING PROVED
--------------------
The **whole candidate**, not a piece of it:

    case -> cells (appendix F section 7) -> RecipeBrain.readout -> limiting_cell -> label

against `native_task.derive_answer`, the runtime's own oracle, on every case `r1_leg_cases` produces.

WHY THIS IS DIFFERENT FROM APPENDIX A'S PROOF
---------------------------------------------
Appendix A's 118,304-case proof compared two **transcriptions** — a hand-written copy of the oracle
against a hand-written copy of the rule — in one file, with no brain and no runtime. It showed the two
rules agree. It could not show that the live brain obeys its own rule, and appendix F is exactly the
finding that it does not. This run uses the live `RecipeBrain` and the live `native_task`.

WHAT IT DOES NOT DO
-------------------
It does not decide whether the candidate is ALLOWED. The reference cell needs to know whether every
leg is present, and whether that crosses the design's own `RT_SHIM_NO_MATH` line is a design question.
This proves the arithmetic agrees with the oracle; nothing more.

Usage:
    C:\\Python314\\python.exe -B prove_candidate_vs_oracle.py <v3-package-root> <r6-source-root> [--quiet]
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import textwrap

CELLS = 8
PAD, LEG_PRESENT, LEG_MISSING, REF_ALL, REF_SOME = 3.0, 2.0, 1.0, 1.0, 3.0

#: Builds the cells and reads the brain. Imports no torch, and refuses to.
BRAIN_SIDE = """
import json, os, sys
CASES_DIR = os.environ["CASES_DIR"]
OUT_PATH = os.environ["OUT_PATH"]
ENCODING = os.environ.get("ENCODING", "padding")
from rb.brain import RecipeBrain
from rb import common
sys.path.insert(0, CASES_DIR)
import r1_leg_cases

CELLS = common.CELLS
PAD, PRESENT, MISSING, REF_ALL, REF_SOME = 3.0, 2.0, 1.0, 1.0, 3.0
#: The padding encoding's three values. SPARE is strictly between MISSING and PRESENT, so the spare
#: cell is the minimum exactly when every leg is present, and a missing leg's cell is the minimum
#: exactly when one is. The bridge needs no knowledge of whether every leg is present: it writes
#: leg membership and one constant, and the brain's own argmin does the rest.
SPARE = 1.5
LEG_MISSING, LEG_PRESENT = 1.0, 3.0

LABELS = tuple("FIRST_UNSUPPORTED_LEG_%d" % i for i in range(7)) + ("ALL_LEGS_PRESENT",)

brain = RecipeBrain()
brain.allocated[0] = True
brain.a[0] = [1.0] * CELLS          # requirement 1 everywhere
brain.h[0] = [1.0] * CELLS
brain.beta[0] = "CANDIDATE"
brain._invalidate()


def candidate_reference(case):
    \"\"\"Appendix F section 7: a reference cell whose value is 1 when EVERY leg is present.

    Requires the bridge to compute the conjunction, which is what RT_SHIM_NO_MATH is about.
    \"\"\"
    route = case["route"]
    edges = {tuple(e) for e in case["edges"]}
    legs = list(zip(route, route[1:]))
    all_present = all(pair in edges for pair in legs)
    x = [REF_ALL if all_present else REF_SOME]
    for pair in legs:
        x.append(PRESENT if pair in edges else MISSING)
    x += [PAD] * (CELLS - len(x))
    return x, len(legs), True


def candidate_padding(case):
    \"\"\"The padding encoding: legs at cells 0..k-1, and the SPARE constant in every cell after them.

    The bridge writes ONE constant and a per-leg membership value. It computes no conjunction and
    holds no part of the answer. The spare cell being the minimum IS the statement "every leg is
    present", and the brain discovers that by its own argmin.
    \"\"\"
    route = case["route"]
    edges = {tuple(e) for e in case["edges"]}
    legs = list(zip(route, route[1:]))
    x = [LEG_PRESENT if pair in edges else LEG_MISSING for pair in legs]
    x += [SPARE] * (CELLS - len(x))
    return x, len(legs), False


def candidate(case):
    x, k, uses_reference = (candidate_reference(case) if ENCODING == "reference"
                            else candidate_padding(case))
    r = brain.readout(x)
    if r.gate is not None or r.limiting is None:
        return ("GATED:" + str(r.gate)), r.label, uses_reference
    c = r.limiting
    # EACH ENCODING HAS ITS OWN CELL LAYOUT, so each has its own mapping.
    #
    # The first version of this refactor gave BOTH encodings the padding layout's mapping. The
    # padding encoding then agreed on all cases and the reference encoding disagreed on all of
    # them, because its reference cell sits at index 0 and its legs at 1..k. The disagreement was
    # the refactor's bug, not a property of the encoding. The digests showed it immediately:
    # d1d4c303 against the oracle's c591c568.
    if uses_reference:
        # reference at cell 0; legs at cells 1..k; padding after.
        if c == 0:
            return LABELS[-1], r.label, uses_reference
        if c > k:
            return ("UNREACHABLE:beyond-the-legs"), r.label, uses_reference
        return LABELS[c - 1], r.label, uses_reference
    # legs at cells 0..k-1; the spare region starts at cell k and is all the same constant.
    if c == k:
        return LABELS[-1], r.label, uses_reference
    if c > k:
        return ("UNREACHABLE:spare-not-first"), r.label, uses_reference
    return LABELS[c], r.label, uses_reference


out = open(OUT_PATH, "w", encoding="utf-8", newline="\\n")
n = 0
gated = 0
used_reference = 0
for case in r1_leg_cases.generate():
    answer, label, uses_reference = candidate(case)
    if answer.startswith("GATED:"):
        gated += 1
    if uses_reference:
        used_reference += 1
    out.write(answer + "\\n")
    n += 1
out.close()
print(json.dumps({"side": "brain", "cases": n, "gated": gated,
                  "encoding": ENCODING, "used_reference_cell": used_reference}))
"""

RUNTIME_SIDE = """
import json, os, sys
CASES_DIR = os.environ["CASES_DIR"]
OUT_PATH = os.environ["OUT_PATH"]
import native_task
sys.path.insert(0, CASES_DIR)
import r1_leg_cases

out = open(OUT_PATH, "w", encoding="utf-8", newline="\\n")
n = 0
for case in r1_leg_cases.generate():
    # The oracle validates its input, so the case is built the way the runtime builds its own.
    # nodes must be exactly list(range(8)) and edges sorted and unique; r1_leg_cases guarantees both.
    built = native_task.make_case(case["edges"], case["route"])
    out.write(native_task.derive_answer(built) + "\\n")
    n += 1
out.close()
print(json.dumps({"side": "runtime", "cases": n}))
"""


def _run(body: str, env_extra: dict, timeout: int) -> dict:
    env = dict(os.environ)
    env.update(env_extra)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([sys.executable, "-B", "-c", textwrap.dedent(body)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env, timeout=timeout)
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()
        return {"_failed": True, "_error": err[-1] if err else "no stderr",
                "_stderr": (proc.stderr or "")[-1500:]}
    return json.loads((proc.stdout or "").strip().splitlines()[-1])


def _digest(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    v3, r6 = (os.path.abspath(p) for p in sys.argv[1:3])
    quiet = "--quiet" in sys.argv
    here = os.path.dirname(os.path.abspath(__file__))
    for path, why in ((os.path.join(v3, "rb"), "rb package"),
                      (os.path.join(r6, "native_task.py"), "native_task.py"),
                      (os.path.join(here, "r1_leg_cases.py"), "r1_leg_cases.py")):
        if not os.path.exists(path):
            print("REFUSED: no %s under %s" % (why, path))
            return 1

    import r1_leg_cases
    expected = sum(1 for _ in r1_leg_cases.generate())
    printed = r1_leg_cases.counts()
    if printed["total"] != expected:
        print("REFUSED: r1_leg_cases.counts() says %d cases and the generator produces %d."
              % (printed["total"], expected))
        print("         A hand-written count that disagrees with reality is worse than no count.")
        return 1
    if not quiet:
        print("=" * 78)
        print("THE APPENDIX-F CANDIDATE, AGAINST THE RUNTIME'S LIVE ORACLE")
        print("=" * 78)
        print("  cases to compare : %d" % expected)
        print("    exhaustive on structure : %d routes of 2, 3 and 4 links over eight nodes,"
              % printed["exhaustive_routes"])
        print("                              crossed with EVERY subset of that route's own legs")
        print("                              = %d cases" % printed["exhaustive_cases"])
        print("    random                  : %d cases on the full eight nodes, routes 2 to 8 links"
              % printed["random_cases"])
        print("    adversarial             : %d cases, every route length, every leg missing in turn"
              % printed["adversarial_cases"])
        print()
        print("  Both sides import the SAME generator module, so a difference in the answers")
        print("  cannot come from a difference in the cases.")
        print()

    brain_out = os.path.join(here, "_candidate_answers.txt")
    oracle_out = os.path.join(here, "_oracle_answers.txt")
    common_env = {"CASES_DIR": here, "PATH": os.environ.get("PATH", "")}

    #: "padding" needs no knowledge of the answer in the bridge; "reference" does. Both are run so
    #: the difference is measured rather than argued.
    encodings = [e for e in ("padding", "reference") if e in sys.argv] or ["padding"]

    if not quiet:
        print("  running the brain side   (no torch)...")
    results = {}
    for encoding in encodings:
        brain = _run(BRAIN_SIDE, {**common_env, "OUT_PATH": brain_out, "PYTHONPATH": v3,
                                  "ENCODING": encoding}, timeout=7200)
        if brain.get("_failed"):
            print("  FAILED on the brain side (%s): %s" % (encoding, brain["_error"]))
            print(brain.get("_stderr", ""))
            return 1
        if not quiet:
            print("    %-10s %d cases, %d gated, bridge used the reference cell: %s"
                  % (encoding, brain["cases"], brain["gated"], bool(brain["used_reference_cell"])))
        results[encoding] = (brain, [ln for ln in open(brain_out, encoding="utf-8").read().splitlines()])
        if len(encodings) > 1:
            # Keep each encoding's answers so the second run does not overwrite the first.
            stored = os.path.join(here, "_answers_%s.txt" % encoding)
            with open(stored, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(results[encoding][1]) + "\n")

    if not quiet:
        print("  running the oracle side  (torch)...")
    oracle = _run(RUNTIME_SIDE, {**common_env, "OUT_PATH": oracle_out,
                                 "PYTHONPATH": os.pathsep.join([r6, v3])}, timeout=7200)
    if oracle.get("_failed"):
        print("  FAILED on the oracle side: %s" % oracle["_error"])
        print(oracle.get("_stderr", ""))
        return 1
    if not quiet:
        print("    %d cases" % oracle["cases"])

    a_oracle = open(oracle_out, encoding="utf-8").read().splitlines()
    print()
    print("  the oracle side  : %d answers  (sha256 %s)" % (len(a_oracle), _digest(oracle_out)[:16]))

    failures = 0
    for encoding in encodings:
        brain, a_brain = results[encoding]
        print()
        print("  --- encoding: %s ---" % encoding)
        print("  the brain side   : %d answers  (sha256 %s)"
              % (len(a_brain), _digest(os.path.join(here, "_answers_%s.txt" % encoding))[:16]
                 if len(encodings) > 1 else _digest(brain_out)[:16]))
        if len(a_brain) != len(a_oracle):
            print("  REFUSED: the two sides produced different numbers of answers (%d against %d),"
                  % (len(a_brain), len(a_oracle)))
            print("  so they did not see the same cases and no comparison is meaningful.")
            failures += 1
            continue
        disagreements = [(i, b, o) for i, (b, o) in enumerate(zip(a_brain, a_oracle)) if b != o]
        print("  cases compared   : %d" % len(a_brain))
        print("  disagreements    : %d" % len(disagreements))
        print("  gated            : %d" % brain["gated"])
        if disagreements:
            failures += 1
            print("  the first disagreements, by index:")
            for i, b, o in disagreements[:10]:
                print("    case %8d  candidate %-28s oracle %s" % (i, b, o))
        print("  verdict          : %s" % ("AGREES with the oracle on every case" if not disagreements
                                           else "DISAGREES"))

    print()
    print("=" * 78)
    print("RESULT")
    if failures:
        print("  NOT PROVED: %d encoding(s) disagreed or could not be compared." % failures)
    else:
        print("  PROVED for: %s" % ", ".join(encodings))
        print()
        if "padding" in encodings:
            print("  The PADDING encoding needs no knowledge of the answer in the bridge. The bridge")
            print("  writes a per-leg membership value and ONE constant, and the brain's own argument")
            print("  of the minimum discovers whether every leg is present. So the reference cell")
            print("  that RT_SHIM_NO_MATH was about is not needed at all.")
        print("  This proves the ARITHMETIC. It does not by itself approve the encoding for a run.")
    print("=" * 78)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
