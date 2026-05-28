# Stage 9 40E GPT-NeoX-20B RunPod Causal Execution Runbook - 2026-05-27

This is an operator runbook for the next RunPod jobs and preservation steps for the Stage 9 original 40-element GPT-NeoX-20B causal closure work.

Scope:

- Prepare and verify the RunPod execution environment.
- Run the next causal jobs only after Agent A, Agent B, and Agent C scripts exist.
- Preserve small reports locally and through RunPod Cloud Sync.
- Keep large binary artifacts out of git.

Non-goals:

- Do not run the causal jobs until the owning agent scripts exist and their CLIs are confirmed.
- Do not commit or `git add` large `.npz` files.
- Do not treat placeholder commands in this document as evidence that a job has run.

## Canonical Paths

Remote RunPod root:

```bash
/workspace/cas-harness-large-eval
```

Remote inputs already used recently:

```bash
REMOTE_ROOT=/workspace/cas-harness-large-eval
DATASET=$REMOTE_ROOT/data/gpt_neox_20b_stage9_original_40e_layers_0_43.npz
SCENARIOS=$REMOTE_ROOT/data/stage9_original_40e_scenarios_20260527.json
READOUT_REPORT=$REMOTE_ROOT/results/gpt_neox_20b_stage9_original_40e_probe_eval_report.json
RESULTS_DIR=$REMOTE_ROOT/results
RUN_ID=stage9_40e_20b_causal_$(date -u +%Y%m%dT%H%M%SZ)
```

Local archive:

```powershell
$Archive = "D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527"
```

RunPod Cloud Sync source path:

```bash
/workspace/cas-harness-large-eval
```

## 1. SSH Into The Pod

Use the SSH command shown in the RunPod UI. Keep host and port explicit so later `scp` commands are unambiguous.

PowerShell placeholders:

```powershell
$PodHost = "<runpod-host>"
$PodPort = "<ssh-port>"
$PodUser = "root"
$KeyPath = "$env:USERPROFILE\.ssh\<runpod-key>"
ssh -i $KeyPath -p $PodPort "$PodUser@$PodHost"
```

If the pod uses a direct SSH command from the UI, paste it as-is and then set the same values for later `scp`.

Inside the pod, start in a durable shell session for long jobs:

```bash
tmux new -s stage9_40e_20b
```

If `tmux` is unavailable, use a normal shell but keep logs with `tee` and do not close the terminal while jobs are running.

## 2. Remote Preflight

Run this before any causal job. It fails fast if `/workspace` is missing or if the expected files are absent.

```bash
set -euo pipefail

REMOTE_ROOT=/workspace/cas-harness-large-eval
DATASET=$REMOTE_ROOT/data/gpt_neox_20b_stage9_original_40e_layers_0_43.npz
SCENARIOS=$REMOTE_ROOT/data/stage9_original_40e_scenarios_20260527.json
READOUT_REPORT=$REMOTE_ROOT/results/gpt_neox_20b_stage9_original_40e_probe_eval_report.json
RESULTS_DIR=$REMOTE_ROOT/results

if [ ! -d /workspace ]; then
  echo "STOP: /workspace is missing. Do not run from /root as a substitute."
  echo "Attach the expected persistent volume or recreate the pod with the correct mount."
  exit 20
fi

if [ ! -d "$REMOTE_ROOT" ]; then
  echo "STOP: $REMOTE_ROOT is missing."
  echo "Confirm the RunPod volume and Cloud Sync source path."
  exit 21
fi

mkdir -p "$RESULTS_DIR" "$RESULTS_DIR/logs"

test -s "$DATASET"
test -s "$SCENARIOS"
test -s "$READOUT_REPORT"

df -h /workspace
du -h "$DATASET" "$SCENARIOS" "$READOUT_REPORT"
ls -lh "$DATASET" "$SCENARIOS" "$READOUT_REPORT"
```

## 3. Verify Dataset And Report Integrity

Create a remote manifest before running anything new.

