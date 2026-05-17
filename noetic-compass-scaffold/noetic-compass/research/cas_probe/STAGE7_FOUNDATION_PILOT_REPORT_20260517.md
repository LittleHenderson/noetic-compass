# Stage 7 Foundation Pilot Report - Original TKS 28 Foundations

**Date:** 2026-05-17
**Branch:** `experiment/cas-probe-pythia`
**Status:** PASS for discriminative hidden-state readout. No generation-control claim.

## Plain-English Result

This run tested whether Pythia-160M's internal activations carry the original TKS 28-Foundation structure better than plain text clues do.

They do.

The best activation probe reads the 28 Foundation labels from Pythia's hidden states at **78.6% locked-test accuracy**. The best text-only baseline reaches **49.7%**. The activation readout beats text by **+28.9 percentage points**, with paired McNemar p = **2.66e-95**.

It also beats the strongest surface-metadata baseline by **+11.9 percentage points**, with paired p = **4.38e-20**.

This means the 28-Foundation structure is not only recoverable from surface wording. In this role-bound pilot, Pythia's hidden states contain a stronger signal than the outside text baseline can explain.

## What Was Tested

Stage 7 tests the original TKS "28 Foundations" as:

> 7 Foundations x 4 Worlds = 28 positions

For CAS v7.5 this is mapped as:

> 7 Drives x 4 Registers = `F1T..F7E`

This is **not** Drive x Domain. The four positions are Register / World positions:

- `T` = high-abstraction / spiritual-world position
- `A` = analytical / mental-world position
- `f` = affective / emotional-world position
- `E` = embodied / physical-world position

The mapping source is:

- `docs/reference/tks_28_foundations_translation_key.md`
- local user-supplied source PDF: `C:\Users\wakil\Downloads\Everthing-Tootra-TKS\28 fOUNDATIONS 1.0.pdf`

## Preflight Before The Pilot

Before the full pilot, Stage 7 preflight checked three things:

1. **Axis confirmation:** confirmed 28 means original TKS seven foundations x four worlds/registers, not Drive x Domain.
2. **Lacunarity-style retrospective:** re-read the noetic negative result through a deterministic gap-map. It flags `^3` and `^5` as wrong-direction slots, but not uniquely; `^1`, `^4`, and `^6` are also weak.
3. **Fractal trajectory check:** existing Stage 3.2 and fresh Stage 6.6B ablation trajectories classify as `oscillatory`, while the older 20-row Stage 6.6B subset classifies as `stabilizing`.

Interpretation:

> CAS's own diagnostics partly explain why the 10-noetic generation route was messy: the noetic signal had gaps and the stronger trajectories were oscillatory, not cleanly stabilizing. That made the more factorized 28-Foundation axis worth testing.

See `STAGE7_PREFLIGHT_DIAGNOSTICS_20260517.md`.

Important boundary: the preflight lacunarity check is deterministic over saved Pythia evidence. It is not the trained neural `LacunarityHead`, because that head is meaningful only with trained CAS Native weights.

## Fixture

File:

- `stage7_foundation_pilot_20260517.jsonl`

Shape:

- records: 4,368
- labels: 28 (`F1T..F7E`)
- records per label: 156
- split:
  - train: 1,344
  - validation: 672
  - locked test: 2,352

Design:

- same-drive register contrasts
- same-register drive-cycle contrasts
- each pair gets two focused rows
- prompt text never contains the literal label, drive name, register name, or CAS notation

Validation:

- `stage7_foundation_pilot_validation_20260517.json`
- errors: 0
- warnings: 0

Fixture SHA-256:

`3e4a1aca9f168a190116578b0b4fdb5bab633232ba06902039b233e589121250`

## Activation Capture

Model:

- Pythia-160M

Captured readouts:

- focus token
- final token
- mean over sequence length

Captured shape:

- records x layers x hidden_dim
- 4,368 x 13 x 768

Full activation artifact:

- `stage7_foundation_pilot_activations_20260517.npz`
- SHA-256: `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f`
- Size: about 304 MB
- Location: RunPod only; not committed because it is too large for normal GitHub handling.

Committed provenance:

- `stage7_foundation_pilot_activations_manifest_20260517.json`

## Evaluation

Report:

- `stage7_foundation_pilot_probe_report_20260517.json`

Evaluator note:

- Initial full eval exposed a real reporting bug: exact McNemar overflowed when discordant pairs were large (`n=1148`).
- The evaluator was patched to use a log-space exact binomial calculation.
- The full report was rerun after the patch and completed cleanly.

