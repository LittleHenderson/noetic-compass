# v1c + RPM Seed + RPM Repair Phase 1 Human Audit

Source artifacts:

- `v1_eval_pack_24records_20260510T041621Z.md`
- `v1_eval_pack_24records_20260510T041621Z.jsonl`

Baseline comparisons:

- v1c-only audit: `v1_eval_pack_24records_20260510T031428Z_CODEX_GRADED.md`
- v1c + RPM seed audit: `v1_eval_pack_24records_20260510T034307Z_CODEX_GRADED.md`

## Verdict

RPM Repair Phase 1 works as a symbolic structural repair. It restores stage identifiers and closing edges without leaking into non-RPM routes.

It does not close the human-quality gate.

Primary structural checks:

- RPM wrong-task hijack: `0/3` after the seed, sustained.
- RPM final edge match: `0/3 pre-repair -> 3/3 post-repair`.
- RPM chain parser fired on exactly records `19, 20, 21`.
- Invalid RPM explanation records `22, 23, 24` were not repaired.

Human-quality gate:

- Target: acceptable+ band `>=18/24`
- Result: `16/24`
- Verdict: FAIL

The repair moves RPM structure in the right direction. It does not meaningfully change the overall acceptable+ count because records 19, 20, and 21 had already moved from wrong to yellow after the decoder seed. Phase 1 mainly upgrades identifier/edge integrity inside those yellow records. Record 21 improves to high-yellow. Records 19 and 20 remain yellow because per-stage noetic/drive content still drifts.

## Grade Counts

| Band | Count | Records |
|---|---:|---|
| Green | 7 | 1, 2, 4, 6, 7, 23, 24 |
| High yellow | 2 | 17, 21 |
| Yellow | 7 | 5, 8, 9, 11, 19, 20, 22 |
| Wrong / flop / incoherent | 8 | 3, 10, 12, 13, 14, 15, 16, 18 |

Acceptable+ count here means green + high yellow + yellow: `16/24`.

Strong count means green + high yellow: `9/24`.

## RPM Repair Details

### Record 19

Grade: Yellow

Phase 1 repairs worked:

- `stageW3_3_0233` became `stageW3_3_0234`.
- `stageP3_3_02` became `stageP3_3_0234`.
- Closing edge was repaired to `stageW3_3_0234 then leads to stageP3_3_0234`.

The record is still yellow because the stage meanings are wrong. Target stage `stageD3_3_0234` should be "something that popped into mind" and vitality-driven. The output says "something that struck a chord" and "wisdom and insight." That is a noetic and drive drift. The structure is now right; the body is not.

### Record 20

Grade: Yellow

Phase 1 repairs worked:

- Truncated/off-by-one stage names are restored.
- Closing edge is repaired to `stageW2_2_0277 then leads to stageP2_2_0277`.

The record remains yellow because the stage content does not faithfully preserve the target. `stageD2_2_0277` should be "who one is shaped by wisdom and insight"; the output says "something that speaks to you." `stageW2_2_0277` should retain the shaped-by-experience pattern; it becomes cognitive attention. The identifier/edge skeleton is now correct, but the internal noetic content is still off.

### Record 21

Grade: High yellow

Phase 1 repairs worked:

- Stage names are restored.
- Closing edge is repaired to `stageA0_2_0287 leads to stageD2_2_0287`.

This is the best RPM row after repair. The output preserves the full stage skeleton, wisdom/insight drive, cognitive/evaluative staging, and the correct final edge. The remaining drift is semantic nuance: `stageD2_2_0287` says "something that speaks to you" rather than the target's "something drawn toward wisdom and insight," and the evaluative/principled arena wording is less exact. It is useful and structurally faithful, but not green.

## Per-Record Grades

1. Green. Exact state-literal rendering.
2. Green. Faithful state-literal rendering.
3. Wrong / flop. "Amemory memory..." remains malformed and not user-facing.
4. Green. Faithful binary composition.
5. Yellow. Understandable transformation, but awkward and repetitive.
6. Green. Faithful binary composition.
7. Green. Strong cross-register omega rendering.
8. Yellow. Outcome is repaired, but register/domain body drifts.
9. Yellow. Outcome survives, but two-mode/three-mode and register content drift.
10. Wrong. Recipe body remains materially wrong despite repaired coefficients/outcome.
11. Yellow. Recipe shape is useful, but side-effect and some body detail are missing.
12. Wrong. Recipe still conflicts with the target and ends on the wrong outcome phrase.
13. Wrong. Fractal sequence order/content is wrong.
14. Wrong. Two-step fractal target becomes a longer invented sequence.
15. Wrong. Long fractal remains scrambled and repetitive.
16. Wrong. Three-group partition is incomplete.
17. High yellow. Product-of-clusters structure is mostly right with one cluster member drift.
18. Wrong. Cover relation becomes partition and cluster membership is materially wrong.
19. Yellow. RPM identifiers/edge repaired; noetic/drive content still drifts.
20. Yellow. RPM identifiers/edge repaired; internal noetic content still drifts.
21. High yellow. RPM identifiers/edge repaired and most body structure survives; nuance still off.
22. Yellow. Invalid explanation is directionally correct but imprecise.
23. Green. Strong invalid-to-explanation rendering.
24. Green. Strong invalid-to-explanation rendering with useful clarification.

## Comparison

| Metric | v1c only | v1c + seed | v1c + seed + repair |
|---|---:|---:|---:|
| RPM hijack | 3/3 | 0/3 | 0/3 |
| RPM final edge match | 0/3 | 0/3 | 3/3 |
| Green | 7/24 | 7/24 | 7/24 |
| High yellow | 1/24 | 1/24 | 2/24 |
| Yellow | 5/24 | 8/24 | 7/24 |
| Wrong/flop | 11/24 | 8/24 | 8/24 |
| Acceptable+ | 13/24 | 16/24 | 16/24 |
| Strong | 8/24 | 8/24 | 9/24 |

## Recommendation

Keep RPM Repair Phase 1. It is doing useful deterministic work and its gate is correctly narrow.

Do not declare the milestone green. The next bottleneck is exactly what Phase 1 intentionally did not touch: semantic content preservation inside the correct RPM skeleton.

Next step should be Phase 2 as a flag-only verifier first:

- For each `let stage = ^N^D_{F}` binding, check the rendered clause for the expected noetic/domain/drive aliases.
- Log semantic drifts with stage variable, expected axis values, and observed evidence.
- Do not rewrite semantic labels on the first pass.

After that, rerun the same 24-pack. If records 19 and 20 show clear, localized semantic drift logs, then decide whether to add a targeted retry or a conservative repair. The broader wrong band remains outside RPM: records 3, 10, 12, 13, 14, 15, 16, and 18.
