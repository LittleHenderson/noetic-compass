# Candidate Reranking Validation

Date: 2026-04-29

Code commit: `b7735f0`

Checkpoint:
`cas-native/training/runs/v2-first-full-20260428-220635/checkpoints/final.pt`

Dataset:
`cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl`

Command mode:
`generate_samples.py --decode-mode rerank --candidate-source hybrid`

## Purpose

This run tested the next step after grammar-constrained decoding: choose among
compiler-valid candidate expressions by teacher-forced model log-probability
conditioned on the prompt.

The intended improvement over token-level grammar sampling was semantic
selection: keep the `30/30` validity guarantee while improving prompt
faithfulness.

## Headline

The validity guarantee held, but semantic reranking did **not** solve prompt
faithfulness.

| Metric | Result |
| --- | ---: |
| Whole compiler-valid | 30/30 |
| Structured-valid | 30/30 |
| Exact match against held-out `cas_expression` | 0/30 |

## Bucket Results

| Bucket | Whole-valid | Structured-valid | Exact match | Unique outputs |
| --- | ---: | ---: | ---: | ---: |
| `v74_baseline` | 5/5 | 5/5 | 0/5 | 3/5 |
| `v75_register` | 5/5 | 5/5 | 0/5 | 4/5 |
| `v77_rule_four` | 5/5 | 5/5 | 0/5 | 1/5 |
| `v77_omega` | 5/5 | 5/5 | 0/5 | 1/5 |
| `v76_production` | 5/5 | 5/5 | 0/5 | 4/5 |
| `meta_logic` | 5/5 | 5/5 | 0/5 | 3/5 |

Candidate bank sizes:

| Bucket | Candidates |
| --- | ---: |
| `v74_baseline` | 1,852 |
| `v75_register` | 2,000 |
| `v77_rule_four` | 1,673 |
| `v77_omega` | 1,798 |
| `v76_production` | 1,005 |
| `meta_logic` | 858 |

## Interpretation

This run confirms that compiler-valid candidate reranking is structurally safe:
every output remains valid CAS. However, the current 1500-step model's
prompt-conditioned probabilities are not discriminative enough to select the
right candidate for the prompt.

The failure pattern is clear:

- `v77_rule_four` collapsed to the same expression for all 5 prompts.
- `v77_omega` collapsed to the same `Ω_cadence` expression for all 5 prompts.
- `meta_logic` over-selected generic `NoeticCluster{...}` expressions even
  when prompts asked for product, coordinate, cover, or union structure.
- `v76_production` selected valid recipe forms but not the exact target recipe
  requested by the prompt.

So the architecture has crossed the syntax barrier, but not the semantic
selection barrier.

## Product Implication

The current safe product path is:

1. Use constrained/reranked decoding only when validity matters.
2. Label output as compiler-valid CAS, not as semantically authoritative.
3. Keep raw model generations out of user-facing surfaces.
4. Add a second-stage intent/shape classifier before candidate selection.

## Next Engineering Step

Reranking needs candidate filtering before model scoring. The model should not
score thousands of heterogeneous candidates when the prompt already implies a
shape.

Recommended next patch:

1. Add a lightweight prompt-to-expression-family classifier.
2. Filter candidate banks by family before reranking:
   - recipe / `Θ(...)`
   - omega / `Ω_*`
   - register co-presence / `+`
   - cross-register integration / `×`
   - cluster / `NoeticCluster` or `StateCluster`
   - product / `Product(...)`
   - coordinate / `Coordinate{...}`
   - cover / `CoverOf(...)`
   - set operation / `∪`, `∩`, `∖`
   - membership / `∈`, `∉`
3. Report family-match rate separately from exact-match rate.

Target next gate:

- Keep whole-valid and structured-valid at `>=95%`.
- Achieve `>=70%` prompt-family match on the 30-sample suite.
- Exact match can remain a longer-term metric because many prompts admit
  multiple defensible CAS expressions.
