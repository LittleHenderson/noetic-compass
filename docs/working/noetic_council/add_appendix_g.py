"""Write appendix G: the client operation, measured.

Idempotent: creates the file, or refuses if it already exists with different content.

Usage:
    C:\\Python314\\python.exe -B add_appendix_g.py <worktree>
"""
from __future__ import annotations

import sys
from pathlib import Path

NAME = "R1_RT_DESIGN_APPENDIX_G_CLIENT_OPERATION_2026_10_16.md"

BODY = """# R1-RT design, appendix G: the client operation, measured

**Date:** 2026-10-16
**Status:** the architecture appendix E said was needed is now **built and measured**. The recipe brain
can be hosted as an operation the runtime itself calls, on the runtime's own path, holding the task's
own content. It costs **three edits**, not the one route D assumed.

## 1. What was built

A copy of the frozen runtime carrying **eleven edits** across four files: route D's nine (appendix D),
plus two more. Prepared by `prepare_client_patch.py`, which refuses to target the frozen source. All
**34 of 34** modules compile after the patch.

| # | file | what it does |
|---|---|---|
| 1-8 | `neural.py`, `network.py`, `runtime.py` | route D: the task's content reaches the operation |
| 9 | `state.py` | **one entry in the frozen operation table** |
| 10 | `runtime.py` | `create()` gains a way to be handed an extension operation |
| 11 | `runtime.py` | `create()` registers it before the state envelope is sealed |

## 2. Why two more edits, and not one

Both reasons were **measured, not read**:

1. **The runtime refuses an operation identity it does not already know.**
   `make_operation_contract` raises `StateContractError("unknown operation identity: ...")` for
   anything outside a four-entry table (`state.py:110-151`). Measured directly:
   `CJTNodeSpec('C', 'experimental_r1_rt_client')` then `create()` fails with exactly that error.
2. **Nothing in the frozen runtime can replace a built-in.** `register_operation` refuses
   (`neural.py:217-218`: "frozen built-in operation identities cannot be replaced"). So a client can
   only ever be an **added** identity, never the `^6` the task's decoder names.

There is a third thing that had to be discovered by running: the extension module must exist **before**
the state envelope is built. `parameter_names_for_node` refuses a node whose operation slot is empty —
"node plasticity allowlist selected no parameters" — and `operation_initializers` cannot serve as the
way in, because it looks the module up **by operation id** and so requires the module to be there
already. That error is what forced edit 10 and 11.

## 3. What the measurement says

Run against the patched copy, on the runtime's own path, with the real CASformer:

| reading | result |
|---|---|
| the runtime accepted a CLIENT node spec | **YES** |
| the runtime accepted the client registration (relation index 4) | **YES** |
| `runtime._prepare_inference` returned | **YES** (`_PreparedInference`) |
| the client RAN on the runtime's own path | **YES**, one call, node `C` |
| it received the task's own content | **YES**, `case_id='client-probe'` |
| the bank was left empty afterwards | **YES** |
| peak memory | **220.1 MiB** of the 300 MiB laptop rule |

Reproduce with `probe_client_operation.py <patched-parent> <base-tree> <gb-root>`.

## 4. What this answers, and what it does not

Appendix E section 7 listed four unknown things. **Three are now answered:**

1. ~~Whether the runtime accepts an experimental operation as a node's registered operation.~~
   **Answered: yes.**
2. ~~Whether the runtime's verifier accepts a proposal whose candidate effect came from outside the
   process.~~ **Partly answered:** `_prepare_inference` returns, which means the routing cross-check
   and the ancestry checks it performs all passed. The full verifier is not exercised by this probe.
3. The per-tick cost of a process boundary. **Still unknown.**
4. ~~Whether the client must be an `nn.Module`.~~ **Answered: yes, and a recorder with parameters is
   accepted.** Note the trap: the recorder must not hold the operation bank, or `state_dict()` walks
   bank to recorder to bank and recurses.

The client in this probe is a **recorder**, not the recipe brain and not a boundary. What is proved is
that the slot exists and is called with the content.

## 5. The consequences the design must state

These are not footnotes. Each changes what R1-RT can claim.

**Three edits, not one.** Route D's patch is necessary but not sufficient. Two more edits are needed,
and both are small: one data-table entry, and one block in `create()`.

**The data-table entry changes no logic.** It adds the client's identity to a table; no control flow in
the runtime changes. It is still an edit to a frozen package, so it needs its own seal and the owner's
line.

**A client run BYPASSES the task's own decoder contract.** `native_task.task_decoder_contracts`
requires `operation_id == "^6"` and refuses anything else. So a run with the client cannot use the
task's own decoder contract and must supply its own. That is a real change to what "the same task"
means, and the reading must say so rather than implying the task ran unaltered. The client's decoder
must also be **version 2** to match the frozen output rule (appendix B), and a version-2 root requires
an exact explicit semantic lineage, which `_semantic_lineage` validates field by field.

**A client can never be the `^6` the task names.** It is an added identity. So the honest description of
a client run is: *HELM's runtime, its store, its verifier and its repair machinery, answering the
route-dependency task with the recipe brain in place of `^6` for the node that was asked* — not *the
task ran exactly as its contract defines it*.

## 6. Defects found while building, kept on the page

1. **A cleanup error masked a whole run.** On Windows the SQLite handle can outlive `runtime.close()`
   by a moment, and the resulting `WinError 32` replaced the probe's entire output. The temporary
   directory is now created with `ignore_cleanup_errors=True`. A tidy-up failure must never hide a
   measurement.
2. **A version-1 decoder refuses the version-2 algorithm.** `SemanticDecodeError: v1 decoder requires
   the unchanged full-width algorithm`. The probe now uses version 1 and says why: it asks whether the
   client is called, not which decoder algorithm runs.
3. **The runtime refuses a network with fewer than three nodes** — "a network state requires at least
   three typed BiasState records". A three-node network costs nothing and was not guessed.
4. **`operation_initializers` looked like the injection point and is not**, for the reason in section 2.

## 7. What remains before a run

1. **The process boundary.** A long-lived brain process, no torch, one JSON line per tick. Its per-tick
   cost is the one unknown left from appendix E.
2. **The brain inside the client**, replacing the recorder, with the **padding encoding** from appendix
   F section 8 as the input rule.
3. **A version-2 decoder contract plus its exact semantic lineage**, since the task's own contract pins
   `^6`.
4. **The output tensor**, written by appendix B's frozen rule from the leg answer.
5. **A re-costed envelope.** The existing one was priced for a shape the design no longer has.
6. **The owner's line.** Nothing here was applied to a frozen tree; everything ran on a copy.
"""


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = Path(sys.argv[1]) / "docs" / "working" / "noetic_council" / NAME
    if target.exists():
        if target.read_text(encoding="utf-8") == BODY:
            print("appendix G is already present and identical; nothing to do")
            return 0
        print("REFUSED: %s exists with different content" % target)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(BODY, encoding="utf-8")
    print("WROTE %s (%d bytes)" % (target, len(BODY)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
