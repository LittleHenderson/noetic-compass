# Candidate E Checkpoint Archive Registry

This file is the canonical pointer to locally-archived trained checkpoints from the Candidate E line. The binary checkpoints themselves are NOT committed to git (664 MB each); they live on the local archive drive. This registry records: archive location, sha256 (so anyone can verify their copy is bit-identical), pod source path, training lineage, and a one-line "what is this" summary.

If you don't see your checkpoint here, it isn't backed up — assume the pod copy is the only copy.

## How to use this registry

1. Find the entry for the checkpoint you need by name.
2. Verify your local copy: `sha256sum <archive path>` matches the listed hash.
3. If you don't have a local copy, ask whoever owns the archive drive (Wakil).
4. Loading: see `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/evaluate_candidate_e_stage2.py` for the canonical load path (`build_simplex_mvp_model` + `model.load_state_dict`).

## Active entry

### Stage 3 code commit (PIN)

The trained Stage 3 checkpoint was produced by the code at commit `e9a0b76161b63e647a6c88633ffcf1f692e06032` ("candidate-e: patch Codex re-audit blockers on scheduled sampling"). This is the last code change before the Stage 3 training launch at 2026-05-13T04:38:25Z. To check out the exact code that matches the checkpoint: `git checkout e9a0b76`. The trainer + scheduled_sampling MD5s verified at deploy time (`4543d11679eb17770af48bf78d8cfa78` and `aef4666f30d7c9b3c4d9bc2c86b247a4` respectively) correspond to this commit.

Code files load-bearing for "load + run the Stage 3 model" — all present in repo at this commit:

- `noetic-compass-scaffold/noetic-compass/cas-native/model/typed_fiber_decoder.py`
- `noetic-compass-scaffold/noetic-compass/cas-native/model/simplex_encoder.py`
- `noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py` (contains `build_simplex_mvp_model`)
- `noetic-compass-scaffold/noetic-compass/cas-native/training/scheduled_sampling.py`
- `noetic-compass-scaffold/noetic-compass/cas-native/training/simplex_checkpoint.py`
- `noetic-compass-scaffold/noetic-compass/cas-native/training/datasets/simplex_collator.py`
- `noetic-compass-scaffold/noetic-compass/cas-native/training/tokenizer.py` (HybridCASTokenizer)
- `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/evaluate_candidate_e_stage2.py` (canonical load + decode reference)
- `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/sample_decoder.py`

### `stage_e3_20260513T043823Z/ckpt_final.pt` — Stage 3 trained checkpoint (PRIMARY)

The current "good model" — passes both load-bearing gates on dev and held-out packs (free-decode identifier_recovery 0.7778 dev / 0.6439 held-out, swap cross_emission 0 across both). Per Codex audit `707249b`: Stage 3 is done for this loop; no further training authorized. This checkpoint is what chat REPL + Mode 7 integration loads.

| field | value |
|---|---|
| Local archive | `D:\tksCAS-archive\stage_e3_20260513T043823Z\ckpt_final.pt` |
| Pod source | `/workspace/tksCAS/stage_e3_20260513T043823Z/ckpt_final.pt` |
| Size | 664,482,404 bytes (~664 MB) |
| sha256 | `5ac364e78419ec8591d25120ce9314f87d2c816467fcf9875802d3d831903a88` |
| Saved at | 2026-05-13T05:40:35Z |
| Schema version | `simplex_mvp_ckpt.v1` |
| torch version | 2.11.0+cpu (training was on cuda:0; cpu in the manifest is the torch build string) |

#### Training config (verbatim from manifest)

| param | value |
|---|---|
| ablation | `e3` |
| n_steps | 1000 |
| batch_size | 16 |
| lr | 1e-4 |
| weight_decay | 1e-4 |
| grad_clip | 1.0 |
| seed | 1729 |
| d_model | 384 |
| encoder_n_layers / n_heads | 4 / 6 |
| decoder_n_layers / n_heads | 6 / 6 |
| max_cas_prefix_len | 192 |
| scheduled_sampling_schedule | `linear:0.0-0.5:1-1000` |
| decoder_arch | transformer |

#### Loss weights (inherited from e2c verbatim — no new losses in e3)

| component | weight |
|---|---:|
| lm | 1.0 |
| fr | 1.0 |
| slot_type | 1.0 |
| copy | 0.5 |
| phrase_bias_aux | 0.1 |
| span | 1.0 |
| contrastive_margin | 0.5 |
| coverage | 0.1 |
| start_anchor | 2.0 |
| anchor_contrastive | 1.0 |

