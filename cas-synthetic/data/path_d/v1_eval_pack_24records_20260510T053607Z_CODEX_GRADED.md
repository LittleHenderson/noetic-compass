# v1c + RPM Repairs + Meta-Logic Phase 1 Human Audit

Source artifacts:

- `v1_eval_pack_24records_20260510T053607Z.md`
- `v1_eval_pack_24records_20260510T053607Z.jsonl`

Baseline:

- RPM Phase 3 audit: `v1_eval_pack_24records_20260510T044827Z_CODEX_GRADED.md`

## Verdict

Meta-logic Phase 1 works as a narrow relation-type repair.

It improves record 18 from wrong to yellow, but it does not close the human-quality gate.

Human-quality gate:

- Previous acceptable+: `16/24`
- Current acceptable+: `17/24`
- Target: `>=18/24`
- Verdict: FAIL, but closer.

Structural checks:

- Meta-logic parsed: exactly records `16, 17, 18`.
- Non-meta `cas_to_english` records no-op.
- Invalid explanation records skipped.
- Only record `18` changed final text.
- Relation repair on record `18`: `PartitionOf -> CoverOf`.

## Grade Counts

| Band | Count | Records |
|---|---:|---|
| Green | 7 | 1, 2, 4, 6, 7, 23, 24 |
| High yellow | 2 | 17, 21 |
| Yellow | 8 | 5, 8, 9, 11, 18, 19, 20, 22 |
| Wrong / flop / incoherent | 7 | 3, 10, 12, 13, 14, 15, 16 |

Acceptable+ count here means green + high yellow + yellow: `17/24`.

Strong count means green + high yellow: `9/24`.

## Meta-Logic Records

### Record 16

Grade: Wrong / flop

No text changed. The relation type is correct (`PartitionOf`), and the model says three groups, but the content is still incomplete. Target has three distinct groups, including a single-member first group and a final group containing thought + popped-into-mind. The generated answer only gives one group with many members and omits required members `^3` and `^4` from the large cluster. It is structurally incomplete enough to stay wrong.

### Record 17

Grade: High yellow

No text changed. Product relation is correct, two clusters are present, and most structure is useful. The second cluster still swaps/omits the `^0` thought member, so it is not green.

### Record 18

Grade: Yellow

This is the actual lift.

Before:

> The ten ways of thinking partition into two groups...

After:

> The ten ways of thinking cover into two groups...

The relation type is now directionally correct: source is `CoverOf`, not `PartitionOf`. That is enough to move the record out of wrong. But the phrase "cover into two groups" is grammatically rough, and the cluster contents are still materially wrong: `^3`, `^4`, and `^8` are missing according to the repair log. So this is yellow, not high-yellow.

## Grammar Note

The current word-level repair is too literal for record 18. Replacing bare `partition` with bare `cover` produces:

> cover into two groups

The natural repair should be closer to:

> are covered by two groups

or:

> cover the set with two groups

This should be a tiny grammar-aware tweak if we continue meta-logic Phase 1. Do not treat it as a model problem; it is a repair-phrasing issue.

## Comparison

| Metric | Before meta repair | After meta repair |
|---|---:|---:|
| Meta relation mismatch on record 18 | yes | no |
| Final text changed | 0/24 | 1/24 |
| Green | 7/24 | 7/24 |
| High yellow | 2/24 | 2/24 |
| Yellow | 7/24 | 8/24 |
| Wrong/flop | 8/24 | 7/24 |
| Acceptable+ | 16/24 | 17/24 |

## Recommendation

Keep Meta-Logic Phase 1. It produced a real lift with narrow gating.

Before moving to member rewriting, patch the grammar of relation repair for `CoverOf` so record 18 reads naturally. Then rerun the same 24-pack. That may not move the numeric band by itself, but it prevents a repair layer from making the prose uglier.

After that, the fastest path to reach `18/24` is probably not meta-logic member repair. It is likely state-literal record 3 or recipe/fractal-specific work. Meta-logic now has only record 16 still clearly wrong; record 18 is usable yellow.
