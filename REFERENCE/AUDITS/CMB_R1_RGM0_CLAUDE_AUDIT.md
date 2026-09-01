# CMB-R1 / RGM-0 — INDEPENDENT CROSS-MODEL AUDIT

**Auditor:** Claude (cross-model software and experimental-design audit — *not* external
scientific replication)
**Target:** branch `research/cmb-r1-rgm0-v1`, commit `95cedfe5`
**Builder:** GLM. GLM's report was treated as a claim to verify, never as evidence.
**Date:** 2026-09-01 · **Cost:** $0, local CPU · no GPU, no model load, no protected data
**Method:** disposable detached worktree at `95cedfe5`. GLM's branch was not modified, not
merged, not cherry-picked. No finding was fixed during the audit.

---

# VERDICT: `PARTIAL_PASS`

The artifact is **honestly built, fully reproducible, and free of answer leakage**. Three of
its component claims survive audit. But the headline status name is not supported by the
evidence as constructed: the word doing the most work — *resonant* — is the one claim the
benchmark cannot establish, and two of the seven kill laws do not measure what they are
reported as measuring.

| Claim | Verdict |
|---|---|
| `STATIC_CAS_GEOMETRY_VALUE` | **SUPPORTED** (within a constructed benchmark) |
| `TRAJECTORY_VALUE` | **SUPPORTED** (within a constructed benchmark) |
| `GRAPH_PROPAGATION_VALUE` | **SUPPORTED** — and it is large |
| `RESONANCE_SPECIFIC_VALUE` | **NOT ESTABLISHED** — refuted on 4 of 5 families |
| `MATCHED_GENERIC_GEOMETRY_ADVANTAGE` | **NOT ESTABLISHED** — the control is not generic geometry |
| `PROVENANCE_ECHO_CONTROL` | **REFUTED AS ATTRIBUTED** — the defence is coherence, not provenance |
| `RETRIEVAL_EFFICIENCY` | **MIS-MEASURED** — 34.6× counting error, *against* GLM's own claim |
| `NEURAL_FOLLOWUP_READINESS` | **NOT READY** |
| `SELECTIVE_REPLAY_BRIDGE_READINESS` | **COHERENT IN PRINCIPLE, NOT READY** |

---

## 1. Isolation — PASS (one minor exception)

- Commit `95cedfe5` exists; parent is **exactly** `9014e3d5` as claimed.
- All 11 changed files live in `cas_only_reasoner/CMB_R1_v0.1/` **except `CHANGELOG.md`**
  (+7 lines, purely additive, never merged). The directive restricted writes to the new
  project directory and named shared ledgers as off-limits. **MINOR finding I-1.**
- No EX1 file, dataset, protected artifact, or threshold was touched. The EX1 lane is
  intact.

## 2. Reproduction — PASS

I re-ran the committed pipeline in the isolated worktree:

- my status `RGM0_RESONANT_MEMORY_SIGNAL` = committed status;
- output **byte-identical** to `rgm0_raw.json` excluding the determinism block;
- triple-run hash `ffdeb748751110339d0f…` **matches** the committed hash exactly.

Every headline number recomputes from the raw artifact: KL1 +0.057820, KL2 +0.034001,
KL3 +0.060016, KL4 +0.578101, KL5 +0.798844, novelty 1.0. **GLM's reproducibility and
arithmetic claims are true.**

## 3. Benchmark leakage — PASS (no leak found)

I searched for every channel the directive names. **`answer_field` and
`verification_status` are written into every memory record but are NEVER READ by any
retrieval arm** (`grep` shows exactly one occurrence each — the assignment). `topic` is
read only inside the *generator*, never inside a scoring arm. Ranking uses only the
semantic vector, the CAS profile/trajectory, the link graph and provenance roots.

I found **no** id-ordering, degree, reachability, or generation-order leak. This is
better hygiene than the benchmark's own risk profile required.

One structural note, not a leak: in `LOOKALIKE` the distractor's stored semantic vector is
*overwritten* with the target's vector plus 0.01 noise (`cmb_r1_core.py:198-200`), so
semantic-only retrieval is **constructed to be unable** to separate them. That is the
registered spec contract and is disclosed — but it means KL1 measures "geometry helps on a
task built so semantics cannot work," not "geometry helps in general."

## 4. Control validity — **CRITICAL C-1: arm E is not a generic geometry**

`assign_generic_geometry` (`cmb_r1_core.py:129-143`) draws **each operation independently**
from a per-position marginal pool. The resulting `generic_trajectory` is *random noise with
matched marginals*, uncorrelated with the memory it is attached to.

