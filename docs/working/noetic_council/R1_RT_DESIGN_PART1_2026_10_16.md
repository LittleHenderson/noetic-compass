# R1-RT — design, first part: the three names, the acceptance test, and the coupling

**Added:** 2026-10-16 PDT by the council's R1-RT turn. **Status:** DESIGN, PART ONE. This names
what must be named before any mark is answerable. It does not pick the shape, does not run
anything, and changes no package.

Part two — the run plan, the marks and the arms — cannot be written until two things exist: the
owner's shape choice (section 4), and the answer to whether the recipe brain must read its own
state through HELM's store (section 3).

---

## 1. The three names, which the target sentence left ambiguous

The target says "the same answers inside HELM that wave 1 measured outside it." Measured, that
comparison is not available as written, so the design must name three things explicitly.

### Name 1 — which brain is being replaced

**The `cas_cjt` runtime's own task is `native.route_dependency_audit/1`** — a directed graph on
eight nodes plus a proposed route; the answer is the first unsupported leg
(`FIRST_UNSUPPORTED_LEG_0` … `_6`) or `ALL_LEGS_PRESENT`. Eight labels.

**GB3's task is 16 synthetic two-board worlds with labels `L0`–`L3`.** Four labels. GB3's package
ships **no** `cas_cjt` python at all — only `bias_state.schema.json` and
`neural_cjt_contracts.schema.json` — and its own `README_GB3.md:93` says of itself: *"No native
checkpoint, no ASOM, **no native task**…"*

They are **two different machines with two different tasks**, and the string `GB3` appears **0**
times in the runtime's 34 files. So "GB3's slot" and "HELM's own runtime" are not interchangeable.
The design names the runtime as the host and therefore inherits **its** task.

### Name 2 — which task and label set the hosted run is scored on

`native.route_dependency_audit/1`, eight labels, input float32 `[1,8,64]`. This is not a choice:
`cas_cjt/teaching.py:31` pins `TASK_SOURCE_SHA256 = "ec6d06a45adc66a740e607824786a035a69e9a49967d6c1f70cc66a838709d93"`
and lines 52–53 require the task module at an exact path or raise `TASK_MODULE_LOCATION_MISMATCH`.
The file re-hashes to exactly that value. **The hosted run does not choose its task.**

### Name 3 — which repair mechanism counts as "the real nested repair"

Six separate documents call the recipe brain's repair frame a stand-in, in the same shape:
*"a built-in mechanism check, **not the HELM runtime**"* (`PREREGISTRATION_RB1G2.md:32`,
`README_RB1G2.md:92`, `rb/driver.py:68`, `FROZEN.precode.json:93`, `TEST_PLAN_HELM_R1.md:61`,
`OPEN_QUESTIONS.md` Q15). Two different mechanisms exist and they are not the same object:

| | the recipe brain's analog | the runtime's real frame |
|---|---|---|
| where | `rb/driver.py:67 nested_frame` — a pure in-memory `copy()` | `runtime.py:793-877` + `repair.py:52` |
| depth cap | 5 | 3 |
| extra requirement | none | forces a **second distinct node** at `t+1` and resumption at `t+2` |
| its record | reported only, tagged `Q15` | `readwrite.restart.db`, `correct = 15`, `state_digest = eb8c2209…` |

**The design names the runtime's own frame.** The analog's 4 of 4 must never be reported as HELM's
repair, and GB3's 1 of 4 must never be attributed to the recipe brain.

## 2. The acceptance test, as a program would read it

Frozen before any code. Every mark is **identity**, not improvement: a higher score than wave 1
would be a fault, because R1-RT is a hosting and continuity check.

