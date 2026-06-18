# Outcome-Native Hallucination PRE_ANSWER Audit

Date: 2026-06-18

## Plain-English Result

This test reached inside the model before the judged answer value appeared. It
captured hidden states at `PRE_ANSWER`, meaning one generated-token step before
the answer boundary identified in the continuation.

The result is **not licensed** as internal hidden-state hallucination detection.

Layer `14` looked perfect at first: hidden-state balanced accuracy was `1.0`.
But the visible generated prefix was already highly predictive. The character
baseline over the generated prefix reached `0.866776`, leaving only `0.133224`
hidden-over-prefix margin. The frozen margin gate is `0.15`, so this fails.

The harder residual check confirms the same problem. After subtracting what the
generated prefix word/character features explain, hidden-state balanced accuracy
dropped to `0.65185`. That is below the `0.75` detection gate and below the
generated-prefix character baseline by `0.214926`.

## Capture

- Model: `Qwen/Qwen2.5-0.5B-Instruct`
- Rows: `1392`
- Layers: `0..24`
- Hidden size: `896`
- Timing point: `PRE_ANSWER`
- Answer boundary found: `1392 / 1392`
- Support labels: `SUPPORTED=1208`, `UNSUPPORTED=184`
- Exact prompt groups: `200`
- Mixed prompt groups: `97`

## Key Artifact

`layer_14_prefix_residual_hardened_50perm.json`

Important gates:

| Gate | Result |
|---|---:|
| hidden_balanced_accuracy_pass | true |
| generated_prefix_char_text_margin_pass | false |
| prefix_residual_control_run_pass | true |
| prefix_residual_hidden_balanced_accuracy_pass | false |
| prefix_residual_generated_prefix_char_margin_pass | false |
| within_topic_permutation_pass | false |

Important metrics:

| Metric | Value |
|---|---:|
| hidden_balanced_accuracy | `1.0` |
| generated_prefix_char_text_hash_balanced_accuracy | `0.866776` |
| hidden_minus_generated_prefix_char_text_balanced_accuracy | `0.133224` |
| prefix_residual_hidden_balanced_accuracy | `0.65185` |
| prefix_residual_hidden_minus_generated_prefix_char_text_balanced_accuracy | `-0.214926` |
| within_topic_permutation_p | `0.019608` |

## Claim Boundary

Correct status:

`OPEN / NOT LICENSED for internal hallucination-risk timing detection.`

This also means hallucination prevention remains:

`OPEN / NOT LICENSED`.

This evidence can support a product-side warning lane only if described as
pre-display/surface-plus-trajectory risk screening. It does not prove hidden
state hallucination detection independent of visible generated prefix text, and
it does not prove prevention, reversal, removal, or causality.

## Archive

Heavy capture archive:

`D:\tksCAS-archive\outcome_native_hallucination_preanswer_qwen05_hard_v2_20260618\outcome_native_hallucination_preanswer_qwen05_hard_v2_20260618.tgz`

The archive contains the `.npz`, rows JSONL, manifest, scout reports, and
residual audit report.

## Next Valid Move

Do not rerun this same PRE_ANSWER setup as a claim attempt. The failure mode is
now clear: the generated prefix carries the decision signal.

The next research move must remove that confound before GPU spend. A valid next
attempt needs either:

- true `W0` prompt-stage risk prediction with a prompt-level risk target, not
  row-level stochastic outcome labels; or
- a pre-display task where the generated prefix is experimentally controlled and
  cannot itself separate `SUPPORTED` from `UNSUPPORTED`.

Until one of those clears text, prefix, residual, layer-0, group-fold, shuffled,
and permutation controls, the internal hallucination detector remains unlicensed.
