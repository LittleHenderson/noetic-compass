# TIER C C1 PREREGISTRATION — transform tournament

**Frozen before any GPU spend. Development-only, non-claim-bearing.**
Owner authorization: "GLM's C0 assessment: ACCEPT / C1 launch: AUTHORIZED / Hard cap:
$0.80, one GPU instance / Protected split: CLOSED / C2: NOT AUTO-AUTHORIZED /
'Specific' after C1: TOO EARLY" (2026-09-01).

---

## 1. What C1 is for (the ladder, kept straight)

| Stage | Job | What it can establish |
|---|---|---|
| C0 (done) | build and inspect the CAS rulebook | the algebra and controls are coherent |
| **C1 (this)** | **find the best neural socket for that rulebook** | **which transform can use relational structure** |
| C2 (not authorized) | put competing rulebooks into the same socket | whether CAS's relational content beats learned and empirical alternatives |

C1 answers only: **which transform turns the relation algebra into useful neural
behavior?** A C1 win supports `THIS NEURAL TRANSFORM CAN USE R` and nothing more.
It does **not** support `THE CAS VERSION OF R IS BETTER THAN SERIOUS ALTERNATIVES` —
that is C2, which does not auto-launch. **"Specific" language is prohibited in every
C1 artifact and report**, whatever the numbers say.

> **Amended 2026-09-01 after a 35-agent adversarial pre-launch review** (13 confirmed
> findings, all fixed before spend; record: `TIER_C_C1_REVIEW_FINDINGS.json`). The
> amendments are recorded inline below and marked **[AMENDED]**. Every amendment either
> removes something I had added, or *strengthens* a criterion toward the owner's nine
> laws. No threshold was lowered.

## 2. Arms **[AMENDED]**

**T0 + four transforms, three seeds {11, 23, 47} = 15 training runs.**

Originally each transform was to be raced against its own "NULL sibling" (an all-zero
table), 24 runs. The review proved those four siblings are **bit-identical models**:
with an all-zero table the structure term is exactly 0, structure gradients are exactly
0, and the shared modules are built first from the same seed, so all four produce
identical trajectories (measured: max |logp difference| = 0.000e+00 after 25 AdamW
steps). Running one shared baseline per seed is therefore **exact, not an
approximation** — and it restores the owner's literal `T0 no relational structure` arm
instead of my four-way substitute. 9 wasted runs removed.

- **T1** additive structural routing: `s2_j += ν·Σ_i a1_i·⟨w_φ, φ(cls_i, cls_j)⟩`
- **T2** operation-conditioned matrix: `msg_j = Σ_i a1_i·M[i,j]·A[rt(i,j)]·k1_i`,
  `s2_j += ν·⟨W_q2 q1, msg_j⟩/√d`
- **T3** bilinear question-operation-entity: `s2_j += ν·Σ_i a1_i·M[i,j]·(q2ᵀ B[jt(i,j)] k2_j)/√d`
- **T4** recurrent composition: hop-1 refinement `a1' = softmax(s1 + ν_a·Σ_k a1_k·⟨w_φ1, φ(k,i)⟩)`
  then `s2_j += ν_b·Σ_i a1'_i·⟨w_φ2, φ(i,j)⟩`

**T0** allocates no structure parameters at all and is the shared baseline every
transform is measured against. Total parameter counts stay matched within 1%
(measured spread 0.455%: T0 3,581,582 / T1 3,581,603 / T2 3,597,967 / T3 3,593,871 /
T4 3,581,624). **Disclosed:** the *structure-channel* parameter counts differ hugely by
design (T0 0, T1 21, T2 16,385, T3 12,289, T4 42) — the ±1% law matches totals, and
both counts are reported so nobody can mistake nominal matching for equal
structure capacity.

**Every arm keeps the exact one-hot operation-label channel** (the A1 `w_r` pathway).
So C1 measures what the **table** adds *beyond labels* — labels are held constant and
are not the variable under test.

