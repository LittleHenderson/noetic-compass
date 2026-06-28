# V1 Smoke LR Fix Runlog - 2026-05-05

Status: running on RunPod.

Purpose: test whether the prior v1 collapse was caused primarily by bad training settings. This is a 3-epoch smoke only, not a full 20-epoch restart.

## Pod

- SSH: `ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519`
- Repo: `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass`
- Run dir: `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_smoke_lr_fix_2026_05_05`
- PID: `14806`
- Launch time observed: `2026-05-05 20:58 UTC`

## Command

```bash
PYTHONUNBUFFERED=1 python3 cas-native/training/train_structured_prediction.py \
  --input ../../cas-synthetic/data/level2_scaffold/level3_combined_v1_v77_relabeled.jsonl \
  --eval-input ../../cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl \
  --out-dir cas-native/training/runs/v1_smoke_lr_fix_2026_05_05 \
  --input-mode structured_token \
  --epochs 3 \
  --paraphrase-augment-train 3 \
  --limit 200000 \
  --diagram-loop-pairs 0 \
  --lr 0.001 \
  --batch-size 128 \
  --weight-decay 0.0001 \
  --device cuda \
  --train-log-every-steps 10 \
  --seed 42
```

The exact command is also saved on the pod at:

`cas-native/training/runs/v1_smoke_lr_fix_2026_05_05/launch_command.txt`

## Initial Checks

Before launch:

- GPU idle: RTX A6000, 1 MiB used, 0% util, about 25 W
- No existing `train_structured_prediction.py` process
- Target run dir did not exist

After launch:

- PID `14806` alive
- Startup log emitted:
  - `n_canonical`: 138,850
  - `n_train`: 555,400
  - `paraphrase_variants_per_record`: 3
  - stage: `tokenize_train`
- Tokenization progress began (`done=1000`, `done=2000`, ...)

## Monitor Commands

```bash
ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519 \
  "date -u; ps -p 14806 -o pid,etime,pcpu,pmem,cmd; tail -n 80 /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_smoke_lr_fix_2026_05_05/launch.log; nvidia-smi --query-gpu=name,memory.used,utilization.gpu,power.draw --format=csv,noheader"
```

Eval-only extraction once epochs land:

```bash
ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519 \
  "grep '\"event\": \"eval\"' /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_smoke_lr_fix_2026_05_05/launch.log"
```

## Decision Criteria

- If epoch 1 eval is at least 49.5% and epoch 2 is higher than epoch 1, the hot learning rate was probably the main cause. Next action: authorize a full 20-epoch run with the same restored settings.
- If epoch 1 is around 49% but epoch 2 collapses again, the learning rate was not the only issue. Next action: inspect corpus mismatch and run no-paraphrase / balanced-corpus smokes.
- If epoch 1 is below 30%, assume something deeper is broken, such as label mismatch or vocabulary issue. Stop and diagnose before any further GPU spend.

## Completion

The smoke run completed cleanly and saved the best checkpoint:

- `best_structured_token_model.pt`
- `manifest.json`
- `samples.jsonl`

Overall trajectory:

| Epoch | Train Loss | Held-Out Exact | Delta vs Hash |
|---:|---:|---:|---:|
| 0 | 2.690114 | 512/1000 = 51.2% | +2.5 pp |
| 1 | 1.148983 | 577/1000 = 57.7% | +9.0 pp |
| 2 | 0.876398 | 552/1000 = 55.2% | +6.5 pp |

Verdict: the `lr=0.001`, `batch_size=128`, `weight_decay=0.0001` fix is validated against the catastrophic-collapse failure. The failed run reached only 34.0% at epoch 2; this smoke reached 55.2% at epoch 2 and peaked at 57.7%.

However, the epoch-2 dip was not uniform noise. The manifest shows it is localized.

Per-bucket rates:

| Bucket | Epoch 0 | Epoch 1 | Epoch 2 | Epoch 1 -> 2 |
|---|---:|---:|---:|---:|
| `meta_logic` | 45.1% | 37.3% | 35.3% | -2.0 pp |
| `v74_baseline` | 37.0% | 37.0% | 32.5% | -4.5 pp |
| `v75_register` | 20.5% | 33.3% | 28.8% | -4.5 pp |
| `v76_production` | 63.9% | 76.9% | 85.2% | +8.3 pp |
| `v77_omega` | 86.1% | 96.3% | 92.5% | -3.7 pp |
| `v77_rule_four` | 66.1% | 62.7% | 61.0% | -1.7 pp |

The dip is concentrated in simpler state/register buckets while `v76_production` keeps improving. That argues against a simple "all buckets got noisy" explanation.

Per-head epoch 1 -> 2 overall:

- `drive`: 81.4% -> 75.7% (-5.7 pp)
- `noetic`: 76.9% -> 76.4% (-0.5 pp)
- `domain`: 88.7% -> 90.0% (+1.3 pp)
- Most other heads are flat or slightly up.

The main weak head is Drive. Bucket-level Drive drops:

- `v74_baseline`: 70.5% -> 59.0% (-11.5 pp)
- `v75_register`: 62.5% -> 53.4% (-9.1 pp)
- `v77_rule_four`: 88.1% -> 79.7% (-8.5 pp)
- `v77_omega`: 96.3% -> 93.3% (-3.0 pp)

The pulled `samples.jsonl` corresponds to the best checkpoint / epoch 1, not the final epoch-2 state. It is still useful because it shows the peak model's remaining weaknesses:

- Overall sample exact: 577/1000 = 57.7%
- Weak buckets at peak:
  - `v75_register`: 88/264 = 33.3%
  - `v74_baseline`: 74/200 = 37.0%
  - `meta_logic`: 38/102 = 37.3%
- Top Drive confusions at peak:
  - `F7 -> F1`: 31
  - `F5 -> F1`: 25
  - `F6 -> F1`: 25
  - `F3 -> F1`: 22
  - `F4 -> F6`: 15

Current recommendation: do not launch the full 20-epoch combined-corpus run yet. The learning-rate fix is real, but the manifest exposes a second issue: the current combined corpus/training recipe weakens Drive prediction, especially in `v74_baseline` and `v75_register`.

Next read-only/low-cost step should be a no-paraphrase 3-epoch smoke with the same restored optimizer settings:

```bash
python3 cas-native/training/train_structured_prediction.py \
  --input ../../cas-synthetic/data/level2_scaffold/level3_combined_v1_v77_relabeled.jsonl \
  --eval-input ../../cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl \
  --out-dir cas-native/training/runs/v1_smoke_lr_fix_no_para_2026_05_05 \
  --input-mode structured_token \
  --epochs 3 \
  --paraphrase-augment-train 0 \
  --limit 200000 \
  --diagram-loop-pairs 0 \
  --lr 0.001 \
  --batch-size 128 \
  --weight-decay 0.0001 \
  --device cuda \
  --train-log-every-steps 10 \
  --seed 42
```

Decision rule for that control:

- If `v74_baseline` / `v75_register` / Drive recover, the issue is paraphrase augmentation interacting badly with the combined corpus.
- If they remain weak, the issue is the combined corpus mix itself, and the next step is a balanced sampler or a recoverable-style filtered corpus smoke.
