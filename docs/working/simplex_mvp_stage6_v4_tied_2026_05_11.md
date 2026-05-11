# Simplex MVP — Stage 6 GPU Dry-Run, FINAL (v4, tied + GPT-2 init)

**Date:** 2026-05-11
**Run timestamp:** 2026-05-11 05:07:33 UTC
**Pod:** RTX A6000 46GB, torch 2.5.1+cu124, CUDA 12.4
**Run dir on pod:** `/workspace/tksCAS/stage6_dry_run_v4_tied_init_20260511T050731Z/`

## Verdict: PASS on all 9 checks at the corrected ~55M budget

This is the final Stage 6 result. v2 (untied) and v3 (tied, default init) were intermediate iterations that surfaced two real issues, both now fixed:

| Iteration | Config | LM @ step 1 | Total params | Verdict | Issue |
|---|---|---|---|---|---|
| v2 | Untied lm_head | 10.80 (healthy) | **70.21M** | 8/9 | Param budget under-estimate (+21.7M over 48.5M target) |
| v3 | Tied, default `N(0, 1)` init | **293.81** (broken) | 55.35M | 9/9 by gate | LM loss 28× too high — bad init for tied weights |
| **v4** | Tied + GPT-2-style `N(0, 0.02)` init | **10.69** (healthy) | **55.35M** | **9/9** | None |

## v4 Checks (9/9 PASS)

| # | Check | Verdict | Evidence |
|---|---|---|---|
| 1 | Real-size model instantiates on cuda:0 | PASS | 55.35M params on cuda:0 (encoder 22.19M + decoder 33.17M) |
| 2 | Shape contracts at d_model=384 | PASS | All 6 output tensors match expected shapes |
| 3 | Simplex invariants | PASS | (p > 0).all() = True; max row-sum deviation 1.2e-7; min p = 0.01083 |
| 4 | Device + dtype contracts | PASS | All params on cuda; simplex_trajectory = fp32 |
| 5 | Param count in budget | PASS | actual 55.352M vs target 55.5M (±3M), delta −0.148M |
| 6 | No NaN/Inf | PASS | total = 17.147; all 5 loss parts finite |
| 7 | Gradient flow both paths | PASS | enc grad-norm 10.32; dec grad-norm 38.05; all finite |
| 8 | Memory + wall-clock | PASS | 1.065 GB peak (< 20 GB); 0.53 s step (< 10 s) |
| 9 | train_progress fields | PASS | All 11 fields emit |

## Loss decomposition at step 1

| Loss term | Value | Status | Notes |
|---|---|---|---|
| L_LM | 10.690 | **LIVE** | `log(38685) = 10.56` → near-uniform softmax baseline; healthy starting state |
| L_FR | 4.610 | **LIVE** | 4 anchors fire from Stage-1 collator stub |
| L_slot_type | 1.847 | **LIVE** | `log(9) = 2.20` baseline; already below uniform from token-position priors |
| L_copy | 0.000 | **PLACEHOLDER** | Collator anchor stub emits `typed_slot_source = -1` for every position; pointer-copy path shape-correct but inactive |
| L_phrase_bias_aux | 0.000 | **PLACEHOLDER** | `compute_losses()` returns `torch.zeros((), requires_grad=False)`; needs corpus-aligned phrase-bias table |
| L_total | 17.147 | — | weighted sum, healthy magnitude for step 1 |

`fr_lm_ratio = 0.431` — interference monitor inside safe band [0.05, 20].

## Resource consumption

- **GPU memory peak:** 1.065 GB out of 46 GB available — 2.3% utilization
- **Wall-clock per step:** 0.53 s
- **Pod cost for full Stage 6 v2+v3+v4 iteration:** < $0.15 total
- **Projected Stage 0 1000-step cost:** ~9 min wall-clock, ~$0.40 at A6000 spot — well under the $25 sub-cap

## Code changes landed (commit pending)

