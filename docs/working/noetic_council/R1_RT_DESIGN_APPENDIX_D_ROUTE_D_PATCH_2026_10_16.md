# R1-RT — design, appendix D: route D's patch, prepared and checked but not applied

**Added:** 2026-10-16 PDT by the council's R1-RT turn. **Status:** A PATCH, PREPARED AND TESTED, still not applied to the frozen source. Nothing here starts a machine or spends anything. It does import the patched module and exercise it in this machine's own environment, and that is reported as what it is.

---

## 1. What this is

Appendix C measured that the recipe brain cannot be put where the runtime's *brain call* is, because
`runtime.py:1011-1025` cross-checks the routing the brain reports against the routing the runtime
materialized — so replacing the call would need a forged telemetry. It can only go where the
*operation module* is (`neural.py:375`). But that module is called with one tensor and an
operation id, and the tensor is the attention's projection of the case, whose one-hots are destroyed
by the projection. So the frozen input rule cannot read it, and the clean case is not reachable.

**Route D is the fix: pass the case to the operation.** This appendix is that patch.

## 2. The patch, in nine edits

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

**Measured:** all eight anchors match exactly once, the patch applies, and **34 of 34 modules compile**
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

## 5. It was tested by running it, not by reading it

A patch that compiles is not a patch that works. So the patched copy was **imported and exercised**,
in this machine's own environment (Python 3.14.0, torch **2.11.0+cpu**), and the one behaviour that
matters was checked directly: *does an operation actually read the case?*

`verify_route_d_case_passing.py` registers one extension operation whose `forward` records what the
bank was holding when it ran, then calls the bank three times and checks the guard:

| check | result |
|---|---|
| the operation reads the case when given one | **PASS** — it saw the probe's own case |
| the attribute is cleared after the call | **PASS** — `None`, so a case cannot leak |
| the operation sees `None` when given none | **PASS** |
| a later, different case is delivered, not sticky | **PASS** |
| an unknown operation id is still refused | **PASS** — the patch weakened no guard |

**Five of five. Route D works.**

### The defect that running it found, which reading it had missed

**The first version of the patch passed the case into the operation bank and then dropped it on the
floor.** The call site at `neural.py:375` looked correct, every anchor matched, all 34 modules
compiled — and the operation still could not read anything, because an operation's `forward` takes
only `value`, so the case arrived as an unused parameter.

The fix is one more edit: the bank now **holds** the case in `self._active_case` for the duration of
the call and clears it in a `finally`. **Compile-level verification would never have caught this.**
It was caught by reading what the bank did with `case`, and then by a probe that asserts it.

### Three environment facts the run produced

1. **`cas_cjt` is ALSO installed in site-packages**, as an older, unpatched copy (24 modules against
   the frozen tree's 34). The first probe run silently tested **that** copy and reported a refusal
   from it while claiming to test the patch. The probe now puts the patched root first and **prints
   which `cas_cjt` it is using**, so this cannot happen unnoticed.
2. **The built-in operations take relation indices 0 to 3** (`^6` decompose, `^2` attract, `^3`
   avert, `^8` trigger), and the bank refuses a duplicate. A new identity needs index 4 and a
   `num_relations` of at least 5. Measured from the source after two refusals taught us.
3. **An extension operation cannot execute until its contract is bound**, and the contract's own
   validator refuses invented values: `legal_bias_paths` must start with `/memory`, `/rpm`,
   `/operating` or `/theta`, and five tuple fields must be non-empty. The probe now **copies the real
   contract values from `state.py:154-200`** rather than inventing a schema, and two earlier attempts
   that guessed were refused. That is the runtime's schema discipline working as intended.

### What this does and does not establish

**Established:** the patched operation bank delivers the case to an extension operation, clears it,
does not leak it, and still refuses unknown operations; and the patched module imports in this
machine's environment.

**Not established:** that a full runtime starts, that a store opens, that CASformer runs, or that a
recipe brain answers correctly. Those need a runtime creation, which needs the GB3 `gb` package and a
store, and this machine had **516 MiB free of 16 GiB** when this was measured — so it was not
attempted here. A bare torch import costs **202.0 MiB peak** against the project's 300 MiB limit,
which is why this is a probe and not a run.

### A full runtime starts with the patched module — measured

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

## 6. What the patch does not do, and cannot claim

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

## 7. Where the owner's decision now stands

| route | the edit | the identity check means | the brain sees |
|---|---|---|---|
| **D** | the patch above, 22 lines in 3 files, a new seal needed | what it says | the question |
| **A** | none | "the brain answered a projection of the question" | CASformer's rendering, so its answer depends on CASformer's weights |
| **C** | replacing the brain call | nothing — it needs a forged telemetry | — (refused) |

**The council recommends D**, and the cost of D is now known rather than estimated: twenty-two added
lines, three files, no interface change, every anchor verified, every module compiling. The price is
a new seal for the runtime package and the owner's line, which is the same price any frozen-package
edit carries.
