# RunPod Preservation Manifest - 2026-05-26

This manifest documents the local preservation state before upgrading or destroying the RunPod. It is a documentation manifest only; no code was changed.

## Local Backup Files

Both backup archives are stored in the local repository root:

- `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_runpod_operational_backup_20260526.tar.gz`
  - Local compressed size observed: 157,153 bytes.
  - Purpose: operational worker/runtime preservation.
- `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_runpod_tksCAS_metadata_backup_20260526.tar.gz`
  - Local compressed size observed: 20,696,410 bytes.
  - Purpose: `/workspace/tksCAS` metadata preservation without large tensor/checkpoint binaries.

## Remote Inventory Observed Before Backup

- `/root/atlas-live-worker-run` - approximately 440K.
- `/root/atlas-live-worker-run.backup-20260525-0958` - approximately 288K.
- `/workspace/atlas-live-worker-current` - approximately 11M.
- `/workspace/atlas-live-worker-3615f13` - approximately 11M.
- `/workspace/atlas-live-worker-b180754` - approximately 11M.
- `/workspace/tksCAS` - approximately 30G, mostly `.pt` checkpoint payloads.

## What Was Backed Up

### Operational Backup

Archive: `cas_runpod_operational_backup_20260526.tar.gz`

This archive preserves the live worker operational surface observed on the RunPod. The tarball stores relative paths, not absolute `/root` or `/workspace` paths. The listing begins with these roots and files:

- `atlas-live-worker-run/`
- `atlas-live-worker-run.backup-20260525-0958/`
- `start-atlas-live-worker.sh`
- `worker.pid`
- `.runpod/config.toml`
- `atlas-live-worker-current/`
- `atlas-live-worker-3615f13/`
- `atlas-live-worker-b180754/` based on the observed remote inventory

The worker directories include app code, runtime modules, schemas, route handlers, tests, `Dockerfile`, `requirements.txt`, startup scripts, README/acceptance notes, and operational logs where present.

### tksCAS Metadata Backup

Archive: `cas_runpod_tksCAS_metadata_backup_20260526.tar.gz`

This archive is rooted at:

- `tksCAS/`

It preserves non-checkpoint metadata from `/workspace/tksCAS`, including manifests, trainer logs, evaluation reports, findings, run markers, tokenizers such as `english_bpe.json` and `tokenizer.json`, shell scripts, watcher logs, and `.pt.manifest.json` files where present.

This archive does not preserve the actual large model/checkpoint tensors.

## What Was Intentionally Not Backed Up

The metadata backup intentionally excludes:

- `*.pt`
- `*.safetensors`
- `*.bin`
- `*.npz`
- `__pycache__/`
- `*.pyc`
- `.cache/`

The operational backup intentionally excludes cache and Python bytecode artifacts.

The backup set should not be treated as a full machine image. It does not claim preservation of Docker image layers, package caches, virtual environments, transient process state, active tunnels, external services, or any remote files outside the listed operational worker paths and `/workspace/tksCAS` metadata selection.

## Key Risk If the Pod Is Destroyed or Upgraded

The large training checkpoints in `/workspace/tksCAS` were not pulled locally. If the upgrade destroys the RunPod filesystem or the attached volume and there is no separate RunPod snapshot, object-store copy, or other binary checkpoint backup, those checkpoint weights are at risk of permanent loss.

Other remaining risks:

- Any files matching the metadata exclusion patterns are not in the local tarballs.
- Any remote edits outside the observed inventory are not covered by this manifest.
- `worker.pid` is historical evidence only and should not be restored as proof of a live process.
- Runtime reproducibility still depends on compatible Python, CUDA, driver, package, and base-image state. The worker backup contains `requirements.txt` and `Dockerfile` where present, but the restored environment still needs to be rebuilt and tested.
- The local tarballs are a single local copy in the repository root. If this workstation copy is deleted or corrupted, the preserved material is lost unless duplicated elsewhere.

## Safe To Upgrade If...

Treat the pod as safe to upgrade only if all applicable items are true:

- Both local tarballs listed above are present outside the RunPod.
- `tar -tzf cas_runpod_operational_backup_20260526.tar.gz` can list the operational archive.
- `tar -tzf cas_runpod_tksCAS_metadata_backup_20260526.tar.gz` can list the metadata archive.
- The user accepts that large checkpoint/model binaries from `/workspace/tksCAS` are not preserved in these local archives.
- Any must-keep `.pt`, `.safetensors`, `.bin`, or `.npz` files have been separately copied, snapshotted, or confirmed disposable.
- The RunPod upgrade will preserve the intended persistent volume, or a separate volume snapshot exists.
- No additional remote directories outside the observed inventory need preservation.
- Restore has been tested or the user is comfortable rebuilding the runtime from the worker files, `requirements.txt`, and `Dockerfile`.

## New H100 Pod Verification

After the preservation backup, a replacement RunPod was inspected at:

- SSH: `root@31.24.80.42 -p 18251`
- GPU: NVIDIA H100 80GB HBM3.
- Persistent volume: `/workspace`, 187GB available.
- Worker source staged at `/workspace/atlas-live-worker-current`.
- Runtime copy staged at `/root/atlas-live-worker-run`.
- Startup hook installed at `/root/start-atlas-live-worker.sh`, `/workspace/start-atlas-live-worker.sh`, and `/pre_start.sh`.

