# CMB-P0 — RESULT: `PHASE_MEMORY_UNSAFE`

**Run:** `cmb-p0-1788323717` · instance `i-01a53aba4c8fcfcd2` · Tesla T4, `us-west-2`
**Cost:** **$0.0241** (2.75 min instance runtime; hard cap was $0.80) · self-terminated
**Harness:** v0.2 · **content hash** `372173ddfb551137801c2acf5b96fe0b`
**Compute:** torch `2.6.0+cu124`, CUDA 12.4, peak VRAM `65,409,536` bytes, harness wall `20.08 s`
**Status emitted by the program**, not by prose, from frozen thresholds.

---

## The headline, stated honestly

**The phase arm beat every single control at every value of K — and the safety override
still fired, because it merges distinct chains.**

`P4_PHASE_OSCILLATOR` won all five registered comparisons, at K=2, K=3 and K=4, in 16–20 of
20 held-out worlds each. Under the five-outcome law that is the pattern for
`PHASE_MULTICHAIN_SIGNAL` — the owner's strongest outcome, the intuition vindicated with a
mechanism.

It was **not** emitted. `PHASE_MEMORY_UNSAFE` overrides every other outcome, *including a
top-1 win*, and it fired on real evidence in 20/20 worlds.

In plain terms: **the phase engine retrieves better while losing track of which train of
thought it retrieved from.** More accurate, less accountable. For a memory system whose
whole purpose is attribution, that trade is the wrong way round.

## Held-out top-1 (20 worlds per K, all arms paired on identical worlds and queries)

| K | P0 | **P1 oracle** | P2 | P3 | **P4 phase** | P5 | P6 |
|---|---|---|---|---|---|---|---|
| 1 *(sanity)* | 0.938 | 0.938 | 0.504 | 0.930 | 0.935 | 0.341 | 0.362 |
| 2 | 0.503 | 0.780 | 0.312 | 0.470 | **0.556** | 0.284 | 0.283 |
| 3 | 0.343 | 0.677 | 0.235 | 0.331 | **0.398** | 0.272 | 0.225 |
| 4 | 0.251 | 0.560 | 0.157 | 0.244 | **0.299** | 0.236 | 0.203 |

`P1` is an **oracle** — handed the true chain labels. It is a ceiling, never a method.

## Why the run is `PHASE_MEMORY_UNSAFE` — false chain merges

`false_chain_merges` counts how many distinct chain pairs an arm collapses into one group.

| K | **P4 phase** | P5 | P2 | P1 oracle | P4 − P2 | worlds |
|---|---|---|---|---|---|---|
| 2 | 0.657 | 0.071 | 0.242 | 0.000 | +0.415 | 20/20 |
| 3 | **1.852** | 0.263 | 0.186 | 0.000 | **+1.666** | 20/20 |
| 4 | **3.538** | 0.484 | 0.200 | 0.000 | **+3.338** | 20/20 |

Threshold `MERGE_MARGIN = 0.50` merges. At K=4, P4 collapses **3.54 of the 6 possible chain
pairs**. The damage grows steeply with K — which is exactly backwards for a mechanism whose
entire promise is *simultaneous-chain capacity*.

**This is the predicted consequence of the synchrony analysis, now measured.** Chains lock
internally (order parameter `0.9931`), and the more chains are active, the more they lock to
*each other*. Phase separates two trains tolerably and four trains not at all.

**A metric that would have lied on its own.** `chain_assignment_accuracy` for P4 reads
0.876 / 0.772 / 0.686 — respectable, and better than P5 at every K. It is computed by
assigning each node to its nearest chain-mean phase, so it still looks healthy *after the
chain means themselves have collapsed together*. Only the merge count sees the collapse. Had
the bench carried the accuracy metric alone, this run would have reported a clean phase
victory.

## Contamination is NOT the problem — and that sharpens the finding

| K | P0 | P4 | P4 − P0 | worlds positive |
|---|---|---|---|---|
| 2 | 0.200 | 0.189 | **−0.011** | 0/20 |
| 3 | 0.398 | 0.378 | **−0.020** | 0/20 |
| 4 | 0.585 | 0.554 | **−0.031** | 0/20 |

