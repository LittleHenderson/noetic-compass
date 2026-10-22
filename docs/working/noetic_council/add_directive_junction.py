"""Add the junction hazard to the council directive's portability section, idempotently.

WHY A SCRIPT. The directive is tracked, and a hand edit between worktree syncs has been destroyed
twice. Every change to it goes through a script with asserted anchors.

Usage:
    C:\\Python314\\python.exe -B add_directive_junction.py <worktree-root>
"""
from __future__ import annotations

import os
import sys

REL = "docs/working/helm_tks_noetic_council_directive_2026_10_16.md"
MARK = "### A junction that copies into infinity"

SECTION = """### A junction that copies into infinity

Measured while backing up the working record, and recorded because naive tooling walks straight
into it.

**`rpm_council_work\\E_c5\\rpm_council` is a directory junction whose target is `E_c5` — its own
parent.** It was left behind by an earlier session's copy step. Following it nests `rpm_council`
inside itself without end.

What that did: `shutil.copytree` followed it, **left 121 directories in the archive**, and then died
with `WinError 1921` when the path passed the Windows limit. The backup's own tree scan had also
reported a suspiciously long path, which is what pointed at it.

**The rule that follows: prune reparse points, never follow them.** A backup or a tree scan must skip
junctions and symlinks and **say how many it skipped**, because a pruned link means the backup does
not contain that subtree and a reader of the manifest is entitled to know. The three trees now back
up as 56, 148 and 4 files with the junction pruned and counted, and the engine hashes in the manifest
match the loop journal's recorded `engine_sha256` exactly — which is how the backup proves it copied
the right bytes.

**This is also why the council's working record was not already backed up safely.** Wave 1's run was
backed up; the machinery, the seat reports and the journal were not, and a naive copy of them fails.

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
        print("the junction note is already present; nothing to do")
        return 0

    anchor = "### What lives only on this machine, and matters"
    assert anchor in text, "the anchor heading is missing"

    text = text.replace(anchor, SECTION + anchor, 1)

    row = ("| 2026-10-16 | **Junction hazard recorded** in section 13: "
           "`rpm_council_work\\E_c5\\rpm_council` is a junction targeting its own parent, and "
           "following it made `shutil.copytree` leave 121 directories and die on the Windows path "
           "limit. Reparse points are now pruned and counted, never followed. The council's working "
           "record is backed up with three confirmations at "
           "`D:\\tksCAS-archive\\noetic_council_20261016\\`, and the manifest's engine hashes match "
           "the loop journal's recorded `engine_sha256`. |\n")
    text = text.replace(
        "| 2026-10-16 | **Third target added:",
        row + "| 2026-10-16 | **Third target added:", 1)

    open(path, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
