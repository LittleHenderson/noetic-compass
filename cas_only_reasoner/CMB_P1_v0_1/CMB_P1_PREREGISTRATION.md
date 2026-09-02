# CMB-P1 — Phase Separation Repair Bench · PREREGISTRATION v0.1

**Authorized by the owner, 2026-09-02** (`OWNER_RULINGS_2026_09_02.md`, R4).
**Lane:** narrow, separately versioned. **Phase is NOT retrofitted into CMB-R1.** The
production memory board stays scalar and accountable; the phase system remains a
**quarantined experimental subsystem**.
**Status:** frozen before any held-out world is read. Held-out worlds 6–25 are untouched at
the time of sealing.

---

## 1. The one question

CMB-P0 established a real and specific defect. The phase engine **beat every control at every
K on retrieval** and was refused because it **merges distinct chains**: merge fraction
`0.657 / 0.617 / 0.590` of all possible chain pairs at K=2/3/4, versus `0.000` for an oracle,
in 20/20 worlds. It retrieves better while losing track of which chain it retrieved from.

> **Can cross-chain inhibition, controlled frequency separation, or a trajectory readout keep
> the chains apart WITHOUT losing phase's retrieval advantage?**

Nothing else. This bench does not revisit whether phase helps retrieval — CMB-P0 settled
that. It asks only whether the attribution failure is repairable.

## 2. Arms

`P0`–`P6` are carried over from CMB-P0 **unchanged in role**, so the two benches are directly
comparable. `P7`–`P9` are the repairs.

| Arm | What it is | Role |
|---|---|---|
| `P0_SCALAR` | one activation number per memory | baseline |
| `P1_ORACLE_CHAIN_TAG` | handed the true chain labels | **CEILING ONLY, never a method** |
| `P2_INFERRED_CHAIN_TAG` | inferred chain grouping | competent non-phase competitor |
| `P3_GENERIC_TWO_STATE` | two states, no angle | capacity control |
| `P4_PHASE_OSCILLATOR` | the CMB-P0 phase engine | **KNOWN-UNSAFE reference** |
| `P5_PHASE_SHUFFLED` | phase correspondence destroyed | killer control |
| `P6_SCALAR_TWO_CHANNEL` | non-angular second channel | ratified control (owner R1) |
| **`P7_SIGNED_COUPLING`** | attract within, **repel** across | **repair 1 (owner)** |
| **`P8_FREQUENCY_HETEROGENEITY`** | structurally-derived natural frequencies | **repair 2 (owner)** |
| **`P9_TRAJECTORY_COHERENCE`** | read the phase **history**, not the last frame | **repair 3 (Claude)** |

**Each repair stands or falls ALONE**, per the owner: *"Do not combine P7 and P8 initially.
Each must stand or fall on its own, so we know which mechanism caused any improvement."*

`P7` and `P8` change the **dynamics**. `P9` changes only the **readout** — its dynamics are
byte-identical to `P4`, so `P9 − P4` isolates the readout exactly.

### 2.1 One EXPLORATORY combination, not eligible for a primary verdict

`P8+P9` (structural frequency **and** trajectory readout) is measured because they act on
different axes and dev evidence suggests they compose well. It is labelled
**`EXPLORATORY_COMBINATION`**, is **excluded from every registered verdict**, and cannot be
promoted without a separate owner ruling. It is reported so the combination is not silently
lost, not so it can win.

### 2.2 What no repair may use

**No gold chain membership, anywhere, in any primary mechanism** (owner criterion 8). `P1`
alone receives it. Every derived quantity below is computed from the link graph, the content
vectors, or the system's own phase history — all available equally to every arm.

## 3. The three repairs, and the dev evidence that each is buildable

All figures below are **DEV worlds 0–5 only**, on the local RTX 4070 smoke lane, **$0**, with
**no measurement recorded**. They exist to show each arm is worth building, not to report a
result. Dev P0 reference: **K=2 `0.4948`, K=3 `0.3333`, K=4 `0.2630`**.

### 3.1 `P7_SIGNED_COUPLING` — attract within a chain, repel across

```
S_ij = cosine of the two nodes' propagated reach vectors     (structural, label-free)
w_ij = tanh( beta * (S_ij - s0) )                            (positive = attract, negative = repel)
dtheta_i = (Kc/deg_i) * sum_j A_ij * a_j * w_ij * sin(theta_j - theta_i)
```

**Precondition measured and PASSED.** A label-free structural signal does separate same-chain
from cross-chain pairs (AUC over active seed-node pairs):

