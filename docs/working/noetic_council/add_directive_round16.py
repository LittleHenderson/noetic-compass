"""Add the round-16 amendment-log rows to the council directive.

IDEMPOTENT PER ROW, and the guard is the ROW ITSELF — `row in text`, not a hand-written marker beside
it. Round 15 shipped a marker-based guard three times and all three markers could never match the
text they guarded. A row cannot fail to contain itself.

Rows are inserted ABOVE the round-13 anchor, so the log stays newest-first.

Usage:
    C:\\Python314\\python.exe -B add_directive_round16.py <worktree> [--list]
"""
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = "| 2026-10-16 | **Third target added: `HELM_R1_RT_HOSTED`**"

#: (a short label FOR DISPLAY ONLY, the row to insert verbatim).
ROWS = [
    (
        "the candidate proved against the live oracle",
        "| 2026-10-16 | **The appendix-F candidate proved against the runtime's own LIVE oracle: "
        "323,851 cases, 0 disagreements, 0 gated.** The two answer streams are **byte-identical**, "
        "sha256 `c591c5685b84f96ae2ab05ceedc4720ccabc16efd68ab9d908832ecf9383dd8e` \u2014 one "
        "written by a process holding a live `RecipeBrain` with no torch, the other by a process "
        "holding the live `native_task`. They cannot share an interpreter (appendix E), so the "
        "comparison crosses the process boundary the design already has to cross. Coverage: "
        "exhaustive on structure for routes of 2, 3 and 4 links \u2014 8,736 routes over eight nodes "
        "crossed with EVERY subset of that route's own legs = **122,304** cases \u2014 plus 200,000 "
        "random and 1,547 adversarial. All eight labels occur, so the comparison is not vacuous. "
        "Evidence manifest: `CANDIDATE_VS_ORACLE_EVIDENCE_2026_10_16.json`. |",
    ),
    (
        "why this is stronger than appendix A's own proof",
        "| 2026-10-16 | **Why the new proof is stronger than appendix A's own, and why the old one "
        "could not simply be reused.** Appendix A's 118,304-case comparison put a hand-written copy "
        "of the oracle against a hand-written copy of the rule, in one file, with no brain and no "
        "runtime. It showed the two **rules** agree; it could not show that the live brain obeys its "
        "own rule, and appendix F is precisely the finding that it does not. Separately, appendix "
        "A's exhaustive half uses **four-node** cases, which the live oracle **refuses**: "
        "`native_task.validate_case` requires `case[\"nodes\"] == list(range(8))` exactly "
        "(`native_task.py:71-72`). That half can never be handed to `derive_answer` at all. |",
    ),
    (
        "two arithmetic errors found while writing the proof",
        "| 2026-10-16 | **Two arithmetic errors of my own, both found by running rather than "
        "reading, both fixed at the source of the error.** **First:** `r1_leg_cases.counts()` "
        "hard-coded the exhaustive total as **122,976** when it is **122,304** \u2014 the wrong "
        "powers of two were used. The counts are now computed from the same constants the generator "
        "uses, and `prove_candidate_vs_oracle.py` **refuses** if `counts()` disagrees with the "
        "generator's actual output, so a hand-typed number cannot survive again. The same defect had "
        "already been written into the docstring. **Second:** the first draft of appendix F section 8 "
        "had the ORACLE's hash typed by hand and got it wrong by one character, `ae2cab` where the "
        "file says `ae2ab`. A wrong hash in a record is worse than no hash because it looks "
        "checkable. The section is now written from the artefact: the script reads the digest from "
        "the answer files and **refuses** if both are not present and identical. |",
    ),
    (
        "an ordering defect in the appendix itself",
        "| 2026-10-16 | **An ordering defect in the appendix, and a repair that over-engineered it.** "
        "The proof section was inserted above \"What is not known\", so the headings read 1..7, 9, 8. "
        "The physical order was already right \u2014 the proof belongs before the remaining unknowns "
        "\u2014 so the repair was a renumbering in place. The **first version of the fix script moved "
        "the proof block to the end of the file**, which reproduced 1..7, 9, 8 from the other side. "
        "Found by reading the headings back after running it. It now renumbers in place and is "
        "idempotent. |",
    ),
    (
        "the reference cell is unnecessary",
        "| 2026-10-16 | **The one open design question DISSOLVED rather than decided: the reference "
        "cell is unnecessary.** Appendix F's remaining question was whether the reference cell "
        "crosses `RT_SHIM_NO_MATH`, since it has to know whether *every* leg is present. A route has "
        "at most seven legs and `CELLS` is eight, so **a spare cell always exists**. Put a constant "
        "`1.5` in the spare region, strictly between the two leg values (`3` present, `1` missing): "
        "with every leg present the minimum is `1.5` and the first cell attaining it is the first "
        "spare cell, index `k`; with leg `j` missing the minimum is `1` and the first cell attaining "
        "it is `j`; and the minimum is never `0`, so G2 does not fire. **The bridge writes a per-leg "
        "membership value and ONE constant. It computes no conjunction and holds no part of the "
        "answer.** Both encodings ran against the live oracle on the same 323,851 cases: **0 "
        "disagreements, 0 gated**, and all three answer streams \u2014 padding, reference, and the "
        "oracle \u2014 are **byte-identical** at "
        "`c591c5685b84f96ae2ab05ceedc4720ccabc16efd68ab9d908832ecf9383dd8e`. |",
    ),
    (
        "a refactor that gave both encodings one mapping",
        "| 2026-10-16 | **A defect in my own refactor, caught by the digest and kept on the page.** "
        "Refactoring the proof to carry both encodings, I gave **both** of them the padding layout's "
        "cell mapping. The padding encoding then agreed on all 323,851 cases and the reference "
        "encoding **disagreed on all 323,851**, because its reference cell sits at index 0 and its "
        "legs at `1..k`. The disagreement was the refactor's bug, not a property of the encoding, and "
        "it was visible immediately as two different digests \u2014 `d1d4c303` against the oracle's "
        "`c591c568`. Each encoding now carries its own mapping and both reproduce the oracle's digest "
        "exactly. Recorded because a disagreement on EVERY case is the signature of a coding error, "
        "not of a wrong idea, and the next reader should not have to rediscover that. |",
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

    # The guard is the row itself. The remaining way this can go wrong is two identical rows.
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
