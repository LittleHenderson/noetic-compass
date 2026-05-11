# Simplex MVP — Stage 6 Dry-Run v7 (STAGE_VAR + OMEGA suffix on real v1c)

**Date:** 2026-05-11
**Run timestamp:** 2026-05-11 05:50:49 UTC
**Pod:** RTX A6000 46GB, torch 2.5.1+cu124, CUDA 12.4
**Run dir on pod:** `/workspace/tksCAS/stage6_dry_run_v7_stagevar_omega_20260511T055048Z/`

## Verdict: PASS architecturally (10/10 checks), but **partial empirical fire**.

| User's required category-level evidence | Result |
|---|---|
| rpm_chain should fire STAGE_VAR | **PASS** — 56 valid copy slots, 3/3 records |
| recipe/CRO should fire OMEGA | **FAIL** — 0 valid copy slots in recipe; 0 in CRO |
| Non-copy paraphrase categories can remain not measured | ✓ (state_literal / binary_composition / fractal / meta_logic = 0 — as designed) |

This is the v7 finding: **STAGE_VAR works on real v1c. OMEGA suffix doesn't.** Reason is a tokenizer-alignment property of the v1c BPE, not a code bug — pre-flagged when we probed the tokenizer.

## 10 architectural checks (all PASS, copy now LIVE)

| # | Check | Result |
|---|---|---|
| 1 | Real-size model on cuda:0 | PASS — 55.35M params |
| 2 | Shape contracts at d_model=384 | PASS — source_hidden (21, 32, 384), p_copy (21, 192, 32) |
| 3 | Simplex invariants | PASS — min_p = 0.00731, rows sum to 1 |
| 4 | Device + dtype contracts | PASS |
| 5 | Param count in budget | PASS — 55.351M (target 55.5M ±5M) |
| 6 | No NaN/Inf | PASS — total = 19.33, all losses finite |
| 7 | Gradient flow both paths | PASS — enc 9.05, dec 44.77 |
| 8 | Memory + wall-clock | PASS — 4.45 GB peak, 0.68 s step |
| 9 | train_progress fields emit | PASS |
| **10** | **L_copy LIVE on real corpus** | **PASS — copy_valid_count = 56 (was 0 in v6)** |

## Loss decomposition

| Term | Value | Status | Note |
|---|---|---|---|
| L_LM | 10.725 | LIVE | unchanged |
| L_FR | 4.740 | LIVE | unchanged |
| L_slot_type | 2.125 | LIVE | unchanged |
| **L_copy** | **3.488** | **LIVE** | new — was 0.0 in v6 |
| L_phrase_bias_aux | 0.000 | PLACEHOLDER | unchanged |
| L_total | 19.334 | — | up from 17.58 in v6 (the +1.75 is the new L_copy contribution × weight 0.5) |

## Per-category breakdown

| Category | records | src_slot_histogram | copy_valid_count |
|---|---|---|---|
| **rpm_chain** | 3 | DOMAIN_LETTER: 3, **STAGE_VAR: 56** | **56** ✅ |
| recipe | 3 | DOMAIN_LETTER: 6, REGISTER_LETTER: 1 | 0 |
| fractal | 3 | (none) | 0 |
| meta_logic | 3 | (none) | 0 |
| cross_register_omega | 3 | DOMAIN_LETTER: 3, OMEGA: 2, REGISTER_LETTER: 7 | 0 |
| state_literal | 3 | DOMAIN_LETTER: 3, DRIVE_LETTER: 3, REGISTER_LETTER: 1 | 0 |
| binary_composition | 3 | DOMAIN_LETTER: 4 | 0 |

The 56 STAGE_VAR slots come from 3 rpm_chain records × ~3 stage variables per record × ~6 subtokens per identifier. The multi-token-span exact match works.

## Why OMEGA suffix didn't fire on recipe/CRO

The v1c tokenizer is **path-dependent**:

```
'Ω_translation_59' → ['<CHAR:03A9>', '<CHAR:005F>', '<CHAR:0074>', '<CHAR:0072>',
                      '<CHAR:0061>', '<CHAR:006E>', '<CHAR:0073>', '<CHAR:006C>',
                      '<CHAR:0061>', '<CHAR:0074>', '<CHAR:0069>', '<CHAR:006F>',
                      '<CHAR:006E>', '<CHAR:005F>', '<CHAR:0035>', '<CHAR:0039>']
                      # all-char-decomposed (16 tokens)

'translation_59'   → ['t', 'ran', 's', '<CHAR:006C>', '<CHAR:0061>', '<CHAR:0074>',
                      '<CHAR:0069>', '<CHAR:006F>', '<CHAR:006E>', '<CHAR:005F>',
                      '<CHAR:0035>', '<CHAR:0039>']
                      # BPE-merged 't', 'ran', 's' then char-decomposed (12 tokens)
```

