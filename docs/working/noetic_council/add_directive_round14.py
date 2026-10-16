"""Add the round-14 amendment-log rows to the council directive.

Idempotent: runs twice, writes once. Refuses if its anchor is missing.

Usage:
    C:\\Python314\\python.exe -B add_directive_round14.py <worktree>
"""
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = "| 2026-10-16 | **Third target added: `HELM_R1_RT_HOSTED`**"

ROW = (
    "| 2026-10-16 | **Route D's central assumption falsified by measurement, and recorded as appendix E "
    "rather than quietly dropped.** The design assumed the sealed recipe brain could be hosted in the "
    "runtime's own process. It cannot: `rb/__init__.py` installs a blocker on import whose `install()` "
    "raises if torch is already loaded, and once installed the blocker refuses any later `import torch`. "
    "**All four import orders were refused**, each run in its own subprocess, and `numpy` rides in with "
    "torch so there is no partial order. Route D as designed is not buildable. The refusal is not an "
    "obstacle to route around: it is how the brain's own run is shown to be torch-free, and the package "
    "is frozen. HELM's own `rb3` package resolves the same shape the other way, on purpose, and says so "
    "in its docstring. |\n"
    "| 2026-10-16 | **What the falsification does not cost.** Appendix A, B and C are unchanged. "
    "Appendix D's patch is unchanged, tested and now **necessary rather than convenient**: across a "
    "process boundary the in-runtime operation becomes the brain's client, and a client has to send the "
    "question, so `cause.content` reaching the operation is the only way it can know what to ask. The "
    "corrected shape is **the patch plus a process boundary**. The envelope must be re-costed. Four "
    "things remain unmeasured and are named in appendix E section 7 rather than glossed. |\n"
    "| 2026-10-16 | **Route D measured from inside the runtime, not from outside it.** "
    "One call to the runtime's own `_prepare_inference` \u2014 the method containing the brain call "
    "at `runtime.py:1006` \u2014 returned `_PreparedInference` against the patched copy, with the real "
    "CASformer. The operation bank received exactly one case and it was the runtime's own content, "
    "`case_id='probe-tick'`. Both holders were empty afterwards. The negative control \u2014 the same "
    "path through the old three-argument signature \u2014 gave the bank `None` while the bank still "
    "ran, so the probe can tell delivering from not delivering. Peak 220.5 MiB of the 300 MiB "
    "laptop rule. |\n"
    "| 2026-10-16 | **The case arrives as a `mappingproxy` with tuple values**, measured rather "
    "than assumed: `case_id=str`, `edges=tuple`, `nodes=tuple`, `route=tuple`, `task_id=str`. It is "
    "read-only and `edges` is `((0, 1),)` rather than `[[0, 1]]`. Any operation that mutates it or "
    "calls `.append()` on it will fail. Recorded in appendix D section 5. |\n"
    "| 2026-10-16 | **Six defects in the runtime-path probes, every one found by running it, every "
    "one recorded rather than quietly fixed.** Four in the first version: the operation bank held as an "
    "attribute of an `nn.Module`, so `state_dict()` walked bank to watcher to bank and raised "
    "`RecursionError`; a hand-set active case that set the very value under test and so hid whether the "
    "edit worked; a prose excuse for a watcher the runtime never invoked, in a run that called the point "
    "proved anyway; and a separately-registered extension operation the runtime had no reason to call. "
    "Two more in the second: the unpatched-detector asked whether the bank had `_active_case` as a class "
    "attribute \u2014 it does not, the bank creates it at call time \u2014 and so aborted a good run; "
    "and the node's \"was it cleared\" check sampled the holder before `network.forward_node`'s `finally` "
    "ran, and falsely accused the patch of leaking it. A seventh: the negative control asserted a "
    "sentinel for a missing argument that the patched node can never produce, because it always passes "
    "its holder down as an explicit `None`. |\n"
)


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
    if "Route D measured from inside the runtime" in text:
        print("the round-14 rows are already present; nothing to do")
        return 0
    if ANCHOR not in text:
        print("REFUSED: anchor not found: %r" % ANCHOR)
        return 1
    if text.count(ANCHOR) != 1:
        print("REFUSED: anchor appears %d times" % text.count(ANCHOR))
        return 1
    target.write_text(text.replace(ANCHOR, ROW + ANCHOR), encoding="utf-8")
    print("WROTE %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
