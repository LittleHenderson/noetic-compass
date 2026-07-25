# GATE 2 ITEM 4 — PRE-REGISTRATION v2 (`TKS-DEFCTX-40E-SPLITLAYER-v2`)

**Written:** 2026-07-25, **after** the v1 run and **with full knowledge of its numbers.**
**Supersedes:** `GATE2_ITEM4_PREREGISTRATION.md` (design `TKS-DEFCTX-40E-PRIMARY-v1`), which is
**retained unedited** as the record of what was frozen and what failed.

---

## 0. THE HONESTY PROBLEM WITH THIS DOCUMENT, STATED FIRST

This pre-registration is written by someone who has already seen the v1 results. That is a real
threat to its validity and it is not waved away. The roadmap's exit clause is explicit:

> *"Mixed or negative results remain `OPEN / NOT LICENSED`; criteria are not rewritten after outcomes
> are known."*

So the following are **binding constraints on this document**, and each is checkable by an auditor:

1. **v1's result stays dead.** Nothing here retroactively licenses the v1 run. Its headline
   (`A 0.1979 / B 0.2041` against `D 0.0390 / E 0.0325 / F 0.0175`) remains `NOT LICENSED` forever,
   regardless of what v2 finds.
2. **No threshold is relaxed.** Every acceptance bar carried over from v1 keeps its v1 value:
   macro-accuracy contrast, margin `>= 0.15`, bootstrap CI excluding zero, layer stability `>= 60%`,
   equal-token-budget same-sign. Not one number is loosened. Where v2 differs it is *stricter*
   (Section 4).
3. **The failed control is not redefined into a pass.** v1's wrong-layer control failed. v2 does not
   rename it, drop it, or reinterpret it as a feature. It **replaces the false claim it refuted** with
   a claim that is true, and then tests the new claim with a *harder* control (Section 3.2).
4. **Layer 12 is not adopted.** v1's arm-free selection chose `L=10`; layer 12 anchors would have
   scored `0.3420` against `0.1979`. v2 does not inherit any layer from v1. It re-selects from
   scratch, arm-free, on a **fresh calibration split with a new seed**, and whatever it picks it keeps.
5. **v2 must run on a model v1 never touched** — see Section 5. A design revised with knowledge of
   one model's results has no claim to be confirmatory on that same model.

If an auditor judges that this document has smuggled a post-hoc advantage past those five
constraints, **the correct response is to discard v2 entirely**, not to argue about it.

---

## 1. WHAT v1 ESTABLISHED, AND WHAT IT KILLED

**Survived v1 (robust, but unlicensed):** the comparative ordering. TKS definitions (Arms A and B)
beat compact CAS, a coherent non-TKS ontology, and nulls at **6 of 7 layers**, survived
sentence-boundary truncation to a common token budget with the same sign, and every null control sat
at chance (`layer0 0.0250`, `random-direction 0.0263`, `shuffled-labels 0.0232`).

**Killed by v1:** the commensurability claim. v1 section 2.0 asserted that anchors `u` and items `v`
are comparable **because** both are read at the same layer through the same scaffold, and called this
"the load-bearing step of the entire design." The clean control refuted it:

| anchor layer | item layer | macro-acc |
|---|---|---|
| L0 | L10 | `0.0250` |
| L6 | L10 | `0.1441` |
| L8 | L10 | `0.2264` |
| **L10 (matched)** | **L10** | **`0.1979`** |
| L12 | L10 | `0.3420` |

Anchors from a deliberately wrong layer **beat** matched anchors with items held constant. Same-layer
reading is not what makes `u` and `v` comparable.

**Also killed:** any claim that the effect is *localized* to the selected layer.

---

## 2. THE CORRECTED CLAIM

v1 claimed: *anchors and items are comparable because they share a layer.* **False.**

v2 claims instead: *anchors and items are comparable because they are produced by the identical
frame set, the identical trailing scaffold, and content beginning at position 0 — and the layer each
is read at is a **free parameter chosen without any arm information**.*

This is weaker, and that is the point. It asserts only what v1's own data supports. It also predicts
v1's anomaly: anchor layer and item layer are **separable** dimensions, so there is no reason the
best anchor layer should equal the best item layer.

---

## 3. DESIGN

### 3.1 Split-layer selection, both arm-free

- **Item layer `L_item`** — selected exactly as v1's fixed rule: an arm-free multinomial logistic
  probe on calibration item states, **fit and scored on disjoint halves** of calibration. (v1's
  original rule fit and scored on the same set, returned `1.0000` at every layer, and made the choice
  arbitrary; the disjoint-halves fix is carried forward.)
