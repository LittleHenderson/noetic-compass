# Simplex MVP — Stage 6 GPU Dry-Run v5 (L_copy LIVE)

**Date:** 2026-05-11
**Run timestamp:** 2026-05-11 05:28:33 UTC
**Pod:** RTX A6000 46GB, torch 2.5.1+cu124, CUDA 12.4
**Run dir on pod:** `/workspace/tksCAS/stage6_dry_run_v5_lcopy_20260511T052832Z/`

## Verdict: PASS — 10/10 checks. 4-of-5 losses LIVE.

| Loss | Value | Status |
|---|---|---|
| L_LM | 10.696 | LIVE |
| L_FR | 4.571 | LIVE (4 anchors fired) |
| L_slot_type | 1.997 | LIVE |
| **L_copy** | **1.696** | **LIVE** (7 valid copy slots; argmax_acc 14.3% — exactly 1/7 random baseline pre-training) |
| L_phrase_bias_aux | 0.000 | **PLACEHOLDER** (deferred per user 2026-05-11; non-gating in Stage 7) |
| L_total | 18.111 | — |

`fr_lm_ratio = 0.427` — inside safe band.

## v3 → v4 → v5 evolution

| Iteration | Total params | LM @ step 1 | L_copy | Live loss count | Verdict |
|---|---|---|---|---|---|
| v2 | 70.21M (untied) | 10.80 | 0.0 placeholder | 3-of-5 | 8/9 (budget) |
| v3 | 55.35M (tied, default init) | 293.81 ❌ | 0.0 placeholder | 3-of-5 | 9/9 by gate, LM broken |
| v4 | 55.35M (tied + GPT-2 init) | 10.69 | 0.0 placeholder | 3-of-5 | 9/9 |
| **v5** | **55.35M (tied + GPT-2 init)** | **10.70** | **1.696 LIVE** | **4-of-5** | **10/10** |

## 10 gate checks (all PASS)

| # | Check | Verdict | Evidence |
|---|---|---|---|
| 1 | Real-size model instantiates on cuda:0 | PASS | 55.35M params (encoder 22.19M + decoder 33.17M) |
| 2 | Shape contracts at d_model=384 | PASS | source_hidden (8,7,384), simplex (8,7,40), p_copy (8,42,7), lm_logits (8,42,38685) |
| 3 | Simplex invariants | PASS | (p > 0).all() = True; row-sum dev 1.2e-7; min p = 0.00938 |
| 4 | Device + dtype contracts | PASS | all params cuda; simplex fp32 |
| 5 | Param count in budget | PASS | 55.352M vs 55.5M (±3M), delta −0.148M |
| 6 | No NaN/Inf | PASS | total = 18.11, all 5 loss parts finite |
| 7 | Gradient flow both paths | PASS | enc 9.52, dec 36.64, all finite |
| 8 | Memory + wall-clock | PASS | 1.10 GB peak; 0.58 s |
| 9 | train_progress fields emit | PASS | 11 fields present |
| **10** | **L_copy live** | **PASS** | **copy_valid_count = 7, copy_loss_live = 1.696, copy_argmax_acc = 0.143** |

## What v5 added on top of v4

1. **Real `typed_slot_source` derivation in `SimplexCollator`** (was a Stage-1 stub):
   - Token-string classifier (`classify_source_token`) regex-matches the four single-token-mappable slot types: `^P/^C/^E/^O` → DOMAIN_LETTER; `F1..F7`, `F_1..F_7` → DRIVE_LETTER; `|T/|A/|f/|E` → REGISTER_LETTER; `Ω*`, `Omega*` → OMEGA.
   - For each target token, scans source tokens for an id-match where the source-side classification is a typed slot. First match wins. Emits `(out_pos, slot_id, src_pos)`.
   - STAGE_VAR, COEFFICIENT, FRACTAL_K_LITERAL remain deferred (multi-token or context-aware — needs more work; slot ids stay defined in `typed_fiber_decoder.SLOT_TYPES` so architecture is unchanged).

2. **Four new copy telemetry fields in `compute_losses` `__copy_metrics__` sub-dict**:
   - `copy_valid_count` — total positions with `typed_slot_source >= 0` in batch
   - `copy_loss_live` — actual L_copy value when valid_count > 0, NaN when not measured
   - `copy_argmax_acc` — hit rate of `p_copy.argmax(dim=-1) == typed_slot_source` at valid positions
   - `copy_entropy_valid_mean` — mean Shannon entropy of `p_copy` at valid positions

