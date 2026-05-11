# v1e Phase C — Aux Heads Design Doc

**Date:** 2026-05-11
**Status:** **Awaiting user sign-off before implementation / GPU spend.**
Task #140 (design) blocks Task #141 (impl + training + eval).
**Triggering decision:** v1e Phase 2 verdict 2026-05-11 — user
rejected first-n metric redefinition, chose architecture-side fix as
the final v1e experiment before pivoting simplex.

## 1. Decision context

Per `project_v1e_phase2_decision_2026_05_11.md`:

- β2 (Task #139) showed decode-side levers are saturated. EOS bias
  produces fragments at high strength; length cap chops mid-clause.
- The v0 model emits noetic indicators DENSELY in connective tissue.
  Decode-time levers cannot separate them from sentence-closing
  prose without unacceptable cost.
- C aux heads target the training side: teach the encoder
  cardinality / per-position Noetic / stop-after-N / cluster
  membership directly, so the model's prose distribution itself
  bounds the fractal output.
- **Kill-switch (user verbatim):** "If C regresses the 24-pack or
  fails fractals, stop v1e and pivot simplex."

## 2. Architecture additions

Four heads attach to the encoder's pooled hidden state via a new
`attach_aux_heads()` method on `CASNativeModel`, mirroring the
existing `attach_nl_gen_head()` pattern. New module:
`cas_native/model/aux_heads.py`.

### 2.1 Cardinality head (H_card)

**Purpose:** predict K = number of expected slots from encoder pool.
Used as training signal AND as inference-time soft prior on
expected output length / when to stop.

**Architecture:**
```
pooled_hidden_state (B, d_model=512)
  → Linear(512, 128) → GELU
  → Linear(128, K_max + 1 = 17)
  → softmax over [0, K_max] classes
```

**Supervision:** per-record `K = len(parse_fractal(source).k_values)`
when source is a fractal; otherwise `K = 0`. Sample-weight =
`task_type == "cas_to_english" AND parse_fractal != None`. Loss:
cross-entropy. Other rows ignored via sample weight.

**Param count:** 512×128 + 128 + 128×17 + 17 = ~67k params.

### 2.2 Per-position Noetic head (H_pos)

**Purpose:** train the encoder pool to KNOW the ordered Noetic
sequence at each position. This is the key inductive bias —
without it the encoder's pool is shaped only by autoregressive LM
loss, which has no signal about source ordering.

**Architecture:**
```
pooled_hidden_state (B, d_model=512)
  → Linear(512, 160 = K_max × 10)
  → reshape (B, K_max=16, 10)
  → softmax over 10 Noetic classes per position
```

**Supervision:** `target[b, i, :] = one_hot(k_values[i])` for
`i < K_actual`; `ignore_index` for `i >= K_actual`. Per-position
cross-entropy.

**Param count:** 512×160 + 160 = ~82k params.

### 2.3 Stop/complete head (H_stop) — DIRECTLY targets β2 failure mode

**Purpose:** predict the EOS-ready position from the decoder. This
is the head most directly aimed at the β2 structural finding
("model doesn't know to stop after N slots"). When the decoder is
PAST the final slot, this head's logit feeds an inference-time EOS
bias that's CONDITIONAL on slot state, not a blunt always-on bias.

**Architecture:**
```
decoder_hidden (B, L, d_model=512)
  → Linear(512, 64) → GELU
  → Linear(64, 2)  # [continue, stop]
  → softmax per position
```

Decoder hidden state at each position is already available in the
NLGenerationHead's forward; we hook in there and apply this small
classifier.

**Supervision:** for each training row, derive a binary target
sequence `stop_target[b, t]` where:
- `0` ("continue") for positions before the last expected-slot
  has emitted its phrase
- `1` ("stop") for positions AT and AFTER the last expected-slot
  commits

The "last slot committed" position is computed offline via the
same `extract_noetic_sequence` walk used in `fractal_repair`:
align expected K with found indicators in the reply_text, and
mark "stop" from the position-AFTER the last alignment onward.

For non-fractal records (no `parse_fractal` match), use the
sequence-end position (reply_text length + 1) as the unique
"stop" position. This is consistent: stop-after-content.

Loss: per-position binary cross-entropy with `loss_mask` to
exclude PAD positions.

**Inference use:** at decode time, when in the
post-final-slot region (state.pos >= n), use H_stop's "stop"
probability as a DYNAMIC EOS bias. High stop probability → high
EOS bias. This replaces the blunt static `fractal_decoder_eos_bias`.

**Param count:** 512×64 + 64 + 64×2 + 2 = ~33k params.

### 2.4 Cluster membership head (H_cluster)

**Purpose:** predict which Noetics belong in which cluster for
meta-logic relations (PartitionOf / CoverOf / Product).
Addresses records 16/17/18 in the 24-pack — orthogonal to the
fractal-loop problem but covered by the same fine-tune at trivial
extra cost.

**Architecture:**
```
pooled_hidden_state (B, d_model=512)
  → Linear(512, 60 = C_max × 10)  # C_max=6 clusters max
  → reshape (B, C_max=6, 10)
  → sigmoid (multi-label per cluster)
```

**Supervision:** for meta_logic rows, `parse_meta_logic(source)`
yields per-cluster `noetics: set[int]`. Convert to multi-hot
(B, C_max, 10). For non-meta-logic rows, all-zero mask via sample
weight.

**Param count:** 512×60 + 60 = ~31k params.

### 2.5 Aux heads total

~213k new params. Encoder backbone (~50M params) and NL gen head
(~20M params) remain unchanged. Param count delta is < 0.4%.

## 3. Supervision pipeline

Extend `NativeNLCollator.__call__` to produce auxiliary labels at
batch time. NO changes to the JSONL training-data format — labels
are derived per-record from the existing `cas_expression` field.

New batch keys (added to existing collator output):

```
aux_K_target            : (B,)        long, K count or -100 (ignore)
aux_K_sample_weight     : (B,)        float, 1.0 if fractal else 0.0
aux_pos_targets         : (B, K_max)  long, k_values[i] or -100
aux_pos_sample_weight   : (B,)        float, 1.0 if fractal else 0.0
aux_stop_targets        : (B, L_dec)  long, 0/1 with -100 PAD ignore
aux_stop_sample_weight  : (B, L_dec)  float, 1.0 where stop_target valid
aux_cluster_mh          : (B, C_max, 10) float, multi-hot
aux_cluster_mask        : (B, C_max)  bool, cluster slot valid
aux_cluster_sample_wt   : (B,)        float, 1.0 if meta_logic else 0.0
```

Stop targets computed via:
1. `parse_fractal(source_cas)` → expected K values
2. `extract_noetic_sequence(reply_text)` → found indicator positions
3. Greedy alignment expected→found (longest-prefix-match)
4. Position-after-last-aligned-indicator = stop boundary
5. `aux_stop_targets[b, :stop_pos] = 0; aux_stop_targets[b, stop_pos:reply_len+1] = 1`

For non-fractal rows: stop_target = `[0]*reply_len + [1]` (stop at EOS).

All reusing existing `cas_native/inference/fractal_repair.py` parsers.
NO new parser code needed for the supervision pipeline.

## 4. Loss formulation

Total loss:
```
L_total = β_lm·L_LM + α_card·L_card + α_pos·L_pos + α_stop·L_stop + α_cluster·L_cluster
```

Per Wave-1 C-architect spec + audit `feedback_cas_native_underfit_over_overfit_short_epochs`:

- `β_lm = 1.0` (existing trainer convention)
- `α_card = 0.10`
- `α_pos = 0.20` (highest-leverage aux head)
- `α_stop = 0.15`
- `α_cluster = 0.10`

**Curriculum: aux weights RAMP DOWN, not up.** First 30% of steps
use `2×` the listed α; linearly decay to base α by 60%; hold to end.
Rationale: force the encoder to commit to structural representation
early, then let LM loss dominate as the head's representations
stabilize.

**Loss-interference monitor:** training script emits per-step
`loss_lm`, `loss_card`, `loss_pos`, `loss_stop`, `loss_cluster`
into the existing `train_progress` JSON stream (per
`feedback_train_progress_logging_required`). If `loss_lm /
sum(aux_losses) < 0.2` at step 1000, halt training and flag —
aux heads are dominating, hparam tune required.

## 5. Training plan

### 5.1 Starting checkpoint

**v1c VALIDTOK 5ep** — NOT v1d. Per
`feedback_v1d_decision_rule_pointer_copy.md`: v1d destabilization
is the empirical prior; v1c is the proven baseline state. Archived
at `D:\tksCAS-archive\v0_rc1\v1c_VALIDTOK_5ep\` (the same checkpoint
the canary uses).

### 5.2 Hyperparameters

Per `feedback_always_restore_baseline_hparams_for_full_retrains`:
```
--lr 0.001
--batch-size 128
--weight-decay 0.0001
--num-epochs 1     # SINGLE EPOCH per user spec
--warmup-steps 100
--gradient-clip-norm 1.0
```

Cross-validate against the v1c training manifest before launch
(read `D:\tksCAS-archive\v0_rc1\v1c_VALIDTOK_5ep\checkpoint_manifest.json`
to confirm `learning_rate`, `batch_size`, `weight_decay` match).

### 5.3 Training data

Reuse the **v1c training mix** (no corpus changes). The v1c mix
already contains:
- ~5,268 cas_to_english records (Path D Wave 2.5)
- ~2,951 invalid_to_explanation records
- ~5,000+ fractal-containing records across the existing path_d data

Aux supervision derived from `cas_expression` at batch time. No new
data generation.

If the v1d mix at `cas-synthetic/data/path_d/v1d_mix_nlgen_*.jsonl`
is more complete/clean (it has the 532-row regenerated targeted
rows), consider it BUT only if user explicitly approves — the
default is to mirror v1c training.

### 5.4 Compute plan

- Cloud GPU: RunPod A100 spot, ~$0.79/hr (per
  `feedback_gpu_vs_cpu_for_real_training_runs.md`).
- 1 epoch on ~8k records × batch 128 = ~62 steps. At ~1-2 sec/step,
  ~2-3 minutes raw compute. Plus checkpoint load + warm-up overhead.
- **Estimated total wall-clock: ~30-60 minutes.**
- **Estimated cost: ~$0.50-1.00.**
- Per `feedback_fetch_master_before_launch`: `git fetch origin` and
  read recent CHANGELOG.md from pod BEFORE launching.

### 5.5 Output artifact

New checkpoint at pod path:
`/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1e_phase_c_aux_1ep_<timestamp>/`

Includes: `model_final.pt`, `tokenizer.json`, `english_bpe.json`,
`checkpoint_manifest.json`, `train.log`, `training_events.jsonl`.

Pull to local archive at:
`D:\tksCAS-archive\v1e_phase_c\v1e_phase_c_aux_1ep_<timestamp>\`

SHA-256 hashes computed and recorded (mirror v0-rc1 archival process).

## 6. Eval plan

### 6.1 Gates (in order, each is a HARD STOP if it fails)

**Gate 1 — v0 canary (existing, deterministic):**
```
python cas-synthetic/scripts/v0_canary.py
```
Must PASS — confirms the C checkpoint's INFERENCE side (when aux
heads are off / unused) doesn't drift from v0 baseline outputs.
Aux heads are non-load-bearing at inference unless explicitly used.

Wait — actually the C checkpoint IS a different checkpoint than
v1c. The canary expects the v1c checkpoint. To run Gate 1 against
the C checkpoint, we need a new canary baseline OR a different
gate. Resolution: **the C eval uses a NEW reference baseline
generated against the C checkpoint with aux heads OFF** — this
proves aux heads don't change the existing inference path.

Concretely: run `v1_eval_pack_24records.py` against the C
checkpoint with default flags (no aux head use, default
apply_fractal_decoder). Compare per-record outputs against the
v1c canary baseline AND grade against the 18/24 acceptable+
reference. **Both must hold.**

**Gate 2 — 24-pack human-quality regression check:**
Per the kill-switch wording ("if C regresses the 24-pack"). Run
the same 24-record eval pack against the C checkpoint with the
v0 flag profile. The chosen-output `final_text` should not drift
materially from the v1c 18/24 baseline. Compare per-record:
- Baseline 18/24 acceptable+ (from the `072551Z_CODEX_GRADED.md`).
- C result should hold ≥ 17/24 acceptable+. Drop of >1 = regression
  = kill-switch trips.

This requires HUMAN GRADING of the C outputs against targets per
`feedback_samples_are_the_only_true_eval_for_cas_native`. NOT
auto-promoted. I (Claude) grade or surface to user for grade.

**Gate 3 — Phase 1B fractal suite (the actual fractal test):**
Run `v1e_phase1b_shadow_eval.py` against the C checkpoint with:
- A_control: aux heads OFF, apply_fractal_decoder=False (baseline)
- C_aux_only: aux heads ON, apply_fractal_decoder=False
  (training-side fix alone; tests if aux heads change v0 inference
  behavior on fractals)
- C_aux_plus_G: aux heads ON + apply_fractal_decoder=True +
  first_n_mode + leaf_exit_boundary (the C+decoder-levers combo)

Three-metric breakdown reported as in Tasks #135/#138/#139:
slot-commit / first-n / full sequence_match.

**Kill-switch on Gate 3 specifically:** if C+aux_only doesn't
materially improve full_seq_match vs v1c-control (target ≥10/35
under C_aux_only OR ≥20/35 under C_aux_plus_G), then **fail
fractals**, stop v1e, pivot simplex.

### 6.2 Promotion gate (heuristic)

If Gate 1 + Gate 2 + Gate 3 all pass:

| Metric | Target | Notes |
|---|---|---|
| v0 canary baseline-equivalence (under default flags) | identical | byte-diff vs v1c baseline outputs |
| 24-pack human grade | ≥ 17/24 acceptable+ | within 1 of v1c 18/24 baseline |
| Fractal suite full_seq_match (C_aux_plus_G config) | ≥ 20/35 | the β2 gate that decode-side couldn't hit |
| Fractal suite first-n preserved | ≥ 33/35 | no regression vs G_baseline |
| Slot-commits | 35/35 | mechanism still works |
| Record 14 prose | ≥ yellow | the gold-standard prose case |
| Non-fractal negatives byte-equivalent | all 7 | source-shape gate respected |

If C clears all 7 gate cells, surface to user for v0.1
promotion decision (Task #136 path α-equivalent).

If C clears 24-pack but doesn't clear fractal full_seq_match,
surface for partial-promotion decision (ship C+aux + G shadow,
but full_seq_match remains best-effort).

If C fails 24-pack or fails fractals (gate-3 thresholds),
**kill-switch trips → stop v1e and write the simplex pivot
decision doc** (new task #142).

## 7. Risk register

| # | Risk | Detection | Mitigation |
|---|---|---|---|
| R1 | Aux loss dominates LM, model collapse | `loss_lm / sum_aux < 0.2` at step 1000 | Halt + decrease α weights, retry |
| R2 | 1-epoch fine-tune destabilizes v1c content | Gate 2 24-pack regression > 1 record | Kill-switch trips, pivot simplex |
| R3 | Aux heads learn but don't transfer to decoder behavior | Gate 3: aux head F1 high but full_seq_match unchanged | Need inference-side wiring of H_stop into EOS decision (lever 5-equivalent) — may extend scope |
| R4 | Stop-target alignment is noisy (extract_noetic_sequence misses indicators in reply_text) | Sample-read 5 records' aux_stop_targets pre-training | Tune alignment heuristic OR widen indicator vocab |
| R5 | Cloud GPU spend overrun | Track $ at 50% / 75% / 100% of $5 budget | Hard cap at $5 spend; kill job |
| R6 | v1c-baseline-hparam drift (commit-since-v1c hparam changes) | Read v1c manifest BEFORE launch, compare to script defaults | Restore exact baseline per `feedback_always_restore_baseline_hparams` |

## 8. Phased implementation order

1. **Stage 1 — `cas_native/model/aux_heads.py` (NEW)**: 4 head
   classes, attach helpers, weight init.
2. **Stage 2 — `cas_native/model/cas_native_model.py`**: extend
   `attach_aux_heads()` method; add aux forward returning
   `{H_card, H_pos, H_stop, H_cluster}` outputs alongside
   existing forward.
3. **Stage 3 — `cas_native/training/datasets/native_nl_collator.py`**:
   add aux-label derivation. Use existing parsers from
   `inference/fractal_repair.py` + `inference/meta_logic_repair.py`.
   Per-record sample weights for task-type masking.
4. **Stage 4 — `cas_native/training/train_native_nl_gen.py`**:
   wire aux losses with curriculum schedule. Extend
   `train_progress` JSON with `loss_card`, `loss_pos`, `loss_stop`,
   `loss_cluster`.
5. **Stage 5 — unit tests**: `cas_native/tests/model/test_aux_heads.py`
   covering each head's shape + init + a forward pass on dummy
   data + smoke training-loss numeric sanity.
6. **Stage 6 — local smoke training**: run 50-step training on
   CPU with batch_size=4 against a 200-row sample of v1c data.
   Verify loss curves are sane, no NaN, gradients flow. **Get user
   green-light before RunPod launch.**
7. **Stage 7 — RunPod launch**: 1-epoch fine-tune from v1c. Use
   the GPU-budget guardrails from R5.
8. **Stage 8 — eval**: Gates 1-3 in order. Sample-read outputs.
9. **Stage 9 — promotion decision**: surface to user with full
   gate-by-gate read + sample sample-reads.

## 9. Cost summary

| Phase | Eng-time | GPU-hours | Cost |
|---|---:|---:|---:|
| Implementation (stages 1-5) | ~2 eng days | 0 | $0 |
| Local smoke (stage 6) | ~0.25 eng days | 0 | $0 |
| RunPod training (stage 7) | ~0 eng-days (background) | ~1 | ~$1 |
| Eval + sample-reading (stage 8-9) | ~0.5 eng-day | 0 | $0 |
| **Total** | **~3 eng-days** | **~1 GPU-hr** | **~$1** |

Cheap enough to be the LAST v1e experiment before simplex per
the user's kill-switch wording.

## 10. Open questions for user

Before I touch any code, three explicit confirms:

1. **Scope confirm:** all 4 heads (cardinality + per-pos Noetic
   + stop + cluster membership), or drop cluster membership to
   keep this even tighter on the fractal-target goal? Cluster
   adds ~31k params but doesn't help fractals directly.

2. **Training corpus:** mirror the v1c training mix exactly, or
   use the v1d mix (which has 532 regenerated targeted rows from
   Task #135-era work)? v1d mix is cleaner but v1d retraining
   destabilized — using its mix carries some inherited risk.
   My default recommendation: **v1c mix**, NOT v1d mix.

3. **Stage 7 GPU budget cap:** hard cap at **$5** spend
   (one-job runaway protection), kill-switch at $5 even if
   training hasn't completed? Or higher?

After your sign-off on these 3 questions, I proceed Stage 1 → Stage 6.
Stage 7 (RunPod launch) gets its own go/no-go confirm with the
smoke-training results in hand.
