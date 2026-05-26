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

### GPT-NeoX-20B probe dataset capture

- Model: `EleutherAI/gpt-neox-20b`
- Status: real model forward completed
- Scenario source: `/workspace/cas-harness-large-eval/scenarios/augmented_library.json`
- Labeled scenarios found: `400`
- Layers captured: 0-43
- Hidden size: `6144`
- Feature shape: `[400, 44, 6144]`
- Output on RunPod: `/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_augmented_400_layers_0_43.npz`
- Metadata on RunPod: `/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_augmented_400_layers_0_43.metadata.json`
- Local copies:
  - `C:\tmp\gpt_neox_20b_augmented_400_layers_0_43.npz`
  - `C:\tmp\gpt_neox_20b_augmented_400_layers_0_43.metadata.json`

### GPT-NeoX-20B heldout readout evaluation

- Evaluator: nearest-centroid readout over real hidden vectors
- Report on RunPod: `/workspace/cas-harness-large-eval/reports/gpt_neox_20b_probe_eval_report.json`
- Candidate cover map on RunPod: `/workspace/cas-harness-large-eval/reports/gpt_neox_20b_candidate_cover_map.json`
- Local copies:
  - `C:\tmp\gpt_neox_20b_probe_eval_report.json`
  - `C:\tmp\gpt_neox_20b_candidate_cover_map.json`

Metric summary:

| Axis | Best layer | Hidden test acc | Majority control | Shuffled-label control | Text-hash baseline | Honest read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Domain | 11 | 46.84% | 44.30% | 26.96% | 74.68% | Hidden beats weak controls; canonical English surface aliases are stronger here |
| Drive | 31 | 35.80% | 22.22% | 15.19% | 74.07% | Hidden beats weak controls; canonical English surface aliases are stronger here |
| Operator | 8 | 31.25% | 16.25% | 8.81% | 83.75% | Hidden beats weak controls; canonical English surface aliases are stronger here |

Interpretation: GPT-NeoX-20B contains recoverable CAS-labeled structure in the hidden states on this canonical-English dataset. The strong text baseline should not be described as "label leakage" by default: CAS colloquialisms are approved English aliases for the axes, so a text baseline doing well is evidence that the surface aliases are predictive. What this run does **not** yet establish is the stronger causal claim: that a localized internal CAS subspace or cover is load-bearing after accounting for the surface text signal. The next proof step is ablation/intervention against the candidate covers, not removing the canonical colloquialisms.

### GPT-NeoX-20B activation-level cover ablation

- Evaluator: `live-trace-worker/scripts/ablate_probe_dataset.py`
- Mode: activation-level train-mean replacement on already captured real GPT-NeoX-20B hidden vectors
- Top-16 report on RunPod: `/workspace/cas-harness-large-eval/reports/gpt_neox_20b_activation_cover_ablation_report_top16.json`
- Top-256 report on RunPod: `/workspace/cas-harness-large-eval/reports/gpt_neox_20b_activation_cover_ablation_report_top256.json`
- Top-256 cover map on RunPod: `/workspace/cas-harness-large-eval/reports/gpt_neox_20b_candidate_cover_map_top256.json`
- Local archive: `D:\tksCAS-archive\gpt_neox_20b_activation_cover_ablation_20260526`

Metric summary:

| Axis | Cover size | Clean acc | Label-cover ablated acc | Same-size random acc | Label-cover drop vs random | Honest read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Domain | 256/class | 46.84% | 43.04% | 46.90% mean | +3.86 pp | Label-specific cover beats same-size random; axis-union cover does not |
| Drive | 256/class | 35.80% | 32.10% | 35.80% mean | +3.70 pp | Label-specific cover beats same-size random; axis-union cover does not |
| Operator | 256/class | 31.25% | 28.75% | 31.25% mean | +2.50 pp | Label-specific cover beats same-size random; axis-union cover does not |

Top-16 covers did **not** reduce heldout top-1 accuracy on any axis. They did weaken label-specific readout margins more than same-size random controls, but that is not strong enough to call a causal pass.

Top-256 label-specific covers are the first 20B causal-control signal: replacing the true-label candidate cover dimensions hurt heldout accuracy more than same-size random replacements on domain, drive, and operator. This is promising, but it is still activation-level evidence only. It is **not** a live model-forward intervention, not a verifier verdict, and not a full CAS Harness ACCEPT on GPT-NeoX-20B.

### GPT-NeoX-20B 27H-style forward-pass cover ablation pilot

- Runner: `live-trace-worker/scripts/run_open_weight_cover_ablation.py`
- Model: `EleutherAI/gpt-neox-20b`
- Axis: `drive`
- Cover map: top-256 candidate covers
- Mode: suppress true-label cover coordinates during a fresh model forward pass, then score the true CAS drive verbalizer likelihood against wrong-cover and matched random-cover controls
- Pilot output on RunPod: `/workspace/cas-harness-large-eval/reports/gpt_neox_20b_forward_cover_ablation_drive_balanced14.json`
- Local copy: `C:\tmp\gpt_neox_20b_forward_cover_ablation_drive_balanced14.json`

