# Stage 7.2 Factor Check Report - Drive, Register, Interaction

**Date:** 2026-05-17
**Branch:** `experiment/cas-probe-pythia`
**Status:** Mixed, with strong Drive and 28-way Interaction passes.

## Plain-English Result

Stage 7.2 split the original-TKS 28-Foundation signal into three parts:

1. **Drive** - which of the 7 Foundations is active.
2. **Register** - which of the 4 Worlds/Register positions is active.
3. **Interaction** - the full 28-way Foundation/Register label.

The result is:

| Factor | Result |
|---|---|
| Drive | PASS |
| Register | Mixed / text-explained |
| Full 28-way interaction | PASS |

Plain English:

> The Drive part of the signal is strong inside Pythia. The full 28-way Foundation structure is also strong. The Register part is real as a readout, but plain text can recover it even better than the activation probe, so Register does not get the same beyond-text claim.

## What Was Tested

Input:

- `stage7_foundation_pilot_20260517.jsonl`

Activation artifact:

- `stage7_foundation_pilot_activations_20260517.npz`
- SHA-256: `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f`
- full artifact lives on RunPod only because it is about 304 MB

Previous gates required:

- Stage 7.0 status: `FOUNDATION_PROBE_RELIABLY_ABOVE_TEXT_BASELINE`
- Stage 7.1 status: `FOUNDATION_SUBSPACE_CAUSAL_FOR_PROBE_READOUT`

Locked readout:

- readout: `focus_token`
- layer: `6`

The script does not sweep layers. It uses the Stage 7.0 validation-selected layer to avoid layer shopping.

## Decision Rules

For each factor:

- activation test accuracy must beat the best text baseline by at least 5 points
- paired McNemar p must be below 0.05
- removing the factor's trained readout subspace must drop the readout to near chance
- same-rank random complement removals must not match that disruption

Metadata baselines are reported as diagnostics, not as the main pass/fail gate, because Drive/Register pair metadata can identify factors by construction in this contrast fixture.

## Drive Result

Status:

`FACTOR_READOUT_AND_ABLATION_PASS`

| Metric | Value |
|---|---:|
| chance | 0.1429 |
| activation test accuracy | 0.8907 |
| activation test macro-F1 | 0.8913 |
| best text baseline | `tfidf_char_3_5` |
| best text test accuracy | 0.6679 |
| activation lift over text | +0.2228 |
| paired p vs text | 1.13e-73 |
| best metadata baseline | `pair_focus` |
| best metadata test accuracy | 0.6667 |
| activation lift over metadata | +0.2241 |
| paired p vs metadata | 4.20e-72 |
| subspace rank | 6 |
| ablated accuracy | 0.1429 |
| disruption | 0.7479 |
| changed prediction rate | 0.8244 |
| random mean disruption | 0.0000 |
| random max disruption | 0.0000 |

Interpretation:

> Drive is the cleanest factor. Pythia hidden states recover it far better than text, and removing the Drive readout subspace drops the readout to exact chance.

## Register Result

Status:

`FACTOR_ABLATION_PASS_TEXT_GATE_FAIL`

| Metric | Value |
|---|---:|
| chance | 0.2500 |
| activation test accuracy | 0.8563 |
| activation test macro-F1 | 0.8558 |
| best text baseline | `tfidf_char_3_5` |
| best text test accuracy | 0.8971 |
| activation lift over text | -0.0408 |
| paired p vs text | 2.75e-06, in favor of text |
| best metadata baseline | `surface_pair_family_focus` |
| best metadata test accuracy | 1.0000 |
| activation lift over metadata | -0.1437 |
| paired p vs metadata | 3.57e-102, in favor of metadata |
| subspace rank | 3 |
| ablated accuracy | 0.2500 |
| disruption | 0.6063 |
| changed prediction rate | 0.7551 |
| random mean disruption | 0.0000 |
| random max disruption | 0.0000 |

Interpretation:

> Register is real inside the readout, because removing its subspace drops accuracy to exact chance. But it is also highly recoverable from the surface wording. The fixture uses different language for the four register/world positions, and the text baseline can exploit that. So Register does not prove hidden-state structure beyond text in this run.

This is not a failure of the whole Stage 7 thesis. It says Register is too visible in the current wording to serve as a beyond-text internal-structure claim.

## Full 28-Way Interaction Result

Status:

`FACTOR_READOUT_AND_ABLATION_PASS`

| Metric | Value |
|---|---:|
| chance | 0.0357 |
| activation test accuracy | 0.7857 |
| activation test macro-F1 | 0.7906 |
| best text baseline | `tfidf_char_3_5` |
| best text test accuracy | 0.4966 |
| activation lift over text | +0.2891 |
| paired p vs text | 2.66e-95 |
| best metadata baseline | `surface_pair_family_focus` |
| best metadata test accuracy | 0.6667 |
| activation lift over metadata | +0.1190 |
| paired p vs metadata | 4.38e-20 |
| subspace rank | 27 |
| ablated accuracy | 0.0357 |
| disruption | 0.7500 |
| changed prediction rate | 0.9558 |
| random mean disruption | 0.0000 |
| random max disruption | 0.0000 |

Interpretation:

> The full 28-way Foundation/Register interaction remains the strongest result. It beats text, beats metadata, and collapses to exact chance when its readout subspace is removed.

## Overall Verdict

`STAGE7_FACTOR_CHECK_MIXED`

Supported:

> Drive is readable from hidden states beyond text and causal for the Drive readout.

Supported:

> The full 28-way Foundation/Register interaction is readable from hidden states beyond text and causal for the full Foundation readout.

Not supported:

> Register is readable beyond text in this fixture.

Supported with caveat:

> Register has a real readout subspace, but the current wording makes Register too easy for text-only baselines.

## What This Means

This result is actually useful.

It says the 28-Foundation success is not just "the model noticed spiritual vs mental vs emotional vs physical wording." If that were the whole story, the Register factor would be the best claim. Instead, Register is the weakest beyond-text claim, while Drive and the full 28-way interaction are strong.

That points toward this interpretation:

> The deep signal is not merely Register/world language. The stronger internal signal is Drive plus the Drive-Register interaction.

## What This Does Not Prove

Still not proven:

- generation steering
- output control
- cross-model transfer
- closed-model interpretability
- full black-box solution

Stage 7.2 remains readout-level evidence.

## Recommended Next Step

Do **not** run Register generation hooks from this fixture. Register is text-explained here.

Next best step:

> Stage 7.3 - Drive-only generation hook or Drive-only counterfactual patching.

Why Drive:

- Drive beats text by +22.3 points.
- Drive beats metadata by +22.4 points.
- Drive ablation drops to exact chance.
- Drive has a compact rank-6 subspace.

If we test generation next, Drive is the right factor to test first.

The full 28-way interaction is also strong, but a rank-27 generation hook may be too broad and could repeat the "too much collateral damage" problem from earlier noetic generation tests.

## Stakeholder-Safe Line

> CAS split the 28-Foundation signal into Drive and Register. Drive passed cleanly: hidden states beat text by 22.3 points, and removing the Drive subspace drops the readout to chance. Register is real but text-explained in this fixture. The full 28-way Foundation signal remains strongest, beating text by 28.9 points and collapsing to chance under ablation.
