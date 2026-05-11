# Simplex Δ°₃₉ MVP — 9-Stage Execution Plan

**Date:** 2026-05-11
**Status:** Plan draft. Awaiting user sign-off (specifically on §10 three confirmations). No code or GPU spend until signed off.
**Parent docs:**
- Build spec: `docs/working/simplex_mvp_build_spec_2026_05_11.md` (signed off 2026-05-11 with 3 modifications)
- User modifications: captured in memory at `project_simplex_mvp_signoff_with_modifications_2026_05_11.md`

## Plan principles (locked from build-spec sign-off)

- **Strategy:** checkpoint-gated unified — unified end-to-end from step 0, but mandatory architecture-feasibility gate at step 1000 of training.
- **Loss weights:** flat defaults `L = 1.0·L_FR + 1.0·L_LM + 1.0·L_slot_type + 0.5·L_copy + 0.1·L_phrase_bias_aux`. If Stage 0 telemetry shows FR or slot dominating LM, fall back to a structured **ablation grid** (LM+FR / LM+slot / LM+FR+slot / full), not blind weight tuning.
- **GPU caps:** $25 Stage 0 sub-cap (incl. ablations if needed), $60 Stage 1 cap, **$75 absolute hard ceiling with auto-stop.**
- **Stage 0 is architecture feasibility, not training progress.** 6 yes/no questions at step 1000 (§7.2 of build spec, expanded here in Stage 7).
- **No code, no GPU spend** beyond what each stage explicitly authorizes. Every stage has an entry gate and an exit gate.

---

## Stage map at a glance

| Stage | What it produces | Cost | User-gate after? |
|---|---|---|---|
| 1. Code skeleton | New files: encoder, decoder, FR loss, collator, trainer driver | ~3 eng-days, $0 | No (internal milestone) |
| 2. Per-component unit tests | `test_simplex_encoder.py`, `test_typed_fiber_decoder.py`, `test_fisher_rao_loss.py`, `test_simplex_collator.py` — all pass | ~2 eng-days, $0 | No |
| 3. Integration wiring | Trainer driver assembles model + collator + losses, 1-step CPU forward+backward works | ~1 eng-day, $0 | No |
| 4. Integration tests | Trainer dry-runs end-to-end on 4-record sample, no NaN, all loss terms fire | ~1 eng-day, $0 | No |
| **5. CPU smoke** | 50 steps × batch 4 × d_model=64 on 200-record stratified sample | ~0.5 eng-day, $0 | **Yes — user reviews loss table + sample reads + tensor-shape report** |
| **6. Pod setup + GPU dry-run** | Code on pod, imports verified, 1-step GPU dry-run on REAL model size (d_model=384, full layer count) — hard gate before any Stage 7 spend | ~0.5 eng-day, ~$2 GPU | **Yes — user reviews the GPU dry-run report before authorizing Stage 7 launch** |
| **7. Stage 0 pre-flight (1000 steps)** | Step-1000 checkpoint + telemetry + 20-record sample read | ~3-4 hrs wall, ≤$25 GPU (with $25 hard cap) | **Yes — user reviews 6-question architecture feasibility gate** |
| **7-bis. Ablation grid** (only if Stage 7 trips) | Four 500-step sub-runs (LM+FR / LM+slot / LM+FR+slot / full) to find viable loss combo | ~6-8 hrs wall (4 sub-runs sequential), within the $25 Stage-0 cap | **Yes — user picks winning ablation** |
| 8. Stage 1 full unified run | 5-epoch checkpoint (or fewer if interference monitor halts) | ~12-18 hrs wall, ≤$60 GPU | No (intermediate stop at epoch 1 surfaces if telemetry diverges) |
| **9. Eval + promotion-gate evaluation** | 24-pack eval + Phase 1B fractal suite + v0-canary fallback verify + sample-read for category regression | ~1 eng-day + 1 evaluator-day, $0 GPU | **Yes — user reviews 6 promotion gates** |

Three user-gates marked **bold** are the load-bearing decision points. Internal stages don't require sign-off.

---

## Stage 1 — Code skeleton (no behavior change)

**Goal:** create new files. No edits to v0 inference path. No changes to existing tests' behavior.

**New files:**
- `noetic-compass-scaffold/noetic-compass/cas-native/model/simplex_encoder.py` — `SimplexEncoder` class per build-spec §2.1
- `noetic-compass-scaffold/noetic-compass/cas-native/model/typed_fiber_decoder.py` — `TypedFiberDecoder` class per §2.3
- `noetic-compass-scaffold/noetic-compass/cas-native/training/fisher_rao_loss.py` — `FisherRaoLoss` per §2.2
- `noetic-compass-scaffold/noetic-compass/cas-native/training/datasets/simplex_collator.py` — `SimplexCollator(NativeNLCollator)` subclass adding 7 batch keys per §4
- `noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py` — new trainer entry point (sibling to `train_native_nl_gen.py`; v0 trainer remains canonical)
- `cas-synthetic/scripts/v1e_phase1b_shadow_eval.py` — add `--checkpoint` arg + `--config simplex_native` mode (small patch, exists already; just extend)