Elapsed evaluation time:

- 1,055.0 seconds

Status:

`FOUNDATION_PROBE_RELIABLY_ABOVE_TEXT_BASELINE`

## Headline Numbers

Validation-selected activation headline:

| Readout | Layer | Val Acc | Test Acc | Test Macro-F1 |
|---|---:|---:|---:|---:|
| focus_token | 6 | 0.9985 | 0.7857 | 0.7906 |

Other validation-selected readouts:

| Readout | Layer | Val Acc | Test Acc | Test Macro-F1 |
|---|---:|---:|---:|---:|
| final_token | 6 | 0.9970 | 0.7764 | 0.7756 |
| mean_over_seq_len | 5 | 0.7619 | 0.5825 | 0.5803 |

Text baselines:

| Baseline | Val Acc | Test Acc | Test Macro-F1 |
|---|---:|---:|---:|
| tfidf_char_3_5 | 0.5119 | 0.4966 | 0.4801 |
| tfidf_word_1_2 | 0.5000 | 0.4524 | 0.4255 |
| count_vector_word_1_2 | 0.5000 | 0.4188 | 0.3911 |
| stratified_dummy | 0.0313 | 0.0391 | 0.0391 |
| majority | 0.0357 | 0.0357 | 0.0025 |

Metadata baselines:

| Baseline | Val Acc | Test Acc |
|---|---:|---:|
| surface_pair_family_focus | 0.6667 | 0.6667 |
| pair_focus | 0.6667 | 0.6667 |
| focus_only | 0.0476 | 0.0476 |
| family_focus | 0.0476 | 0.0476 |

Paired activation vs best text baseline:

- activation-only correct: 914
- text-only correct: 234
- discordant pairs: 1,148
- McNemar exact p: `2.6557483981655295e-95`
- lift: `+0.2891156462585034`

Paired activation vs best metadata baseline:

- activation-only correct: 609
- metadata-only correct: 329
- discordant pairs: 938
- McNemar exact p: `4.3820010365889715e-20`
- lift: `+0.11904761904761907`

## What This Supports

Supported:

> In Pythia-160M, the original-TKS 28-Foundation labels are recoverable from hidden states far better than from plain text alone in this locked pilot.

Supported:

> The 28-Foundation structure is a stronger discriminative readout than the earlier noetic-only route because it is more factorized: Drive x Register instead of one entangled 10-way axis.

Supported:

> The Stage 7 axis is now a better candidate than raw noetics for the next causal readout-ablation test.

## What This Does Not Support Yet

Not supported yet:

> CAS controls Pythia's generated language through the 28 Foundations.

Not supported yet:

> The 28-Foundation subspace is causally load-bearing for generation.

Not supported yet:

> CAS solved the black-box problem.

Not supported yet:

> The result transfers to larger Pythia, OLMo, Qwen, Llama, Claude, GPT, or any closed model.

## Honest Interpretation

This is a strong pass, but it is the same category of evidence as Stage 6.4: discriminative internal readout.

The difference is that Stage 7 is much cleaner:

- 28 classes instead of 10
- balanced label distribution
- strong text-baseline defeat
- strong metadata-baseline defeat
- a factorized axis with Drive x Register structure
- full locked-test evaluation, not a smoke

Plain English:

> The model's hidden states know more about the Foundation structure than the words on the page reveal. That is a serious interpretability signal. The next question is whether removing that Foundation subspace breaks the Foundation readout the way Stage 6.5 did for noetics.

## Recommended Next Step

Run Stage 7.1:

> 28-Foundation readout-subspace ablation with same-rank random controls.

This should mirror the discipline of Stage 6.5:

- use the validation-selected `focus_token` layer 6 readout
- remove the trained 28-class Foundation readout subspace
- measure readout accuracy drop on the locked test set
- compare against same-rank random orthogonal removals
- require the Foundation removal to outperform random controls

Do **not** jump to generation steering yet. First prove the Foundation subspace is causal for the Foundation readout.

## Stakeholder-Safe Line

> CAS tested the original 28 Foundations inside an open model. The hidden-state probe read those Foundation labels at 78.6% accuracy, beating the best text-only baseline by 28.9 points and the strongest surface-metadata baseline by 11.9 points. This is strong evidence that the 28-Foundation structure is present in the model's internal activity. It is not yet evidence that CAS can steer the model's generated language.
