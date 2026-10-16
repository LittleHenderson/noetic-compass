"""Add a portability section to the council directive, and record what is verified.

WHY THIS EXISTS
---------------
Every edit to a tracked file between worktree syncs is lost, because `git reset --hard` reverts it.
One such edit has already been destroyed once. So every change to the directive is applied by a
script that asserts its anchors and can be re-run safely.

Idempotent: if the section is already present it says so and changes nothing.

Usage:
    C:\\Python314\\python.exe -B add_directive_portability.py <worktree-root>
"""
from __future__ import annotations

import os
import sys

REL = "docs/working/helm_tks_noetic_council_directive_2026_10_16.md"
MARK = "## 13. Portability: what runs where, and what it reads"

NEW_SECTION = """## 13. Portability: what runs where, and what it reads

The council was built on this machine, so its paths are this machine's paths. That is worth stating
plainly rather than discovering later.

### The machinery is portable

Measured by copying eight files into an empty folder — no journal, no seats directory, no
environment — and running the loop there: **it runs, writes its own journal, and reaches the same
diagnosis.** The eight files are `council_loop.py`, the three `run_loop_*.py` runners, the three
`target_*.py` modules, and `verify_r1_rt_rules.py`.

**A reading that names a path on this machine is not portable; a reading that names a record is.**

### The rule this produced, now enforced in the code

`RT_SPECIFIED` originally listed a **hard-coded worktree directory** to find the R1-RT design. The
design is **committed** to `origin/claude/project-thread-pmbzd6`; the worktree was only where it was
written. Had that worktree been removed, the reading would have reported **"no design" while the
design sat on the branch** — wrong about the one thing it names, which is exactly what section 12
forbids.

It now reads the live branch through `git show <branch>:<dir>` and falls back to disk only when git
cannot be reached, and its detail says **which source was used**. The rule generalises: **prefer
the record to the path.**

### What each target reads, and where it breaks elsewhere

| target | what it reads | portable? |
|---|---|---|
| `ENGINE_CANON_FAITHFUL` | the engine candidates under `Documents\\Codex\\2026-10-16\\rpm_council_work\\` | **no** — it is a repository of the engine's own repair history, and it is this machine's |
| `HELM_R1_WAVE1_DONE` | the frozen reader's verdict, the run receipts, the AWS ledger, and the live record through `git show` | **partly** — the record half is portable; the verdict and receipts are files this machine holds |
| `HELM_R1_RT_HOSTED` | the runtime source, the recipe brain package, `WAVES.md`, and the design on the live branch | **partly** — the design and the plan are portable; the runtime and package are disk copies |
| any Run reading | the run's own receipts by path | **no** — a receipt lives where it was written |

**None of this is a defect to fix now.** It is a limit to state, because a future agent on another
machine will otherwise read a green reading and believe it.

### What lives only on this machine, and matters

- the engine of record and the candidates it was selected from,
- the wave-1 verdict, its receipts, the supervisor receipt, and the AWS ledger,
- the runtime source and the recipe brain packages,
- the seat reports under `noetic_loop\\seats\\`,
- the loop journal.

The wave-1 **run** is backed up at `D:\\tksCAS-archive\\helm_r1_w1_c34g_20261016\\` with three
confirmations, and that backup is the durable copy of the result. The rest has no backup, and that
is recorded here rather than assumed away.

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
        print("the portability section is already present; nothing to do")
        return 0

    assert "## 13. Reporting to the owner" in text, "the section 13 anchor is missing"
    assert "## 14. What is verified, and what is not" in text, "the old 14 heading is missing"
    assert "## 15. Amendment log" in text, "the old 15 heading is missing"

    # Renumber the tail first, so the new section's own 13 cannot collide with the old one.
    text = text.replace("## 14. What is verified, and what is not",
                        "## 15. What is verified, and what is not", 1)
    text = text.replace("## 15. Amendment log", "## 16. Amendment log", 1)

    # The VERIFIED table gains the new rows measured in this session. Every row must be something
    # this session actually ran and read; a row that merely sounds true is the failure section 12
    # forbids, and the first draft of this script contained one, which was removed before it was
    # ever written to disk.
    text = text.replace(
        "| The council corrected its orchestrator | five corrections by five seats in one turn, "
        "each verified against the bytes |",
        "| The council corrected its orchestrator | five corrections by five seats in one turn, "
        "each verified against the bytes |\n"
        "| The council runs from a fresh checkout | eight files copied into an empty folder: the "
        "loop ran, wrote its own journal, and reached the same diagnosis |\n"
        "| The R1-RT input rule matches the runtime's own oracle | 20,000 random and 98,304 "
        "exhaustive cases, 0 disagreements |\n"
        "| The R1-RT output rule survives the decoder's arithmetic | 4 constants x 8 labels, 32 of "
        "32 correct, and the all-zero trap demonstrated |\n"
        "| The two halves of R1-RT refuse each other | `runtime.py:9` is an unguarded `import torch` "
        "and 17 of 34 runtime files import it; `rb/no_torch.py` refuses a process already holding "
        "torch and raises on install. Both import orders fail |\n"
        "| The runtime cross-checks the brain's routing | `runtime.py:1011-1025` compares three "
        "telemetry fields with `torch.equal` against the materialized route and raises on mismatch |",
        1)

    text = text.replace("## 13. Reporting to the owner",
                        NEW_SECTION + "## 14. Reporting to the owner", 1)
    text = text.replace(
        "| 2026-10-16 | **Third target added:",
        "| 2026-10-16 | **Section 13 added: portability.** The council runs from a fresh checkout "
        "(measured), but several readings name paths on this machine. The rule that follows is "
        "enforced in the code: `RT_SPECIFIED` now reads the design from the live branch through "
        "`git show` rather than from a hard-coded worktree path, because the design is committed and "
        "the worktree was only where it was written. Prefer the record to the path. |\n"
        "| 2026-10-16 | **Third target added:",
        1)

    open(path, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