**Files NOT touched (v0 hands-off):**
- `cas-native/inference/*` — anything routed_generate, postprocessor, repair scaffolds. v0 inference path is canonical.
- `cas-native/model/cas_native_model.py`, `nl_generation_head.py`, `aux_heads.py` — v0 architecture stays untouched.
- `cas-native/training/train_native_nl_gen.py` — v0 trainer untouched.
- `cas-synthetic/scripts/v0_canary.py` — canary is sacrosanct.

**Entry gate:** §10 user sign-off on this execution plan.
**Exit gate:** all 5 new files compile and import. Adjacent test suite still passes:
```bash
pytest cas-native/tests/model/test_aux_heads.py cas-native/tests/training/test_native_nl_collator.py cas-native/tests/inference/test_fractal_decoder.py
```

**Kill-switches:** none yet (no model running).

---

## Stage 2 — Per-component unit tests

**Goal:** each new module passes shape + invariant tests in isolation. Mirrors the v1e Phase C Stage 5 pattern.

**New test files:**
- `cas-native/tests/model/test_simplex_encoder.py` — at least 12 tests:
  - Shape: trunk output `(B, L_src, 384)`, simplex_trajectory `(B, L_src, 40)`, simplex_final `(B, 40)`
  - Invariant: `(simplex_trajectory > 0).all()` and `simplex_trajectory.sum(-1) ≈ 1` on dummy inputs of varying shape
  - Boundary: with extreme logit input, `simplex_min > ε` after softmax+ε+renorm
  - Gradient flow: `loss.backward()` on dummy loss produces non-zero grads on trunk + tail
  - Mirror-descent step: `g_θ` output matches expected shape
  - RoPE positional: deterministic across runs given fixed seed
- `cas-native/tests/training/test_fisher_rao_loss.py` — at least 8 tests:
  - Shape: scalar output
  - Sanity: `L_FR(p, p) ≈ 0` (zero distance to self)
  - Sanity: `L_FR(p, antipode_of_p) ≈ π²` (max distance squared)
  - Numerical: near-1 σ doesn't NaN (clamp working)
  - Near-0 σ doesn't NaN
  - Sample weights: anchor mask correctly zeros non-anchor positions
  - fp64 internal compute path verified
  - Squared distance: gradient magnitude check near optimum
- `cas-native/tests/model/test_typed_fiber_decoder.py` — at least 15 tests:
  - Shape: lm_logits, slot_type_logits, p_copy
  - 9-class slot_type head correctly classifies each class on synthetic input
  - Pointer-copy attention masked correctly by source-token-type filter
  - Phrase-bias only fires when slot_type predicts NOETIC_PHRASE
  - Cross-attention to simplex_trajectory and src_token_emb runs
  - Default-off when slot_type predicts CONNECTIVE: phrase_bias × 0
  - Gradient flow through copy attention, lm head, slot_type head, phrase table
  - Param count within budget (~24M ± 2M)
- `cas-native/tests/training/test_simplex_collator.py` — at least 8 tests:
  - All 16 batch keys produced (9 existing + 7 new)
  - `fr_target_path` strictly positive, row-stochastic
  - `fr_target_mask` correctly anchors at fractal slot positions on fractal records
  - `typed_slot_positions` correctly identifies Ω, stage_var, coefficient slots on real records
  - `src_token_type` regex-derived correctly on `cas_expression` strings
  - Non-fractal records: `fr_target_mask` mostly zero
  - Non-meta-logic records: cluster slots absent
  - Backward compatibility: with `enable_simplex_aux=False`, batch identical to `NativeNLCollator` output

**Total new tests:** ~43.

**Entry gate:** Stage 1 complete.
**Exit gate:** all new tests pass. Adjacent test suite still passes (no regressions in v1c/v1e tests).
**Kill-switches:** any test fails → fix before continuing.

---

## Stage 3 — Integration wiring

**Goal:** trainer driver assembles model + collator + losses; 1-step CPU forward+backward works on a 4-record sample.

