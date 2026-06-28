# CAS Harness matched-taxonomy 20B execution paths

Date: 2026-05-30
Owner: Agent C - artifact discovery and execution readiness
Scope: read-only artifact discovery plus this execution-paths doc only

## Readiness verdict

The full pre-registered GPT-NeoX-20B matched-taxonomy control is **not ready to run end-to-end tonight from verified local artifacts alone**.

The blocker is not Stage9 activation capture. The claim-bearing Stage9 original 40E activation dataset is present locally and hash-pinned. The blockers are:

1. The current repo has no dedicated matched-taxonomy runner that executes all required CAS, scrambled-CAS, coherent non-CAS, text-baseline, shuffled-label, flat-lacunarity, and nested-lacunarity reports under one fixed split.
2. The coherent non-CAS taxonomy label manifests are not present.
3. The exact Stage7/Foundation28 role-bound activation NPZ is not present in the verified local archive or `C:\tmp` staging path. Its metadata, scenario JSON, reports, and packet are present, but the load-bearing NPZ is missing locally.
4. Both recorded RunPod SSH endpoints timed out during read-only checks, so I could not verify that the remote `/workspace/cas-harness-large-eval` volume still holds the missing F28 NPZ.

Narrow answer to "without re-capturing activations":

- Stage9 40E: **yes**, the activations exist locally; no recapture is needed for Stage9 hidden/text/lacunarity controls once the matched-taxonomy runner and labels exist.
- Stage7/Foundation28: **not verified**. No local recapture is needed only if the remote volume, Cloud Sync, snapshot, or another archive can restore `/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz`. From the artifacts I could inspect, this NPZ is missing locally.
- Full 20B matched-taxonomy gate: **no**, because it needs both axes plus missing runner/label manifests.

## Pre-registration and packet-contract inputs

Current repo inputs:

- `docs/working/cas_harness_matched_taxonomy_control_prereg_20260530.md`
  - SHA256: `83AC7261C79576C8F9633CD53E149FF99F70407758B5D674CA01083C05E0B733`
- `docs/working/cas_harness_matched_taxonomy_evidence_packet_spec_20260530.md`
  - SHA256: `D123F6DEBC9244D252E089B60D60CBA18C4BB48B336FBD2CC8172E038CE685D6`

The preregistration requires same model, same activations, same split, same balanced-logistic probe family, same text baselines, same shuffled-label controls, and flat-plus-nested lacunarity scoring.

## Stage9 40E claim-bearing artifacts

Use this Stage9 dataset. It is the clean original role-bound/counterfactual fixture, not the compact-gloss TKS40 v0 set.

Local archive:

```text
D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527
```

Present files:

```text
D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\gpt_neox_20b_stage9_original_40e_layers_0_43.npz
D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\gpt_neox_20b_stage9_original_40e_layers_0_43.metadata.json
D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\gpt_neox_20b_stage9_original_40e_probe_eval_report.json
D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\stage9_original_40e_scenarios_20260527.json
D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\stage9_original_40e_text_baseline_diagnostic_20260527.json
D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\SHA256SUMS.txt
D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\REPRODUCIBILITY_NOTES.md
```

Observed sizes and hashes:

```text
4,160,353,076  gpt_neox_20b_stage9_original_40e_layers_0_43.npz
2,471          gpt_neox_20b_stage9_original_40e_layers_0_43.metadata.json
12,512         gpt_neox_20b_stage9_original_40e_probe_eval_report.json
9,138,320      stage9_original_40e_scenarios_20260527.json
82,467         stage9_original_40e_text_baseline_diagnostic_20260527.json

5f9a14714dcad87991a04a8317119b4eeb8097af7377446e59efb1c65f428610  gpt_neox_20b_stage9_original_40e_layers_0_43.npz
22d5e6c19c4dd25d549e82bc2509282634878df465967df1d68f11d90accf6ef  gpt_neox_20b_stage9_original_40e_layers_0_43.metadata.json
e90268444fd914f558b2244c90c9d039936fc273bdefbad266ebaf844d004030  gpt_neox_20b_stage9_original_40e_probe_eval_report.json
b2ad0481daaa1e5597a445a7ad8a9f2a4d108ead213818edd2ffb665af55b537  stage9_original_40e_scenarios_20260527.json
44cdf5c1e4fcf6e69365ba2f865db44a8f247700fe075c0cb7298a553a63c6e1  stage9_original_40e_text_baseline_diagnostic_20260527.json
```

