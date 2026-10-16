"""Add the full-runtime-startup results to R1-RT appendix D, idempotently.

WHY A SCRIPT. Appendix D is tracked, and a hand edit between worktree syncs is destroyed by the next
`git reset --hard`. That has happened twice to tracked design documents already.

Usage:
    C:\\Python314\\python.exe -B add_appendix_d_startup.py <worktree-root>
"""
from __future__ import annotations

import os
import sys

REL = ("docs/working/noetic_council/"
       "R1_RT_DESIGN_APPENDIX_D_ROUTE_D_PATCH_2026_10_16.md")
MARK = "### A full runtime starts with the patched module — measured"

SECTION = """### A full runtime starts with the patched module — measured

`probe_runtime_startup.py` goes further than the bank probe: it creates a real `NeuralCJTRuntime`,
on a scratch SQLite store, using **GB3's own** configuration, specs and topology, then re-opens it.

| | result |
|---|---|
| the patched `cas_cjt` is the one loaded | **confirmed** — the probe asserts the patch marker is present and aborts if it is not |
| `NeuralCJTRuntime.create` on a scratch store | **CREATE OK**, store file written |
| the runtime's own state reads back | `model_id cas-cjt-network-model`, `model_digest 1dbbd05fc5da0c8d` |
| `NeuralCJTRuntime.open` on the same store | **OPEN OK** |
| peak memory | **219.3 MiB**, inside the project's 300 MiB per-part laptop rule |

**So the gap between "the patch compiles" and "a runtime runs with it" is now closed.**
`cas_cjt` and `casformer` are not import-time barriers on a full start-up.

### Three more things this probe found, each of which changed what is known

1. **GB3's carrier ships its OWN `cas_cjt` and its OWN `casformer`.** They are 29 and 8 modules,
   against the R6 source's 34. The `gb` scaffold uses **the carrier's** copies, and the anchors the
   patch needs exist in **both** trees — so the patch is not R6-specific.
   `prepare_route_d_patch.py` now takes `--source` instead of assuming one tree.
2. **The installed `casformer` (0.1.0, in the Python 3.14 site-packages) is a DIFFERENT version**
   from the carrier's. It lacks `bias_read_enabled` and `bias_write_mode`, which GB3's own `config()`
   passes, so the scaffold cannot even build its configuration against it. **The vendored copy must
   be used**, which is what the carrier exists for.
3. **`gb/continuity.py:52` imports `resource`, a UNIX-ONLY module.** GB3's scaffold therefore cannot
   import on Windows at all. The probe installs a **named, minimal shim** for it and says so; the
   real resource-limit behaviour belongs on the Linux host where the scaffold was written to live.

### A defect in the probe itself, of exactly the kind the directive warns about

The probe's path setup read:

```python
for p in (patched_parent, base_tree, gb_root):   # WRONG
    sys.path.insert(0, p)
```

**Each insert goes to position 0, so the list ends up in REVERSE priority — the last path wins.** The
probe was loading the **base** tree's unpatched `cas_cjt` while the comment directly above the loop
said the patched tree came first. The first two runs reported a green result from the wrong code, and
the reason they looked consistent is that the unpatched runtime **also** creates and re-opens fine.

It was caught because the probe now **asserts** which copy it loaded instead of trusting the path
arithmetic, and it aborted with `ROUTE D PATCH PRESENT: False` rather than reporting a success that
meant nothing. The loop is fixed, and the assertion stays.

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
        print("the startup section is already present; nothing to do")
        return 0

    anchor = "## 6. What the patch does not do, and cannot claim"
    assert anchor in text, "the section 6 anchor is missing"
    assert "## 7. Where the owner's decision now stands" in text, "the section 7 anchor is missing"

    text = text.replace(anchor, SECTION + anchor, 1)
    open(path, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
