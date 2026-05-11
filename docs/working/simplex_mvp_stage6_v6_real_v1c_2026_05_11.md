# Simplex MVP — Stage 6 GPU Dry-Run v6 (real v1c tokenizer + corpus)

**Date:** 2026-05-11
**Run timestamp:** 2026-05-11 05:36:03 UTC
**Pod:** RTX A6000 46GB, torch 2.5.1+cu124, CUDA 12.4
**Run dir on pod:** `/workspace/tksCAS/stage6_dry_run_v6_real_20260511T053602Z/`

## Verdict: FAIL — 9 of 10 checks PASS, but check 10 (L_copy live) fails on real corpus.

**Critical finding:** the v5 copy supervision approach (literal token-id match between source and target) **does NOT fire on the v1c corpus**, even though the source-side classifier correctly identifies DOMAIN_LETTER, DRIVE_LETTER, REGISTER_LETTER, OMEGA tokens. Reason: **v1c replies are English paraphrases of CAS**, not literal copies.

Stage 7 launch is **NOT authorized**. Per user 2026-05-11 caveat:

> "If v6 shows copy supervision mostly misses rpm/fractal rows, extend those derivations before Stage 7. Stage 7 should not spend 1000 steps proving an incomplete copy signal."

v6 shows copy misses **every** category, not just rpm/fractal. Extensions required.

## Architectural checks (9/9 PASS — unchanged from v5)

| # | Check | Verdict | Evidence |
|---|---|---|---|
| 1 | Real-size model on cuda:0 | PASS | 55.35M params (real v1c tokenizer vocab=38683 — 2 ids smaller than the placeholder 38685; tokenizer-determined) |
| 2 | Shape contracts at d_model=384 | PASS | source_hidden (21, 32, 384), lm_logits (21, 192, 38683), p_copy (21, 192, 32) — actual batch_size=21 from stratified sample |
| 3 | Simplex invariants | PASS | (p > 0).all() = True; min_p = 0.00731 |
| 4 | Device + dtype contracts | PASS | all params cuda; simplex fp32 |
| 5 | Param count in budget | PASS | 55.351M vs 55.5M target, delta −0.149M |
| 6 | No NaN/Inf | PASS | total = 17.58, all losses finite |
| 7 | Gradient flow | PASS | enc 9.20, dec 45.37 |
| 8 | Memory + wall-clock | PASS | 4.45 GB peak (was 1.10 GB in v5 — larger from 21-record batch), 0.58 s step |
| 9 | train_progress fields emit | PASS | all 11 fields present |

## Check 10 — L_copy live (FAIL on real corpus)

| Metric | Value |
|---|---|
| copy_valid_count | **0** (across all 21 records / 7 categories) |
| L_copy | 0.000 (placeholder — no slots fired) |
| copy_loss_live | NaN (not measured) |
| copy_argmax_acc | NaN (not measured) |

## Per-category breakdown — the structural finding

Source-side classifier WORKS on all 7 categories (DOMAIN_LETTER/DRIVE_LETTER/REGISTER_LETTER/OMEGA correctly tagged on source). Target-side literal copy NEVER fires.

| Category | Records | src_slot_histogram | copy_valid_count |
|---|---|---|---|
| rpm_chain | 3 | DOMAIN_LETTER: 3 | **0** |
| recipe | 3 | DOMAIN_LETTER: 6, REGISTER_LETTER: 1 | **0** |
| fractal | 3 | (none — `Phi⟨…⟩` form has no source-side DOMAIN/DRIVE/REG/OMEGA) | **0** |
| meta_logic | 3 | (none — `PartitionOf(NoeticCluster{^4, …})` form has no source-side DOMAIN/DRIVE/REG/OMEGA) | **0** |
| cross_register_omega | 3 | REGISTER_LETTER: 7, OMEGA: 2, DOMAIN_LETTER: 3 | **0** |
| state_literal | 3 | DOMAIN_LETTER: 3, DRIVE_LETTER: 3, REGISTER_LETTER: 1 | **0** |
| binary_composition | 3 | DOMAIN_LETTER: 4 | **0** |

## Sample diagnosis (why copy fails)

**state_literal** — cas `^0^C_{F4}` reply: "A thought in cognitive thinking, driven by a need for connection."

- Source tokens (per v1c tokenizer probe): `['^0', '^C', '_{', 'F4', '}']`
- Source-side classifier correctly marks `^C` → DOMAIN_LETTER, `F4` → DRIVE_LETTER.
- Reply text contains NO `^C`, NO `F4`. The reply paraphrases `^C` → "cognitive thinking" and `F4` → "need for connection".

**rpm_chain** — cas `let stageA0_5_0296 = ^0^P; ...` reply: `Let stageA0_5_0296 name a foundational thought, stageD5_5_0296 name practiced rhythm...`