Worse, the **query key is never converted to the generic space**: `arm_d(geo_mode="generic")`
compares the query's *real CAS* trajectory against the memory's *random* trajectory
(`cmb_r1_core.py:454-456, 477`). Arm E therefore scores real signal against noise.

**Consequence: `D − E = +0.5781` means "correct geometry beats random noise." It says
nothing about whether CAS geometry beats a serious generic memory geometry.** Per the
directive, arm E is reclassified:

> **E = `RELATIONAL_MISINFORMATION_CONTROL`** — and `D − E` may not be used to claim CAS
> beats generic geometry. Arm F (permuted trajectories) is a second, cleaner misinformation
> control. The build contains **two misinformation controls and zero generic-geometry
> controls.**

KL4 is additionally unfalsifiable in practice: it fires only if `D − E ≤ 0.005`, and with E
scoring noise that can essentially never happen.

### **CRITICAL C-2: arm E also runs with the verifier partly disabled**

`coherence_off = (geo_mode == "generic") or not use_coherence` (`cmb_r1_core.py:490`), and
E is invoked as `run_d("E", memories, "generic", True, False)` (`run_rgm0.py:83`). **E
differs from D in two ways at once** — geometry *and* the coherence quarantine. Any E-vs-D
gap is unattributable. This also invalidates the "E unsafe" line in GLM's commit message
and CHANGELOG.

## 5. Resonance isolation — **CRITICAL C-3: resonance-specific value is not established**

`resonate()` implements `a' = BoundedTopK[(1−δ)a + γWa]` — ordinary damped graph
propagation with top-k truncation. There is no oscillation, phase, or frequency. "Resonance"
is a naming choice, not a mechanism.

The directive required an X arm. **I built one** (read-only, in my scratchpad, not in GLM's
tree): ordinary bounded best-first expansion — same seeds, same graph, same depth, same
top-k budget, same root-dedup, same rescoring, same verifier; only `resonate()` is swapped
for plain frontier expansion with distance decay, with no damping and no coupling.

| Family | D (resonance) | X (plain expansion) | D − X |
|---|---|---|---|
| LOOKALIKE | 0.9613 | **1.0000** | −0.0387 |
| ORDER_MATTERS | 0.9412 | **1.0000** | −0.0588 |
| CROSS_DOMAIN | 0.9600 | **1.0000** | −0.0400 |
| **PATTERN_COMPLETION** | 0.2059 | **0.2059** | **+0.0000** |
| INDEPENDENT_CORROB | **0.9579** | 0.4868 | +0.4711 |
| mean | 0.8053 | 0.7385 | +0.0667 |

**Ordinary graph expansion beats resonance on three of five families and ties it exactly on
pattern completion — the family GLM's findings call "the clearest resonance win."** That win
is a *graph-propagation* win (C scores 0.0020; both D and X score 0.2059), not a resonance
win.

D's only advantage over X is `INDEPENDENT_CORROB` (+0.4711), and the mechanism is
identifiable: `resonate()` **accumulates** activation from multiple neighbours
(`cand[nb] += γ·w·amp`) while X takes a **max**. Accumulation is corroboration-counting, and
`INDEPENDENT_CORROB` is the one family built to reward exactly that. That is a real and
interesting property — but it is *accumulative propagation*, not resonance, and it is worth
naming honestly.

Per the directive's registered rule:

```
GRAPH_PROPAGATION_VALUE_SUPPORTED
RESONANCE_SPECIFIC_VALUE_NOT_ESTABLISHED
```

**Damping and coupling are not shown to be load-bearing either**: X has neither and wins
three families. An ablation of δ and γ should precede any new pulse parameter.

### **MAJOR M-1: the resonance gain is exempt from GLM's own residual law**

KL7 residual-tests KL1, KL2 and KL5 — **but not KL3** (`run_rgm0.py:160-167`). Recomputing
per family:

| Family | D − C |
|---|---|
| CROSS_DOMAIN | −0.0400 |
| LOOKALIKE | −0.0387 |
| ORDER_MATTERS | −0.0588 |
| PATTERN_COMPLETION | +0.2039 |
| INDEPENDENT_CORROB | +0.4711 |

**D is worse than C on three of five families.** Drop the two families that carry the gain
and D−C over the remainder is **−0.0458**. The residual law GLM describes as
"institutionalised" does not cover the one law it most needed to cover.

## 6. Statistics — MAJOR M-2: the independent unit is one world

