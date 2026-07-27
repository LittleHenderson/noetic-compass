# PRE-REGISTRATION — `SMALL-MODEL-SEMANTIC-MATCH-v1`

**Committed BEFORE any model is loaded.**
**Date:** 2026-07-27
**Gate 2 status at time of writing:** OPEN at `0.38`

---

## Why this design, and why now

`JUDGE-POSITIVE-CONTROL-v1` (result `d755665b`) closed two questions and opened one:

- The harness is sound (`T0 = 28/28`).
- The authored scenarios carry no recoverable signal (`T2`, `p = 0.3011`).
- **`T1 = 160/160` could not be read as semantic discrimination**, because `T1` items stayed
  lexically close to their targets. A string matcher would score the same.

Two gaps therefore block any Gate 2 claim, and both are named in the gate's own wording —
*"the scoring actually works **on a small model**, with fair comparisons and honest error bars"*:

1. `gemini-2.5-flash` is not a small model.
2. No tier exists that separates *matching strings* from *recovering meaning*.

This design closes both.

---

## The semantic tier already exists in committed data

Each of the 28 foundations has **two independently-worded descriptions**:

| Source | `F1T` example |
|---|---|
| TKS canon | `Core drive to merge with the divine, transcending ego. Manifests as meditation, prayer, seeking mystical experiences.` |
| Compact composition | `drive = integrating separate parts into one coherent whole; register = ideal, meaning-centered, value-level, or purpose-level` |

**Measured word overlap across all 28 cells: mean Jaccard `0.0209`, max `0.1071`, min `0.0000`.**
Several cells share *zero* words.

Matching one phrasing to the other is therefore a genuine semantic task in which **surface
controls should sit at chance by construction**. That property is itself a pre-registered check
(`S3` below): if the surface controls score well, the tier is contaminated and the run is VOID.

---

## Task

Build a `28 × 28` similarity matrix between compact descriptions and TKS descriptions, then take
top-1 in **both directions**:

- compact → TKS (`28` queries)
- TKS → compact (`28` queries)

**`n = 56` queries.** Chance top-1 = `1/28` = `0.0357`.

Secondary decompositions, which carry more power: **drive** accuracy (chance `1/7 = 0.1429`) and
**register** accuracy (chance `1/4 = 0.2500`).

## Models and representations — all frozen here, no sweeps

| Arm | Model | Layer | Rule |
|---|---|---|---|
| Primary | `EleutherAI/pythia-160m` | `6` | middle layer, `⌊12/2⌋` — a rule, not a search |
| Replication | `gpt2` | `6` | same rule, `⌊12/2⌋`; different architecture family and tokenizer |
| Depth control | both | `0` | token embeddings only — "does depth add anything" |

Representation: **mean-pooled hidden states**, cosine similarity. This matches the
representation already pre-registered in Gate 2 Attempts 2–4, so it is not a new choice made
after seeing data.

## Surface controls — the fair comparison

Computed on the **identical** item pairs:

- **char 3–5-gram TF-IDF**, cosine — mandatory per the standing char-level control rule.
- **word TF-IDF**, cosine.

`best_surface = max(char, word)`.

---

## Frozen criteria

| # | Criterion | Bar |
|---|---|---|
| `S1` | **Beats surface** | `model_top1 - best_surface_top1 >= 0.10` AND bootstrap 95% CI of the difference excludes `0` |
| `S2` | **Above chance** | permutation `p < 0.01` (`10,000` label-preserving permutations) |
| `S3` | **Tier validity** | `best_surface_top1 <= 0.15` — confirms the tier is genuinely low-overlap |
| `S4` | **No degenerate collapse** | no single foundation predicted for `> 30%` of queries |
| `S5` | **Depth contributes** *(secondary, non-gating)* | layer `6` `>` layer `0` |

Bootstrap: `10,000` iterations, percentile method, over the `56` queries. **At `n = 56` the
interval will be wide, and it will be reported at full width without rounding toward the bar.**

---

## Pre-committed consequences

- **`S3` FAILS** → `VOID_TIER_CONTAMINATED`. The two phrasings share more surface than measured
  and the tier does not test meaning. No claim, and the overlap measurement is republished.
- **`S4` FAILS** → `VOID_DEGENERATE`.
- **`S1` and `S2` PASS** → `LICENSED`, with the ceiling in the next section.
- **`S2` passes, `S1` FAILS** → `NOT_LICENSED`. The model is above chance but not above a
  surface baseline; under the standing char-level rule that is not a licensed result.
- **`S2` FAILS** → `NOT_LICENSED`. No recoverable signal at this scale.
- **Primary passes, replication (`gpt2`) fails** → licensed **for `pythia-160m` only**, with the
  replication failure reported in the same sentence as the claim.

---

## Ceiling on what a PASS licenses

> *"On `EleutherAI/pythia-160m`, mean-pooled representations at layer 6 recover the correct
> foundation from an independently-worded description of the same cell, above chance and above
> word- and character-level surface baselines computed on the same items, with a reported
> bootstrap interval at `n = 56`."*

It licenses **nothing** about: TKS versus compact superiority (no arm comparison exists in this
design), the authored scenarios (shown empty, `p = 0.3011`), larger models beyond any arm that
actually runs, or any product capability.

A PASS **would** constitute a small-model demonstration with fair comparisons and honest error
bars. Whether that satisfies Gate 2 is the owner's determination, not mine, and I will not
declare the gate closed from inside the experiment that targets it.

---

## Why this cannot manufacture a favourable result

- Both text sets are **already committed to git** and are read verbatim from the canon files.
- Layers are set by a stated rule (`⌊n_layers/2⌋`), not chosen after inspecting results.
- The representation matches what was pre-registered in earlier attempts.
- Surface controls run on identical items; `best_surface` takes the **max**, favouring the control.
- `S3` can VOID the run on the strength of the controls alone.
- The overlap statistics that motivate the tier were measured and are quoted above **before** any
  model ran, and the measurement script is committed with this file.

---

## Status

`LOCKED / COMMITTED BEFORE MODEL LOAD / NOTHING LICENSED`
