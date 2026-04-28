# CAS-Native v2 First Full Training Run

Run: `v2-first-full-20260428-135024`

Date: 2026-04-28

Hardware: RunPod RTX A6000

Dataset: `cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl`

## Summary

- Status: `COMPLETED`
- Wall-clock: 201.7 seconds / 3.4 minutes
- Final step: 750 / 750
- Epochs: 3
- Batch size: 32
- Peak GPU memory: 2.93 GB / 49 GB
- NaN/Inf: none
- OOM: none
- Checkpoints: written locally under `checkpoints/`, ignored by Git via `.gitignore`

## Active Components

- `use_register_film`
- `use_emergent_register`
- `use_production_semantics`
- `use_expression_proposer`
- `use_rust_validation` disabled

## Loss Trajectory

| Step | Total | LM | Production | Null-space | Proposer |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 435.9261 | 10.409 | 410.692 | 511.812 | 6.131 |
| 250 | 400.7233 | 8.016 | 381.835 | 509.640 | 5.389 |
| 500 | 215.6666 | 6.056 | 199.667 | 505.912 | 4.016 |
| 700 | 141.9603 | 5.706 | 126.638 | 503.751 | 3.407 |

Observed reduction:

- Total loss: approximately 67% down
- LM loss: approximately 45% down
- Production loss: approximately 69% down
- Proposer Rule 4 loss: approximately 44% down
- Null-space regularization: approximately 1.6% down, consistent with prior saturation analysis

## Findings

Training itself completed cleanly. The step-450 total-loss dip was caused by a batch with no v7.6 production examples, producing `production_loss=0`; the run recovered cleanly afterward.

Validation pass failed because the runner wrapped `trainer._train_step(...)` in `torch.no_grad()`, but `_train_step` performs backward/optimizer work internally. The fix for the next run is a separate eval path that computes forward/loss only and never calls `_train_step`.

GPU memory utilization was low: 2.93 GB peak on a 49 GB A6000. Future runs should test batch size 128 or 256 after the eval-loop fix.

## Artifacts

- `metrics.json`: full per-step metric history
- `train.log`: training log
- `checkpoints/step_500.pt`: local model checkpoint, ignored by Git
- `checkpoints/final.pt`: local final checkpoint, ignored by Git
