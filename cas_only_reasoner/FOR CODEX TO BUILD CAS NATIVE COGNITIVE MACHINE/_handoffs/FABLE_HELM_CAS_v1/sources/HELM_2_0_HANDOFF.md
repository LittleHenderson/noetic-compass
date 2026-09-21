# Helm 2.0 — handoff to the next agent

**Branch:** `research/helm-2.0-iterating-rounds`, cut from `codex/cncm-vision-next`.
**Date:** 2026-09-20. **Cost so far: $0.** No GPU, no AWS, no claim promoted.
**Read first:** `HELM_ARCHITECTURE_FINDING_AND_PLAN.md` (why), then
`AUDIT_REPORT_20260920_INDEPENDENT.md` (what the audit found), then this file (what is built).

**Nothing here is a result.** Code changed; no run has been made. The only thing measured is that
the machine is now CAPABLE of things Helm 1.0 could not represent. Whether it does them is a
question for a run and for the frozen grader, which is untouched.

---

## The one-paragraph version

Helm 1.0's eight reasoning rounds were one round repeated eight times: the loop aggregated the
frozen input features instead of its own state, so the round input was bitwise identical every
round and the receptive field was exactly one hop. That is fixed. Two heads that could not express
their own task are fixed too. The optimiser now clips and can follow a schedule. The brain went
from **157,919** numbers in **46** groups to **174,303** in **48** — **+16,384, +10.4%**.

---

## What is DONE

| id | change | where | state |
|---|---|---|---|
| **F1** | **the loop reads its own state** | `pointer_learner.py:_rounds` | ✅ done, gate passes |
| F1b | `state_encode` `Linear(64,64)`, the round's own encoder | `_PointerContainer.__init__`, `_block_input` | ✅ +4,096 |
| F1c | `BLOCK_INPUT_WIDTH` `3*NODE_ROW_WIDTH` → `3*WIDTH` (54 → 192) | module constants | ✅ |
| **F2a** | **the reach head is shown the node pair it judges** | `_pair_states`, `_reach_options` | ✅ +8,192 |
| **F2b** | **correspondence gets a bilinear pair score + Sinkhorn** | `match_key`, `_mapping_logits` | ✅ +4,096 |
| **F4a** | **gradient clipping, recorded in every update row** | `commit`/step block | ✅ `GRADIENT_CLIP_NORM = 1.0` |
| **F4b** | **warm-up then cosine schedule, opt-in** | `_learning_rate` | ✅ see the seam below |
| — | the $0 gate, 6 checks | `rounds_iterate_check.py` | ✅ `ROUNDS_ITERATE_PASS` |

### What the gate prints today

```
python records/typed_pointer_001/rounds_iterate_check.py     ->  ROUNDS_ITERATE_PASS
  True | _rounds has no assigned-and-never-read name
  True | the round input is three STATE vectors
  True | the round input differs across rounds
  True | a change two hops away reaches the node
  True | the reach mode head receives the query's node pair
  True | different sources can prefer different targets
  params 174303  groups 48
```

Run this before touching anything. **If it does not print `ROUNDS_ITERATE_PASS`, stop.**

Two readings worth keeping: the round-to-round difference now **grows monotonically**
(0.034, 0.068, 0.102, 0.135, 0.167, 0.199, 0.230 against round 0), which is information spreading
one hop per round; and the two-hop test moved from exactly `0.000e+00` to a non-zero difference.

### The learning-rate seam — read this before you run anything

The schedule is **opt-in and defaults to Helm 1.0's constant rate**. It turns on only when the
caller puts `planned_main_updates` in `limits`:

```python
limits = {..., "planned_main_updates": 1470}      # warm-up 5%, then cosine to 10% of base
limits = {...}                                     # absent -> constant 0.003, exactly Helm 1.0
```

