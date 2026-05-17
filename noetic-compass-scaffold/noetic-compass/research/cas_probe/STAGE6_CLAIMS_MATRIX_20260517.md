# Stage 6 Claims Matrix / Evidence Packet

**Status:** Stage 6 supports internal readout detection and readout-causal
ablation. Stage 6 does **not** currently support generated-language causality.

**Branch:** `experiment/cas-probe-pythia`

**Purpose:** lock the evidence boundary before any Stage 6.7 counterfactual
patching. This prevents the project from sliding from evidence into
test-chasing.

## Executive Summary

Plain English:

> CAS found a noetic signal inside Pythia-160M's hidden states. That signal was
> stronger than text-only baselines, and when we removed the signal the CAS
> readout collapsed to chance. But when we tried to make Pythia's generated
> language change by removing that signal, the effect did not survive matched
> random controls.

What this proves:

> CAS can detect and causally test an internal readout signal in an open model.

What this does not prove:

> CAS has shown that this signal controls the model's generated language.

Stakeholder-safe one-liner:

> CAS turns part of the black box into an inspectable readout: we can locate a
> noetic signal inside an open model, verify it beats text-only baselines, and
> remove it from the readout. The stronger claim that it controls generation is
> still unproven.

## Locked Artifacts

| Artifact | File | SHA-256 / Status |
|---|---|---|
| Locked Stage 6 dataset | `stage6_role_bound_full_20260516.jsonl` | `450086d137396cd9906f8458ab37ead041ead1842fbfa866d47326befd155710` |
| Activation capture | `stage6_role_bound_full_activations_20260516.npz` | `6641e28519eefeadc66d053c4996075d640401f6f650ef14b80435ccd57206f2`; local/pod artifact, not committed because it is >100 MB |
| Activation manifest | `stage6_role_bound_full_activations_manifest_20260516.json` | `589635cb1a0cd3d6d78ae1208a7bb3e7128375befc160733f258516cbe4d2330` |
| Stage 6.4 probe report | `stage6_role_bound_full_probe_report_20260516.json` | `51c0342c0d82db49e0a685925ba39385d988cba5cfaf2cafea39162f840ab683` |
| Stage 6.5 ablation report | `stage6_role_bound_layer5_ablation_report_20260516.json` | `3c97257906dd6fe2761f24f517ccf3798ee5bbb6e139fd8400c78beeaaf34064` |
| Stage 6.6B old-subset report | `stage6_role_bound_generation_localized_full_n30_hook_report_20260517.json` | `fd8a8f533683a2d5baeccf7e717665c3c867f98b1e2dae5296d07a7f551c07b8` |
| Stage 6.6B fresh-holdout report | `stage6_role_bound_generation_localized_fresh_n30_hook_report_20260517.json` | `f410922fb06f5c7094b9b94d950efcc197656e10c0e15bd8ef713a5d9108846f` |

## Claim Matrix

| Claim | Status | Evidence Supporting It | Evidence Blocking / Limiting It | Allowed Language |
|---|---|---|---|---|
| Stage 6 dataset is locked and class-balanced. | Supported | 3,000 rows; 60 bundles; 1,500 counterfactual pairs; 300 rows/noetic; train/val/test = 1,200/400/1,400. Dataset SHA locked above. | Dataset is synthetic and role-bound; it is not a natural web benchmark. | "The experiment uses a frozen, balanced, role-bound CAS dataset." |
| Pythia hidden states contain a role-bound noetic signal. | Supported | Stage 6.4 focus-token layer-5 probe: test accuracy `0.7393`, macro-F1 `0.7409` over locked 1,400-row test set. | A probe result alone is correlation/readout evidence, not generation causality. | "A trained probe can recover the focused noetic role from Pythia hidden states." |
| The signal beats text-only baselines. | Supported | Best validation-selected text baseline `tfidf_char_3_5`: test accuracy `0.4643`; activation lift `+0.275`; McNemar p `8.14e-50`. | Text baselines still perform above chance; the dataset has learnable surface structure. | "The activation readout is materially stronger than strong text-only baselines." |
| The result is not just focus-position metadata. | Supported | Focus-only metadata baseline stays chance: `0.100`. | Pair+focus metadata reaches `0.500` because it narrows to two candidate noetics; activation still beats it. | "The result is not explained by knowing only which role, A or B, is focused." |
| The noetic subspace is causal for the CAS readout. | Supported | Stage 6.5: removing the layer-5 noetic subspace drops readout accuracy from `0.7393` to `0.1000` chance; changed prediction rate `0.9007`; random same-rank controls mean/max disruption `0.0`; empirical p `0.0323`. | This is causality for the trained CAS readout, not direct causality for Pythia's generated text. | "Removing the noetic subspace collapses the CAS readout to chance while random removals do not." |
| The noetic subspace controls generated language under ablation. | Not supported | Stage 6.6A had a small underpowered signal; paired re-analysis p about `0.10`. | Stage 6.6B with `n_random=30` fails. Old subset: extra divergence `-0.0146`, paired p `0.8006`. Fresh holdout: extra `+0.0100`, paired p `0.2932`, below the `+0.03` floor. | "This experiment did not show generated-language causality." |
| CAS has solved the black-box problem. | Not supported | Stage 6 demonstrates a real inspectable readout channel. | It does not expose every internal cause, every neuron, or full generation control. | "CAS reduces opacity for this tested signal; it does not fully solve the black-box problem." |
| Glass House AI is validated across models. | Not tested | Pythia-160M result is a first-model internal probe study. | No OLMo/Qwen/Llama replication yet. | "This is a first open-model probe result, not a cross-model product validation." |

