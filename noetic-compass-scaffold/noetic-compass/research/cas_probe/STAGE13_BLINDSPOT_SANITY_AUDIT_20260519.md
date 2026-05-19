# Stage 13 Blind-Spot Sanity Audit

**Verdict:** `BLINDSPOT_LANGUAGE_DEFENSIBLE_WITH_PER_READOUT_BOUNDARY`

## Population Check

- Perfectly balanced fixture: `True`
- Per split: train `360`, val `120`, test `420` per class when balanced.

## Threshold Provenance

- low confidence: at least half of layer positions have confidence < 0.45
- high entropy: at least half of layer positions have entropy > 70% of maximum 10-class entropy
- stable: majority label covers at least 70% of layers and longest stable run is at least 5 layers
- early-correct-then-drift: first correct layer <= 4 and final layer is wrong
- late-emerging-correct: first correct layer >= 7 and final layer is correct, or final layer correct after non-stable trace
- conflicted: at least 5 switches or no majority over half the layers
- bug fix 80377ab changed invalid strict zip iteration for switch count only; it did not change thresholds

## Per-Readout Blind Spots

- `final_token`: `cardinality_assertion` (0.777), `set_operation_formula` (0.818), `production_recipe` (0.838), `membership_assertion` (0.835), `cover_partition_formula` (0.846)
- `focus_token`: `cardinality_assertion` (0.803), `set_operation_formula` (0.828), `membership_assertion` (0.818), `cover_partition_formula` (0.849), `yield_query` (0.854)
- `mean_over_seq_len`: `relation_dependency` (0.551), `production_recipe` (0.602), `membership_assertion` (0.617), `cover_partition_formula` (0.622), `yield_query` (0.645)

## Relation Dependency

- Headline readout/layer: `focus_token` layer `12`
- Headline accuracy: `0.9738`

Interpretation: `relation_dependency` is an aggregate/readout-path blind-spot candidate, not a failure at the best headline readout.

## Boundary

Blind spot means weak or unstable evidence under a specific readout path. It does not prove model incapacity, exact causal neurons, or internal CAS compiler validation.
