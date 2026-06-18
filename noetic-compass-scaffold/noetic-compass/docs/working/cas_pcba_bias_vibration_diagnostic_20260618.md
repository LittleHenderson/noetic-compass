# CAS PCBA Bias/Vibration Diagnostic

## Plain-English Answer

Yes: the CAS PCBA Engineer book points to a better solution path than the old
one-shot hidden-state classifier.

The book says a safety circuit is not certified by asking "did the final answer
look safe?" It is certified by probing named internal test points and measuring
whether the circuit's bias, gain, saturation, and feedback behave correctly.
For CAS Harness, that means the next internal detector should measure how the
model's hidden state moves under controlled paired perturbations:

- `^5` bias: does untrusted low-authority text move the model's high-authority
  safety substrate?
- `^4` Vibration: does an unsupported factual lure create a strong internal
  resonance before the answer is shown?
- `beta/gm/r_pi`: how much does the hidden state move when the cause or framing
  is nudged?
- `E-CJT-008` cross-domain bias: can quoted/untrusted text bias a principled
  or policy-level state?

That is a stronger experiment because it stops asking, "Can a probe read the
label from one hidden vector?" and starts asking, "Can the system measure the
model's internal response curve the way an engineer measures a transistor?"

## Book Basis

- `book/CAS_PCBA_Engineer/Chapter_09_CJT_Deep_Dive.md:28-31` defines beta,
  `gm`, `r_pi`, and saturation as the core CJT datasheet quantities.
- `book/CAS_PCBA_Engineer/Chapter_09_CJT_Deep_Dive.md:117-145` says the
  operating point must sit in the active region, not cutoff or saturation.
- `book/CAS_PCBA_Engineer/Chapter_16_Feedback_Systems.md:293-303` describes a
  self-monitoring loop that watches beta drift and re-trims bias.
- `book/CAS_PCBA_Engineer/Chapter_18_CSB_Cognitive_Safety_Board.md:146-148`
  says injection framing should cancel as common-mode signal in a differential
  pair, if the bias is shared.
- `book/CAS_PCBA_Engineer/Chapter_18_CSB_Cognitive_Safety_Board.md:176-182`
  says the slow low-pass feedback protects the constitution from being rewritten
  by a single burst.
- `book/CAS_PCBA_Engineer/Chapter_23_Testing_Cognitive_Circuits.md:27-31`
  defines the CJT gain unit test as a Fisher-Rao response ratio.
- `book/CAS_PCBA_Engineer/Chapter_26_Governance.md:37-56` names
  `E-CJT-008 CjtCrossDomainBias` as a structural certification failure and a
  prompt-injection signature.

## What I Built

Two runnable artifacts now turn that book insight into a CAS Harness lane:

1. `live-trace-worker/scripts/build_cjt_bias_vibration_bank.py`

   Builds paired prompt groups. Each group has:
   - base trusted prompt,
   - benign paraphrase control,
   - untrusted prompt-injection perturbation,
   - trusted correction control,
   - supported factual candidate,
   - unsupported factual lure.

2. `live-trace-worker/scripts/evaluate_cjt_bias_vibration_diagnostic.py`

   Evaluates captured activations by subtracting the base hidden state from
   each perturbation hidden state, then testing whether hidden deltas separate
   risky perturbations from controls while beating word text, character text,
   length, layer-0, payload/domain, family, shuffled-label, and grouped
   permutation controls.

The all-layer W0 capture script now preserves the new PCBA metadata fields:
`labels_cjt_role`, `labels_cjt_family`, `labels_cjt_pair_role`,
`labels_trusted_authority`, and `labels_pcba_expected_signal`.

## Claim Boundary

This is a real solution path, but not a licensed public claim yet.

It can become an internal detection claim only if a real pod capture passes the
new evaluator on held-out prompt groups and beats the controls. It still does
not prove prevention, removal, reversal, live interception, or causality. Those
require the separate intervention gate.

## Next Execution

Generate the bank:

```powershell
python live-trace-worker\scripts\build_cjt_bias_vibration_bank.py `
  --samples-per-variant 2 `
  --output live-trace-worker\scenarios\cjt_bias_vibration_bank_v0_20260618.json `
  --summary-output docs\working\cjt_bias_vibration_bank_v0_20260618_summary.json
```

Capture W0 on the pod:

```powershell
python live-trace-worker\scripts\capture_enabled_predicate_w0_all_layers.py `
  --model-id Qwen/Qwen2.5-1.5B-Instruct `
  --prompt-bank live-trace-worker\scenarios\cjt_bias_vibration_bank_v0_20260618.json `
  --output-dir D:\tksCAS-archive\cjt_bias_vibration_w0_qwen_20260618 `
  --layers all `
  --timing-point W0
```

Evaluate a candidate nonzero layer:

```powershell
python live-trace-worker\scripts\evaluate_cjt_bias_vibration_diagnostic.py `
  --dataset D:\tksCAS-archive\cjt_bias_vibration_w0_qwen_20260618\enabled_predicate_w0_all_layers_dataset.npz `
  --layer 14 `
  --output-report docs\working\cjt_bias_vibration_w0_qwen_20260618_layer14.json `
  --permutations 1000 `
  --shuffle-controls 50
```

