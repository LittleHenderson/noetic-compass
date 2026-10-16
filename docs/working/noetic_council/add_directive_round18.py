"""Add the round-18 amendment-log rows: the owner's two authorisations.

IDEMPOTENT PER ROW, guard is the ROW ITSELF. Rows go ABOVE the round-13 anchor.

Usage:
    C:\\Python314\\python.exe -B add_directive_round18.py <worktree> [--list]
"""
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = "| 2026-10-16 | **Third target added: `HELM_R1_RT_HOSTED`**"

ROWS = [
    (
        "the owner authorised R1-RT to go ahead",
        "| 2026-10-16 | **OWNER AUTHORISATION: R1-RT GOES AHEAD.** The owner was asked the one "
        "question that was actually open \u2014 whether the work to put the recipe brain inside "
        "HELM's own runtime should proceed \u2014 and selected **\"Yes, go ahead (costs $0 for "
        "now)\"**. Scope of this authorisation, stated so it cannot be read wider than it is: it "
        "authorises work on **copies** on this laptop, which spends nothing. It does **not** "
        "authorise applying anything to a frozen tree, and it does **not** authorise a paid run. A "
        "paid run needs a separate, later yes with its own cost figure. The question channel used "
        "issues no message id, so none is recorded: an invented identifier is worse than an absent "
        "one. |",
    ),
    (
        "the owner cleared the seven wave-1 holds",
        "| 2026-10-16 | **OWNER DISPOSITION: the seven open wave-1 holds are cleared.** The wave-1 "
        "reconciliation record carries its own rule \u2014 *\"holds change only by explicit owner "
        "disposition or accepted billing reconciliation\"* \u2014 and the owner gave that "
        "disposition, selecting **\"Yes, clear them\"**. Recorded executably in the budget addendum "
        "family as `BUDGET_DISPOSITION_W1_C34_HOLDS_20261016T232626Z.json`, digest "
        "`8b70c13b8b2e77980e91c3ae2e6f99740db60183aef26deaf691d64e6a2848d4`. The script reads all "
        "six figures from the reconciliation record and **refuses** if any has moved, because a "
        "disposition written against stale figures is worse than none. **63.75 USD of holds become "
        "unreserved, so the unreserved room goes from 37.55 to 101.30 USD.** The ledger total stays "
        "at 162.45 of 200.00 and no charge is re-priced. |",
    ),
    (
        "the holds were bookkeeping, and AWS was checked",
        "| 2026-10-16 | **The cleared holds were bookkeeping, and AWS was checked rather than "
        "assumed.** Nothing was ever reserved on Amazon's side, so clearing them changes no AWS "
        "resource. `describe_instances` was run in the default region and in us-east-1 and "
        "us-west-2: **no wave-1 machine is present**, so the job's own instances are gone. Three "
        "instances were found that this work did NOT create and did NOT touch, and they are recorded "
        "because two are running and billing: `i-0bd0a082507a51ae3` (`t3.small`, `nc-customer-app`, "
        "running), `i-02137d196e671b5c1` (`t3.small`, `nc-canary-app`, running), and "
        "`i-0c3028734c8885542` (`g6e.xlarge`, `cas-bridge-control-20260822`, stopped). Changing them "
        "is the owner's call and nobody else's. |",
    ),
    (
        "the asks were rewritten after the owner called them ambiguous",
        "| 2026-10-16 | **The council's own reporting fault, recorded because it cost the owner "
        "time.** A status report put three asks to the owner and the owner replied that they were "
        "ambiguous and could not be acted on. Two of the three were **already dead when sent**: the "
        "third asked whether to build the client, which had already been built and measured, and the "
        "first offered a three-way choice that had been superseded twice. The second handed the owner "
        "a bookkeeping chore that was the council's own to verify. The ask was rewritten as **one "
        "yes-or-no question with a plain consequence for each answer**, and every stale or "
        "already-done item was withdrawn out loud. Standing rule added: before putting a question to "
        "the owner, check that each option is still live, that the action is not the council's own, "
        "and that the consequence of each answer is stated in plain words. |",
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
