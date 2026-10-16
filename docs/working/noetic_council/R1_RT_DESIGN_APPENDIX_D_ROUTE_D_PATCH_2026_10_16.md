# R1-RT — design, appendix D: route D's patch, prepared and checked but not applied

**Added:** 2026-10-16 PDT by the council's R1-RT turn. **Status:** A PATCH, PREPARED. It is applied to
a copy, never to the frozen source. Nothing here runs a model, starts a machine, or spends anything.

---

## 1. What this is

Appendix C measured that the recipe brain cannot be put where the runtime's *brain call* is, because
`runtime.py:1011-1025` cross-checks the routing the brain reports against the routing the runtime
materialized — so replacing the call would need a forged telemetry. It can only go where the
*operation module* is (`neural.py:375`). But that module is called with one tensor and an
operation id, and the tensor is the attention's projection of the case, whose one-hots are destroyed
by the projection. So the frozen input rule cannot read it, and the clean case is not reachable.

**Route D is the fix: pass the case to the operation.** This appendix is that patch.

## 2. The patch, in seven edits and 22 lines

Applied by `prepare_route_d_patch.py`, which copies the runtime into a scratch tree, asserts every
anchor, patches the copy, and compiles all 34 modules. **The frozen source is never written to.**

| # | file | the edit | why |
|---|---|---|---|
| 1 | `neural.py` | adds `from typing import Any, Mapping` | the patch's annotations need them (see §4) |
| 2 | `neural.py` | `RegisteredOperationBank.__init__` gains `self._active_case = None` | a place to hold the case |
| 3 | `neural.py` | `RegisteredOperationBank.forward` gains `case: Mapping[str, Any] \| None = None` | the operation can receive it |
| 4 | `neural.py` | `NeuralCJT` gains `set_active_case(case)` | the node can be told it |
| 5 | `neural.py` | `transformed = self.operations(operation_id, projected_effect, self._active_case)` | the node hands it over |
| 6 | `network.py` | `forward_node` gains `case=...`, sets it on the node, and clears it in a `finally` | it travels with the call and cannot leak |
| 7 | `runtime.py` | the call site passes `cause.content` | the case is already in scope — `CausePacket.content` is the task's own content — so **no new public parameter is added anywhere** |

**Measured:** all seven anchors match exactly once, the patch applies, and **34 of 34 modules compile**
after it. Both facts come from running the script, not from reading it.

## 3. Why the change is small

`runtime.py:939-950` shows `_prepare_inference` already receives a `cause: CausePacket`, and
`types.py:301` shows `CausePacket.content: Mapping[str, Any]` — the task's own content. So the case is
already inside the call the runtime is making; **the patch only carries it one frame further**.

That matters beyond tidiness: a patch that added a public parameter would change the runtime's
interface and every caller. This one changes no signature that anyone outside these three files
uses. The new parameter on `forward_node` and on the operation's `forward` is **optional and
defaults to `None`**, so every existing caller behaves as before.

## 4. A latent defect the patch found, and fixed

The first draft used `Mapping` and `Any` in `neural.py` — which **imports no typing names at all**.
My first check for that was wrong: I searched for `Any` and found five hits, all of them the built-in
`any(...)` or a tensor's `.any()`. `neural.py` has no `from typing import ...` line.

With `from __future__ import annotations` at `neural.py:9`, the annotations are never evaluated, so
the code would have run anyway. **That is exactly the kind of latent break that surfaces later** —
under `typing.get_type_hints()`, under a type checker, or on the day someone removes the future
import. The patch now adds the import (edit 1) rather than relying on the accident.

## 5. What the patch does not do, and cannot claim

- **It is not applied.** Where the runtime source is frozen, a package edit needs a new seal and the
  owner's line. The patch lives in the repository as a reviewable artifact and its script refuses to
  target the frozen directory.
- **It is not run.** No model was loaded, no torch import happened, no store was opened. The patch's
  correctness is compile-level and anchor-level, not behavioural.
- **It does not prove the bridge works.** It only makes the case *reachable* from the operation,
  which is what the frozen input rule needs. Whether the recipe brain answers the runtime's task
  correctly is still unmeasured, and is what the run would measure.
- **It does not re-open appendix A.** The frozen input rule applies unchanged on route D, which is
  route D's whole point: the brain sees the question, not a rendering of it.

## 6. Where the owner's decision now stands

| route | the edit | the identity check means | the brain sees |
|---|---|---|---|
| **D** | the patch above, 22 lines in 3 files, a new seal needed | what it says | the question |
| **A** | none | "the brain answered a projection of the question" | CASformer's rendering, so its answer depends on CASformer's weights |
| **C** | replacing the brain call | nothing — it needs a forged telemetry | — (refused) |

**The council recommends D**, and the cost of D is now known rather than estimated: twenty-two added
lines, three files, no interface change, every anchor verified, every module compiling. The price is
a new seal for the runtime package and the owner's line, which is the same price any frozen-package
edit carries.
