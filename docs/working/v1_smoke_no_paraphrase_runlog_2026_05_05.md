# V1 Smoke No-Paraphrase Runlog - 2026-05-05

Status: running on RunPod.

Purpose: isolate whether the Drive-head weakness in the LR-fix smoke came from `--paraphrase-augment-train 3` interacting with the mixed corpus, or from the canonical combined corpus itself.

## Pod

- SSH: `ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519`
- Repo: `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass`
- Run dir: `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_smoke_no_paraphrase_2026_05_05`
- PID: `15217`
- Launch time observed: `2026-05-06 02:15 UTC`

## Command

```bash
PYTHONUNBUFFERED=1 python3 cas-native/training/train_structured_prediction.py \
  --input ../../cas-synthetic/data/level2_scaffold/level3_combined_v1_v77_relabeled.jsonl \
  --eval-input ../../cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl \
  --out-dir cas-native/training/runs/v1_smoke_no_paraphrase_2026_05_05 \
  --input-mode structured_token \
  --epochs 3 \
  --paraphrase-augment-train 0 \
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

`cas-native/training/runs/v1_smoke_no_paraphrase_2026_05_05/launch_command.txt`

## Initial Checks

Before launch:

- GPU idle: RTX A6000, 1 MiB used, 0% util, about 25 W
- No existing `train_structured_prediction.py` process
- Target run dir did not exist

After launch:

- PID `15217` alive
- Startup log emitted:
  - `n_canonical`: 138,850
  - `n_train`: 138,850
  - `paraphrase_variants_per_record`: 0
  - stage: `tokenize_train`
- Tokenization progress began (`done=1000`, ...)

This confirms the control is clean: same canonical post-filter count as the LR-fix smoke, but no 3x paraphrase expansion.

## Monitor Commands

```bash
ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519 \
  "date -u; ps -p 15217 -o pid,etime,pcpu,pmem,cmd; tail -n 80 /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_smoke_no_paraphrase_2026_05_05/launch.log; nvidia-smi --query-gpu=name,memory.used,utilization.gpu,power.draw --format=csv,noheader"
```

Eval extraction once epochs land:

```bash
ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519 \
  "grep '\"event\": \"eval\"' /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_smoke_no_paraphrase_2026_05_05/launch.log"
```

Manifest pull after completion:

```bash
scp -P 15409 -i ~/.ssh/id_ed25519 \
  root@104.255.9.187:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_smoke_no_paraphrase_2026_05_05/manifest.json \
  ./v1_smoke_no_paraphrase_manifest_20260505.json
```

## Decision Criteria

- If epoch 2 Drive head is at least 80% and overall exact is at least 55%, the paraphrase/mixed-corpus interaction is the likely cause. Next action: consider full retry with `--paraphrase-augment-train 0`.
- If epoch 2 Drive head is still about 75% or worse, the canonical combined corpus itself is causing the Drive weakness. Next action: no full retry; inspect corpus balancing, especially Drive distribution and bucket stratification.
- If epoch 2 Drive head is around 70% or worse, paraphrase was helping rather than hurting. Next action: rethink the augmentation strategy rather than simply dropping paraphrases.

## Prior Comparison

Previous LR-fix smoke with `--paraphrase-augment-train 3`:

| Epoch | Train Loss | Held-Out Exact |
|---:|---:|---:|
| 0 | 2.690114 | 51.2% |
| 1 | 1.148983 | 57.7% |
| 2 | 0.876398 | 55.2% |

Important weakness in that run:

- Overall Drive head dropped from 81.4% at epoch 1 to 75.7% at epoch 2.
- Bucket-level Drive drops were strongest in `v74_baseline`, `v75_register`, and `v77_rule_four`.

