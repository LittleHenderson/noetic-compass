# Stage 10 Five Operator Gates

Date: 2026-05-17

Branch: `experiment/cas-probe-pythia`

## Purpose

Stage 10 tests the next compositional layer after the Stage 9 original-TKS 40 Elements pass.

Stage 9 asked whether Pythia-160M hidden states encode CAS/TKS slots:

- Domain/World
- Noetic
- Full 40-way Element interaction

Stage 10 asks whether Pythia-160M hidden states encode the five CAS generative operations that move between slots:

| Internal label | CAS symbol | Plain-English function |
|---|---:|---|
| `multiply_integrate` | `x` | parts become one working whole |
| `divide_ratio` | `/` | one thing is measured against another |
| `compose_sequence` | `o` | one step's result becomes the next step's starting point |
| `add_copresence` | `+` | distinct things stay present together without merging |
| `subtract_remove` | `-` | one thing is taken out and the remainder changes |

The model-facing fixture must not expose the literal symbols or framework labels. Metadata may keep them for audit.

## Pre-Registered Data Shape

- Model: frozen `EleutherAI/pythia-160m`
- Labels: five operators listed above
- Fixture style: role-bound same-sentence counterfactuals
- Each row includes two candidate roles in one sentence plus `Focus: A` or `Focus: B`
- All unordered operator pairs are used
- Train/val/test splits inherit the locked Stage 6 bundle splits
- Test split includes extra paraphrase families not present in train/val

## Claim-Bearing Gates

Stage 10 is a pass only if both readout and ablation gates pass.

### Readout Gate

Validation-selected activation headline:

- Train all text baselines on train split
- Train all metadata baselines on train split
- Train all activation readouts across `focus_token`, `final_token`, and `mean_over_seq_len`
- Select headline by validation accuracy, not test accuracy
- Report locked-test performance once

Pass requirements:

- Activation test accuracy >= `0.35` against 5-class chance `0.20`
- Activation test accuracy minus best validation-selected text baseline >= `+0.05`
- McNemar exact binomial p vs best text baseline < `0.05`

### Readout-Subspace Ablation Gate

Run only on the validation-selected headline readout/layer.

Pass requirements:

- Targeted operator-subspace removal drops test readout accuracy to <= `0.25` (`chance + 0.05`)
- Thirty same-rank random complement removals do not match targeted disruption
- One-sided empirical p for `random_disruption >= targeted_disruption` < `0.05`

## Verdict Tiers

- `STAGE10_OPERATORS_FULL_PASS`: readout gate and ablation gate both pass
- `STAGE10_OPERATORS_READOUT_ONLY`: readout passes but ablation does not
- `STAGE10_OPERATORS_GREY`: activation is above text numerically but misses a statistical gate
- `STAGE10_OPERATORS_NULL`: no reliable beyond-text operator readout

## Boundary

Stage 10 is not a full-expression, full-equation, or visible-generation test. A pass means the five operator classes are recoverable from hidden states beyond text baselines and causal for the trained readout. It does not prove formula parsing, raw-symbol understanding, or generation steering.

If Stage 10 passes cleanly, the next ladder step is Stage 11 full expression grammar shapes.
