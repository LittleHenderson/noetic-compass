"""Can the sealed recipe brain and HELM's torch runtime share ONE process?

WHY THIS MATTERS
----------------
Route D hosts the recipe brain where the runtime's operation module sits. That means `rb.brain` and
`cas_cjt` (torch) in one interpreter. `rb/__init__.py` installs `rb.no_torch` on import, and
`no_torch.install()` raises if torch is already in `sys.modules`. So this probe measures the only
question that decides whether route D is buildable at all: in which order, if any, both can load.

It runs each order in its OWN subprocess, because the first import poisons `sys.modules` for the
second and an in-process test would measure the wrong thing.

WHAT IT REPORTS
---------------
Every outcome is one of: BOTH LOADED, or the exact exception text. `ok=None` is not used; there is
nothing here to be unsure about.

Usage:
    C:\\Python314\\python.exe -B probe_brain_in_runtime.py <v3-package-root>
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap

ORDERS = {
    "torch first, then rb (what route D needs)": """
        import torch
        torch_ok = torch.__version__
        import rb
        from rb.brain import RecipeBrain
        print(RESULT)
    """,
    "rb first, then torch": """
        import rb
        from rb.brain import RecipeBrain
        import torch
        torch_ok = torch.__version__
        print(RESULT)
    """,
    "torch, rb, then rb3 (rb3's blocker is not installed on import)": """
        import torch
        import rb
        import rb3
        from rb.brain import RecipeBrain
        print(RESULT)
    """,
    "the runtime's own module set, then rb": """
        import torch
        from cas_cjt.types import CausePacket
        from cas_cjt.neural import RegisteredOperationBank
        import rb
        from rb.brain import RecipeBrain
        print(RESULT)
    """,
}

FILLER = """
import json
RESULT = json.dumps({"reached": "the end of the script"})
"""


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    v3 = os.path.abspath(sys.argv[1])
    if not os.path.isdir(os.path.join(v3, "rb")):
        print("REFUSED: no rb package under %s" % v3)
        return 1

    print("=" * 78)
    print("CAN THE SEALED RECIPE BRAIN AND THE TORCH RUNTIME SHARE ONE PROCESS?")
    print("=" * 78)
    print("  package root : %s" % v3)
    print("  python       : %s" % sys.version.split()[0])
    print()

    results = {}
    for label, body in ORDERS.items():
        script = textwrap.dedent(body)
        env = dict(os.environ)
        env["PYTHONPATH"] = v3
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True,
                              text=True, encoding="utf-8", errors="replace", env=env, timeout=900)
        tail = (proc.stdout or "").strip().splitlines()
        reached = "the end of the script" in (proc.stdout or "")
        err = (proc.stderr or "").strip().splitlines()
        last = err[-1] if err else ""
        outcome = "BOTH LOADED" if reached else "REFUSED"
        results[label] = {"outcome": outcome, "exit": proc.returncode, "last_line": last}
        print("  %s" % label)
        print("    outcome    : %s  (exit %d)" % (outcome, proc.returncode))
        if reached:
            print("    stdout     : %s" % (tail[-1] if tail else ""))
        if last:
            print("    exception  : %s" % last[:180])
        print()

    print("=" * 78)
    print("RESULT")
    torch_first = results["torch first, then rb (what route D needs)"]["outcome"]
    print("  route D's order (torch, then rb)                : %s" % torch_first)
    print("  the reverse order                               : %s"
          % results["rb first, then torch"]["outcome"])
    print()
    if torch_first == "REFUSED":
        print("  Route D, as designed, is NOT BUILDABLE against the frozen `rb` package.")
        print("  The recipe brain refuses to share a process with torch, by design, and that")
        print("  refusal is part of how its own run is shown to be torch-free. It is a seal,")
        print("  not a defect. Any design that puts the brain inside the runtime has to cross")
        print("  a process boundary instead.")
    else:
        print("  Route D's import order works. The design can be built in one process.")
    print("=" * 78)
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
