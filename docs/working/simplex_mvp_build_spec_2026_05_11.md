# Simplex Δ°₃₉ MVP — Build Spec (post 6-agent recon)

**Date:** 2026-05-11
**Status:** Build spec draft. Awaiting user sign-off on the synthesis below (especially §7's checkpoint-gated-unified resolution) before any code work.
**Source:** Wave-1 specs from 4 specialists (A encoder, B Fisher-Rao loss, C typed-fiber decoder, D integration) + Wave-2 critic debate (Staged vs Unified). All 6 agent outputs preserved in the prior recon turn.

## 1. Decision context (where this fits)

v0-rc1 deployed at 18/24 acceptable+ on the canonical 24-pack. v1d (data) + v1e (decode-time + aux-head fine-tune) failed three cheap-path attempts to close the fractal-rendering gap; Phase C regressed to 12/24 and killed v1e. The simplex Δ°₃₉ rebuild is the next architectural step. MVP is **the smallest simplex-based model that proves whether the architecture solves what v0/v1d/v1e couldn't** — NOT the shippable product. v0-rc1 stays canonical throughout MVP development; fallback is deployment-level routing to the archived v0 checkpoint, never a same-checkpoint flag.

## 2. Per-component build spec

### 2.1 Δ°₃₉ encoder (Specialist A)

```
class SimplexEncoder(nn.Module):
    # Trunk: 4-layer pre-norm Transformer, d_model=384, n_heads=6, FFN=1536, GELU
    # Positional: RoPE (rotary), NOT sinusoidal
    # Self-attention: bidirectional over source CAS tokens
    # Dropout 0.1; layer-norm at sublayer inputs

    # Tail: 2-layer logit-space mirror-descent recurrence
    #   z_0 = 0 in R^40 (uniform)
    #   For each source position t:
    #     z_{t+1} = z_t + g_theta(h_t, z_t)
    #   g_theta = MLP[(d_model + 40) -> 256 -> 40] with GELU + LN

    # Output projection (ONLY here; trunk + tail are in unbounded R):
    #   p_t = softmax(z_t)
    #   p_t = (p_t + eps) / (1 + 40*eps)        # eps=1e-6 floor + renorm
```

**Outputs:**
- `source_hidden: (B, L_src, 384)` — per-token trunk hidden (decoder cross-attends here)
- `simplex_trajectory: (B, L_src, 40)` — strict positive, row-stochastic; per-source-token Δ°₃₉ point
- `simplex_final: (B, 40)` — masked-mean pool over `simplex_trajectory` (trajectory representative)
- `floor_violations: (B, L_src)` — count of `p_k ≤ 2ε` steps; telemetry for B's monitor

**Params:** ~24.5M trainable. Token embedding 38685 × 384 ≈ 14.9M (reuses v1c VALIDTOK tokenizer); trunk ≈ 9.4M; tail ≈ 0.1M. ~½ of v1c's encoder.

**Rationale:**
- **Logit-space updates** keep gradients bounded (`∂p/∂z` bounded by 1 in operator norm) even when `p_k → ε`. The Fisher-Rao `1/p_k` blow-up at the boundary is contained because mirror descent operates on `z`, not on `p`.
- **Softmax + ε + renorm at the OUTPUT only** matches the existing `embedding.py:_project_to_open_simplex` pattern; B's loss can reuse existing simplex-validity asserts.
- **No FiLM on encoder.** Register becomes a typed fiber inside C.
- **Reject Aitchison CLR/ILR** — elegant but Jacobian adds gradient noise we don't need to debug at MVP scale.

### 2.2 Fisher-Rao trajectory loss (Specialist B)

```
sigma_{b,t} = sum_k sqrt(p[b,t,k] * q[b,t,k])
sigma_{b,t} = clamp(sigma_{b,t}, 0.0, 1.0 - 1e-7)   # numerical safety
d_{b,t}     = 2 * arccos(sigma_{b,t})               # geodesic distance
L_FR        = (sum_{b,t} m[b,t] * d_{b,t}^2) / max(sum_{b,t} m[b,t], 1)
```

**Target trajectory `q ∈ R^(B,T,40)`** derived via **Option γ (hybrid)** at collator time:
- Anchor positions: where a target-English noetic indicator lands (via `extract_noetic_sequence_with_positions(reply_text)`) AND where a typed-slot fixpoint appears in source CAS (Ω, stage_var, coef, register-letter, fractal-k-literal).
- At each anchor: `q[b,t] = near-one-hot` on state `k = (noetic × domain)` index, with ε-floor on others to stay in Δ°₃₉.
- Off-anchor: `m[b,t] = 0`, no loss contribution. Free trajectory between anchors.

**Squared distance, NOT unsquared** — squaring suppresses the gradient near σ=1 where `arccos′` blows up. fp64 internal, fp32 cast at output.

**Combination with C's losses:**
```
L_total = α·L_FR + β·L_LM + γ·L_slot_type + δ·L_copy + 0.1·L_phrase_bias_aux
```
**Flat weights, NO curriculum** (Phase C's ramp was the proximate cause of LM perturbation; flat is structurally safer here because all weights are fresh-init).
- Defaults: `α = 1.0, β = 1.0, γ = 1.0, δ = 0.5`
- Interference monitor at step 1000: `mean(L_FR) / mean(L_LM)` outside `[0.05, 20]` → halt and surface (not auto-restart).

**Metrics emitted in `train_progress` JSON:**
`loss_fr, loss_fr_mean_d, loss_fr_anchor_count, loss_fr_pct_within_eps, simplex_entropy_mean, fr_lm_ratio, simplex_min_p`.

### 2.3 Typed-fiber decoder (Specialist C)

```
class TypedFiberDecoder(nn.Module):
    # 6-layer Transformer decoder, d_model=384, n_heads=6, FFN=1536
    # Two cross-attention KV streams:
    #   stream A: simplex_proj(simplex_trajectory) -> (B, T_src, 384) for cognitive-state alignment
    #   stream B: src_token_emb(src_ids)           -> (B, T_src, 384) for pointer-copy lookup
    # NO FiLM register modulation
    # NO cas_prefix_ids prepended to decoder input

    # Per-position heads:
    #   slot_type_head : Linear(384, 9)
    #   lm_head        : Linear(384, V_english)
    #   copy_attn      : MHA with src_token_emb keys (returns p_copy over T_src)
    #   phrase_bias    : (10, n_phrases_per_k, 384) embedding table
```

**9-class slot types:** `{CONNECTIVE, OMEGA, STAGE_VAR, COEFFICIENT, REGISTER_LETTER, DOMAIN_LETTER, DRIVE_LETTER, FRACTAL_K_LITERAL, NOETIC_PHRASE}`.

**Emission rule per output position:**
- **CONNECTIVE** → standard `lm_head` softmax over English BPE vocab.
- **OMEGA / STAGE_VAR / COEFFICIENT / REGISTER_LETTER / DOMAIN_LETTER / DRIVE_LETTER / FRACTAL_K_LITERAL** → **pointer-copy** from source. `p_copy(j) = softmax((W_q h_t)·(W_k src_emb_j)/√d)`, masked by source-token-type filter so OMEGA slots can only copy from OMEGA-tagged source tokens. Emit `src_ids[argmax_j p_copy(j)]`.
- **NOETIC_PHRASE** → **soft simplex-conditioned phrase bias**:
  ```
  P_next = softmax(lm_logit(h_t) + α_layer · phrase_bias(h_t, k*))
  ```
  where `k* = argmax_d Σ_dom simplex_trajectory[t_src*, 10·dom + k_index]`. NOT hard mask (lesson from v1e Phase 1B).

**Source-side type tags:** `src_token_type: (B, T_src)` computed deterministically at dataset-prep from regex patterns over source CAS. Fed as input to decoder, used by the copy-mask.

**Losses (this lane):**
- `L_LM = CE(lm_logits, target_BPE)` at CONNECTIVE + NOETIC_PHRASE positions only.
- `L_slot_type = CE(slot_type_logits, slot_type_target)` at every position.
- `L_copy = -log p_copy(j*)` at every typed-slot position (pointer-network style; `j*` is corpus-aligned source pointer).
- `L_phrase_bias_aux = -log P_phrase_bias(target_phrase_token | k*, h_t)` at NOETIC_PHRASE positions, weight 0.1.

**Params:** ~24M. Decoupling-via-cross-attention path resolves the v1e "trailing-prose-emits-noetics" problem: `slot_type_head` gates whether the noetic-phrase bias fires; at CONNECTIVE positions the bias multiplies by 0. Connective tissue can therefore emit "then", "after which", "finally" WITHOUT triggering ^7 indicators, even when the simplex coordinate is at ^7.

## 3. Component interfaces (the actual tensor contracts)

```
SimplexEncoder.forward(input_ids, attention_mask) -> dict:
  source_hidden:           (B, L_src, 384)   fp32 or bf16
  simplex_trajectory:      (B, L_src, 40)    fp32, strict positive, row-stochastic
  simplex_final:           (B, 40)           fp32 (masked-mean pool)
  source_attention_mask:   (B, L_src)        bool (echo of input)
  floor_violations:        (B, L_src)        int (telemetry)

FisherRaoLoss.forward(simplex_trajectory, target_trajectory, target_mask) -> scalar
  # Where target_trajectory and target_mask are collator-derived (§4 below)

TypedFiberDecoder.forward(
    decoder_input_ids,
    source_hidden, simplex_trajectory,         # encoder outputs
    src_ids, src_token_type, src_padding_mask  # source for copy
) -> dict:
  lm_logits:                (B, L_out, V_english)
  slot_type_logits:         (B, L_out, 9)
  p_copy:                   (B, L_out, T_src)
  copy_source_indices:      (B, L_out) int16  (-1 at non-typed positions, source idx at typed)
  decoder_hidden_state:     (B, L_out, 384)   (exposed for trace; not for L_FR)
```

**Key alignment point (resolves a Wave-1 tension identified by both critics):** A's trajectory is per-SOURCE-token, B's anchors are derived from TARGET English noetic positions. C's decoder cross-attends to the full `simplex_trajectory (B, T_src, 384-projected)` and the decoder LEARNS the source→target alignment as part of training. B's anchor mask, in turn, places losses at typed-slot fixpoints in the SOURCE (which DO have per-source-token positions) — not at target English positions. This means **B's loss is fully source-indexed; the target-English noetic positions inform WHICH source positions are anchors, but the loss is computed against the source trajectory**. This resolves the alignment ambiguity Critic 1 surfaced.

## 4. Training data + collator

**Data source:** `cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl` (v1c mix, ~7395 records, ~6.2MB). Verbatim, no SDG.

**Fields used:** `cas_expression`, `prompt_text`, `reply_text`, `register`, `v1mix_task_type`, `v1mix_grammar_category_or_error_class`, `id`, `trace_id`.

**New collator class `SimplexCollator`** (sibling to `NativeNLCollator`):
- Existing 9 batch keys preserved (`input_ids`, `attention_mask`, `lm_decoder_input_ids`, `cas_prefix_ids`, `cas_prefix_mask`, `register_id`, `lm_targets`, `loss_mask`, `record_ids`, `trace_ids`).
- New keys added:
  - `fr_target_path: (B, L_src_max, 40)` — per-source-position target simplex points
  - `fr_target_mask: (B, L_src_max)` — bool, True at anchors
  - `fr_target_len: (B,)` — per-record valid trajectory length
  - `typed_slot_positions: (B, L_out, 9)` — one-hot or class id of slot type per output position
  - `typed_slot_source: (B, L_out)` — int16, source-position index for pointer copy at typed positions; -1 elsewhere
  - `src_token_type: (B, L_src_max)` — int8, source-side type tags (9 classes)
  - `parser_strategy: (B,)` — int diagnostic (which target-derivation branch fired per record)
- Auxiliary derivation via `parse_fractal`, `parse_meta_logic`, `extract_noetic_sequence_with_positions` (existing parsers). NO new SDG, NO new parsers.

## 5. Losses + metrics

**Loss assembly** (flat weights, no curriculum):
```
L_total = 1.0·L_FR + 1.0·L_LM + 1.0·L_slot_type + 0.5·L_copy + 0.1·L_phrase_bias_aux
```

**Per-step `train_progress` JSON fields** (always emitted, per `feedback_train_progress_logging_required`):
- `loss_total, loss_lm, loss_fr, loss_slot_type, loss_copy, loss_phrase_bias_aux`
- `loss_fr_mean_d` (unsquared geodesic, interpretable as "how far off target")
- `loss_fr_pct_within_eps` (% anchors with d < 0.1)
- `simplex_entropy_mean` (collapse detector; expected range 1.5-3.0; uniform = 3.69)
- `simplex_min_p` (boundary detector; should stay > 1e-4)
- `fr_lm_ratio` (interference monitor signal)
- `slot_type_accuracy_per_class` (every N steps; detects collapse to always-CONNECTIVE)
- `p_copy_entropy_mean` (detects copy collapse to single source token)
- `grad_norm_encoder, grad_norm_decoder` (separate; clip at 1.0 each)

## 6. CPU smoke plan (mandatory; both critics agree)

Tiny config: `d_model=64`, encoder 2 layers, decoder 2 layers, 4 attention heads. 200-record stratified sample (at least one from each of 8 grammar categories). 50 steps × batch 4 × CPU × lr=1e-4 × no mixed precision × single worker dataloader.

**Required success indicators:**
- All 6 loss terms finite at every step. NO NaN/Inf in any tensor.
- `(simplex_trajectory > 0).all()` and `simplex_trajectory.sum(-1) ≈ 1` at every step (load-bearing assertion).
- `L_LM` decreasing on 10-step smoothing window.
- `L_FR` decreasing AND finite — boundary stability test.
- `L_slot_type`, `L_copy` decreasing on records where they fire.
- 4-record greedy sample read at end (one per category) — output exists, no NaN tokens, no degenerate empties. NOT a quality grade; plumbing check only.

**Halt conditions:** any NaN/Inf → exit 1; `simplex_min_p ≤ 0` ever → exit 1; memory > 4GB → exit 1; any loss frozen (no gradient on records it should fire on) for 5 consecutive steps → exit 1.

## 7. First RunPod experiment plan — **checkpoint-gated unified** (synthesis of Wave-2)

**Both critics converged on this hybrid.** Unified end-to-end training from step 0 (Critic 2's position) **with mandatory checkpoint-and-sample-read at step 1000 and step 2500** (Critic 1's pre-flight insurance, Critic 2's go/no-go gates).

### 7.1 Stage 0 — Pre-flight (~$15-20, hard auto-kill at $25)

- Random-init weights, all components. NO v1c warm-start.
- Hyperparameters anchored to v1c VALIDTOK baseline:
  - `lr = 2e-4`, linear warmup 500 steps, cosine decay to lr/10
  - `batch_size = 8`, `weight_decay = 0.01`, `grad_clip = 1.0`
  - **Run only 1000 steps in Stage 0.**
- Save checkpoint at step 1000. Pull to local. Sample-read 20 records (10 cas_to_english, 10 invalid_to_explanation) via greedy decode. Inspect simplex trajectories on 5 of those.

### 7.2 Stage 0 decision gate (the load-bearing fork)

Check these 4 signatures at step 1000. **ANY ONE TRIPPING flips us from unified to staged S1.**

| Signature | Trip threshold | What it means | Action |
|---|---|---|---|
| FR loss decreasing but LM loss flat/rising | LM loss(step 1000) ≥ LM loss(step 100) | Encoder learning trajectory the decoder can't use; joint training failed | Flip to staged S1 (FR-only encoder pre-train) per §7.5 |
| Simplex collapse | `simplex_min_p < 1e-5` for 100+ consecutive steps OR `simplex_entropy_mean < 0.5` OR `simplex_entropy_mean > 3.5` | Trivial trajectory; FR loss minimized without useful signal | Flip to staged S1 with explicit entropy regularizer |
| slot_type head accuracy < 40% on held-out | Probe 100 held-out records | Decoder not learning typed-slot distinction | Flip to staged S1 then frozen-encoder S2 |
| Source-target cross-attention entropy near uniform | `H(p_copy) > 0.95·log(T_src)` mean | Decoder's pointer-copy attention isn't learning alignment | Flip to staged S1 |

**If all 4 clean at step 1000 → continue unified to step 2500.** Re-check the same 4 signatures. If clean → continue to 5 epochs.

### 7.3 Stage 1 — Full unified run (~$60, hard cap at $75 — D's spec)

- Continue from Stage 0 checkpoint
- 5 epochs total (matching v1c VALIDTOK 5ep baseline)
- ~4625 steps/epoch at 7395 records / batch 8 → ~23k steps total
- Save checkpoint after every epoch
- Continuous monitor: `fr_lm_ratio` interference check at every logging interval (not just step 1000 anymore); `simplex_min_p` continuously

### 7.4 Pre-launch checklist

1. Code synced to pod (scp; pod has no git)
2. Imports verified: `python -c "from cas_native.model.simplex_encoder import SimplexEncoder; from cas_native.model.typed_fiber_decoder import TypedFiberDecoder; from cas_native.training.fisher_rao_loss import FisherRaoLoss; print('ok')"`
3. Single-step GPU dry-run: `python train_simplex_mvp.py --smoke-test` — 1 forward + 1 backward on a 4-record sample, validates CUDA kernel shapes
4. Dataset SHA-256 on pod matches local
5. `nvidia-smi` + `df -h /workspace` — GPU available, ≥40GB free

### 7.5 Fallback path: staged S1 → S2 → S3 (if Stage 0 gate trips)

- **S1** (~1.5 weeks, ~$25): encoder + FR loss only, 2 epochs. Trajectory eval metric: `mean Fisher-Rao distance to analytic target < 0.15 rad` on 80% of held-out items, `simplex entropy ≥ 1.2`. Exit gate: trajectory eval passes.
- **S2** (~2 weeks, ~$30): freeze encoder, attach decoder, train decoder+typed-fiber losses, NO FR. Exit gate: 24-pack ≥ 15/24 acceptable+, slot_type accuracy ≥ 85%, copy F1 ≥ 0.7.
- **S3** (~1 week, ~$20): unfreeze encoder, joint fine-tune 1 epoch at lr=5e-5. Exit gate: 24-pack lifts to ≥ 18/24; S1 trajectory eval holds within 10% degradation.
- Total staged cost: ~$75, same as unified cap.

## 8. Eval gates → v0/v1d/v1e failure evidence (Specialist D's table)

| # | Gate | Test | Failure evidence cited | Kill-switch | Fallback |
|---|---|---|---|---|---|
| 1 | ≥18/24 acceptable+ on 24-pack | `v1_eval_pack_24records.py` against simplex checkpoint, human-grade | v0=18/24 floor; v1d=15/24 regression; Phase C=12/24 | <18 → simplex thesis-in-question | v0-rc1 deployment route |
| 2 | ≥20/35 fractal full seq_match | `v1e_phase1b_shadow_eval.py` with `--checkpoint` patch | v1e Phase 1B 0/35; β2 best 5/35 — the gate v1e couldn't hit | <10 → architectural redesign | v0-rc1 deployment route |
| 3 | 0 truncations on long-output records | Count `truncated=true` in 24-pack JSONL | v1c 0; Phase C 5 (records 11, 15, 19, 20, 21) | Any truncation → kill | v0-rc1 deployment route |
| 4 | Clean stage-var copying on records 19/20/21 | Byte-equal substring check for stage identifiers in `reply_text` | Phase C produced "stageD3_3_0233333" with extra digits | Any corrupted identifier → kill | v0-rc1 deployment route |
| 5 | v0 canary deployment-route fallback always available | `v0_canary.py --check` exit 0 on every PR touching `cas-native/{inference,model}/**` | v0-canary's whole purpose; deployment routing must not affect v0 | Drift on any PR → block PR | v0-rc1 is always available |
| 6 | No catastrophic category regression | Per-record band check: 1/2/4/6/7/8/23/24 stay ≥yellow; 17/18/22 hold; 19/20/21 with clean stage IDs | Phase C: 4 green→yellow, 11/15/19/20/21 → wrong/flop | Any prior-green drops below yellow → kill | v0-rc1 deployment route |

## 9. Risks + kill-switches (synthesized from all 4 specialists)

| Risk | Detection | Mitigation | Kill-switch |
|---|---|---|---|
| Simplex collapse to uniform/single-mode | `simplex_min_p < 1e-5` 100+ steps OR `entropy` outside [0.5, 3.5] for 500 steps | ε-floor at output; optional entropy regularizer `+λ·H(p)` with λ=0.01 (off default, on if signature appears) | Auto-halt training |
| Boundary gradient explosion in L_FR | `grad_norm_encoder > 1e3` OR NaN in L_FR | fp64 internal compute; clamp `σ ∈ [0, 1-1e-7]`; clip_grad_norm 1.0 | NaN → halt; preserve checkpoint for postmortem |
| Loss interference (FR vs LM fight) | `fr_lm_ratio` outside [0.05, 20] at step 1000; cosine `< -0.3` between L_FR and L_LM gradients on probe batches | Flat weights; no curriculum; **PCGrad-style projection only if Stage 0 gate trips** | Surface to user (not auto-restart) |
| Pointer-copy collapse to always-copy | `mean(slot_type == CONNECTIVE) < 0.5` (corpus statistic is ~0.7-0.85) | L_slot_type supervised at every position pulls non-typed → CONNECTIVE | Down-weight L_copy to 0.25 if persistent |
| Noetic-prose decoupling fail (CONNECTIVE positions emit noetic indicators) | Extract noetic indicators from generated CONNECTIVE spans on held-out; should be near 0% | Soft phrase bias is gated by slot_type predicting NOETIC_PHRASE — connective positions multiply by 0 | If leakage >5%: add Bernoulli gate on `α · phrase_bias` |
| Typed-slot detector confused by ambiguous source | Error analysis on records 22-24 (invalid-CAS) where coefficients ≠ COEFFICIENT slot | Slot type head reads decoder hidden state (already simplex-conditioned); add global `is_invalid_cas` flag if needed | Slot_type accuracy < 60% → halt, audit source-type tagging |
| v0 byte-equivalence broken | `v0_canary.py --check` exit nonzero | All simplex code in NEW files; deployment routing selects checkpoint at process boot, not at inference call | Canary drift → block PR; do NOT proceed |
| RunPod cost overrun | Per-hour cost-check posted to `training_events.jsonl` | Hard cap `auto_stop_at_dollar_amount = 75` in launch script | Pod self-terminates; partial checkpoint preserved |
| Almost-tripped patterns that should NOT abort | Single-step LM loss spikes (gradient clip events); single record failing on eval; `simplex_min_p` briefly touching 1e-4 in first 100 steps | Documented as known false-positives | None — these don't halt training |

## 10. Open questions for user before implementation

**Three sign-off points** before I commit any code or write the `train_simplex_mvp.py` driver:

1. **Approve the checkpoint-gated unified strategy in §7?** This is the Wave-2 critic synthesis: unified from step 0, but mandatory 1000-step checkpoint with 4 specific flip conditions that fall back to staged S1→S2→S3. Or do you prefer pure staged (Critic 1's full position) or pure unified (Critic 2's full position)?

2. **Approve the loss-weight defaults?** `L_total = 1.0·L_FR + 1.0·L_LM + 1.0·L_slot_type + 0.5·L_copy + 0.1·L_phrase_bias_aux`, flat weights, no curriculum. The interference monitor at step 1000 catches imbalance.

3. **Approve the GPU cap?** $75 total for the full unified run (Stage 0 + Stage 1), with $25 sub-cap for Stage 0 pre-flight. Per-stage auto-stop on cost overrun.

## 11. Wave-1 + Wave-2 traceability

Every spec line in this synthesis cites a specialist:

- §2.1 architecture, parameterization, output shape, params, boundary cases → Specialist A
- §2.2 loss formula, target derivation (Option γ), numerical stability, squared-vs-unsquared → Specialist B
- §2.3 decoder architecture, 9-class slot types, pointer-copy + phrase bias decoupling → Specialist C
- §3 interfaces — synthesized to resolve A↔B↔C tensor alignment (per both critics' tension callout); explicit clarification that B's loss is source-indexed even though anchor positions are informed by target-English noetic positions
- §4 data + collator, §5 losses, §6 CPU smoke, §8 eval gates → Specialist D
- §7 Stage 0 checkpoint-gated strategy → Wave-2 synthesis of Critic 1 (staged) + Critic 2 (unified)
- §7.2 4-signature trip table → Critic 1 + Critic 2 both proposed these signatures; combined here
- §7.5 staged fallback path → Critic 1's S1→S2→S3 plan verbatim
- §9 risks → all 4 specialists, deduplicated

## 12. What I'm NOT proposing (anti-recidivism reminder)

Per `project_v1e_killswitch_tripped_simplex_pivot_2026_05_11.md` + `feedback_simplex_mvp_user_review_guardrails_2026_05_11.md`:

- NOT a v1c fine-tune. Train from scratch.
- NOT a retry / repair scaffold of any kind. The "PCGrad-style projection only if Stage 0 gate trips" in §9 is a one-time mitigation, NOT a retry loop.
- NOT a same-checkpoint v0 fallback. Fallback is deployment-level routing to archived v0-rc1.
- NOT a compiler-validated generation gate. CAS→English emits English; compiler validation belongs to v1.1 English→CAS work.
- NOT a new SDG / cleaner-corpus / one-more-epoch loop. v1c mix verbatim.
- NOT curriculum-scheduled aux weights. Flat weights or hard switch to staged via §7.2 gate; no Phase-C-style ramp.

## Next action

User sign-off on §10's three questions. Once approved, I write a 9-stage execution plan (modeled on v1e Phase C's Stages 1-9 from `docs/working/v1e_phase_c_aux_heads_design_2026_05_11.md`) with explicit user-gates at:
- end of CPU smoke → user reviews loss table + sample outputs
- end of Stage 0 (step 1000) → user reviews the 4 trip signatures + sample reads
- end of Stage 1 epoch 1 → user reviews mid-training telemetry
- post-training → user reviews 24-pack grade + Phase 1B fractal eval

No code, no GPU spend until that execution plan is also signed off.