## 3. Frozen laws (owner's nine, plus how each is honored)

1. **R-RANDOM matching** — pool matched on defined cells, sparsity, row/col marginals,
   result/mediator frequencies, symmetric-pair count (verified 0 for R-CAS and every
   pool member), sign/duality counts, M-rank, walk counts (2,3,4), automorphism-group
   size (=1); 3455 members, none isomorphic to R-CAS. R-RANDOM is used in C1 only as an
   **eval-time ablation**, and remains classified `RELATIONAL_MISINFORMATION_CONTROL`.
2. **Complete per-family margins in every report** — every C1 verdict carries: overall
   accuracy, accuracy by family, margin vs the NULL sibling by family, margin after
   removing each family, mean extra correct answers, and the fraction of total gain
   supplied by each family.
3. **Dedicated split** — `C1_TRANSFORM_SELECT`, 597 records (QB_REL 196 / QB_COMP 198 /
   QB_INT 203), frozen in `tier_c/C1_SPLIT_MANIFEST.json` by the pid-keyed law
   `HashPRNG("TIERC_SPLIT|<pid>").randbelow(2)==0`.
4. **C2 stays sealed** — the 528 `C2_STRUCTURE_EVAL` records are never extracted, never
   evaluated, never inspected. Enforcement is at the extraction level: the harness
   materializes activations only for C1 pids, into its own cache directory, under a
   fail-closed content-hash binding.
5. **T0 capacity and compute matched** — parameter counts within 1% across all four
   transforms (measured spread 0.455%); identical updates, batch size, schedule, seeds,
   and evaluation for every arm. Plus a **frozen structure-channel init calibration**
   (see §4).
6. **Winner must causally depend on R** — eval-time R-removal (swap in the NULL table on
   the trained CAS model) must drop accuracy by ≥ 0.02. Corruption directions
   (permuted table, R-RANDOM table) are measured and reported for every CAS arm.
7. **Winner must improve ≥ 2 primary families** — at the same 0.02 margin.
8. **QC_VALID stays diagnostic-only** — it is not part of C1 at all.
9. **C2 does not auto-launch** — C1 emits a status and stops.

## 4. Structure-channel scaling: NONE **[AMENDED — my own fix was the defect]**

An earlier version of this preregistration froze a per-transform output scalar (T1 1.172,
T2 27.342, T3 33.746, T4 1.296) to equalize init-time structure magnitude, on the
reasoning that a transform "could lose for starting quiet rather than for being a worse
socket." **The review refuted the premise and confirmed the fix was harmful, and it has
been removed entirely.**

- The premise is false under this optimizer. AdamW's per-parameter step is ~lr regardless
  of gradient size, so it erases the init imbalance unaided: with no scaling the
  structure-magnitude spread goes 61.9× (step 0) → 3.1× (step 40) → 2.0× (step 50), i.e.
  a ~50-step transient out of 1000 updates.
- The scalar is a pure output multiplier on a channel whose parameters are then trained,
  so it multiplies the whole trajectory, not just its start. Measured with the harness's
  own optimizer: |s_str| at step 50 became T1 0.276 / T2 8.62 / T3 8.33 / T4 0.287 — a
  ~30× spread that **plateaus rather than decaying** (T3 held ~5× the base attention
  score from step 50 to step 400 and the loss never pulled it back).
- The neutrality argument I had registered — "applied identically to the CAS and NULL
  variants, so it cannot bias the comparison" — is a **non sequitur**. It is neutral
  *within* a transform; the tournament is decided by an argmax *between* transforms of
  each transform's own margin, and the scalar sets how far each transform's structure
  channel can move. It would have decided the winner.
- Secondary error: the scales were derived at `CAL_SEED`, while training uses seeds
  {11, 23, 47}, so even the claimed init equalization did not hold at the seeds actually
  used (magnitudes ranged 0.057–0.372, a 6.5× spread).

