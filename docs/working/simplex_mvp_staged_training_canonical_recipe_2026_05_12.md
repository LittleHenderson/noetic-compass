# Simplex MVP — Canonical Staged Training Recipe (B1 → B2 → B3)

**Date locked:** 2026-05-12
**Status:** CANONICAL training pipeline for the v1 CAS-Native simplex model. **Broader eval still required before declaring production-ready.** v0-rc1 remains the deployed model.

## What this document is

The architectural review (A → C → B) ended with Candidate B validated end-to-end. The B1 → B2 → B3 staged training schedule is now the **canonical training pipeline** for any simplex MVP retraining. Any future training run on this architecture should use this exact recipe unless explicitly testing a deviation.

## What this document is NOT

- It is not a promotion of B3 to production. v0-rc1 stays canonical until broader eval passes (24-pack + rpm-heavy identifier suite + non-rpm leakage negatives + fractal suite).
- It is not a tuning playground. Per the anti-tuning rule, deviations from these hparams require an explicit experiment with locked kill/validate criteria, not "let me try a smaller lr."

## The recipe

### Stage B1 — LM + FR only

**Goal:** establish that the LM head produces non-trivial non-looping prose without joint pressure from slot/copy.

**Loss weights** (`--ablation b1`):
- `lm = 1.0`
- `fr = 1.0`
- `slot_type = 0.0`
- `copy = 0.0`
- `phrase_bias_aux = 0.0`

**Launch command:**
```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT=/workspace/tksCAS/stage7_candidate_b1_lmfr_${TS}

nohup python /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py \
  --data-path /workspace/tksCAS/cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl \
  --output-dir ${OUT} \
  --device cuda:0 \
  --d-model 384 --encoder-n-layers 4 --decoder-n-layers 6 \
  --encoder-n-heads 6 --decoder-n-heads 6 \
  --batch-size 16 --limit 7000 --n-steps 1000 \
  --lr 1e-4 --weight-decay 1e-4 --grad-clip 1.0 \
  --ablation b1 --train-log-every-steps 50 \
  --tokenizer-path /workspace/tksCAS/stage6_v6_artifacts/tokenizer.json \
  --english-bpe-path /workspace/tksCAS/stage6_v6_artifacts/english_bpe.json \
  --sample-canary-at 250,500,750,1000 --sample-canary-post-training \
  --save-checkpoints-at 250,500,750,1000 --save-final-checkpoint \
  --canary-max-new-tokens 128 --seed 1729 \
  > ${OUT}.log 2>&1 &
```

**Locked B1 gate:** KILL if any rpm_chain canary shows phrase_loop, n_tokens<30, text_len<30, or hit_eos with n_tokens<50.

**B1 result on first canonical run (2026-05-11):** Qualified pass. mean_severity 3.64 → 1.23 (step 750) → 1.82 (post-training). rpm_chain_002 flagged `phrase_loop("a", count=3)` — a function-word stutter inside coherent prose, not a Candidate-C-class attractor loop. Gate exception recorded in design doc.

### Stage B2 — + slot loss (warm-start from B1's ckpt_final.pt)

**Goal:** the slot gate develops on top of B1's stable LM head and sustains STAGE_VAR on rpm_chain inputs without leaking onto non-rpm inputs.

**Loss weights** (`--ablation b2`):
- `lm = 1.0`
- `fr = 1.0`
- `slot_type = 1.0`
- `copy = 0.0`
- `phrase_bias_aux = 0.0`

**Launch additions vs B1:**
```bash
  --ablation b2 \
  --load-model-from /workspace/tksCAS/stage7_candidate_b1_lmfr_<B1_TS>/ckpt_final.pt
```

Out dir prefix: `stage7_candidate_b2_lmfr_slot_${TS}`.

**Locked B2 gate:** validate if at least 1/2 rpm_chain shows STAGE_VAR ≥5 consecutive positions AND neither rpm_chain has CONNECTIVE >90% AND zero non-rpm canaries show STAGE_VAR ≥3 consecutive positions. B1 regression guards remain in force (catastrophic loop / triviality / mean_severity > 1.82).

