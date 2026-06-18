# CJT Bias/Vibration W0 Qwen v1 Audit Summary

## Verdict

`PASS` for a scoped PCBA/CJT paired hidden-response screen.

This is the first successful version of the PCBA/CJT lane after the v0 surface
leak failure. The v1 bank passed surface preflight first, then Qwen W0 hidden
states beat word, character, length, layer-0, payload/domain/family, shuffled,
and permutation controls on six layers.

## What Passed

- Model: `Qwen/Qwen2.5-1.5B-Instruct`
- Timing: `W0`
- Generated prefix tokens: `0` for all 72 rows
- Prompt bank:
  `live-trace-worker/scenarios/cjt_bias_vibration_bank_v1_20260618.json`
- Surface preflight:
  `docs/working/cjt_bias_vibration_surface_screen_v1_20260618.json`
- Full local archive:
  `D:\tksCAS-archive\cjt_bias_vibration_w0_qwen_v1_20260618\`

Passing layers:

- `18`
- `22`
- `23`
- `25`
- `27`
- `28`

Best layer: `18`

- hidden balanced accuracy: `0.8472222222222222`
- word-text delta balanced accuracy: `0.4583333333333333`
- char-text delta balanced accuracy: `0.4027777777777778`
- length delta balanced accuracy: `0.5`
- layer-0 delta balanced accuracy: `0.5`
- hidden-minus-char margin: `0.4444444444444444`
- hidden-minus-layer-0 margin: `0.3472222222222222`
- within-family payload permutation p: `0.000999000999000999`
- failed gates: none

Family breakdown on layer `18`:

- instruction-integrity: `0.875`
- factual-support: `0.8333333333333333`

## Plain English

The first PCBA/CJT bank failed because the risky prompts looked obviously
different from the control prompts. The hidden states moved, but so did the text.
That was not proof.

The v1 bank fixed that by putting the same safe, unsafe, supported, and
unsupported material in every prompt, then rotating a neutral active channel such
as `CHANNEL_A` or `CHANNEL_B`. The text-only baselines could no longer read the
label. After that, the W0 hidden states still separated risk perturbations from
controls on multiple layers.

So the honest result is:

CAS Harness now has evidence that Qwen carries a pre-output hidden-state response
to PCBA/CJT bias and vibration perturbations in this controlled paired design.

## What This Does Not Prove Yet

This does not yet license:

- universal hidden-state prompt-injection detection
- universal hidden-state hallucination detection
- prompt-injection removal or reversal
- hallucination prevention
- causal control
- live interception claims beyond this offline W0 evidence packet

Those claims still need separate same-prompt behavior-state and causal
intervention gates.

## Audit Artifacts

- Compact sweep summary:
  `docs/working/cjt_bias_vibration_w0_qwen_v1_20260618/cjt_bias_vibration_layer_sweep_summary.json`
- Per-layer reports:
  `docs/working/cjt_bias_vibration_w0_qwen_v1_20260618/eval/`
- Capture manifest:
  `docs/working/cjt_bias_vibration_w0_qwen_v1_20260618/enabled_predicate_w0_all_layers_manifest.json`
- Full heavy archive:
  `D:\tksCAS-archive\cjt_bias_vibration_w0_qwen_v1_20260618\`

## Next Gate

Use the passing layer window, starting with layer `18`, to build the causal
intervention test:

- no-op condition
- `+risk/refusal` direction
- `-risk/refusal` direction
- random same-norm direction
- paired seeds
- held-out prompt groups

Only that gate can upgrade this from hidden-response detection to causal proof
or removal/reversal.
