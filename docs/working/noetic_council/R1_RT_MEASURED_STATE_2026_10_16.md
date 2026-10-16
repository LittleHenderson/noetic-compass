# The council's third target — R1-RT measured before anything is built

**Added:** 2026-10-16 PDT. **Status:** measurement only. Nothing here runs a model, spends money,
or claims anything about the recipe brain's quality.

## Why this file exists

`WAVES.md` lists R1-RT — "host the brain inside HELM's own runtime" — as **optional** and its state
as **"not designed"**. Wave 1 gave it half its gate: "W1's reading and the owner's word". The
reading now exists (spec sheet §7.47). The design does not.

Before any design is written, the prerequisite state should be on the record rather than in a
document's optimism. So the council's loop was pointed at R1-RT and its conditions were measured
with program readings. Each reading names the file or search that produced it, and a reading that
cannot be taken returns `None`, which **blocks** the gate instead of passing it.

Run it:

```
C:\Python314\python.exe -B run_loop_helm_r1_rt.py      # one turn of the loop
C:\Python314\python.exe -B target_helm_r1_rt.py        # just the readings
```

Both need `council_loop.py` and the RPM engine beside them; the paths are stated in the directive,
`docs/working/helm_tks_noetic_council_directive_2026_10_16.md`.

## What the readings found, 2026-10-16

| Condition | Reading |
|---|---|
| the runtime is on disk and nameable | ✅ 34 python files; the ones R1-RT would touch are `runtime.py`, `persistence.py`, `semantic.py`, `neural.py`, `control.py`, `cncm_bridge.py` |
| the runtime has a durable store | ✅ SQLite, WAL and `BEGIN IMMEDIATE` all present in `persistence.py` |
| the recipe brain's state can be written and reloaded with a check | ✅ `rb/state.py`: one JSON document, atomic write, format marker, sha256 and a recomputed state digest on reload |
| the claim boundary is stated | ✅ the wave-1 reading already excludes "operation inside HELM's runtime" in its own words, so R1-RT is a **new test**, not an upgrade of wave 1's claim |
| an adapter carrying the recipe brain into the runtime | 🟥 **none exists.** `cas_cjt/cncm_bridge.py` is present but **INERT**: it grants `INERT_PROPOSAL_ONLY_NOT_ADMITTED_BY_CURRENT_CNCM` and imports no kernel |
| R1-RT's own gate | 🟧 **HALF MET.** The reading half is licensed. **No record anywhere approves R1-RT.** The owner's half of a gate is not an agent's to give, so this reading is `None` and it blocks |
| an R1-RT design | 🟥 **none.** `WAVES.md`'s own word for this row is "not designed" |

The RPM diagnosis for this target reads: blocker `UNKNOWN`, blocked stage `D` (is the condition
understood and specified), with the physical failure at evidence stage `P` on three leaves —
`RT_SPECIFIED`, `RT_BRIDGE_EXISTS` and `RT_GATE_OPEN`.

## The measurement that decides how big R1-RT is

The two sides share no vocabulary, and one of them assumes the other is a neural network:

- **GB3's task** is `native.route_dependency_audit/1`: a directed graph on eight nodes plus a
  proposed route; the answer is the first unsupported leg (`FIRST_UNSUPPORTED_LEG_0` to `_6`) or
  `ALL_LEGS_PRESENT`. Input is float32 `[1,8,64]`; the brain emits eight logits.
  (`base/accepted_observer_r2/TASK_CONTRACT.md`, lines 9–41.)
- **The recipe brain's** family is CAS v7.6 production semantics: ingredients, stock, requirement,
  yield = min(stock / requirement), and the Limiting Reagent decides.
- **The runtime imports torch and its state checks are tensor operations.** `runtime.py` line 9 is
  `import torch`; line 529 is `expected = operation.state_dict()`; line 548 is
  `operation.load_state_dict(retained, strict=True)`; line 1013 is `torch.equal(...)`.

So R1-RT is not a rename and not a wrapper alone. The runtime's own validity checks are written
against a `state_dict` of tensors, and a brain whose state is a JSON document of recipes satisfies
none of them. **That is the real content of the missing design**, and it is the question the ten
seats were sent to answer.

## What this file deliberately does not do

- It does not write the design. `RT_SPECIFIED` is the condition the council exists to move, and
  moving it by fiat would be the substitution this project keeps getting bitten by.
- It does not change any runtime file, any package, or any ledger.
- It does not claim the recipe brain is ready to be hosted. It measures what a host would need.
- It does not give the owner's half of the gate. That reading is `None` on purpose.

## The two clean paths this measurement leaves open

1. **Design first, gate second.** The council produces the R1-RT design (what runs, on which exam,
   read by which program, with its acceptance test frozen before any code). The owner then gives or
   withholds the word, and the run happens only on his word.
2. **Gate first, design second.** The owner says yes now; the council still has to produce the
   design, because no run may start without a frozen acceptance test.

Either way the missing artifact is the same, and it is written, not run.
