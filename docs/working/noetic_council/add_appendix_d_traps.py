"""Add the extension-operation traps to R1-RT appendix D, idempotently.

WHY A SCRIPT: appendix D is tracked, and a hand edit between worktree syncs is destroyed by the next
`git reset --hard`. Applied by script so it can be re-run safely.

Usage:
    C:\\Python314\\python.exe -B add_appendix_d_traps.py <worktree-root>
"""
from __future__ import annotations

import os
import sys

REL = ("docs/working/noetic_council/"
       "R1_RT_DESIGN_APPENDIX_D_ROUTE_D_PATCH_2026_10_16.md")
MARK = "### Three traps for anyone who writes an extension operation"

SECTION = """### Three traps for anyone who writes an extension operation

Found while testing the patch, kept because the next person to write a shim will meet them.

**1. An extension operation that holds a reference to its own bank makes the module graph cyclic.**
The first version of the test's recorder stored the `RegisteredOperationBank` on itself to read the
held case. Both are `nn.Module`s, so `state_dict()` walked bank → recorder → bank → … until Python
raised **`RecursionError`**. The recorder now reads through a **plain callable**, and the probe has a
sixth check — `state_dict()` has 10 entries and does not recurse — so the cycle cannot come back
unnoticed. *Module bookkeeping must stay out of the module tree.*

**2. The built-in operations occupy relation indices 0 to 3.** `^6` decompose, `^2` attract, `^3`
avert and `^8` trigger take them in `OPERATION_REGISTRATIONS`, and `register_operation` refuses a
duplicate and refuses any index at or above `num_relations`. A new identity therefore needs index 4
**and** a config with `num_relations` of at least 5. Two attempts died on this before it was measured
from the source rather than assumed.

**3. An extension operation cannot execute until its contract is bound**, and the contract's own
validator refuses invented values: `legal_bias_paths` must start with `/memory`, `/rpm`, `/operating`
or `/theta`, and `memory_interface`, `legal_actions`, `legal_bias_paths`, `plasticity_groups` and
`governance_requirements` must all be non-empty. The probe copies the real values from
`cas_cjt/state.py:154-200` rather than guessing; two earlier attempts that guessed were refused, which
is the schema discipline working as intended rather than an obstacle.

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
        print("the traps section is already present; nothing to do")
        return 0

    anchor = "## 6. What the patch does not do, and cannot claim"
    assert anchor in text, "the section 6 anchor is missing"
    text = text.replace(anchor, SECTION + anchor, 1)
    open(path, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