**Code work:**
- `train_simplex_mvp.py` `build_parser()` with CLI args: `--data-path`, `--output-dir`, `--epochs`, `--batch-size`, `--lr`, `--device`, `--smoke-test`, `--smoke-records 4`, ablation flags `--ablation {full,lm_fr,lm_slot,lm_fr_slot}` defaulting to `full`
- `build_simplex_mvp_model()` factory — instantiates `SimplexEncoder` + `TypedFiberDecoder`, wires the cross-attention streams
- Training loop: forward → losses → backward → optim step → `train_progress` JSON
- Per-loss telemetry emitted to `train_progress`:
  - `loss_total, loss_lm, loss_fr, loss_slot_type, loss_copy, loss_phrase_bias_aux`
  - `loss_fr_mean_d`, `loss_fr_pct_within_eps`, `loss_fr_anchor_count`
  - `simplex_entropy_mean`, `simplex_min_p`
  - `fr_lm_ratio` (interference monitor signal — every log step, not just step 1000)
  - `slot_type_accuracy_running`, `p_copy_entropy_mean`
  - `grad_norm_encoder`, `grad_norm_decoder` (separate)
  - `lr_now`, `step`, `epoch`, `batch_in_epoch`, `batches_per_sec`, `eta_epoch_min`
- Ablation grid plumbing: with `--ablation lm_fr`, weight `L_slot_type = L_copy = L_phrase_bias_aux = 0`; with `--ablation lm_slot`, weight `L_FR = L_copy = L_phrase_bias_aux = 0`; with `--ablation lm_fr_slot`, weight `L_copy = L_phrase_bias_aux = 0`; with `--ablation full`, all 5 losses live.

**Entry gate:** Stage 2 complete, all unit tests pass.
**Exit gate:** `python train_simplex_mvp.py --smoke-test` runs 1 forward + 1 backward on 4 records, no NaN, all 5 loss terms have non-zero gradients on records where they should fire.
**Kill-switches:** NaN at integration → halt; surface to user.

---

## Stage 4 — Integration tests

**Goal:** trainer dry-runs end-to-end on a 4-record sample. Catches shape mismatches at the model/collator/loss interface that unit tests miss.

**New test file:** `cas-native/tests/training/test_simplex_mvp_integration.py` — at least 6 tests:
- Trainer initializes from CLI args; model + collator + optimizer constructed
- 1-step forward returns dict with all expected keys
- 1-step backward populates gradients on all param groups
- Loss sum is finite and positive
- `train_progress` event JSON has all expected fields
- `--ablation lm_fr` mode: `loss_slot_type == 0`, `loss_copy == 0`, `loss_phrase_bias_aux == 0` (verified zero-weight)

**Entry gate:** Stage 3 complete.
**Exit gate:** all 6 integration tests pass. Total test count: ~49 new + existing.
**Kill-switches:** integration test fails → halt; surface for fix.

---

## Stage 5 — CPU smoke ← **User-gate**

**Goal:** prove the architecture trains coherently on real records (not toy inputs) before any GPU spend.

**Smoke config:** identical to build spec §6:
- `d_model = 64`, encoder 2 layers, decoder 2 layers, 4 attention heads
- 200-record stratified sample from `v1_mix_nlgen_train.jsonl` (≥1 record per of 8 grammar categories)
- 50 steps × batch 4 × CPU × `lr = 1e-4` × no mixed precision × single worker dataloader
- `--ablation full` (all 5 losses live)
- `--train-log-every-steps 10`
- Output: `D:/tmp/simplex_mvp_cpu_smoke_<timestamp>/`

**Run command** (committed in repo for reproducibility):
```bash
python noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py \
  --data-path cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl \
  --output-dir D:/tmp/simplex_mvp_cpu_smoke_<timestamp>/ \
  --epochs 1 --batch-size 4 --limit 200 --device cpu \
  --d-model 64 --encoder-n-layers 2 --decoder-n-layers 2 \
  --encoder-n-heads 4 --decoder-n-heads 4 \
  --lr 1e-4 --ablation full \
  --train-log-every-steps 10 --logging-steps 25 \
  --sample-every-steps 25 --sample-record-index 0
```

**Success indicators (all required):**
- All 5 loss terms finite at every step. NO NaN/Inf.
- `(simplex_trajectory > 0).all()` and `simplex_trajectory.sum(-1) ≈ 1` asserted at step 0 and step 25.
- `L_LM` decreasing on a 10-step smoothing window.
- `L_FR` decreasing AND finite — boundary stability test.
- `L_slot_type` and `L_copy` decreasing on records where they fire.
- 4-record greedy sample read at end (one per category) — output exists, no NaN tokens.

**Halt conditions:**
- Any NaN/Inf in any tensor → exit 1.
- `simplex_min_p ≤ 0` ever → exit 1.
- Memory > 4GB → exit 1.
- Any loss frozen for 5 consecutive steps on records where it should fire → exit 1.

**Surface to user:**
- Loss table per logging interval (~5 rows)
- Tensor shape check report
- 4 sample outputs (greedy reads, NOT graded — plumbing check only)
- Param count: model total + per-component breakdown
- Wall-clock time