P4 returns *fewer* wrong-chain items than the scalar engine, in 0/20 worlds worse. So the
failure is not "it retrieves from the wrong chain". It is **"it cannot tell you which chain
it retrieved from"** — a grouping failure, not a retrieval failure. Those are different
defects and the bench separated them.

## Every registered comparison (paired, per K; `W` = win under the frozen rule)

| Comparison | K=2 | K=3 | K=4 |
|---|---|---|---|
| P4 vs P0 | +0.0531 19/20 **W** | +0.0555 18/20 **W** | +0.0484 18/20 **W** |
| P4 vs P3 *(capacity)* | +0.0867 16/20 **W** | +0.0672 19/20 **W** | +0.0555 19/20 **W** |
| P4 vs P5 *(killer)* | +0.2727 20/20 **W** | +0.1266 17/20 **W** | +0.0633 17/20 **W** |
| P4 vs P6 *(2nd channel)* | +0.2734 19/20 **W** | +0.1734 17/20 **W** | +0.0961 16/20 **W** |
| P4 vs P2 *(tags)* | +0.2437 20/20 **W** | +0.1633 18/20 **W** | +0.1422 18/20 **W** |
| P3 vs P0 | −0.0336 5/20 | −0.0117 3/20 | −0.0070 2/20 |
| P2 vs P0 | −0.1906 0/20 | −0.1078 4/20 | −0.0938 4/20 |

Three secondary findings fall out, and none of them is what the design document predicted:

1. **Extra state alone buys nothing.** `P3 − P0` is *negative* at every K. A second number
   per node, used the ordinary way, does not help. `EXTRA_STATE_CAPACITY_SUPPORTED` is not
   supported.
2. **Inferred tags are worse than no tags.** `P2 − P0` is negative at every K, while the
   *oracle* tags (P1) are far better than everything. So the tag mechanism works only with
   perfect labels; with labels you have to infer, mis-assignment routes the query into the
   wrong channel and costs more than the tag buys. The design document's expectation that
   "a tag closes the gap more cheaply" **is not supported on this construction** — inference
   is the bottleneck, and it is expensive.
3. **The advantage is not just "a second channel".** P4 beats `P6_SCALAR_TWO_CHANNEL` — a
   non-angular second cue-seeded field in P4's identical product form — at every K. So the
   angle is doing something a plain second channel does not.

## Instrument gates — one FAILED, and it matters

| K | `GATE_HEADROOM` P0 < 0.90 | `GATE_ORACLE` P1 ≥ 0.60 |
|---|---|---|
| 2 | 0.503 **PASS** | 0.780 **PASS** |
| 3 | 0.343 **PASS** | 0.677 **PASS** |
| 4 | 0.251 **PASS** | **0.560 FAIL** |

**At K=4 the oracle itself falls below the ill-posedness threshold.** Even handed the true
chain labels, the task is only 56% solvable. K=4 is therefore flagged
`INSTRUMENT_OR_TASK_ILL_POSED` and its numbers must not be read on their own.

The safety verdict does **not** depend on that stratum: the merge finding is already decisive
at **K=3**, where the oracle passes at 0.677 — `+1.666` merges in **20/20** worlds against a
threshold of 0.50. Had K=4 been excluded entirely, the status would be unchanged.

*Ordering note:* safety is evaluated **before** the gates, so `PHASE_MEMORY_UNSAFE`
pre-empted the K=4 gate failure. That ordering was a deliberate pre-launch repair — the
draft checked gates first, which would have let a saturating baseline hide a genuine safety
finding.

## Construct-validity checks that passed

- **`B_STATIC` diagnostic = 0.0000 at every K.** The order-blind static-profile attack is
  fully defeated: gold and every rival completion carry the same multiset of features in a
  different order, so a static readout cannot separate them. The preregistration called this
  the sharpest adversarial property; it is now actually mounted and actually defeated.
