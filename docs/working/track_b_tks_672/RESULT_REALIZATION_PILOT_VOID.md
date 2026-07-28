# RESULT — `WORLD_REALIZATION_GRAMMAR_V1_PILOT`

**Verdict:** `VOID_APPARATUS_DEFECT` — **not** an `R1` failure against the grammar.
**Lock:** `e56a6e7a` · parser fix `067ca84a`

**The grammar was never actually tested.** Two defects in my instrument, both mine.

---

## What the numbers said

```
overall pilot leak   0.4058     v2 baseline 0.1420     +0.2638
1d  0.275 -> 0.750   +0.475        5d  0.350 -> 0.812   +0.463
6a  0.300 -> 0.667   +0.367        7a  0.300 -> 0.625   +0.325
7c  0.375 -> 0.688   +0.312
```

Every starved cell got **worse**. On its face that reads as a decisive `R1` failure. It is not,
because the instrument was broken in a way that manufactures exactly this result.

---

## Defect 1 — my prompt printed the forbidden word, twice, in capitals

```
WORLD REALIZATION GRAMMAR ...
  {wname}: {wcrit}                                    <- "PHYSICAL: ..."
  For this target it must become true in the {wname} sense above.   <- "PHYSICAL" again
ABSOLUTE PROHIBITION — none of these may appear: ... physical ...
```

**`72%` of all leaks are the cell's own World name** (`69/96`). Leak counts:
`physical 49` · `emotional 16` · `spiritual 14` · `mental 9` · `physically 8`.

I named the concept in capitals immediately before forbidding it. That is a priming effect, and it
is the single most likely cause of a `3×` leak increase in a run whose entire purpose was to
*reduce* leakage.

**This is the same class of error as the `P5` gate missing the descriptor channel:** I built a
control and then leaked through a channel I created myself.

## Defect 2 — payload shape loss made `R4`/`R5` unevaluable

```
candidates recorded          207 / 320 expected
realization_family = None    127 / 207
```

The author returned inconsistent shapes; my normalizer recovered the scenarios but the
`realization_family` field was absent from most payloads. **The held-out family control — the
load-bearing protection against the grammar becoming a synonym list — could not be evaluated at
all.**

A run that cannot evaluate its own key control is not a test.

---

## Why this is `VOID` and not `FAIL`

| | Means |
|---|---|
| `R1 FAIL` | *the grammar does not reduce leakage* |
| **`VOID_APPARATUS_DEFECT`** | **this run could not determine that** |

Recording this as `R1 FAIL` would attribute to the grammar a result produced by my prompt
construction. That would be a false negative entered into the permanent record, and it would
wrongly close off option C.

## What is NOT concluded

- **Not** that the realization grammar fails. It was not tested.
- **Not** that Physical/Spiritual are inherently harder — the v2 evidence for that stands on its
  own and is unaffected, but this run adds nothing to it.
- **Not** anything about `R2`–`R6`. None ran.

## Required for the successor — a NEW lock, not a re-run

1. **The World name must never appear in the author prompt.** Refer to the criterion only —
   *"the decisive change occurs in bodily, spatial, material or operational reality"* — with **no
   label at all**. The author should never see the word it must not write.
2. **Prompt-side leak audit before generation:** assert that no prohibited word appears in the
   assembled prompt. A mechanical check, not a reading.
3. **Port `normalize_payload` and require `realization_family`**; a payload lacking it is a
   retryable failure, so `R4`/`R5` remain evaluable.
4. Baselines unchanged: v2 per-cell rates and the `0.142` overall.

**No threshold, control cell, or criterion changes.** The frozen 16-cell set stands. The defect is
in prompt assembly and payload handling, not in the experimental design.

## Status

```
pilot v1   VOID_APPARATUS_DEFECT / QUARANTINED / NOT EVIDENCE FOR OR AGAINST THE GRAMMAR
v1 corpus  NOT_FROZEN / NOT_SCORED
v2 corpus  FAIL_AUTHORING_YIELD
Gate 2     OPEN at 0.38
```