Local pod health checks on the new pod returned:

```json
{
  "status": "ok",
  "worker_version": "m2-real-pythia",
  "model_id": "EleutherAI/pythia-160m",
  "is_real_model": true,
  "model_loaded": true,
  "load_error": null
}
```

The real-mode proof endpoint returned:

```json
{
  "verdict": "REAL_PYTHIA_WEIGHTS_LOADED",
  "is_real_model": true,
  "fake_runtime_env": false,
  "model_loaded": true,
  "load_error": null,
  "manifest_is_real_model": true,
  "model_id": "EleutherAI/pythia-160m",
  "worker_version": "m2-real-pythia"
}
```

The direct pod IP did not expose `8080` externally, but RunPod's public proxy
for `8888` is reachable. The worker was also started on `8888`, and this public
endpoint returned `REAL_PYTHIA_WEIGHTS_LOADED`:

- `https://6bmmab3vbf1yij-8888.proxy.runpod.net/health/realmode`

Set the noetic-compass API environment variable to:

```text
ATLAS_LIVE_WORKER_URL=https://6bmmab3vbf1yij-8888.proxy.runpod.net
```

The hosted Atlas app should be considered fully live-connected only after the
Render API proxy reports the same real-mode verdict through
`/atlas/live/health/realmode`.

## Restore Outline

Do not extract blindly over an active system. Extract into a staging directory first, inspect, then copy into place.

### 1. Verify The Local Archives

From the local repository root:

```powershell
cd C:\Users\wakil\OneDrive\Desktop\tksCAS
tar -tzf cas_runpod_operational_backup_20260526.tar.gz
tar -tzf cas_runpod_tksCAS_metadata_backup_20260526.tar.gz
```

### 2. Stage Locally For Inspection

```powershell
New-Item -ItemType Directory -Force C:\tmp\runpod_restore_20260526\operational
New-Item -ItemType Directory -Force C:\tmp\runpod_restore_20260526\metadata
tar -xzf C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_runpod_operational_backup_20260526.tar.gz -C C:\tmp\runpod_restore_20260526\operational
tar -xzf C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_runpod_tksCAS_metadata_backup_20260526.tar.gz -C C:\tmp\runpod_restore_20260526\metadata
```

Expected staged roots include:

- `C:\tmp\runpod_restore_20260526\operational\atlas-live-worker-run`
- `C:\tmp\runpod_restore_20260526\operational\atlas-live-worker-run.backup-20260525-0958`
- `C:\tmp\runpod_restore_20260526\operational\.runpod`
- `C:\tmp\runpod_restore_20260526\operational\atlas-live-worker-current`
- `C:\tmp\runpod_restore_20260526\metadata\tksCAS`

### 3. Restore Onto A New Or Upgraded Pod

Copy the tarballs to the pod, then extract into staging paths:

```bash
mkdir -p /tmp/runpod_restore_20260526/operational
mkdir -p /tmp/runpod_restore_20260526/metadata
tar -xzf /path/to/cas_runpod_operational_backup_20260526.tar.gz -C /tmp/runpod_restore_20260526/operational
tar -xzf /path/to/cas_runpod_tksCAS_metadata_backup_20260526.tar.gz -C /tmp/runpod_restore_20260526/metadata
```

Map staged content back to the intended locations:

```bash
mkdir -p /root /workspace
rsync -a /tmp/runpod_restore_20260526/operational/atlas-live-worker-run/ /root/atlas-live-worker-run/
rsync -a /tmp/runpod_restore_20260526/operational/atlas-live-worker-run.backup-20260525-0958/ /root/atlas-live-worker-run.backup-20260525-0958/
rsync -a /tmp/runpod_restore_20260526/operational/.runpod/ /root/.runpod/
install -m 0755 /tmp/runpod_restore_20260526/operational/start-atlas-live-worker.sh /root/start-atlas-live-worker.sh
rsync -a /tmp/runpod_restore_20260526/operational/atlas-live-worker-current/ /workspace/atlas-live-worker-current/
rsync -a /tmp/runpod_restore_20260526/operational/atlas-live-worker-3615f13/ /workspace/atlas-live-worker-3615f13/
rsync -a /tmp/runpod_restore_20260526/operational/atlas-live-worker-b180754/ /workspace/atlas-live-worker-b180754/
rsync -a /tmp/runpod_restore_20260526/metadata/tksCAS/ /workspace/tksCAS/
```

Then reinstall and validate dependencies from the restored worker tree selected for use:

```bash
cd /root/atlas-live-worker-run
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest
```

Start the worker using the restored startup script after dependency validation. Do not rely on the restored `worker.pid` as a running process marker.

### 4. Restore Checkpoints Separately

If checkpoint execution or evaluation is required, restore the excluded checkpoint/model binaries from a separate source before running checkpoint-dependent jobs:

- RunPod persistent volume retained across upgrade.
- RunPod snapshot.
- Object storage backup.
- Separate local or remote copy of `*.pt`, `*.safetensors`, `*.bin`, or `*.npz` files.

The metadata archive can restore checkpoint manifests and logs, but not the checkpoint weights themselves.