**Entry gate:** Stages 1-4 complete.
**Exit gate:** smoke runs to completion, all 5 success indicators hold, user signs off on the smoke report before Stage 6.
**Kill-switches:** smoke fails → diagnose + fix; do NOT proceed to GPU spend.

---

## Stage 6 — Pod setup + GPU dry-run ← **User-gate (HARD)**

**Goal:** push code to pod and validate actual tensor / device / dtype wiring on the **real model size**, NOT a toy config. This is a HARD GATE, not mechanical setup — per user instruction 2026-05-11: "Stage 6 GPU 1-step dry-run should come before any 1000-step Stage 0 spend, and it must verify actual tensor/device/dtype wiring on the real model size."

**Tasks:**
1. SCP new files to pod (no git on pod):
   - `simplex_encoder.py`, `typed_fiber_decoder.py`, `fisher_rao_loss.py`, `simplex_collator.py`, `train_simplex_mvp.py`
2. SSH to pod, import sanity:
   ```bash
   python -c "from cas_native.model.simplex_encoder import SimplexEncoder; \
              from cas_native.model.typed_fiber_decoder import TypedFiberDecoder; \
              from cas_native.training.fisher_rao_loss import FisherRaoLoss; \
              from cas_native.training.datasets.simplex_collator import SimplexCollator; \
              print('ok')"
   ```
3. **GPU 1-step dry-run at REAL MODEL SIZE** (NOT toy d_model=64; the CPU smoke already validated toy):
   - `d_model = 384`, encoder 4 layers, decoder 6 layers, n_heads = 6
   - `batch_size = 8` (the Stage 7 batch size)
   - Sample: 8 records from `v1_mix_nlgen_train.jsonl` covering ≥2 grammar categories (e.g., 4 fractal + 4 state_literal)
   - 1 forward + 1 backward + 1 optimizer step
   - `--device cuda`
4. `nvidia-smi` shows GPU available; `df -h /workspace` shows ≥40GB free.
5. Dataset SHA-256 on pod matches local.

**Hard validation checks (ALL must pass before authorizing Stage 7):**
- **Tensor shape contracts hold** at full size: encoder produces `(8, L_src, 384)` source_hidden, `(8, L_src, 40)` simplex_trajectory, `(8, 40)` simplex_final; decoder produces `(8, L_out, V)` lm_logits, `(8, L_out, 9)` slot_type_logits.
- **Simplex invariants hold:** `(simplex_trajectory > 0).all()` AND `simplex_trajectory.sum(-1) ≈ 1` (tolerance 1e-5) on the real-size forward.
- **Device contracts hold:** all parameters on `cuda:0`; no silent CPU fallback.
- **Dtype contracts hold:** simplex computation in fp32 even if rest of model is bf16/fp16; encoder/decoder match the documented dtype scheme.
- **Param count matches expectation:** total model params within ±2M of estimate (~48.5M for encoder + decoder at d_model=384).
- **No NaN/Inf** in any tensor — losses, gradients, intermediate activations.
- **Backward pass produces gradients on all 5 loss components.** Verified by inspecting `param.grad` is non-None and non-zero on a sample param from each module.
- **GPU memory usage** under 20GB on a 40GB A100 (gives headroom for batch growth or activation checkpointing at Stage 7).
- **Wall-clock** for the 1-step forward+backward < 10 seconds (catches a runaway shape that produces correct outputs but is unusably slow).

**Surface to user:**
- Stage 6 report containing all 8 hard validation results above, with concrete numbers (tensor shapes, param count, GPU memory used, wall-clock).
- `nvidia-smi` snapshot.
- Dataset SHA-256 confirmation.
- Imports-verified confirmation.
- Recommendation: proceed to Stage 7 / fix specific defect / abort.

**Entry gate:** Stage 5 user sign-off + budget available.
**Exit gate:** all 8 hard validation checks pass AND user signs off on the Stage 6 report before any Stage 7 spend.
**Cost:** ~$2 GPU (single step, real size). Counts against the $25 Stage-0 sub-cap.
**Kill-switches:**
- Any tensor shape contract fails → halt, SCP fix from local + retry
- Any simplex invariant fails → halt, debug encoder
- NaN/Inf at real model size (when CPU smoke was clean) → halt, surface as critical (likely dtype or device bug)
- Param count off by >10% → halt, audit module definitions
- GPU memory > 30GB → halt, reduce batch size or add activation checkpointing
- Cumulative cost (Stage 6 alone) > $5 → auto-stop, surface for diagnosis

---

## Stage 7 — Stage 0 pre-flight (1000 steps) ← **User-gate**

