# Simplex MVP — Diagnostic Replay Plan (ready for pod)

**Date locked:** 2026-05-11
**Status:** READY. Awaiting pod funding + user authorization to launch.
**Scope:** Diagnostics only. **v0-rc1 remains canonical.** No product-path changes.

## The single diagnostic replay run

Same setup as Stage 7 v7.1b (verified from saved report):

| Setting | Value | Source |
|---|---|---|
| d_model | 384 | v7.1b config_summary |
| encoder_n_layers | 4 | v7.1b config_summary |
| decoder_n_layers | 6 | v7.1b config_summary |
| encoder_n_heads | 6 | v7.1b config_summary |
| decoder_n_heads | 6 | v7.1b config_summary |
| **batch_size** | **16** | v7.1b config_summary (do NOT change per user 2026-05-11) |
| lr | 1e-4 | v7.1b config_summary |
| ablation | full | v7.1b config_summary |
| weight_decay | 1e-4 | v7.1b launch flags |
| grad_clip | 1.0 | v7.1b launch flags |
| n_steps | 1000 | matches v7.1b |
| seed | 1729 | matches v7.1b |
| limit | 7000 | matches v7.1b |
| device | cuda:0 | RunPod A6000 |

### Launch command

```
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT=/workspace/tksCAS/stage7_diagnostic_replay_${TS}

nohup python /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py \
  --data-path /workspace/tksCAS/cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl \
  --output-dir ${OUT} \
  --device cuda:0 \
  --d-model 384 --encoder-n-layers 4 --decoder-n-layers 6 \
  --encoder-n-heads 6 --decoder-n-heads 6 \
  --batch-size 16 --limit 7000 --n-steps 1000 \
  --lr 1e-4 --weight-decay 1e-4 --grad-clip 1.0 \
  --ablation full --train-log-every-steps 50 \
  --tokenizer-path /workspace/tksCAS/stage6_v6_artifacts/tokenizer.json \
  --english-bpe-path /workspace/tksCAS/stage6_v6_artifacts/english_bpe.json \
  --sample-canary-at 250,500,750,1000 --sample-canary-post-training \
  --save-checkpoints-at 250,500,750,1000 --save-final-checkpoint \
  --canary-max-new-tokens 128 --seed 1729 \
  > ${OUT}.log 2>&1 &
```

Expected: ~50 min wall-clock, ~$0.42 spot.

### Pre-launch sync (files updated since v7.1b)

```
scp -P 22026 -i ~/.ssh/id_ed25519 \
  noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py \
  noetic-compass-scaffold/noetic-compass/cas-native/training/simplex_checkpoint.py \
  root@<pod-ip>:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/

scp -P 22026 -i ~/.ssh/id_ed25519 \
  noetic-compass-scaffold/noetic-compass/cas-native/evaluation/teacher_forced_canary.py \
  noetic-compass-scaffold/noetic-compass/cas-native/evaluation/decode_ablations.py \
  noetic-compass-scaffold/noetic-compass/cas-native/evaluation/sample_decoder.py \
  root@<pod-ip>:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/evaluation/
```

## Post-replay analyses (against `ckpt_final.pt`)

These run **after** the training replay finishes. They reuse the saved checkpoint — no new training. Each takes ~30-90 sec on A6000.

### Analysis A — Teacher-forced canary eval

```python
# On pod:
python -c "
import torch
from cas_native.training.simplex_checkpoint import load_checkpoint
from cas_native.training.train_simplex_mvp import (
    build_simplex_mvp_model, SimplexTrainConfig, DEFAULT_LOSS_WEIGHTS,
)
from cas_native.training.tokenizer import HybridCASTokenizer
from cas_native.training.datasets.simplex_collator import SimplexCollator
from cas_native.evaluation.stage7_canary_pack import canary_pack
from cas_native.evaluation.teacher_forced_canary import teacher_forced_canary_pack

tok = HybridCASTokenizer.load('/workspace/tksCAS/stage6_v6_artifacts/tokenizer.json')
tok = tok.with_english_bpe('/workspace/tksCAS/stage6_v6_artifacts/english_bpe.json')

cfg = SimplexTrainConfig(
    data_path='', output_dir='',
    d_model=384, encoder_n_layers=4, decoder_n_layers=6,
    encoder_n_heads=6, decoder_n_heads=6, batch_size=1,
)
cfg.loss_weights = dict(DEFAULT_LOSS_WEIGHTS)
model = build_simplex_mvp_model(cfg, vocab_size=int(tok.vocab_size),
                                vocab_size_english=int(tok.vocab_size))
load_checkpoint('${OUT}/ckpt_final.pt', model=model, map_location='cuda:0')
model = model.to('cuda:0')

collator = SimplexCollator(tok, enable_simplex_aux=True)
import json
result = teacher_forced_canary_pack(model, canary_pack(), collator, tok,
                                     device=torch.device('cuda:0'))
with open('${OUT}/tf_canary_report.json', 'w') as f:
    json.dump(result, f, indent=2)
print('TF summary:', json.dumps(result['summary'], indent=2))
"
```