| mark | what it compares | denominator | pass rule |
|---|---|---|---|
| `RT_IDENTITY_PANEL` | the recipe brain's ordered answers **from inside the runtime** against its ordered answers **from outside**, on the same worlds and the same encoding | the panel's world count, stated at freeze | every world equal, symbol for symbol |
| `RT_IDENTITY_FRESH` | the same comparison on a fresh sealed set | the fresh count | every world equal |
| `RT_RESTART_STORE` | the hosted brain's answers after the process restarts and reloads through HELM's store | the panel count | every world equal to the pre-restart answers |
| `RT_STORE_INTEGRITY` | the store's own integrity reading for those rows | the row count | no integrity failure; every row present and validated |
| `RT_NESTED_FRAME` | the runtime's own repair frame, entered and resumed | the frame's own denominator | reported: `repair_correct`, `repair_returned`, `repair_total` — **with no pass rule**, because a mechanically clean frame that destroys answers is a finding, not a pass |
| `RT_NON_VACUOUS` | the control that stops a vacuous pass | a deliberately broken interface (see below) | the broken interface must **fail** these marks, or the whole reading is `INSTRUMENT_ERROR` |

**`RT_NON_VACUOUS` is the mark that makes the rest mean anything.** Seat CO-2 measured that all
four of wave 1's panels read **0** `UNDETERMINED`, so the one interface defect that would make
"the same answers" meaningless could pass unnoticed. The control is a copy of the interface with
its translation stripped out; if the identity marks still pass with it, they were measuring nothing.

**Verdict order:** `INSTRUMENT_ERROR` → `FAILURE` → `R1_RT_IDENTITY_HOLDS`.

## 3. The coupling, now measured exactly — and why it decides the shape

This is the new measurement of this turn, and it is worse than "the runtime imports torch".

**`cas_cjt/persistence.py` — the store itself — imports no torch at all.** I read its imports: they
are `dataclasses`, `hashlib`, `hmac`, `json`, `pathlib`, `sqlite3`, `typing` and five sibling
modules. Zero torch.

**But it cannot be imported in a torch-free process.** I ran it with torch and numpy blocked by a
meta-path finder and the import was **refused**. Tracing the graph:

- of the runtime's 34 modules, **17 import torch or numpy directly**
- from `persistence`, **31 modules are reachable**
- of those, **16 of the 17 torch-importing modules are reachable** — every one except `runtime.py`
  itself

**Why the store drags torch in:** it validates what it stores. `persistence.py` calls
`validate_contract` and `repair_frame_from_dict` and `bias_from_dict`, and the state path runs
through `types.TensorArtifactRef` and `state.tensor_ref_from_mapping` into `checkpoint.py`, which
imports `torch` and `torch.nn` at lines 10–11 and builds `_DTYPE_TO_NAME` as a dict keyed by
**`torch.dtype` objects** at line 20. A dictionary keyed by torch dtypes cannot exist in a process
that does not have torch.

**So the torch-free store does not exist as a layer.** It exists as a *file* with torch-free
imports, welded into the runtime's validation chain, which is torch through and through.

### What that does to the three shapes

| shape | does it survive this measurement? |
|---|---|
| **1 — two processes**, the brain answering across a boundary | **Only if the recipe brain never reads or writes its own state through the store.** If it must, then the process holding the store has torch, and the only question left is which process the recipe brain lives in — which is the same question as shape 2. |
| **2 — drop the blocker**, let the recipe brain's process hold torch | **Survives.** The blocker is the only obstacle, and it is a package edit: a new seal and a new owner line. The recipe brain's own algorithms do not need torch; its package merely refuses to be in a process that has it. |
| **3 — a torch-shaped stand-in** | Refused, and this measurement shows why it is worse than it looked: the stand-in would have to supply `torch.dtype` objects that key a dict, so `validate_contract` would pass on a fabricated type system. That is a check that has stopped being a check. |

**The open question, and it is the one that decides everything:** does the hosted recipe brain have
to read or write its own learned state through `cas_cjt/persistence.py`, or can its state live in
the same SQLite database through a path that does not run the runtime's neural validation? The
target says *"surviving a restart through HELM's own store"*, which sounds like the first. Nobody
has measured it. **Until it is measured, shape 1 cannot be priced and shape 2 cannot be ruled out.**

### The open question, answered — measured in this same turn

I measured it, and the answer is **no**. The recipe brain never touches the runtime's store, and it
never imports the runtime at all.