**Goal:** the architecture-feasibility gate per build-spec §7. Answer the 6 yes/no questions at step 1000.

**Run config:**
- Random-init weights (no `--resume-from`)
- Hyperparameters anchored to v1c baseline: `lr = 2e-4`, linear warmup 500 steps, cosine decay to lr/10, `batch_size = 8`, `weight_decay = 0.01`, `grad_clip = 1.0`
- Full dimensions: `d_model = 384`, encoder 4 layers, decoder 6 layers (matches build spec §2)
- `--ablation full` (all 5 losses live)
- **1000 training steps only** (max ~$25)
- Save checkpoint at step 1000

**Pod RUN_DIR:** `/workspace/runs/simplex_mvp_stage0_<timestamp>/`

**Cost control:**
- Per-hour cost-check posted to `training_events.jsonl`
- `auto_stop_at_dollar_amount = 25` in launch script
- Trip = pod shuts down, partial checkpoint preserved

**Post-run: pull checkpoint to local, run sample-read script:**
- Greedy-decode 20 records (10 cas_to_english, 10 invalid_to_explanation) — stratified across all 8 grammar categories
- Inspect simplex trajectories on 5 of those (per-step `argmax_k p_t` visualization)

### Stage 7 decision gate — the 6 architecture-feasibility questions

| # | Question | Pass criterion | Detection method |
|---|---|---|---|
| 1 | Does simplex stay non-collapsed? | `simplex_min_p > 1e-5` AND `simplex_entropy_mean ∈ [0.5, 3.5]` | Telemetry from `train_progress` events, last 200 steps |
| 2 | Does FR decrease without LM collapse? | `mean(L_FR)` at step 1000 < `mean(L_FR)` at step 100 AND `mean(L_LM)` at step 1000 ≤ `mean(L_LM)` at step 100 + 0.1 | Telemetry, smoothed |
| 3 | Does slot_type learn above chance? | `slot_type_accuracy_running > 0.40` on the last 100 records | Telemetry `slot_type_accuracy_running` |
| 4 | Is copy path non-random? | `mean(p_copy_entropy) < 0.95 · log(T_src)` averaged over last 200 steps | Telemetry `p_copy_entropy_mean` |
| 5 | Is cross-attention non-uniform? | Mean cross-attn entropy < 0.95 · log(T_src) for at least 1 decoder layer | Add cross-attn entropy probe at step 1000 (extra telemetry) |
| 6 | Are samples non-degenerate? | 20-record sample read: ≥ 15 records produce parseable English (no NaN tokens, no pure repetition, no obvious failure) | Human sample-read |
| **6-veto** | **Phase-C-shape failure check (HARD OVERRIDE)** | NO record in the 20-record sample exhibits severe token corruption (`"ABeing"`, `"stageD3_3_0233333"`-style boundary glitches), abrupt mid-clause truncation, or pure repetition loops (≥3 consecutive identical phrases). Per user 2026-05-11: "if any sample shows severe token corruption/truncation/repetition like Phase C, fail even if scalar metrics look okay." | Human sample-read with explicit checklist against the v1e Phase C damage signature |

**Decision rule:**
- **All 6 = YES AND 6-veto = clean** → continue to Stage 8 (full unified run)
- **ANY = NO OR 6-veto trips** → trigger Stage 7-bis (ablation grid)
- **If Stage 7-bis also fails** → STOP iterating; flip to staged S1→S2→S3 fallback OR pause for architectural review (user picks)

The 6-veto is intentionally a hard override: scalar metrics can look acceptable (slot_type accuracy 45%, p_copy entropy below threshold) while sample reads reveal Phase-C-style structural damage. The v1e Phase C lesson is durable: telemetry-clean training does not imply eval-clean model. The 6-veto is the architectural-feasibility analog at Stage 0.

**Surface to user:**
- 6-question scorecard with pass/fail per question + the specific telemetry value
- Loss table per logging interval (full 1000-step trace, ~20 rows at log_every=50)
- Per-loss magnitudes + ratios (`fr_lm_ratio`, etc.) — per user mod #2
- Cost: actual GPU spend vs $25 sub-cap
- 20-record sample read text + per-record simplex argmax trajectory for 5 records
- Recommendation: proceed / ablation / staged fallback

**Entry gate:** Stage 6 complete; ≤$25 budget available.
**Exit gate:** user signs off on which path (proceed / ablation / staged).
**Kill-switches:**
- Cost exceeds $25 → auto-stop
- NaN in any loss → halt
- `simplex_min_p < 1e-5` for 100 consecutive steps → halt, surface as critical
- `fr_lm_ratio` outside [0.05, 20] at step 1000 → flag as gate failure (question 2 NO)

---

