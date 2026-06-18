# Grounded Factual-QA Hallucination W0 Audit Summary

Date: 2026-06-18

## Verdict

`FAIL` for internal W0 hallucination-risk detection on this Qwen run.

This does not license hidden-state hallucination detection or hallucination
prevention. The active CAS Harness claim remains `OPEN / NOT LICENSED`.

## What Was Tested

- Model: `Qwen/Qwen2.5-1.5B-Instruct`
- Dataset: `400` prompt-stage W0 traces
- Layers captured: `0..28`
- Topics: `5`
- Labels: `SUPPORTED=200`, `UNSUPPORTED=200`
- Prompt groups: `40` exact same-prompt groups
- Mixed prompt groups: `40`
- Surface preflight: `READY_FOR_W0_CAPTURE`
- Heavy activation archive:
  `D:\tksCAS-archive\grounded_factual_qa_hallucination_w0_qwen_grouped_20260618\enabled_predicate_w0_all_layers_dataset.npz`

## Final Confirmatory Result

Final report:
`docs/working/grounded_factual_qa_hallucination_w0_qwen_grouped_20260618/hallucination_prespeech_eval_qwen_grouped_layer_14_confirm_20260618.json`

Key metrics:

- `status`: `FAIL`
- `hidden_balanced_accuracy`: `0.5`
- `text_hash_balanced_accuracy`: `0.5`
- `char_text_hash_balanced_accuracy`: `0.5`
- `l0_embedding_balanced_accuracy`: `0.5`
- `hidden_minus_char_text_balanced_accuracy`: `0.0`
- `within_topic_permutation_p`: `0.293706`

All layers scouted at `0.5` hidden balanced accuracy after the prompt-group
fix, so no layer showed a W0 support-status readout. Layer 14 is the final
confirmatory reference because it also keeps the layer-0 baseline present.

## Important Fix Found During The Run

The first pullback exposed a validation bug: the W0 capture `.npz` did not save
`prompt_group_ids`, so the evaluator derived groups from `scenario_id` and split
supported/unsupported slots apart. That would make the same-prompt gate
meaningless.

Fix applied:

- `capture_enabled_predicate_w0_all_layers.py` now writes `prompt_group_ids`.
- `evaluate_hallucination_prespeech.py` now uses saved `prompt_group_ids` when
  present, with fallback for older datasets.
- Regression test now asserts `prompt_group_ids` survive in the `.npz`.

The corrected grouped run is the only one to use for claim decisions.

## Plain-English Meaning

The surface-clean bank worked, the W0 capture worked, and the evaluator worked.
But Qwen's prompt-final hidden state did not distinguish the paired
`SUPPORTED` versus `UNSUPPORTED` labels before generation. In this formulation,
the exact same prompt gives the same W0 state, so branch-level hallucination
prediction at W0 is not licensed.

The next productive direction is not to relabel this as a win. The next
direction is to move the hallucination product lane to:

- surface/evidence integrity warnings before output is shown;
- W1/W8 timing controls, where generated-token context may expose emerging
  unsupported-claim drift before the answer is displayed;
- separate intervention/guardrail proof that reduces unsupported answers while
  preserving supported-answer quality.