3. **Copy-bearing record fixture** (`copy_bearing_records()` in `train_simplex_mvp.py`):
   - 8 records with reply texts that literally contain source-side typed identifiers (`|f`, `|T`, `|A`, `|E`, `Ω_resolve`, `Ω_grounding`, `Ω_clarity`, `^O`, etc.)
   - Drives 7 valid copy slots in a batch of 8 records (some have multiple registers, some single).

4. **Stage 6 check 10 (NEW)** — `L_copy live`:
   - PASS iff `copy_valid_count > 0` AND `copy_loss_live` is finite AND `copy_loss_live > 0`.
   - At step 1, `copy_argmax_acc = 14.3%` = exactly `1/7` (random baseline for 7 source positions). The copy head starts random and must rise above chance with training — that's Stage 7's job to verify.

## Stage 7 Q4 revision (per user 2026-05-11 caveat)

The Stage 7 architecture-feasibility gate Q4 ("Is copy path non-random?") is now well-posed:

> **Revised Q4:** "When valid copy slots exist in the batch (`copy_valid_count > 0`), is `copy_argmax_acc` above the random baseline of `1 / L_src_mean` AND `copy_loss_live` decreasing on a 100-step smoothing window? If `copy_valid_count == 0` for the entire 1000-step run, treat Q4 as **NOT MEASURED**, not pass/fail."

This is the correct framing: we don't penalize the architecture when there are no copy slots to evaluate; we only judge it when there's signal to measure. The copy-bearing fixture in `stage6_gpu_dry_run.py` guarantees signal-bearing batches during dry-run; the v1c training corpus will produce a mix of copy-bearing and non-copy-bearing batches naturally.

## Loss decomposition

| Term | Value (step 1) | Status | Note |
|---|---|---|---|
| L_LM | 10.696 | LIVE | ≈ `log(38685) = 10.56` baseline; near-uniform softmax pre-training |
| L_FR | 4.571 | LIVE | 4 anchors per record fire from typed source tokens |
| L_slot_type | 1.997 | LIVE | `log(9) = 2.20` baseline; just under uniform |
| L_copy | 1.696 | LIVE | `log(7) = 1.95` baseline; just under uniform |
| L_phrase_bias_aux | 0.000 | **PLACEHOLDER** | `torch.zeros((), requires_grad=False)` — deferred work |

## Stage 7 entry status

**Stage 7 launch is now AUTHORIZED on architectural grounds** — 4 of 5 losses exercise live gradient paths and the placeholder is documented as non-gating. Three remaining preconditions before the 1000-step run kicks off:

1. **User explicit approval to launch Stage 7** — this report is a precondition, not a green-light.
2. **Update execution plan §Stage 7 Q4** with the revised "not measured" framing above (small markdown edit).
3. **Decide on Stage 7 entry config**: at minimum, the same flag set used for v5 plus the real v1c training corpus + tokenizer (vs synthetic). The dry-run validated wiring, not corpus learning dynamics.

## Resource consumption

- **GPU memory peak:** 1.10 GB out of 46 GB available (2.4% utilization)
- **Wall-clock per step:** 0.58 s
- **Pod cost for v5 iteration:** < $0.05 spot
- **Cumulative Stage 6 cost (v2 + v3 + v4 + v5):** < $0.20 spot

## Companion artifacts (this commit)

- `noetic-compass-scaffold/noetic-compass/cas-native/training/datasets/simplex_collator.py` — live derivation
- `noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py` — copy telemetry + fixture
- `noetic-compass-scaffold/noetic-compass/cas-native/training/stage6_gpu_dry_run.py` — uses copy_bearing_records + check 10
- `noetic-compass-scaffold/noetic-compass/cas-native/tests/training/test_simplex_collator.py` — 9 new derivation tests
- `docs/working/simplex_mvp_stage6_v5_lcopy_live_2026_05_11.md` — this report
- `docs/working/simplex_mvp_stage6_v5_lcopy_live_report_2026_05_11.json` — machine-readable

Pod artifact:
- `/workspace/tksCAS/stage6_dry_run_v5_lcopy_20260511T052832Z/stage6_report.json`
