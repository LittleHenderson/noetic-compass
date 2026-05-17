# Stage 7.3 Drive Generation Hook Report

**Date:** 2026-05-17
**Branch:** `experiment/cas-probe-pythia`
**Status:** Negative for generated-language effect above random controls.

## Plain-English Result

Stage 7.3 tested the cleanest factor from Stage 7.2: **Drive**.

The question was:

> If CAS removes the Drive signal at the focus token while Pythia generates text, does Pythia's continuation change more than it changes under same-size random removals?

Answer:

> No.

The Drive readout is real and causal for the CAS readout, but this localized generation hook did not show that removing Drive changes Pythia's generated language more than random controls.

## What Was Tested

Input:

- `stage7_foundation_pilot_20260517.jsonl`

Activation artifact:

- `stage7_foundation_pilot_activations_20260517.npz`
- SHA-256: `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f`
- full artifact lives on RunPod only because it is about 304 MB

Stage 7.2 gate:

- Drive status required: `FACTOR_READOUT_AND_ABLATION_PASS`

Hook:

- factor: Drive
- readout: `focus_token`
- layer: 6
- hook block index: 5
- hook scope: the terminal `Focus: A/B` token only
- subspace rank: 6

Selection:

- test split only
- only `same_register_drive_cycle_*` rows, so the selected A/B pair actually contrasts Drive
- 4 rows per Drive
- 7 Drives
- 28 selected rows total
- 3 forced continuation templates
- 84 generated cases

Prompt templates:

- `In other words,`
- `The focused role means`
- `A concise explanation is`

Controls:

- no-hook reproducibility control
- 30 same-rank random complement removals
- paired case-level sign test

## Main Numbers

| Metric | Value |
|---|---:|
| selected rows | 28 |
| generated cases | 84 |
| Drive subspace rank | 6 |
| no-hook exact reproducibility | 1.0000 |
| Drive-removal mean token match | 0.9301 |
| random-removal mean token match | 0.8863 |
| Drive extra divergence vs random | -0.0438 |
| Drive first-step KL | 0.00729 |
| random first-step KL | 0.00757 |
| empirical p, random token match <= Drive | 1.0000 |
| paired case sign p | 1.0000 |

Token-match interpretation:

- Lower token match means more disruption.
- Drive removal token match: `0.9301`
- Random removal token match: `0.8863`

Random removals disrupted the continuation more than Drive removal did.

## First-Token Behavior

Drive removal barely changed the first generated token:

| Metric | Value |
|---|---:|
| first-step top-1 match rate | 0.9881 |
| exact continuation match rate | 0.8333 |

Baseline first-token distribution:

| Token | Count |
|---|---:|
| `the` | 40 |
| `that` | 28 |
| `given` | 11 |
| `provided` | 4 |
| `a` | 1 |

Drive-ablated first-token distribution:

| Token | Count |
|---|---:|
| `the` | 39 |
| `that` | 28 |
| `given` | 11 |
| `provided` | 4 |
| `a` | 2 |

The first-token distribution is basically unchanged.

## Template Breakdown

| Template | Cases | Mean Token Match | Exact Match | First-Step Match |
|---|---:|---:|---:|---:|
| `In other words,` | 28 | 0.9777 | 0.8929 | 1.0000 |
| `The focused role means` | 28 | 0.8929 | 0.7500 | 1.0000 |
| `A concise explanation is` | 28 | 0.9196 | 0.8571 | 0.9643 |

The strongest visible disruption is in `The focused role means`, but it still does not beat the random-control distribution overall.

## Verdict

`DRIVE_LOCALIZED_GENERATION_EFFECT_NOT_ABOVE_RANDOM_CONTROL`

Supported:

> Drive is readable from hidden states and causal for the Drive readout.

Not supported:

> Drive removal changes generated language more than same-rank random removals.

Not supported:

> CAS can steer Pythia's generated language through Drive.

## What This Means

This does **not** invalidate Stage 7.0, Stage 7.1, or Stage 7.2.

Those results remain:

- 28-way Foundation readout beats text and metadata.
- 28-way Foundation readout collapses to chance under subspace removal.
- Drive readout beats text and metadata.
- Drive readout collapses to chance under subspace removal.

Stage 7.3 says something narrower:

> The readout-active Drive subspace is not routed into Pythia's greedy generated language by this focus-token-localized removal method.

Plain English:

> CAS can find and remove the Drive signal from the internal readout, but that does not mean the same removal controls what Pythia says next.

## Honest Interpretation

The black-box claim boundary stays the same:

CAS has strong evidence for internal readout and readout-causal intervention in Pythia-160M.

CAS does **not** yet have evidence for generated-language control in Pythia-160M.

This is still meaningful. A model can carry a readable internal structure without routing that structure directly into next-token generation in a way our current hook can isolate.

## Recommended Next Step

Stop trying more generation hooks for Stage 7 until the claim matrix is updated.

Recommended next:

> Stage 7 claims matrix refresh.

The matrix should separate:

- hidden-state readout
- readout-causal ablation
- factorization evidence
- generated-language causality
- semantic steering

Current evidence supports the first three. It does not support the last two.

After that, if another experiment is justified, the best one would be a preregistered Drive counterfactual patching test. But that should not run until the Stage 7 claim boundary is locked.

## Stakeholder-Safe Line

> CAS found a strong Drive signal inside Pythia and proved the CAS readout depends on it. But removing that Drive signal at generation time did not change Pythia's text more than random controls. So the honest claim is internal readout and readout-causal evidence, not language steering.