## Stage 7-bis — Ablation grid (conditional on Stage 7 trip)

**Triggered if:** Stage 7's 6-question gate has ANY NO due to loss imbalance (specifically if questions 2 or 3 fail because one loss is dominating).

**Goal:** identify which loss combination is structurally viable. Per user mod #2: do NOT tune weights blindly; run a structured ablation grid.

**4 sub-runs, each 500 training steps, sequential within $25 Stage-0 cap:**

| Sub-run | `--ablation` flag | Active losses | Question this answers |
|---|---|---|---|
| 7-bis-1 | `lm_fr` | L_LM + L_FR | Can simplex trajectory learn from FR alone alongside LM? |
| 7-bis-2 | `lm_slot` | L_LM + L_slot_type | Can slot-type detector learn alongside LM without FR? |
| 7-bis-3 | `lm_fr_slot` | L_LM + L_FR + L_slot_type | Do FR and slot interact constructively without copy/phrase? |
| 7-bis-4 | `full` | all 5 losses | Full default — replays Stage 7 for comparison |

Each sub-run gets the same 6-question gate at its step 500.

**Cost:** each sub-run ~500 × batch 8 ≈ 65 batches × ~1 sec/step ≈ ~1.5 min training + ~5 min checkpoint load. 4 sub-runs × ~10 min wall-clock = ~40 min total. ~$1.20 each at A100 spot ≈ ~$5 total. Well within remaining $25 sub-cap.

**Surface to user:**
- 6-question scorecard for EACH of 4 sub-runs
- Per-sub-run loss curves (LM, FR, slot, copy, phrase_bias_aux per active term)
- Per-sub-run 5-record sample reads
- Recommendation: which ablation wins (or "none viable, flip to staged")

**Entry gate:** Stage 7 6-question gate has NO (OR 6-veto trips on Phase-C-shape damage).
**Exit gate:** user picks the winning ablation OR signs off on flipping to staged fallback / architectural review.

**Hard stop rule (per user 2026-05-11):** "If all four ablations fail, do not keep tuning. Move to staged S1→S2→S3 or pause for architectural review." After 4 ablation sub-runs, there are no more weight-tuning iterations — the choice is between:
- **Staged fallback** (S1 encoder+FR only → S2 frozen-encoder + decoder → S3 unfreeze joint fine-tune, build spec §7.5)
- **Architectural review pause** — back to design-doc level; specialists re-recon; potentially redesign components A/B/C before any further training spend
This rule prevents the ablation grid from quietly becoming a "tune the weights and retry" loop, which is exactly the v1e Phase 3 / retry-scaffold pattern the anti-recidivism guardrails ban.

**Kill-switches:**
- Cumulative cost (Stages 6 + 7 + 7-bis) approaching $25 → halt remaining sub-runs
- All 4 sub-runs fail their 6-question gate (AND/OR the 6-veto sample-shape check) → STOP iterating; surface to user with staged-vs-architectural-review choice
- Any sub-run hits Phase-C-shape damage in samples → flag as failure regardless of scalar metrics (same 6-veto rule from Stage 7)

---

## Stage 8 — Stage 1 full unified run (5 epochs or until convergence)

**Goal:** train the full simplex MVP from the Stage 7 (or Stage 7-bis winning) checkpoint to a deployable state.

**Run config:**
- Continue from Stage 7 (or 7-bis winning) checkpoint
- Same hyperparameters as Stage 7
- 5 epochs total (matches v1c VALIDTOK 5ep baseline)
- ~4625 steps/epoch at 7395 records / batch 8 → ~23k steps total
- Save checkpoint after every epoch
- **Continuous interference monitor:** `fr_lm_ratio` checked at every logging interval. If outside [0.05, 20] for 5 consecutive intervals → emit `fr_lm_imbalance` event and halt (NOT auto-restart).
- **Continuous simplex collapse monitor:** if `simplex_min_p < 1e-5` for 500 consecutive steps → halt.

**Pod RUN_DIR:** `/workspace/runs/simplex_mvp_stage1_<timestamp>/`

**Cost control:**
- `auto_stop_at_dollar_amount = 60` in launch script
- Per-hour cost-check posted; surface warning at $30 (halfway)
- Trip = pod shuts down, partial checkpoint preserved

**Intermediate stop:**
- At end of epoch 1: print loss table + 20-record sample read in train.log (NOT a user-gate; just observable in real-time tail)
- If end-of-epoch loss values diverge wildly from Stage 7 trends → operator (Claude) may signal halt to user before continuing

**Entry gate:** Stage 7 PASS (or 7-bis winning combo).
**Exit gate:** 5 epochs complete OR interference monitor halt OR simplex collapse halt OR cost cap.
**Kill-switches:**
- Cost > $60 sub-cap → auto-stop
- Cumulative cost (Stage 7 + 7-bis + Stage 8) > $75 absolute cap → auto-stop
- Interference monitor 5 consecutive intervals → auto-halt
- Simplex collapse 500 steps → auto-halt

