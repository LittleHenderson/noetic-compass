# Simplex MVP — Stage 6 GPU Dry-Run Report

**Date:** 2026-05-11
**Run timestamp:** 2026-05-11 04:56:04 UTC
**Pod:** root@194.68.245.88:22026 — NVIDIA RTX A6000, 46 GB VRAM, torch 2.5.1+cu124, CUDA 12.4
**Run dir on pod:** `/workspace/tksCAS/stage6_dry_run_v2_20260511T045602Z/`
**Verdict:** **8 of 9 checks PASS, 1 build-spec correction surfaced** — architecturally green, budget-doc needs an update.

## Run command

```
python cas-native/training/stage6_gpu_dry_run.py \
  --output-dir /workspace/tksCAS/stage6_dry_run_v2_<ts>/ \
  --device cuda:0 \
  --d-model 384 --encoder-n-layers 4 --decoder-n-layers 6 \
  --encoder-n-heads 6 --decoder-n-heads 6 \
  --batch-size 4 --vocab-size-override 38685
```

## Check results (8/9 architectural PASS)

| # | Check | Verdict | Evidence |
|---|---|---|---|
| 1 | Real-size model instantiates on cuda:0 | **PASS** | encoder=22.19M + decoder=48.02M = 70.21M params on cuda:0 |
| 2 | Tensor shape contracts at d_model=384 | **PASS** | source_hidden=(4,3,384), simplex_traj=(4,3,40), simplex_final=(4,40), slot_type=(4,25,9), p_copy=(4,25,3), lm_logits=(4,25,38685) |
| 3 | Simplex invariants at real size | **PASS** | (p > 0).all() = True; rows sum to 1 (max deviation 1.2e-7); min_p = 0.01083 |
| 4 | Device + dtype contracts | **PASS** | all params on cuda; simplex_trajectory dtype = torch.float32 (build-spec §3 contract) |
| 5 | Param count in budget (48.5M ± 2M) | **FAIL** | **actual 70.208M vs target 48.5M, delta +21.7M — build-spec correction needed** |
| 6 | No NaN/Inf in forward + backward | **PASS** | total = 17.461; all 5 loss parts finite |
| 7 | Gradient flow encoder + decoder | **PASS** | enc grad-norm = 7.76; dec grad-norm = 14.57; all grads finite |
| 8 | GPU memory + wall-clock | **PASS** | peak = 1.34 GB (< 20 GB); step = 0.52 s (< 10 s) |
| 9 | train_progress JSON fields emit | **PASS** | all 11 fields present (loss_total, loss_lm, loss_fr, loss_slot_type, loss_copy, loss_phrase_bias_aux, grad_norms, simplex_entropy_mean, simplex_min_p, fr_lm_ratio) |

## Check 5 — what the failure means

The model size on cuda is **70.2M params, not 48.5M**. The build-spec underestimated:

- Encoder: 22.19M (vs spec ~24.5M) — close, slightly below
- Decoder: **48.02M (vs spec ~24M)** — **2× the spec estimate**

The decoder's actual breakdown:
- 6-layer Transformer body: ~16M
- `token_emb` at 38685 × 384: **14.9M** (decoder has its own English BPE embedding)
- `lm_head` at 384 × 38685: **14.9M**
- `simplex_proj`, `src_token_proj`, `slot_type_head`, `phrase_bias_table`, `phrase_bias_proj`: ~2M combined

The build-spec line "Params: ~24M" for the decoder seems to have under-counted the token_emb + lm_head pair at the v1c vocab size. There is no double-counting bug in our code — these are two separate weight matrices (input embedding vs output logits), neither is weight-tied (yet).

**This is a build-spec budget correction, not an architectural failure.**

Options going into Stage 7:
- **A. Accept 70M, update build-spec.** No code change. GPU memory (1.34 GB) and wall-clock (0.52s) are deep inside their thresholds; the architecture has no operational problem at this size. The $25 Stage 0 sub-cap and $60 Stage 1 cap were sized assuming 48.5M; with 70M the per-step cost rises ~50% but wall-clock margin is enormous (52ms vs 10s budget).
- **B. Tie `lm_head.weight` to decoder `token_emb.weight`.** Saves 14.9M, drops total to ~55M. Standard transformer trick. Costs one extra `weight=` argument on `nn.Linear` construction (or a transpose in forward). Low-risk, well-supported pattern.
- **C. Reduce decoder layers 6 → 4.** Saves ~6M, drops total to ~64M. Drops decoder capacity which we may want for the typed-fiber decoder's job (slot_type + copy + phrase-bias on top of LM).

