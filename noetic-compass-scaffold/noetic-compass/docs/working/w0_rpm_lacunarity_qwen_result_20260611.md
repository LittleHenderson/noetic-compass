# W0 RPM/Lacunarity Internal Diagnostic — Qwen Result

Date: 2026-06-11

## Plain-English Result

This test reads inside the model. It uses prompt-stage W0 hidden states from the
800-row Qwen enabled-predicate capture. It does not use model output text as an
input feature.

The result is not strong enough to license the desired product claim yet.

## Inputs

- Dataset: `D:\tksCAS-archive\enabled_predicate_prespeech_qwen_phi_20260611\enabled_predicate_prespeech_qwen_phi_20260611.tgz::qwen2_5_1_5b_chat_combined_seed0_7/enabled_predicate_w0_dataset_combined_seed0_7.npz`
- Model: `Qwen/Qwen2.5-1.5B-Instruct`
- Captured layers available in this archive: `[0, 14]`
- Evaluated hidden layer: `14`
- Noetic probe: `D:\tksCAS-archive\qwen_gate_a_20260610\qwen2p5_1p5b_noetic_probes_v1_20260610.npz`
- Full JSON report: `docs\working\w0_rpm_lacunarity_qwen_result_20260611.json`

## What Was Tested

The evaluator applies the Qwen Gate-A noetic-10 probe to W0 hidden states, then
computes:

- `^2/^3` RPM intended-operator satisfaction.
- Noetic-10 lacunarity.
- A 10x4 state-profile proxy from noetic-10 probabilities and an internal W0
  domain readout.
- Axis-A pathway disruption proxy from the `^2/^3` margin and lacunarity.
- Optional post-hoc outcome-mismatch metrics using generated behavior labels as
  evaluation labels only.

## Result Metrics

- `rpm_intent_balanced_accuracy`: `0.5`
- `text_intent_balanced_accuracy`: `1.0`
- `hidden_minus_text_intent_balanced_accuracy`: `-0.5`
- `outcome_mismatch_count`: `214 / 800`
- `outcome_mismatch_rate`: `0.2675`
- `rpm_break_score_outcome_mismatch_auc`: `0.494402`
- `lacunarity_outcome_mismatch_auc`: `0.395801`
- `supervised_w0_chain_break_balanced_accuracy`: `0.686661`
- `supervised_text_chain_break_balanced_accuracy`: `0.709499`
- `supervised_w0_minus_text_chain_break_balanced_accuracy`: `-0.022838`
- `mean_state40_proxy_lacunarity`: `4.849164`
- `state40_proxy_lacunarity_spike_rate`: `0.95`

## Interpretation

This confirms that the implementation is internal-W0 capable, but it does not
prove the hoped-for detector on the current artifact.

The strongest honest reading:

- W0 hidden states are present and readable.
- The Qwen noetic probe is compatible with layer 14 hidden dimension.
- The internal domain readout is strong enough to recover domain structure from
  W0 hidden states on this dataset.
- The transferred noetic-10 W0 RPM readout does not recover the intended `^2/^3`
  RPM state.
- The RPM/lacunarity break score does not predict later chain break above chance.
- A supervised W0 chain-break probe is below the text baseline.

## Claim Boundary

This is an internal hidden-state diagnostic, not a transcript-side detector.

It still does not license prompt-injection prevention/removal/reversal,
hallucination prevention, pre-speech/live interception, or causal compliance-state
detection. Those claims remain `OPEN` / `NOT LICENSED`.

## Next Valid Move

The current archive stores only layer 0 and one target layer. To test the user's
full hypothesis, the next capture should store all prompt-stage layers and apply
or train compatible noetic/domain/40-state readouts per layer. The pass condition
should require the hidden-state RPM/lacunarity detector to beat text, payload,
domain, and layer-0 baselines before any public claim.
