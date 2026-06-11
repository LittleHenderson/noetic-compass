# Qwen pre-speech behavior probe diagnostic

**Date:** 2026-06-10
**Status:** Diagnostic complete; pre-speech/live claim remains OPEN.

## Plain-English result

We built the missing local bridge from the archived Qwen traces into the normal
probe dataset format, then tested the actual prompt-stage vector before any
generated text. The raw bucket problem is fixed for a diagnostic run:

- COMPLIED: 161
- REFUSED: 143
- Feature: `raw_prompt_vec`
- Layer: 14
- Rows: 304

The global prompt-stage probe separates behavior, but it does not clear the
honesty gate. The text-only baseline beats the hidden-state probe, which means
the readout is probably reading the kind of request/payload, not a clean
internal comply/refuse state.

## Artifacts

- Dataset: `D:\tksCAS-archive\qwen_prespeech_behavior_probe_20260610\qwen_prompt_behavior_raw_prompt_vec.npz`
- Manifest: `D:\tksCAS-archive\qwen_prespeech_behavior_probe_20260610\qwen_prompt_behavior_raw_prompt_vec_manifest.json`
- Global eval: `D:\tksCAS-archive\qwen_prespeech_behavior_probe_20260610\qwen_prompt_behavior_eval_report.json`
- Within-payload eval: `D:\tksCAS-archive\qwen_prespeech_behavior_probe_20260610\qwen_prompt_behavior_within_payload_report.json`

## Global readout

`behavior` axis:

- Test accuracy: 0.852459
- Test macro F1: 0.851018
- Majority baseline: 0.524590
- Shuffled-label hidden control mean: 0.517213
- Text-hash baseline: 0.885246
- Hidden minus text: -0.032787

Interpretation: useful diagnostic separation, but not activation-native evidence
because the text baseline is stronger.

## Payload-controlled gate

Within-payload status: `blocked_insufficient_within_payload_n`

Only one payload class currently has both COMPLIED and REFUSED with at least
three examples:

- `overt_5`: COMPLIED 7, REFUSED 5, within-payload test accuracy 0.5

This blocks the pre-speech claim. The refusal bucket is full globally, but the
dataset is still payload-confounded. A causal/live claim would be premature.

## What this changes

The old bottleneck was described as "not enough refusals." That was true for
the original frozen run, but after adding v3 refusal traces the sharper
bottleneck is:

> not enough COMPLIED and REFUSED examples inside the same payload classes.

The next capture should target mixed payload classes, not just more refusal
examples. Minimum useful target:

- At least three payload classes with COMPLIED >= 8 and REFUSED >= 8 each
- Better target: five payload classes with COMPLIED >= 10 and REFUSED >= 10 each
- Keep prompt-stage W0 as the claim gate
- Do not run causal/live ablation as a claim until the within-payload gate passes

## Repro commands

```powershell
python live-trace-worker/scripts/build_behavior_probe_dataset.py --capture 'D:\tksCAS-archive\qwen_confirmatory_20260610\captures_qwen_20260610.jsonl' --capture 'D:\tksCAS-archive\qwen_confirmatory_v3_20260610\captures_qwen_v3r_20260610.jsonl' --labels 'D:\tksCAS-archive\qwen_confirmatory_20260610\consensus_labels_qwen_20260610.jsonl' --labels 'D:\tksCAS-archive\qwen_confirmatory_20260610\majority_labels_qwen_20260610.jsonl' --labels 'D:\tksCAS-archive\qwen_confirmatory_20260610\adjudication_captures_qwen_20260610.verified_labels.jsonl' --labels 'D:\tksCAS-archive\qwen_confirmatory_v3_20260610\consensus_labels_qwen_v3r_20260610.jsonl' --corpus 'D:\tksCAS-archive\qwen_confirmatory_20260610\injected_overt_combined_240_20260609.jsonl' --corpus 'D:\tksCAS-archive\qwen_confirmatory_20260610\clean_instruction_40_20260610.jsonl' --corpus 'D:\tksCAS-archive\qwen_confirmatory_v3_20260610\injected_overt_v3r_120_20260610.jsonl' --output 'D:\tksCAS-archive\qwen_prespeech_behavior_probe_20260610\qwen_prompt_behavior_raw_prompt_vec.npz' --metadata-output 'D:\tksCAS-archive\qwen_prespeech_behavior_probe_20260610\qwen_prompt_behavior_raw_prompt_vec_manifest.json'

python live-trace-worker/scripts/evaluate_probe_dataset.py --dataset 'D:\tksCAS-archive\qwen_prespeech_behavior_probe_20260610\qwen_prompt_behavior_raw_prompt_vec.npz' --output-report 'D:\tksCAS-archive\qwen_prespeech_behavior_probe_20260610\qwen_prompt_behavior_eval_report.json' --output-cover-map 'D:\tksCAS-archive\qwen_prespeech_behavior_probe_20260610\qwen_prompt_behavior_cover_map.json' --min-class-count 3 --seed 42

python live-trace-worker/scripts/evaluate_behavior_within_payload.py --dataset 'D:\tksCAS-archive\qwen_prespeech_behavior_probe_20260610\qwen_prompt_behavior_raw_prompt_vec.npz' --output-report 'D:\tksCAS-archive\qwen_prespeech_behavior_probe_20260610\qwen_prompt_behavior_within_payload_report.json' --min-class-count 3 --min-testable-payload-classes 3 --seed 42
```