When `Ω_` precedes `translation_59`, the tokenizer falls back to char-by-char after Ω. When `translation_59` appears standalone, the BPE merges `t`/`ran`/`s` first. So the source's 14-char suffix sequence does NOT appear as a subsequence anywhere in the target's BPE-tokenized reply.

This is the user's explicitly-acknowledged risk:

> "Again, only if token alignment is clean enough to map target subtokens to source subtokens."

It's not clean for this corpus's Ω-name pattern. The exact-subseq match correctly skips the case (no fuzzy match, per scope).

For reserved Ω names (`Ω_resolve`, `Ω_grounding`, etc.), the source tokenizes as single tokens but v1c replies still paraphrase — so the single-token classifier from v5 also doesn't fire (0 of 2 OMEGA-classified source tokens in CRO produced a copy match).

## What this means for Stage 7

Two empirical realities:

1. **STAGE_VAR copy IS load-bearing on rpm_chain** — and likely on `rpm` category (323 records in v1c) too. ~56 slots from 3 records suggests ~6,000 slots per epoch over the full v1c corpus.

2. **OMEGA copy is not viable on v1c as-shaped** — the corpus paraphrases Ω names and the tokenizer doesn't preserve subseq alignment for char-decomposed Ω prefixes.

The Stage 7 Q4 revised wording handles this gracefully: "If `copy_valid_count == 0` for the entire 1000-step run, treat Q4 as NOT MEASURED, not pass/fail." But across the full corpus, rpm_chain + rpm rows (323 + 425 ≈ 750 records out of 7395) will produce copy signal. The other ~90% of the corpus will be NOT MEASURED for copy — slot_type / LM / FR continue to train.

That's actually fine: Stage 7's Q4 only needs **above-random copy_argmax_acc on the steps where slots fire**. ~10% of steps having copy signal is enough to measure the head.

## Two decision paths for Stage 7

**A. Proceed to Stage 7 with STAGE_VAR-only copy.** Accept that OMEGA / DOMAIN / DRIVE / REGISTER won't fire on real v1c. Q4 measures on the rpm/rpm_chain batches only. Risk: 90% of Stage 7 steps will be Q4-NOT-MEASURED.

**B. Add OMEGA re-tokenization workaround** (the "Option 2A" I described earlier): when source has a char-decomposed Ω_X span, extract the suffix string `X`, re-tokenize `X` standalone, then search for the *re-tokenized* sequence in target. If found, map all K target positions to the *same* source position (the start of the suffix span). Trades 1:1 source-target alignment for many-to-one alignment.

The user said: "exact multi-token span match, source and target must tokenize compatibly. ... No fuzzy matching." A many-to-one mapping is technically not "fuzzy" (it's exact subseq match in target space, just with collapsed source pointers). But it does violate the literal 1:1 alignment described.

This is a user decision.

## Resource consumption

- **GPU memory peak:** 4.45 GB (unchanged from v6)
- **Wall-clock per step:** 0.68 s (slightly up from 0.58 s — STAGE_VAR span scanning adds ~20% overhead per record)
- **Pod cost for v7:** < $0.05 spot
- **Cumulative Stage 6 spend (v2 + v3 + v4 + v5 + v6 + v7):** < $0.30 spot

## Companion artifacts (this commit)

- `noetic-compass-scaffold/noetic-compass/cas-native/training/datasets/simplex_collator.py` — `find_stage_var_spans`, `find_omega_suffix_spans`, `find_subsequence`, `_is_identifier_continuation` helpers + `_derive_anchors` wiring
- `noetic-compass-scaffold/noetic-compass/cas-native/tests/training/test_simplex_collator.py` — 11 new helper tests
- `docs/working/simplex_mvp_stage6_v7_stagevar_omega_2026_05_11.md` — this report
- `docs/working/simplex_mvp_stage6_v7_stagevar_omega_report_2026_05_11.json` — machine-readable

Pod artifact: `/workspace/tksCAS/stage6_dry_run_v7_stagevar_omega_20260511T055048Z/`