Every update row now records `learning_rate_this_step`, `learning_rate_schedule`,
`gradient_norm_before_clip`, `gradient_clip_norm` and `gradient_was_clipped`, so both guards are
auditable rather than trusted. **The worker does not pass `planned_main_updates` yet** — see the
first item under NOT DONE.

Sanity reading at 1470 planned updates, base `0.003`:
`update 0 -> 0.000041`, `73 -> 0.003000` (warm-up ends), `735 -> 0.001761`, `1469 -> 0.000300`.

---

## What is NOT DONE — pick up here

Ordered by what I would do next.

### 1. Wire `planned_main_updates` through the worker  🔧 small, $0
The schedule exists but nothing sets it. Find where `typed_pointer_worker.py` builds `limits` for
`PointerCourseLearner` and add the run's planned main-update count (1470 for the ten-pass plan;
take it from the schedule stats, do not retype the number). Until this lands, every run silently
uses the constant rate — which is safe, but means F4b is dormant.

### 2. F4c — report held-back loss every pass  🔧 small, $0
`AUDIT_PACK.md` trap 4 says training loss is not learning. Today only training loss is in the
update rows. Add the held-back set's loss per pass to the progress record so the curve people
actually read is the right curve.

### 3. F2c — multi-head attention  🔧 small
`attention_key` is `Linear(64, 1)`: **64 numbers, one scalar score per node, for all of pooling.**
Replace with 4 heads of width 16 (4×64 = 256 numbers). Cheap; lets the world vector attend to more
than one thing at a time.

### 4. F3 — BUILT. `records/typed_pointer_001/ladder/` — read `LADDER_README.md`  ✅
18 worlds at 4/6/10/16/25/40 nodes, 1,072 questions, difficulty axis = hop distance, continuous
score beside exact match, zero-learning envelope shipped inside the artifact, disjoint labels
proven, byte-deterministic (digest `4436fb6b481ff606`). **373 evidence questions at distance >= 2.**
The bar there is `best_zero_learning` ~0.53, NOT zero. `parts`/`edge_account` are a size CONTROL,
never evidence. No model has run on it. What remains of F3 is only WIRING: a runner that feeds
`ladder_v0_1.json` through the worker and scores with `build_ladder.py:score`.

#### (original F3 brief, kept for the record)
**This is the largest remaining item and it gates every scaling run.** Eighteen yes/no questions
about four-node worlds cannot show a continuous curve — eleven of the nineteen possible scores are
already reachable by a rule that learns nothing. Needed:
- a **difficulty ladder**: worlds at 4, 6, 10, 16, 25, 40 nodes; questions at hop-distance 1..5+;
- a **continuous score** beside exact match (per-slot log-likelihood, or edge-set F1);
- **hundreds** of held-out questions, stratified by hop-distance and world size;
- the **mechanism-free baseline plotted on every chart** — the one-hop adjacency rule's line. A
  curve above it is a result; a curve tracking it is not. This is the single most important habit
  the audit produced.

**Build this BESIDE the frozen 18. Never change the frozen 18 or the pass mark** — `BRAIN_LINEAGE.md`
rule 4. The ten-node development panel (`7/59, 9/59, 6/59` under Helm 1.0) is the first rung and
the natural place to start: it is already wired, already scored every pass, and already has
headroom.

### 5. F5 — scale, only after 1–4  🔧 GPU, money
In this order: `CORE_ROUNDS` 8 → 12 → 16 first (**zero new parameters**, the round is shared, so it
is the cheapest capability per pound in the system); then `d_model` 64 → 128; then more taught
worlds; then try shrinking `declaration_table` from 1024 to 512 rows and spending the freed ~32k on
the core. Measure both ways — `definition` and `context` are currently perfect and that table is
what carries them.

---

## Things that will bite you

1. **A Helm 1.0 checkpoint will not load strictly.** Three tensors differ:
   `state_encode.weight` (new), `match_key.weight` (new), `reach_option_head.0.weight` (widened
   `132 → 260`). `rounds_iterate_check.py:_container` shows the honest way to handle it — drop and
   REPORT both classes, never silently coerce. Anything restoring a 1.0 checkpoint into a 2.0
   container must do the same, and a **practice-checkpoint phase-A restore may need the same
   treatment — I have not exercised that path.**

