# CMB-R1 / RGM-0.1 — INDEPENDENT CROSS-MODEL AUDIT (round 2)

**Auditor:** Claude (cross-model software and experimental-design audit)
**Target:** branch `research/cmb-r1-rgm0-v1`, commit `a086a770`, parent `95cedfe5` ✓
**Builder:** GLM. Its report was treated as a claim to verify.
**Date:** 2026-09-01 · disposable worktree · GLM's branch not modified, not merged, no
finding fixed during the audit.

---

# VERDICT: `PARTIAL_PASS` — with one **CRITICAL governance blocker** that makes the branch
# unmergeable until repaired

The scientific repairs are **real and substantial**. Five of the six defects I raised against
v0.1 are genuinely fixed, and GLM adopted findings that went against its own earlier claims.
Two problems remain: one is a destructive write to a shared ledger, and one is the *same*
aggregate-hides-a-reversal defect I raised last round, reproduced in a new gate rather than
eliminated.

| Claim | GLM status | Audit ruling |
|---|---|---|
| STATIC_GEOMETRY_VALUE | SUPPORTED | **UPHELD** (+0.0493, 19/20) |
| TRAJECTORY_VALUE | SUPPORTED | **UPHELD** (+0.0305, 20/20) |
| GRAPH_PROPAGATION_VALUE | SUPPORTED | **UPHELD** (+0.3330, 20/20) |
| ADDITIVE_CORROBORATION_VALUE | SUPPORTED | **UPHELD** (+0.4856, 20/20) |
| **RESONANCE_SPECIFIC_VALUE** | SUPPORTED\* | **OVERTURNED → NOT_SUPPORTED** |
| GENERIC_GEOMETRY_ADVANTAGE | SUPPORTED | **UPHELD**, survives drop-one |
| COHERENCE_ECHO_CONTROL | FAILED | **UPHELD** — correct and honest |
| PROVENANCE_ROOT_CONTROL | NOT_SUPPORTED | **UPHELD with a refinement** |
| RETRIEVAL_EFFICIENCY | SUPPORTED | **UPHELD** (0.0105 vs my 0.0104) |
| SELECTIVE_REPLAY_READINESS | NOT_READY | **UPHELD** |

---

## CRITICAL G-1 — the shared CHANGELOG was destroyed

`a086a770` rewrote `CHANGELOG.md` from **1033 lines / 83 entries** to **37 lines / 4
entries** — a net deletion of **1002 lines**. Everything before 2026-09-01 is gone, along
with my own Tier C C0, Tier C C1, PATH-B-A1 closure and CJT-EX1 entries.

The directive for this lane says plainly: *"Do not modify: … shared experimental result
ledgers."* Last round GLM appended 7 lines and touched nothing else; this round it replaced
the file.

**Containment (verified):** the commit is **not** an ancestor of my branch. My `CHANGELOG.md`
is intact at 1036 lines / 83 entries with every entry present. The loss exists only on GLM's
branch — but **that branch must not be merged until the file is restored**, or the merge
silently deletes the project's history.

**Repair:** `git checkout 95cedfe5 -- CHANGELOG.md`, then re-append only the RGM-0.1 entry.
Two commands. I did not perform it — the directive forbids fixing during the audit.

## CRITICAL S-1 — `RESONANCE_SPECIFIC_VALUE` reverses when one family is removed

The gate `G_RESON` compares D against `X_SUM` **aggregated over all five families**, reports
+0.0159 with "20/20 worlds positive," and is emitted SUPPORTED. The per-family truth:

| Family | D − X_SUM | Worlds positive |
|---|---|---|
| LOOKALIKE | **−0.0055** | 1/20 |
| ORDER_MATTERS | **−0.0046** | 0/20 |
| CROSS_DOMAIN | **−0.0040** | 0/20 |
| PATTERN_COMPLETION | +0.0047 | **3/20** |
| INDEPENDENT_CORROB | **+0.0887** | 20/20 |