## Evidence Ladder

| Tier | Question | Current Answer |
|---|---|---|
| Dataset | Is the test frozen and auditable? | Yes. |
| Readout | Can CAS recover the label from hidden states? | Yes. |
| Baseline | Is it better than text-only classifiers? | Yes. |
| Readout causality | Does removing the subspace break the CAS readout? | Yes. |
| Generation causality | Does removing the subspace reliably change generated text more than random controls? | No. |
| Counterfactual routing | Does patching a matched donor focus-token activation route generated text toward the donor? | No. |
| Cross-model generality | Does this hold across open models? | Not tested. |

## Reviewer Playbook

1. Verify the dataset SHA:
   `450086d137396cd9906f8458ab37ead041ead1842fbfa866d47326befd155710`.
2. Verify the activation artifact SHA if the local/pod `.npz` is available:
   `6641e28519eefeadc66d053c4996075d640401f6f650ef14b80435ccd57206f2`.
3. Inspect Stage 6.4:
   `STAGE6_FULL_PROBE_REPORT_20260516.md`.
4. Inspect Stage 6.5:
   `STAGE6_LAYER5_ABLATION_REPORT_20260516.md`.
5. Inspect Stage 6.6B:
   `STAGE6_GENERATION_CLOSURE_REPORT_20260517.md`.
6. Confirm the claim boundary:
   internal readout and readout-causality are supported; generated-language
   causality is not.

## Stakeholder Language

Use this:

> "In an open model, CAS can find a structured internal signal, test that it
> beats text-only explanations, and remove it from the CAS readout. That is a
> real step toward transparent AI. We are not claiming that this experiment
> proves control over the model's generated language."

Do not use this:

> "CAS reads the model's thoughts."

Do not use this:

> "CAS solved the black box."

Do not use this:

> "CAS can control Pythia's language generation."

## Stage 6.7 Pre-Registration Boundary

Stage 6.7 is allowed as a **different causal test**, not as a rescue of Stage
6.6.

Plain English:

> Instead of deleting noetic information, Stage 6.7 will swap it. If a prompt is
> focused on role A, patch in the focus-token activation from a matched role B
> counterfactual and test whether the continuation shifts toward role B.

Pre-registered setup:

- Use the locked Stage 6 full fixture.
- Start with focus-token layer 5 because Stage 6.4/6.5 use that layer.
- Use matched counterfactual pairs from the same sentence bundle.
- Patch focus-token hidden state from donor role into receiver role.
- Compare against matched random donor patches.
- Score generated continuations with the same paired discipline used in
  Stage 6.6B.

Pass requires:

- no-hook reproducibility remains exact
- patched continuations shift more than random donor controls
- paired p <= `0.05`
- effect survives the fresh-holdout setting, not only the old 20-row subset
- semantic review shows directionally meaningful movement, not only token churn

If Stage 6.7 passes:

> CAS has evidence that role-bound noetic information can be routed through
> generation under counterfactual patching.

If Stage 6.7 fails:

> Pythia carries a CAS-readable noetic signal and the readout depends on it,
> but this test did not show that the signal routes generation.

Stage 6.7 result, 2026-05-17:

> Failed. Fresh confirmatory run used 40 receivers, 120 cases, and 30 random
> donor controls. True patch directional score was `-0.0729`; random donor
> mean was `-0.0646`; extra directional score was `-0.0083`; empirical p was
> `0.6774`.

## Current Bottom Line

The honest Stage 6 result is still valuable:

> CAS does not open the whole black box. It opens a verified window: a specific
> internal noetic readout can be found, measured above baselines, and causally
> removed from the readout. The tested generation routes did not pass.