Recommend **A or B**. **C** trades architecture for budget; given the GPU has 46 GB and Stage 5 showed losses moving correctly, capacity is not the bottleneck.

## Placeholder surfacing (user requirement)

Stage 6 explicitly does NOT imply the full 5-loss system is functionally live:

| Loss term | Value at step 1 | Status | Why |
|---|---|---|---|
| L_LM | 10.795 | **LIVE** | Cross-entropy at every non-pad output position; gradient flows to encoder + decoder |
| L_FR | 4.610 | **LIVE** | Fisher-Rao squared geodesic on Δ°₃₉; 4 anchors fire from the Stage-1 collator stub |
| L_slot_type | 2.056 | **LIVE** | 9-class CE; targets from typed_slot_positions (Stage-1 collator emits one-hot CONNECTIVE or first-slot OMEGA) |
| L_copy | **0.000** | **PLACEHOLDER** | Collator anchor stub emits `typed_slot_source = -1` for every output position. Pointer-copy path is shape-correct (Stage 2 tests) but no live gradient signal. Wired for Stage 7 anchor-derivation work. |
| L_phrase_bias_aux | **0.000** | **PLACEHOLDER** | `compute_losses()` returns `torch.zeros((), requires_grad=False)`. Phrase-bias target table needs corpus-aligned labels. Wired for Stage 7. |

**Warning surfaced in `stage6_report.json`:**

> Stage 6 PASS only validates that LM + FR + slot_type are live and the model wiring is sound at real size. It does NOT validate L_copy or L_phrase_bias_aux. Treat the 5-loss assembly as **3-of-5 live** until Stage 7.

## fr_lm_ratio at step 1

`fr_lm_ratio = 0.427` — inside the interference-monitor safe band [0.05, 20] from build-spec §2.2. No retune signal triggered.

## Resource consumption

- **GPU memory peak**: 1.34 GB out of 46 GB available (3% utilization). Plenty of headroom for the 1000-step Stage 0 + 5-epoch Stage 1 runs even if 70M is the locked size.
- **Wall-clock**: 0.52 s for a single step. 1000 steps at this rate ≈ 9 minutes; the Stage 0 $25 sub-cap covers ~30 min of A6000, so we have ~3× wall-clock margin.
- **Pod elapsed for Stage 6**: ~90 s total (sync + run). Sub-$0.05 spend at A6000 spot pricing.

## Stage 7 entry decision

The architecture-feasibility property is met: 8 of 8 architectural checks PASS. Check 5 is a build-spec doc correction, not an architectural failure.

Recommendation: **approve A (accept 70M, update budget doc) OR B (weight-tie, get to 55M), then proceed to Stage 7**.

If the user picks B, the change is ~5 lines in `typed_fiber_decoder.py`:
```python
# In __init__:
self.lm_head = nn.Linear(self.cfg.d_model, self.cfg.vocab_size_english, bias=False)
self.lm_head.weight = self.token_emb.weight  # tie
```
We rerun the dry-run to confirm 55M before launching Stage 7.

If A: surface the budget delta in the execution plan, update the Stage 0 $25 sub-cap rationale (still fits), and launch Stage 7.

**Stage 7 launch authorization is the user's call — not auto-greenlit by this report.**

## Companion artifacts (committed)

- `noetic-compass-scaffold/noetic-compass/cas-native/training/stage6_gpu_dry_run.py` — the self-contained dry-run script
- `docs/working/simplex_mvp_stage6_gpu_dry_run_report_2026_05_11.json` — full machine-readable report

Pod-side artifacts (in `/workspace/tksCAS/stage6_dry_run_v2_20260511T045602Z/`):
- `stage6_report.json` (same content as the doc copy above)