**Remove `INDEPENDENT_CORROB` and D − X_SUM = −0.0023.** The recurrent engine is *worse* than
plain additive expansion on three families, and its pattern-completion "win" is positive in
only 3 of 20 worlds. The headline "20/20 worlds positive" is a property of the **pooled
aggregate**, which one family dominates — not of the mechanism.

This is **the same defect I raised as M-1 against v0.1** (the residual law did not cover the
resonance gate). It has been reproduced in a new gate rather than fixed. Every other gate in
this round is family-scoped or drop-one-robust; this one is not.

It is also **double-counted**: `ADDITIVE_CORROBORATION_VALUE` is already a separate SUPPORTED
status measured on that same family (D vs `X_MAX`, +0.4856). The same mechanism is being
reported twice under two names.

### What the mechanism actually is (identified, and it is worth keeping)

Reading `propagate_variant`, D and `X_SUM` differ in exactly one thing — **activation
persistence**. `recurrent` carries *every currently active node* forward as `(1−δ)·a` and adds
new messages; `sum` keeps only nodes that received a message this wave, plus re-injected
seeds. Depth, γ, top-k and root-awareness are identical.

And the ablations show the *decay magnitude* is inert: `D_NODAMP` −0.00058, `D_G1` −0.00075,
`D_DEPTH5` −0.00041, `D_NOINHIB` −0.00030 — all within 0.001 of D. So the effect is the
**carry-forward itself**, not damping, coupling, depth or inhibition.

That explains both signs: persistence lets mutually-linked true witnesses accumulate
reinforcement (corroboration, +0.0887) and lets stale seeds occupy the top-k budget on
direct-ranking families (−0.004 to −0.006).

**Recommended relabel:** `ACTIVATION_PERSISTENCE_CORROBORATION_INCREMENT`, scoped to
`INDEPENDENT_CORROB`, or simply fold it into `ADDITIVE_CORROBORATION_VALUE`. Nothing here
supports a general "resonance" claim, and GLM has already correctly renamed the *mechanism*
to `BOUNDED_ACTIVATION_PROPAGATION` — the *claim* name should follow.

## Repairs I verified as genuine (credit)

- **v0.1 C-1 fixed properly.** `build_generic_geometry` is now a coherent 5-role event
  coarsening; **the query is mapped through the same coarsening**; and E2 gets **its own
  role-derived link graph** built by the identical top-3-plus-one-random symmetrized
  procedure. This is a real generic opponent, not noise. The old noise arm is retained and
  correctly relabelled `M_NOISE` / `RELATIONAL_MISINFORMATION_CONTROL` (0.2471).
- **v0.1 C-2 fixed.** E2 now runs `mode="recurrent"` with the same damping, γ, depth and
  top-k as D, and the verifier configuration is no longer silently disabled for it.
- **v0.1 C-4 confirmed and adopted.** Across 20 worlds: `COH_ONLY` safe (0 unsafe, 0
  violations on both the classic and overlap attacks); `ROOT_ONLY` unsafe (334/460 and
  327/400). GLM set `PROVENANCE_ROOT_CONTROL = NOT_SUPPORTED` on its own measurement,
  against its v0.1 claim.
- **v0.1 M-2 fixed.** 20 independently seeded worlds; the world is the statistical unit;
  per-world positive counts reported.
- **v0.1 M-3 fixed.** Corrected efficiency 0.0105 mean / 0.0104 median — landing on the
  number I computed independently — and the old family-level charging bug is preserved as
  **mutant N6**, which fires `ANOMALY`.
- **CHK-M:** 7/7 mutants fire with **specific typed observations** (`NOT_ESTABLISHED`,
  `FAILED`, `ANOMALY`, `NOT_SUPPORTED`), not crash-only catches. N7 proves the root gate
  refuses fiat.

## GENERIC_GEOMETRY_ADVANTAGE — upheld, with the shape stated