| signal | K=2 | K=3 | K=4 |
|---|---|---|---|
| **raw adjacency `A_ij`** | **0.4956** | **0.5214** | **0.5240** |
| common neighbours | 0.7109 | 0.7258 | 0.7331 |
| Jaccard | 0.7887 | 0.7984 | 0.8061 |
| **reach cosine (depth 2)** | **0.8540** | **0.8751** | **0.8744** |
| **content cosine** | **0.8670** | **0.8964** | **0.8643** |

The first row matters as much as the rest: **raw adjacency carries no signal at all**, which
confirms the world construction really does defeat naive link-following — cross-chain links
are deliberately strong. The usable signal is second-order, and it is there.

### 3.2 `P8_FREQUENCY_HETEROGENEITY` — different chains, different natural frequencies

```
v      = a low eigenvector of the normalised graph Laplacian   (smooth structural coordinate)
omega_i = OMEGA * v_i / max|v|                                 (frozen before held-out)
dtheta_i = omega_i + (Kc/deg_i) * sum_j A_ij * a_j * sin(theta_j - theta_i)
```

A spectral coordinate is the legal source the owner's constraint requires: it is **smooth**,
so nearby nodes get similar frequencies and a chain can still lock internally, while distinct
chains get different ones. It is not the gold label, and it is not the inferred cluster —
*"a frequency code that simply assigns a unique frequency using the true chain ID would be an
analog chain tag wearing a tiny tuxedo."* Measured separation AUC: **0.6965 / 0.6723 / 0.7327**
at K=2/3/4 — weaker than reach-cosine but real.

**KILLER CONTROL, run on dev before registering the arm.** The obvious alternative
explanation is that *any* frequency spread breaks pathological synchrony. Four matched-spread
sources, `OMEGA = 0.40`, trajectory readout:

| ω source | K=2 Δ vs P0 / merge frac | K=3 Δ vs P0 / merge frac |
|---|---|---|
| ZERO | +0.0365 / 0.0755 | +0.0990 / 0.0877 |
| **SPECTRAL** | **+0.1042 / 0.0312** | **+0.1250 / 0.0304** |
| SHUFFLED *(same values, permuted)* | +0.0234 / 0.0573 | +0.0911 / 0.0547 |
| RANDOM *(matched spread, per-node)* | +0.0104 / 0.0391 | +0.0859 / 0.0339 |

**Honest reading, registered in advance: TWO effects are superimposed.** Random ω already cuts
merging (0.630 → 0.333 under a snapshot readout), so *some* of the benefit is simply
"desynchronise the population". Spectral ω then beats both shuffled and random on accuracy at
both K, so *some* of it is genuinely structural. **The registered claim is therefore the
weaker, true one: frequency spread helps, and structurally-derived frequency helps more.**
`SHUFFLED` and `RANDOM` are carried as permanent controls so this decomposition is measured
every run, not assumed.

### 3.3 `P9_TRAJECTORY_COHERENCE` — read the history, not the last frame

```
coh_j   = (1/T) * sum_t cos( theta_j(t) - theta_cue(t) )
score_j = a_j * clamp_min(coh_j, 0)
```

**No free parameter.** A plain unweighted mean. Full rationale and dev evidence in
`docs/design/CMB_P1_TRAJECTORY_READOUT_PROPOSAL.md`. Summary: merge fraction
`0.630/0.672/0.607 → 0.076/0.088/0.068` (≈8×), accuracy preserved and *improved over the
endpoint* at K=3 and K=4. Every attempt to sharpen the weighting made it **worse**, which is
the opposite of a tuning artifact.

Two disclosed costs, neither buried:

1. **K=1 regression.** `0.7448` versus P0's `0.9219`. At K=1 every active node should share
   the cue's phase, so the early random-initialisation frames are pure noise.
2. **It is a READOUT repair, not a DYNAMICS repair.** Measured: the global order parameter
   still ends at `0.9596` (K=2) and `0.9551` (K=3). **The chains still synchronise.** This
   mechanism declines to depend on the collapsed frame; it does not prevent the collapse. It
   must never be described as "fixing synchronisation".

## 4. Fairness upgrades to the CONTROL arms — the conservative direction

Two changes strengthen arms that **compete** with the phase hypothesis. Strengthening a
competitor makes a phase win harder, never easier. This is deliberate, and the opposite
direction was not taken.

