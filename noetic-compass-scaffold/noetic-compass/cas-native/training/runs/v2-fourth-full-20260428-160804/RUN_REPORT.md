# CAS-Native v2 Fourth Full Training Run

Run: `v2-fourth-full-20260428-160804`

Date: 2026-04-28

Hardware: RunPod RTX A5000

Dataset: `cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl`

## Summary

- Status: `COMPLETED`
- Wall-clock: 57.7 seconds / 1.0 minute
- Final step: 189 / 189
- Epochs: 3
- Batch size: 128
- Peak GPU memory: 8.06 GB
- NaN/Inf: none
- OOM: none
- Checkpoints: `step_100.pt` and `final.pt` retrieved locally, ignored by Git

## Runtime Gates

- `_eval_step` runtime path executed successfully at steps 50, 100, and 150.
- `production_weight` appeared in train and eval metrics.
- Production curriculum reached full weight at step 100.
- Checkpoint save fired at step 100.
- Seed initialization was added to `run_v2_full.py` before this run.

## Key Metrics

| Step | Total | LM | Production | Production Weight | Null-space | Proposer |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 24.3225 | 10.3770 | 411.8581 | 0.00 | 509.4264 | 6.1961 |
| 50 | 226.7621 | 10.1310 | 410.5120 | 0.50 | 509.2300 | 6.1190 |
| 100 | 430.1499 | 9.5640 | 409.2570 | 1.00 | 508.8410 | 5.9720 |
| 150 | 419.9560 | 8.8310 | 399.9230 | 1.00 | 508.2800 | 5.7830 |
| 175 | 417.8700 | 8.3540 | 398.3960 | 1.00 | 507.8760 | 5.6320 |

Eval totals:

- Step 50: 226.9548 over 8 batches
- Step 100: 428.3138 over 8 batches
- Step 150: 421.5708 over 8 batches

## Qualitative Assessment

The checkpoint is not yet useful for downstream qualitative generation. The qualitative run produced 30 samples across six buckets. The script's loose `compile_valid_anywhere` metric reported 24 / 30 because bare `^N` fragments compile, but the structured CAS expression rate was effectively 0 / 30.

Observed failure mode:

- Outputs were dominated by `[UNK]`.
- The model emitted occasional bare Noetic tokens `^0` through `^9`.
- It did not assemble structured states such as `^N^D_{Fk}|R`.
- It did not produce valid recipes, named emergent assignments, typed clusters, or Rule 4 structures.

Interpretation: training mechanics are working, but 189 updates on a 73M-parameter scratch model are not enough for structured CAS generation. Longer training and tokenizer improvements are required.

## Next Recommendations

- Do not treat this checkpoint as a product-quality model.
- Train at least 10x longer for the next qualitative check.
- Move from the whitespace `SimpleTokenizer` to BPE/SentencePiece or reserve CAS structural tokens to reduce `[UNK]` leakage.
- Tighten qualitative scoring so bare `^N` fragments do not count as structured CAS success.

## Artifacts

- `metrics.json`: full per-step metric history
- `train.log`: training log
- `checkpoints/step_100.pt`: local checkpoint, ignored by Git
- `checkpoints/final.pt`: local final checkpoint, ignored by Git
- `cas-native/inference/runs/qualitative-20260428-161231/samples.jsonl`: qualitative samples
- `cas-native/inference/runs/qualitative-20260428-161231/bucket_summary.json`: automated loose validity summary
- `cas-native/inference/runs/qualitative-20260428-161231/comparison_report.md`: detailed qualitative review
