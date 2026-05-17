# Stage 7.1 Foundation Readout Ablation Report

**Date:** 2026-05-17
**Branch:** `experiment/cas-probe-pythia`
**Status:** PASS for readout-causal evidence. No generation-control claim.

## Plain-English Result

Stage 7.0 showed that Pythia-160M hidden states carry a strong original-TKS 28-Foundation signal.

Stage 7.1 asked the next question:

> If we remove the exact hidden-state direction that the 28-Foundation probe uses, does the Foundation readout collapse?

Yes.

The readout accuracy drops from **78.6%** to **3.57%**, which is exact chance for 28 balanced classes. The model's probe predictions collapse to one class (`F6A`) after the Foundation subspace is removed.

Thirty same-rank random removals do not change the readout at all:

- random mean disruption: `0.0`
- random max disruption: `0.0`
- empirical p: `0.0323`

That means the disruption is specific to the trained Foundation readout subspace. Removing random same-size directions does not break the readout.

## What Was Tested

Input:

- `stage7_foundation_pilot_20260517.jsonl`

Activation artifact:

- `stage7_foundation_pilot_activations_20260517.npz`
- SHA-256: `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f`
- full artifact lives on RunPod only because it is about 304 MB

Stage 7.0 report:

- `stage7_foundation_pilot_probe_report_20260517.json`

Stage 7.1 report:

- `stage7_foundation_layer6_ablation_report_20260517.json`

Locked readout:

- readout: `focus_token`
- layer: `6`
- labels: 28 original-TKS Foundation/Register labels (`F1T..F7E`)

The script refuses to run if the Stage 7.0 report does not have the validation-selected headline `focus_token` layer 6 or if Stage 7.0 did not pass its text-baseline gate.

## Method

1. Retrain the same logistic-regression Foundation probe on the locked train split.
2. Convert the learned standardized classifier weights back into raw activation space.
3. Use SVD to extract the trained Foundation readout subspace.
4. Remove that subspace from locked-test activations.
5. Re-run the same trained probe on the ablated activations.
6. Compare against 30 same-rank random orthogonal removals from the complement of the Foundation subspace.

This tests the readout mechanism itself.

It does **not** test whether Pythia's generated language changes.

## Metrics

| Metric | Value |
|---|---:|
| baseline test accuracy | 0.7857 |
| Foundation-ablated test accuracy | 0.0357 |
| chance accuracy | 0.0357 |
| disruption | 0.7500 |
| changed prediction rate | 0.9558 |
| subspace rank | 27 |
| random controls | 30 |
| random mean disruption | 0.0000 |
| random max disruption | 0.0000 |
| random min disruption | 0.0000 |
| empirical p, random >= Foundation | 0.0323 |
| max abs random x Foundation cosine | 2.47e-16 |

Prediction distribution after Foundation ablation:

| Predicted Label | Count |
|---|---:|
| F6A | 2,352 |

Because the locked test set is perfectly balanced across 28 labels, predicting one class for every row gives exact chance accuracy:

> 84 correct / 2,352 = 0.0357

## Why Random Controls Are Zero

The random controls are deliberately sampled from the orthogonal complement of the trained Foundation readout subspace.

For this readout-level test, that is the point:

- If the implementation is correct, removing random complement directions should leave the linear readout unchanged.
- Removing the trained Foundation subspace should destroy the readout.

That is exactly what happened.

This does not mean random controls are unnecessary. They prove the collapse is not caused by generic same-rank damage to the activation vector. It is specific to the trained Foundation readout subspace.

## Verdict

`FOUNDATION_SUBSPACE_CAUSAL_FOR_PROBE_READOUT`

Supported claim:

> In Pythia-160M, the Stage 7 original-TKS 28-Foundation readout depends on a specific hidden-state subspace at focus-token layer 6. Removing that subspace collapses the Foundation readout to chance; same-rank random complement removals do not.

## What This Supports

Supported:

> The 28-Foundation signal is not just detectable. It is load-bearing for the CAS Foundation readout.

Supported:

> The original-TKS 28-Foundation axis is stronger than the earlier raw noetic route for internal readout work in Pythia-160M.

Supported:

> Stage 7 now has the same two-part evidence pattern Stage 6 had, but stronger: readout above text baseline, plus readout-causal ablation.

## What This Does Not Support Yet

Not supported yet:

> CAS controls Pythia's generated language through the 28 Foundations.

Not supported yet:

> Removing the 28-Foundation subspace changes Pythia's generated answers in a Foundation-specific way.

Not supported yet:

> CAS solved the black-box problem.

Not supported yet:

> The result transfers to larger Pythia, OLMo, Qwen, Llama, Claude, GPT, or any closed model.

## Honest Interpretation

This is a strong mechanistic-readout result, not a language-steering result.

Plain English:

> CAS found a 28-Foundation signal inside Pythia's hidden states. When that exact signal is removed, CAS can no longer read the Foundation structure. When random directions of the same size are removed, the readout survives. That makes the Foundation signal real and load-bearing for the readout.

This is stronger than "the signal is merely associated with hidden states." It shows the trained readout actually depends on that subspace.

It is still weaker than "the subspace controls what Pythia says." That remains a separate generation-causality test.

## Recommended Next Step

Do not jump straight to generation steering yet.

Next best step:

> Stage 7.2 - per-axis factor check.

Because the 28 labels are factorized as `Drive x Register`, test whether the Foundation readout decomposes into:

- a 7-way Drive readout
- a 4-way Register readout
- and their 28-way interaction

If Drive and Register both pass text baselines and readout ablation separately, then a later generation test can be more targeted:

- remove only Drive
- remove only Register
- remove the interaction

That would tell us what part of the Foundation signal is doing the work before we spend time on language generation hooks.

Generation tests should come after that.

## Stakeholder-Safe Line

> CAS found a 28-Foundation signal inside an open model's hidden states. The signal is not just readable: removing the exact subspace collapses the CAS Foundation readout to chance, while same-size random removals do nothing. This is strong evidence for a real internal readout channel. It is not yet evidence that CAS can steer the model's generated language.