#### Lineage (warm-start chain)

```
b2 (audited) → e2a (warmup) → e2b (span / contrastive / coverage)
            → e2c (start_anchor / anchor_contrastive)
            → stage_e2c_cont_20260513T002539Z/ckpt_final.pt  (E2c continuation, 1000 more steps)
            → stage_e3_20260513T043823Z/ckpt_final.pt        (THIS ENTRY: Stage 3 scheduled-sampling)
```

`load_model_from` for this run: `/workspace/tksCAS/stage_e2c_cont_20260513T002539Z/ckpt_final.pt` (E2c continuation).

#### Required runtime artifacts to load this checkpoint

These MUST be present at runtime; they are not bundled in the checkpoint binary. Both are now backed up locally (per `decisions.md` 2026-05-13T07:25Z); Phase 1 loader should verify by sha256 and fail clearly if missing.

| artifact | local archive | pod path | sha256 |
|---|---|---|---|
| tokenizer | `D:\tksCAS-archive\stage6_v6_artifacts\tokenizer.json` | `/workspace/tksCAS/stage6_v6_artifacts/tokenizer.json` | `9c544425c9c08140070b2f3929adef864bbfafb0c00c1d687f2d6b98e0589b9b` |
| english_bpe | `D:\tksCAS-archive\stage6_v6_artifacts\english_bpe.json` | `/workspace/tksCAS/stage6_v6_artifacts/english_bpe.json` | `ac4d12a6d26cc1194ea31fee8cdc07d52a0a759964810956b13cafea08a06889` |

Hashes verified bit-for-bit pod ↔ local on backup (2026-05-13T07:30Z) AND match the values recorded by the trainer manifest at training time (the `tokenizer_info.*_sha256` fields in `ckpt_final.pt.manifest.json`). Three independent confirmations of the same hash means we can trust these files are the tokenizer + BPE the Stage 3 model was actually trained with.

#### Companion artifacts in the same archive directory

These are NOT load-bearing for inference but ARE load-bearing for reproducibility / forensic analysis. They are tiny — kept alongside the checkpoint binary.

| file | sha256 | what it is |
|---|---|---|
| `ckpt_final.pt.manifest.json` | `28c13127e919097ee3337eab13bcb929c6b104ee5afecd6f7af64e80d05a9dd6` | Schema metadata — config, lineage, tokenizer hashes |
| `trainer_manifest.json` | `346223ff286b2c245ec29ba61f62b88c16acdb57a0863cd67ca8110bb7fcc849` | Training-run summary written at trainer init |
| `trainer_log.jsonl` | `5be168ad9c24c8dfe27f1fa394dd0800633e0a03ba9221f73c86073d5798e196` | Per-step `train_progress` events (telemetry for the full 1000-step run) |
| `smoke_report.json` | `83893bc5810f9eb386afa2dc6c44daa37fb88286074381fbd88df0b3533680e2` | Trainer's built-in end-of-run gate report (verdict + loss trajectory) |

#### Verification post-archive (2026-05-13T07:10Z)

scp completed; all 5 files transferred; sha256 verified pod-side and local-side independently — all 5 hashes match bit-for-bit. The local archive is a faithful copy of the pod source.

#### What this checkpoint can / cannot do

Can:
- Free-decode CAS identifier copying at ~64% identifier_recovery on truly held-out RPM records, with zero cross-pair body emission (no leakage).
- Teacher-forced CAS reproduction at ~72% identifier_recovery (held-out) / ~89% per-token accuracy.
- Slot-type classification (CONNECTIVE / STAGE_VAR / OMEGA / NOETIC_PHRASE / etc.) per output position with high accuracy.

Cannot (current state, may change with later phases):
- Free-decode strong-pass (≥0.70 identifier_recovery) on held-out data — dev was 0.78, held-out fell to 0.64. The dev → held-out drop is asymmetric: TF only fell 1.7pp; free-decode fell 13.4pp. The copy-pointer module generalizes; the keep-copying-while-generating behavior is somewhat dev-tuned.
- Multi-utterance dialogue state tracking (this is a copy-grounded RPM-task model, not a chatbot).
- Free-form English chat input — the encoder expects a CAS prefix. The chat REPL integration plan (`docs/working/chat_repl_stage3_integration_plan_2026_05_13.md`) is where the NL→CAS-prefix bridge gets designed.

