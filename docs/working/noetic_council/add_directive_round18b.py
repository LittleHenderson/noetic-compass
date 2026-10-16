"""Add the round-18 amendment-log row: the process boundary, measured.

IDEMPOTENT PER ROW, guard is the ROW ITSELF. Rows go ABOVE the round-13 anchor.

Usage:
    C:\\Python314\\python.exe -B add_directive_round18b.py <worktree> [--list]
"""
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = "| 2026-10-16 | **Third target added: `HELM_R1_RT_HOSTED`**"

ROWS = [
    (
        "the process boundary works and costs 0.061 ms per tick",
        "| 2026-10-16 | **The process boundary works, and it costs 0.061 ms per tick \u2014 "
        "appendix E's last unknown is closed.** `brain_worker.py` is a separate interpreter that "
        "imports `rb` and nothing that could pull torch in; it is given its package root as an "
        "argument and **`PYTHONPATH` is stripped** from its environment, so a stray path cannot "
        "smuggle a torch import into the one process that must never have one. Its own first line "
        "reports `blocker_installed: true`, `torch_in_sys_modules: false`, `numpy_in_sys_modules: "
        "false`. **7 of 7 answers crossed correctly**, with the answer computed on the probe's side "
        "so the check does not lean on the worker \u2014 including the seven-leg all-present case "
        "that appendix F's spare-constant encoding exists to get right. **Negative control:** a "
        "one-node route has no legs and must be REFUSED, and it was \u2014 with an error rather than "
        "an answer \u2014 and the worker kept working afterwards. Cost over 2000 ticks: min 0.046, "
        "**median 0.061**, mean 0.070, p99 0.172, max 0.273 ms; the same arithmetic in-process has a "
        "median of 0.001 ms, so the boundary itself costs about 0.060 ms. **For scale:** the recipe "
        "side of wave 1 took 445.65 s over 35 units, 12.7 s per unit, so at 0.061 ms per tick the "
        "boundary would need roughly **208,000 ticks to cost one second**. Recorded as appendix H. |",
    ),
    (
        "every unknown from appendix E is now closed",
        "| 2026-10-16 | **Every one of appendix E section 7's four unknowns is now closed.** Item 1, "
        "whether the runtime accepts an experimental operation as a node's registered operation: "
        "**yes** (appendix G). Item 2, whether the verifier accepts a proposal whose effect came from "
        "outside the process: **partly** \u2014 `_prepare_inference` returns, so the routing "
        "cross-check and its ancestry checks passed, though the full verifier is not yet exercised. "
        "Item 3, the per-tick cost of a boundary: **0.061 ms median** (appendix H). Item 4, whether "
        "the client must be an `nn.Module`: **yes, and one with parameters is accepted** (appendix "
        "G). What remains is engineering, not discovery. |",
    ),
    (
        "the boundary is not yet driven by the runtime",
        "| 2026-10-16 | **What the boundary measurement does NOT cover, stated so it is not "
        "over-read.** The worker answers over a boundary, but the client inside the runtime is still "
        "the **recorder** from appendix G \u2014 the two are not yet joined. And the cost above is "
        "for a request **the probe made**; a tick driven by `_prepare_inference` would also pay the "
        "runtime's own overhead, which dwarfs 0.061 ms. So this closes the *cost of the boundary*, "
        "not the *cost of a hosted tick*. The latter needs the two joined. |",
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