---

## Stage 9 — Eval + promotion-gate evaluation ← **User-gate**

**Goal:** run all 6 promotion gates from build-spec §8 against the Stage 8 checkpoint. NO GPU spend (eval is local CPU + human grading).

**Tasks (in order, hard-stop if any gate fails):**

1. **Pull Stage 8 checkpoint to local archive** with SHA-256:
   - `D:\tksCAS-archive\v1e_simplex_mvp\<timestamp>\` (mirrors v0-rc1 + v1e_phase_c archive structure)
   - Files: `model_final.pt`, `tokenizer.json`, `english_bpe.json`, `checkpoint_manifest.json`, `train.log`, `training_events.jsonl`, `run_info.txt`
   - SHA-256 hashes computed and recorded

2. **Gate 5 (v0-canary fallback always available):** 
   - `python cas-synthetic/scripts/v0_canary.py --check` → must exit 0
   - Validates that simplex MVP development did NOT alter v0 inference path
   - If FAILS: STOP, regenerate canary baseline OR diagnose v0 contamination

3. **Patch eval-pack for simplex checkpoint loading:**
   - `v1_eval_pack_24records.py` needs a `--simplex-checkpoint` mode that builds `SimplexEncoder + TypedFiberDecoder` instead of `CASNativeModel + NLGenerationHead`
   - Or: a separate `v1_eval_pack_24records_simplex.py` driver
   - Verify load works on the new checkpoint with strict=False as needed

4. **Gate 1 (≥18/24 acceptable+ on 24-pack):**
   - Run patched eval-pack
   - Human sample-read each of 24 records against target, assign band (green / high yellow / yellow / wrong/flop)
   - Tally acceptable+ band

5. **Gate 3 (0 truncations on long-output records):**
   - Count `truncated=true` in the JSONL output
   - If any → kill-switch

6. **Gate 4 (clean stage-var copying on records 19/20/21):**
   - Byte-equal substring check for every `stageA0_*` / `stageD*` / `stageW*` / `stageP*` identifier in `reply_text` vs `cas_expression`
   - If any corrupted (Phase C signature: "stageD3_3_0233333") → kill-switch

7. **Gate 6 (no catastrophic category regression):**
   - Per-record band check against build-spec §8 specific records
   - Records 1, 2, 4, 6, 7, 8, 23, 24 must remain ≥yellow
   - Records 17, 18, 22 must hold
   - Records 19, 20, 21 must remain ≥yellow with clean stage identifiers
   - If any prior-green drops below yellow → kill-switch

8. **Gate 2 (≥20/35 fractal full seq_match):**
   - Patch `v1e_phase1b_shadow_eval.py` to accept simplex checkpoint
   - Run against 35 fractal records + 7 negative controls
   - Three-metric breakdown: slot-commits / first-n / **full seq_match**
   - Full seq_match ≥ 20/35 required
   - Negative controls byte-match v0 baseline

**Surface to user — final report:**
- 6-gate scorecard with pass/fail + concrete numbers per gate
- Per-record band table for the 24-pack with C-vs-v0 deltas
- Phase 1B 35-record fractal table with three-metric breakdown
- Sample reads for any record that regressed or barely passed
- v0-canary verification result
- SHA-256 hashes of archived files
- Recommendation: **promote to v0.1 / hold for v1.1 work / kill-switch fallback to v0**

**Entry gate:** Stage 8 produced a final checkpoint.
**Exit gate:** user makes the promotion / hold / kill decision based on the report.
**Kill-switches:** any gate failure → STOP, do NOT deploy. v0-rc1 remains canonical product.

---

## Decision tree summary

```
User signs off on this plan
  ↓
Stage 1-4 (code skeleton + tests, ~7 eng-days, $0)
  ↓
Stage 5 CPU smoke ← user-gate
  ↓
Stage 6 pod setup (~$2)
  ↓
Stage 7 Stage-0 pre-flight (1000 steps, ≤$25) ← user-gate
  ↓
  ALL 6 questions YES? ─── Yes ──→ Stage 8 full unified ($60) ──→ Stage 9 eval ← user-gate
                       │
                       └─── No ──→ Stage 7-bis ablation grid (within $25 cap) ← user-gate
                                  ↓
                                  Winning ablation? ── Yes ──→ Stage 8 with winning loss combo
                                                    │
                                                    └── No ──→ Staged fallback (S1→S2→S3, ~$75)