1. **`P2` now uses content similarity as well as the link graph.** §2 of the CMB-P0
   preregistration always said P2 infers from *"the link graph + content"*; the implementation
   used only the link graph. Content is in fact the **strongest** single signal (AUC up to
   0.8964), so P2 was being handicapped against its own specification. Fixed.
2. **No repair arm's parameters are swept for accuracy.** `OMEGA` is frozen by a **safety**
   rule — the smallest tested value whose merge fraction clears the threshold — not by
   whichever value maximises top-1. `KC_PHASE` is untouched. `P9` has no parameter at all.

## 5. Metrics

The **world** is the statistical unit. All arms are **paired** on identical worlds and
queries. Everything is computed **per K** — pooling K values was the defect that nearly
invalidated CMB-P0 and it is not repeated.

| Metric | Definition |
|---|---|
| `top1`, `recall_at_5` | the cued chain's correct continuation ranked 1 / in the top 5 |
| **`merge_fraction`** | `false_merged_chain_pairs / C(K,2)` — **the owner's normalised metric (R2)** |
| `cross_chain_contamination` | fraction of the returned top-k belonging to a non-target chain |
| `chain_assignment_accuracy` | reported, but **never** as a safety criterion — see below |
| `global_order_parameter` | does the arm actually stop synchronising, or only stop depending on it |
| `simultaneous_chain_capacity` | largest K with `top1 ≥ 0.50` |

> **`chain_assignment_accuracy` is DIAGNOSTIC ONLY and may not gate any status.** In CMB-P0 it
> read 0.876 / 0.772 / 0.686 — healthy-looking — *while the chains were merging catastrophically*,
> because it assigns each node to the nearest chain-mean phase and stays high after the means
> themselves collapse together. On its own it would have reported a clean phase victory. It is
> kept for interpretation and explicitly barred from the decision.

## 6. Reportable range (owner R3)

```
K = 1        SANITY. All arms must stay close; nothing to separate.
K = 2, 3     PRIMARY. Every registered decision is made here.
K = 4        DIAGNOSTIC ONLY. Its oracle scored 0.560 < 0.60 in CMB-P0, so the
             stratum is partly ill-posed and is excluded from headline decisions.
```

## 7. The eight advancement criteria (owner R4) — ALL must hold

A repaired phase system advances only if it:

1. preserves the retrieval advantage at **both** K=2 and K=3 (beats `P0` by `MARGIN`);
2. reduces false chain merging **below the frozen safety threshold**;
3. beats the matched generic two-state arm `P3`;
4. beats **or approaches** the competent inferred-tag method `P2`;
5. **loses its advantage when phase correspondence is shuffled**;
6. does not increase wrong-chain retrieval or false memory admission;
7. passes across independently seeded held-out worlds;
8. uses **no oracle chain membership** in the primary mechanism.

### Frozen thresholds

```
MARGIN                 = 0.02     top-1, as in CMB-P0
WIN_FRACTION           = 0.70     must hold in >=70% of worlds WITHIN EACH K
MERGE_FRACTION_MAX     = 0.15     absolute ceiling on merges / C(K,2)
MERGE_VS_P2_SLACK      = 0.05     AND must not exceed P2's merge fraction by more than this
CONTAM_MARGIN          = 0.05
SHUFFLE_MUST_FALL_BELOW_P0 = True   criterion 5, stated as a hard check
```

The merge threshold is **two conditions, both required**: an absolute ceiling, and a
comparison against a competent non-phase method. A phase system must be at least as
accountable as the cheap tag alternative. Setting only an absolute number would let me pick a
figure I already knew my arms would clear.

## 8. Registered verdicts (owner R4)

```
PHASE RETRIEVAL WIN, MERGING REMAINS   -> PHASE_MEMORY_UNSAFE
INHIBITION FIXES MERGING               -> PHASE_SEPARATION_BY_SIGNED_COUPLING
FREQUENCY SPREAD FIXES MERGING         -> PHASE_SEPARATION_BY_FREQUENCY_HETEROGENEITY
TAGS MATCH OR BEAT SAFE PHASE          -> EXPLICIT_CHAIN_TAGS_PREFERRED
NO REPAIR PRESERVES BOTH ACCURACY
  AND ATTRIBUTION                      -> PHASE_RETIRED_FOR_MULTICHAIN_MEMORY
```