- Source tokens for `stageA0_5_0296`: `['stage', 'A', '<CHAR:0030>', '<CHAR:005F>', '<CHAR:0035>', '<CHAR:005F>', '<CHAR:0030>', '<CHAR:0032>', '<CHAR:0039>', '<CHAR:0036>']` — 10 tokens, identifier-decomposed.
- Reply tokens contain the EXACT SAME 10-token span (the rpm stage variable name IS preserved literally in the reply).
- But the v5 classifier doesn't fire on STAGE_VAR — it's still deferred.
- And single-token matching would create false positives (matching every `stage`, `A`, `0`, `_` token).
- **Multi-token span matching would catch this — but it's NOT implemented.**

**recipe** — cas `Θ(Ω_translation_59) = 2*^9^O + 1*^8^O → Ω_translation_59` reply: "To produce the outcome called translation_59, combine 2 of what one thing leads to another in operational thinking with..."

- `Ω_translation_59` → 16 tokens in source (Ω + _ + t + r + a + n + s + ...).
- Reply contains `translation_59` (Ω-prefix stripped) — partial-suffix match would catch this; literal full-id match would not.
- Reply contains `2`, `combine 2 of...` — COEFFICIENT digit literally preserved, but COEFFICIENT classifier is deferred.

**fractal** — cas `Phi⟨1:5:2:7:-1:9:9⟩` reply: "The list of values inside the expression contains a negative number..."

- Source tokens: `['Phi', '⟨', '1', ':', '5', ':', '2', ':', '7', ':', '-', '1', ':', '<CHAR:0039>', ...]`
- Reply does NOT literally contain `1`, `5`, `2`, `7` — it describes the list, not enumerate it.
- For THIS particular reply, fractal-k-literal copy wouldn't fire even with FRACTAL_K_LITERAL classifier. Other fractal records might preserve digits literally; this one doesn't.

## What v6 actually validated

| Concern | Status |
|---|---|
| Real-size model instantiates with v1c tokenizer | ✅ |
| Wiring is unaffected by tokenizer swap | ✅ |
| No NaN/Inf with real corpus | ✅ |
| Gradient paths flow through real corpus | ✅ |
| Memory still fits at batch 21 (4.45 GB << 20 GB threshold) | ✅ |
| param-count budget still hits target | ✅ |
| **L_copy fires on real v1c corpus rows** | ❌ |

## Required extensions before Stage 7 (per user caveat)

Three slot types need real derivation. Empirically prioritized by which categories they unblock:

| Extension | Categories it serves | Implementation complexity | Estimated yield |
|---|---|---|---|
| **STAGE_VAR multi-token span match** | rpm, rpm_chain | Medium — multi-token contiguous-span matching | High (rpm_chain reply literally contains identifier; would fire ~10+ matches per record) |
| **OMEGA suffix match** (Ω_X → X) | recipe, cross_register_omega | Low — strip Ω_ prefix, match suffix | High (recipe replies typically contain `translation_59`/`alignment_X`) |
| **COEFFICIENT digit-span** | recipe | Low — digit-only token sequences | Medium (replies say "combine 2 of …", digit preserved) |
| **FRACTAL_K_LITERAL digit-span in `⟨…⟩`** | fractal | Medium — context-aware (inside fractal brackets only) | Low–medium (some fractal replies enumerate, some paraphrase) |

What `DOMAIN_LETTER`/`DRIVE_LETTER`/`REGISTER_LETTER` give in practice: **almost nothing on the v1c corpus** — these are paraphrased. They still fire on synthetic copy-bearing fixtures (v5 passed), but won't on real training data. That's an inherent property of the v1c reply style (English paraphrase of CAS), not a bug.

## Resource consumption

- **GPU memory peak:** 4.45 GB out of 46 GB available (9.7% utilization) — larger batch (21 vs 8 in v5) shifted memory up but still deep inside threshold.
- **Wall-clock per step:** 0.58 s (~same as v5)
- **Pod cost for v6:** < $0.05 spot

## Cumulative Stage 6 spend (v2 + v3 + v4 + v5 + v6): < $0.25 spot.

## Stage 7 status — NOT AUTHORIZED

Stage 7 launch is held until at least the **STAGE_VAR** and **OMEGA suffix** extensions land and a v7 dry-run shows copy_valid_count > 0 on real v1c rows.

## Companion artifacts (this commit)

- `noetic-compass-scaffold/noetic-compass/cas-native/training/stage6_gpu_dry_run.py` — v6 flags + per-category breakdown
- `docs/working/simplex_mvp_stage6_v6_real_v1c_2026_05_11.md` — this report
- `docs/working/simplex_mvp_stage6_v6_real_v1c_report_2026_05_11.json` — machine-readable
- `docs/working/simplex_mvp_execution_plan_2026_05_11.md` — §Stage 7 Q4 revised (not-measured framing)

Pod artifact:
- `/workspace/tksCAS/stage6_dry_run_v6_real_20260511T053602Z/stage6_report.json`