```

---

## Costs + timeline

| Stage | Eng-time | Wall-clock | GPU cost |
|---|---|---|---|
| 1 — Code skeleton | 3 days | — | $0 |
| 2 — Unit tests | 2 days | — | $0 |
| 3 — Integration wiring | 1 day | — | $0 |
| 4 — Integration tests | 1 day | — | $0 |
| 5 — CPU smoke | 0.5 day | 30 min | $0 |
| 6 — Pod setup + dry-run | 0.5 day | 1 hr | ~$2 |
| 7 — Stage 0 pre-flight | 0.5 day | 3-4 hr | ≤$25 |
| 7-bis — Ablation grid (conditional) | 1 day | 1 hr | within $25 sub-cap |
| 8 — Stage 1 full unified | 0 days (background) | 12-18 hr | ≤$60 |
| 9 — Eval | 1 day eng + 1 day evaluator | 4 hr | $0 |
| **Total** | **~10-11 eng-days + 1 evaluator-day** | **~3 days calendar including waiting** | **≤$75 absolute cap** |

---

## Files this plan will create / touch / leave alone

**Create (Stage 1):**
- `cas-native/model/simplex_encoder.py`
- `cas-native/model/typed_fiber_decoder.py`
- `cas-native/training/fisher_rao_loss.py`
- `cas-native/training/datasets/simplex_collator.py`
- `cas-native/training/train_simplex_mvp.py`
- `cas-native/tests/model/test_simplex_encoder.py`
- `cas-native/tests/model/test_typed_fiber_decoder.py`
- `cas-native/tests/training/test_fisher_rao_loss.py`
- `cas-native/tests/training/test_simplex_collator.py`
- `cas-native/tests/training/test_simplex_mvp_integration.py`

**Touch (Stage 9):**
- `cas-synthetic/scripts/v1_eval_pack_24records.py` (add simplex-checkpoint loading mode)
- `cas-synthetic/scripts/v1e_phase1b_shadow_eval.py` (add simplex-checkpoint mode)

**Leave alone (v0 hands-off):**
- `cas-native/inference/*` (v0 inference path canonical)
- `cas-native/model/cas_native_model.py`, `nl_generation_head.py`, `aux_heads.py`
- `cas-native/training/train_native_nl_gen.py`
- `cas-synthetic/scripts/v0_canary.py`
- `D:\tksCAS-archive\v0_rc1\*` — v0 checkpoint archive

---

## Anti-recidivism reminder (per memory)

- NOT a v1c fine-tune — train from scratch
- NOT a retry / repair scaffold of any kind
- NOT a same-checkpoint v0 fallback (deployment routing only)
- NOT compiler-validated generation in MVP
- NOT a curriculum-scheduled aux weight (flat or hard switch to staged via Stage 7 gate)
- NOT a "tune the weights and retry" loop if Stage 7 trips — the **ablation grid** is the structured response per user mod #2
- NOT a v0-canary regeneration without explicit user authorization (v0.N-rc bump)

---

## §10 — User sign-off received 2026-05-11

User approved the 9-stage plan with one tightening + two additions:

1. **9-stage plan + 3 user-gates** → **APPROVED**, with the tightening:
   - Stage 6 (Pod setup + GPU dry-run) **promoted to HARD GATE** with full-size tensor/device/dtype validation BEFORE any Stage 7 1000-step spend. 8 hard validation checks now required; user reviews Stage 6 report before authorizing Stage 7 launch.

2. **Stage 7 6-question architecture-feasibility checklist** → **APPROVED** with the addition:
   - **6-veto Phase-C-shape failure check** added as a hard override. If ANY sample in the 20-record sample read shows severe token corruption ("ABeing", "stageD3_3_0233333"-style), mid-clause truncation, or pure repetition loops, the gate fails regardless of scalar metrics. User's words: "if any sample shows severe token corruption/truncation/repetition like Phase C, fail even if scalar metrics look okay."

3. **Stage 7-bis ablation grid** → **APPROVED** with the hard-stop rule:
   - 4 sub-runs within $25 Stage-0 sub-cap
   - **If all 4 ablations fail, do NOT keep tuning.** Move to staged S1→S2→S3 OR pause for architectural review. User's words: "If all four ablations fail, do not keep tuning. Move to staged S1→S2→S3 or pause for architectural review."

User's exact authorization (2026-05-11):
> "Proceed to commit/push the execution plan, then Stage 1 code skeleton."

**Status: PROCEEDING TO STAGE 1.**

I will surface at the end of Stage 4 (before CPU smoke) to confirm the test suite passes; that is an internal milestone but not a hard user-gate. Hard user-gates remain at Stage 5 (CPU smoke), Stage 6 (GPU dry-run at real size), Stage 7 (1000-step gate + 7-bis if needed), and Stage 9 (promotion gates).
