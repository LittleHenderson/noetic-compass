# CJT Bias/Vibration W0 Qwen Result

## Verdict

`FAIL` for a hidden-state/internal claim.

The PCBA mechanism remains promising, but the v0 bank is surface-leaky. Qwen
W0 hidden-state deltas separate the risk/control roles very strongly, but word,
character, and length baselines also separate them. That means the current
artifact cannot prove internal prompt-injection or hallucination-risk detection.

## Run

- Model: `Qwen/Qwen2.5-1.5B-Instruct`
- Timing: `W0`
- Generated tokens: `0`
- Rows: `72`
- Layers: `29` (`0..28`)
- Hidden size: `1536`
- Prompt bank:
  `live-trace-worker/scenarios/cjt_bias_vibration_bank_v0_20260618.json`
- Local full archive:
  `D:\tksCAS-archive\cjt_bias_vibration_w0_qwen_20260618\`

## Best Observed Layer

Layer `1` reached perfect hidden separation, but failed the surface controls:

- hidden balanced accuracy: `1.0`
- word-text delta balanced accuracy: `0.9166666666666667`
- char-text delta balanced accuracy: `0.9583333333333333`
- length delta balanced accuracy: `0.9722222222222222`
- layer-0 delta balanced accuracy: `0.5`
- hidden-minus-char margin: `0.04166666666666674`
- permutation p: `0.000999000999000999`

Failed gates:

- `text_margin_pass`
- `char_text_margin_pass`
- `length_margin_pass`

No layer passed.

## Surface Preflight

After the pod run exposed the leakage, a dedicated surface preflight was added:

`live-trace-worker/scripts/screen_cjt_bias_vibration_surface_leakage.py`

The v0 bank is now correctly blocked before GPU capture:

- status: `BLOCKED_SURFACE_LEAKAGE`
- word-text delta BA: `0.9166666666666667`
- char-text delta BA: `0.9583333333333333`
- length delta BA: `0.9722222222222222`

Report:

`docs/working/cjt_bias_vibration_surface_screen_v0_20260618.json`

## Plain-English Interpretation

The hidden states moved in a real, structured way, but the prompt wording made
the answer too easy for a text baseline. This means v0 mostly tests whether the
bank's role labels are visible in the prompt, not whether CAS Harness has found
a payload-independent internal detector.

The next correct move is not another GPU run on v0. The next move is a
surface-balanced v1 bank where:

- all variants use the same section structure,
- role text and lengths are counterbalanced,
- risky and control rows both contain similar trusted/untrusted/evidence blocks,
- surface preflight must pass before W0 capture,
- only then do we rerun the hidden-state delta evaluator.

## Claim Boundary

Remain:

- hidden-state prompt-injection detection: `OPEN / NOT LICENSED`
- hidden-state hallucination detection: `OPEN / NOT LICENSED`
- prompt-injection prevention/removal/reversal: `OPEN / NOT LICENSED`
- live interception: `OPEN / NOT LICENSED`
- causal proof: `OPEN / NOT LICENSED`