`paired_permutation` runs a sign-flip permutation over **per-query** deltas. All queries are
generated from **one corpus, one seed** (`SEED = 20260901`), share memories, topics and the
link graph. Queries are therefore correlated and the reported p-values are optimistic. Triple
deterministic reruns establish *byte reproducibility*, not independent replication — GLM's
receipt says this correctly, but the p-values are still computed as if queries were
independent units.

**Required before any p-value is quoted again:** regenerate over ≥ 20 independently seeded
memory worlds and group uncertainty by world.

## 7. Echo and provenance — **CRITICAL C-4: the defence is coherence, not provenance**

I isolated the two verifier controls that `arm_d` applies together:

| Verifier configuration | False memory in top-5 | |
|---|---|---|
| root-dedup **ON**, coherence **ON** | 0/23 | safe |
| root-dedup **ON**, coherence **OFF** | **17/23** | **UNSAFE** |
| root-dedup **OFF**, coherence **ON** | 0/23 | safe |
| both OFF | 17/23 | UNSAFE |

**Root deduplication alone fails on 17 of 23 echo queries. The trajectory-coherence
quarantine alone is fully sufficient.** The echo defence in this build is a
similarity threshold (`traj_sim < TAU_COH = 0.75` quarantines the rotated-trajectory
forgeries), not a provenance mechanism.

Arm G disables **both** controls at once (`run_rgm0.py:84`), so KL6 can only show "some
control is required" — it cannot attribute the effect. GLM's conclusion that *provenance
controls* are load-bearing is **not supported by its own run**, and the harder attacks I
added (forged multi-roots, true memories sharing one root, missing roots — all safe, 0/15)
are safe *because provenance is irrelevant here*, not because provenance is robust.

### **WORDING W-1: a prohibited claim word was used**

GLM's commit message and CHANGELOG state *"provenance controls load-bearing and
**CAS-specific**."* `CAS-specific` is a **prohibited term** under the standing claim law,
reserved for incremental value over serious matched controls under protected evaluation. It
is unsupported twice over: the controls are not provenance-driven, and no serious generic
provenance control was run. Per the directive, the correct label is:

> **provenance-aware echo controls** — and on this evidence, more accurately
> **trajectory-coherence echo controls**.

## 8. Efficiency — MAJOR M-3: a 34.6× counting error, *against* GLM's own claim

`eff["C"] += len(memories)` sits **outside** the per-query loop (`run_rgm0.py:50`), so arm C
is charged its expensive-scorer cost **once per family** instead of once per query.

- charged: 5 × 2366 = **11,830**
- actual: 173 ranked queries × 2366 = **409,318** (34.6× undercount)
- reported ratio: 4255 / 11830 = **0.3597** → efficiency leg reported **FAILED** vs the 0.25 cap
- true ratio: 4255 / 409,318 = **0.0104** → the efficiency leg **passes by a wide margin**

GLM disclosed an efficiency failure that its own bug manufactured. The status is unaffected
(KL3 passed on the quality leg), but the receipt's efficiency number is wrong and should not
be quoted.

## 9. CHK-M validity — PASS with one disclosed weakness

All six mutants run, preserve schema, and fire their registered typed reason; GLM preserved
both the first FAILED run (`STATIC_CAS_GEOMETRY_REDUNDANT`) and the M4 gap-and-fix history
rather than hiding them. That is good practice and I credit it.

**MINOR N-1:** M4 is a *law-level* mutant — it overwrites arm E's results with arm D's
(`run_rgm0.py:127-130`) rather than making the generic geometry genuinely equal the CAS
geometry. GLM discloses this and justifies it by arm E's verifier asymmetry. But that
asymmetry is finding C-2 — a confound, not a feature. Once E is repaired to share D's
verifier, M4 should be re-derived at the geometry level.

## 10. Bridge to CMB-RP1 (selective replay) — coherent, not ready

**Technically coherent.** The pipeline (cheap seed → bounded expansion → expensive rescore →
verifier) is a reasonable selector for "which old examples should I replay now," and the
EX1 result gives it a real target: catastrophic forgetting was total (retained accuracy fell
from ~0.37 to 0.005–0.041, below chance) and **organization-independent** — a single shared
expert and meaningless routing tied for the least forgetting.

**Not ready, and the gap is not small.** What must exist first:

1. **The link graph must come from somewhere real.** RGM-0's advantage is graph propagation
   over a graph the generator *built* by linking each memory to its three
   nearest-trajectory neighbours. On real training data no such graph exists; it must be
   constructed, and its construction is then the actual hypothesis under test.
2. **Real embeddings.** RGM-0 uses 32-d synthetic topic vectors with 0.15 noise.
3. **Honest naming.** On present evidence the selector to test is *bounded graph expansion
   with a coherence verifier*, not "resonance."