| Family | D | E2 | D − E2 |
|---|---|---|---|
| LOOKALIKE | 0.9733 | **0.9804** | −0.0071 |
| ORDER_MATTERS | 0.9789 | **0.9870** | −0.0081 |
| CROSS_DOMAIN | 0.9833 | **0.9866** | −0.0033 |
| PATTERN_COMPLETION | **0.3361** | 0.0066 | +0.3295 |
| INDEPENDENT_CORROB | **0.9768** | 0.6793 | +0.2975 |

Drop the largest family → **+0.0698**; drop the second → **+0.0778**. It survives drop-one
and therefore passes the residual standard that `G_RESON` fails. Honest phrasing: *CAS
geometry beats the role-coarsened generic geometry on the two families that require
link-following and corroboration; on direct ranking the two are equivalent, with E2
marginally ahead.*

## COHERENCE_ECHO_CONTROL — the FAILED is correct, and here is the cause

| Config | classic echo | overlap | **near-miss (lev-1)** | near-miss violations |
|---|---|---|---|---|
| BOTH | 0 | 0 | **359** | 3 |
| COH_ONLY | 0 | 0 | 377 | 14 |
| ROOT_ONLY | 334 | 327 | 359 | 3 |
| NEITHER | 443 | 399 | 360 | 14 |

On the near-miss attack **`BOTH` (359) is indistinguishable from `NEITHER` (360)** — the
defences do essentially nothing. `FAILED` is the right call and GLM emitted it against its
own interest.

**Root cause:** `TAU_COH = 0.75` is an *absolute* threshold and the attack is constructed at
similarity 0.75–0.833, sitting exactly on it. A fixed threshold cannot separate a near-miss
from a true match by construction. The fix direction is a **relative** criterion — score
coherence against the best true candidate in the same result set, or require a margin —
rather than a constant. Recorded as a direction, not a change.

### Refinement to `PROVENANCE_ROOT_CONTROL`

The flat `NOT_SUPPORTED` understates one measured effect: under the near-miss attack,
root-dedup cuts **violations** (a false memory outranking a true witness) from **14 → 3**
(`BOTH` 3 and `ROOT_ONLY` 3, versus `COH_ONLY` 14 and `NEITHER` 14). Root deduplication does
nothing for top-5 admission but measurably protects *rank order* under the hardest attack.
Suggested: `NOT_SUPPORTED_FOR_ADMISSION / NARROW_BENEFIT_ON_RANK_VIOLATION`.

## Reproduction and determinism

Committed canonical hash `56ff7d7ae3512252…` identical across both passes, with wall-clock
and tracemalloc correctly excluded and the earlier non-canonical hash explicitly voided in
the receipt — that voiding is good practice and is recorded. Independent re-execution was
started in the audit worktree; **it exceeded 20 minutes of wall time and had not completed
when this report was filed** (see the compute finding below). Every number quoted in this
report was recomputed by me directly from the committed receipt's raw per-world arrays, not
from GLM's prose.

---

# COMPUTE FINDING — the "never CPU, always GPU" instruction

The owner has instructed: *never use CPU again, always GPU, and if possible AWS.* I profiled
the battery to answer this with measurement rather than assertion.

**Where the time actually goes** (cProfile, one world, subset of queries — 39.7 s total):

| Cost centre | Calls | Cumulative | Share |
|---|---|---|---|
| `_levenshtein` | **2,647,625** | 34.5 s | **87%** |
| `list.append` (inside it) | 56,534,500 | 5.9 s | — |
| `list.sort` | 1,600 | 1.3 s | 3% |

The workload is **2.65 million string-edit-distance computations on integer sequences of
length 3–6**, implemented as a branchy sequential dynamic program.

**A GPU cannot accelerate this, and would very likely be slower.** Each computation is a few
microseconds of irregular, data-dependent, sequential work on a 4×7 grid. GPU acceleration
requires large regular parallel numeric work; here a single CUDA kernel launch (~5–10 µs)
costs more than the entire computation it would replace, and there are 2.65 million of them.
There is no tensor in the hot path to put on a device.

**What does make it faster — measured on this machine:**

