# PRE-REGISTRATION — `SMALL-MODEL-RECOVERY-v1`

**Committed BEFORE any model is loaded.**
**Date:** 2026-07-27
**Gate 2 status:** OPEN at `0.38`

---

## The one remaining gap

Gate 2 reads: *"The scoring actually works **on a small model**, with fair comparisons and honest
error bars."*

Three of those four clauses are now demonstrated. `SPEC-AUTHORED-SCENARIOS-v1` (`59e9044c`)
produced `0.9167` against chance `0.0357`, with five pre-registered criteria, five baselines, a
post-hoc control built specifically to attack the result, and a disclosed leak. What it did not do
is use a small model — the judge was `models/gemini-2.5-flash`.

**Every prior small-model attempt in this campaign asked a small model to find signal that was not
in the items.** The positive control proved the old scenarios were empty (`p = 0.3011`). This is
the first time a small model will be pointed at a dataset where an independent judge has confirmed
the signal is present.

---

## Why the design changes from 28-way to axis recovery

`84` items across `28` classes is `3` per class — far too few to fit an honest probe. Attempting
28-way probing at that density would produce a number driven by fold luck, which is the split
artifact already documented in this campaign (`+0.0375` margin whose seed-inclusive mean was
`-0.0094`).

The axes have adequate density:

| Target | Classes | Items/class | Chance |
|---|---|---|---|
| **drive** | `7` | `12` | `0.1429` |
| **World** | `4` | `21` | `0.2500` |
| foundation | `28` | `3` | `0.0357` |

**Drive recovery is the primary endpoint.** It is also the axis the judge recovered *perfectly*
(`84/84`) and the one with **no known leak** — the descriptor-keyed char baseline reached only
`0.2738` there. The World axis carries a disclosed contamination (`56%` of scenarios name the
World outright) and is therefore **secondary and flagged**.

## Grouping — the honest effective sample size

The three scenarios for a given foundation were generated in **one call from one plan** and are
correlated. Folds are therefore grouped by **foundation**, never by item.

- `GroupKFold`, `4` folds, groups = the `28` foundations.
- Each fold trains on `21` foundations and tests on `7` entirely unseen ones.
- **Honest effective `n` = `28` groups**, not `84` rows. This is reported as the sample size.

## Model and representation — frozen, no sweeps

| Arm | Model | Layer | Rule |
|---|---|---|---|
| Primary | `EleutherAI/pythia-160m` | `6` | middle layer, `⌊12/2⌋` |
| Replication | `gpt2` | `6` | same rule, different architecture family |
| Depth control | both | `0` | token embeddings only |

Mean-pooled hidden states, then a logistic-regression probe under the grouped CV above. This
representation matches Gate 2 Attempts 2–4 and is not a new choice made after seeing data.

## Fair comparison — baselines get the identical treatment

Each runs through **the same probe and the same grouped folds**:

- char 3–5-gram TF-IDF
- word TF-IDF
- random (analytic) and majority-class

Baselines are fitted **inside each training fold only**. They retain full access to every lexical
channel including the disclosed World leak — the comparison is not made easy for the model.

---

## Frozen criteria

| # | Criterion | Bar |
|---|---|---|
| `G1` | **Drive above chance** | drive accuracy `> 0.1429`, permutation `p < 0.01` (`10,000` label permutations **within groups**) |
| `G2` | **Drive beats best lexical** | `drive_acc - best_lexical >= 0.10` AND bootstrap 95% CI over the `28` groups excludes `0` |
| `G3` | **No degenerate collapse** | no single class predicted for `> 40%` of items (7-way) |
| `G4` | **Honest error bars** | bootstrap CI over groups reported at **full width**, unrounded, whatever it shows |
| `G5` | **World** *(secondary, flagged)* | world accuracy `> 0.2500` — reported **with the `56%` leak disclosure attached, never alone** |

---

## Pre-committed consequences

- **`G1` and `G2` PASS** → `SMALL_MODEL_RECOVERY_LICENSED`. The scoring recovers CAS drive
  structure on a small model, above lexical baselines on identical items, with honest error bars
  at `n = 28` groups. **This is the Gate 2 demonstration** on its own wording — though the gate
  determination is the owner's, not mine.
- **`G1` passes, `G2` FAILS** → `NOT_LICENSED_LEXICAL`. Above chance but not above a bag of
  characters. Under the standing char-level rule this licenses nothing.
- **`G1` FAILS** → `NOT_LICENSED`. A `160M` model does not recover the structure from these items
  by this method. This would **NOT** overturn `59e9044c` — the signal is independently confirmed
  present; it would mean *this* representation at *this* scale cannot reach it, and a different
  readout is required.
- **`G3` FAILS** → `VOID_DEGENERATE`.
- **Primary passes, `gpt2` replication fails** → licensed for `pythia-160m` only, with the
  replication failure stated in the same sentence.

## Ceiling on a PASS

> *"On `EleutherAI/pythia-160m`, mean-pooled layer-6 representations support recovery of the CAS
> drive axis from spec-authored scenarios above chance and above character- and word-level lexical
> baselines under foundation-grouped cross-validation, at an honest effective sample size of `28`
> groups."*

Licenses nothing about: the World axis as a clean measurement, TKS vs CAS quality, the 28-way
task, human performance, or product capability.

## Why this cannot manufacture a favourable result

- Items are **already committed to git** (`59e9044c`) and are read verbatim. No new authoring.
- Layers set by a stated rule, not a search.
- Baselines share the probe, the folds, and full access to the disclosed leak.
- Folds are grouped by foundation, so no scenario's siblings can appear in its training set.
- The primary axis is the one **without** the known leak; the leaked axis is secondary and flagged.
- `G4` requires the interval be published at full width regardless of what it shows.

## Status

`LOCKED / COMMITTED BEFORE MODEL LOAD / NOTHING LICENSED`
