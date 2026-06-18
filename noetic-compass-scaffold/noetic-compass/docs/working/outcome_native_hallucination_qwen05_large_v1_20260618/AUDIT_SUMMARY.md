# CAS Harness Outcome-Native Hallucination Trajectory Audit

Date: 2026-06-18

Model: `Qwen/Qwen2.5-0.5B-Instruct`

Archive:
`D:\tksCAS-archive\outcome_native_hallucination_qwen05_large_v1_20260618\`

## Purpose

This run tested a stricter hallucination-detection path: label the model's actual generated answer first, then ask whether early hidden states predict whether that answer will be supported or unsupported by trusted evidence.

This is not a prevention test and not a causal proof.

## Data Result

The 800-row outcome-native bank produced real unsupported factual outputs:

- Total generations: `800`
- Binary labeled rows: `576`
- `SUPPORTED`: `541`
- `UNSUPPORTED`: `35`
- Excluded non-binary rows: `224`
- `NO_CLAIM`: `210`
- `AMBIGUOUS`: `14`
- Mixed exact-prompt groups: `28`

This is the first useful outcome-native hallucination dataset for this lane because labels came from judged model outputs, not prewritten row labels.

## Timing Results

All timing scouts are `FAIL` for licensing internal hallucination detection.

| Timing | Best Layer | Hidden BA | Text BA | Prefix Char BA | Status | Main Failure |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `W1` | `1` | `0.662371` | `0.481357` | `0.603908` | `FAIL` | Hidden BA below gate and prefix/layer-0 controls not beaten |
| `W8` | `15` | `0.652786` | `0.481357` | `0.547082` | `FAIL` | Hidden BA below gate and prefix/layer-0 controls not beaten |
| `W16` | `1` | `0.793478` | `0.482609` | `0.726812` | `FAIL` | Stronger signal, but not cleanly internal: generated-prefix and layer-0 controls explain too much |

## Claim Boundary

`hidden-state hallucination detection` remains `OPEN / NOT LICENSED`.

`hallucination prevention` remains `OPEN / NOT LICENSED`.

`causal proof` remains `OPEN / NOT LICENSED`.

The honest product claim remains:

> CAS Harness can flag prompt-injection and instruction-integrity risk before the model's answer is shown, with Evidence Packet audit trails.

This run supports a research next step, not a public hidden-state hallucination claim.

## What This Proves

It proves the benchmark design is now viable enough to produce real supported versus unsupported outcomes on the same model family.

It does not prove CAS Harness can internally detect hallucinations before display.

## Next Gate

Build the next hallucination bank around more unsupported-balanced outcome variation, not around easier trusted-evidence prompts.

Minimum next data target:

- At least `80` unsupported outputs.
- At least `40` mixed exact-prompt groups.
- At least `8` unsupported rows per topic.
- Keep W1/W8/W16 controls.
- Require hidden-state BA `>= 0.75`.
- Require hidden-state margin `>= 0.15` over prompt text, char text, layer-0, and generated-prefix controls.

Only after that passes should causal or prevention work begin.
