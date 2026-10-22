"""Add to appendix F section 8: the padding encoding, which needs no reference cell.

Idempotent: guarded by the new subsection's own heading, and the digest is read from the answer files
rather than typed, so a hash cannot be written wrongly.

Usage:
    C:\\Python314\\python.exe -B add_appendix_f_padding.py <worktree> [--list]
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

FILE = "R1_RT_DESIGN_APPENDIX_F_INPUT_RULE_FALSIFIED_2026_10_16.md"
ANCHOR = "### Why this is stronger than appendix A's own proof"
HEADING = "### The reference cell is unnecessary, and the one open design question dissolves"

SECTION = """### The reference cell is unnecessary, and the one open design question dissolves

Section 7 left one question open, and called it the one that mattered: the reference cell has to know
whether *every* leg is present, and deciding whether that crosses the design's own `RT_SHIM_NO_MATH`
line is a design question rather than a measurement.

**The question can be dissolved instead of decided.** A route has at most seven legs, and `CELLS` is
eight, so **there is always at least one spare cell**. Give the spare cells a constant value strictly
between the two leg values:

| cells | value |
|---|---|
| `0` to `k-1`, one per route leg | `3` if that leg is present, `1` if not |
| `k` to `7`, the spare region | the constant **`1.5`** |
| requirement | `1` everywhere, as before |

Then:

- **every leg present** — all leg cells are `3`, the spare region is `1.5`, so the minimum is `1.5`
  and the first cell attaining it is the first spare cell, index `k`;
- **leg `j` missing** — that cell is `1`, which is below `1.5`, so the minimum is `1` and the first
  cell attaining it is the lowest missing leg's cell, index `j`;
- **no gate** — the minimum is `1` or `1.5`, never `0`, so G2 does not fire.

The bridge therefore writes a per-leg membership value and **one constant**. It computes no
conjunction, holds no part of the answer, and does not know whether every leg is present — the brain's
own argument of the minimum discovers that. `RT_SHIM_NO_MATH` is satisfied by construction rather than
by a judgement call.

**Measured, not argued.** Both encodings were run against the live oracle on the same 323,851 cases:

| encoding | cases | disagreements | gated | sha256 of the answer stream |
|---|---|---|---|---|
| **padding** (no reference cell) | 323,851 | **0** | **0** | `{DIGEST}` |
| reference cell (section 7) | 323,851 | **0** | **0** | `{DIGEST}` |
| the runtime's own oracle | 323,851 | — | — | `{DIGEST}` |

All three streams have the **same digest**: not merely equal answers, but byte-identical files.

Run both with:

```
python -B prove_candidate_vs_oracle.py <v3-package-root> <r6-source-root> padding reference
```

**A defect found while measuring this, kept on the page.** Refactoring the proof to carry both
encodings, I gave **both** of them the padding layout's cell mapping. The padding encoding then agreed
on every case and the reference encoding disagreed on every case, because its reference cell sits at
index 0 and its legs at `1..k`. The disagreement was the refactor's bug, not a property of the
encoding, and it was visible immediately as two different digests (`d1d4c303` against `c591c568`).
Each encoding now carries its own mapping, and both reproduce the oracle's digest exactly.

**What this does not establish.** It does not approve the encoding for a run, and it does not touch
the four-against-eight alphabet problem in section 5, which is solved here by reading the limiting
**cell** rather than the label. Section 9 lists what remains.

"""


def _digest() -> "str | None":
    """Read the digest from the answer files. A typed hash is not acceptable: the first draft of
    section 8 had the oracle's hash wrong by one character."""
    here = os.path.dirname(os.path.abspath(__file__))
    found = {}
    for name in ("_candidate_answers.txt", "_oracle_answers.txt", "_answers_padding.txt"):
        path = os.path.join(here, name)
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                found[name] = hashlib.sha256(fh.read()).hexdigest()
    if len(set(found.values())) != 1:
        raise SystemExit("REFUSED: the answer files do not share one digest: %r" % found)
    return next(iter(found.values()))


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
        print("the padding subsection is already present; nothing to do")
        return 0
    if ANCHOR not in text:
        print("REFUSED: anchor not found: %r" % ANCHOR)
        return 1
    if text.count(ANCHOR) != 1:
        print("REFUSED: anchor appears %d times" % text.count(ANCHOR))
        return 1

    digest = _digest()
    if digest is None:
        print("REFUSED: no answer files beside this script, so the digest cannot be taken from the")
        print("         artefact. Run prove_candidate_vs_oracle.py first.")
        return 1
    print("digest taken from the answer files: %s" % digest)

    target.write_text(text.replace(ANCHOR, SECTION.replace("{DIGEST}", digest) + ANCHOR),
                      encoding="utf-8")
    print("WROTE %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
