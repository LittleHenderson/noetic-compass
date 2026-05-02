# Structured-Token Paraphrase Retrain Report

Run: `structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045`

Date: 2026-05-02

Hardware: RunPod NVIDIA RTX A6000

## Inputs

- Training input: `cas-synthetic/data/level2_scaffold/level3_recoverable_full_v77_relabeled.jsonl`
- Held-out eval: `cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000.jsonl`
- Base training corpus: `level3_recoverable_full.jsonl`, 19,454 records
- v7.7 relabel count: 1,198 `v77_rule_four` overlap records relabeled to `v77_omega`
- Eval-overlap filter removed: 2,884 records
- Canonical train records after filter: 16,570
- Training paraphrases: 49,710
- Total train records: 66,280
- Vocabulary size: 293

## Command

```bash
python3 -u /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/train_structured_prediction.py \
  --input /workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_recoverable_full_v77_relabeled.jsonl \
  --limit 100000 \
  --eval-input /workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000.jsonl \
  --input-mode structured_token \
  --epochs 20 \
  --batch-size 128 \
  --d-model 128 \
  --bottleneck-dim 64 \
  --lr 0.001 \
  --weight-decay 0.0001 \
  --device cuda \
  --seed 42 \
  --max-length 256 \
  --vocab-min-count 1 \
  --paraphrase-augment-train 3 \
  --out-dir /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045
```

## Canonical Eval

- All-heads exact: 868/1000 = 86.8%
- Prior current-eval checkpoint: 851/1000 = 85.1%
- Delta vs prior current-eval checkpoint: +1.7 pp
- Hash baseline: 48.7%
- Delta vs hash: +38.1 pp

Best epoch was epoch 10.

## Bucket Results

| Bucket | n | Exact | Rate |
|---|---:|---:|---:|
| v74_baseline | 200 | 199 | 99.5% |
| v75_register | 264 | 244 | 92.4% |
| v76_production | 108 | 102 | 94.4% |
| v77_omega | 203 | 201 | 99.0% |
| meta_logic | 102 | 80 | 78.4% |
| v77_rule_four | 123 | 42 | 34.1% |

## Paraphrase Eval

Against 3 held-out eval paraphrases per canonical record:

- Paraphrase all-heads exact: 41.3%
- Prediction consistency vs canonical: 48.4%
- Canonical-exact retention: 46.7%

Prior paraphrase baseline from Session 43:

- Paraphrase all-heads exact: 37.2%
- Prediction consistency vs canonical: 44.4%
- Canonical-exact retention: 42.4%

This run improves paraphrase exact by +4.1 pp and consistency by +4.0 pp while also improving canonical exact by +1.7 pp.

## Important Diagnosis

An earlier run in this session accidentally used `cas-synthetic/data/level3_pilot_full.jsonl`, which is a conversational/free-form corpus, not the recoverable slot-reading corpus. That wrong-corpus run collapsed to 1.4% exact and is not a valid model result. The correct training file for this structured-token prediction harness is `cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl`.

## Remaining Bottleneck

The main canonical failure remains `v77_rule_four`: 81/123 failures. Of those, the 64 old held-out `omega_emergent` records are still labeled as `v77_rule_four` in eval but are structurally `v77_omega`; the new relabeled training data correctly teaches them as omega. Future evaluation should relabel or regenerate the held-out eval set to remove that historical structural overlap.
