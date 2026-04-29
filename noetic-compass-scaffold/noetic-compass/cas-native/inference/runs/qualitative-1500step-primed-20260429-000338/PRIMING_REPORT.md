# 1500-Step Primed Decoding Diagnostic

Date: 2026-04-29

Checkpoint:
`cas-native/training/runs/v2-first-full-20260428-220635/checkpoints/final.pt`

Runner:
`cas-native/inference/generate_samples_primed.py`

## Purpose

This run tested whether bucket-canonical response prefixes would let the
1500-step causal CAS-Native model complete well-formed CAS expressions for the
complex buckets that failed under free sampling.

The hypothesis was:

> If the model has learned the relevant grammar but struggles to start the
> right shape, then forcing a canonical opening should substantially improve
> structured-valid output.

## Result

The hypothesis was falsified.

| Metric | Result |
| --- | ---: |
| Total samples | 30 |
| Loose fragment-valid samples | 30/30 |
| Whole/bucket structured-valid samples | 1/30 |
| Structured-valid bucket | `v77_rule_four` only |

Bucket breakdown:

| Bucket | Structured-valid |
| --- | ---: |
| `v74_baseline` | 0/5 |
| `v75_register` | 0/5 |
| `v77_rule_four` | 1/5 |
| `v77_omega` | 0/5 |
| `v76_production` | 0/5 |
| `meta_logic` | 0/5 |

The `30/30` loose-valid result is not a success signal. It mostly means the
generated text contains small fragments such as `^1` or `^7` that compile in
isolation. It does not mean the full generated expression is usable.

## Diagnostic Read

The model has learned CAS token families and partial motifs, but it has not
learned reliable grammar-state transitions.

Examples of failure modes:

- Prefixes such as `Theta(Omega_name) =` still continue into comma-separated
  fragments instead of coefficient-state-arrow-target recipe structure.
- Omega/register examples repeat register suffixes or emit malformed delimiter
  sequences.
- Meta-logic primers start the right constructor family but do not close the
  constructor grammar.
- Fragment-valid evaluation overstates quality because tiny CAS atoms compile
  even when the whole expression fails.

This is now an engineering problem, not primarily a compute problem.

## Next Move

Build grammar-aware constrained decoding.

The model should provide logits, but the inference layer should mask illegal
next tokens before temperature/top-p sampling. EOS should only be allowed when
the current grammar state is accepting and the decoded expression passes the
bucket's structured-valid predicate.

Recommended implementation path:

1. Add a sidecar grammar constraint API rather than changing
   `compile_expression`.
2. Start with finite-state bucket grammars for the six current generator
   buckets.
3. Wire constrained mode into the inference sampler before top-p filtering.
4. Report whole-expression validity separately from fragment validity.
5. Keep compiler validation as the terminal authority.

Target next gate:

- `>=20/30` structured-valid on the same 30-sample qualitative suite under
  grammar-constrained decoding.
- Product-facing target remains `>=95%` compiler-valid after constrained
  decode plus bounded repair/fallback.

## Known Runner Issue

The primed runner should be cleaned up before reuse as a formal benchmark. One
primer path can emit a literal placeholder shape (`^N^D_{F`) instead of a fully
substituted CAS prefix. This does not change the main diagnostic conclusion,
but it should be fixed when the free/primed/constrained sample runners are
unified.
