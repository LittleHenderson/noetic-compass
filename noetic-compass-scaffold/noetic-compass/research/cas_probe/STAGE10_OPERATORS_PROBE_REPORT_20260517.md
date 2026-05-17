# Stage 10 Five Operator Probe Report

**Status:** `STAGE10_OPERATORS_GREY`

## Headline

- Readout: `mean_over_seq_len`
- Layer: `0`
- Activation test accuracy: `0.9918`
- Best text baseline: `tfidf_char_3_5` test `0.9557`
- Best metadata baseline: `surface_pair_family_focus` test `1.0000`
- Lift over text: `+0.0361`
- McNemar p vs text: `3.20746e-22`

## Ablation

- Subspace rank: `4`
- Targeted ablated accuracy: `0.2000`
- Targeted disruption: `+0.7918`
- Random max disruption: `+0.0000`
- p(random >= targeted): `0.0323`

## Boundary

This is a hidden-state readout and readout-subspace ablation result for the five operator classes. It does not prove full-expression parsing, raw-symbol understanding, visible generation control, or cross-model generality.
