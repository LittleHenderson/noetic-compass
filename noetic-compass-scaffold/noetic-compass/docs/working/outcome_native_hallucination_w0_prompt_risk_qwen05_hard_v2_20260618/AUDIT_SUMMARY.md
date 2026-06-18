# Outcome-Native Hallucination W0 Prompt-Risk Scout

Date: 2026-06-18

## Plain-English Result

This was the stronger W0 version of the hallucination-risk question.

Instead of asking the impossible row-level question, "which random branch will
this exact same prompt take later?", this scout asked a prompt-level product
question:

> Before generation starts, can W0 hidden states tell whether this prompt setup
> is high risk for unsupported answers?

The answer on this run is: **not as an internal hidden-state claim**.

There is prompt-level risk signal, but text sees it as well or better.

## Capture

- Model: `Qwen/Qwen2.5-0.5B-Instruct`
- Rows: `1392`
- Layers: `0..24`
- Hidden size: `896`
- Timing point: `W0`
- Generated-prefix tokens: `0`
- Source labeled bank:
  `docs/working/outcome_native_hallucination_generation_qwen05_hard_v2_20260618/outcome_native_labeled_prompt_bank.json`

## Prompt-Level Target

Unit:

`prompt_group_id`

Label rule:

- `HIGH_RISK` if unsupported answer rate is at least `0.25`
- `LOW_RISK` if unsupported answer rate is exactly `0.0`
- groups with fewer than `5` samples or middle rates are excluded

Evaluated groups:

- Total: `120`
- `LOW_RISK`: `85`
- `HIGH_RISK`: `35`

## Scout Result

Key report:

`prompt_level_w0_risk_scout.json`

Best hidden layer:

- Layer: `1`
- Hidden balanced accuracy: `0.835294`
- Word text balanced accuracy: `0.843697`
- Character text balanced accuracy: `0.821008`
- Hidden minus word text: `-0.008403`
- Hidden minus character text: `0.014286`

## Verdict

Correct status:

`OPEN / NOT LICENSED for internal W0 hallucination-risk detection.`

This is not a failure of the product lane. It means the W0 prompt-risk signal is
not uniquely internal on this bank. The same risk is readable from the prompt
and evidence text, so it belongs in a surface/evidence integrity warning system
unless a future hidden readout beats those controls.

## Archive

Heavy capture archive:

`D:\tksCAS-archive\outcome_native_hallucination_w0_prompt_risk_qwen05_hard_v2_20260618\outcome_native_hallucination_w0_prompt_risk_qwen05_hard_v2_20260618.tgz`

## Next Valid Move

For hallucination, the immediate marketable lane is:

`surface/evidence integrity warning before the answer is shown`

The internal hidden-state hallucination claim remains unlicensed until a future
bank produces hidden-state W0 or pre-display evidence that beats prompt text,
character text, generated-prefix text, layer-0, grouped-fold, shuffled-label,
and permutation controls.