- **Anchor layer `L_anchor`** — selected on calibration by **anchor-to-anchor separability only**:
  the mean pairwise cosine distance between the 40 centered anchors, computed **per arm and then
  averaged across arms with equal weight**. This never touches item states, never touches labels, and
  never touches any arm's *score*. It cannot prefer one arm, because every arm contributes equally.
- The two are selected **independently** and may differ. Both are frozen before any arm is scored.

**Why this is not the layer-12 trap.** The trap would be picking the layer that maximises *Arm A's
accuracy*. This criterion never computes an arm's accuracy. It is a property of the anchor geometry
averaged over all arms, computable with the labels destroyed.

### 3.2 The replacement control, which is HARDER than v1's

v1 asked: does a mismatched layer fail? (It didn't, refuting v1's claim.)
v2 asks the question that actually threatens the corrected claim:

> **Does the readout still work when the FRAME/SCAFFOLD symmetry is broken, holding both layers fixed?**

Three new controls, all expected near chance if the corrected claim is true:

- **C1 — scaffold mismatch.** Anchors rendered with the frozen scaffold; items rendered with a
  *different* trailing scaffold (`"This sentence concerns:"`). If accuracy survives, the shared
  scaffold is not what makes them comparable and v2's claim is refuted in turn.
- **C2 — frame mismatch.** Anchors through frames 1–4; items through four *held-out* frames never
  used for anchors.
- **C3 — position break.** Item content preceded by a 40-token neutral filler so it does not begin at
  position 0, while anchors do.

**Pre-committed consequence:** if any of C1–C3 scores above `0.5 x matched`, the corrected
commensurability claim is **also** false, v2 is reported `NOT LICENSED`, and the definition-anchored
prototype family is **closed** — exactly as the injection family was closed after four attempts. No v3.

### 3.3 Carried forward unchanged from v1

Frames, trailing scaffold, `code`/`title` discarded, arm-internal class centering, label-free
calibration centering, argmax over cosine with **zero fitted parameters**, the repaired admissible
bank, 20 seeds, group bootstrap, and the full null battery (layer-0, random-direction,
shuffled-label). The contaminated fixture (816/816 rows embedding Arm B's definition) stays excluded.

---

## 4. ACCEPTANCE CRITERIA — UNCHANGED IN VALUE, STRICTER IN COMPOSITION

| # | Criterion | Bar | vs v1 |
|---|---|---|---|
| A1 | TKS arms > D, E, F | strict | same |
| A2 | A−D margin | `>= 0.15` | same |
| A3 | Group bootstrap CI on that margin | **lower bound `>= 0.15`** | **STRICTER** — v1 accepted "excludes zero"; v1's actual CI lower was `0.1422`, which would fail this |
| A4 | Layer stability | `>= 60%` of grid | same |
| A5 | Equal-token-budget replicate | same sign **and margin `>= 0.15`** | **STRICTER** — v1 required only same sign; v1's truncated margin `0.1300` would fail this |
| A6 | Null battery | all at chance | same |
| A7 | **C1–C3 commensurability controls** | all `< 0.5 x matched` | **NEW** |
| A8 | Order-aware encoder control | TKS arms must beat it | same (still unpinned) |

**A3 and A5 are deliberately set where v1 would have failed them.** A revised design that only passes
because its bars moved down is worthless; these moved up.

---

## 5. MANDATORY MODEL CHANGE

v2 runs on **a model v1 never touched**. `pythia-160m` is retired from this design permanently. A
design revised with knowledge of one model's numbers cannot be confirmatory on that model. Candidate
models are pinned in the run manifest before capture; `pythia-410m` and `pythia-1b` are both already
available locally.

**Consequence, accepted in advance:** if the effect is a `pythia-160m` artifact, v2 fails. That is the
test working.

---

## 6. WHAT A NEGATIVE RESULT MEANS

If v2 fails: definition-anchored prototype readout does not support a licensed
definition-selection claim at accessible scales, the family closes, and Gate 2 must route through a
different item-4 instrument. The owner's prior — that original TKS wording preserves more semantic
signal — would then stand **unsupported by this method**, which is not the same as refuted, and must
be reported with that distinction intact.

---

## 7. STATUS

`LOCKED / NOT YET RUNNABLE / NOTHING LICENSED`

Outstanding before capture: pin the v2 model + revision + hashes; pin the order-aware encoder (B7,
still `INCOMPLETE_ORDER_AWARE_ENCODER_NOT_PINNED`); author the C1–C3 held-out frames and filler; and
the two owner items unchanged from v1 — Arm D crosswalk ratification (B5) and the 28-Foundation axis
acknowledgement (B9).

Gate 2 remains **OPEN at `0.38`**. This document licenses nothing.
