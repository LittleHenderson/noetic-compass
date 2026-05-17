# Stage 10 Five Operator Claims Matrix

Date: 2026-05-17

Branch: `experiment/cas-probe-pythia`

## Formal Verdict

`STAGE10_OPERATORS_GREY`

The five CAS operator classes are highly recoverable from Pythia-160M hidden states, and the trained operator readout is causally dependent on a rank-4 operator subspace. However, the pre-registered clean-pass gate required an absolute activation-over-text lift of at least +5.0 percentage points. The best text baseline reached 95.57%, so the activation headline at 99.18% produced only +3.61 points of absolute lift.

This is not a null result. It is a ceiling-limited grey result.

## Evidence Table

| Claim | Status | Evidence | Boundary |
|---|---|---|---|
| Pythia-160M hidden states contain strong five-operator information | Supported | Validation-selected `mean_over_seq_len` layer 0 test acc `0.9918` on 5 classes | Readout evidence only |
| Operator readout beats text statistically | Supported but ceiling-limited | Best text baseline `tfidf_char_3_5` test acc `0.9557`; activation lift `+0.0361`; McNemar p `3.21e-22` | Misses pre-registered absolute `+0.05` lift floor |
| Operator subspace is causal for the trained readout | Supported | Targeted rank-4 removal drops test acc `0.9918 -> 0.2000` exact chance; random max disruption `0.0000`; p(random >= targeted) `0.0323` | Causal for readout, not generation |
| Operator metadata was not sufficient | Not supported | Best metadata baseline `surface_pair_family_focus` test acc `1.0000` | Metadata baseline is diagnostic only; the fixture metadata intentionally contains pair/family/focus structure |
| Full clean Stage 10 pass | Not supported | Formal status `STAGE10_OPERATORS_GREY` | Absolute text-lift gate missed |
| Full CAS expression parsing | Not tested | Stage 10 used isolated operator roles only | Requires Stage 11 |
| Full equations/formulas | Not tested | No equality, recipe, theta/omega, let binding, or compiler-shaped formula targets | Requires Stage 12+ |
| Visible generation steering | Not tested | No CPL/generation stage was run for operators | Requires separate eta-to-epsilon operator bridge test |

## Plain-English Read

The five-operator layer is there, but the isolated operator task is too easy for text. Pythia's hidden states get almost perfect performance, and removing the learned operator subspace collapses the readout to chance. But because a plain text classifier also gets 95.57%, the strict absolute lift gate does not let us call this a pass-clean beyond-text result.

The right interpretation is:

> CAS operator information is strongly readable and readout-causal in Pythia-160M, but the isolated five-operator fixture is ceiling-limited. This supports moving to expression-level tests, where operators must be read in relation to operands and structure, not just from standalone semantic phrases.

## Next Ladder

1. Stage 11: full expression grammar shapes
2. Stage 11.1: operator plus operand-role factorization
3. Stage 11.CPL: readable eta-to-epsilon operator/expression prefix likelihood
4. Stage 12: full equations/formulas with compiler-validated structures

Do not revise the Stage 10 gate post hoc. If a ceiling-aware gate is desired, it must be pre-registered for a new held-out fixture.
