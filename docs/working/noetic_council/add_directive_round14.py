"""Add the round-14 amendment-log rows to the council directive.

IDEMPOTENT PER ROW. The first version of this script guarded on one marker for the whole block, and
that guard wrongly blocked two new rows because the marker it looked for had already been added by an
earlier merge. Each row is now checked against its own marker and inserted only if absent, so rows can
be added in any order and re-running never duplicates or drops one.

Rows are appended ABOVE the round-13 anchor, so the log stays newest-first.

Usage:
    C:\\Python314\\python.exe -B add_directive_round14.py <worktree> [--list]
"""
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = "| 2026-10-16 | **Third target added: `HELM_R1_RT_HOSTED`**"

#: (marker that proves this row is already present, the row itself)
ROWS = [
    (
        "Route D's central assumption falsified by measurement",
        "| 2026-10-16 | **Route D's central assumption falsified by measurement, and recorded as "
        "appendix E rather than quietly dropped.** The design assumed the sealed recipe brain could be "
        "hosted in the runtime's own process. It cannot: `rb/__init__.py` installs a blocker on import "
        "whose `install()` raises if torch is already loaded, and once installed the blocker refuses any "
        "later `import torch`. **All four import orders were refused**, each run in its own subprocess, "
        "and `numpy` rides in with torch so there is no partial order. Route D as designed is not "
        "buildable. The refusal is not an obstacle to route around: it is how the brain's own run is "
        "shown to be torch-free, and the package is frozen. HELM's own `rb3` package resolves the same "
        "shape the other way, on purpose, and says so in its docstring. |",
    ),
    (
        "What the falsification does not cost",
        "| 2026-10-16 | **What the falsification does not cost.** Appendix A, B and C are unchanged. "
        "Appendix D's patch is unchanged, tested and now **necessary rather than convenient**: across a "
        "process boundary the in-runtime operation becomes the brain's client, and a client has to send "
        "the question, so `cause.content` reaching the operation is the only way it can know what to "
        "ask. The corrected shape is **the patch plus a process boundary**. The envelope must be "
        "re-costed. Four things remain unmeasured and are named in appendix E section 7 rather than "
        "glossed. |",
    ),
    (
        "Three further defects in the runtime-path probe",
        "| 2026-10-16 | **Three further defects in the runtime-path probe, found after the first three "
        "were recorded, and kept as a separate row rather than folded into it.** **Fourth:** the "
        "unpatched-detector asked whether the bank had `_active_case` as an attribute of its class. It "
        "does not, for a correctly patched tree \u2014 the node sets its own holder in `__init__`, but "
        "the bank creates `self._active_case` at **call time** inside `forward` \u2014 so the detector "
        "**aborted a good run**. It now tests the thing the patch changes, the bank's `forward` "
        "signature. **Fifth:** the node's \"was it cleared\" check read the holder inside a wrapper "
        "around `node.forward`, which runs *before* `network.forward_node`'s `finally` clears it, so it "
        "always saw the live case and reported **\"the node was not cleared\"** \u2014 a false "
        "accusation against the patch, which was then confirmed correct once the holder was read after "
        "the whole call. **Sixth:** the negative control asserted a sentinel for a missing argument that "
        "the patched node can never produce, because it always passes its holder down as an explicit "
        "`None`; the control now asserts `None`. Seven probe defects in total across the two versions, "
        "every one found by running it. |",
    ),
]


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = (Path(sys.argv[1]) / "docs" / "working"
              / "helm_tks_noetic_council_directive_2026_10_16.md")
    if not target.is_file():
        print("REFUSED: no directive at %s" % target)
        return 1
    text = target.read_text(encoding="utf-8")

    if "--list" in sys.argv:
        for marker, _row in ROWS:
            print("%-8s %s" % ("PRESENT" if marker in text else "ABSENT", marker))
        return 0

    missing = [(m, r) for m, r in ROWS if m not in text]
    if not missing:
        print("all %d rows are already present; nothing to do" % len(ROWS))
        return 0
    if ANCHOR not in text:
        print("REFUSED: anchor not found: %r" % ANCHOR)
        return 1
    if text.count(ANCHOR) != 1:
        print("REFUSED: anchor appears %d times" % text.count(ANCHOR))
        return 1

    block = "".join(row + "\n" for _m, row in missing)
    target.write_text(text.replace(ANCHOR, block + ANCHOR), encoding="utf-8")
    for marker, _row in missing:
        print("ADDED   %s" % marker)
    print("WROTE %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