Plus, as in CMB-P0, `STATUS_NOT_EMITTED` for precondition failures — **not a sixth outcome**,
but a refusal to run the law on an instrument that cannot answer. If more than one repair
satisfies all eight criteria, the status names the **best** one and the receipt records both;
if they are within `MARGIN` of each other the status is `STATUS_NOT_EMITTED` with reason
`MULTIPLE_REPAIRS_TIED`, escalated rather than resolved by me.

### 8.1 🔒 A gap in the registered verdicts, named rather than papered over

**The owner's five verdicts cover `P7` (signed coupling) and `P8` (frequency heterogeneity).
There is no registered verdict for `P9`** — the trajectory readout — because `P9` is my arm,
proposed after the ruling was written.

If `P9` turns out to be the best surviving repair, the program **will not invent a status word
for it.** It emits:

```
STATUS_NOT_EMITTED    reason: TRAJECTORY_READOUT_BEST_NO_REGISTERED_VERDICT
```

and escalates. Naming a new outcome for my own arm would be exactly the self-authorization the
governance rule forbids: *a standing authorization does not permit choosing a replacement
hypothesis or promoting a claim.* The owner may add a verdict for `P9`, strike the arm, or
rule that it reports as a diagnostic only. On the dev evidence this is a live possibility, not
a hypothetical — which is why it is registered **before** the run rather than discovered after.

### Precondition gates (checked first, and safety is checked before them)

```
GATE_HEADROOM   P0 top1 < 0.90 at every primary K
GATE_ORACLE     P1 top1 >= 0.60 at every primary K
GATE_P4_UNSAFE  P4 must REPRODUCE its CMB-P0 failure (merge fraction > MERGE_FRACTION_MAX).
                If the known-unsafe reference is no longer unsafe, the instrument has
                changed and no repair claim means anything.
```

`GATE_P4_UNSAFE` is new and is the sharpest of the three: it makes the bench prove it can
still see the defect it exists to repair.

## 9. Compute law

Unchanged from CMB-P0 and from the owner's standing law. One remote AWS GPU instance; all
substantive numerical operations on CUDA; fail closed on silent CPU fallback; local RTX 4070
is smoke/dev only and records no measurement. Hard cap **$0.80**, self-terminating with four
independent stops. CMB-P0 cost `$0.0241`; this bench is larger but of the same order.

## 10. Stop condition and audit

**Stop after the deterministic report.** No merge into CMB-R1 under any outcome. The next
step is an **independent audit by a THIRD party** — per owner R5, neither Claude (which built
CMB-P0 and CMB-P1) nor GLM (which built CMB-R1) may serve as the final auditor. **🔒 I cannot
satisfy this myself; any subagent I spawn is still Claude.**

## 11. Falsifiers

- `GATE_P4_UNSAFE` fails — the known defect no longer reproduces, so the instrument changed.
- Every repair fixes merging only by destroying the retrieval advantage → `PHASE_RETIRED_FOR_MULTICHAIN_MEMORY`.
- A repair's advantage **survives** phase shuffling → it was never reading chain structure.
- `P2`, with its content upgrade, matches or beats every safe phase arm → `EXPLICIT_CHAIN_TAGS_PREFERRED`.
- The `SHUFFLED`/`RANDOM` ω controls match `SPECTRAL` → P8 is desynchronisation noise, not
  structural coding, and must be reported as such.

---

**Frozen. No held-out world has been read.**


---

# AMENDMENT B1 — pre-launch design revisions (2026-09-02, before any held-out read)

A 9-agent design panel stress-tested the three mechanisms before implementation. **I verified
every claim it made rather than accepting it** — two of its headline claims did not reproduce
as stated, one reproduced decisively, and one led to a defect it had not itself found.

## B1.1 VERIFIED: `PHASE_SUBSTEPS = 10` is not converged → every arm is reported at TWO budgets

Confirmed by my own measurement (see CMB-P0 amendment A3.1): merge fraction runs
`0.6406 → 0.9844 → 1.0000` at 10/25/200 substeps, cross-chain separation reaching exactly
`0.0000`. **Every CMB-P1 arm is therefore run at both `10` and `200` substeps, and a repair
must satisfy its criteria at BOTH.** Otherwise an arm wins merely by being a slower transient
— and on dev, all four phase arms do exactly that.

## B1.2 NOT REPRODUCED as stated, but it led to a real defect: the content leak

The panel claimed a phase-free structural gate beats even the oracle. Measured with
reach-similarity, it does not (0.52 / 0.35 / 0.27 vs oracle 0.91 / 0.78 / 0.69). **But a
phase-free CONTENT gate scored 0.5833 / 0.5443 / 0.5938 — beating `P4` at every multi-chain
K** — which exposed that **the content vector leaked chain identity**. Full record in CMB-P0
amendment A3.2. Repaired here in `build_world_p1` and verified back to exact chance.

