# Stage 11 Expression Shape Claims Matrix

Date: 2026-05-17

Branch: `experiment/cas-probe-pythia`

## Formal Verdict

`STAGE11_EXPRESSION_SHAPES_FULL_PASS`

Stage 11 is the first pass-clean result above the isolated operator layer. It shows that Pythia-160M hidden states encode the overall CAS expression grammar shape beyond text and metadata baselines, and that the trained readout depends on a compact rank-9 expression-shape subspace.

## Evidence Table

| Claim | Status | Evidence | Boundary |
|---|---|---|---|
| Pythia-160M hidden states encode expression grammar shape | Supported | Validation-selected `final_token` layer 2 test acc `0.9300` on 10 classes | Readout evidence only |
| Expression-shape readout beats text | Supported | Best text baseline `tfidf_char_3_5` test acc `0.6443`; activation lift `+0.2857`; McNemar p `2.94e-227` | Fixture-level expression-shape labels |
| Expression-shape readout beats metadata | Supported | Best metadata baseline `surface_pair_family_focus` test acc `0.6667`; activation lift `+0.2633`; McNemar p `4.20e-216` | Metadata baselines are diagnostic |
| Expression-shape subspace is causal for the trained readout | Supported | Targeted rank-9 removal drops test acc `0.9300 -> 0.1000` exact chance; random max disruption `0.0000`; p(random >= targeted) `0.0323` | Causal for readout, not generation |
| Full expression grammar-shape clean pass | Supported | Formal status `STAGE11_EXPRESSION_SHAPES_FULL_PASS` | Does not include compiler execution |
| Full equation/formula understanding | Not tested | No theta/omega equation solving, coefficient recovery, equality reasoning, or compiler-validated output generation | Requires Stage 12 |
| Raw-symbol parsing | Not tested | Model-facing text intentionally avoided CAS notation and formula symbols | Separate raw-symbol track required |
| Visible generation steering | Not tested | No CPL/generation stage was run for expression shapes | Requires separate eta-to-epsilon expression bridge test |

## Plain-English Read

Stage 10 showed that isolated operator labels were too easy for text. Stage 11 changed the unit of measurement from standalone operator meaning to full expression shape. That made the task materially harder for text while remaining highly readable from Pythia's hidden states.

The result is clean:

> CAS expression-shape information is strongly readable in Pythia-160M and readout-causal under targeted subspace removal. The result survives text and metadata baselines by a wide margin.

## What This Adds To The Ladder

Supported before Stage 11:

- Noetic readout
- 28 Foundation readout
- Original TKS 40 Element readout
- Five isolated operator readout, ceiling-limited but readout-causal

Added by Stage 11:

- Full expression grammar-shape readout
- Full expression grammar-shape readout causality

## Next Ladder

1. Stage 12: equations/formulas with compiler-validated structures
2. Stage 12.1: coefficient / variable / target recovery inside formulas
3. Stage 12.CPL: readable eta-to-epsilon formula prefix likelihood
4. Optional raw-symbol track: CAS notation as text, explicitly separated from meaning-level expression-shape readout

Do not describe Stage 11 as "formula solving." The clean claim is expression grammar-shape readout and readout-causal subspace evidence.