Metric summary:

| Run | Rows | Drive balance | Mean target drop | Mean random drop | Target minus random | Target beats random mean | Honest read |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| First pilot | 6 | skewed mostly F7 | -0.0479 | +0.0730 | -0.1209 | 1/6 | Not usable as a balanced result |
| Balanced pilot | 14 | 2 rows each for F1-F7 | -0.0244 | +0.0140 | -0.0383 | 5/14 | Current cover does not pass 27H-style forward intervention |

The balanced pilot is a genuine 20B forward-pass intervention, but it is **not** a positive 27H result. Suppressing the current candidate drive covers did not reduce the true-drive verbalizer likelihood more than matched random controls. The likely next move is not to overclaim the result; it is to improve the cover/rubric pair:

1. build per-drive balanced scenarios specifically designed for 27H output scoring,
2. test alternative cover sizes and selection methods,
3. score against multiple verbalizers per drive instead of one sentence,
4. only then rerun the 27H forward-pass gate.

### Original-results audit correction

Re-reading the original CAS Harness notes changes the 20B priority. The strongest original Pythia evidence was **not** drive-only forward steering. It was the 28-Foundation chain:

- 28 Foundations readout: Pythia-160M `78.6%`, `+28.9 pp` over text baseline, p about `1e-95`.
- Foundation subspace ablation: `78.6% -> 3.57%`, exact `1/28` chance.
- Random same-rank ablations: clean/null.
- 28-Foundation lacunarity: `0.021`, far cleaner than the noisier Noetic axis.
- 40-Element readout: `89.8%`, `+39.7 pp` over text baseline.
- Likelihood-tier eta-to-epsilon bridge: Pythia-160M `+0.283`, Pythia-1B `+0.554`.

The same notes also record null or bounded results that must not be confused with the closed claim:

- Stage 6.6 noetic generation steering: NULL.
- Stage 7.3 drive-subspace generation steering: NULL, p = `1.0`.
- Stage 7.LA late-layer additive steering: NULL.
- Stage 27H / 27I prefix-plus-neuron steering: diagnostic/null at Pythia-160M scale, not free-form generation control.

So the current 20B drive-only forward pilot is a useful negative diagnostic, but it is **not** the proper replication of the original success. The correct 20B proof path is to build a real 28-Foundation dataset (`drive x register`), train/evaluate 28-Foundation readouts, run matched ablation/intervention against those covers, and only then attempt the Foundation-level likelihood/output bridge.

## What this proves

This proves the new open-weight probe-shard runner can load and run a real 20B open-weight transformer on H100, capture all transformer layers, emit a non-fabricated evidence fragment, capture raw hidden vectors for 400 labeled scenarios, train/evaluate heldout readout probes, and run an activation-level matched-control ablation over candidate covers.

It does **not** yet prove CAS universality at 20B. The current evidence includes heldout readout, activation-level matched-control ablation, and a first genuine 27H-style forward-pass pilot. The forward-pass pilot is currently null against random controls, so the 20B behavioral intervention claim remains open.

## Why the missing fields are good, not bad

The first-pass runner did not invent proof. Because no GPT-NeoX-20B probe weights or cover maps were supplied, it returned:

- missing `cas_axis_readout`
- missing `blindspot_overlay`

That is the correct anti-fake behavior. The system can now say, "we captured real 20B activations and got a first heldout readout signal above weak controls." It cannot yet say, "CAS passed on 20B."

## Next required proof steps for 20B

1. Keep the canonical CAS colloquialisms; do not treat approved English aliases as contamination.
2. Build or recover a balanced 28-Foundation scenario set (`F1..F7 x T/A/f/E`). The current 400-row 20B dataset has domain, drive, and operator labels only; it does **not** contain register/foundation labels in the captured metadata.
3. Capture GPT-NeoX-20B hidden states for that Foundation-labeled set.
4. Train/evaluate the 28-Foundation readout and compare it against weak controls plus the canonical-English surface baseline.
5. Run Foundation-level subspace/cover ablation with matched random and wrong-Foundation controls.
6. Only after the Foundation readout/intervention gate passes, run the 27H-style likelihood/output bridge at the Foundation level.
7. Run the same scenario set with:
   - probe readout
   - ablation/intervention
   - matched random/wrong-label controls
   - output-effect prediction
   - Evidence Packet merge
8. Report accepted accuracy, coverage, confidence bands, and failures separately.

## 100B / 300B status

No genuine 100B or 300B model eval has run yet.

A single H100 80GB is not enough for a full 100B/300B open-weight audit in normal fp16/bf16 mode. Those runs require a fleet plan with multiple assigned workers, enough model storage, and returned receipts before the verifier is allowed to merge anything.

The correct next step is not to fake a 100B/300B run. The correct next step is to add workers and execute the distributed fleet path already being prepared in PRs #97/#98.
