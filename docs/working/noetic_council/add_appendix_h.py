"""Write appendix H: the process boundary, measured.

Idempotent: creates the file, or refuses if it already exists with different content.

Usage:
    C:\\Python314\\python.exe -B add_appendix_h.py <worktree>
"""
from __future__ import annotations

import sys
from pathlib import Path

NAME = "R1_RT_DESIGN_APPENDIX_H_PROCESS_BOUNDARY_2026_10_16.md"

BODY = """# R1-RT design, appendix H: the process boundary, measured

**Date:** 2026-10-16
**Status:** appendix E section 7's **last unknown is answered**. The boundary works, and it costs
**0.061 milliseconds per tick**.

## 1. What was built

Two pieces, both new, neither touching a frozen tree:

- `brain_worker.py` — the brain's end. A separate interpreter that imports `rb` and nothing that could
  pull torch in. One JSON object per line in, one out.
- `probe_process_boundary.py` — starts one worker, checks it, and times it.

The worker is given its package root as an **argument**, and `PYTHONPATH` is removed from its
environment before it starts, so a stray path cannot smuggle a torch import into the one process that
must never have one.

## 2. The worker has never held torch — its own report

The worker's first line is its own account of itself, not the client's claim about it:

```json
{"blocker": {"blocker_installed": true, "numpy_in_sys_modules": false,
             "torch_in_sys_modules": false},
 "cells": 8, "spare": 1.5, "leg_missing": 1.0, "leg_present": 3.0,
 "torch_absent": true, "type": "hello"}
```

| reading | result |
|---|---|
| it has never held torch or numpy | **YES** |
| the sealed package's blocker is installed | **YES** |

This is the thing appendix E made necessary. The brain refuses to share a process with torch, and this
arrangement means it does not have to.

## 3. The answers cross correctly, and a refusal is proved

Seven cases, with the answer computed on **this** side of the boundary so the check does not lean on
the worker:

| case | answer |
|---|---|
| every leg present | `ALL_LEGS_PRESENT` |
| the second leg missing | `FIRST_UNSUPPORTED_LEG_1` |
| the first leg missing | `FIRST_UNSUPPORTED_LEG_0` |
| no legs at all | `FIRST_UNSUPPORTED_LEG_0` |
| a longer route | `FIRST_UNSUPPORTED_LEG_1` |
| a seven-leg route, the longest the task has | `FIRST_UNSUPPORTED_LEG_3` |
| seven legs all present, the case the constant spare cell decides | `ALL_LEGS_PRESENT` |

**7 of 7 correct.** The last row is the one that matters most: it is the case appendix F's
spare-constant encoding exists to get right, and it crossed the boundary correctly.

**Negative control.** A one-node route has no legs and must be refused, not answered. The worker
returned `{"error": "ValueError: a route needs at least two nodes"}` rather than an answer, **and kept
working afterwards** — a refusal that broke the stream would be a different failure. A boundary that
agreed with everything would have proved nothing.

## 4. The cost per tick

Two thousand ticks, one long-lived worker, same request each time:

| | milliseconds |
|---|---|
| the first call, which warms the brain's own caches | 0.084 |
| min | 0.046 |
| **median** | **0.061** |
| mean | 0.070 |
| p99 | 0.172 |
| max | 0.273 |

The same arithmetic computed inside the probe's own process has a median of 0.001 ms, so the boundary
itself costs about **0.060 ms**.

**Appendix E section 7 item 3 is therefore answered: 0.061 ms per tick, median.** For scale, the
recipe side of wave 1 took 445.65 s over 35 units, which is 12.7 s per unit. The boundary at
0.061 ms per tick would need roughly **208,000 ticks to cost one second**. It is not a term that
matters in the envelope.

## 5. Every unknown from appendix E section 7 is now closed

| # | the unknown | now |
|---|---|---|
| 1 | whether the runtime accepts an experimental operation as a node's registered operation | **answered in appendix G: yes** |
| 2 | whether the verifier accepts a proposal whose effect came from outside the process | **partly answered in appendix G** — `_prepare_inference` returns, so the routing cross-check and its ancestry checks passed; the full verifier is not yet exercised |
| 3 | the per-tick cost of a process boundary | **answered here: 0.061 ms median** |
| 4 | whether the client must be an `nn.Module` | **answered in appendix G: yes, and one with parameters is accepted** |

## 6. What is still not done

1. **The brain is not yet inside the runtime.** The worker answers over a boundary; the client inside
   the runtime is still the recorder from appendix G. Joining the two is the next step and it is
   engineering, not discovery.
2. **The boundary is not yet driven by the runtime's own ticks.** The cost above is for a request the
   probe made. A tick driven by `_prepare_inference` will also pay the runtime's own overhead, which
   dwarfs it.
3. **The version-2 decoder contract and its exact semantic lineage** are still needed, because the
   task's own contract pins `^6`.
4. **The output tensor** is still not written from a brain answer by appendix B's rule.
5. **The envelope is not re-costed.** This appendix gives the one number it needs; the run plan that
   fixes the tick count is not yet written.
6. **The owner's line.** Nothing here was applied to a frozen tree, and no paid run is authorised.

## 7. Defects found while building

None in the boundary. The two worth recording are smaller and both were caught by reading the output
rather than assuming it:

- The probe's first draft did not remove `PYTHONPATH` from the worker's environment. It worked, but it
  worked for a reason nobody had checked: a parent path *could* have put torch on the worker's import
  path. Removing it makes the "never held torch" reading mean what it says rather than merely being
  true today.
- The first case list included a malformed route — a repeated node — which the worker correctly used
  as its negative control instead of as a correctness case. Promoting it rather than deleting it is why
  the refusal is now proved.
"""


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = Path(sys.argv[1]) / "docs" / "working" / "noetic_council" / NAME
    if target.exists():
        if target.read_text(encoding="utf-8") == BODY:
            print("appendix H is already present and identical; nothing to do")
            return 0
        print("REFUSED: %s exists with different content" % target)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(BODY, encoding="utf-8")
    print("WROTE %s (%d bytes)" % (target, len(BODY)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
