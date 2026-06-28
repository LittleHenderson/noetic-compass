# V1 Smoke Drive Class-Weighted Loss Runlog - 2026-05-06

Status: running on RunPod.

Purpose: test option C after the Drive-balanced sampler failed. This keeps the natural record stream and paraphrase x3, but weights only the Drive head loss by inverse Drive class frequency.

## Code Change

Local files changed:

- `noetic-compass-scaffold/noetic-compass/cas-native/model/structured_prediction.py`
- `noetic-compass-scaffold/noetic-compass/cas-native/training/train_structured_prediction.py`

What changed:

- Added optional `drive_class_weights` to `structured_prediction_loss`.
- Added opt-in `--drive-class-weighted-loss`.
- The default loss path is unchanged when the flag is absent.
- Drive weights are computed from the post-filter, post-augmentation training records.
- Only the Drive cross-entropy receives class weights; all other heads stay uniform.
- Kept the existing diagnostic flags:
  - `--train-log-every-steps`
  - `--drive-balanced-sampler`
  - `--diagram-loop-pairs 0` compatibility

Local verification:

- `python -m py_compile .../train_structured_prediction.py .../structured_prediction.py`
- Tiny CPU smoke with `--drive-class-weighted-loss --diagram-loop-pairs 0 --train-log-every-steps 2`
- Smoke manifest recorded `drive_class_weighted_loss` counts and weights.

Pod backups before overwrite:

- `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/train_structured_prediction.py.codex_bak_drive_weighted_loss_20260506_0850`
- `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/model/structured_prediction.py.codex_bak_drive_weighted_loss_20260506_0850`

Pod verification after overwrite:

- `python3 -m py_compile cas-native/training/train_structured_prediction.py cas-native/model/structured_prediction.py`
- `--help` exposes:
  - `--diagram-loop-pairs`
  - `--train-log-every-steps`
  - `--drive-balanced-sampler`
  - `--drive-class-weighted-loss`

## Pod

- SSH: `ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519`
- Repo: `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass`
- Run dir: `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_smoke_drive_class_weighted_loss_2026_05_06`
- PID: `16433`
- Launch time observed: `2026-05-06 08:51 UTC`

## Command

```bash
PYTHONUNBUFFERED=1 python3 cas-native/training/train_structured_prediction.py \
  --input ../../cas-synthetic/data/level2_scaffold/level3_combined_v1_v77_relabeled.jsonl \
  --eval-input ../../cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl \
  --out-dir cas-native/training/runs/v1_smoke_drive_class_weighted_loss_2026_05_06 \
  --input-mode structured_token \
  --epochs 3 \
  --paraphrase-augment-train 3 \
  --drive-class-weighted-loss \
  --limit 200000 \
  --diagram-loop-pairs 0 \
  --lr 0.001 \
  --batch-size 128 \
  --weight-decay 0.0001 \
  --seed 42 \
  --device cuda \
  --train-log-every-steps 10
```

The exact command is also saved on the pod at:

`cas-native/training/runs/v1_smoke_drive_class_weighted_loss_2026_05_06/launch_command.txt`

## Initial Checks

Before launch:

- GPU idle: RTX A6000, 1 MiB used, 0% util, about 25 W
- No existing `train_structured_prediction.py` process
- Target run dir did not exist

After launch:

- PID `16433` alive
- Startup log emitted:
  - `n_canonical`: 138,850
  - `n_train`: 555,400
  - `paraphrase_variants_per_record`: 3
  - stage: `tokenize_train`

This confirms the run preserves the paraphrase x3 corpus size and changes only the Drive loss weighting.

## Monitor Commands

```bash
ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519 \
  "date -u; ps -p 16433 -o pid,etime,pcpu,pmem,cmd; tail -n 80 /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_smoke_drive_class_weighted_loss_2026_05_06/launch.log; nvidia-smi --query-gpu=name,memory.used,utilization.gpu,power.draw --format=csv,noheader"
```

Eval extraction once epochs land:

```bash
ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519 \
  "grep '\"event\": \"eval\"' /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_smoke_drive_class_weighted_loss_2026_05_06/launch.log"
```

Manifest pull after completion:

```bash
scp -P 15409 -i ~/.ssh/id_ed25519 \
  root@104.255.9.187:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_smoke_drive_class_weighted_loss_2026_05_06/manifest.json \
  ./v1_smoke_drive_class_weighted_loss_manifest_20260506.json
```

## Decision Criteria

Compare against the prior three smokes:

- Paraphrase x3, no sampler: peak overall 57.7%, Drive 81.4%, but F1 over-predicted +42%.
- No paraphrase: overall 44.4%, Drive 77.2%, too thin for v75/v76.
- Drive-balanced sampler: peak overall 50.9%, Drive 76.2%, moved bias from F1 to F6.

Greenlight full retry only if class-weighted loss keeps the paraphrase lift and reduces Drive bias:

- Overall exact at epoch 2 should stay near or above 55%.
- Drive head should be at least 80%.
- F1 over-prediction should be materially lower than +42%.
- F6 should not become the new over-predicted sink.
- `v75_register` and `v76_production` should not crash.

If overall is healthy but Drive bias remains, inverse-frequency loss is too weak or the class signal is structurally ambiguous; next step would be a smaller targeted architecture/loss change rather than another sampler.

