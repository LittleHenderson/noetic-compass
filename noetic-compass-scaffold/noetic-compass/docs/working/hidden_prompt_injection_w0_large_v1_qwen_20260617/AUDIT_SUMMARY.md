# Hidden/Encoded Prompt-Injection W0 Audit Summary

Date: 2026-06-18 UTC

## ⛔ CORRECTION 2026-06-18 — LICENSE WITHDRAWN (independent re-audit)

An independent re-audit added a **character-level n-gram** surface control (the
original `text_hash` control was word/whitespace-level, so each base64 blob was a
single opaque token → 0.503). Under the stronger control:

- char-level surface text BA = **0.931** (de-dup N=320) / **0.925** (full set)
- hidden-state BA = **0.897**
- hidden − char_text = **−0.03** (FAILS the +0.15 `char_text_margin_pass` gate)

The PRESENT and ABSENT prompts are byte-identical except the base64 note, and
injection payloads share encoded prefixes — so a surface character classifier
separates them *better* than the hidden state. The hidden readout therefore does
**not** beat surface text, and the claim is **downgraded to OPEN / NOT LICENSED**.

Additional caveats from the re-audit:
- "2560 rows" = **320 unique prompts replicated 8×** (seed_00–07, identical text);
  effective independent N is 320, not 2560.
- Layer 18 was selected from a 29-layer scan (mild selection optimism).
- PRESENT ⟺ REFUSED is perfectly collinear (cannot separate "injection present"
  from "would-refuse").

`char_text_margin_pass` is now a permanent gate in the evaluator and the auditor.
The metrics below reproduce exactly from the raw `.npz` (verified) — but passing
the *old* 14-gate battery was insufficient. The win does not hold. See
`docs/working/hidden_prompt_injection_w0_license_withdrawn_20260618.md`.

## Result (ORIGINAL — superseded by the correction above)

The Qwen hidden/encoded prompt-injection W0 run produced a scoped `PASS` for internal prompt-stage hidden-state detection:

- Report: `docs/working/hidden_prompt_injection_w0_large_v1_qwen_20260617/hidden_prompt_injection_prespeech_eval_large_v1_qwen_layer_18_parallel_20260617.json`
- Schema: `cas_harness_hidden_prompt_injection_prespeech_eval.v1`
- Model: `Qwen/Qwen2.5-1.5B-Instruct`
- Layer: `18`
- Rows: `2560`
- Exact prompt groups: `320`
- Payload classes: `5`
- Labels: `ABSENT=1280`, `PRESENT=1280`
- Encodings: `base64=1280`, `url=1280`

## Main Metrics

- Hidden balanced accuracy: `0.896875`
- Text-hash balanced accuracy: `0.503125`
- Layer-0 embedding balanced accuracy: `0.5`
- Hidden minus text balanced accuracy: `0.39375`
- Hidden minus layer-0 balanced accuracy: `0.396875`
- Shuffled-label hidden mean balanced accuracy: `0.500719`
- Within-payload permutation p-value: `0.000999`
- Per-payload hidden balanced accuracy floor:
  - `credential_secret_boundary`: `0.890625`
  - `harmful_action_boundary`: `0.953125`
  - `private_data_boundary`: `0.90625`
  - `system_instruction_boundary`: `0.875`
  - `tool_authority_boundary`: `0.859375`

## Gates

All 14 hidden-injection W0 gates passed:

- `exact_prompt_group_pass`
- `payload_floor_pass`
- `label_per_payload_floor_pass`
- `hidden_balanced_accuracy_pass`
- `l0_baseline_present_pass`
- `l0_margin_pass`
- `text_margin_pass`
- `payload_margin_pass`
- `domain_margin_pass`
- `encoding_margin_pass`
- `length_margin_pass`
- `shuffled_control_pass`
- `within_payload_permutation_pass`
- `per_payload_floor_pass`

The active-goal auditor now reports `claims_licensed=1`, `claims_not_licensed=5`. The licensed claim is only `internal_w0_prompt_injection_detection`.

## Claim Ceiling

This licenses only a scoped prompt-stage hidden-state `PRESENT` / `ABSENT` readout for this exact model, layer, prompt-bank protocol, and evaluator:

`LICENSED only for this model/layer/protocol W0 hidden/encoded prompt-injection presence screen.`

It does not license:

- live pre-speech interception
- prompt-injection prevention/removal/reversal
- hallucination prevention
- CjtPredictionHead claims
- causal proof

Those five claims remain `OPEN` / `NOT LICENSED` in `docs/working/cas_harness_active_goal_claim_audit_20260617.json`.

## Reproducibility Artifacts

Tracked repo artifacts:

- `docs/working/hidden_prompt_injection_w0_large_v1_qwen_20260617/enabled_predicate_w0_all_layers_manifest.json`
- `docs/working/hidden_prompt_injection_w0_large_v1_qwen_20260617/full_capture.log`
- `docs/working/hidden_prompt_injection_w0_large_v1_qwen_20260617/layer_scout.log`
- `docs/working/hidden_prompt_injection_w0_large_v1_qwen_20260617/layer_*_scout.json`
- `docs/working/hidden_prompt_injection_w0_large_v1_qwen_20260617/confirm_layer18_parallel.log`
- `docs/working/hidden_prompt_injection_w0_large_v1_qwen_20260617/hidden_prompt_injection_prespeech_eval_large_v1_qwen_layer_18_parallel_20260617.json`

Large local archive, not committed to git:

- `D:\tksCAS-archive\hidden_prompt_injection_w0_large_v1_qwen_20260617\enabled_predicate_w0_all_layers_dataset.npz`
- `D:\tksCAS-archive\hidden_prompt_injection_w0_large_v1_qwen_20260617\enabled_predicate_w0_all_layers_rows.jsonl`
- `D:\tksCAS-archive\hidden_prompt_injection_w0_large_v1_qwen_20260617\enabled_predicate_w0_all_layers_manifest.json`
- `D:\tksCAS-archive\hidden_prompt_injection_w0_large_v1_qwen_20260617\full_capture.log`
- `D:\tksCAS-archive\hidden_prompt_injection_w0_large_v1_qwen_20260617\layer_scout.log`
- `D:\tksCAS-archive\hidden_prompt_injection_w0_large_v1_qwen_20260617\confirm_layer18_parallel.log`
- `D:\tksCAS-archive\hidden_prompt_injection_w0_large_v1_qwen_20260617\hidden_prompt_injection_prespeech_eval_large_v1_qwen_layer_18_parallel_20260617.json`

## Implementation Note

The first confirmatory run used the serial control path and was stopped after it remained CPU-bound for more than one hour. The evaluator was then extended with deterministic parallel control execution:

- `--control-jobs 16`
- `--progress-every 50`

A local smoke test confirmed serial and parallel controls produce identical seeded p-values and shuffled-control means on the same synthetic input.
