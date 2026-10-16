"""Add the round-21 amendment-log row: the verifier abstains, so the repair cannot be reached.

IDEMPOTENT PER ROW, guard is the ROW ITSELF. Rows go ABOVE the round-13 anchor.

Usage:
    C:\\Python314\\python.exe -B add_directive_round21.py <worktree> [--list]
"""
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = "| 2026-10-16 | **Third target added: `HELM_R1_RT_HOSTED`**"

ROWS = [
    (
        "the verifier abstains, so a nested repair cannot be reached",
        "| 2026-10-16 | **MEASURED: HELM's verifier ABSTAINS on every hosted answer, so R1-RT's third "
        "requirement cannot be met by a client operation.** The brain answered "
        "`FIRST_UNSUPPORTED_LEG_1` and the runtime's own decoder read it back correctly \u2014 and "
        "then the runtime declined to publish it: `disposition ABSTAIN`, `semantic_outcome UNKNOWN`, "
        "`reason_codes ('EXPERIMENTAL_OPERATION_NOT_AUTHORITY_ADMITTED',)`, `repair_required False`, "
        "**no repair frame opened**, and **`audit_only: True`**. The cause is the ORDER of the tests "
        "in `verifier.py:304-340`: the test for a non-canonical operation runs **before** the semantic "
        "comparison, and **both** REPAIR outcomes live below that test. So a client operation can "
        "never reach ACCEPT, can never reach REPAIR, and can never drive a nested repair. **The "
        "runtime is doing the right thing** \u2014 it is refusing to give authority to an operation "
        "that is not authority-admitted, which is the governance design working. The design asked for "
        "something the runtime's own rules forbid. Recorded as appendix K. |",
    ),
    (
        "the claim R1-RT can actually make is weaker",
        "| 2026-10-16 | **The claim R1-RT can actually make, stated so nothing overreaches.** Not "
        "*the same answers inside HELM*, but **the same answers computed inside HELM's runtime, "
        "decoded by its own decoder, and withheld by its own verifier**. Everything already proved "
        "stands unchanged \u2014 the replaced input rule (323,851 cases), the patch, the client "
        "operation, the boundary (0.061 ms per tick, never held torch), the hosted tick (3 of 3) and "
        "restart survival. What is removed is R1-RT's third requirement as the design wrote it, and "
        "the word \\\"answers\\\" as it was meant. Reaching a real repair needs one of two things, "
        "neither of them an engineering choice: declare the client operation **canonical-admitted**, "
        "which is a claim about authority needing its own seal and the owner's line, or find another "
        "route into the repair machinery. The council recommends investigating the alternatives "
        "first, then accepting the weaker claim \u2014 **not** the authority change. |",
    ),
    (
        "the reading defect behind it",
        "| 2026-10-16 | **The reading defect behind it, kept on the page.** Appendix G measured that "
        "the runtime accepts and **CALLS** a client operation. It never asked whether the runtime "
        "would **BELIEVE** it. Those are different questions, and only the first was asked \u2014 for "
        "several rounds, while the design was built on the assumption that the second would follow. "
        "Standing rule added: when a design puts a component into a governed slot, ask what the "
        "governance does with the component's output, and ask it before building on the slot. |",
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
