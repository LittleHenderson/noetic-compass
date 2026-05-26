# CAS Harness Large-Model RunPod Status — 2026-05-26

## Current RunPod

- SSH: `root@31.24.80.42 -p 18251`
- GPU: NVIDIA H100 80GB HBM3
- Workspace volume: `/workspace`, 187 GB available
- Atlas live worker: still running separately for Pythia-160M
- Large-eval workspace: `/workspace/cas-harness-large-eval`

## What genuinely ran

### Pythia-160M smoke

- Model: `EleutherAI/pythia-160m`
- Status: real model forward completed
- Layers: 0-2
- Scenarios: 2
- Output: `/workspace/cas-harness-large-eval/results/pythia_probe_smoke.json`
- Produced: `layer_activation_summary`, `worker_evidence_manifest`
- Missing by design: `cas_axis_readout`, `blindspot_overlay`

### GPT-NeoX-20B full activation pass

- Model: `EleutherAI/gpt-neox-20b`
- Parameter count recorded by runner: `20,554,567,680`
- Architecture: `GPTNeoXForCausalLM`
- Hidden size: `6144`
- Layers: `44`
- Attention heads: `64`
- Dtype: `torch.float16`
- Device map: `auto`
- Status: real model forward completed
- Layers captured: 0-43
- Scenarios: all 25 alpha scenarios
- Output on RunPod: `/workspace/cas-harness-large-eval/results/gpt_neox_20b_full_activation_layers_0_43.json`
- Local copy: `C:\tmp\gpt_neox_20b_full_activation_layers_0_43.json`
- Produced: `layer_activation_summary`, `worker_evidence_manifest`
- Missing by design: `cas_axis_readout`, `blindspot_overlay`

## What this proves

This proves the new open-weight probe-shard runner can load and run a real 20B open-weight transformer on H100, capture all transformer layers, and emit a non-fabricated evidence fragment.

It does **not** yet prove CAS universality at 20B, because the run did not include GPT-NeoX-20B-specific probe weights, cover maps, ablations, matched controls, or verifier merge.

## Why the missing fields are good, not bad

The runner did not invent proof. Because no GPT-NeoX-20B probe weights or cover maps were supplied, it returned:

- missing `cas_axis_readout`
- missing `blindspot_overlay`

That is the correct anti-fake behavior. The system can say, "we captured real 20B activations," but it cannot yet say, "CAS passed on 20B."

## Next required proof steps for 20B

1. Train or import GPT-NeoX-20B CAS probe weights.
2. Build GPT-NeoX-20B cover maps for the CAS drives/registers under test.
3. Run the same 25 alpha scenarios with:
   - probe readout
   - ablation/intervention
   - matched random/wrong-drive controls
   - output-effect prediction
   - Evidence Packet merge
4. Report accepted accuracy, coverage, confidence bands, and failures separately.

## 100B / 300B status

No genuine 100B or 300B model eval has run yet.

A single H100 80GB is not enough for a full 100B/300B open-weight audit in normal fp16/bf16 mode. Those runs require a fleet plan with multiple assigned workers, enough model storage, and returned receipts before the verifier is allowed to merge anything.

The correct next step is not to fake a 100B/300B run. The correct next step is to add workers and execute the distributed fleet path already being prepared in PRs #97/#98.
