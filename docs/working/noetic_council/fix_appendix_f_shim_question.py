"""Point appendix F sections 7 and 9 at the padding encoding, which answers the question they leave open.

WHAT CHANGES
------------
- Section 7's heading and its closing paragraph call the `RT_SHIM_NO_MATH` question open. The padding
  encoding dissolves it, so they now say so and point at section 8.
- Section 9's item 1 said the same question "matters, and it is not a measurement". It is now
  answered, so the old text is kept struck through and the answer replaces it.

Idempotent: re-running finds the text already updated and does nothing.

Usage:
    C:\\Python314\\python.exe -B fix_appendix_f_shim_question.py <worktree> [--check]
"""
from __future__ import annotations

import sys
from pathlib import Path

FILE = "R1_RT_DESIGN_APPENDIX_F_INPUT_RULE_FALSIFIED_2026_10_16.md"

HEADING_OLD = "## 7. A candidate repair: its arithmetic is measured, its permission is not"
HEADING_NEW = ("## 7. A candidate repair: its arithmetic is measured, its permission is not\n"
               "*(the reference cell described here is no longer needed — see the padding encoding "
               "in section 8)*")

PARA_OLD = """**What is NOT measured, and is the whole remaining question.** The reference cell has to know whether
*every* leg is present. That is a conjunction over the same facts the rule already reads, so it may be
legitimate — but it is closer to the answer than anything else in the bridge, and `RT_SHIM_NO_MATH`
exists to draw exactly that line. **Whether it crosses the line is a design question and is not
decided here.** The candidate also changes appendix A, which is frozen, so it would need its own
freeze and the owner's line before any run."""

PARA_NEW = """**What was NOT measured here, and how it was resolved.** The reference cell has to know whether
*every* leg is present. That is a conjunction over the same facts the rule already reads, so it may be
legitimate — but it is closer to the answer than anything else in the bridge, and `RT_SHIM_NO_MATH`
exists to draw exactly that line. **That was a design question and it is no longer one.** Section 8
shows the reference cell is unnecessary: a constant in the always-present spare region does its job,
and the bridge then holds no part of the answer. The encoding described in this section is kept
because it is one of the two the proof ran against, and it agrees with the oracle on the same 323,851
cases. The candidate still changes appendix A, which is frozen, so it needs its own freeze and the
owner's line before any run."""

ITEM_1_OLD = """1. Whether the candidate in section 7 survives the `RT_SHIM_NO_MATH` line. **This is the one that
   matters, and it is not a measurement.**"""

ITEM_1_NEW = """1. ~~Whether the candidate in section 7 survives the `RT_SHIM_NO_MATH` line. This is the one that
   matters, and it is not a measurement.~~ **DISSOLVED by section 8.** The padding encoding needs no
   reference cell, so the bridge writes a per-leg membership value and one constant and holds no part
   of the answer. The question was not decided; the thing it was about turned out to be unnecessary."""


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = Path(sys.argv[1]) / "docs" / "working" / "noetic_council" / FILE
    if not target.is_file():
        print("REFUSED: no appendix F at %s" % target)
        return 1
    text = target.read_text(encoding="utf-8")

    if HEADING_NEW in text and ITEM_1_NEW in text:
        print("sections 7 and 9 already point at the padding encoding; nothing to do")
        return 0
    if "--check" in sys.argv:
        print("NEEDS UPDATING")
        return 1

    problems = []
    if HEADING_OLD not in text:
        problems.append("section 7's heading note is neither needed nor present")
    if PARA_OLD not in text:
        problems.append("section 7's closing paragraph is not where it was")
    if ITEM_1_OLD not in text:
        problems.append("section 9's item 1 is not where it was")
    if problems:
        for p in problems:
            print("REFUSED: %s" % p)
        return 1

    text = text.replace(HEADING_OLD, HEADING_NEW, 1)
    text = text.replace(PARA_OLD, PARA_NEW, 1)
    text = text.replace(ITEM_1_OLD, ITEM_1_NEW, 1)
    target.write_text(text, encoding="utf-8")
    print("WROTE %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