**Replacement:** no scaling of any kind. The structure-term magnitude and its ratio to
the base attention score are **logged at every checkpoint for every arm** and reported.
The ratio is **flagged but does not gate** qualification — the owner's nine C1 laws
contain no loudness criterion, an invented cap could disqualify the true winner (T4
carries two structure terms and starts above 1.0 by architecture), and admitting a
"loud" socket costs little because C2 freezes the winning transform and swaps rulebooks
*through it*, holding loudness constant across every C2 arm.

## 5. Gates before the tournament spends **[AMENDED — hardened]**

**Preflight (fail-closed, before any GPU work):**
- both dataset files match their digests declared in `PATHB_DATASET_MANIFEST.json`
  (`train` e49c7e99…, `val` 7cbbe5fa…);
- the C1 pid set matches `C1_SPLIT_MANIFEST.json`'s `c1_pids_sha256`, **and** the C2 pid
  set matches `c2_pids_sha256` — recomputed from **pids only**, so owner law 4 is now
  *verified* rather than merely *intended*, without reading a single C2 record;
- `R_CAS.json` and `R_RANDOM.json` match the digests sealed in `TIER_C_C0_RECEIPT.json`.

**C1 P0 smoke:**
- cache binding verified fail-closed (per-record content hashes, dataset manifest, model,
  tokenizer, extraction-code digest, layer, pid-set equality) **with the verified-record
  counts persisted** — no Boolean-only gate, per the spec's own §6 law;
- total parameter counts matched within 1%, **and** structure-channel counts reported
  separately;
- **every** structure parameter of every Tx receives a nonzero gradient at step 50
  (previously "any one of them", which would have passed a transform whose main tensor
  was dead while only `nu` moved);
- T0's structure term is exactly 0.0;
- table swap moves logits.

Any failure → `C1_SMOKE_FAILED`, no tournament spend.

**Construction check, run on CPU at $0 before launch:** the C0
`PROOF_OF_NON_EQUIVARIANCE` ran on `tier_c_transforms.ConformanceModel` (a d=32
synthetic scorer), but the C1 harness re-implements T1–T4 inline — so the proof did not
cover the code that will actually run. `tier_c_c1_nonequivariance_check.py` re-runs
Test A and Test B **against the real C1 executor**. Its criterion is registered
separately because the C0 constant does not transfer: consistent renaming is *exactly*
equivariant here (step-0 forward difference 0.000e+00 for every transform), but five
AdamW steps amplify float32 accumulation-order rounding, and deeper structure tensors
accumulate more. So the criterion is (i) Test A collapses to ≤ 1e-9 in float64 — a
precision witness that the equivariance is exact in exact arithmetic; (ii) the fp32
Test-A residual is ≤ 1e-3 of the Test-B divergence the proof relies on; (iii) Test B
diverges ≥ 1e-3 for every non-identity permutation. Result artifact:
`tier_c/C1_EXECUTOR_NONEQUIVARIANCE.json`.

## 5a. Evidence durability **[AMENDED]**

The 15 runs are written incrementally to `TIERC_C1_PARTIAL_RUNS.json` after **every**
run, and the tournament loop is wrapped so that a mid-run failure writes
`TIERC_C1_ABORTED.json` with the completed runs, the traceback, and the cost so far.
Previously a single failure on run 15 would have destroyed all evidence and the whole
budget.

## 6. Deterministic selection law (frozen) **[AMENDED — strengthened only]**

A transform **qualifies** iff *all four* hold:
- margin over **T0** ≥ **0.02** overall, **and**
- margin ≥ 0.02 on ≥ **2 of 3** primary families, **and**
- eval-time R-**removal** fall ≥ **0.02**, **and**
- eval-time max R-**corruption** fall (permuted table, R-RANDOM table) ≥ **0.02**.

The fourth clause is new: owner law 6 says "remove **or corrupt** R and performance must
fall", and my original law implemented only removal while computing the corruption
controls and never using them. Adding the clause makes qualification **stricter**, never
looser.

