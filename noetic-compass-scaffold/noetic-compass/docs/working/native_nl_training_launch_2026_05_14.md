# CAS Native NL Training Launch - 2026-05-14

## Status

Training started on 2026-05-14.

Completed locally:

- CPU smoke test passed.
- Real-path micro-run passed on the Native NL corpus.
- Manifest-based micro-run passed against `v1_dialogue_50k_claude_20260507_manifest.json`, proving the trainer now reads all sharded corpus files through one manifest.

Full training should run on a GPU box, not Render or Vercel. Render is for serving the API after a checkpoint exists; it is not the right place to train the model.

## Full GPU Command

Run this from the `noetic-compass-scaffold/noetic-compass` directory on the GPU machine. Adjust `/workspace/tksCAS` if the corpus is mounted somewhere else.

```bash
python cas-native/training/train_native_nl_gen.py \
  --data-path /workspace/tksCAS/cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_manifest.json \
  --output-dir cas-native/training/runs/native_nl_full_50k_20260514 \
  --epochs 5 \
  --batch-size 16 \
  --device cuda \
  --d-model 512 \
  --encoder-n-layers 6 \
  --encoder-n-heads 8 \
  --head-n-layers 6 \
  --head-n-heads 8 \
  --max-prompt-len 256 \
  --max-reply-len 256 \
  --max-cas-prefix-len 32 \
  --logging-steps 50 \
  --train-log-every-steps 20 \
  --sample-every-steps 250 \
  --sample-record-indices 0,10,50,100,250 \
  --sample-max-new-tokens 96 \
  --sample-sampling greedy \
  --english-bpe-path /workspace/tksCAS/cas-synthetic/data/native_nl/english_bpe_50k_claude_20260507.json \
  --use-cas-prefix \
  --seed 20260514
```

## Watch Progress

```bash
tail -f cas-native/training/runs/native_nl_full_50k_20260514/training_events.jsonl
```

The key artifacts at completion are:

- `model_final.pt`
- `tokenizer.json`
- `english_bpe.json`
- `training_events.jsonl`
- `checkpoint_manifest.json`

## Serving After Training

After the run finishes, point the API at the run directory:

```bash
NC_CAS_NATIVE_PREDICTOR_RUN_DIR=cas-native/training/runs/native_nl_full_50k_20260514
NC_CAS_NATIVE_PREDICTOR_DEVICE=cpu
NC_CAS_NATIVE_PREDICTOR_ENABLED=true
```

Mode 7 `/mode7/runtime` should then report `predictor_ready: true` once the API can see the checkpoint artifacts and import torch.
