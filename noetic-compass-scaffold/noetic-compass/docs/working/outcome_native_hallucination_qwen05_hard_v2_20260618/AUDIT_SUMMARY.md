# Outcome-Native Hallucination Timing Audit - Qwen-0.5B Hard v2

Date: 2026-06-18

Model: `Qwen/Qwen2.5-0.5B-Instruct`

Claim status: `OPEN / NOT LICENSED` for internal hallucination-risk timing detection.

## Plain-English Result

This run fixed the previous data bottleneck. The hard bank produced many more unsupported answers and many more same-prompt mixed groups, so the test is now meaningful.

The hidden-state signal is real and strong, especially at W16. But it is not clean enough to claim internal hallucination detection, because early generated-prefix text baselines explain too much of the same signal. In plain English: by W16 the model has already started to reveal where the answer is going, and a text baseline reading that early prefix comes too close to the hidden-state detector.

That means this is useful as a pre-display trajectory warning, but not licensed as "CAS reads hallucinations from hidden states."

## Data Bank

- Prompt bank: `docs/working/outcome_native_hallucination_hard_qwen05_bank_v2_20260618.json`
- Scenarios: `2400`
- Prompt groups: `200`
- Samples per prompt: `12`
- Challenge modes: `8`
- Generation output: `2400`
- Binary labels: `1392`
- Supported labels: `1208`
- Unsupported labels: `184`
- Mixed prompt groups: `97`

Unsupported labels by challenge mode:

- `draft_json_repair`: `58`
- `stale_majority_vote`: `44`
- `stale_first_revision`: `26`
- `conflicting_snippets`: `20`
- `answer_slot_autocomplete`: `19`
- `trusted_first_strict`: `8`
- `draft_anchor`: `5`
- `cached_answer_bias`: `4`

## Timing Results

| Timing | Best layer | Rows | Mixed groups | Hidden BA | Text BA | Char BA | Prefix text BA | Prefix char BA | Status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| W1 | 22 | 1392 | 97 | 0.796106 | 0.647945 | 0.674939 | 0.682605 | 0.578426 | FAIL |
| W8 | 14 | 1381 | 97 | 0.835753 | 0.645177 | 0.670981 | 0.670486 | 0.742093 | FAIL |
| W16 confirm | 15 | 968 | 88 | 0.888633 | 0.649253 | 0.615042 | 0.795350 | 0.828944 | FAIL |
| W32 | 15 | 328 | 50 | 0.859448 | 0.591966 | 0.656472 | 0.847432 | 0.833203 | FAIL |

## Confirmatory W16 Gate

Confirmatory report: `w16_best_layer_15_confirm.json`

Passed:

- hidden balanced accuracy: `0.888633`
- hidden minus word text: `0.239380`
- hidden minus char text: `0.273591`
- hidden minus layer-0: `0.189665`
- hidden minus challenge-mode baseline: `0.314054`
- within-topic permutation p-value: `0.000999`
- same-prompt mixed groups: `88`
- all topic floors and per-topic floors

Failed:

- `generated_prefix_text_margin_pass`
- `generated_prefix_char_text_margin_pass`

The failed margins are the blocker:

- hidden minus generated-prefix word text: `0.093283`
- hidden minus generated-prefix char text: `0.059689`

The frozen margin requirement is `0.15`, so W16 is not licensed.

## Residual-Over-Prefix Diagnostic

Residual diagnostic report: `w16_layer15_prefix_residual_diagnostic.json`

This diagnostic asks a sharper question: after a fold-local model learns what the generated prefix can explain about the hidden state, does the leftover hidden-state signal still predict `SUPPORTED` versus `UNSUPPORTED`?

Result:

- hidden BA before residualization: `0.888633`
- generated-prefix char BA in this diagnostic run: `0.840450`
- hidden minus generated-prefix char: `0.048183`
- prefix-residual hidden BA: `0.686017`
- prefix-residual hidden minus generated-prefix char: `-0.154433`

Plain English: once the early generated prefix is accounted for, the hidden-state-only leftover drops below the `0.75` floor. That strengthens the negative conclusion. The current W16 signal is mostly trajectory/prefix-tied, not clean hidden-state hallucination detection.

## Claim Boundary

Licensed product-safe wording:

`CAS Harness can flag unsupported-answer trajectory risk before the final answer is shown, with Evidence Packet audit trails.`

Not licensed:

`CAS Harness has proven hidden-state hallucination detection.`

Not licensed:

`CAS Harness prevents, removes, reverses, or causally controls hallucinations.`

## Next Gate

The next technical gate is a residual-over-prefix or pre-answer-token detector:

1. Predict unsupported risk from hidden states.
2. Explicitly subtract or control for the generated prefix.
3. Require hidden-state residual signal to beat generated-prefix word and character baselines by at least `0.15`.
4. Only after that passes, run a guardrail/intervention proof to test whether unsupported answers are reduced without harming supported-answer quality.