Metadata summary:

```text
model_id: EleutherAI/gpt-neox-20b
feature_shape: [8320, 44, 6144]
scenario_count: 8320
layers: 0..43
labels: labels_operator + labels_domain, 40 classes
balance: 208 examples per ^0..^9 x C/E/O/P cell
remote output in metadata: data/gpt_neox_20b_stage9_original_40e_layers_0_43.npz
remote scenario in metadata: data/stage9_original_40e_scenarios_20260527.json
```

Existing CAS readout result:

```text
best layer: 2
hidden accuracy: 95.625%
hidden macro-F1: 95.617%
CountVectorizer text baseline: 49.241071%
text-hash baseline: 50.000%
majority baseline: 2.500%
shuffled-label mean: 2.619%
split: fixed metadata.split; train 3840 / test 4480; group overlap 0
status: packet_ready_evaluation_completed
```

Optional Stage9 CAS readout recheck command, using the current repo script:

```powershell
cd C:\Users\wakil\OneDrive\Desktop\tksCAS
New-Item -ItemType Directory -Force C:\tmp\cas_matched_taxonomy_20b_20260530 | Out-Null

python noetic-compass-scaffold\noetic-compass\live-trace-worker\scripts\evaluate_40_element_probe.py `
  --dataset D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\gpt_neox_20b_stage9_original_40e_layers_0_43.npz `
  --metadata D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\gpt_neox_20b_stage9_original_40e_layers_0_43.metadata.json `
  --output C:\tmp\cas_matched_taxonomy_20b_20260530\stage9_40e_cas_readout_recheck.json `
  --test-size 0.2 `
  --shuffled-trials 20 `
  --probe-C 0.1 `
  --probe-max-iter 1000 `
  --seed 2026 `
  --min-samples-per-cell 10 `
  --require-balanced-40e
```

This command is only a CAS 40E recheck. It is not the matched-taxonomy control because it does not evaluate coherent non-CAS taxonomies.

Stage9 downstream proof archives, useful for provenance but not primary matched-taxonomy inputs:

```text
D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_causal_proof_20260528
D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_bridge_proof_20260528
C:\tmp\gpt_neox_20b_stage9_original_40e_subspace_ablation_report_20260528T0155Z.json
C:\tmp\gpt_neox_20b_stage9_original_40e_neuron_covers_top8_20260528T0210Z.json
C:\tmp\gpt_neox_20b_stage9_original_40e_evidence_packet_20260528T0215Z.json
C:\tmp\gpt_neox_20b_stage9_original_40e_eta_epsilon_bridge_per2_20260528T0455Z.json
```

The bridge-proof archive is hash-documented by:

```text
docs\working\gpt_neox_20b_stage9_original_40e_bridge_proof_REPRODUCIBILITY_NOTES_20260528.md
docs\working\gpt_neox_20b_stage9_original_40e_bridge_proof_SHA256SUMS_20260528.txt
```

## Stage7/Foundation28 artifacts

The exact Stage7 role-bound F28 run is the correct F28 target for the matched-taxonomy control. Do not substitute the compact generated `foundation28_balanced_v0_20260526` set for the claim-bearing run; that generated library had a 100% text baseline in the status docs.

Local archive with reports and packet:

```text
D:\tksCAS-archive\gpt_neox_20b_balanced_logistic_closure_20260526
```

Present archive files:

```text
D:\tksCAS-archive\gpt_neox_20b_balanced_logistic_closure_20260526\gpt_neox_20b_stage7_eta_epsilon_bridge_logistic.json
D:\tksCAS-archive\gpt_neox_20b_balanced_logistic_closure_20260526\gpt_neox_20b_stage7_foundation_rolebound_probe_eval_report_top256.json
D:\tksCAS-archive\gpt_neox_20b_balanced_logistic_closure_20260526\gpt_neox_20b_stage7_trace_diagnostics_logistic.json
D:\tksCAS-archive\gpt_neox_20b_balanced_logistic_closure_20260526\S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json
D:\tksCAS-archive\gpt_neox_20b_balanced_logistic_closure_20260526\S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.md
D:\tksCAS-archive\gpt_neox_20b_balanced_logistic_closure_20260526\SHA256SUMS.txt
D:\tksCAS-archive\gpt_neox_20b_balanced_logistic_closure_20260526\REPRODUCIBILITY_NOTES.md
```

Hashes from the archive:

```text
94010bbd17ff2e6abd43a94ebe5ca68ba00ad94ee409e4add54ed85a759d8eeb  gpt_neox_20b_stage7_eta_epsilon_bridge_logistic.json
3f5706c33f67dac52c06a79390431850c4b13ba077e59346f81cfca29bc074c9  gpt_neox_20b_stage7_foundation_rolebound_probe_eval_report_top256.json
01346fd74aeb73e56b2982e78a8e3db684b0e0a5c617c701399a3a5a8989c922  gpt_neox_20b_stage7_trace_diagnostics_logistic.json
d7eb3e3f032266010472c42cb51c1a32e092a6bc37fb72ad8e952107f0ee1136  S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json
40c96278b7e625576e7f41f8b4ca08ee62fe577dd0e97570eb339e27b8d1f63b  S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.md
```

Local staging path with scenario and metadata:

```text
C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526
```

Present staging files relevant to exact Stage7:

```text
C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\stage7_foundation_rolebound_pilot_20260526.json
C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.metadata.json
C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\gpt_neox_20b_stage7_foundation_rolebound_probe_eval_report_top256.json
C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\gpt_neox_20b_stage7_foundation_rolebound_activation_cover_ablation_report_top256.json
C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\gpt_neox_20b_stage7_foundation_rolebound_candidate_cover_map_top256.json
C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\gpt_neox_20b_stage7_eta_epsilon_bridge_logistic.json
C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\gpt_neox_20b_stage7_trace_diagnostics_logistic.json
C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json
```

Observed hashes:

```text
5b8aad738ca22afec11c60186981193ed3b951a4e13da3fd7bfd5f7acb54d46d  stage7_foundation_rolebound_pilot_20260526.json
9f698313c376eb91e8317e22cc96be7e729c96e1269a2835065009b55dac9381  gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.metadata.json
3f5706c33f67dac52c06a79390431850c4b13ba077e59346f81cfca29bc074c9  gpt_neox_20b_stage7_foundation_rolebound_probe_eval_report_top256.json
```

F28 metadata summary:

```text
model_id: EleutherAI/gpt-neox-20b
feature_shape: [4368, 44, 6144]
scenario_count: 4368
labels: foundation, drive, register
balance: 156 examples per F1..F7 x T/A/f/E class
metadata output path: datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz
metadata scenario path: scenarios/stage7_foundation_rolebound_pilot_20260526.json
```

Existing F28 evidence packet result:

```text
method: S7-F28-BALANCED-BRIDGE
balanced-logistic heldout Foundation accuracy: 86.8622%
heldout macro-F1: 86.9944%
readout layer: 40
probe-readable eta -> epsilon delta: +0.596413
probe-readable positive rows: 90/112
sign-test p: 3e-11
Foundation lacunarity: 0.006715
Drive lacunarity inside Foundation grid: 0.002752
Register lacunarity inside Foundation grid: 0.001283
packet verdict: FLAG_FOR_HUMAN_REVIEW
```

Missing local F28 activation file:

```text
D:\tksCAS-archive\gpt_neox_20b_balanced_logistic_closure_20260526\gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz
C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz
```

Both paths returned `False` in read-only `Test-Path` checks.

Remote canonical F28 paths from docs:

```text
/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz
/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.metadata.json
/workspace/cas-harness-large-eval/scenarios/stage7_foundation_rolebound_pilot_20260526.json
/workspace/cas-harness-large-eval/reports/gpt_neox_20b_stage7_foundation_rolebound_probe_eval_report_top256.json
```

Remote endpoints checked:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 -i $env:USERPROFILE\.ssh\id_ed25519 -p 30987 root@38.80.152.148 "ls -lh /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz"
```

Result on 2026-05-30: timed out.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 -i $env:USERPROFILE\.ssh\id_ed25519 -p 18251 root@31.24.80.42 "ls -lh /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz"
```

Result on 2026-05-30: timed out.

## Do-not-use datasets for the matched 20B gate

These are useful historical artifacts but should not be used as the matched-taxonomy 20B gate inputs:

```text
D:\tksCAS-archive\gpt_neox_20b_probe_dataset_eval_20260526\gpt_neox_20b_augmented_400_layers_0_43.npz
```

Reason: 400-row augmented dataset is not the exact Stage9 40E or exact Stage7 F28 role-bound fixture. It has drive/domain/operator labels but is not balanced for the 40E grid and is not the claim-bearing control substrate.

```text
C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\gpt_neox_20b_foundation28_280_layers_0_43.metadata.json
```

Reason: generated 280-row compact Foundation28 v0 path; status docs report text baseline at 100%, so it is not the clean original Foundation28 text adversary.

```text
noetic-compass-scaffold\noetic-compass\research\cas_probe\stage7_foundation_pilot_activations_20260517.npz
noetic-compass-scaffold\noetic-compass\research\cas_probe\stage7_foundation_pilot_smoke_activations_20260517.npz
```

Reason: local repo pilot/smoke activations are not GPT-NeoX-20B Stage7 role-bound 20260526 activations.

## Runner and script readiness

Current repo scripts found:

```text
noetic-compass-scaffold\noetic-compass\live-trace-worker\scripts\evaluate_40_element_probe.py
noetic-compass-scaffold\noetic-compass\live-trace-worker\scripts\run_stage9_40e_subspace_ablation.py
noetic-compass-scaffold\noetic-compass\live-trace-worker\scripts\discover_stage9_40e_neuron_covers.py
noetic-compass-scaffold\noetic-compass\live-trace-worker\scripts\merge_stage9_40e_evidence_packet.py
```

These are Stage9/CAS-specific proof scripts. They do not implement the pre-registered matched-taxonomy control across coherent non-CAS taxonomies.

Restored reference scripts exist outside the current repo under:

```text
C:\tmp\cas-harness-enterprise-scale\noetic-compass-scaffold\noetic-compass\live-trace-worker\scripts
C:\tmp\cas-runpod-master\noetic-compass-scaffold\noetic-compass\live-trace-worker\scripts
```

Relevant restored script names include:

```text
capture_open_weight_probe_dataset.py
evaluate_probe_dataset.py
derive_probe_dataset_axis.py
diagnose_tks40_text_baseline.py
build_foundation28_scenarios.py
merge_s7_f28_balanced_bridge_evidence_packet.py
run_stage9_40e_eta_epsilon_bridge.py
build_stage9_40e_verifier_report.py
```

Caveat: `evaluate_probe_dataset.py` help says it uses dependency-light nearest-centroid probes, not the required `StandardScaler + LogisticRegression(class_weight="balanced")` matched-taxonomy protocol. Treat these restored scripts as references only unless another owner explicitly promotes them back into the current repo.

## Missing files and artifacts

Blocking for any real matched-taxonomy verdict:

1. Dedicated matched-taxonomy runner in the current repo, or an explicitly approved external runner.
2. CAS and non-CAS label manifests for every Stage9 row:
   - CAS 40E label manifest from existing `labels_operator + labels_domain`
   - scrambled CAS 40-way label manifest with fixed seeds
   - coherent non-CAS 40-way label manifest
   - text-only adversary report manifest