- **One-hop adjacency is uninformative** — re-measured at chance after the C1 repair.
- **Distinct queries**: 26/64, 51/64, 54/64 (was 2/64, 3/64, 4/64 before the C2 repair).
- **Single-chain sanity (K=1)**: P0, P1, P3, P4 all cluster at 0.93–0.94. Where there is
  nothing to separate, the arms agree — as the preregistration required.

## The parameter freeze cost P4 accuracy, and the receipt proves it

The convergence sweep is persisted in the receipt:

| phase substeps | within-chain order | cross-chain separation | P4 top-1 |
|---|---|---|---|
| 1 | 0.5973 | 1.3268 | 0.2474 |
| **4** | 0.9143 | 0.8053 | **0.4601** ← highest |
| **10 (frozen)** | 0.9937 | 0.2497 | 0.4123 |
| 25 | 0.9998 | 0.0166 | 0.3602 |

Freezing at the converged value (10) rather than the transient (4) **cost P4 0.048 of
top-1**. The freeze was made against the hypothesis, and the receipt lets anyone verify that
rather than take it on trust.

## Mathematics (registered, derived, never set as knobs)

```
two-state block operator M = [[(1-d)I + gW, -bI], [eI, (1-e)I]],  d=0.30 g=0.50 b=0.30 e=0.50
complex modes            1600 / 1600          (adding one state variable DOES create rotation)
spectral radius          0.8660   stable      (margin 0.1340)
one-state max|Im|        0.0                  (reproduces the design doc's finding)
pulse width  tau         2.8037 waves = -1/ln(1-delta)     NOT 1/delta (= 3.3333)
Q                        0.6698  dimensionless, dominant decaying oscillatory mode
period                   32.61 waves
```

`Q` uses the formula registered in §4.2: `Q = omega_d / (2*alpha)`. The provisional
`Q ≈ 6.88` in the design document used an unregistered convention and is **superseded**.

**Scope, stated plainly:** this spectrum characterises `P3`'s engine. It does **not** describe
`P4`, whose phase dynamics are nonlinear; `P4`'s registered diagnostic is the Kuramoto order
parameter (within-chain `0.9931`, cross-chain separation `0.2772`).

## What is licensed, and what is not

**Licensed — this exact sentence:**

> On synthetic multi-chain worlds of this construction, a phase-coded two-state engine
> retrieved the cued chain's continuation more accurately than a scalar engine, than a
> matched two-state engine without phase, than a non-angular second channel, than inferred
> chain tags, and than its own phase-destroyed control — at K=2, 3 and 4 — **and** collapsed
> distinct chains into a single phase group at a rate rising to 3.54 of 6 pairs at K=4,
> which the preregistered safety rule classifies as `PHASE_MEMORY_UNSAFE`.

**NOT licensed:** any resonance-specific claim. Any CAS-specific claim. Any statement about
real memory, real cognition, or any graph other than these synthetic worlds. Any claim that
K=4 numbers stand alone (that stratum failed its own oracle gate). Any merge into CMB-R1.

## Stop condition

**Stopped, as directed.** No merge into CMB-R1. No follow-on arm. No parameter retry. The
next step is an **independent audit** by a model other than me.

## Owner decisions outstanding

1. **Ratify or strike `P6_SCALAR_TWO_CHANNEL`** — a seventh arm I added beyond the
   registered six. It is a control, so it can only weaken a phase claim. P4 beat it anyway.
2. **Rule on §6's merge comparator.** §6 says merges must exceed **P0's**; P0 produces no
   chain assignment, so that clause is unimplementable as written. The code used **P2**.
   Since this decided the emitted status, it needs an explicit ruling.
3. **Rule on K=4.** Its oracle gate failed. Options: drop the stratum, lower `L_CHAIN`, or
   accept K∈{2,3} as the reportable range.
4. Whether to open a lane on **cross-chain inhibition or frequency heterogeneity** — the
   named missing ingredients for stable phase separation. Neither was built: a free frequency
   control is forbidden by your constraint, and negative coupling is a new mechanism, not a
   parameter, so it is not mine to authorize.