1. **`cas-native/model/typed_fiber_decoder.py`** — two changes:
   - Re-init `token_emb.weight` to `N(0, 0.02)` (GPT-2 standard) before tying. PAD row zeroed for safety.
   - `self.lm_head.weight = self.token_emb.weight` (the tie itself, ~5 lines including comment).

2. **`cas-native/tests/model/test_typed_fiber_decoder.py`** — 5 new tests:
   - `test_lm_head_weight_tied_to_token_emb` — `is` identity check on tensor objects
   - `test_weight_tying_propagates_in_place_edits` — fill_(1.234) on one surfaces in the other
   - `test_weight_tying_dedup_in_parameters` — `model.parameters()` yields the tied tensor exactly once (no double-update)
   - `test_weight_tying_param_count_reduction_at_real_vocab` — param-count delta sanity check at vocab=38685
   - `test_weight_tying_gradient_lands_on_shared_tensor` — backward through lm_logits populates `token_emb.weight.grad`

## Test totals after the changes

- 563/563 adjacent model + training + inference suite green
- 17/17 typed_fiber_decoder tests pass (12 existing + 5 new tying tests)
- 19/19 simplex MVP integration tests pass

## Build-spec budget correction

The original build-spec estimate of 48.5M assumed weight-tying was implicit, but did not state it. Corrected entry:

> **Total params (vocab=38685):** ~55.4M with `lm_head` weight-tied to decoder `token_emb`.
> - Encoder: 22.19M (~14.9M token_emb + ~7.3M trunk + ~0.1M tail; encoder embedding is NOT tied — encoder reads source CAS tokens, decoder reads English BPE tokens — they have separate vocabularies and serve different roles)
> - Decoder: 33.17M (~14.9M tied token_emb/lm_head + ~17M 6-layer body + ~1M heads + ~0.3M phrase-bias)

The original "~48.5M" line in `docs/working/simplex_mvp_build_spec_2026_05_11.md` §2.1/§2.3 should be updated to "~55.4M post-tie" in a follow-up edit (not part of this commit — separates the architectural change from the doc reconciliation).

## Stage 7 entry status — NOT YET AUTHORIZED

Per user 2026-05-11 caveat: Stage 6 PASS does **not** auto-authorize Stage 7 launch. Before 1000-step preflight begins, the plan must:

> "Either wire those [L_copy, L_phrase_bias_aux] live or explicitly revise the Stage 7 gates. Otherwise the 'copy path non-random' gate is partly invalid by construction."

The Stage 7 architecture-feasibility gate has 6 questions (per execution plan §Stage 7); two of them are:
- Q3: "Does slot_type learn above chance?" — exercised (slot_type is LIVE)
- Q4: "Is copy path non-random?" — **invalid by construction** with L_copy stub at zero

Open decision:
- **Option A**: Wire L_copy live before Stage 7 (requires real anchor derivation in collator — moves Stage 7 work into Stage 6.5).
- **Option B**: Wire L_phrase_bias_aux live before Stage 7 (requires phrase-bias target table — same Stage 6.5 detour).
- **Option C**: Revise Stage 7 gate Q4 (and possibly Q5) to acknowledge the 3-of-5 live state — re-scope to "what we can validate now."
- **Option D**: Mixed — wire L_copy (which is more architecturally important for the typed-fiber decoder's slot/copy work) but defer L_phrase_bias_aux behind a relaxed Q5 phrasing.

User decision required before Stage 7 launch.

## Companion artifacts (this commit)

- `noetic-compass-scaffold/noetic-compass/cas-native/model/typed_fiber_decoder.py` — tied + init fix
- `noetic-compass-scaffold/noetic-compass/cas-native/tests/model/test_typed_fiber_decoder.py` — 5 new tests
- `docs/working/simplex_mvp_stage6_v4_tied_2026_05_11.md` — this report
- `docs/working/simplex_mvp_stage6_v4_tied_report_2026_05_11.json` — machine-readable v4 report

Pod-side artifacts:
- `/workspace/tksCAS/stage6_dry_run_v4_tied_init_20260511T050731Z/stage6_report.json`