3. CAS and non-CAS label manifests for every F28 row:
   - CAS F28 label manifest from `foundation` / `drive + register`
   - scrambled CAS 28-way label manifest with fixed seeds
   - coherent non-CAS 7 x 4 nested label manifest
   - text-only adversary report manifest
4. Split manifests and hashes for Stage9 and F28, using the original metadata split/group keys.
5. F28 activation NPZ:
   - `/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz`
   - or a local restored copy with matching metadata and hash.
6. Final matched-taxonomy packet builder conforming to `cas_matched_taxonomy_packet.v0`.

Non-blocking but should be recorded:

- Model-weight SHA is not available in the existing packets.
- Stage7 existing packet verdict is `FLAG_FOR_HUMAN_REVIEW`, not production `ACCEPT`.
- Existing Stage9 eta -> epsilon bridge packet was initially flagged for human review in its notes; verifier artifacts exist in restored `C:\tmp` trees but are not part of the current repo path set I own here.

## Safe execution order

1. Freeze current artifacts. Do not recapture anything until the preflight proves a required activation NPZ is missing from all restore locations.
2. Hash local Stage9 inputs and compare to `SHA256SUMS.txt`.
3. Locate or restore the F28 activation NPZ. Prefer RunPod volume, Cloud Sync, object-store copy, or a local archive restore. Recapture only if those fail.
4. Add or receive the matched-taxonomy runner and label manifests from the owning agent. Do not modify current Stage9/F28 proof scripts for this doc task.
5. Run a dry-run/schema-only packet check against small fixture copies.
6. Run Stage9 40E matched-taxonomy control.
7. Run Stage7/F28 matched-taxonomy control.
8. Build the matched-taxonomy Evidence Packet with all artifact hashes and explicit `PASS`, `GREY`, `FAIL`, or `BLOCKED`.
9. Archive outputs under a new dated directory, keeping large NPZ files out of git.
10. Only after the 20B gate passes, replay the same protocol on the validated smaller model points listed in the preregistration.

## Exact preflight commands

Local Stage9 hash verification:

```powershell
cd C:\Users\wakil\OneDrive\Desktop\tksCAS

Get-FileHash -Algorithm SHA256 -LiteralPath D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\gpt_neox_20b_stage9_original_40e_layers_0_43.npz
Get-FileHash -Algorithm SHA256 -LiteralPath D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\gpt_neox_20b_stage9_original_40e_layers_0_43.metadata.json
Get-FileHash -Algorithm SHA256 -LiteralPath D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\gpt_neox_20b_stage9_original_40e_probe_eval_report.json
Get-FileHash -Algorithm SHA256 -LiteralPath D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\stage9_original_40e_scenarios_20260527.json
Get-FileHash -Algorithm SHA256 -LiteralPath D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\stage9_original_40e_text_baseline_diagnostic_20260527.json
Get-Content -LiteralPath D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\SHA256SUMS.txt
```

Local F28 existence check:

```powershell
cd C:\Users\wakil\OneDrive\Desktop\tksCAS

Test-Path D:\tksCAS-archive\gpt_neox_20b_balanced_logistic_closure_20260526\gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz
Test-Path C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz

Get-FileHash -Algorithm SHA256 -LiteralPath C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\stage7_foundation_rolebound_pilot_20260526.json
Get-FileHash -Algorithm SHA256 -LiteralPath C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.metadata.json
Get-FileHash -Algorithm SHA256 -LiteralPath C:\tmp\gpt_neox_20b_foundation28_and_40element_20260526\gpt_neox_20b_stage7_foundation_rolebound_probe_eval_report_top256.json
Get-Content -LiteralPath D:\tksCAS-archive\gpt_neox_20b_balanced_logistic_closure_20260526\SHA256SUMS.txt
```

Remote F28 preflight, if either recorded RunPod endpoint is reachable again:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 -i $env:USERPROFILE\.ssh\id_ed25519 -p 18251 root@31.24.80.42 "ls -lh /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.metadata.json /workspace/cas-harness-large-eval/scenarios/stage7_foundation_rolebound_pilot_20260526.json"
```

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 -i $env:USERPROFILE\.ssh\id_ed25519 -p 30987 root@38.80.152.148 "ls -lh /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.metadata.json /workspace/cas-harness-large-eval/scenarios/stage7_foundation_rolebound_pilot_20260526.json"
```

