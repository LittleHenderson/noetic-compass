# Stage 12 Equations And Formulas Gates

Date: 2026-05-17

Branch: `experiment/cas-probe-pythia`

## Purpose

Stage 12 tests the next ladder step after Stage 11 expression grammar shapes.

Stage 11 showed that Pythia-160M hidden states can read out broad CAS
expression grammar shapes. Stage 12 asks a harder question:

> Does Pythia-160M encode the family of a full compiler-validated CAS
> equation or formula when the model-facing prompt describes the formula's
> functional role without showing raw CAS notation?

This stage is deliberately not a raw-symbol parsing test. Each row carries a
real compiler-validated CAS expression in metadata, but the model-facing
English does not contain CAS notation, formula symbols, framework names, or the
internal class names. A later stage can test raw formula strings directly.

## Labels

The target labels are ten compiler-supported formula/equation families:

| Internal label | Plain-English fixture meaning |
|---|---|
| `relation_dependency` | one condition points forward to a later dependent condition |
| `typed_program` | a named value and typed reusable action are declared, then used |
| `production_recipe` | a named outcome is built from weighted requirements |
| `yield_query` | a request asks for expected, actual, or efficiency value |
| `state_vector` | one profile records several weighted activations |
| `emergent_register_assignment` | several modes of one pattern fuse into a named result |
| `membership_assertion` | one item is checked for belonging inside a collection |
| `cardinality_assertion` | a collection is checked against an exact count |
| `set_operation_formula` | finite collections are combined or overlapped |
| `cover_partition_formula` | collections are checked for complete reach or clean separation |

Every row must include:

- `cas_formula`: the actual CAS expression
- `compiler.valid == true`
- `compiler.result_kind`: the compiler result family
- no model-facing leakage of CAS/TKS labels, raw symbols, or internal class names

## Pre-Registered Data Shape

- Model: frozen `EleutherAI/pythia-160m`
- Labels: ten formula/equation families above
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

Stage 12 is a pass only if both readout and ablation gates pass.

### Readout Gate

Validation-selected activation headline:

- Train all text baselines on train split
- Train all metadata baselines on train split
- Train all activation readouts across `focus_token`, `final_token`, and
  `mean_over_seq_len`
- Select headline by validation accuracy, not test accuracy
- Report locked-test performance once

Pass requirements:

- Activation test accuracy >= `0.25` against 10-class chance `0.10`
- Activation test accuracy minus best validation-selected text baseline >= `+0.05`
- McNemar exact binomial p vs best text baseline < `0.05`

### Readout-Subspace Ablation Gate

Run only on the validation-selected headline readout/layer.

Pass requirements:

- Targeted formula-family subspace removal drops test readout accuracy to
  <= `0.15` (`chance + 0.05`)
- Thirty same-rank random complement removals do not match targeted disruption
- One-sided empirical p for `random_disruption >= targeted_disruption` < `0.05`

## Verdict Tiers

- `STAGE12_EQUATIONS_FORMULAS_FULL_PASS`: readout gate and ablation gate both pass
- `STAGE12_EQUATIONS_FORMULAS_READOUT_ONLY`: readout passes but ablation does not
- `STAGE12_EQUATIONS_FORMULAS_GREY`: activation is above text numerically but misses a statistical gate
- `STAGE12_EQUATIONS_FORMULAS_NULL`: no reliable beyond-text formula-family readout

## Boundary

Stage 12 tests formula/equation family readout over compiler-validated CAS
formula metadata. It does not prove that Pythia executes the formulas, parses
raw CAS symbols, performs compiler validation internally, steers visible
generation, or generalizes cross-model.