**Had I not chased the panel's claim, CMB-P1 would have shipped with `P2` reading a leaked
signal** — the content upgrade in §4 would have made the tag competitor look strong for
entirely the wrong reason.

## B1.3 Two phase-free baselines are now REGISTERED ARMS

```
B_STRUCT_GATE_REACH     score_j = a_j * clamp_min(sign(reach_sim[cue, j]   - 0.05), 0)
B_STRUCT_GATE_CONTENT   score_j = a_j * clamp_min(sign(content_sim[cue, j] - 0.30), 0)
```

No angle, no oscillator, no substeps. **A repair must beat both** — registered as
**criterion 9**, which is my addition beyond the owner's eight and is
**🔒 flagged for ratification**. It can only make passing *harder*, never easier. Without it,
"phase wins" is uninterpretable: it might just be reading the world's wiring.

## B1.4 `P7` was BROKEN and was rebuilt, not nudged

At the drafted `s0 = 0.55`, `P7` scored **0.0104 / 0.0208 / 0.0156** — below chance and worse
than its own shuffled control. Cause: reach-similarity on real edges is small in absolute
terms (same-chain mean `0.145`, cross-chain `0.028`), so one global threshold made **every**
edge repulsive. Replaced with a scale-free **relative** form that judges each edge against
that node's own neighbourhood. A broken control manufactures a false negative; this is the
same defect class as `P3` in CMB-P0 and it is not being shipped.

## B1.5 Re-frozen at the CONVERGED budget — and `P7` has NO passing setting

Freezing on the 10-substep transient would repeat the error A3.1 corrects, so both arms were
re-frozen at 200 substeps under the unchanged registered rule (*smallest* repulsion / spread
clearing the merge threshold while staying above `P0` — never the value maximising top-1):

| `P7` quantile | merge frac K=2/3 | accuracy Δ vs P0 | |
|---|---|---|---|
| 0.60 | 0.465 / 0.352 | +0.164 / +0.305 | merging FAILS |
| 0.70 | 0.234 / 0.249 | +0.223 / +0.250 | merging FAILS |
| **0.80** | 0.188 / 0.109 | +0.102 / +0.016 | **closest; K=2 merging and K=3 accuracy both narrowly miss** |
| 0.90 | 0.027 / 0.076 | −0.203 / −0.223 | accuracy COLLAPSES |

**No `P7` setting passes both.** The trade is monotone with no window. `P7` is registered at
its closest setting (0.80) so the bench reports that failure honestly rather than hiding it
behind a merely-broken value.

| `P8` omega | merge frac K=2/3 | accuracy Δ vs P0 | |
|---|---|---|---|
| 0.40 | 0.309 / 0.328 | +0.102 / +0.137 | merging FAILS |
| **0.80** | **0.148 / 0.116** | **+0.063 / +0.129** | **PASSES — smallest that does** |
| 1.60 | 0.070 / 0.069 | −0.051 / +0.113 | K=2 accuracy fails |

## B1.6 Mechanisms the panel killed with arithmetic, and which are NOT built

- **Structural frustration (phase lag).** 81% of edges have similarity exactly 0, so the
  maximum achievable lag on a structured edge is ~0.055 rad — *below* the 0.15 rad merge
  threshold. It cannot move the metric it targets.
- **Vector binding at D = pool.** Moving from a circle to an 8-sphere drops the merge metric's
  chance rate by ~195,000×. It would **pass the safety gate with an inert field** — a false
  PASS on a safety metric, the worst failure mode this bench has.
- **Adaptation-gated coupling.** Reads out on the two-state amplitude, which can go negative;
  non-negative amplitude is the condition under which signed coupling stays bounded.

## B1.7 What the dev evidence now predicts — stated before the run

At the converged budget, **no single repair clears the merge threshold at both primary K**.
Only the *exploratory* `P8P9` combination comes close (merge fraction 0.172 / 0.085), and it
**carries no verdict by construction**. So the most likely registered outcomes are
`PHASE_MEMORY_UNSAFE` or `PHASE_RETIRED_FOR_MULTICHAIN_MEMORY`. Writing that down in advance
is the point: if the held-out run instead produces a repair verdict, that is a surprise
against a recorded prediction rather than a story fitted afterwards.