If the remote NPZ exists, pull it into a new archive folder and hash it:

```powershell
$Archive = "D:\tksCAS-archive\gpt_neox_20b_stage7_foundation_rolebound_activations_20260530"
New-Item -ItemType Directory -Force -Path $Archive | Out-Null

scp -i $env:USERPROFILE\.ssh\id_ed25519 -P 18251 root@31.24.80.42:/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.npz $Archive\
scp -i $env:USERPROFILE\.ssh\id_ed25519 -P 18251 root@31.24.80.42:/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_stage7_foundation_rolebound_pilot_layers_0_43.metadata.json $Archive\
scp -i $env:USERPROFILE\.ssh\id_ed25519 -P 18251 root@31.24.80.42:/workspace/cas-harness-large-eval/scenarios/stage7_foundation_rolebound_pilot_20260526.json $Archive\

Get-ChildItem -LiteralPath $Archive -File | Sort-Object Name | ForEach-Object {
  Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName
}
```

Use the `38.80.152.148:30987` endpoint in the same command shape only if that is the active pod. Both endpoints timed out during this discovery pass.

## Final matched-taxonomy run command status

There is no exact final matched-taxonomy run command in the current repo because the runner does not exist here yet.

Do not fabricate a result by chaining the existing Stage9 scripts. A valid runner must accept at least:

```text
--axis stage9_40e|stage7_f28
--dataset <activation_npz>
--metadata <metadata_json>
--scenarios <scenario_json>
--taxonomy-manifest <cas_or_control_labels_json>
--split-key metadata.split
--group-key metadata.counterfactual_pair_id
--test-split test
--probe-kind balanced_logistic
--probe-C 0.1
--probe-max-iter 1000
--layers all
--text-baseline count_vectorizer_logistic
--shuffled-seeds <fixed list>
--lacunarity variance_over_mean_squared
--output-report <json>
```

The output must then feed the packet schema in `docs/working/cas_harness_matched_taxonomy_evidence_packet_spec_20260530.md`.

## Runtime estimate

Assumptions: local workstation can read a 4.16 GB NPZ, has 32 GB RAM minimum and 64 GB preferred, Python/scikit-learn/numpy available, no model forward pass required if activations are present.

Estimated local CPU time:

```text
Stage9 40E artifact hash/preflight: 5-15 minutes, dominated by hashing the 4.16 GB NPZ.
Stage9 40E one CAS recheck over all layers: 20-90 minutes depending CPU/RAM.
Stage9 40E full matched-taxonomy sweep: 2-6 hours for CAS + scrambled + coherent 40-way + text baselines + lacunarity, depending runner optimization.
Stage7/F28 full matched-taxonomy sweep after NPZ restore: 1-4 hours.
Packet assembly and hash manifest: 5-20 minutes.
```

If the F28 NPZ must be recaptured:

```text
H100 model/cache preflight: 10-60 minutes depending whether weights are already cached.
F28 activation recapture for 4,368 scenarios x 44 layers: likely 30-120 minutes on H100, plus transfer/hash time.
Local pull of the F28 NPZ: likely 10-60 minutes depending network and final compressed size.
```

Practical tonight estimate:

- Stage9-only matched control could run tonight if the runner and label manifests land early.
- Full 20B Stage9 + F28 matched control is unlikely tonight unless the F28 NPZ is quickly restored from the old RunPod volume/cloud sync and the runner/labels already exist from another agent.

## Bottom line

Do not recapture Stage9. The correct Stage9 activation dataset is present and hash-pinned.

Do not claim the full 20B matched-taxonomy control is runnable from local disk yet. Restore or recapture the exact Stage7 role-bound F28 NPZ first, and require a dedicated matched-taxonomy runner plus label manifests before any PASS/GREY/FAIL packet is produced.
