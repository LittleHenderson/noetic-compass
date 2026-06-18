# Outcome-Native Hallucination Early-Trajectory Audit

Date: 2026-06-18

## Plain-English Verdict

The next test removed the answer-bearing W8 prefix and measured only the earliest internal movement:

`W0 -> W1`

That helped with the worst generated-prefix character leak, but it still does **not** license hidden-state hallucination detection.

Best scout result:

- Layer 15: trajectory hidden balanced accuracy `0.790797`
- Layer 14: trajectory hidden balanced accuracy `0.784894`
- Layer 1: trajectory hidden balanced accuracy `0.771829`

The early trajectory is real signal, but it is not clean enough. It does not beat W0-static hidden state, prompt character text, layer-0 trajectory, or shuffled-time controls by the frozen `0.15` margin.

## What Improved

The generated-prefix character baseline got much weaker at W1 than it was at W8:

- W1 generated-prefix char BA: `0.562230`
- Layer 15 trajectory minus W1 generated-prefix char: `0.228567`

So the answer-bearing W8 prefix really was part of the problem.

## Why It Still Fails

Best layer 15 failed these important gates:

- `w0_static_control_margin_pass`: trajectory beats W0-static by only `0.072542`
- `prompt_char_text_margin_pass`: trajectory beats prompt char text by only `0.079722`
- `l0_trajectory_margin_pass`: trajectory beats layer-0 trajectory by only `0.112151`
- `shuffled_time_control_margin_pass`
- `generated_prefix_text_margin_pass`
- `per_stratum_floor_pass`
- `within_stratum_permutation_pass` was not confirmatory because this was a 10-permutation scout

Because the margin gates fail, a 1000-permutation confirmatory run is not justified.

## Claim Boundary

This is useful evidence about where the hallucination-risk signal appears and where it is still contaminated. It is not a product claim.

Current status remains:

- Hidden-state hallucination detection: `OPEN` / `NOT LICENSED`
- Hallucination prevention: `OPEN` / `NOT LICENSED`
- Live pre-speech interception: `OPEN` / `NOT LICENSED`
- Prompt-injection prevention/removal/reversal: `OPEN` / `NOT LICENSED`
- Causal proof: `OPEN` / `NOT LICENSED`

Next valid research move: design a cleaner same-prompt unsupported-risk task where W0/W1 behavior variation is not already partially readable from prompt surface text, or move this exact trajectory gate to a stronger/more variable model.
