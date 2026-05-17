# Stage 12 Equations And Formulas Probe Report

**Status:** `STAGE12_EQUATIONS_FORMULAS_FULL_PASS`

## Headline

- Readout: `final_token`
- Layer: `2`
- Activation test accuracy: `0.8995`
- Best text baseline: `tfidf_char_3_5` test `0.6393`
- Best metadata baseline: `surface_pair_family_focus` test `0.6667`
- Lift over text: `+0.2602`
- McNemar p vs text: `3.03751e-176`

## Ablation

- Subspace rank: `9`
- Targeted ablated accuracy: `0.1000`
- Targeted disruption: `+0.7995`
- Random max disruption: `+0.0000`
- p(random >= targeted): `0.0323`

## Boundary

This is a hidden-state readout and readout-subspace ablation result for compiler-validated CAS equation/formula families. It does not prove that Pythia executes formulas, parses raw CAS symbols, performs compiler validation internally, controls visible generation, or generalizes cross-model.