4. **The right control set.** CMB-RP1 must include random replay, semantic-only replay, and
   a **matched generic-geometry** replay — the control that RGM-0 does not currently have.

**Blunt caveat:** replay is already known to work here (the owner cites 0.944 vs 0.000).
CMB-RP1 can only claim value if resonant selection beats *random and semantic* selection at
equal replay budget. Nothing in RGM-0 predicts that it will.

## 11. Pulse-knob ruling — add none

| Knob | Operational definition | Duplicates | Verdict |
|---|---|---|---|
| Frequency | refresh/reconsideration rate | iteration count / `DEPTH` | **Reject now** — no periodic benchmark exists |
| Phase | relative ordering of active chains | the stored ordered trajectory | **Reject now** — trajectories already carry order |
| Pulse width | activation persistence | low `DAMPING` | **Reject now** — no delayed-recall task exists |
| Q | persistence × selectivity | derivable from δ, γ, inhibition | **Diagnostic only**, never a control |

The case against adding knobs is stronger than "premature": **the knobs already present are
not yet shown to do anything.** X — with *no* damping and *no* coupling — beats D on three of
five families. Before any new pulse property, ablate δ and γ and show they earn their place.

---

# FINDINGS BY SEVERITY

**CRITICAL**
- **C-1** Arm E is random noise, not a generic geometry, and the query key is never mapped
  into the generic space. `D − E` cannot support the generic-sufficiency claim.
- **C-2** Arm E additionally runs with the coherence verifier disabled — a second
  simultaneous difference that makes any E-vs-D gap unattributable.
- **C-3** Resonance-specific value not established: ordinary best-first expansion beats D on
  three of five families and ties it exactly on pattern completion.
- **C-4** The echo defence is the trajectory-coherence quarantine, not provenance:
  root-dedup alone fails 17/23; coherence alone is sufficient.

**MAJOR**
- **M-1** KL7's residual law does not cover KL3; D is worse than C on three of five families
  and −0.0458 once the two carrying families are removed.
- **M-2** All queries come from one corpus and one seed; per-query permutation treats
  correlated queries as independent units.
- **M-3** Arm C's expensive-scorer cost is undercounted 34.6× (charged per family, not per
  query); the reported efficiency failure at 0.36 is an artifact — the true ratio is 0.0104.

**MINOR**
- **I-1** `CHANGELOG.md` written outside the permitted project directory.
- **N-1** M4 is a law-level mutant standing in for a geometry-level one.
- **N-2** `LOOKALIKE` is constructed so semantic-only retrieval *cannot* separate the pair;
  KL1 is therefore a demonstration on a task built for it, and should be described that way.

**WORDING / CLAIM BOUNDARY**
- **W-1** `CAS-specific` — a prohibited term — appears in the commit message and CHANGELOG,
  and is unsupported. Replace with *provenance-aware echo controls*, or more accurately
  *trajectory-coherence echo controls*.
- **W-2** The status name `RGM0_RESONANT_MEMORY_SIGNAL` asserts the one property the
  benchmark cannot establish. `RGM0_GRAPH_PROPAGATION_SIGNAL` would match the evidence.

---

# WHAT I CREDIT

This is a careful build, and several things deserve saying plainly. The first run **failed**
and GLM preserved the failure as an artifact rather than quietly regenerating. The M4 gate
gap was recorded as a gap before it was fixed. The efficiency leg was reported as *failing*
— GLM published a number against its own interest, and it turned out to be a bug that
understated the system. Reproduction is exact to the hash. There is no answer leakage, and
the search for it was not trivial to pass.

The defects here are of design and attribution, not of honesty.

---

# RECOMMENDATION

1. **Do not authorize RGM-1 (neural) on this evidence.** Three of the four load-bearing
   claims are unestablished or misattributed.
2. **Cheap repairs, all $0 CPU, in this order:** repair arm E into a genuine generic
   geometry (map the query into the generic space; give E the same verifier as D); add arm X
   permanently; split arm G into root-dedup-only and coherence-only; extend KL7 to cover
   KL3; fix the efficiency counter; regenerate across ≥20 independent worlds.
3. **Then re-emit the status.** On current evidence the honest headline is
   *graph propagation plus a coherence verifier helps retrieval on a constructed benchmark*
   — which is a real result, and a smaller one than the name claims.
4. **The replay bridge is the most valuable thread here**, because EX1 produced a concrete
   forgetting problem for it to attack. But it needs a real link graph before it means
   anything.

**Audit ends here. No implementation was modified.**
