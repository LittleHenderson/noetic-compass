# V1 Collapse Diagnosis - 2026-05-05

Status: read-only diagnosis after stopped RunPod run. No restart performed.

Run inspected:

- Pod: `root@104.255.9.187 -p 15409`
- Run dir: `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_observed_restart`
- Frozen log copied locally as: `launch_stopped_after_epoch2_collapse_20260505.log`
- Local diagnosis artifact: this file

## What Happened

The run was healthy mechanically, but bad statistically.

Log counts:

- `startup`: 4
- `startup_progress`: 557
- `train_progress`: 2,854
- `epoch_end`: 3
- `eval`: 3

Trajectory:

| Epoch | Train Loss | Held-Out Exact | Delta vs Hash |
|---:|---:|---:|---:|
| 0 | 1.563305 | 495/1000 = 49.5% | +0.8 pp |
| 1 | 0.770650 | 454/1000 = 45.4% | -3.3 pp |
| 2 | 0.661895 | 340/1000 = 34.0% | -14.7 pp |

Plain diagnosis: the model was learning the training set while getting worse on the held-out set. That is not a GPU issue or a logging issue. It is a training recipe/data split issue.

## Primary Cause Found

The full run used the script's smoke-test defaults instead of the successful structured-token baseline settings.

Failed run command omitted these successful-run flags:

- `--lr 0.001`
- `--batch-size 128`
- `--weight-decay 0.0001`

Because they were omitted, the script used:

- `lr = 0.01`
- `batch_size = 64`
- `weight_decay = 0.0`

That is a 10x hotter learning rate, half the batch size, and no regularization. On this larger mixed corpus, that is the cleanest explanation for the fast eval collapse.

Successful comparison runs:

| Run | LR | Batch | Weight Decay | Train Rows | Result |
|---|---:|---:|---:|---:|---:|
| `structured-token-20epoch-gpu-20260502-001907` | 0.001 | 128 | 0.0001 | 17,974 | 85.3% |
| `structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045` | 0.001 | 128 | 0.0001 | 66,280 | 86.8% |
| failed observed restart | 0.01 | 64 | 0.0 | 555,400 after augmentation | 49.5% -> 45.4% -> 34.0% |

Important: paraphrase augmentation by itself is probably not the main cause. The successful `v77fix` run also used `--paraphrase-augment-train 3` and improved from 45.0% at epoch 0 to 86.8% final. The failed run combined paraphrase augmentation with much hotter training settings and a much larger/more mixed corpus.

## Corpus Facts

The input file has 162,230 rows. The trainer then filters eval overlaps by:

- `id`
- `source_level2_id`
- `cas_expression`

Filter result:

- Raw train rows: 162,230
- Removed by eval-overlap filter: 23,380
- Kept canonical rows: 138,850
- After `--paraphrase-augment-train 3`: 555,400 training rows

Overlap removal:

- Removed by `cas_expression`: 23,380
- Removed by `source_level2_id`: 16,104
- Match sets:
  - `cas_expression` only: 7,276
  - `source_level2_id + cas_expression`: 16,104

Post-filter kept corpus:

| Slice | Rows |
|---|---:|
| `rule_based_v1` | 89,140 |
| `free_form_v1` | 49,710 |
| demographic/tonal tagged | 89,140 |
| no demographic/tone tag | 49,710 |

Post-filter buckets:

| Bucket | Rows | Share |
|---|---:|---:|
| `v77_omega` | 35,798 | 25.782% |
| `v75_register` | 33,268 | 23.960% |
| `v74_baseline` | 24,604 | 17.720% |
| `meta_logic` | 20,514 | 14.774% |
| `v76_production` | 15,156 | 10.915% |
| `v77_rule_four` | 9,510 | 6.849% |

Held-out eval buckets:

| Bucket | Rows | Share |
|---|---:|---:|
| `v77_omega` | 267 | 26.700% |
| `v75_register` | 264 | 26.400% |
| `v74_baseline` | 200 | 20.000% |
| `v76_production` | 108 | 10.800% |
| `meta_logic` | 102 | 10.200% |
| `v77_rule_four` | 59 | 5.900% |

The bucket mix is not wildly different. The bigger data risk is style mix:

- Train after filter: 64.199% demographic/tonal or free-form distribution shift relative to eval.
- Eval: 100% old recoverable deterministic style with no demographic/tone tags.

This is a real risk, but it should be tested after restoring the known-good hyperparameters.

## Label Consistency

No missing `bucket` or `cas_expression` rows were found in local JSONL parsing.

Distribution differences on core CAS axes are modest:

- Noetic largest delta: about 1.4 pp.
- Domain largest delta: about 2.2 pp.
- Drive largest delta: `MISSING` drive is 19.1% train vs 14.9% eval, about 4.2 pp.
- Meta-logic is 14.8% train vs 10.2% eval, about 4.6 pp.

These differences can hurt, but they do not explain a collapse from 49.5% to 34.0% in two epochs as cleanly as the bad training settings do.

## Recommended No-Restart Path

Before any full 20-epoch rerun, run tiny smokes only. Pass condition: eval must improve for 1-3 epochs, not collapse.

Smoke A - restore known-good training settings on the same combined corpus:

```bash
python3 cas-native/training/train_structured_prediction.py \
  --input ../../cas-synthetic/data/level2_scaffold/level3_combined_v1_v77_relabeled.jsonl \
  --eval-input ../../cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl \
  --out-dir cas-native/training/runs/v1_smoke_known_good_hparams_20260505 \
  --input-mode structured_token \
  --epochs 3 \
  --paraphrase-augment-train 3 \
  --limit 200000 \
  --diagram-loop-pairs 0 \
  --device cuda \
  --train-log-every-steps 25 \
  --lr 0.001 \
  --batch-size 128 \
  --weight-decay 0.0001
```

Smoke B - same as A, but no train-time paraphrase augmentation:

```bash
  --paraphrase-augment-train 0
```

Smoke C - same as A, but stricter learning rate if A still drops:

```bash
  --lr 0.0003
```

Smoke D - train only on eval-style recoverable/rule-based rows, no free-form/demographic-tonal expansion, if A improves but stays low.

## Decision Rule

Do not run a full 20-epoch job until a smoke run shows:

- Epoch 0 eval at or above roughly 45-50%, and
- Epoch 1/2 eval increases rather than drops.

If Smoke A improves, the failure was mostly the bad hyperparameter recipe.

If Smoke A still collapses but Smoke B improves, paraphrase augmentation is interacting badly with the combined corpus.

If A and B both fail but D improves, the combined corpus is fighting the recoverable-only eval and needs either a balanced sampler or a matching eval suite.

