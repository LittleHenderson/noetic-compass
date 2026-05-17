# Stage 11 Expression Grammar Shape Gates

Date: 2026-05-17

Branch: `experiment/cas-probe-pythia`

## Purpose

Stage 11 tests the next ladder step after Stage 10's isolated five-operator result.

Stage 10 showed that standalone operator classes are highly readable and readout-causal, but ceiling-limited against text. Stage 11 therefore asks a harder compositional question:

> Does Pythia-160M encode the overall CAS expression grammar shape when the operator must be understood together with operand/structure roles?

This is not a full equation/formula test yet. It is expression-shape classification.

## Labels

The target labels are the existing Path D grammar categories already used in the repo:

| Internal label | Plain-English fixture meaning |
|---|---|
| `state_literal` | one marked condition stands alone |
| `binary_composition` | two marked conditions are linked into one relation |
| `let_binding` | a temporary name is introduced and later used |
| `recipe` | a desired outcome is specified by weighted contributors |
| `rpm_chain` | a starting point advances through staged checkpoints |
| `fractal_sequence` | a repeated pattern of moves is applied in order |
| `cross_register_omega` | one named outcome is viewed across different modes |
| `meta_logic_relation` | a rule describes how another rule relates or follows |
| `inversion` | the usual direction is turned around |
| `diagram_export` | a named cluster is packaged for outside viewing |

Model-facing text must not contain the internal labels, CAS/TKS, grammar-category names, CAS notation, or formula symbols.

## Pre-Registered Data Shape

- Model: frozen `EleutherAI/pythia-160m`
- Labels: ten expression grammar shapes above
- Fixture style: role-bound same-sentence counterfactuals
- Pair schedule: 15 balanced pairs, each class appears in exactly three pairs
- Split source: locked Stage 6 lexical bundles
- Paraphrase families:
  - train/val: 4 core families
  - test: 4 core + 3 held-out families

Expected size:

- Train: `30 bundles x 15 pairs x 4 families x 2 focuses = 3,600`
- Val: `10 bundles x 15 pairs x 4 families x 2 focuses = 1,200`
- Test: `20 bundles x 15 pairs x 7 families x 2 focuses = 4,200`
- Total: `9,000`

## Claim-Bearing Gates

Stage 11 is a pass only if both readout and ablation gates pass.

### Readout Gate

Validation-selected activation headline:

- Train all text baselines on train split
- Train all metadata baselines on train split
- Train all activation readouts across `focus_token`, `final_token`, and `mean_over_seq_len`
- Select headline by validation accuracy, not test accuracy
- Report locked-test performance once

Pass requirements:

- Activation test accuracy >= `0.25` against 10-class chance `0.10`
- Activation test accuracy minus best validation-selected text baseline >= `+0.05`
- McNemar exact binomial p vs best text baseline < `0.05`

### Readout-Subspace Ablation Gate

Run only on the validation-selected headline readout/layer.

Pass requirements:

- Targeted expression-shape subspace removal drops test readout accuracy to <= `0.15` (`chance + 0.05`)
- Thirty same-rank random complement removals do not match targeted disruption
- One-sided empirical p for `random_disruption >= targeted_disruption` < `0.05`

## Verdict Tiers

- `STAGE11_EXPRESSION_SHAPES_FULL_PASS`: readout gate and ablation gate both pass
- `STAGE11_EXPRESSION_SHAPES_READOUT_ONLY`: readout passes but ablation does not
- `STAGE11_EXPRESSION_SHAPES_GREY`: activation is above text numerically but misses a statistical gate
- `STAGE11_EXPRESSION_SHAPES_NULL`: no reliable beyond-text expression-shape readout

## Boundary

Stage 11 is not full equation/formula understanding. It tests expression grammar-shape readout and readout-subspace causality only. It does not prove raw-symbol parsing, compiler execution, visible generation control, or cross-model generality.

If Stage 11 passes cleanly, the next ladder step is Stage 12 equations/formulas with compiler-validated structures.