## Warm-start lineage archive

### `stage_e2c_cont_20260513T002539Z/ckpt_final.pt` — E2c continuation (Stage 3 warm-start source)

The checkpoint Stage 3 trained from. `--load-model-from` for the Stage 3 run pointed at this file on pod. Required for "retrain Stage 3 from the same starting point" reproducibility. NOT load-bearing for "run the trained Stage 3 model" — for inference, only the Stage 3 entry above matters.

| field | value |
|---|---|
| Local archive | `D:\tksCAS-archive\stage_e2c_cont_20260513T002539Z\ckpt_final.pt` |
| Pod source | `/workspace/tksCAS/stage_e2c_cont_20260513T002539Z/ckpt_final.pt` |
| Size | 664,482,084 bytes (~664 MB) |
| sha256 | `86bd7d6c6663c90abe7fa7b3a34bb59e871e96893b09f73f41deb8c8dc0adfc6` |
| Saved at | 2026-05-13T01:20Z |
| Schema version | `simplex_mvp_ckpt.v1` |

#### Training config (verbatim from manifest)

| param | value |
|---|---|
| ablation | `e2c` |
| n_steps | 1000 (continuation after first E2c run at 1000 steps) |
| batch_size | 16 |
| lr | 1e-4 |
| max_cas_prefix_len | 192 |
| seed | 1729 |
| `load_model_from` | `/workspace/tksCAS/stage_e2c_anchor_20260512T192622Z/ckpt_step_1000.pt` (E2c first run, ckpt_step_1000.pt; that earlier checkpoint is NOT backed up locally — Tier 4 / pod-only) |

#### Companion artifacts in the same archive directory

| file | sha256 |
|---|---|
| `ckpt_final.pt.manifest.json` | `01bf2ac6a4a16af49784270009f7ae6fd91adeee7ea0c24e6c5d59fdd79b42f2` |
| `trainer_manifest.json` | `fabe42f2976dee245ac1e2f2ca3f935eb5e5ada5ac9c99072172488ed3f892ba` |
| `trainer_log.jsonl` | `34fb4eaf42eab2898cea1aacaf26996c38cfc8e078939eb65d6231329102389f` |
| `smoke_report.json` | `72a65a7b27ec471ed95b0db11122a79840cbbdeb1bb59f01684a6c9bfdd9d126` |

#### Verification post-archive (2026-05-13T07:50Z)

scp completed; all 5 files transferred; sha256 verified pod-side and local-side independently — all 5 hashes match bit-for-bit. The local archive is a faithful copy of the pod source.

#### What this checkpoint enables

If Stage 3 needs to be retrained exactly (same weights to within RNG noise):

1. Check out the Stage 3 code commit: `git checkout e9a0b76161b63e647a6c88633ffcf1f692e06032`.
2. Load the warm-start ckpt from `D:\tksCAS-archive\stage_e2c_cont_20260513T002539Z\ckpt_final.pt` via `--load-model-from`.
3. Run training with the recorded hparams (verbatim from the Stage 3 manifest: `--ablation e3 --scheduled-sampling-schedule "linear:0.0-0.5:1-1000" --n-steps 1000 --batch-size 16 --lr 1e-4 --weight-decay 1e-4 --grad-clip 1.0 --max-cas-prefix-len 192 --seed 1729`).
4. Training data: `cas-synthetic/data/path_d/rpm_copy_grounding_v2_train.jsonl` (already in repo, no separate archive copy).

## Tier 4 / forensic-replay archives (pod-only)

NOT backed up locally. These are only needed if we want to re-derive Stage 3 from earlier in the warm-start chain. Per Codex audit 2026-05-13: "No full Tier 4 unless forensic replay."

- E2a checkpoint
- E2b checkpoint
- E2c first-run checkpoint at `/workspace/tksCAS/stage_e2c_anchor_20260512T192622Z/`
- E2c continuation intermediate checkpoints (ckpt_step_500.pt, ckpt_step_1000.pt — note: ckpt_step_1000.pt is content-identical to ckpt_final.pt, just a different filename)
- B2 checkpoint and earlier lineage

If the pod dies before Phase 1 integration code lands, these are lost. We can still rebuild Stage 3 from the E2c-continuation backup (Tier 3) without them.