```bash
set -euo pipefail

REMOTE_ROOT=/workspace/cas-harness-large-eval
DATASET=$REMOTE_ROOT/data/gpt_neox_20b_stage9_original_40e_layers_0_43.npz
SCENARIOS=$REMOTE_ROOT/data/stage9_original_40e_scenarios_20260527.json
READOUT_REPORT=$REMOTE_ROOT/results/gpt_neox_20b_stage9_original_40e_probe_eval_report.json
RESULTS_DIR=$REMOTE_ROOT/results
MANIFEST=$RESULTS_DIR/stage9_40e_20b_remote_input_sha256s_20260527.txt

sha256sum "$DATASET" "$SCENARIOS" "$READOUT_REPORT" | tee "$MANIFEST"

python - "$DATASET" "$SCENARIOS" "$READOUT_REPORT" <<'PY'
import json
import sys
from pathlib import Path

import numpy as np

dataset = Path(sys.argv[1])
scenarios = Path(sys.argv[2])
readout = Path(sys.argv[3])

data = np.load(dataset, allow_pickle=True)
required = {"features", "layers", "labels_domain", "labels_operator", "prompts"}
missing = sorted(required - set(data.files))
if missing:
    raise SystemExit(f"STOP: dataset missing required keys: {missing}")

features = data["features"]
if features.ndim != 3:
    raise SystemExit(f"STOP: expected features [N, layers, hidden_dim], got {features.shape}")

scenario_doc = json.loads(scenarios.read_text(encoding="utf-8"))
report = json.loads(readout.read_text(encoding="utf-8"))

print("dataset_shape", tuple(int(x) for x in features.shape))
print("dataset_layers", [int(x) for x in data["layers"][:5]], "...", [int(x) for x in data["layers"][-5:]])
print("scenario_type", type(scenario_doc).__name__)
print("readout_schema_version", report.get("schema_version"))
print("readout_status", report.get("status"))
print("readout_dataset", report.get("dataset"))

if str(dataset) != report.get("dataset"):
    raise SystemExit("STOP: readout report dataset path does not match canonical DATASET")

bad_statuses = {
    "blocked_missing_balanced_40e_artifact",
    "diagnostic_completed_not_packet_ready",
    "payload_only",
}
if report.get("status") in bad_statuses:
    raise SystemExit(f"STOP: readout report is not a completed packet-ready report: {report.get('status')}")
PY
```

Copy the remote manifest back before comparing to local archive:

```powershell
$PodHost = "<runpod-host>"
$PodPort = "<ssh-port>"
$PodUser = "root"
$KeyPath = "$env:USERPROFILE\.ssh\<runpod-key>"
$Archive = "D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527"

New-Item -ItemType Directory -Force -Path $Archive | Out-Null
scp -i $KeyPath -P $PodPort "$PodUser@$PodHost:/workspace/cas-harness-large-eval/results/stage9_40e_20b_remote_input_sha256s_20260527.txt" "$Archive\"
```

Compare the remote manifest against the local archived files. Adjust local paths only if the archive layout differs.

```powershell
$Archive = "D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527"
$LocalDataset = Join-Path $Archive "gpt_neox_20b_stage9_original_40e_layers_0_43.npz"
$LocalScenarios = Join-Path $Archive "stage9_original_40e_scenarios_20260527.json"
$LocalReadout = Join-Path $Archive "gpt_neox_20b_stage9_original_40e_probe_eval_report.json"

Get-FileHash -Algorithm SHA256 -LiteralPath $LocalDataset
Get-FileHash -Algorithm SHA256 -LiteralPath $LocalScenarios
Get-FileHash -Algorithm SHA256 -LiteralPath $LocalReadout
Get-Content -LiteralPath (Join-Path $Archive "stage9_40e_20b_remote_input_sha256s_20260527.txt")
```

Stop if any local hash differs from the remote manifest unless the difference is explicitly explained and documented in `REPRODUCIBILITY_NOTES.md`.

## 4. Confirm Repository And Script Locations

The causal scripts are expected to live in the checked-out `noetic-compass` repository on the pod. Set `REPO_ROOT` to the actual checkout path.

```bash
REPO_ROOT=${REPO_ROOT:-/workspace/tksCAS/noetic-compass-scaffold/noetic-compass}
test -d "$REPO_ROOT"
test -d "$REPO_ROOT/live-trace-worker/scripts"
cd "$REPO_ROOT"

git status --short
```

Do not resolve a missing script by editing code during this operator run. Wait for the owning agent to land the script.

## 5. Agent A Job: Subspace Ablation

Run after `run_stage9_40e_subspace_ablation.py` is present and its `--help` confirms the CLI.

