# v1c + RPM Seed 24-Record Human Audit

Source artifacts:

- `v1_eval_pack_24records_20260510T034307Z.md`
- `v1_eval_pack_24records_20260510T034307Z.jsonl`

Baseline comparison:

- Prior v1c audit: `v1_eval_pack_24records_20260510T031428Z_CODEX_GRADED.md`
- Prior commit: `0d641df`

## Verdict

The RPM decoder seed fixes the primary silhouette hijack, but this run is still not green.

Primary gate:

- Target: `rpm_chain` hijack `3/3 -> 0/3`
- Result: `3/3 -> 0/3`
- Verdict: PASS

Secondary gate:

- Target: acceptable+ band `12/24 -> >=18/24`
- Result: `16/24`
- Verdict: FAIL

The seed moved records 19, 20, and 21 from wrong-task invalid-explanation outputs into valid let-binding-shaped RPM outputs. That is a real architectural win. But all three still contain per-stage content drift: wrong noetic aliases, wrong drive labels, wrong final edge, or malformed stage suffixes. They move from wrong to yellow, not to green.

## Grade Counts

| Band | Count | Records |
|---|---:|---|
| Green | 7 | 1, 2, 4, 6, 7, 23, 24 |
| High yellow | 1 | 17 |
| Yellow | 8 | 5, 8, 9, 11, 19, 20, 21, 22 |
| Wrong / flop / incoherent | 8 | 3, 10, 12, 13, 14, 15, 16, 18 |

Acceptable+ count here means green + high yellow + yellow: `16/24`.

Strong count means green + high yellow: `8/24`.

## Primary Gate Details

### Record 19

Grade: Yellow

The seed fires and the output is let-binding-shaped. It preserves the opening variable `stageA0_3_0234` and mentions the other stage variables. That fixes the previous invalid-explanation hijack.

The body is not faithful enough for green. Target stage `stageD3_3_0234` should be "something that popped into mind" with vitality; generation says "struck a chord" and "wisdom and insight." The final edge is also wrong: target says `stageW3_3_0234 then leads to stageP3_3_0234`; generation drifts toward `stageA0_3_0234 then leads to stageD3_3_02`.

### Record 20

Grade: Yellow

The seed fixes the silhouette. It produces a valid-looking chain with `stageA0_2_0277`, `stageD2_2_0277`, `stageW2_2_0277`, and `stageP2_2_0277`.

The content still drifts. The generated ending uses malformed/wrong identifiers: `A0_2_0272` and `stageD2_2_0272` instead of the source edge. It also changes several stage meanings from the target phrasing.

### Record 21

Grade: Yellow

The seed fixes the wrong-task collapse. It now produces the expected let-binding form and carries the main stage names.

The stage body is still not faithful. Target `stageD2_2_0287` should be "drawn toward wisdom and insight in the evaluative arena"; generation says "something that speaks to you." The final edge is wrong: target says `stageA0_2_0287 leads to stageD2_2_0287`; generation says `stageD2_2_028 leads to stageW2_2_028`.

## Per-Record Grades

1. Green. Exact state-literal rendering.
2. Green. Faithful state-literal rendering; "in an analytical way" is acceptable for the target.
3. Wrong / flop. The intended content is partly present, but "Amemory memory..." makes the output malformed and not user-facing.
4. Green. Faithful binary composition.
5. Yellow. Broad transformation is understandable, but the phrasing is awkward and the first side repeats rather than cleanly preserving the source.
6. Green. Faithful binary composition.
7. Green. Strong cross-register omega answer; preserves chord/resonance, cognitive frame, three modes, and `clarity`.
8. Yellow. Outcome is repaired correctly, but the body drifts from affective/transcendent into principled/analytical.
9. Yellow. Outcome and broad evaluative attention survive, but three-mode structure collapses into two embodied modes.
10. Wrong. Recipe body is materially wrong: extra contribution, wrong noetic/body, and incoherent coefficient structure despite repaired outcome name.
11. Yellow. Recipe silhouette and main outcome survive, but side contribution is dropped and body details are compressed/drifted.
12. Wrong. Target outcome and generated outcome conflict (`judgment_78` vs `tracking_78`), with coefficient/body drift.
13. Wrong. Fractal silhouette exists, but the sequence does not preserve the target k-values.
14. Wrong. Target is a two-step aversion-to-rhythm sequence; generation invents extra states and misses the aversion.
15. Wrong. Long fractal sequence is badly scrambled and repetitive.
16. Wrong. Target is a three-group partition; generation gives two incomplete groups.
17. High yellow. Correct product-of-clusters silhouette and most relation structure, but the second cluster has a wrong member.
18. Wrong. Cover relation becomes a partition, and cluster contents are materially wrong.
19. Yellow. RPM hijack fixed by seed, but stage content and final edge drift.
20. Yellow. RPM hijack fixed by seed, but final edge and identifiers drift.
21. Yellow. RPM hijack fixed by seed, but stage content and final edge drift.
22. Yellow. Correct invalid-transition idea, but phrasing is sloppy and less precise than the target.
23. Green. Strong invalid-to-explanation rendering.
24. Green. Strong invalid-to-explanation rendering with useful added clarification.

## Comparison To v1c-Only Audit

| Metric | v1c only | v1c + RPM seed | Change |
|---|---:|---:|---:|
| RPM hijack | 3/3 | 0/3 | Primary gate fixed |
| Green | 7/24 | 7/24 | Flat |
| High yellow | 1/24 | 1/24 | Flat |
| Yellow | 5/24 | 8/24 | +3 |
| Wrong/flop | 11/24 | 8/24 | -3 |
| Acceptable+ | 13/24 | 16/24 | +3 |

The seed is a real improvement, but it is not enough to pass the broader 18/24 human-quality gate.

## Recommendation

Promote the RPM seed as a gated inference fallback for valid `rpm_chain` shapes, because it fixes a deterministic wrong-task collapse without touching invalid explanations.

Do not call the model chat-ready from this run. The next blocker is no longer RPM task routing; it is content fidelity inside the correct silhouette, especially:

- RPM per-stage noetic/drive/edge preservation
- Fractal sequence k-order preservation
- Meta-logic cluster cardinality and member preservation
- Recipe coefficient/body preservation

The next useful experiment is not another `[VALID]` token retrain. It is a targeted content-fidelity pass: grammar-aware postprocessing/repair for RPM stage edges and identifiers, plus a small human-graded 24-record rerun after that.
