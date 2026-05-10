# v1d 2-epoch retrain — 24-record human audit (Claude-graded)

Source artifacts:
- `cas-synthetic/data/path_d/v1_eval_pack_24records_20260510T191358Z.md`
- `cas-synthetic/data/path_d/v1_eval_pack_24records_20260510T191358Z.jsonl`

Baseline comparison: `v1c + all scaffolds` final state (commit `83a0cde` /
`810b66e` / `1ad6e02` era).

Evaluator: Claude (user delegated).

## Verdict

**Mixed: real signal on the fractal primary, but real instability spillover
on binary_composition / recipe / meta-logic. Net acceptable+ drops by one.**

- Acceptable+ band: v1c **16/24** → v1d **15/24** (−1)
- Strong band (green + high-yellow): v1c **9/24** → v1d **9/24** (flat)
- Records 13/14/15 fractal (primary): 1 of 3 moved (record 14 wrong → yellow);
  records 13/15 unchanged
- Records 10/12 recipe (regression watch): record 10 unchanged (wrong);
  record 12 unchanged (wrong); record 11 yellow → wrong (regression)
- Record 16 meta-logic (regression watch): unchanged (wrong)
- Hard-notation leaks: stay at 0/24 ✓
- Cleanup/repair counts dropped net (29 → 25) — model doing more work itself ✓

The data fix moved record 14 cleanly and improved 4 records (8, 9, 14, 22)
but destabilized 4 others (5, 6, 11, 17). Net is slightly negative.

## Grade counts

| Band | Count | Records |
|---|---:|---|
| Green | 9 | 1, 2, 4, 7, 8, 9, 22, 23, 24 |
| High yellow | 0 | — |
| Yellow | 6 | 6, 14, 18, 19, 20, 21 |
| Wrong / flop / incoherent | 9 | 3, 5, 10, 11, 12, 13, 15, 16, 17 |

Acceptable+ (green + high yellow + yellow): **15/24**.

## Per-record grades

| # | Category | v1c band | v1d band | Δ | Notes |
|---:|---|---|---|---|---|
| 1 | state_literal | green | green | = | Identical to target. |
| 2 | state_literal | green | green | = | Identical to target. |
| 3 | state_literal | wrong | wrong | = | "memory triggered by memory" repetition; adds hallucinated "transcendent strategic way" not in source. |
| 4 | binary_composition | green | green | = | Faithful; "principled arena" = ^P. |
| 5 | binary_composition | yellow | wrong | ↓ | **REGRESSION.** `->` rendered as "combined with" (= `+`); adds "just clicked" hallucination. |
| 6 | binary_composition | green | yellow | ↓ | **REGRESSION.** Doubled "combined with practiced rhythm" — repetition glitch. |
| 7 | cross_register_omega | green | green | = | Faithful three-mode fusion. |
| 8 | cross_register_omega | yellow | green | ↑ | **IMPROVEMENT.** Both modes correctly preserved; clean prose. |
| 9 | cross_register_omega | yellow | green | ↑ | **IMPROVEMENT.** "two modes" matches the 2 cross-register terms in source. |
| 10 | recipe | wrong | wrong | = | Both terms rendered as ^1^P|f when source has ^3^E + ^1^P|f; term 1 swapped wrong. |
| 11 | recipe | yellow | wrong | ↓ | **REGRESSION.** F3 → F5 drive swap, coef 2 → 1.5, outcome name corruption (rehearsal_11 → engagement_11), side product missing. |
| 12 | recipe | wrong | wrong | = | Only 2 of 3 source inputs described; coef recovery 3/3 → 1/3 at validator level. |
| 13 | fractal_sequence | wrong | wrong | = | Cardinality flipped to True (8 stages) but degenerates into "popped into mind again" loop. Not human-useful. |
| 14 | fractal_sequence | wrong | yellow | ↑ | **IMPROVEMENT.** ^3→^7 path preserved cleanly: "rubs the wrong way led to a thought that then became muscle memory". One extra clause; clean prose. |
| 15 | fractal_sequence | wrong | wrong | = | Position 0 (^1) and position 3 (^3) correct; rest scrambled. Some match but not coherent recovery. |
| 16 | meta_logic_relation | wrong | wrong | = | **REGRESSION on cluster count.** Source has 3 partitions; v1d emits 2 groups. |
| 17 | meta_logic_relation | high yellow | wrong | ↓ | **REGRESSION.** Cluster 1 has ^0 instead of ^9; cluster 2 has ^3/^5 not in source, missing ^0; plus hallucinated extra cluster. |
| 18 | meta_logic_relation | yellow | yellow | = | Relation word + cluster count correct (idiom rewrite intact); cluster contents drift. |
| 19 | rpm_chain | yellow | yellow | = | Silhouette correct (seed worked); stage content drifts (^9→^2, F3→F2). |
| 20 | rpm_chain | yellow | yellow | = | Silhouette correct; stageP2 missing definition; per-stage content drifts. |
| 21 | rpm_chain | high yellow | yellow | ↓ | Slight regression. F2 captured, ^2 partly captured (stageW2/P2 mention "positive draw"), but stageD2 wrong. |
| 22 | invalid_to_explanation | yellow | green | ↑ | **IMPROVEMENT.** Cross-domain explanation now cleaner and more complete. |
| 23 | invalid_to_explanation | green | green | = | Faithful. |
| 24 | invalid_to_explanation | green | green | = | Faithful + clean clarification. |

