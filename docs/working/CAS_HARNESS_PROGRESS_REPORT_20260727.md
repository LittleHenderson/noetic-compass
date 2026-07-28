# CAS Harness — Progress Report

**Date:** 2026-07-27 · **Ladder position:** `0.38` of `1.00` · **Current gate:** 2 of 8

---

## 1. The ladder

| Gate | Condition | Score | Status |
|---|---|---|---|
| **1** | fresh technical canary independently passes | `0.38` | **EARNED** 2026-07-24 |
| **2** | small-model semantic authority, matched controls, uncertainty, claims reconciliation, withdrawn-`ACCEPT` root cause close | `0.46` | **OPEN** |
| 3 | Pythia prompt-injection and steering/ablation pass preregistered controls; CJT/J-Space/Bias/RPM/CAS-Ohm resolve | `0.56` | not started |
| 4 | five model families pass held-out confirmation | `0.65` | not started |
| 5 | 100B rehearsal then recoverable 300B/314B run | `0.75` | not started |
| 6 | evidence storage, WORM/witness, failover, isolation, incident recovery | `0.85` | not started |
| 7 | accounts, product UI, billing, legal/compliance, phased launch | `0.95` | not started |
| 8 | independent reproduction, nine customer-production authorities, release decision | `1.00` | not started |

**Gate 1 was earned by Attempt 11** — receiver-confirmed technical canary pass (`f95cc610`),
which moved the score from `0.33` to `0.38` (`194fec39`). The Jacobian machinery is proven to
produce technically valid derivatives.

---

## 2. Headline: the campaign's central defect was found and fixed today

For months, **sixteen consecutive instruments returned null results** on Gate 2. The working
assumption was that the framework might not be measurable. That assumption was wrong, and the real
cause was found by running a check nobody had run.

### The diagnosis

Every instrument compared **two things that might both be undetectable**. None asked the prior
question: *can this apparatus detect a signal that is certainly present?* A positive control
(`d755665b`) answered it:

| Tier | Item shown to the judge | Accuracy | vs chance `0.0357` |
|---|---|---|---|
| `T0` | the definition, verbatim | `1.000` (28/28) | `p = 3.0e-41` |
| `T1` | a mechanical rewrite | `1.000` (160/160) | `p = 2.8e-232` |
| `T2` | **the real test scenarios** | `0.0429` (12/280) | **`p = 0.3011`** |

**The harness was fine. The test items were empty.** `T2` was statistically indistinguishable from
a coin flip. Every instrument built downstream of scenario authoring had been measuring noise.

### The repair

The owner supplied a 27-section contrastive authoring specification. Holding the **author model
fixed** at the same weak `gemini-2.5-flash-lite` that produced the empty scenarios:

| | Protocol | 28-way recovery |
|---|---|---|
| baseline | thin prompt | `0.0429` — a coin flip |
| **repaired** | owner's specification | **`0.9167`** (77/84), `p = 1.3e-102` |

Only the instructions changed. **Drive recovery was perfect: `84/84`.**

**Scope, narrowed at owner instruction:** the original authoring prompt was a *sufficient* cause of
the scenario-signal failure and appears to explain a major portion of the downstream nulls. It is
**not** established that all sixteen instruments were otherwise flawless.

---

## 3. Honest claim ledger

### Licensed

| Result | Claim |
|---|---|
| `SCRAMBLE-NULL-COMPLETION-v1` | The TKS grid is non-arbitrary beyond vocabulary overlap on `pythia-1b`. `0/200` fresh scrambles beat it; margin beyond lexical `+0.184`. *(Secondary ordinal test FAILED — no "gradient" claim.)* |
| `SPEC-AUTHORED-SCENARIOS-v1` | Scenarios authored under the specification carry recoverable foundation signal at `0.9167` where the thin prompt scored `0.0429`. The deficit was authoring protocol. |

### Not licensed — and why

