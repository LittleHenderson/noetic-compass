"""Append to appendix K: the alternative route is closed.

Idempotent: guarded by the new subsection's own heading.

Usage:
    C:\\Python314\\python.exe -B add_appendix_k_route.py <worktree> [--list]
"""
from __future__ import annotations

import sys
from pathlib import Path

FILE = "R1_RT_DESIGN_APPENDIX_K_VERIFIER_ABSTAINS_2026_10_16.md"
ANCHOR = "## 7. Defects found while measuring"
HEADING = "## 7. The alternative route is closed, so the choice is now a real one"

SECTION = """## 7. The alternative route is closed, so the choice is now a real one

Section 4 named two ways to reach the repair machinery and left the second one — "find another route
into the repair machinery" — as something to investigate. **It has been investigated. It is closed,
and the reason is one line.**

Every route into a repair frame passes through `repair.open_repair`, and its first statement is:

```python
if receipt.disposition is not VerifierDisposition.REPAIR or not receipt.repair_required:
    raise RepairError("only an independent REPAIR receipt can open a repair frame")
```

So opening a repair frame **requires** a REPAIR receipt. A REPAIR receipt is produced only by the
verifier's semantic comparison, which section 2 showed is unreachable for a non-canonical operation.
The other thirteen call sites of `repair_frame_from_dict` across `runtime.py`,
`network_coordinator.py` and `persistence.py` either *read back* a frame that was already opened or
sit inside the same `open_repair` path; none of them opens a frame by another means.

**Therefore there is exactly one door, and it needs a REPAIR receipt.** The two ways named in section
4 were never two: the second one leads back through the first.

That collapses the decision to two real options, and it is worth being exact about what they are:

- **Accept the weaker claim.** R1-RT reports what it honestly earned: the answers computed inside
  HELM's runtime, decoded by its own decoder, and withheld by its own verifier. Wave 1 remains the
  project's licensed result. Nothing further is spent, and no new claim is made.
- **Make the operation authority-admitted.** This declares that the brain's output carries canonical
  authority. It would let a REPAIR appear and a nested repair be driven. It is a claim about authority
  rather than a configuration change, it needs its own seal, and it changes what the project asserts.

There is no third option, and the council recommends the first. The authority change purchases a
nested repair by asserting something about the brain that this work has not shown — the brain's
answers were correct on the cases tried, and correctness on cases tried is not authority.

"""


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = Path(sys.argv[1]) / "docs" / "working" / "noetic_council" / FILE
    if not target.is_file():
        print("REFUSED: no appendix K at %s" % target)
        return 1
    text = target.read_text(encoding="utf-8")
    if "--list" in sys.argv:
        print("%-8s %s" % ("PRESENT" if HEADING in text else "ABSENT", HEADING))
        return 0
    if HEADING in text:
        print("the new section is already present; nothing to do")
        return 0
    if ANCHOR not in text:
        print("REFUSED: anchor not found: %r" % ANCHOR)
        return 1
    if text.count(ANCHOR) != 1:
        print("REFUSED: anchor appears %d times" % text.count(ANCHOR))
        return 1
    # The old section 7 becomes 8, since the new one takes its number.
    text = text.replace("## 7. Defects found while measuring",
                        "## 8. Defects found while measuring", 1)
    target.write_text(text.replace("## 8. Defects found while measuring",
                                   SECTION + "## 8. Defects found while measuring", 1),
                      encoding="utf-8")
    print("WROTE %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
