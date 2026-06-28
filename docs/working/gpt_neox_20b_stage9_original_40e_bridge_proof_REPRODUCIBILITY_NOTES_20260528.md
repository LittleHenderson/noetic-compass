# GPT-NeoX-20B Stage 9 Original 40E Bridge Proof Reproducibility Notes

Date: 2026-05-28

## Run

- Model: `EleutherAI/gpt-neox-20b`
- Hardware: RunPod H100 80GB HBM3
- Remote working directory: `/workspace/cas-harness-large-eval`
- Scenario set: `data/stage9_original_40e_scenarios_20260527.json`
- Activation dataset: `data/gpt_neox_20b_stage9_original_40e_layers_0_43.npz`
- Readout layer: `2`
- Readout method: balanced logistic readout over Stage 9 original 40E labels
- Bridge method: eta-to-epsilon readable prefix likelihood bridge
- Case selection: `--per-element 2`, 80 total cases, seed `20260528`

## Command

```powershell
ssh root@38.80.152.148 -p 30987 -i ~/.ssh/id_ed25519
```

```bash
cd /workspace/cas-harness-large-eval
HF_HOME=/workspace/hf-cache TRANSFORMERS_CACHE=/workspace/hf-cache python live-trace-worker/scripts/run_stage9_40e_eta_epsilon_bridge.py \
  --model-id EleutherAI/gpt-neox-20b \
  --scenario-path data/stage9_original_40e_scenarios_20260527.json \
  --dataset data/gpt_neox_20b_stage9_original_40e_layers_0_43.npz \
  --eval-report results/gpt_neox_20b_stage9_original_40e_probe_eval_report.json \
  --output results/gpt_neox_20b_stage9_original_40e_eta_epsilon_bridge_per2_20260528T0455Z.json \
  --output-md results/gpt_neox_20b_stage9_original_40e_eta_epsilon_bridge_per2_20260528T0455Z.md \
  --readout-layer 2 \
  --per-element 2 \
  --selection-seed 20260528 \
  --readout-seed 20260527 \
  --torch-dtype float16 \
  --device-map auto \
  --max-length 256
```

## Result

- Status: `PROBE_PREDICTED_40E_ETA_EPSILON_BRIDGE_PASS`
- Cases: `80`
- Selected element accuracy: `0.975`
- Selected operator accuracy: `0.975`
- Selected domain accuracy: `1.000`
- All-test element accuracy: `0.952679`
- Probe-readable delta vs none: `+1.412050`
- Probe-readable minus partner-readable margin: `+2.881239`
- Gold-readable delta vs none: `+1.497513`
- Gold-readable minus partner-readable margin: `+2.966701`
- Probe raw delta vs none: `+0.013817`
- Gold raw delta vs none: `+0.013427`

Interpretation: readable epsilon realization is load-bearing; raw CAS symbols are not. The bridge proof is present in the Evidence Packet, but the packet remains `FLAG_FOR_HUMAN_REVIEW` because the verifier decision layer is still missing.

## Archive

Archive path:

```text
D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_bridge_proof_20260528
```

Integrity manifest:

```text
SHA256SUMS.txt
```

Verify from the archive folder with:

```powershell
Get-FileHash -Algorithm SHA256 .\gpt_neox_20b_stage9_original_40e_eta_epsilon_bridge_per2_20260528T0455Z.json
Get-FileHash -Algorithm SHA256 .\gpt_neox_20b_stage9_original_40e_eta_epsilon_bridge_per2_20260528T0455Z.md
Get-FileHash -Algorithm SHA256 .\gpt_neox_20b_stage9_original_40e_evidence_packet_20260528T0455Z.json
Get-FileHash -Algorithm SHA256 .\gpt_neox_20b_stage9_original_40e_evidence_packet_20260528T0455Z.md
Get-FileHash -Algorithm SHA256 .\gpt_neox_20b_stage9_original_40e_eta_epsilon_bridge_per2_20260528T0455Z.log
```