| Result | Verdict |
|---|---|
| `SMALL-MODEL-RECOVERY-v1` | `NOT_LICENSED_LEXICAL`. Drive far above chance (`0.5595` vs `0.1429`, `p = 0.0001`) but **did not beat character n-grams** (`0.6071`). |
| `LATIN-SQUARE-SUCCESSOR-v1` | `NOT_LICENSED_LEXICAL` — **replicates** the above under corrected folds. `0.4524` vs char `0.4881`. |
| matched A/B (TKS vs compact definitions) | `NOT_LICENSED_DEGENERATE` at two scales. Both arms near floor — now explained: the items were empty. |
| 8 further instruments | honest nulls |

### Void — no result, not a negative

| Design | Reason |
|---|---|
| `SMALL-MODEL-SEMANTIC-MATCH-v1` | **Premise defect I introduced.** Treated TKS canon text and CAS compact text as two wordings of the same cell. They are a *positional* relabeling that deliberately changes semantics. Killed before any number existed. |
| World endpoint of `SMALL-MODEL-RECOVERY-v1` | `world = 0.0000` exactly, every arm — fold construction put each World entirely in one test fold, absent from its training set. Structurally unidentifiable. |
| repetition-inversion (`B4`) | Surface guard fired; control **not** amended after it fired. |

### Disclosed contamination

`47/84` scenarios (`56%`) contain the literal World name — a leak my `P5` gate did not measure,
found in a post-hoc audit of my own result. The World axis is flagged everywhere it appears.

---

## 4. The apparatus is now validated

First time in the campaign that both leakage controls have been run:

| Control | Observed | Expected | |
|---|---|---|---|
| `C-PERM` group-level label permutation | `0.0595` | `~0.1429` | **PASS** |
| `C-BODY` constant text, no metadata to extractor | `0.1429` | `≤` majority `0.1429` | **PASS** |

`C-BODY` landing *exactly* on the majority rate is the clean signature. **No leakage through
ordering, file structure, position, identifiers, or split construction.**

---

## 5. Where the evidence state moved

```
BEFORE today    "the items contain no signal"  — cause unknown, 16 nulls
AFTER today     "the small model has not demonstrated semantic extraction
                 beyond lexical regularities"
```

Those are **entirely different states of evidence**. Only the second is now in play.

One pattern worth flagging: **the only axis where the small model leads is the contaminated one.**
On World (56% leaked) it beats lexical by `+0.0357`; on drive (clean, judge-perfect) it does not
beat character n-grams. That points *away* from semantic extraction.

---

## 6. Closed, and why

**The 84-item scenario lane is COMPLETE** (`bed3fc94`). Further layer, pooling, classifier, or fold
tuning on those items is prohibited — it would turn a clean experiment into benchmark fitting.
Reopen only for reproduction, audit, or explicit successor comparison.

**A governance defect was repaired.** An external agent read a dated handoff and recommended
executing a canary that had already passed four attempts earlier. `CAS_HARNESS_CURRENT_STATE.json`
is now the machine-readable continuation pointer, and three superseded documents carry
`HISTORICAL SNAPSHOT` banners.

---

## 7. What happens next

1. **Mainline — the narrow CJT/J-space joined experiment** (`0dcca79b`, pre-registered). One
   cause–bias–effect circuit, one ordered prerequisite gate. Observation map frozen to
   `C_EQUALS_I_AT_REGISTERED_TEST_POINT`. Observational map first, freeze, *then* intervention.
2. **In parallel — the `672`-item corpus** (`28 × 8 independent plans × 3 siblings`), generated
   against the **existing June 2026 surface gates** rather than a new framework. Register/World was
   already known to be the surface-loud axis; today's leak was a rediscovery.
3. **Then** compare the full readout ladder: char → TF-IDF → L0 → mean-pool → decision token →
   Jacobian projection → J-space.

**Gate 2 closure is a separate governance decision** under `G2-JSPACE-SUCCESSOR`, and it is the
owner's call — never declared equivalent after the fact.

---

## 8. Standing rules earned the hard way

- Statistical uncertainty cannot convert *did not exceed* into *exceeded*.
- Grid position never licenses semantic equivalence.
- A control that fires is evidence, not an obstacle.
- Effective `n` is the honest grouping unit, never the row count.
- Every design needs a positive control.
- Fluent generated items can encode nothing — validate items before comparing arms.

**21 commits today. Gate 2 remains OPEN at `0.38`.**
