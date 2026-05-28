# GPT-NeoX-20B Stage 9 Original 40E Replication - 2026-05-27

## Status

The original Pythia-era Stage 9 40-Element fixture was run on real
`EleutherAI/gpt-neox-20b` weights on a RunPod H100 80GB.

Method label: `S9-40E-ORIGINAL-BASELINE-READOUT`

Plain-English name: **Stage 9 40-Element Original-Fixture Balanced Readout**

This is the corrected TKS40 replication path:

- original Stage 9 role-bound/counterfactual scenario fixture,
- real open-weight GPT-NeoX-20B hidden-state capture,
- all 44 layers captured,
- original fixed train/test split from the fixture metadata,
- `StandardScaler + LogisticRegression(C=0.1, class_weight="balanced")`,
- majority, shuffled-label, text-hash, and confirmed text-baseline controls.

## Headline

| Measure | Result |
| --- | ---: |
| Model | `EleutherAI/gpt-neox-20b` |
| Axis | 40 Elements: `10 Noetics x 4 Domains` |
| Rows | `8,320` |
| Classes | `40` |
| Samples per class | `208` |
| Train / test | `3,840 / 4,480` |
| Train/test group overlap | `0` |
| Best hidden layer | `2` |
| Hidden readout accuracy | `95.625%` |
| Hidden readout macro-F1 | `95.617%` |
| Confirmed CountVectorizer text baseline | `49.241%` |
| Text-hash baseline in evaluator | `50.000%` |
| Majority baseline | `2.500%` |
| Shuffled-label mean | `2.619%` |
| Shuffled-label max | `3.304%` |
| Pythia-160M 40E comparator | `89.800%` |

## Interpretation

This fixes the earlier compact-gloss TKS40 v0 problem.

The compact TKS40 v0 scenario library had a `100.00%` text-only baseline, so
it could not support a "CAS beats text" claim. The original Stage 9 fixture
does not have that failure. Under the modern diagnostic, the original Stage 9
text-only baseline is `49.241%`, and the GPT-NeoX-20B hidden-state probe reaches
`95.625%` on the same fixed split.

Plain English:

> On the original Stage 9 40-Element task, GPT-NeoX-20B's hidden states carry
> the TKS40/CAS structure far more strongly than surface text alone.

## Commands

Smoke capture first:

```bash
cd /workspace/cas-harness-large-eval
HF_HOME=/workspace/hf-cache TRANSFORMERS_CACHE=/workspace/hf-cache \
python live-trace-worker/scripts/capture_open_weight_probe_dataset.py \
  --model-id EleutherAI/gpt-neox-20b \
  --scenario-path data/stage9_original_40e_scenarios_20260527.json \
  --output data/stage9_smoke_2_gpt_neox_20b.npz \
  --metadata-output data/stage9_smoke_2_gpt_neox_20b.metadata.json \
  --torch-dtype float16 \
  --device-map auto \
  --layer-start 0 \
  --layer-end 43 \
  --max-scenarios 2 \
  --max-length 192
```

Full capture:

```bash
cd /workspace/cas-harness-large-eval
HF_HOME=/workspace/hf-cache TRANSFORMERS_CACHE=/workspace/hf-cache \
python live-trace-worker/scripts/capture_open_weight_probe_dataset.py \
  --model-id EleutherAI/gpt-neox-20b \
  --scenario-path data/stage9_original_40e_scenarios_20260527.json \
  --output data/gpt_neox_20b_stage9_original_40e_layers_0_43.npz \
  --metadata-output data/gpt_neox_20b_stage9_original_40e_layers_0_43.metadata.json \
  --torch-dtype float16 \
  --device-map auto \
  --layer-start 0 \
  --layer-end 43 \
  --max-scenarios 0 \
  --max-length 192
```

Evaluation:

```bash
cd /workspace/cas-harness-large-eval
python live-trace-worker/scripts/evaluate_40_element_probe.py \
  --dataset data/gpt_neox_20b_stage9_original_40e_layers_0_43.npz \
  --metadata data/gpt_neox_20b_stage9_original_40e_layers_0_43.metadata.json \
  --output results/gpt_neox_20b_stage9_original_40e_probe_eval_report.json \
  --scenario-path data/stage9_original_40e_scenarios_20260527.json \
  --split-key metadata.split \
  --test-split test \
  --group-key metadata.counterfactual_pair_id \
  --confirmed-text-baseline-report results/stage9_original_40e_text_baseline_diagnostic_20260527.json \
  --require-balanced-40e \
  --shuffled-trials 20 \
  --probe-C 0.1 \
  --probe-max-iter 1000 \
  --seed 2026
```

## Artifact Hashes

Remote artifact hashes from `/workspace/cas-harness-large-eval`:

```text
5f9a14714dcad87991a04a8317119b4eeb8097af7377446e59efb1c65f428610  data/gpt_neox_20b_stage9_original_40e_layers_0_43.npz
22d5e6c19c4dd25d549e82bc2509282634878df465967df1d68f11d90accf6ef  data/gpt_neox_20b_stage9_original_40e_layers_0_43.metadata.json
e90268444fd914f558b2244c90c9d039936fc273bdefbad266ebaf844d004030  results/gpt_neox_20b_stage9_original_40e_probe_eval_report.json
a1f155c379fada4547b75d7c3a3980d46db25aee38e509e6b813c292a8cf3b5a  results/gpt_neox_20b_stage9_original_40e_capture.log
```

The JSON report was corrected after the run to clarify that the fixed Stage 9
split was used; no numeric result was changed.

## What This Is Not

This is not yet a full Evidence Packet merge, causal ablation, eta-to-epsilon
bridge, or ACCEPT/SUPPRESS production verdict.

This is the corrected 40E hidden-state readout replication. It should feed the
next evidence tiers:

1. activation-level 40E cover/ablation,
2. matched random/wrong-cover controls,
3. eta-to-epsilon bridge on 40E,
4. trace diagnostics,
5. Evidence Packet merge.