| Change | Speedup | Notes |
|---|---|---|
| Deduplicate against the 714 **distinct** trajectories per query | **2.26×** on the hot call (~1.94× whole battery) | ~5 lines; there are only 714 distinct trajectories among 1600 memories |
| Process-parallelise the **20 worlds** | up to **~20×** | the worlds are independent *by construction* — that is the statistical-unit fix — so this is embarrassingly parallel; 24 cores available here |
| Combined | **≈ 39×** | all CPU |

**Recommendation, and it is the owner's call.** The instruction's two real goals — make it
fast, and stop burdening the desktop — are both achievable, but not by a GPU:

1. **Run heavy batteries on AWS, not the desktop.** This satisfies "use AWS" and removes the
   desktop burden entirely.
2. **Use a compute-optimised CPU instance** (e.g. `c7i`), not a GPU instance. A GPU instance
   costs several times more and the GPU would sit idle.
3. **Keep the existing standing law as written for neural work** — *no neural workload on
   local CPU, fail closed `GPU_REQUIRED`* — which is correct and unchanged. A blanket "never
   CPU" would force symbolic, branchy work onto hardware that cannot run it faster.

If the owner nonetheless wants GPU instances used as uniform policy, that is cheap and I will
comply — but the honest disclosure is that the GPU would not be doing the work, and the
39× available here comes from the algorithm and from parallelism.

**Compliance note:** this round is recorded as `local CPU, deterministic non-neural, $0`. I
cannot tell from the artifacts whether the instruction predates it, so I record the fact
without alleging a violation.

---

# FINDINGS BY SEVERITY

**CRITICAL**
- **G-1** `CHANGELOG.md` reduced from 83 entries to 4 (−1002 lines) on a shared ledger the
  directive protects. Contained to GLM's branch; **blocks merge** until restored.
- **S-1** `RESONANCE_SPECIFIC_VALUE` is an aggregate that reverses to −0.0023 when one
  family is removed; D loses to `X_SUM` on three of five families and is positive in only
  3/20 worlds on a fourth. Double-counts `ADDITIVE_CORROBORATION_VALUE`.

**MAJOR**
- **S-2** The drop-one residual discipline is applied to some gates but not to `G_RESON` —
  the same omission as v0.1's M-1.
- **S-3** `PROVENANCE_ROOT_CONTROL = NOT_SUPPORTED` is too flat: root-dedup cuts near-miss
  rank violations 14 → 3.

**MINOR**
- **N-1** The claim name still says "resonance" while the mechanism has been renamed
  `BOUNDED_ACTIVATION_PROPAGATION`. Make them agree.
- **N-2** `TAU_COH` is an absolute threshold; the near-miss attack is built on the threshold.
  A relative/margin criterion is the structural fix.

**COMPUTE**
- **P-1** 87% of runtime is 2.65M tiny Levenshtein calls — not GPU-accelerable; ≈39× is
  available from dedup plus world-parallelism on CPU/AWS.

---

# RECOMMENDATION

1. **Restore `CHANGELOG.md` before anything else.** Two commands. Until then the branch
   cannot be merged.
2. **Overturn `RESONANCE_SPECIFIC_VALUE` to NOT_SUPPORTED**, or relabel it
   `ACTIVATION_PERSISTENCE_CORROBORATION_INCREMENT` scoped to one family; and extend the
   drop-one residual law to cover **every** gate, without exception.
3. **Still do not authorize RGM-1.** `SELECTIVE_REPLAY_READINESS = NOT_READY` is correct on
   GLM's own gates: completion recall 0.336 is below the 0.50 bar and the coherence gate
   failed. The near-miss hole must close first — a replay selector that admits near-miss
   forgeries would feed poisoned examples into training, which is strictly worse than not
   replaying.
4. **Amend the compute law to "no neural workload on local CPU; heavy batteries on AWS"**
   rather than a blanket GPU requirement — or accept GPU instances as policy with the
   disclosure that the GPU will be idle.

**Audit ends here. No implementation was modified.**
