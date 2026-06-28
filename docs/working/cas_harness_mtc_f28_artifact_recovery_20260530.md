# MTC.1 F28 Artifact Recovery - Agent F

Date: 2026-05-30
Owner: Agent F
Scope: find or recover the exact GPT-NeoX-20B Stage 7 / Foundation-28 activation NPZ needed for the MTC.1 F28 nested-control lane.
Write scope used: this file only.

## Verdict

The exact Stage 7 / Foundation-28 GPT-NeoX-20B activation artifact needed for MTC.1 is:

```text
gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz
```

Canonical remote path from reproducibility notes and reports:

```text
/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz
```

I did not find this NPZ in the local repo or in `D:\tksCAS-archive`. I also checked the staging path named in the evidence packet, `C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526`, because the notes point there; the metadata, scenario, reports, cover map, and packet are present, but the NPZ itself is missing.

Artifact-wise, the F28 nested control cannot run tonight, May 30, 2026, from verified local disk without retrieval or recapture. It can run without recapture only if the old RunPod volume, a snapshot, Cloud Sync, or another external copy still has the canonical remote NPZ.

## Exact Artifact Identity

The matching metadata file is present at:

```text
C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.metadata.json
```

Metadata hash:

```text
9F698313C376EB91E8317E22CC96BE7E729C96E1269A2835065009B55DAC9381
```

Scenario file:

```text
C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\stage7_foundation_rolebound_pilot_20260526.json
```

Scenario hash:

```text
5B8AAD738CA22AFEC11C60186981193ED3B951A4E13DA3FD7BFD5F7ACB54D46D
```

Metadata summary:

```text
model_id: EleutherAI/gpt-neox-20b
schema_version: cas_harness_open_weight_probe_dataset.v1
feature_shape: [4368, 44, 6144]
layers: 0..43
scenario_count: 4368
classes: 28 Foundation labels
balance: 156 rows per F1..F7 x T/A/f/E class
metadata output: datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz
metadata scenario: scenarios/stage7_foundation_rolebound_pilot_20260526.json
```

Important: I did not find an original SHA256 for the missing NPZ in the inspected SHA files. The archive hashes bind reports and packet files, not the activation NPZ. If the old NPZ is recovered, hash it immediately and preserve that SHA beside the restored file.

## Local Search Results

Missing exact local paths checked:

```text
D:\tksCAS-archive\gpt_neox_20b_balanced_logistic_closure_20260526\gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz
C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz
```

Both returned `False` in read-only `Test-Path` checks.

Archive directory with the F28 reports and packet, but not the NPZ:

```text
D:\tksCAS-archive\gpt_neox_20b_balanced_logistic_closure_20260526
```

Relevant hashes from that archive:

```text
94010bbd17ff2e6abd43a94ebe5ca68ba00ad94ee409e4add54ed85a759d8eeb  gpt_neox_20b_stage7_eta_epsilon_bridge_logistic.json
3f5706c33f67dac52c06a79390431850c4b13ba077e59346f81cfca29bc074c9  gpt_neox_20b_stage7_foundation_rolebound_probe_eval_report_top256.json
01346fd74aeb73e56b2982e78a8e3db684b0e0a5c617c701399a3a5a8989c922  gpt_neox_20b_stage7_trace_diagnostics_logistic.json
d7eb3e3f032266010472c42cb51c1a32e092a6bc37fb72ad8e952107f0ee1136  S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json
40c96278b7e625576e7f41f8b4ca08ee62fe577dd0e97570eb339e27b8d1f63b  S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.md
```

The repo does contain older Stage 7 Foundation NPZs:

```text
noetic-compass-scaffold\noetic-compass\research\cas_probe\stage7_foundation_pilot_activations_20260517.npz
noetic-compass-scaffold\noetic-compass\research\cas_probe\stage7_foundation_pilot_smoke_activations_20260517.npz
```

They are not substitutes. The smoke manifest records `EleutherAI/pythia-160m`, hidden dim `768`, `56` records, and 13 layer positions. Hashes observed:

```text
F63A66DE86366A63EA0FD786AD0DC0BEF68D5634BE3B5FAE525D4FB667F14D53  stage7_foundation_pilot_activations_20260517.npz
04800D4263E16FF1AA25653D58FE8DB3531A9035602429EA7E658413320B4913  stage7_foundation_pilot_smoke_activations_20260517.npz
```

Other do-not-use NPZs found:

```text
D:\tksCAS-archive\gpt_neox_20b_probe_dataset_eval_20260526\gpt_neox_20b_augmented_400_layers_0_43.npz
D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\gpt_neox_20b_stage9_original_40e_layers_0_43.npz
```

The first is a 400-row augmented GPT-NeoX dataset, not the exact Stage 7 role-bound F28 fixture. The second is the Stage 9 original 40E artifact, not F28.

## Evidence That This Is The Claim-Bearing F28 Fixture

The restored large-model status note identifies the exact original Stage 7 Foundation-28 rerun as:

```text
Scenario source: /workspace/cas-harness-large-eval/scenarios/stage7_foundation_rolebound_pilot_20260526.json
Original JSONL: /workspace/cas-harness-large-eval/original_stage7/stage7_foundation_pilot_20260517.jsonl
Original manifest: /workspace/cas-harness-large-eval/original_stage7/stage7_foundation_pilot_manifest_20260517.json
Dataset: /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz
Metadata: /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.metadata.json
Eval report: /workspace/cas-harness-large-eval/reports/gpt_neox_20b_stage7_foundation_rolebound_probe_eval_report_top256.json
Ablation report: /workspace/cas-harness-large-eval/reports/gpt_neox_20b_stage7_foundation_rolebound_activation_cover_ablation_report_top256.json
```

The balanced-logistic closure notes use the same dataset path for both the eta-to-epsilon bridge and the trace diagnostics. The existing packet result is `S7-F28-BALANCED-BRIDGE`, with heldout Foundation accuracy `0.868622`, Foundation lacunarity `0.006715`, and probe-readable bridge delta `0.596413`.

## Remote Check

Recorded RunPod endpoints found in notes:

```text
root@31.24.80.42 -p 18251
root@38.80.152.148 -p 30987
```

I ran read-only `ssh ls` checks against both endpoints for the NPZ, metadata, and scenario paths. Both timed out on 2026-05-30:

```text
ssh: connect to host 31.24.80.42 port 18251: Connection timed out
ssh: connect to host 38.80.152.148 port 30987: Connection timed out
```

This does not prove the volume is gone. It only means neither recorded SSH endpoint was reachable from this session.

## Safe Retrieval Commands

Use these only after confirming which endpoint is active. They create a new timestamped archive directory and avoid overwriting an existing local folder.

Primary endpoint from the May 26 large-model status note:

```powershell
$Remote = "root@31.24.80.42"
$Port = 18251
$Key = "$env:USERPROFILE\.ssh\id_ed25519"

$RemoteDataset = "/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz"
$RemoteMetadata = "/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.metadata.json"
$RemoteScenario = "/workspace/cas-harness-large-eval/scenarios/stage7_foundation_rolebound_pilot_20260526.json"

ssh -o BatchMode=yes -o ConnectTimeout=20 -i $Key -p $Port $Remote "ls -lh $RemoteDataset $RemoteMetadata $RemoteScenario"

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Archive = "D:\tksCAS-archive\gpt_neox_20b_stage7_foundation_rolebound_activations_$Stamp"
New-Item -ItemType Directory -Path $Archive -ErrorAction Stop | Out-Null

scp -i $Key -P $Port "${Remote}:$RemoteDataset" "$Archive\"
scp -i $Key -P $Port "${Remote}:$RemoteMetadata" "$Archive\"
scp -i $Key -P $Port "${Remote}:$RemoteScenario" "$Archive\"

Get-ChildItem -LiteralPath $Archive -File | Sort-Object Name | ForEach-Object {
  Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName
}
```

Fallback endpoint from the Stage 9 bridge proof notes:

```powershell
$Remote = "root@38.80.152.148"
$Port = 30987
$Key = "$env:USERPROFILE\.ssh\id_ed25519"

$RemoteDataset = "/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz"
$RemoteMetadata = "/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.metadata.json"
$RemoteScenario = "/workspace/cas-harness-large-eval/scenarios/stage7_foundation_rolebound_pilot_20260526.json"

ssh -o BatchMode=yes -o ConnectTimeout=20 -i $Key -p $Port $Remote "ls -lh $RemoteDataset $RemoteMetadata $RemoteScenario"

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Archive = "D:\tksCAS-archive\gpt_neox_20b_stage7_foundation_rolebound_activations_$Stamp"
New-Item -ItemType Directory -Path $Archive -ErrorAction Stop | Out-Null

scp -i $Key -P $Port "${Remote}:$RemoteDataset" "$Archive\"
scp -i $Key -P $Port "${Remote}:$RemoteMetadata" "$Archive\"
scp -i $Key -P $Port "${Remote}:$RemoteScenario" "$Archive\"

Get-ChildItem -LiteralPath $Archive -File | Sort-Object Name | ForEach-Object {
  Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName
}
```

If the NPZ is found on a volume snapshot or cloud-sync mount instead of SSH, copy the same three files into a new dated archive directory and hash them immediately. Do not place the multi-GB NPZ in git.

## Shortest Recapture Path If Retrieval Fails

Recapture is a fallback, not exact artifact recovery. It should preserve the same scenario row order, model ID, layers, dtype, and output name, but it will produce a new NPZ hash and may vary if package/model-cache state differs.

Prerequisites on an H100 80GB pod or equivalent:

```text
/workspace/cas-harness-large-eval/live-trace-worker
/workspace/cas-harness-large-eval/scenarios/stage7_foundation_rolebound_pilot_20260526.json
/root/atlas-live-worker-venv/bin/python
cached or downloadable EleutherAI/gpt-neox-20b weights
```

If the scenario file is missing on the pod, upload the local copy first:

```powershell
$Remote = "root@31.24.80.42"
$Port = 18251
$Key = "$env:USERPROFILE\.ssh\id_ed25519"
$LocalScenario = "C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\stage7_foundation_rolebound_pilot_20260526.json"

ssh -i $Key -p $Port $Remote "mkdir -p /workspace/cas-harness-large-eval/scenarios /workspace/cas-harness-large-eval/datasets /workspace/hf-cache /workspace/tmp"
scp -i $Key -P $Port $LocalScenario "${Remote}:/workspace/cas-harness-large-eval/scenarios/stage7_foundation_rolebound_pilot_20260526.json"
```

Run recapture on the pod:

```bash
cd /workspace/cas-harness-large-eval/live-trace-worker
mkdir -p /workspace/cas-harness-large-eval/datasets /workspace/hf-cache /workspace/tmp

export HF_HOME="/workspace/hf-cache"
export HF_HUB_CACHE="/workspace/hf-cache/hub"
export XDG_CACHE_HOME="/workspace/.cache"
export TMPDIR="/workspace/tmp"

/root/atlas-live-worker-venv/bin/python scripts/capture_open_weight_probe_dataset.py \
  --model-id EleutherAI/gpt-neox-20b \
  --scenario-path /workspace/cas-harness-large-eval/scenarios/stage7_foundation_rolebound_pilot_20260526.json \
  --output /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz \
  --metadata-output /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.metadata.json \
  --layer-start 0 \
  --layer-end 43 \
  --max-scenarios 0 \
  --max-length 192 \
  --torch-dtype float16 \
  --device-map auto
```

After recapture, pull into a new timestamped archive directory using the retrieval command above and hash the NPZ, metadata, and scenario.

## Bottom Line For Tonight

No, the F28 nested-control lane is not runnable tonight from verified local artifacts alone. The local machine has the right scenario, metadata, reports, packet, and SHA records, but not the required GPT-NeoX-20B Stage 7 role-bound F28 activation NPZ.

Shortest path:

1. Try to restore the canonical NPZ from the old RunPod volume, snapshot, Cloud Sync, or object storage at `/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz`.
2. If a remote copy exists, retrieve it into a new archive directory and hash it. This avoids recapture.
3. If no remote copy exists, recapture on an H100 using `stage7_foundation_rolebound_pilot_20260526.json` and the capture command above, then treat the new NPZ as a regenerated replacement with fresh hashes.

