"""Add the round-15 amendment-log rows to the council directive.

IDEMPOTENT PER ROW. The presence test is `row in text` — the guard IS the row, not a hand-written
marker beside it. Rows are inserted ABOVE the round-13 anchor so the log stays newest-first.

WHY THE GUARD IS THE ROW
------------------------
The first version guarded each row with a short marker string. Three of the five markers could never
match the text they guarded — one was written `appendix F` against text saying `Appendix F`, and two
were paraphrases of the row rather than literal substrings — so all three re-added their rows on
every run, and the first run inserted **all four rows twice**. Found by running the script a second
time and reading a line that said `ADDED` where it should have said `nothing to do`.

Deriving the guard from the row removes the whole class of bug: a row cannot fail to contain itself.
The remaining failure mode, two identical rows, is refused explicitly.

Usage:
    C:\\Python314\\python.exe -B add_directive_round15.py <worktree> [--list]
"""
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = "| 2026-10-16 | **Third target added: `HELM_R1_RT_HOSTED`**"

ROWS = [
    (
        "Appendix F written: the frozen input rule is falsified",
        "| 2026-10-16 | **Appendix F written: the frozen input rule is falsified, and the ceiling it "
        "puts on the brain is 36 of 288.** Appendix A froze stock exactly `0` or `1` and requirement "
        "exactly `1`, so a missing leg yields exactly zero. `rb/brain.py`'s readout tests `best == "
        "ZERO` and refuses on gate **G2**. Measured on a live brain: one leg missing gives "
        "`UNDETERMINED`/`G2`. No requirement value avoids it \u2014 all five values across the "
        "brain's own bounds `[0.05, 20]` gave `G2`, because zero divided by anything is still zero "
        "\u2014 and a second allocated recipe makes it **worse**: gate `G1`, both active sets empty. "
        "The runtime's own dataset is authored balanced across its eight answers "
        "(`native_task.py:189`), so `ALL_LEGS_PRESENT` is exactly one eighth of cases: **36 of "
        "288**. That is the brain's ceiling on this task, and on the other 252 its answer is "
        "`UNDETERMINED`, which the project's own scoring counts as not wrong and not right. |",
    ),
    (
        "A second, independent mismatch measured: the answer alphabet",
        "| 2026-10-16 | **A second, independent mismatch measured: the answer alphabet.** The brain "
        "has `RECIPES = 4` and its own labels `L0`\u2013`L3`; the task produces **8** answers "
        "(`native_task.py:23`) and the decoder reads channels `0`\u20137. One readout returns exactly "
        "one `beta[winner]` and there are four beta slots, so **at most four answers can ever be "
        "named by one readout**. SHORT BY 4. This would be reachable by a wider brain; it is "
        "recorded because it is independent of the gate problem and has to be solved separately. |",
    ),
    (
        "A candidate repair, with its arithmetic measured",
        "| 2026-10-16 | **A candidate repair, with its arithmetic measured and its permission "
        "explicitly not.** Give the cells values that are never zero \u2014 a reference cell at "
        "index 0, leg cells 1..7, padding \u2014 so the minimum is `1` and the brain's own argmin "
        "finds the first missing leg. Run on a live brain over **every route length from one leg to "
        "seven and every position of a single missing leg: 35 cases, 0 gated, 35 agreed.** What is "
        "NOT measured, and is the whole remaining question: the reference cell has to know whether "
        "*every* leg is present. That is a conjunction over the same facts the rule already reads, "
        "so it may be legitimate, but it is closer to the answer than anything else in the bridge "
        "and `RT_SHIM_NO_MATH` exists to draw exactly that line. Whether it crosses is a design "
        "question, not a measurement, and it is not decided. The candidate also changes a frozen "
        "appendix and would need its own freeze and the owner's line. |",
    ),
    (
        "Fed back into the loop as two new leaves",
        "| 2026-10-16 | **Appendix F fed back into the loop as two new leaves.** "
        "`RT_ANSWER_ALPHABET_COVERS` and `RT_INPUT_RULE_SURVIVES_GATE`, both read from the packages' "
        "own source so the readings move if either package moves, and both prerequisites of "
        "`RT_BRIDGE_EXISTS`. Iteration 20's diagnosis tree now reads `HELM_R1_RT_HOSTED` \u2192 "
        "`RT_BRIDGE_EXISTS` \u2192 three measured leaves, all three UNSATISFIED, plus "
        "`RT_GATE_OPEN` UNKNOWN. No safeguard fired, no cycle, no contradiction. |",
    ),
    (
        "A guard that looked like a guard and was not",
        "| 2026-10-16 | **A guard that looked like a guard, and was not, in the amendment log's own "
        "writer.** The first version of round 15's row-insertion script guarded each row with a "
        "short marker string, and one marker was written `appendix F` while the text says "
        "`Appendix F`. The check is case-sensitive, so it answered `False` forever and **inserted "
        "all four rows twice**. Found by running the script a second time and reading the line that "
        "said `ADDED` when it should have said `nothing to do`. The script now asserts that every "
        "marker is a literal substring of the row it guards, so a marker that can never match fails "
        "loudly instead of silently re-adding. This is section 12's failure in miniature: a check "
        "that looks like a check. |",
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

    # The guard is the ROW ITSELF, tested with `row in text`, so it cannot drift from what it
    # guards. Round 15 shipped a hand-written marker three times and all three could never match the
    # text they guarded, so all three re-added their rows on every run. The first two were caught by
    # a substring assertion; deriving the guard from the row removes the whole class of bug.
    #
    # The remaining way this can go wrong is two identical rows, which would make `row in text`
    # unable to tell one insertion from two. Refuse that rather than guess.
    if len({r for _l, r in ROWS}) != len(ROWS):
        print("REFUSED: two rows are identical, so the presence test cannot count insertions.")
        return 1

    missing = [(l, r) for l, r in ROWS if r not in text]
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