Placeholder setup:

```bash
set -euo pipefail

REMOTE_ROOT=/workspace/cas-harness-large-eval
DATASET=$REMOTE_ROOT/data/gpt_neox_20b_stage9_original_40e_layers_0_43.npz
SCENARIOS=$REMOTE_ROOT/data/stage9_original_40e_scenarios_20260527.json
READOUT_REPORT=$REMOTE_ROOT/results/gpt_neox_20b_stage9_original_40e_probe_eval_report.json
RESULTS_DIR=$REMOTE_ROOT/results
REPO_ROOT=${REPO_ROOT:-/workspace/tksCAS/noetic-compass-scaffold/noetic-compass}
RUN_ID=stage9_40e_20b_subspace_ablation_$(date -u +%Y%m%dT%H%M%SZ)

AGENT_A_SCRIPT=$REPO_ROOT/live-trace-worker/scripts/run_stage9_40e_subspace_ablation.py
SUBSPACE_REPORT=$RESULTS_DIR/gpt_neox_20b_stage9_original_40e_subspace_ablation_report_${RUN_ID}.json
SUBSPACE_LOG=$RESULTS_DIR/logs/${RUN_ID}.log

test -s "$AGENT_A_SCRIPT"
python "$AGENT_A_SCRIPT" --help
```

Run:

```bash
set -o pipefail
python "$AGENT_A_SCRIPT" \
  --dataset "$DATASET" \
  --metadata "$REMOTE_ROOT/data/gpt_neox_20b_stage9_original_40e_layers_0_43.metadata.json" \
  --scenarios "$SCENARIOS" \
  --probe-report "$READOUT_REPORT" \
  --output "$SUBSPACE_REPORT" \
  --layers best \
  --seed 20260527 \
  --random-control-trials 20 \
  2>&1 | tee "$SUBSPACE_LOG"
rc=${PIPESTATUS[0]}
test "$rc" -eq 0
test -s "$SUBSPACE_REPORT"
python -m json.tool "$SUBSPACE_REPORT" >/dev/null
sha256sum "$SUBSPACE_REPORT" "$SUBSPACE_LOG" | tee "$RESULTS_DIR/${RUN_ID}_sha256.txt"
```

Minimum acceptance checks:

- Report is parseable JSON.
- Report names the exact canonical dataset path.
- Report records method parameters, seed, layers, and controls.
- Report status indicates completion, not blocked, dry-run, payload-only, or placeholder.
- Log exit code is zero and has no traceback.

## 6. Agent B Job: Sparse Cover Discovery

Run after `discover_stage9_40e_neuron_covers.py` is present and its `--help` confirms the CLI.

Placeholder setup:

```bash
set -euo pipefail

REMOTE_ROOT=/workspace/cas-harness-large-eval
DATASET=$REMOTE_ROOT/data/gpt_neox_20b_stage9_original_40e_layers_0_43.npz
SCENARIOS=$REMOTE_ROOT/data/stage9_original_40e_scenarios_20260527.json
READOUT_REPORT=$REMOTE_ROOT/results/gpt_neox_20b_stage9_original_40e_probe_eval_report.json
RESULTS_DIR=$REMOTE_ROOT/results
REPO_ROOT=${REPO_ROOT:-/workspace/tksCAS/noetic-compass-scaffold/noetic-compass}
RUN_ID=stage9_40e_20b_cover_discovery_$(date -u +%Y%m%dT%H%M%SZ)

AGENT_B_SCRIPT=$REPO_ROOT/live-trace-worker/scripts/discover_stage9_40e_neuron_covers.py
COVER_REPORT=$RESULTS_DIR/gpt_neox_20b_stage9_original_40e_cover_discovery_report_${RUN_ID}.json
COVER_LOG=$RESULTS_DIR/logs/${RUN_ID}.log

test -s "$AGENT_B_SCRIPT"
python "$AGENT_B_SCRIPT" --help
```

Run:

```bash
set -o pipefail
python "$AGENT_B_SCRIPT" \
  --dataset "$DATASET" \
  --metadata "$REMOTE_ROOT/data/gpt_neox_20b_stage9_original_40e_layers_0_43.metadata.json" \
  --output "$COVER_REPORT" \
  --layer 2 \
  --top-k 8 \
  --seed 20260527 \
  --random-control-trials 20 \
  --wrong-class-controls 3 \
  2>&1 | tee "$COVER_LOG"
rc=${PIPESTATUS[0]}
test "$rc" -eq 0
test -s "$COVER_REPORT"
python -m json.tool "$COVER_REPORT" >/dev/null
sha256sum "$COVER_REPORT" "$COVER_LOG" | tee "$RESULTS_DIR/${RUN_ID}_sha256.txt"
```

Minimum acceptance checks:

- Report is parseable JSON.
- Report names the exact canonical dataset path.
- Report records selected layers, cover size, scoring rule, seed, and matched-control construction.
- Report distinguishes true covers from same-size controls.
- Report status indicates completion, not blocked, dry-run, payload-only, or placeholder.

## 7. Agent C Job: Evidence Packet Merge

Run after `merge_stage9_40e_evidence_packet.py` is present and after the readout, subspace ablation, and cover discovery reports all pass validation.

Placeholder setup:

```bash
set -euo pipefail

REMOTE_ROOT=/workspace/cas-harness-large-eval
DATASET=$REMOTE_ROOT/data/gpt_neox_20b_stage9_original_40e_layers_0_43.npz
SCENARIOS=$REMOTE_ROOT/data/stage9_original_40e_scenarios_20260527.json
READOUT_REPORT=$REMOTE_ROOT/results/gpt_neox_20b_stage9_original_40e_probe_eval_report.json
RESULTS_DIR=$REMOTE_ROOT/results
REPO_ROOT=${REPO_ROOT:-/workspace/tksCAS/noetic-compass-scaffold/noetic-compass}
RUN_ID=stage9_40e_20b_evidence_packet_$(date -u +%Y%m%dT%H%M%SZ)
: "${SUBSPACE_RUN_ID:?Set SUBSPACE_RUN_ID to the section 5 run id before merging}"
: "${COVER_RUN_ID:?Set COVER_RUN_ID to the section 6 run id before merging}"

AGENT_C_SCRIPT=$REPO_ROOT/live-trace-worker/scripts/merge_stage9_40e_evidence_packet.py
SUBSPACE_REPORT=$RESULTS_DIR/gpt_neox_20b_stage9_original_40e_subspace_ablation_report_${SUBSPACE_RUN_ID}.json
COVER_REPORT=$RESULTS_DIR/gpt_neox_20b_stage9_original_40e_cover_discovery_report_${COVER_RUN_ID}.json
EVIDENCE_PACKET=$RESULTS_DIR/gpt_neox_20b_stage9_original_40e_evidence_packet_${RUN_ID}.json
EVIDENCE_MARKDOWN=$RESULTS_DIR/gpt_neox_20b_stage9_original_40e_evidence_packet_${RUN_ID}.md
EVIDENCE_LOG=$RESULTS_DIR/logs/${RUN_ID}.log

test -s "$AGENT_C_SCRIPT"
test -s "$READOUT_REPORT"
test -s "$SUBSPACE_REPORT"
test -s "$COVER_REPORT"
python "$AGENT_C_SCRIPT" --help
python -m json.tool "$READOUT_REPORT" >/dev/null
python -m json.tool "$SUBSPACE_REPORT" >/dev/null
python -m json.tool "$COVER_REPORT" >/dev/null
```

Set `SUBSPACE_RUN_ID` and `COVER_RUN_ID` to the actual run ids printed in sections 5 and 6, then run:

```bash
set -o pipefail
python "$AGENT_C_SCRIPT" \
  --readout-report "$READOUT_REPORT" \
  --ablation-report "$SUBSPACE_REPORT" \
  --cover-report "$COVER_REPORT" \
  --output-json "$EVIDENCE_PACKET" \
  --output-markdown "$EVIDENCE_MARKDOWN" \
  2>&1 | tee "$EVIDENCE_LOG"
rc=${PIPESTATUS[0]}
test "$rc" -eq 0
test -s "$EVIDENCE_PACKET"
test -s "$EVIDENCE_MARKDOWN"
python -m json.tool "$EVIDENCE_PACKET" >/dev/null
sha256sum "$EVIDENCE_PACKET" "$EVIDENCE_MARKDOWN" "$EVIDENCE_LOG" | tee "$RESULTS_DIR/${RUN_ID}_sha256.txt"
```

Evidence packet acceptance checks:

```bash
python - "$EVIDENCE_PACKET" "$DATASET" <<'PY'
import json
import sys
from pathlib import Path

packet = Path(sys.argv[1])
dataset = sys.argv[2]
doc = json.loads(packet.read_text(encoding="utf-8"))

print("packet", packet)
print("schema_version", doc.get("schema_version"))
print("status", doc.get("status"))

blob = json.dumps(doc, sort_keys=True)
bad_tokens = ["<agent_", "<absolute-path", "TODO", "PLACEHOLDER", "payload_only", "fake"]
found = [token for token in bad_tokens if token in blob]
if found:
    raise SystemExit(f"STOP: evidence packet still contains placeholder or invalid tokens: {found}")

if dataset not in blob:
    raise SystemExit("STOP: evidence packet does not reference the canonical dataset")

status = str(doc.get("status", "")).lower()
if not status or any(x in status for x in ["blocked", "partial", "dry", "payload"]):
    raise SystemExit(f"STOP: evidence packet status is not final: {doc.get('status')}")
PY
```

## 8. Copy Small Reports Back With SCP

Do not use the report pullback step to copy the large `.npz`. Pull back JSON, Markdown, text manifests, logs, and the scenario JSON only.

PowerShell:

```powershell
$PodHost = "<runpod-host>"
$PodPort = "<ssh-port>"
$PodUser = "root"
$KeyPath = "$env:USERPROFILE\.ssh\<runpod-key>"
$Archive = "D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527"
$ReportsDir = Join-Path $Archive "runpod_small_reports_20260527"

New-Item -ItemType Directory -Force -Path $ReportsDir | Out-Null
```

Option A: copy known files individually.

```powershell
scp -i $KeyPath -P $PodPort "$PodUser@$PodHost:/workspace/cas-harness-large-eval/results/gpt_neox_20b_stage9_original_40e_probe_eval_report.json" "$ReportsDir\"
scp -i $KeyPath -P $PodPort "$PodUser@$PodHost:/workspace/cas-harness-large-eval/results/stage9_40e_20b_remote_input_sha256s_20260527.txt" "$ReportsDir\"
scp -i $KeyPath -P $PodPort "$PodUser@$PodHost:/workspace/cas-harness-large-eval/data/stage9_original_40e_scenarios_20260527.json" "$ReportsDir\"
scp -i $KeyPath -P $PodPort "$PodUser@$PodHost:/workspace/cas-harness-large-eval/results/<agent-a-report>.json" "$ReportsDir\"
scp -i $KeyPath -P $PodPort "$PodUser@$PodHost:/workspace/cas-harness-large-eval/results/<agent-b-report>.json" "$ReportsDir\"
scp -i $KeyPath -P $PodPort "$PodUser@$PodHost:/workspace/cas-harness-large-eval/results/<agent-c-evidence-packet>.json" "$ReportsDir\"
```

Option B: create a small remote tarball, then copy that tarball.

```powershell
ssh -i $KeyPath -p $PodPort "$PodUser@$PodHost" "cd /workspace/cas-harness-large-eval && tar --ignore-failed-read -czf /tmp/stage9_40e_20b_small_reports_20260527.tgz results/*.json results/*.txt results/logs/*.log data/stage9_original_40e_scenarios_20260527.json"
scp -i $KeyPath -P $PodPort "$PodUser@$PodHost:/tmp/stage9_40e_20b_small_reports_20260527.tgz" "$Archive\"
$SmallReportsTar = Join-Path $Archive "stage9_40e_20b_small_reports_20260527.tgz"
tar -xzf $SmallReportsTar -C $ReportsDir
```

After copying:

```powershell
Get-ChildItem -Recurse -File $ReportsDir | Sort-Object FullName | Select-Object FullName, Length, LastWriteTime
Get-ChildItem -Recurse -File $ReportsDir -Include *.json | ForEach-Object { python -m json.tool $_.FullName > $null }
```

## 9. RunPod Cloud Sync Preservation

Use RunPod Cloud Sync for the full remote working root:

```bash
/workspace/cas-harness-large-eval
```

Operator checklist:

- In RunPod UI, set Cloud Sync source path to `/workspace/cas-harness-large-eval`.
- Do not set the source path to an S3 URI. S3 or object storage is the destination, not the local path used by the Python jobs.
- Wait for Cloud Sync to show completion after the final Agent C evidence packet is written.
- Record the destination bucket or provider path in `REPRODUCIBILITY_NOTES.md`.
- Before destroying or resizing the pod, confirm both local archive and Cloud Sync contain the latest small reports and the large dataset.

Remote inventory to preserve with the synced directory:

```bash
REMOTE_ROOT=/workspace/cas-harness-large-eval
RESULTS_DIR=$REMOTE_ROOT/results

find "$REMOTE_ROOT" -maxdepth 3 -type f -printf '%p\t%s\t%TY-%Tm-%TdT%TH:%TM:%TS\n' \
  | sort \
  | tee "$RESULTS_DIR/stage9_40e_20b_file_inventory_20260527.txt"

sha256sum \
  "$REMOTE_ROOT/data/gpt_neox_20b_stage9_original_40e_layers_0_43.npz" \
  "$REMOTE_ROOT/data/stage9_original_40e_scenarios_20260527.json" \
  "$REMOTE_ROOT/results/gpt_neox_20b_stage9_original_40e_probe_eval_report.json" \
  "$RESULTS_DIR"/*.json \
  "$RESULTS_DIR"/*.txt \
  > "$RESULTS_DIR/stage9_40e_20b_preservation_sha256s_20260527.txt"
```

If using direct S3 tooling for verification, keep it separate from execution paths:

```bash
aws s3 ls s3://<bucket>/<prefix>/cas-harness-large-eval/
aws s3 cp s3://<bucket>/<prefix>/cas-harness-large-eval/results/stage9_40e_20b_preservation_sha256s_20260527.txt -
```

Do not pass `s3://...` paths to Agent A, B, or C scripts unless the script explicitly documents object-store support.

## 10. Update Local Archive Metadata

After report pullback, update `SHA256SUMS` in the local archive.

```powershell
$Archive = "D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527"
$Root = (Resolve-Path -LiteralPath $Archive).Path
$ShaPath = Join-Path $Archive "SHA256SUMS"

Get-ChildItem -LiteralPath $Archive -Recurse -File |
  Where-Object { $_.FullName -ne $ShaPath } |
  Sort-Object FullName |
  ForEach-Object {
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
    $rel = $_.FullName.Substring($Root.Length + 1).Replace('\', '/')
    "$hash  $rel"
  } | Set-Content -Encoding ascii -LiteralPath $ShaPath

Get-Content -LiteralPath $ShaPath
```

Append or update `REPRODUCIBILITY_NOTES.md`.

```powershell
$Archive = "D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527"
$Notes = Join-Path $Archive "REPRODUCIBILITY_NOTES.md"
$Note = @"

## Stage 9 40E GPT-NeoX-20B causal execution preservation - 2026-05-27

Remote source root: /workspace/cas-harness-large-eval
RunPod Cloud Sync source path: /workspace/cas-harness-large-eval
Cloud Sync destination: <bucket-or-provider-path-filled-after-sync>

Canonical dataset:
/workspace/cas-harness-large-eval/data/gpt_neox_20b_stage9_original_40e_layers_0_43.npz

Canonical scenario JSON:
/workspace/cas-harness-large-eval/data/stage9_original_40e_scenarios_20260527.json

Canonical readout report:
/workspace/cas-harness-large-eval/results/gpt_neox_20b_stage9_original_40e_probe_eval_report.json

Agent A subspace ablation script/version:
<script path, git commit, command, report path>

Agent B cover discovery script/version:
<script path, git commit, command, report path>

Agent C evidence packet merge script/version:
<script path, git commit, command, evidence packet path>

Remote SHA256 manifests:
stage9_40e_20b_remote_input_sha256s_20260527.txt
stage9_40e_20b_preservation_sha256s_20260527.txt

Local SHA256 manifest:
SHA256SUMS

Git discipline:
Large NPZ files are preserved by local archive and RunPod Cloud Sync only. They are not committed to git.
"@

Add-Content -Encoding ascii -LiteralPath $Notes -Value $Note
Get-Content -LiteralPath $Notes
```

## 11. Git Discipline

The local repository should only receive small documentation or code-review artifacts. The Stage 9 `.npz` dataset is a large binary artifact and must not be committed.

Before any commit:

```powershell
git status --short
git diff --stat
```

Only stage intentional small files. Example for this runbook:

```powershell
git add noetic-compass-scaffold/noetic-compass/docs/working/stage9_40e_20b_runpod_causal_execution_runbook_20260527.md
```

Do not run:

```powershell
git add D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\*.npz
git add **\*.npz
git add .
```

If an `.npz` appears in `git status --short`, stop and remove it from the index before committing:

```powershell
git status --short | Select-String "\.npz"
git restore --staged -- <path-to-large-npz>
```

Do not delete the file from disk unless explicitly directed. The goal is to keep it archived, not versioned.

## 12. Failure Modes And Responses

### Missing `/workspace`

Symptoms:

- `/workspace` does not exist.
- `/workspace/cas-harness-large-eval` does not exist.
- Files appear under `/root` after a mistaken copy.

Response:

- Stop immediately.
- Do not run jobs from `/root` as a substitute.
- Confirm the pod has the expected persistent volume mounted.
- Confirm RunPod Cloud Sync source path is `/workspace/cas-harness-large-eval`.
- Re-run the remote preflight only after the mount is fixed.

### S3 Bucket Path Confusion

Symptoms:

- A command uses `s3://...` as `--dataset`.
- A local path is set to the bucket destination instead of `/workspace/cas-harness-large-eval`.
- Cloud Sync destination is mistaken for the live execution directory.

Response:

- Keep execution paths as POSIX paths under `/workspace/cas-harness-large-eval`.
- Use S3 paths only for separate object-store verification or manual restore.
- If a file must be restored from S3, copy it back into `/workspace/cas-harness-large-eval` first, then run scripts against the restored local path.

### Fake Or Partial Reports

Symptoms:

- Report file is empty, tiny, or not parseable JSON.
- Report contains placeholders such as `<agent_...>`, `<absolute-path...>`, `TODO`, or `PLACEHOLDER`.
- Report status is `blocked`, `diagnostic_completed_not_packet_ready`, `payload_only`, `dry_run`, or `partial`.
- Report references a different dataset path than `/workspace/cas-harness-large-eval/data/gpt_neox_20b_stage9_original_40e_layers_0_43.npz`.
- The log has a traceback even though a JSON file exists.

Response:

- Treat the report as invalid.
- Preserve the bad report and log for debugging, but do not merge it into the evidence packet.
- Re-run only after fixing the input, script, or CLI issue.
- Update `REPRODUCIBILITY_NOTES.md` with the failed run ID and reason if the failed run was material.

Generic report validator:

```bash
python - "$REPORT_PATH" "$DATASET" <<'PY'
import json
import sys
from pathlib import Path

report = Path(sys.argv[1])
dataset = sys.argv[2]

if not report.exists() or report.stat().st_size < 200:
    raise SystemExit(f"STOP: missing or too-small report: {report}")

doc = json.loads(report.read_text(encoding="utf-8"))
blob = json.dumps(doc, sort_keys=True)

bad_tokens = ["<agent_", "<absolute-path", "TODO", "PLACEHOLDER", "payload_only"]
found = [token for token in bad_tokens if token in blob]
if found:
    raise SystemExit(f"STOP: invalid placeholder/status token(s): {found}")

status = str(doc.get("status", "")).lower()
if any(x in status for x in ["blocked", "partial", "dry", "payload"]):
    raise SystemExit(f"STOP: non-final report status: {doc.get('status')}")

if dataset not in blob and doc.get("dataset") != dataset:
    raise SystemExit("STOP: report does not reference canonical dataset")

print(json.dumps({
    "report": str(report),
    "status": doc.get("status"),
    "schema_version": doc.get("schema_version"),
}, indent=2))
PY
```

## 13. Final Preservation Checklist

Before stopping, resizing, or destroying the pod:

- Remote preflight passed.
- Remote input SHA256 manifest exists.
- Local archive hashes match remote input hashes.
- Agent A report exists, validates, and has a log and SHA256 entry.
- Agent B report exists, validates, and has a log and SHA256 entry.
- Agent C evidence packet exists, validates, and has a log and SHA256 entry.
- Small reports have been copied back by `scp`.
- `D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\SHA256SUMS` is updated.
- `D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\REPRODUCIBILITY_NOTES.md` is updated.
- RunPod Cloud Sync completed with source path `/workspace/cas-harness-large-eval`.
- No `.npz` files were staged or committed to git.
