"""Add to appendix D: the runtime's own method measured with the case actually arriving.

Idempotent: runs twice, writes once. Refuses if its anchor is missing, rather than appending to
the wrong place.

Usage:
    C:\\Python314\\python.exe -B add_appendix_d_realpath.py <worktree>
"""
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = "## 6. What the patch does not do, and cannot claim"

SECTION = """### The runtime's own method, with the case actually arriving

Everything above measured the patch from outside. This measures it from inside the runtime: one call
to **`runtime._prepare_inference`**, the runtime's own method that contains the brain call at
`runtime.py:1006`. Nothing was set by hand. If the edit were missing, the run would have said so.

Measured, on the patched copy, with the real CASformer:

- `_prepare_inference` **returned** `_PreparedInference`. It cannot return without its own routing
  cross-check passing, so the `torch.equal` guard that refused routes B and C agreed here.
- The operation bank received **exactly one case**, and it was the runtime's own content:
  `case_id='probe-tick'` — the value `make_input_cause` was given, not a copy of it.
- Both holders were **empty after the call**: the node's, sampled after the whole call, and the
  bank's, sampled both inside `bank.forward` and after the call.
- **Negative control.** The same path called through the old three-argument signature gave the bank
  `None` while the bank still ran. Without this, a probe that always sees a case would prove nothing
  about the edit.
- Peak memory **220.5 MiB**, against the project's 300 MiB per-part laptop rule.

#### One measured detail the operation must respect

The case does not arrive as the dictionary it was written as. It arrives as a **`mappingproxy`**
whose sequence values have been converted to **tuples**:

```
case_id=str   edges=tuple   nodes=tuple   route=tuple   task_id=str
```

So it is **read-only**, and `edges` is `((0, 1),)` rather than `[[0, 1]]`. An operation that calls
`.append()` on it, or that mutates it in place, will fail. This was not predicted; it was read off
the value the bank actually received.

#### Three defects in this probe, all three found by running it

Kept because they are the same failure the directive names: a check that looks like a measurement
and is not one.

1. **The unpatched-detector asked the wrong question.** It tested whether `_active_case` was an
   attribute of the bank's class. It is not, for a correctly patched tree: the node sets its own
   holder in `__init__`, but the bank creates `self._active_case` at **call time** inside `forward`.
   The detector therefore **aborted a good run**. It now tests the thing the patch changes — the
   bank's `forward` signature, which reads `self, operation_id, value, case`.
2. **The node's "was it cleared" read sampled too early.** It read the holder inside a wrapper
   around `node.forward`, which runs *before* `network.forward_node`'s `finally` clears it, so it
   always saw the live case and reported **"the node was not cleared"** — a false accusation against
   the patch. The holder is now read after the whole call returns.
3. **The negative control asserted a sentinel that cannot occur.** It expected a missing argument to
   show up as a sentinel. The patched node always passes its holder down, so an uncased call arrives
   as an explicit `None`. The control now asserts `None`, which is the difference the probe can
   actually make.

A fourth defect, in the first version, is recorded in the probe's own docstring: it held the
operation bank as an attribute of an `nn.Module`, so `state_dict()` walked bank to watcher to bank
and raised `RecursionError` — the same trap recorded in section 5 above.

"""


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = (Path(sys.argv[1]) / "docs" / "working" / "noetic_council"
              / "R1_RT_DESIGN_APPENDIX_D_ROUTE_D_PATCH_2026_10_16.md")
    if not target.is_file():
        print("REFUSED: no appendix D at %s" % target)
        return 1
    text = target.read_text(encoding="utf-8")
    if "with the case actually arriving" in text:
        print("the real-path section is already present; nothing to do")
        return 0
    if ANCHOR not in text:
        print("REFUSED: anchor not found: %r" % ANCHOR)
        return 1
    if text.count(ANCHOR) != 1:
        print("REFUSED: anchor appears %d times" % text.count(ANCHOR))
        return 1
    target.write_text(text.replace(ANCHOR, SECTION + ANCHOR), encoding="utf-8")
    print("WROTE %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