## Comparison to v1c+scaffolds baseline

| Metric | v1c+scaffolds | v1d (this run) | Δ |
|---|---:|---:|---:|
| Green | 7 | 9 | +2 |
| High yellow | 2 | 0 | −2 |
| Yellow | 7 | 6 | −1 |
| Wrong/flop | 8 | 9 | +1 |
| Strong band | 9 | 9 | 0 |
| Acceptable+ band | 16 | 15 | **−1** |

Net: **−1 acceptable+ row**, **0 strong band**. Strong band held (the 2 records
that dropped from high yellow → yellow are offset by 2 records moving from
yellow → green). The lost acceptable+ row came from records 5/11/17 dropping
out of the band while only record 14 was added.

## Primary target diagnostic — records 13/14/15

- **Record 14**: cleanly improved wrong → yellow. The `^3 → ^7` silhouette
  is preserved with one extra middle clause. This is the cleanest fractal
  output in the audit and shows the data fix had a real effect.
- **Record 13**: cardinality_match flipped False → True (model learned the
  "K stages" structural rule), but the content degenerated into a ^9 loop.
  The strict gate now sees 8 stages but they're 6 of 8 identical `popped into
  mind` clauses. Net: still wrong/flop in human terms.
- **Record 15**: 2 of 7 positions match source (^1 at pos 0, ^3 at pos 3).
  Different drift from v1c but no clear net improvement.

**Verdict on primary target**: 1 of 3 fractals materially improved (record 14
moved a full band). Records 13/15 still fail the human-useful bar.

## Decision-rule application

Per the user's decision rules:

> - If acceptable+ improves despite regressions: consider 1 more epoch or freeze v1d.  ✗ (not improved)
> - If acceptable+ is flat but fractals improved: likely one more epoch is worth testing.  ~ (acceptable+ −1, fractal lift partial)
> - If acceptable+ drops: stop v1d and pivot architecture/pointer-copy.  ✓ (dropped by 1)
> - If fractals still fail all three: pivot architecture now.  ✗ (record 14 succeeded)

Two rules apply ambiguously: acceptable+ technically dropped (by 1), AND
fractals didn't fail ALL three (record 14 lifted).

**Honest read**: v1d's data fix did real work — record 14 is the cleanest
fractal output in the audit, and the strong band held — but the
destabilization spillover (4 regressions on binary_composition / recipe /
meta-logic) outweighs the 4 improvements at the acceptable+ level. The
corpus fix is partially right but the model needs a different lever to
close the remaining gap.

The 1-record acceptable+ drop is within audit noise (a single record's
band judgment could swing it back). But the regression PATTERN — recipe
content drifts more, meta-logic cluster contents drift more, binary
composition gains a repetition glitch — suggests v1d retraining
destabilized v1c-acquired patterns more than it stabilized fractal
content. That's a model-side instability signal, not a corpus-quality
signal.

## Recommendation

**Pivot to pointer/copy/fractal-aware decoding** (per the architecture R&D
agent's brief and the memory entry
`feedback_v1d_decision_rule_pointer_copy.md`).

The data-fix hypothesis got its cleanest test: $1.28 in SDG + corpus
cleanup + 2-epoch retrain. Record 14 shows the data path works in
principle, but records 13/15 + the regression spillover indicate the
model needs structural inductive bias for source-binding (count, order,
identifier preservation) — not just cleaner teacher signal.

The pointer-generator + fractal-aware decoder mode described in the
architecture R&D agent brief targets exactly this gap: forces the decoder
to copy Ω-identifiers, coefficients, let-vars from `cas_prefix_ids`
rather than memorize, and adds K-aware constrained beam for fractal
rendering.

Estimated cost (from architecture agent's earlier estimate):
~3 engineering weeks for the new heads + fine-tune; ~6-12 GPU-hours
for the fine-tune itself.

If the user prefers to first try **one more epoch of v1d** to see if the
regressions stabilize or get worse, that's defensible — but the signal
from this 2-epoch eval suggests the corpus-fix lever has reached its
limit and the next $5-10 of GPU spend is better invested in the
architectural change.