Across the whole sealed v3 package, counting every `.py` file at every depth:

| token looked for | occurrences in the recipe package |
|---|---|
| `persistence` | **0** |
| `BEGIN IMMEDIATE` | **0** |
| `CommitReceipt` | **0** |
| `validate_contract` | **0** |
| `cas_cjt` | 9 — and **every one of them is either a comment or a docstring, or a file on the transformer side** |

The nine are: `params.py:4`, `t_b.py:15` and `t_b.py:122` (comments and docstrings describing the
runtime's `^6` operation and its decoder contract), and six real imports in `t_gb_check.py:55`,
`t_b.py:72-75` and `score_t.py:50` — **all of which are the transformer arm, not the recipe brain.**
The recipe brain's own modules (`rb/`, `rb2/`, `rb3/`, `r1/`) import the runtime **zero** times.

And it persists through its own file, not any store: `rb/state.py` writes one JSON document
(`partial` → `fsync` → `rename`) with a format marker and a recomputed state digest, and its only
callers are within the package itself (`driver.py:300/341/377`, `gb_ls.py:171`, `tb_arms.py:34`,
`cce_stage.py:19/49`).

**What this settles.** The sentence *"surviving a restart through HELM's own store"* cannot mean
that the runtime's SQLite holds the recipe brain's learned state, because nothing in the recipe
brain asks it to and the store's validation would refuse a JSON brain anyway. So the restart claim
must be re-worded, and there are exactly two honest readings:

1. **A reference, not the state.** The runtime's store holds a reference to the recipe brain's own
   state document, and the restart is survived by reloading that document behind the store's
   bookkeeping. The identity marks then test the reload, and the store's role is stated as
   bookkeeping rather than as the holder of the brain.
2. **The state is the runtime's.** The runtime's store holds it, which requires the runtime's
   validation to accept a non-tensor state — a runtime edit, with everything that implies.

**Reading 1 survives the measurement with both guarantees intact**; reading 2 does not. And this
also removes shape 1's fatal objection: because the recipe brain never calls the store, a
**torch-free process** holding the recipe brain is genuinely torch-free, and the store process keeps
its torch. The two processes need a protocol, not a shared type system.

## 4. What the owner is being asked

The measurement in section 3 changes what is being asked, so it is stated in its new form:

- **Shape 1 — two processes.** Now known to be coherent: the recipe brain's process stays torch-free
  because it never calls the store, and the runtime's process keeps torch and holds a *reference* to
  the brain's state document. **Costs:** a process boundary whose protocol is undesigned, and a
  re-worded restart claim (bookkeeping, not custody). **Keeps:** both guarantees intact.
- **Shape 2 — drop the blocker.** The recipe brain's process holds torch. Simpler plumbing, and it
  makes the store's direct custody of the state possible — but only if the runtime's validation is
  also taught to accept a JSON state, which is a second, larger edit. **Costs:** a guarantee the
  package was built to enforce and its preregistration requires, hence a new seal and the owner's
  line.
- **Shape 3 — a torch-shaped stand-in.** Refused, and section 3 shows why it is worse than it
  looked: it would have to supply `torch.dtype` objects that key a dict (`artifacts.py:175`,
  `checkpoint.py:20`), so `validate_contract` would pass on a fabricated type system.

**The council's recommendation, now that the measurement is in:** **shape 1, with the restart claim
re-worded to reading 1.** The reason is not that it is cheaper but that it is the only shape that
keeps every guarantee both packages were built to hold, and the measurement shows the price is a
protocol rather than a rewrite. **The decision is still the owner's**, and shape 2 remains a
legitimate choice if he prefers one process over one boundary.

## 5. What this document is not

- Not the full run plan. This is part one: the three names, the acceptance test, the coupling, and
  the shape recommendation. Part two adds the arms, the machine, the window and the cost envelope.
- Not a claim. Nothing has been hosted, nothing has been compared, no mark has a value.
- Not a shape decision taken by an agent. Section 4 is the owner's, and the recommendation above is
  a recommendation.
