# Independent preservation (round-trip) checker — FROZEN law

## Independence law

`tools/independent_roundtrip_checker.py` is the independent parser required by the
construction-gold law. Independence constraints (registered, checkable):

1. **No shared rendering code.** The checker imports NOTHING from the generator and
   shares no template-rendering function; it recovers operations from surface text
   with its own grammar (regular expressions written against the registered template
   families, not against generator internals).
2. **Recovery must be exact.** For every passage the checker must recover, from the
   clause texts alone: the ordered op-class sequence, every argument (minds, ideas,
   parts in order), the question type, the question arguments, and the gold answer
   derived ONLY from its own recovered trace. Any mismatch with the seed record —
   class, argument, order, question, or derived answer — fails the passage.
3. **Failed round trips are EXCLUDED, never relabeled.** The checker has no write
   access to labels; it emits pass/fail verdicts and the exclusion list only.
4. **Honest limit (recorded):** this is same-process code-path independence — two
   disjoint programs in one repository — not organizational independence. It kills
   generator/parser shared-bug label corruption; it does not substitute for the
   later independent audit of Gate 1B results.

## Verdicts

Per passage: `ROUNDTRIP_PASS` or `ROUNDTRIP_FAIL(reason)` with the first mismatch
named (class / argument / order / question / answer). Aggregate output feeds
`DATASET_MANIFEST_CANDIDATE.json`: counts per split, exclusion list, and the
checker's own file digest.

## Gate 1B use

The AWS job re-runs this exact checker (pinned by digest) over the regenerated
splits — including the protected split — BEFORE any training or evaluation; any
verdict change versus the pre-registered manifest aborts the run with
`DATASET_INTEGRITY_FAILURE`.
