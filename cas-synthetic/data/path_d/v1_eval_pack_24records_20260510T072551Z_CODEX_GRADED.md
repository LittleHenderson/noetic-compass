# v1c + Repairs + Generation Cleanup Human Audit

Source artifacts:

- `v1_eval_pack_24records_20260510T072551Z.md`
- `v1_eval_pack_24records_20260510T072551Z.jsonl`

Baseline:

- Meta-logic Phase 1 audit: `v1_eval_pack_24records_20260510T053607Z_CODEX_GRADED.md`

## Verdict

This run clears the secondary 24-record human-quality gate.

Human-quality gate:

- Previous acceptable+: `17/24`
- Current acceptable+: `18/24`
- Target: `>=18/24`
- Verdict: PASS

Primary structural status remains:

- RPM wrong-task hijack: fixed.
- RPM stage identifiers and final edges: repaired.
- RPM semantic drifts: logged, not rewritten.
- Meta-logic relation type: repaired.
- Generation cleanup: 1/24 records, 2 substitutions total.

This is not chat-ready in the broad product sense. It is a meaningful local milestone: the 24-record eval now passes the agreed secondary gate without hiding raw model behavior.

## Grade Counts

| Band | Count | Records |
|---|---:|---|
| Green | 7 | 1, 2, 4, 6, 7, 23, 24 |
| High yellow | 3 | 17, 18, 21 |
| Yellow | 8 | 3, 5, 8, 9, 11, 19, 20, 22 |
| Wrong / flop / incoherent | 6 | 10, 12, 13, 14, 15, 16 |

Acceptable+ count here means green + high yellow + yellow: `18/24`.

Strong count means green + high yellow: `10/24`.

## Changed Records

Only records `3` and `18` changed from the prior run.

### Record 3

Previous:

> Amemory memory triggered a memory or association triggered a connection in a principled foundation, expressed through an embodied way of sensing and moving.

Current:

> A memory triggered a memory or association triggered a connection in a principled foundation, expressed through an embodied way of sensing and moving.

Grade: Yellow

The cleanup pass fixes the token corruption:

- `Amemory` -> `A memory`
- `memory memory` -> `memory`

The sentence is now readable and mostly aligned with the target: triggered memory/association, principled foundation, embodied expression. It is still not green because it repeats "triggered" and is less clean than the target. But it is no longer malformed/flop.

### Record 18

Previous:

> The ten ways of thinking cover into two groups...

Current:

> The ten ways of thinking are covered by two groups...

Grade: High yellow

The relation is now both structurally correct and grammatical. It still is not green because the member drift remains: `^3`, `^4`, and `^8` are missing according to the meta-logic repair log, and the second cluster still contains wrong repeated members. But the answer now expresses the correct CoverOf relation clearly enough to be useful.

## Per-Record Grades

1. Green. Exact state-literal rendering.
2. Green. Faithful state-literal rendering.
3. Yellow. Cleanup fixed token corruption; still repetitive but usable.
4. Green. Faithful binary composition.
5. Yellow. Understandable but awkward/repetitive transformation.
6. Green. Faithful binary composition.
7. Green. Strong cross-register omega rendering.
8. Yellow. Outcome repaired; register/domain body still drifts.
9. Yellow. Outcome survives; mode/register structure still drifts.
10. Wrong. Recipe body remains materially wrong.
11. Yellow. Useful recipe shape, but missing side-effect and body detail.
12. Wrong. Recipe still ends on wrong outcome phrase and drifts body.
13. Wrong. Fractal sequence order/content wrong.
14. Wrong. Two-step fractal target becomes longer invented sequence.
15. Wrong. Long fractal scrambled and repetitive.
16. Wrong. Partition remains incomplete despite correct relation type.
17. High yellow. Product relation mostly right with one member drift.
18. High yellow. Cover relation now correct and grammatical; member drift remains.
19. Yellow. RPM identifiers/edge repaired; noetic/drive body drift remains.
20. Yellow. RPM identifiers/edge repaired; noetic body drift remains.
21. High yellow. RPM structure strong after repair; some semantic evidence incomplete.
22. Yellow. Invalid explanation directionally correct but imprecise.
23. Green. Strong invalid-to-explanation rendering.
24. Green. Strong invalid-to-explanation rendering.

## Policy Check

Generation cleanup did not violate the generative-AI policy line.

- `raw_text` preserved.
- `final_text` cleaned.
- `generation_cleanup_log` records both substitutions.
- Cleanup fired on `1/24` records only.
- Broad cleanup would be visible as a regression signal.

This remains hygiene-class postprocessing, not semantic generation.

## Remaining Wrong Band

The wrong/flop band is now:

- `10`, `12`: recipe body preservation
- `13`, `14`, `15`: fractal sequence order and k-value preservation
- `16`: meta-logic partition member/group completeness

Recommended next move: stop chasing the 24-record gate for a moment. The gate is now met. The next useful work is category-specific, with fractal or recipe likely giving the biggest remaining lift.
