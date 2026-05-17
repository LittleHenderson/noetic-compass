# Stage 11 Expression Shape Probe Report

**Status:** `STAGE11_EXPRESSION_SHAPES_FULL_PASS`

## Headline

- Readout: `final_token`
- Layer: `2`
- Activation test accuracy: `0.9300`
- Best text baseline: `tfidf_char_3_5` test `0.6443`
- Best metadata baseline: `surface_pair_family_focus` test `0.6667`
- Lift over text: `+0.2857`
- McNemar p vs text: `2.93895e-227`

## Ablation

- Subspace rank: `9`
- Targeted ablated accuracy: `0.1000`
- Targeted disruption: `+0.8300`
- Random max disruption: `+0.0000`
- p(random >= targeted): `0.0323`

## Boundary

This is a hidden-state readout and readout-subspace ablation result for expression grammar shapes. It does not prove full equation/formula parsing, compiler execution, visible generation control, or cross-model generality.