**B2 result on first canonical run (2026-05-11):** Full strict validate. rpm_chain STAGE_VAR runs of 10 and 9 positions, CONNECTIVE 50% / 55%, zero leakage, mean_severity 0.05.

### Stage B3 — + copy + hard typed emission (warm-start from B2's ckpt_final.pt)

**Goal:** hard typed-fiber routing reconstructs canonical identifiers on rpm_chain inputs without leaking onto non-rpm.

**Loss weights** (`--ablation b3`, equivalent to `full`):
- `lm = 1.0`
- `fr = 1.0`
- `slot_type = 1.0`
- `copy = 0.5`
- `phrase_bias_aux = 0.1`

**Launch additions vs B2:**
```bash
  --ablation b3 \
  --load-model-from /workspace/tksCAS/stage7_candidate_b2_lmfr_slot_<B2_TS>/ckpt_final.pt \
  --hard-typed-emission --copy-confidence-threshold 0.5
```

Out dir prefix: `stage7_candidate_b3_full_hardemit_${TS}`.

**Postmortem must use the same hard-emission flags** so `decode_ablations.json` includes `hard_full` mode side-by-side with the four baseline modes:

```bash
python /workspace/.../evaluation/run_v7_postmortem_analyses.py \
  --checkpoint-path ${OUT}/ckpt_final.pt \
  --tokenizer-path /workspace/tksCAS/stage6_v6_artifacts/tokenizer.json \
  --english-bpe-path /workspace/tksCAS/stage6_v6_artifacts/english_bpe.json \
  --output-dir ${OUT} \
  --device cuda:0 \
  --canary-max-new-tokens 128 \
  --hard-typed-emission --copy-confidence-threshold 0.5
```

**Locked B3 gate:** five clauses, see `simplex_mvp_candidate_b_design_2026_05_11.md` for full text. Summary: both rpm_chain copy ≥10, non-rpm copy=0, TF `canonical_stage_vars_in_argmax ≥ 1`, hard_full beats full (with Gate 4 measurement caveat that TF recovery is the rigorous proxy), pack kill ≤ 3/11.

**B3 result on first canonical run (2026-05-12):** 4 strict pass + Gate 4 literal-tie/spirit-pass. TF canonical_recovery_rate 0.0 → 0.5. Hard routing reconstructs `stageA0_4_0049` and `stageD4_4_0049` exact-match on rpm_chain_002. Zero non-rpm leakage. Pack 11/11 clean.

## Pre-launch protocol (mandatory before every stage)

MD5-verify required files on pod match local. Required files by stage:

| File | B1 | B2 | B3 |
|---|---|---|---|
| `cas-native/training/train_simplex_mvp.py` | ✓ | ✓ | ✓ |
| `cas-native/evaluation/sample_decoder.py` (hard-emission STAGE_VAR scope + type-match) | | | ✓ |
| `cas-native/evaluation/decode_ablations.py` (`hard_full` mode) | | | ✓ |
| `cas-native/evaluation/run_v7_postmortem_analyses.py` (threads hard-emission to ablations) | | | ✓ |

```bash
# Local MD5s (LF-normalized for cross-platform parity)
python -c "
import hashlib
for f in [
  'noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py',
  'noetic-compass-scaffold/noetic-compass/cas-native/evaluation/sample_decoder.py',
  'noetic-compass-scaffold/noetic-compass/cas-native/evaluation/decode_ablations.py',
  'noetic-compass-scaffold/noetic-compass/cas-native/evaluation/run_v7_postmortem_analyses.py',
]:
  data = open(f, 'rb').read().replace(b'\r\n', b'\n')
  print(hashlib.md5(data).hexdigest(), f.split('/')[-1])
"

# Pod MD5s
ssh -p 22026 -i ~/.ssh/id_ed25519 root@194.68.245.88 'cd /workspace/tksCAS/noetic-compass-scaffold/noetic-compass && md5sum \
  cas-native/training/train_simplex_mvp.py \
  cas-native/evaluation/sample_decoder.py \
  cas-native/evaluation/decode_ablations.py \
  cas-native/evaluation/run_v7_postmortem_analyses.py'
```