Winner = qualifying transform with the largest overall margin; ties broken toward the
**simpler** transform (T1 < T2 < T3 < T4).

Statuses: `TRANSFORM_SELECTED:<Tx>` | `NO_TRANSFORM_CONSUMES_STRUCTURE`.

### 6a. Saturation disclosure **[AMENDED — registered before the run]**

In the predecessor A1 result **QB_COMP scored 1.000 for every arm** (375/375 in 10 of
12 runs). A family at ceiling cannot exhibit a 0.02 margin for *any* arm. So the frozen
"≥ 2 of 3 families" clause is, in practice, **"QB_REL and QB_INT must both move"** — and
QB_INT sat near 0.38 in A1. **The clause is applied UNCHANGED — it is not weakened,
re-scoped, or reinterpreted.** What is added is transparency: the results carry
per-family saturation flags and a **report-only** `families_at_margin_excluding_saturated`
field, so that a `NO_TRANSFORM_CONSUMES_STRUCTURE` outcome driven by a ceiling is
*visible as such* rather than silently attributed to the transforms. This is registered
in advance precisely so it cannot be offered afterwards as an excuse.

**Noise disclosure (registered before the run):** per-family C1 counts ≈ 199, so a
single-seed family accuracy has sd ≈ √(0.25/199) ≈ 0.035 and a 3-seed mean has standard
error ≈ 0.020. **The 0.02 family margin is therefore roughly one standard error** — it
is a decision threshold, not a significance claim, and is applied by the deterministic
law regardless of what the numbers turn out to be. Overall margins (597 records) carry
se ≈ 0.012. This is stated in advance so no post-hoc reinterpretation is possible.

## 7. Returned quantities (owner's C1 return list) **[AMENDED — completed]**

losses (per-checkpoint curves), overall accuracy, per-family accuracy, relation-path
gradients (per structure parameter at steps 50/250/1000), relation contribution norms
(structure-term magnitude **and** its ratio to the base attention score, per arm, at
every checkpoint — for T4 this sums **both** its hop-1 and hop-2 structure terms),
R ablations (null / permuted / R-RANDOM tables), parameter counts (total **and**
structure-channel), runtime, GPU memory, and cost.

Per owner law 2, every verdict additionally carries: overall accuracy, accuracy by
family, margin vs T0 by family, margin after removing each family, **signed** raw extra
correct answers by family, and the **signed** fraction of the net gain by family. The
signs are preserved — an earlier version clamped negative per-family gains to 0.0, which
made a family that *lost* answers indistinguishable from one that did not move.

**Uncertainty is reported alongside every decision quantity** (the thresholds sit at
roughly one standard error, so reporting a bare margin would be misleading): per-seed
margins, the count of seeds with a positive margin, and an approximate standard error on
the overall margin.

**Cost:** the harness records `estimated_cost_usd` by the `compute_wall_estimate` method
and labels it explicitly as a **lower bound**; the authoritative spend proxy remains the
watchdog's `instance_runtime_estimate`, filed in the run receipt. The two methods are
never mixed.

## 8. Money safety

One self-terminating `g4dn.xlarge` (Tesla T4) in us-west-2, `$0.526/hr`, hard cap
**$0.80** (≈ 91 minutes total including boot, dependency install, model download, and
activation extraction). `InstanceInitiatedShutdownBehavior=terminate` + EXIT-trap
shutdown + in-instance hard timer + client-side watchdog force-terminate. No
autoscaling; one instance; no unused C1 budget transfers to C2. A standalone receipt is
filed in the same commit as the results (instance id, runtime, self-termination
evidence, cost + method `instance_runtime_estimate`), per the standing receipt law.

## 9. Prohibitions

No "CAS-specific" claim. No C2 auto-launch. No protected read. No C2_STRUCTURE_EVAL
read. No status rewrite. No lowering of any threshold after seeing numbers. No second
tournament to "fix" a disappointing result — a `NO_TRANSFORM_CONSUMES_STRUCTURE`
outcome is a finding, recorded and kept.
