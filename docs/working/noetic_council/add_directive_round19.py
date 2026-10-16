"""Add the round-19 amendment-log row: the brain answered a real runtime tick.

IDEMPOTENT PER ROW, guard is the ROW ITSELF. Rows go ABOVE the round-13 anchor.

Usage:
    C:\\Python314\\python.exe -B add_directive_round19.py <worktree> [--list]
"""
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = "| 2026-10-16 | **Third target added: `HELM_R1_RT_HOSTED`**"

ROWS = [
    (
        "the brain answered a real runtime tick",
        "| 2026-10-16 | **THE BRAIN ANSWERED A REAL RUNTIME TICK. The mechanism is finished.** The "
        "two halves proved separately \u2014 the runtime calling a client operation (appendix G) and "
        "the brain answering across a process boundary (appendix H) \u2014 have been joined and run. "
        "One `runtime._prepare_inference` call now produces a tensor whose decoded symbol is the "
        "recipe brain's answer, read back through **the runtime's own decoder** rather than by "
        "inspecting the tensor. Three ticks, three different cases: **3 of 3 agreed**, with **three "
        "distinct symbols**, so a client returning a fixed value cannot pass. The worker never held "
        "torch (its own report). The bank was left empty. Peak **221.6 MiB** of the 300 MiB laptop "
        "rule. **The join needed no new edits** \u2014 the three from appendix G were enough, and the "
        "client slotted into the operation position the runtime was already calling. Recorded as "
        "appendix I. |",
    ),
    (
        "what the hosted tick does not establish",
        "| 2026-10-16 | **What the hosted tick does NOT establish, recorded because the result is "
        "easy to read wider than it is.** (1) **It is not a result on the exam** \u2014 three "
        "hand-written cases prove the mechanism, not a mark, and nothing here upgrades or touches "
        "wave 1's reading. (2) **The decoder is the design's, not the task's** \u2014 "
        "`native_task.task_decoder_contracts` pins `^6`, so the task's own contract could not be "
        "used; a run that claims the task needs a version-2 contract **and** its exact semantic "
        "lineage, which `_semantic_lineage` validates field by field. (3) **No durability, no "
        "restart, no nested repair** \u2014 nothing was written to the store, so the halves of the "
        "target sentence beyond the answers are untouched. (4) **It ran on copies** \u2014 the frozen "
        "source is unchanged at 0 of 34, 0 of 29 and 0 of 11. (5) **The envelope is not re-costed** "
        "\u2014 appendix H gives the boundary cost, but a hosted tick also pays the runtime's own "
        "overhead, which this probe does not separate out. |",
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
        for label, row in ROWS:
            print("%-8s %s" % ("PRESENT" if row in text else "ABSENT", label))
        return 0

    if len({r for _l, r in ROWS}) != len(ROWS):
        print("REFUSED: two rows are identical, so the presence test cannot count insertions.")
        return 1

    missing = [(label, row) for label, row in ROWS if row not in text]
    if not missing:
        print("all %d rows are already present; nothing to do" % len(ROWS))
        return 0
    if ANCHOR not in text:
        print("REFUSED: anchor not found: %r" % ANCHOR)
        return 1
    if text.count(ANCHOR) != 1:
        print("REFUSED: anchor appears %d times" % text.count(ANCHOR))
        return 1

    block = "".join(row + "\n" for _l, row in missing)
    target.write_text(text.replace(ANCHOR, block + ANCHOR), encoding="utf-8")
    for label, _row in missing:
        print("ADDED   %s" % label)
    print("WROTE %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
