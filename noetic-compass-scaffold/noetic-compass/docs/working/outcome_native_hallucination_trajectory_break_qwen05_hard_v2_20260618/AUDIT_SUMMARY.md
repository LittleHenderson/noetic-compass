# Outcome-Native Hallucination Trajectory-Break Audit

Date: 2026-06-18

## Plain-English Verdict

The W0 -> W1 -> W8 trajectory-break evaluator works on the real outcome-native Qwen-0.5B hard-v2 capture, and it found a real hidden-state movement signal. It still does **not** license hidden-state hallucination detection.

Best scout result:

- Layer 14: trajectory hidden balanced accuracy `0.819487`
- Layer 15: trajectory hidden balanced accuracy `0.818499`
- Layer 1: trajectory hidden balanced accuracy `0.789687`

The signal is not clean enough because it does not beat the required controls by the frozen `0.15` margin.

## Data Alignment

Inputs:

- W0: `C:\Users\wakil\OneDrive\Desktop\tksCAS\.tmp\trajectory_break_extract\outcome_native_hallucination_w0_prompt_risk_qwen05_hard_v2_20260618\enabled_predicate_w0_all_layers_dataset.npz`
- W1: `D:\tksCAS-archive\outcome_native_hallucination_qwen05_hard_v2_20260618\outcome_native_hallucination_w1_qwen05_hard_v2_20260618\enabled_predicate_w0_all_layers_dataset.npz`
- W8: `D:\tksCAS-archive\outcome_native_hallucination_qwen05_hard_v2_20260618\outcome_native_hallucination_w8_qwen05_hard_v2_20260618\enabled_predicate_w0_all_layers_dataset.npz`

The evaluator used explicit row-intersection mode:

- W0 rows: `1392`
- W1 rows: `1392`
- W8 rows: `1381`
- Retained aligned trajectories: `1381`
- Retention fraction: `0.992098`
- W8 excluded labels: `SUPPORTED=8`, `UNSUPPORTED=3`
- Identity hashes checked: `model_output_sha256s`, `judged_answer_sha256s`

## Failed Gates

Best layer 14 failed:

- `w0_static_control_margin_pass`: trajectory beats W0-static by only `0.104846`, below `0.15`
- `generated_prefix_char_text_margin_pass`: trajectory beats generated-prefix char text by only `0.085002`, below `0.15`
- `prompt_char_text_margin_pass`: trajectory beats prompt char text by only `0.112270`, below `0.15`
- `l0_trajectory_margin_pass`: trajectory beats layer-0 trajectory by only `0.112610`, below `0.15`
- `prefix_length_margin_pass`
- `per_stratum_floor_pass`
- `within_stratum_permutation_pass` was not confirmatory because this was a 10-permutation scout

Because margin gates already failed, a 1000-permutation confirmatory run was not justified.

## Claim Boundary

This result is useful research evidence that the trajectory lens can read a non-trivial pre-display signal. It is not a licensed product or research claim for internal hallucination detection.

Current status remains:

- Hidden-state hallucination detection: `OPEN` / `NOT LICENSED`
- Hallucination prevention: `OPEN` / `NOT LICENSED`
- Live pre-speech interception: `OPEN` / `NOT LICENSED`
- Prompt-injection prevention/removal/reversal: `OPEN` / `NOT LICENSED`
- Causal proof: `OPEN` / `NOT LICENSED`

Next valid move: use this trajectory gate on a cleaner pre-answer or W0/W1 formulation where answer-bearing prefix text does not explain the signal, or move to a model/task setup that produces unsupported outcomes before the generated prefix becomes label-readable.
