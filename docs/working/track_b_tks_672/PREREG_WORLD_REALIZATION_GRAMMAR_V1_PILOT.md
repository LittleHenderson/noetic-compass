# PRE-REGISTRATION — `WORLD_REALIZATION_GRAMMAR_V1_PILOT`

**The immediate successor.** Committed before any pilot generation.
**Date:** 2026-07-27 · **Gate 2:** OPEN at `0.38`

Sequence, owner-decided: **C → B**, with **A as diagnostic only**.

```
C  build and validate a better World-realization instrument   <- THIS
B  regenerate all 28 Foundations under one validated v3 lock
A  420-balanced view: diagnostic use only, never Gate 2 evidence
```

---

## 1. Why not a synonym whitelist

A fixed list —

```
Spiritual = sacred, soul, divine, transcendent
Physical  = body, object, movement, material
```

— would be learned by a character n-gram model immediately. It replaces one lexical shortcut with
another. **Rejected.**

## 2. `WORLD_REALIZATION_GRAMMAR_V1` — causal criteria, not vocabulary

The governing question for every scenario:

> **Where must the decisive success criterion become true?**

That is a question about causal structure, not descriptive nouns.

| World | The decisive change occurs in… | Realization families |
|---|---|---|
| **Spiritual** | a motive, authority, relationship, or success condition existing **beyond** ordinary material, informational, or felt outcome | nonphysical relationship · sacred obligation · continuity beyond bodily presence · metaphysical belonging · ritual participation · communion with an unseen order · transformation of existential relation |
| **Mental** | a **representation** | map · distinction · inference · explanation · interpretation · plan · conceptual organization · understanding |
| **Emotional** | **experienced value or relation** | felt attachment · comfort · grief · affection · aversion · emotional safety · resentment · trust · felt belonging |
| **Physical** | **bodily, spatial, material, or operational reality** | body state · object possession · location · movement · consumption · construction · measurable physical condition · material resource · direct action |

**No phrase is mandatory.** These name functions, not required words.

## 3. Held-out realization families — the protection against C becoming a synonym instrument

**This is the load-bearing control.** Realization families are **split**; not every family may
appear in training.

```
Spiritual, illustrative split
  TRAIN  ancestor relationship · ritual obligation · sacred promise · unseen guidance
  TEST   continuity after death · transcendent belonging
```

A character model may learn one family's vocabulary. It should **not** succeed on genuinely
held-out families unless a broader shortcut survives. The train/test family split is **frozen
before generation** and applied per World.

## 4. Pilot — disposable, never enters the final corpus

The eight starved cells, plus eight **pre-selected** matched controls (same-drive/different-World,
same-World/different-drive, including the easy Mental cells `2b` and `7b`):

```
starved   5d  2a  7a  7c  1d  6a  6b  7d
controls  chosen BEFORE generation, recorded in the lock
16 Foundations x 4 independent plans x 5 candidates = 320 candidate scenarios
```

**Pilot items are quarantined. None may enter `TKS_672_V3`.**

## 5. Frozen pilot criteria

| # | Criterion |
|---|---|
| `R1` | **direct leakage** — starved-cell World-label leakage materially reduced from v2 (`5d 0.350`, `7c 0.375`, `6a 0.300`, `7a 0.300`, `1d 0.275`) |
| `R2` | **surface control** — every admitted family passes the existing June `0.60` gate |
| `R3` | **semantic positive control** — blind judges recover intended World **and** drive in ≥ `0.70` of complete families |
| `R4` | **cue-family transfer** — judges retain recovery on **held-out** realization families |
| `R5` | **lexical resistance** — char 3–5-gram and word TF-IDF do **not** recover World by learning realization-family vocabulary |
| `R6` | **author comparison** — the World asymmetry is checked against a **second author source** or a small human-authored arm |

`R4` and `R5` failing together → the grammar became a synonym list. **Rejected, back to design.**

### `R6` interpretation table — frozen before data

| weak author | second author | conclusion |
|---|---|---|
| Physical/Spiritual leak more | same pattern | stronger expressibility / canon evidence |
| leaks | does not | **author-model limitation** |
| both avoid labels, judges fail | — | semantic boundaries genuinely unclear |
| both avoid labels, judges recover | — | **the realization grammar works** |

## 6. `v3` budget — set by the verified binomial, frozen now

At the worst observed candidate leak (`7c = 0.375`, so `p_pass = 0.625`):

```
n=5 candidates  P(>=3 clean) = 0.7248     <- v2's budget, verified
n=8 candidates  P(>=3 clean) = 0.9640     <- v3
```

Sanity check on the model: at v2's mean leak `0.142`, it predicts family completeness `0.977`
against `211/224 = 0.942` observed — optimistic by exactly the expected margin, since it assumes
independent candidates and regex-only gating.

**Frozen v3 structure:**

```
28 Foundations x 12 ATTEMPTED plans x 8 candidates per plan
retain the FIRST 8 PASSING families per Foundation in frozen plan order
28 x 8 x 3 = 672 final items
```

Twelve plans give headroom for the later surface and recoverability gates **without changing rules
after seeing yield**. Surplus passing families are preserved as **unused reserve evidence**.

> **The eight retained families are chosen by frozen plan order, NEVER by best judge score.**

Per-family admission, unchanged from v2: generate `8` in frozen order → apply **only** the
direct-label regex → retain the first `3` passing → June gates on the selected family →
independent recoverability control → accept or reject the **whole family**.

## 7. v1, v2, and the 420 view

```
v1   NOT_FROZEN / NOT_SCORED / AUTHORING-YIELD EVIDENCE      preserved
v2   FAIL_AUTHORING_YIELD / NOT_FROZEN / NOT_SCORED          preserved, 653 siblings intact
```

`TKS_420_BALANCED_DIAGNOSTIC_V1` is a **manifest view over the preserved v2 corpus** — no item is
physically discarded.

**Permitted:** readout-software testing · fold checking · lexical-baseline measurement · report
development · Foundation 4/6 confusion analysis.
**Prohibited:** `GATE_2_CLAIM_BEARING_EVIDENCE`.

Promoting the 420 subset now would revise the evidentiary target *after* seeing
`FAIL_AUTHORING_YIELD`, and five independent families per Foundation is too thin for a 28-way
authority claim.

## 8. Mixture benchmark stays separate

`TKS_28_FOUNDATION_BENCHMARK_V3` (dominant hard classification) and
`TKS_FOUNDATION_MIXTURE_ORDINAL_V1` (`A-dominant` / `balanced` / `B-dominant`) remain distinct
artifacts. `80/20`-style labels are **construction targets only**; the scientific claim is ordinal.
Θ supports weighted ingredients and the simplex supports distributed mass, but **natural-language
mixture magnitude must be empirically calibrated, never assumed from author intent.**

## Status

`LOCKED / PILOT ITEMS QUARANTINED / NOTHING LICENSED`
