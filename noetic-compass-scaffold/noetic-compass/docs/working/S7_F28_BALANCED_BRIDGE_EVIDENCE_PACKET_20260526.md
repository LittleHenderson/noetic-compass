# S7-F28 Balanced Bridge Evidence Packet

- Trace ID: `s7-f28-balanced-bridge-gpt-neox-20b-20260526`
- Method: `S7-F28-BALANCED-BRIDGE`
- Model: `EleutherAI/gpt-neox-20b`
- Verdict: `FLAG_FOR_HUMAN_REVIEW`
- Evidence confidence: `0.803571`
- Confidence formula: `min(balanced_logistic_heldout_accuracy, probe_readable_positive_fraction, causal_control_pass, trace_gate_pass)`

## Core Results

- Balanced-logistic heldout Foundation accuracy: `0.868622`
- Foundation lacunarity: `0.006715`
- Label-cover ablation drop: `0.124424`
- Random-control mean drop: `0.000749`
- Wrong-cover drop: `0.001152`
- Probe-readable bridge delta: `0.596413`
- Probe-readable positive rows: `90/112`
- Trace diagnostic: `TRACE_DIAGNOSTICS_PASS` / `Amplifying`

## Why Not ACCEPT Yet

This packet assembles the evidence chain. It does not attach the final Stage 19/20/21 production verifier, so the public verdict stays `FLAG_FOR_HUMAN_REVIEW`.

## Caveats

- This packet is a GPT-NeoX-20B S7-F28 validation artifact, not a universal 20B/100B/300B proof.
- The verdict is FLAG_FOR_HUMAN_REVIEW because the Stage 19/20/21 production verifier layer is not attached.
- The trace diagnostic uses a numeric layer-trace proxy, not yet the discrete cas-engine CognitiveFractal orbit classifier.
- Activation-cover ablation is measured on captured hidden states; it is not the same as a live forward-pass steering hook.
- The packet records model identity and architecture, but no independent model-weight SHA is available in these artifacts.