### Analysis B — Per-token greedy trace

```python
# Reuse the same loaded model. Run greedy_decode(..., trace=True) on the
# 2 rpm_chain canary records (where v7.1b's loops were worst).
python -c "
... # (mirrors Analysis A's loader)
from cas_native.evaluation.sample_decoder import greedy_decode
import json

records = [r for r in canary_pack()
           if r['v1mix_grammar_category_or_error_class'] == 'rpm_chain']
traces = []
for rec in records:
    result = greedy_decode(model, rec, collator, tok,
                            device=torch.device('cuda:0'),
                            max_new_tokens=64, trace=True, topk=5)
    traces.append({'id': rec['id'], **result})
with open('${OUT}/per_token_trace.json', 'w') as f:
    json.dump(traces, f, indent=2)
print(f'traced {len(traces)} records')
"
```

### Analysis C — Decode ablations

```python
python -c "
... # (mirrors Analysis A's loader)
from cas_native.evaluation.decode_ablations import run_decode_ablations_pack
import json

result = run_decode_ablations_pack(model, canary_pack(), collator, tok,
                                    device=torch.device('cuda:0'),
                                    max_new_tokens=128)
with open('${OUT}/decode_ablations.json', 'w') as f:
    json.dump(result, f, indent=2)
print('Pack verdicts by mode:')
for mode, v in result['summary_by_mode'].items():
    print(f\"  {mode}: {v['verdict']} ({v['by_verdict']})\")
"
```

## Decision standard (per user 2026-05-11, durably locked here)

| Diagnostic outcome | Reading | Next action |
|---|---|---|
| **TF clean + greedy bad** | Exposure-bias / free-decode failure | **Do NOT run loss-weight ablations first.** Scheduled sampling / teacher-forcing mix-in is the right Stage 7-bis lever. |
| **`copy_disabled` cleaner than `full`** | Copy path is destabilizing decode | Then LM+FR+slot is the right ablation. Stage 7-bis becomes loss-weight, not decode-strategy. |
| **`lm_only` bad** | Decoder/LM head architecture problem | **Pause for architectural review.** Greedy decode + label smoothing + temperature won't save it. |
| **Slot always CONNECTIVE** | Slot gate not doing its job | Inspect slot supervision / weight. Phrase-bias path is unreachable as long as slot_type collapses to id 0. |
| **All modes bad but severity improves with steps** | Only then discuss longer training. Samples remain primary gate. | Train longer. NOT a license to ignore samples. |

## What v0-rc1 stays as

Per user 2026-05-11: **v0-rc1 remains canonical.** None of the v7/v7.1/v7.1b/diagnostic replay artifacts get promoted to production. The post-tie ~55M simplex model is a research target; the deployed model continues to be the archived v0-rc1 checkpoint at `D:/tksCAS-archive/v0_rc1/v1c_VALIDTOK_5ep/`.

The diagnostic replay is research-track only.

## Cost projection

| Step | Wall-clock | Spot cost |
|---|---|---|
| Pre-launch sync | ~30 sec | $0 |
| 1000-step training replay | ~50 min | ~$0.42 |
| Analysis A (TF eval) | ~30 sec | ~$0.005 |
| Analysis B (trace, 2 records) | ~10 sec | ~$0.002 |
| Analysis C (ablations, 4 modes × 11 records) | ~3 min | ~$0.03 |
| **Total** | **~54 min** | **~$0.46** |

Cumulative since simplex MVP started: ~$1.20 spot. $60 budget has ~$58.80 headroom.

## Pre-launch checklist

- [ ] Pod up and reachable
- [ ] `/workspace/tksCAS/stage6_v6_artifacts/tokenizer.json` + `english_bpe.json` present (from v6+)
- [ ] `/workspace/tksCAS/cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl` present
- [ ] Latest commits synced (run the scp block above)
- [ ] User explicit approval to launch (not auto-greenlit by this doc)

## What this doc does NOT do

- Does NOT launch the pod run
- Does NOT modify v0-rc1
- Does NOT pre-decide Stage 7-bis or architectural review
- Does NOT promise the diagnostic will explain the failure (it might surface a 6th hypothesis we haven't named)

## Companion files

- `noetic-compass-scaffold/noetic-compass/cas-native/training/simplex_checkpoint.py` (piece 1)
- `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/teacher_forced_canary.py` (piece 2)
- `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/sample_decoder.py` (piece 3 — trace mode)
- `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/decode_ablations.py` (piece 4)
- `docs/working/simplex_mvp_stage7_v7_1b_postmortem_2026_05_11.md` (the why)
- `docs/working/simplex_mvp_stage7_v7_1b_canary_report_2026_05_11.json` (the empirical baseline this replay compares against)
