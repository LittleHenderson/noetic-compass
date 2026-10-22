"""Renumber appendix F's last two sections and refresh the unknown that is now answered.

WHY THIS EXISTS
---------------
The proof section (§9) was inserted ABOVE "What is not known" (§8), so the headings read 1..7, 9, 8.

**The physical order was already right** — the proof belongs before the remaining unknowns — so the
repair is a renumbering in place: the proof becomes §8 and the unknowns become §9. The first version
of this script moved the proof block to the end of the file instead, which produced 1..7, 9, 8 all
over again from the other side. Found by reading the headings back after running it.

The unknowns list is also refreshed: its item 4 asked whether the candidate could be proved against
the runtime's own oracle, which the proof section now answers. The old text is kept, struck through,
rather than deleted.

Idempotent: re-running finds the headings already correct and does nothing.

Usage:
    C:\\Python314\\python.exe -B fix_appendix_f_order.py <worktree> [--check]
"""
from __future__ import annotations

import sys
from pathlib import Path

FILE = "R1_RT_DESIGN_APPENDIX_F_INPUT_RULE_FALSIFIED_2026_10_16.md"

PROOF_OLD = "## 9. The candidate's arithmetic, proved against the runtime's own LIVE oracle"
PROOF_NEW = "## 8. The candidate's arithmetic, proved against the runtime's own LIVE oracle"
UNKNOWN_OLD = "## 8. What is not known"
UNKNOWN_NEW = "## 9. What is not known"

OLD_ITEM_4 = """4. Whether the candidate can be proved **equivalent to the runtime's own oracle** the way appendix A
   was proved, over the same 118,304 cases. Appendix A's proof is the reason a hosted run's answer
   could be trusted; the candidate currently has 35 cases and no oracle comparison."""

NEW_ITEM_4 = """4. ~~Whether the candidate can be proved equivalent to the runtime's own oracle the way appendix A
   was proved, over the same 118,304 cases.~~ **ANSWERED by section 8: it was proved on 323,851
   cases with 0 disagreements, against the LIVE oracle rather than a transcription.** What remains
   open is not agreement but coverage: the long routes are random and adversarial rather than
   exhaustive, and full exhaustion is about 2.6e7 cases."""


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = Path(sys.argv[1]) / "docs" / "working" / "noetic_council" / FILE
    if not target.is_file():
        print("REFUSED: no appendix F at %s" % target)
        return 1
    text = target.read_text(encoding="utf-8")

    if PROOF_NEW in text and UNKNOWN_NEW in text:
        print("the headings are already renumbered; nothing to do")
        return 0
    if "--check" in sys.argv:
        print("NEEDS FIXING")
        return 1

    for old, new, label in ((PROOF_OLD, PROOF_NEW, "the proof section"),
                            (UNKNOWN_OLD, UNKNOWN_NEW, "the unknowns section")):
        if old not in text:
            print("REFUSED: cannot find %s (%r)" % (label, old))
            return 1
        if text.count(old) != 1:
            print("REFUSED: %s appears %d times" % (label, text.count(old)))
            return 1

    # Renumber the unknowns FIRST. Doing it second would make the proof's old heading ambiguous,
    # because renaming the unknowns to `## 9.` would then collide with the proof's `## 9.`.
    text = text.replace(UNKNOWN_OLD, UNKNOWN_NEW, 1)
    text = text.replace(PROOF_OLD, PROOF_NEW, 1)

    if OLD_ITEM_4 in text:
        text = text.replace(OLD_ITEM_4, NEW_ITEM_4, 1)
        print("refreshed the unknowns list item 4")
    elif NEW_ITEM_4.splitlines()[0] not in text:
        print("WARNING: item 4 was neither found nor already refreshed; headings were renumbered")

    target.write_text(text, encoding="utf-8")
    print("WROTE %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
