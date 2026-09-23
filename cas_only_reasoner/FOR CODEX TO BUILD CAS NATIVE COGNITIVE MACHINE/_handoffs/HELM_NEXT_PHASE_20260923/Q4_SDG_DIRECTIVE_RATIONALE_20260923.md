# Q4 SDG directive: the rationale the owner pasted (2026-09-23)

The owner pasted this analysis into the Claude coordination chat, after attaching
`Q4_SDG_AND_TARGETED_FEEDBACK_DIRECTIVE_20260923.md`. It explains the directive. It adds no new instruction beyond
the directive, and it states that "No model was run or repository changed during this analysis". Its main points:

- **Make the feedback more informative, not merely more severe.**
  - Q4 already trains with per-token cross-entropy, AdamW and gradient clipping.
  - A global multiplier adds no information, and AdamW normalisation and clipping blunt it.
  - Weight specific decisions instead. For example, count STATE-versus-BINARY decisions twice, in both directions.
    This is a proposed test setting, not a proven value.
  - Never penalise PLUS itself.
- **EOS is only allowed after a completed tree,** so a short wrong tree can come from choosing STATE where BINARY
  belonged. Inspect the structural choices first.
- **Use CAS SDG as a targeted lesson builder, not a pile of examples.**
  - One-field-difference pairs, for example `^8^C_{F2}|A` against `^8^C_{F2}|E`.
  - Same-symbols, different-grouping pairs, for example `(^1^C + (^2^C + ^3^C))` against `((^1^C + ^2^C) + ^3^C)`.
  - Operator swaps and left/right exchanges.
  - Fresh lessons generated from recurring mistake types.
  - All checked with the pinned compiler.
  - Family G exists because the older SDG pool had narrow structural variety, so the old pool must not simply be
    dumped in.
- **The practice budget.** The first run did 128 single-example updates over a 2,048-row pool: 6.25% of one pass.
  Later diagnostics (memorised 8 rows; no exact reconstruction after 2,000 updates over 256 rows) leave both the
  training and the representation question open.
- **Order of comparison.** A (existing G) against B (new SDG lessons) first, then B against C (targeted weighting),
  with the same GRU, matched starts and a declared, comparable practice budget. The protected examination stays out
  of the feedback loop.
- **Change the architecture** (repeat the summary at every step, or let the decoder consult per-position encoder
  states) only as a separately identified experiment, if the evidence warrants it.
