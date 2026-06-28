# V1 Smoke Drive-Balanced Sampler Runlog - 2026-05-05

Status: running on RunPod.

Purpose: test whether a Drive-balanced sampler can preserve the paraphrase x3 lift while reducing the F1/F6 Drive bias seen in the LR-fix smoke.

## Code Change

Local file changed:

- `noetic-compass-scaffold/noetic-compass/cas-native/training/train_structured_prediction.py`

What changed:

- Added opt-in `--drive-balanced-sampler`.
- The default path is unchanged: normal per-epoch shuffle without replacement.
- When enabled, each epoch samples with replacement from Drive groups so F1-F7 are exposed roughly evenly.
- Added `--train-log-every-steps` locally, matching the pod observability patch from the earlier stuck-run diagnosis.
- Added `--diagram-loop-pairs 0` compatibility so combined-run commands still parse. Nonzero values are rejected in this trainer path.

Local verification:

- `python -m py_compile .../train_structured_prediction.py`
- Tiny CPU smoke with `--drive-balanced-sampler --diagram-loop-pairs 0 --train-log-every-steps 1`

Pod backup before overwrite:

- `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/train_structured_prediction.py.codex_bak_drive_sampler_20260506_0338`

Pod verification after overwrite:

- `python3 -m py_compile cas-native/training/train_structured_prediction.py`
- `--help` exposes:
  - `--diagram-loop-pairs`
  - `--train-log-every-steps`
  - `--drive-balanced-sampler`

## Pod

- SSH: `ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519`
- Repo: `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass`
- Run dir: `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_smoke_drive_balanced_sampler_2026_05_05`
- PID: `15781`
- Launch time observed: `2026-05-06 03:42 UTC`

## Command

```bash
PYTHONUNBUFFERED=1 python3 cas-native/training/train_structured_prediction.py \
  --input ../../cas-synthetic/data/level2_scaffold/level3_combined_v1_v77_relabeled.jsonl \
  --eval-input ../../cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl \
  --out-dir cas-native/training/runs/v1_smoke_drive_balanced_sampler_2026_05_05 \
  --input-mode structured_token \
  --epochs 3 \
  --paraphrase-augment-train 3 \
  --drive-balanced-sampler \
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

`cas-native/training/runs/v1_smoke_drive_balanced_sampler_2026_05_05/launch_command.txt`

## Initial Checks

Before launch:

- GPU idle: RTX A6000, 1 MiB used, 0% util, about 25 W
- No existing `train_structured_prediction.py` process
- Target run dir did not exist

After launch:

- PID `15781` alive
- Startup log emitted:
  - `n_canonical`: 138,850
  - `n_train`: 555,400
  - `paraphrase_variants_per_record`: 3
  - stage: `tokenize_train`
- Tokenization progress began (`done=1000`, `done=2000`, ...)

## Monitor Commands

```bash
ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519 \
  "date -u; ps -p 15781 -o pid,etime,pcpu,pmem,cmd; tail -n 80 /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_smoke_drive_balanced_sampler_2026_05_05/launch.log; nvidia-smi --query-gpu=name,memory.used,utilization.gpu,power.draw --format=csv,noheader"
```

Eval extraction once epochs land:

```bash
ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519 \
  "grep '\"event\": \"eval\"' /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_smoke_drive_balanced_sampler_2026_05_05/launch.log"
```

Manifest pull after completion:

```bash
scp -P 15409 -i ~/.ssh/id_ed25519 \
  root@104.255.9.187:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_smoke_drive_balanced_sampler_2026_05_05/manifest.json \
  ./v1_smoke_drive_balanced_sampler_manifest_20260505.json
```

## Decision Criteria

Compare against the LR-fix paraphrase smoke:

- Overall exact peak: 57.7%
- Epoch-2 overall: 55.2%
- Epoch-2 Drive head: 75.7%
- Problem shape: Drive bias toward F1/F6, especially in `v74_baseline`, `v75_register`, and `v77_rule_four`.

Greenlight full retry only if the balanced sampler keeps paraphrase lift and improves Drive:

- Overall exact at epoch 2 should stay near or above 55%.
- Drive head at epoch 2 should recover to at least 80%.
- Predicted Drive distribution should reduce F1 over-prediction without crashing `v76_production` / `v75_register`.

If overall improves but Drive remains around 75%, the sampler is insufficient; try Drive class-weighted loss next.

If Drive improves but overall/buckets crash, the sampler is too aggressive; try class-weighted loss or capped oversampling instead of full uniform Drive exposure.

