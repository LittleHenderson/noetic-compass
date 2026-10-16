"""Can the recipe brain even NAME the runtime's answers?

WHY THIS EXISTS
---------------
Appendix A froze how a case becomes the brain's ingredients, and it produces one of eight answers:
`FIRST_UNSUPPORTED_LEG_0` through `FIRST_UNSUPPORTED_LEG_6`, or `ALL_LEGS_PRESENT`. That is the
runtime's own `ANSWER_LABELS`, read from `native_task.py:23`.

The recipe brain's readout returns `self.beta[winner]` where `winner` is an index into a list of
`RECIPES` entries. If `RECIPES` is smaller than the task's answer set, then the brain cannot name
every answer the task can have, no matter how the bridge is written. That is a hard limit on the
design, not a tuning problem, so it is worth measuring before anything is built.

This probe reads BOTH numbers from the live objects, in separate subprocesses, because the two
packages cannot share a process at all (appendix E): `rb` refuses torch, and `native_task.py`
imports torch at line 13.

WHAT IT DOES NOT DO
-------------------
It does not decide what to do about a shortfall. It reports the two numbers, their difference, and
which of the runtime's answers are unreachable.

Usage:
    C:\\Python314\\python.exe -B probe_answer_alphabet.py <v3-package-root> <r6-source-root>
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap

#: Reads the BRAIN's side. Must not import torch, and must not import native_task.
BRAIN_SIDE = """
import json
from rb.brain import RecipeBrain
from rb import common
b = RecipeBrain()
report = {
    "recipes": common.RECIPES,
    "brain_labels": list(common.LABELS),
    "beta_slots": len(b.beta),
    "a_rows": len(b.a),
    "cells": common.CELLS,
    "readout_probe": b.readout([0.0] * common.CELLS).as_record(),
}
print(json.dumps(report))
"""

#: Reads the RUNTIME's side. Imports torch, so it must be its own process.
RUNTIME_SIDE = """
import json
import native_task
from cas_cjt import CJTNodeSpec
# Read the decoder contract the runtime itself builds, rather than guessing its name. The first
# version of this probe guessed `build_decoder_contract`, which does not exist, and the probe
# refused instead of reporting a number it had not measured.
specs = (CJTNodeSpec("A", "^6"),)
contract = native_task.task_decoder_contracts(specs)["A"]
report = {
    "task_id": native_task.TASK_ID,
    "answer_labels": list(native_task.ANSWER_LABELS),
    "n_answers": len(native_task.ANSWER_LABELS),
    "decoder": {"labels": list(contract.labels),
                "channel_indices": list(contract.channel_indices),
                "algorithm": contract.algorithm,
                "version": contract.version,
                "input_width": contract.input_width},
}
print(json.dumps(report))
"""


def _run(body: str, env_extra: dict) -> dict:
    env = dict(os.environ)
    env.update(env_extra)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([sys.executable, "-B", "-c", textwrap.dedent(body)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env, timeout=900)
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()
        return {"_failed": True, "_error": err[-1] if err else "no stderr"}
    return json.loads((proc.stdout or "").strip().splitlines()[-1])


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    v3, r6 = (os.path.abspath(p) for p in sys.argv[1:3])
    if not os.path.isdir(os.path.join(v3, "rb")):
        print("REFUSED: no rb package under %s" % v3)
        return 1
    if not os.path.isfile(os.path.join(r6, "native_task.py")):
        print("REFUSED: no native_task.py under %s" % r6)
        return 1

    brain = _run(BRAIN_SIDE, {"PYTHONPATH": v3})
    runtime = _run(RUNTIME_SIDE, {"PYTHONPATH": os.pathsep.join([r6, v3])})

    print("=" * 78)
    print("CAN THE RECIPE BRAIN NAME THE RUNTIME'S ANSWERS?")
    print("=" * 78)
    if brain.get("_failed") or runtime.get("_failed"):
        print("  the brain side   : %s" % (brain.get("_error") or "ok"))
        print("  the runtime side : %s" % (runtime.get("_error") or "ok"))
        print("REFUSED: one side could not be read, so no comparison is made.")
        return 1

    print("  the brain, from rb.common and a live RecipeBrain():")
    print("    RECIPES                 : %d" % brain["recipes"])
    print("    beta slots              : %d" % brain["beta_slots"])
    print("    its own label strings   : %s" % brain["brain_labels"])
    print("    cells                   : %d" % brain["cells"])
    print()
    print("  the runtime, from a live native_task:")
    print("    task_id                 : %s" % runtime["task_id"])
    print("    ANSWER_LABELS           : %d labels" % runtime["n_answers"])
    print("      %s" % ", ".join(runtime["answer_labels"]))
    print("    the decoder's labels    : %s" % runtime["decoder"]["labels"])
    print("    the decoder's channels  : %s" % runtime["decoder"]["channel_indices"])
    print("    the decoder's algorithm : %s" % runtime["decoder"]["algorithm"])
    print()

    # A single readout returns exactly one `beta[winner]`. Distinct answers a readout can produce
    # are therefore bounded by the number of beta slots, whatever those slots are set to.
    reachable_max = brain["beta_slots"]
    needed = runtime["n_answers"]
    shortfall = needed - reachable_max
    print("  ONE readout returns exactly one beta[winner].")
    print("  So the distinct answers ANY readout can name is at most the beta slots: %d."
          % reachable_max)
    print("  The runtime's answer set has %d." % needed)
    print()
    print("=" * 78)
    print("RESULT")
    if shortfall > 0:
        print("  SHORTFALL: %d answer(s) the task can produce can NEVER be named by this brain."
              % shortfall)
        print("  The unreachable ones depend on which labels the four betas are set to. With the")
        print("  first four, these four can never be produced:")
        print("    %s" % ", ".join(runtime["answer_labels"][reachable_max:]))
        print()
        print("  This is a limit of the frozen brain, not of the bridge. `RECIPES` is 4 and the")
        print("  answer alphabet is %d. Closing the gap needs either a wider brain (a new seal on a"
              % needed)
        print("  frozen package) or arithmetic in the shim, which the design's own RT_SHIM_NO_MATH")
        print("  rule forbids.")
    else:
        print("  NO SHORTFALL: the brain has at least as many beta slots as the task has answers.")
    print("=" * 78)
    print(json.dumps({"brain": brain, "runtime": runtime,
                      "reachable_max": reachable_max, "needed": needed,
                      "shortfall": shortfall}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
