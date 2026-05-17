# Stage 12 Claims Matrix

Date: 2026-05-17

Branch: `experiment/cas-probe-pythia`

## Verdict

`STAGE12_EQUATIONS_FORMULAS_FULL_PASS`

Stage 12 extends the ladder from expression grammar shapes to full
compiler-validated CAS equation/formula families.

## Load-Bearing Result

| Claim | Evidence | Status |
|---|---|---|
| Formula/equation family is readable from Pythia-160M hidden states | Validation-selected `final_token` layer 2, locked-test acc `0.8995`, macro-F1 `0.9037` on 10 classes | Supported |
| Readout beats plain text | Best text baseline `tfidf_char_3_5` test acc `0.6393`; activation lift `+0.2602`; McNemar p `3.04e-176` | Supported |
| Readout beats surface metadata | Best metadata baseline `surface_pair_family_focus` test acc `0.6667`; activation lift `+0.2329`; McNemar p `1.49e-142` | Supported |
| Formula-family subspace is causal for the trained readout | Targeted rank-9 removal drops locked-test acc from `0.8995` to exact chance `0.1000` | Supported |
| Random same-rank removals do not explain the effect | 30 random complement controls; random max disruption `0.0000`; p(random >= targeted) `0.0323` | Supported |
| Fixture is compiler-backed | 9,000 rows; every `cas_formula` compiles with `compiler.valid=true`; fixture SHA `a0bebdc2a073f26a2b1099bfd2f4bf41d4091505cdcd8397b88a450dad210974` | Supported |

## What This Does Not Claim

| Claim | Status |
|---|---|
| Pythia internally executes CAS formulas | Not shown |
| Pythia performs compiler validation internally | Not shown |
| Pythia parses raw CAS notation from the prompt | Not tested; model-facing English withheld raw symbols |
| This controls visible generation | Not tested in Stage 12 |
| This generalizes to larger or different open models | Not shown by Stage 12 |

## Formula Families

The ten labels were:

- `relation_dependency`
- `typed_program`
- `production_recipe`
- `yield_query`
- `state_vector`
- `emergent_register_assignment`
- `membership_assertion`
- `cardinality_assertion`
- `set_operation_formula`
- `cover_partition_formula`

## Boundary Sentence

Stage 12 supports this claim:

> In Pythia-160M, compiler-validated CAS equation/formula families are readable
> from hidden states well above text and metadata baselines, and the trained
> readout depends on a specific rank-9 activation subspace.

Stage 12 does not support this claim:

> Pythia can execute CAS formulas, validate CAS formulas internally, parse raw
> CAS notation, or steer generated language through those formula families.

## Next Gate

The next ladder step should be separated into one of two explicit tests:

1. **Raw-symbol formula parsing:** put the actual `cas_formula` text into the
   model-facing prompt and test whether hidden states classify the formula
   family above text/metadata controls.
2. **Formula-conditioned harness bridge:** use predicted formula family or
   compiler result kind as an external readable prefix and test likelihood or
   visible-generation movement, following the Stage 7 eta-to-epsilon pattern.
