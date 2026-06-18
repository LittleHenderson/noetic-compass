# Outcome-Native Hallucination Multi-Token Trajectory Scout

Date: 2026-06-18

Model/data: Qwen-0.5B hard-v2 outcome-native hallucination timing captures.

Question: does adding a later prompt-to-prefix trajectory point (`W16`) make the hidden-state hallucination signal beat the required controls strongly enough to license hidden-state timing-trajectory detection?

## Verdict

`FAIL` / `OPEN` / `NOT LICENSED`.

The multi-token trajectory strengthened the hidden signal, but not enough. The best scout was layer `15` on `W0 -> W1 -> W8 -> W16`:

- trajectory hidden BA: `0.870244`
- W0-static BA: `0.725879`
- trajectory minus W0-static: `0.144365`, just below the required `0.15`
- generated-prefix char baseline BA: `0.828634`
- trajectory minus generated-prefix char baseline: `0.041609`, far below the required `0.15`
- layer-0 trajectory BA: `0.755382`
- trajectory minus layer-0: `0.114862`, below the required `0.15`
- quick within-stratum permutation p: `0.090909`, not significant
- retained rows for W16: `968 / 1392`, retention `0.695402`
- fixed license-retention gate: failed, because licensing requires retention at least `0.95`

Plain English: the inside-of-model trajectory is real and stronger with W16, but the visible generated prefix still gives away too much. Also, too many examples ended before W16, so this is a selected subset, not a licensing-grade full capture.

## Reports

- `multitoken_trajectory_w16_layer15_scout_10perm.json` - best W16 scout, `FAIL`
- `multitoken_trajectory_w16_layer14_scout_10perm.json` - layer 14 scout, `FAIL`
- `multitoken_trajectory_w16_layer18_scout_10perm.json` - layer 18 scout, `FAIL`
- `multitoken_trajectory_w16_layer1_scout_10perm.json` - shallow-layer scout, `FAIL`
- `multitoken_trajectory_w32_retention_blocked_layer15.json` - W32 blocked before evaluation because row intersection retained only `328 / 1392` rows, retention `0.235632`

## Gate Impact

No active CAS Harness claim is upgraded.

- hidden-state hallucination detection/prevention: `OPEN` / `NOT LICENSED`
- live pre-speech interception: `OPEN` / `NOT LICENSED`
- prompt-injection prevention/removal/reversal: `OPEN` / `NOT LICENSED`
- causal proof: `OPEN` / `NOT LICENSED`

## Next Technical Move

The next useful experiment is not another Qwen-0.5B layer sweep. The data says the bottlenecks are model capacity, generated-prefix leakage, and long-prefix row loss.

Run the same trajectory evaluator on `Qwen/Qwen2.5-1.5B-Instruct` or a larger refusal/grounding-variable model with capture configured to preserve enough generated tokens for `W16` and `W32`. Keep the same gates: grouped prompt folds, W0-static control, layer-0 control, generated-prefix word/char controls, metadata/length controls, shuffled-time control, permutation test, and fixed `0.95` row-retention-for-license.
