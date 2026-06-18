# CJT Bias/Vibration Causal Qwen Result

## Verdict

Full bidirectional causal gate: `FAIL` / `OPEN / NOT LICENSED`.

Risk-reduction/removal screen: `PASS_DIAGNOSTIC_NOT_LICENSED`.

This is the honest next result after the W0 hidden-response PASS. The layer-18
PCBA/CJT direction is readable inside Qwen before output, and applying the
negative direction reduced risk adoption in the held-out generation run. But the
full causal proof is not licensed because the positive `+risk` direction did not
increase risk behavior and the stricter public-proof gate is not met.

## Run

- Model: `Qwen/Qwen2.5-1.5B-Instruct`
- Layer: `18`
- Alpha: `10.0`
- Prompt count: `16` held-out risk prompts
- Seeds: `4`
- Rows: `256`
- Full archive: `D:\tksCAS-archive\cjt_bias_vibration_causal_qwen_20260618\`

## Full Causal Gate

- status: `FAIL`
- claim: `OPEN / NOT LICENSED for PCBA/CJT causal risk control.`
- baseline risk adoption: `0.15625`
- `+risk` risk adoption shift: `0.03125`
- `-risk` risk adoption shift: `-0.140625`
- random same-norm risk shift: `0.0`
- `+risk` sign-flip p: `0.388261`

Failed full-gate items:

- `plus_beats_random_pass`
- `plus_risk_ci_low_pass`
- `plus_risk_shift_pass`
- `plus_risk_sign_flip_p_pass`

## Risk-Reduction Screen

- status: `PASS_DIAGNOSTIC_NOT_LICENSED`
- claim: `Candidate PCBA/CJT risk-reduction direction detected under auto labels, but still NOT LICENSED for public removal/reversal until stricter p<0.001, human label audit, and held-out replication pass.`
- `-risk` reduction shift: `0.140625`
- random reduction shift: `0.0`
- reduction minus random: `0.140625`
- reduction p: `0.004`
- reduction CI95: `[0.0625, 0.21875]`
- ignored shift under `-risk`: `0.0625`
- malformed shift under `-risk`: `0.0`

## Plain English

The detector found a real internal direction. When we pushed the model in the
negative direction at layer 18, the risky outputs dropped from `0.15625` to
`0.015625` after relabeling. That is promising for a removal/reversal product
lane.

But the stronger proof is still not closed. A clean causal proof needs both a
reliable `+risk` worsening effect and a reliable `-risk` removal effect, or a
separately frozen removal-only preregistration with stricter p-value, human label
audit, and replication on more held-out prompts. This run gives us a serious
lead, not a public removal claim.

## Audit Artifacts

- Relabeled analysis: `docs/working/cjt_bias_vibration_causal_qwen_20260618/cjt_causal_analysis_alpha10_seed4_relabeled.json`
- Relabel metadata: `docs/working/cjt_bias_vibration_causal_qwen_20260618/cjt_causal_relabel_alpha10_seed4.json`
- Relabeled rows: `docs/working/cjt_bias_vibration_causal_qwen_20260618/cjt_causal_rows_alpha10_seed4_relabeled.jsonl`
- Causal bank: `live-trace-worker/scenarios/cjt_bias_vibration_causal_bank_v0_20260618.json`
- Frozen direction: `docs/working/cjt_bias_vibration_w0_qwen_v1_20260618/cjt_bias_vibration_risk_direction_layer18.npy`
- Direction metadata: `docs/working/cjt_bias_vibration_w0_qwen_v1_20260618/cjt_bias_vibration_risk_direction_layer18.json`

## Next Gate

Expand the held-out causal bank and rerun the removal-only preregistration so the
prompt-level p-value can clear `p < 0.001`, then human-audit the labels. Only
after that should CAS Harness call this prompt-injection/hallucination-risk
removal or reversal.
