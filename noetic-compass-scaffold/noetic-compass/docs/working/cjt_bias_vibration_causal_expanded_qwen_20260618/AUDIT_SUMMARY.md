# PCBA/CJT Expanded Causal Intervention Audit

## Verdict

Expanded causal/removal gate: `FAIL` / `OPEN / NOT LICENSED`.

The earlier small-bank diagnostic removal lead did not survive a larger held-out
bank. Splitting the PCBA/CJT direction into `^4` unsupported-vibration and `^5`
untrusted-bias axes also failed the causal/removal gates.

The honest claim boundary is:

- W0 hidden-response detection remains the useful lead.
- Causal hidden-state removal/reversal is not proven.
- Public language must not claim prompt-injection or hallucination removal from
  hidden-state intervention.

## Expanded Blended Run

- Model: `Qwen/Qwen2.5-1.5B-Instruct`
- Layer: `18`
- Direction: blended PCBA/CJT risk-minus-control direction
- Alpha: `10.0`
- Prompt count: `70` held-out risk prompts
- Seeds: `2`
- Rows: `560`
- Complete prompt+seed condition blocks: `140`
- Status: `FAIL`

Metrics:

- Baseline risk adoption: `0.15`
- `-risk` risk adoption: `0.085714`
- `-risk` reduction shift: `0.064286`
- Random same-norm reduction shift: `0.007143`
- `-risk` reduction p: `0.024599`
- `-risk` reduction CI95: `[0.007143, 0.121429]`

This is directionally favorable but below gate: p is not `< 0.001`, the shift is
below the screen floor, and it does not beat random by the required margin.

## Split `^4` Unsupported-Vibration Run

- Direction: `UNSUPPORTED_LURE` vs `SUPPORTED_EVIDENCE`
- Prompt count: `35`
- Seeds: `2`
- Rows: `280`
- Status: `FAIL`

Metrics:

- Baseline risk adoption: `0.071429`
- `-risk` risk adoption: `0.057143`
- `-risk` reduction shift: `0.014286`
- Random same-norm risk shift: `0.1`
- `-risk` reduction p: `0.498125`

This lane fails because the baseline risk floor is too low, the reduction is too
small, and random same-norm steering is not inert.

## Split `^5` Untrusted-Bias Run

- Direction: `UNTRUSTED_INJECTION` vs `BENIGN_PARAPHRASE` + `TRUSTED_CORRECTION`
- Prompt count: `35`
- Seeds: `2`
- Rows: `280`
- Status: `FAIL`

Metrics:

- Baseline risk adoption: `0.128571`
- `-risk` risk adoption: `0.071429`
- `-risk` reduction shift: `0.057143`
- Random same-norm risk shift: `0.028571`
- `-risk` reduction p: `0.183091`

This lane has a small favorable reduction, but it is not statistically reliable
and does not clear the removal screen.

## What This Means

The larger test says the current intervention direction is not a working
removal/reversal solution. It may nudge risk behavior in some small slices, but
it is not stable enough for a claim.

The product path should stay with the proven, marketable lane:

> CAS Harness can flag prompt-injection and instruction-integrity risk before
> the answer is shown, with evidence-packet audit trails.

The research path must treat causal removal as open. The next credible research
move is not another larger run of the same direction. It is a new intervention
design trained against generated behavior outcomes, with random-direction,
no-op, held-out prompt, and human-label controls from the start.

## Artifacts

- Expanded bank: `live-trace-worker/scenarios/cjt_bias_vibration_causal_bank_expanded_v1_20260618.json`
- Expanded bank summary: `docs/working/cjt_bias_vibration_causal_bank_expanded_v1_20260618_summary.json`
- Blended analysis: `docs/working/cjt_bias_vibration_causal_expanded_qwen_20260618/cjt_causal_analysis_expanded_alpha10_seed2_relabeled.json`
- `^4` direction metadata: `docs/working/cjt_bias_vibration_causal_expanded_qwen_20260618/cjt_vibration_unsupported_direction_layer18.json`
- `^4` analysis: `docs/working/cjt_bias_vibration_causal_expanded_qwen_20260618/cjt_vibration_analysis_alpha10_seed2_relabeled.json`
- `^5` direction metadata: `docs/working/cjt_bias_vibration_causal_expanded_qwen_20260618/cjt_bias_injection_direction_layer18.json`
- `^5` analysis: `docs/working/cjt_bias_vibration_causal_expanded_qwen_20260618/cjt_bias_analysis_alpha10_seed2_relabeled.json`
- Full archive: `D:\tksCAS-archive\cjt_bias_vibration_causal_expanded_qwen_20260618\`