If any MD5 differs, scp the local file over.

## Auto-postmortem watcher (B3 only)

B3 requires a watcher that fires `run_v7_postmortem_analyses.py` after training writes `ckpt_final.pt`. The watcher pattern used 2026-05-12:

```bash
cat > /workspace/tksCAS/stage7_candidate_b3_postmortem_watcher.sh <<'EOF'
#!/bin/bash
set -u
OUT=<the B3 OUT dir>
WATCHER_LOG=${OUT}.watcher.log
echo "[watcher] start $(date -u +%FT%TZ) waiting for ${OUT}/ckpt_final.pt" > ${WATCHER_LOG}
SECONDS=0
while [ ! -f "${OUT}/ckpt_final.pt" ]; do
  sleep 30
  if [ $SECONDS -gt 7200 ]; then echo "[watcher] timeout 2h" >> ${WATCHER_LOG}; exit 1; fi
done
echo "[watcher] checkpoint found at ${SECONDS}s" >> ${WATCHER_LOG}
cd /workspace/tksCAS
python /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/evaluation/run_v7_postmortem_analyses.py \
  --checkpoint-path ${OUT}/ckpt_final.pt \
  --tokenizer-path /workspace/tksCAS/stage6_v6_artifacts/tokenizer.json \
  --english-bpe-path /workspace/tksCAS/stage6_v6_artifacts/english_bpe.json \
  --output-dir ${OUT} \
  --device cuda:0 \
  --canary-max-new-tokens 128 \
  --hard-typed-emission --copy-confidence-threshold 0.5 \
  >> ${WATCHER_LOG} 2>&1
echo "[watcher] postmortem done at ${SECONDS}s" >> ${WATCHER_LOG}
EOF
chmod +x /workspace/tksCAS/stage7_candidate_b3_postmortem_watcher.sh
nohup /workspace/tksCAS/stage7_candidate_b3_postmortem_watcher.sh > /dev/null 2>&1 & disown
```

## Anti-tuning discipline (in force across all three stages)

- **Do NOT vary lr, batch_size, weight_decay, grad_clip, or seed across stages without an explicit experiment.** The baseline values (1e-4 / 16 / 1e-4 / 1.0 / 1729) are the ones that produced this validation; deviation requires a new locked kill/validate criterion.
- **Do NOT extend a stage past 1000 steps to "try to make it pass" if its gate fails.** Gate failure means stop and surface, not retune.
- **Do NOT auto-chain B1 → B2 → B3 on pod.** Each stage launches separately after its kill criterion is applied by a human. The audit gates are the discipline.
- **MD5-verify required files before every stage launch.** Skipping this risks running stale code (the C audit caught hard-emission flags missing from postmortem, which would have invalidated the C verdict if not caught).

## Cost projection (per full B1→B2→B3 cycle)

| Stage | Wall-clock | Spot |
|---|---|---|
| B1 + canary | ~50 min | ~$0.44 |
| B2 + canary | ~50 min | ~$0.44 |
| B3 + canary + postmortem | ~55 min | ~$0.49 |
| **B total** | **~2.5 hr** | **~$1.37** |

## Companion files

- `docs/working/simplex_mvp_candidate_b3_findings_2026_05_12.md` — the empirical validation that justifies this recipe.
- `docs/working/simplex_mvp_candidate_b_design_2026_05_11.md` — the original design + audit fixes + gate exception records.
- `docs/working/candidate_b1/`, `docs/working/candidate_b3/` — artifact archives.
- `docs/future/cas_self_training_recursive_gated_successor_2026_05_12.md` — long-horizon target that uses this recipe to train successors.
