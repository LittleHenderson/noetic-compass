# CAS-Native v2 Smoke Run Report

**Timestamp**: 20260428-105951
**Pod**: RunPod RTX A4500 (20 GB VRAM)
**Dataset**: Level 2 v1 (level2_full_10k.json, commit 74e5350)
**Status**: COMPLETED

## Hyperparameters

- batch_size: 4
- max_steps: 100
- learning_rate: 0.0001
- warmup_steps: 10
- mixed_precision: fp32 (bf16 deferred to full run)
- v2 component flags: ALL OFF (legacy v7.4-equivalent path)

## Model

- params: 73,063,424

## Loss Curve

- Step 0: 16.2283
- Step 99: 10.1064
- Min over run: 9.6849
- Max over run: 16.2283
- Direction: **DECREASING**

## Resources

- Peak GPU memory: 1.38 GB / 20 GB
- Wall-clock total: 8.7s
- Per-step avg: 0.09s
- Steps/sec: 11.45

## Pipeline Status

Pipeline validated end-to-end on cloud GPU. Ready for full 3-epoch training on similar compute when scheduled.