2. **The frozen rehearsal copy must not be touched.**
   `records/typed_pointer_001/admission_001/rehearsal/.../pointer_learner.py` is a frozen artefact
   of the Helm 1.0 study. I left it alone. Leave it alone.

3. **The loop is now genuinely recurrent, so it can diverge.** `PER_ROUND_UPDATE_CAP = 0.01` and the
   `rms` after each round are what hold it, and they were already there. If you raise `CORE_ROUNDS`,
   watch for `POINTER_STATE_NONFINITE`.

4. **Helm 1.0's numbers do not carry over.** Different shape, different brain. Under
   `BRAIN_LINEAGE.md`'s own versioning a shape change is a **2.0** and gets its own row. **I did not
   touch `BRAIN_LINEAGE.md`.** Helm 1.0 stays exactly as certified.

5. **Never edit `pointer_learner.py` while a preflight is running.** The worker re-reads its
   source files and checks them against a source attestation, so an edit landing mid-run kills it
   with `ValueError: TYPED_MATCHED:SOURCES_CHANGED` after however long it had already spent. I did
   exactly this to the audit's own check-4 run and threw away about nine minutes of it. The
   attestation is taken from what is ON DISK when the run starts, which is why the Helm 2.0
   preflight -- started after the edits -- passes it without any pin needing to change.

6. **Sinkhorn is in the log domain** (`scores - logsumexp(rows)`, then `- logsumexp(columns)`,
   `SINKHORN_STEPS = 3`). The output is still logits, so the loss and `slots._check_scores` consume
   it unchanged. `_mapping_logits` caches per plan on purpose — normalising one row in isolation
   would put back exactly the independence it replaces.

---

## Verification state, honestly

| check | state |
|---|---|
| `rounds_iterate_check.py`, 6 checks | ✅ **PASS**, 174,303 params, 48 groups |
| `pytest tests/test_typed_pointer_study.py` after F1 alone | ✅ **22 passed** |
| `pytest` after F1 + F2a + F2b + F4 | ✅ **22 passed in 147.46s** |
| `preflight_dry_run.py` end-to-end on Helm 2.0 | 🟨 **seed 1 COMPLETE** (`COMPLETE_TYPED_POINTER_ARM`, no failed checks, 551 files, 1804.61 s); **seed 2 killed by the tool harness** at pass 8, update 1100 of 1470, exit 127, no Python error. Re-run from a real terminal, not through an agent's Bash tool — a 45+ minute CPU job gets cut. |
| F4 recording exercised end to end | ⬜ **NO.** The dry run's stand-in brain bypasses `PointerCourseLearner`'s step, so its update rows carry none of the F4 fields (`learning_rate_schedule` is absent). F4 is unit-checked only. The first real run is what exercises it. |
| any GPU run | ⬜ **none. No money spent, nothing claimed.** |

**Confirm the preflight finished before you build anything on top of this.** The preflight wants a directory
that does **not exist** — it stops with `FileExistsError` if you create it first.

```bash
python records/typed_pointer_001/rounds_iterate_check.py
python -m pytest tests/test_typed_pointer_study.py -q
python records/typed_pointer_001/preflight_dry_run.py <a path that does not exist>
```

---

## Still open from the audit, untouched by this work

These are separate from the architecture and none of them is mine to decide:

1. The zero-learning floor of **11 of 18** is missing from `BRAIN_LINEAGE.md`.
2. The grader does **not** check the scoring files against the sha256 the run recorded for them in
   its own `artifact_manifest.json`. I demonstrated a fabricated pass through that gap.
3. `BRAIN_LINEAGE.md` says "new wiring"; all five held worlds' link patterns occur among the taught
   worlds. And `Chuck` and `Gear` were both taught.
