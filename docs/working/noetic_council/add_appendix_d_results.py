"""Add the "tested, not just compiled" section to R1-RT appendix D, and correct its edit count.

WHY A SCRIPT. Appendix D is a tracked file. An edit made by hand in the worktree is destroyed by the
next `git reset --hard` — which happened once already, to the directive, and again to this file. So
every change to a tracked design document is applied by a script that asserts its anchors and can be
re-run safely.

Idempotent: if the section is present it says so and changes nothing.

Usage:
    C:\\Python314\\python.exe -B add_appendix_d_results.py <worktree-root>
"""
from __future__ import annotations

import os
import sys

REL = ("docs/working/noetic_council/"
       "R1_RT_DESIGN_APPENDIX_D_ROUTE_D_PATCH_2026_10_16.md")
MARK = "## 5. It was tested by running it, not by reading it"

NEW_SECTION = """## 5. It was tested by running it, not by reading it

A patch that compiles is not a patch that works. So the patched copy was **imported and exercised**,
in this machine's own environment (Python 3.14.0, torch **2.11.0+cpu**), and the one behaviour that
matters was checked directly: *does an operation actually read the case?*

`verify_route_d_case_passing.py` registers one extension operation whose `forward` records what the
bank was holding when it ran, then calls the bank three times and checks the guard:

| check | result |
|---|---|
| the operation reads the case when given one | **PASS** — it saw the probe's own case |
| the attribute is cleared after the call | **PASS** — `None`, so a case cannot leak |
| the operation sees `None` when given none | **PASS** |
| a later, different case is delivered, not sticky | **PASS** |
| an unknown operation id is still refused | **PASS** — the patch weakened no guard |

**Five of five. Route D works.**

### The defect that running it found, which reading it had missed

**The first version of the patch passed the case into the operation bank and then dropped it on the
floor.** The call site at `neural.py:375` looked correct, every anchor matched, all 34 modules
compiled — and the operation still could not read anything, because an operation's `forward` takes
only `value`, so the case arrived as an unused parameter.

The fix is one more edit: the bank now **holds** the case in `self._active_case` for the duration of
the call and clears it in a `finally`. **Compile-level verification would never have caught this.**
It was caught by reading what the bank did with `case`, and then by a probe that asserts it.

### Three environment facts the run produced

1. **`cas_cjt` is ALSO installed in site-packages**, as an older, unpatched copy (24 modules against
   the frozen tree's 34). The first probe run silently tested **that** copy and reported a refusal
   from it while claiming to test the patch. The probe now puts the patched root first and **prints
   which `cas_cjt` it is using**, so this cannot happen unnoticed.
2. **The built-in operations take relation indices 0 to 3** (`^6` decompose, `^2` attract, `^3`
   avert, `^8` trigger), and the bank refuses a duplicate. A new identity needs index 4 and a
   `num_relations` of at least 5. Measured from the source after two refusals taught us.
3. **An extension operation cannot execute until its contract is bound**, and the contract's own
   validator refuses invented values: `legal_bias_paths` must start with `/memory`, `/rpm`,
   `/operating` or `/theta`, and five tuple fields must be non-empty. The probe now **copies the real
   contract values from `state.py:154-200`** rather than inventing a schema, and two earlier attempts
   that guessed were refused. That is the runtime's schema discipline working as intended.

### What this does and does not establish

**Established:** the patched operation bank delivers the case to an extension operation, clears it,
does not leak it, and still refuses unknown operations; and the patched module imports in this
machine's environment.

**Not established:** that a full runtime starts, that a store opens, that CASformer runs, or that a
recipe brain answers correctly. Those need a runtime creation, which needs the GB3 `gb` package and a
store, and this machine had **516 MiB free of 16 GiB** when this was measured — so it was not
attempted here. A bare torch import costs **202.0 MiB peak** against the project's 300 MiB limit,
which is why this is a probe and not a run.

"""


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = os.path.join(sys.argv[1], REL.replace("/", os.sep))
    if not os.path.isfile(path):
        print("NOT FOUND: %s" % path)
        return 1
    text = open(path, encoding="utf-8").read()
    if MARK in text:
        print("the results section is already present; nothing to do")
        return 0

    assert "## 5. What the patch does not do, and cannot claim" in text, "the section 5 anchor is missing"
    assert "## 6. Where the owner's decision now stands" in text, "the section 6 anchor is missing"
    assert "## 2. The patch, in seven edits and 22 lines" in text, "the edit-count heading is missing"
    assert "all seven anchors match exactly once" in text, "the edit-count sentence is missing"
    assert "**Status:** A PATCH, PREPARED. It is applied to" in text, "the status line is missing"

    # Renumber the tail first, so the new section's own 5 cannot collide with the old one.
    text = text.replace("## 6. Where the owner's decision now stands",
                        "## 7. Where the owner's decision now stands", 1)

    # Correct the edit count: eight anchors, nine edits (one is the typing import).
    text = text.replace("## 2. The patch, in seven edits and 22 lines",
                        "## 2. The patch, in nine edits", 1)
    text = text.replace("all seven anchors match exactly once",
                        "all eight anchors match exactly once", 1)

    text = text.replace("## 5. What the patch does not do, and cannot claim",
                        NEW_SECTION + "## 6. What the patch does not do, and cannot claim", 1)

    text = text.replace(
        "**Status:** A PATCH, PREPARED. It is applied to\na copy, never to the frozen source. Nothing "
        "here runs a model, starts a machine, or spends anything.",
        "**Status:** A PATCH, PREPARED AND TESTED, still not applied to the frozen source. Nothing "
        "here starts a machine or spends anything. It does import the patched module and exercise it "
        "in this machine's own environment, and that is reported as what it is.", 1)

    open(path, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
