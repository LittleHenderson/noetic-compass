# Grounded Factual QA Hallucination Timing Audit - W1/W8

Date: 2026-06-18

Model: `Qwen/Qwen2.5-1.5B-Instruct`

Benchmark: `live-trace-worker/scenarios/grounded_factual_qa_hallucination_bank_v0_20260618.json`

Purpose: test whether early pre-display hidden states at `W1` and `W8` can separate `SUPPORTED` from `UNSUPPORTED` factual-answer cases after the `W0` test landed at chance.

## Result

Status: `FAIL`

Claim remains: `OPEN / NOT LICENSED for internal hallucination-risk timing detection.`

Both timing points were negative:

| Timing | Best layer | Confirm status | Hidden BA | Char text BA | Prefix char BA | Within-topic permutation p |
|---|---:|---|---:|---:|---:|---:|
| `W1` | 1 | `FAIL` | 0.5 | 0.5 | 0.5 | 0.220779 |
| `W8` | 1 | `FAIL` | 0.5 | 0.5 | 0.5 | 0.083916 |

## What This Means

The timing apparatus works: the capture path records `W1` and `W8` hidden states, timing metadata, generated-prefix text, and generated-prefix token counts.

The detector did not work on this benchmark/model pair. The best hidden readout stayed at chance at both `W1` and `W8`, so there is no licensed internal hallucination-risk detection claim here.

This result does not weaken the product-safe surface/evidence-integrity lane. CAS Harness can still flag prompt-injection and instruction-integrity risk before the answer is shown, with Evidence Packet audit trails. It just cannot claim hidden-state hallucination detection or hallucination prevention from this run.

## Important Controls

The evaluator now requires generated-prefix controls for W1/W8. That means a timing readout cannot pass just because the first few internally generated tokens reveal the label.

The failing gates included:

- `hidden_balanced_accuracy_pass`
- `generated_prefix_text_margin_pass`
- `generated_prefix_char_text_margin_pass`
- `text_margin_pass`
- `char_text_margin_pass`
- `within_topic_permutation_pass`
- `per_topic_floor_pass`

## Artifact Pointers

Primary machine summary:

`docs/working/grounded_factual_qa_hallucination_w1_w8_qwen_timing_20260618/TIMING_AUDIT_SUMMARY.json`

Confirmatory reports:

- `docs/working/grounded_factual_qa_hallucination_w1_w8_qwen_timing_20260618/w1_eval/hallucination_timing_eval_w1_confirm_layer_1.json`
- `docs/working/grounded_factual_qa_hallucination_w1_w8_qwen_timing_20260618/w8_eval/hallucination_timing_eval_w8_confirm_layer_1.json`

Heavy activation archives:

`D:\tksCAS-archive\grounded_factual_qa_hallucination_w1_w8_qwen_timing_20260618\`

## Next Research Move

Do not rerun this exact Qwen same-prompt support-status benchmark hoping for a different answer.

The next useful move is a different formulation:

- outcome-native hallucination labels from actual generated answers,
- retrieval-conflict cases where the model must choose between evidence and prior belief,
- or a larger/more capable model where unsupported-claim formation may appear in hidden states before display.

Until one of those passes the same controls, hidden-state hallucination detection and hallucination prevention remain `OPEN / NOT LICENSED`.
