"""Append to appendix F: the candidate's arithmetic proved against the live oracle.

Idempotent: appends one section once, verified by the section's own heading. Refuses rather than
guessing if the anchor is missing or appears more than once.

Usage:
    C:\\Python314\\python.exe -B add_appendix_f_proof.py <worktree> [--list]
"""
from __future__ import annotations

import sys
from pathlib import Path

FILE = "R1_RT_DESIGN_APPENDIX_F_INPUT_RULE_FALSIFIED_2026_10_16.md"
#: The section is inserted just above this heading, so it lands after section 8.
ANCHOR = "## 8. What is not known"
HEADING = "## 9. The candidate's arithmetic, proved against the runtime's own LIVE oracle"

SECTION = """## 9. The candidate's arithmetic, proved against the runtime's own LIVE oracle

**Date:** 2026-10-16. **Status:** the arithmetic in section 7 now agrees with the runtime's own oracle
on every case tried, using the **live** recipe brain and the **live** `native_task` — not
transcriptions of them.

| | |
|---|---|
| cases compared | **323,851** |
| disagreements | **0** |
| cases the brain could not answer (gated) | **0** |
| sha256 of the candidate's answers | `{DIGEST}` |
| sha256 of the oracle's answers | `{DIGEST}` |

The two answer streams are **byte-identical**, not merely equal case by case. One file was written by
a process that has never seen torch and holds a live `RecipeBrain`; the other by a process holding the
live `native_task`. They cannot share an interpreter (appendix E), so the comparison crosses the
process boundary the design already has to cross.

Reproduce with `prove_candidate_vs_oracle.py <v3-package-root> <r6-source-root>`.

<!-- DIGESTS-VERIFIED-BY-THE-WRITER -->

### Why this is stronger than appendix A's own proof

Appendix A's 118,304-case comparison put a hand-written copy of the oracle against a hand-written copy
of the rule, in one file, with no brain and no runtime. It showed the two **rules** agree. It could not
show that the live brain obeys its own rule — and section 2 of this appendix is precisely the finding
that it does not. This run uses the live objects, so it can fail for the reason that matters.

There is a second reason appendix A's proof could not have been reused as it stood: its exhaustive
part uses cases on **four** nodes, and the live oracle **refuses** them. `native_task.validate_case`
requires `case["nodes"] == list(range(8))` exactly (`native_task.py:71-72`). So the old proof's
exhaustive half can never be handed to `derive_answer` at all.

### What was covered, and why it is enough

`native_task.derive_answer` reads one thing: whether each **route leg** is a member of the edge set.
Edges outside the route never affect the answer. The task's answer function therefore has exactly two
inputs — the route, and which of the route's legs are present — and the coverage targets both:

| part | cases | what it covers |
|---|---|---|
| exhaustive on structure | **122,304** | every route of 2, 3 and 4 links over eight nodes — 8,736 routes — crossed with **every** subset of that route's own legs |
| random | **200,000** | the full eight nodes, random edge subsets, routes of 2 to 8 links, fixed seed |
| adversarial | **1,547** | every route length: all legs present, each leg missing in turn, and all legs missing |

The exhaustive part leaves nothing about a short route untried. The long routes cannot be exhausted on
a laptop — full exhaustion is every route of 2 to 8 links crossed with every leg subset, roughly
2.6e7 cases — so they are covered by 200,000 random cases plus the adversarial set.

The comparison is not vacuous. Every one of the eight labels occurs in the answers:

| label | count |
|---|---|
| `ALL_LEGS_PRESENT` | 29,915 |
| `FIRST_UNSUPPORTED_LEG_0` | 183,367 |
| `FIRST_UNSUPPORTED_LEG_1` | 69,487 |
| `FIRST_UNSUPPORTED_LEG_2` | 28,271 |
| `FIRST_UNSUPPORTED_LEG_3` | 11,770 |
| `FIRST_UNSUPPORTED_LEG_4` | 828 |
| `FIRST_UNSUPPORTED_LEG_5` | 174 |
| `FIRST_UNSUPPORTED_LEG_6` | 39 |

### What this does NOT establish

1. **It does not decide whether the candidate is allowed.** The reference cell is part of the thing
   being proved, so this shows the arithmetic agrees with the oracle — not that the design's own
   `RT_SHIM_NO_MATH` line permits a reference cell. That is still the open question, and it is still a
   design question rather than a measurement.
2. **It does not cover the long routes exhaustively.** Stated above rather than glossed.
3. **It does not touch the eight-answer alphabet problem.** The brain still has four beta slots. The
   candidate gets round that by reading `limiting_cell` rather than the label, which is why the label
   is irrelevant here — but that is an argument, and the alphabet mismatch in section 5 stands
   unmeasured against as a separate thing to solve.
4. **It is not a runtime result.** No tensor was produced, no decoder ran, no store was written. What
   runs between the label and HELM's runtime is appendix B's rule, unchanged.

"""


def _real_digest() -> "str | None":
    """Read the digest from the answer files the proof actually wrote.

    The first draft of this section had the ORACLE's hash typed by hand and got it wrong by one
    character (`ae2cab` where the file says `ae2ab`). A wrong hash in a record is worse than no hash,
    because it looks checkable. The section is now written from the file, and the script REFUSES if
    the two files are absent or disagree.
    """
    import hashlib
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    digests = {}
    for name in ("_candidate_answers.txt", "_oracle_answers.txt"):
        path = os.path.join(here, name)
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as fh:
            digests[name] = hashlib.sha256(fh.read()).hexdigest()
    if len(set(digests.values())) != 1:
        raise SystemExit("REFUSED: the two answer files do not have the same digest: %r" % digests)
    return next(iter(digests.values()))


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = Path(sys.argv[1]) / "docs" / "working" / "noetic_council" / FILE
    if not target.is_file():
        print("REFUSED: no appendix F at %s" % target)
        return 1
    text = target.read_text(encoding="utf-8")

    if "--list" in sys.argv:
        print("%-8s %s" % ("PRESENT" if HEADING in text else "ABSENT", HEADING))
        return 0

    if HEADING in text:
        print("section 9 is already present; nothing to do")
        return 0
    if ANCHOR not in text:
        print("REFUSED: anchor not found: %r" % ANCHOR)
        return 1
    if text.count(ANCHOR) != 1:
        print("REFUSED: anchor appears %d times" % text.count(ANCHOR))
        return 1

    digest = _real_digest()
    if digest is None:
        print("REFUSED: the proof's answer files are not beside this script, so the hash cannot be")
        print("         taken from the artefact. Run prove_candidate_vs_oracle.py first, or pass")
        print("         the files' directory. A typed hash is not acceptable.")
        return 1
    print("digest taken from the answer files: %s" % digest)

    target.write_text(text.replace(ANCHOR, SECTION.replace("{DIGEST}", digest) + ANCHOR),
                      encoding="utf-8")
    print("WROTE %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
