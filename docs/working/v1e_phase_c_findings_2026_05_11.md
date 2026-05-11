# v1e Phase C — Findings (kill-switch tripped, v1e ended)

**Date:** 2026-05-11
**Status:** v1e Phase C killed by 24-pack regression gate. v1e exhausted; pivoting to simplex Δ°₃₉ rebuild.
**Artifacts:** archived checkpoint at `D:\tksCAS-archive\v1e_phase_c\v1e_phase_c_aux_1ep_20260511T014257Z\` with `NEGATIVE_RESULT.md`. 24-pack eval JSONL alongside.

## Key sentence

**v1e decode-side and small aux-head fine-tune interventions improved isolated structural signals, but failed product-level generation and regressed v0 behavior.**

## What v1e tried (3 sub-phases, all archived as evidence)

| Phase | Lever(s) | Result |
|---|---|---|
| **Phase 1B (#134)** | Phrase-trie + state-machine constrained decoder, leaf-exit boundary, first-n comparator | Slot-commits 35/35; first-n 33/35; full seq-match 0/35. Decode-side ceiling. |
| **β2 (#139)** | EOS bias 5/8/10; length cap 12n+8 | Best case 5/35 full seq-match at eos_bias=10, but the wins were FRAGMENTS ("averse in muscle memory " — no period). Length cap truncated 19/35. Decode-side levers saturated. |
| **Phase C (#141)** | Aux heads (H_card / H_pos / H_stop / H_cluster) attached to encoder pool + decoder hidden; 1-epoch fine-tune from v1c | 24-pack regressed 18/24 → 12/24. Kill-switch tripped. |

## C 24-pack grading (sample-read against targets, per record)

Read against the v0-rc1 baseline at `v1_eval_pack_24records_20260510T072551Z_CODEX_GRADED.md` (18/24 acceptable+):

| # | Cat | v1c band | **C band** | Δ | Note |
|---:|---|---|---|---|---|
| 1 | state_lit | green | green | = | identical to v1c |
| 2 | state_lit | green | green | = | identical |
| 3 | state_lit | wrong | wrong | = | "expressed in an embodied way, expressed in an embodied way" — doubled |
| 4 | binary | green | **yellow** | ↓ | "ABeing resonance" — broken opener token |
| 5 | binary | yellow | yellow | = | `->` rendered as "combined with" |
| 6 | binary | green | **yellow** | ↓ | adds extra ^3 "felt aversion" (not in source) |
| 7 | CRO | green | high yellow | ↓ | extra "a thought" prepended |
| 8 | CRO | yellow | **green** | ↑ | clean two-mode fusion, both registers right |
| 9 | CRO | yellow | yellow | = | wrong second register (T instead of f) |
| 10 | recipe | wrong | wrong | = | wrong noetics (^1 not ^3, ^0 not ^1) |
| 11 | recipe | yellow | **wrong** [TRUNC] | ↓ | hit max tokens, side-product Ω wrong |
| 12 | recipe | wrong | wrong | = | coef assignment crossed |
| 13 | fractal | wrong | wrong | = | different ^9-loop, still wrong |
| 14 | fractal | wrong | wrong | = | got ^3 opening but lost ^7 closing |
| 15 | fractal | yellow | **wrong** [TRUNC] | ↓ | "time paying attention" glitch + truncation |
| 16 | meta-logic | wrong | wrong | = | wrong first cluster (^4 vs ^5) |
| 17 | meta-logic | high yellow | **yellow** | ↓ | extra ^0 in cluster 1 |
| 18 | meta-logic | yellow | yellow | = | partial coverage |
| 19 | rpm_chain | yellow | **wrong** [TRUNC] | ↓ | "stageD3_3_0233333" (extra digits) + truncation |
| 20 | rpm_chain | yellow | **wrong** [TRUNC] | ↓ | stage var stalls, repeats |
| 21 | rpm_chain | high yellow | **wrong** [TRUNC] | ↓ | same stalling pattern |
| 22 | invalid_expl | yellow | yellow | = | similar |
| 23 | invalid_expl | green | green | = | identical |
| 24 | invalid_expl | green | green | = | identical |

**Tally:** green 5, high yellow 1, yellow 6, wrong/flop 12. Acceptable+ = **12/24**.

**Net movement vs v1c:** 1 record up (8), **8 records down** (4, 6, 7, 11, 15, 17, 19, 20, 21 — wait, that's 9 if I include 7 going from green→high yellow). Recounting: -1 from {4, 6, 17} (one band each), -2 from {7 went green→high yellow which is -1 band actually; 11, 15, 19, 20, 21 each went down ≥1 band to wrong/flop}. Net: 1 up, 8 down. **Acceptable+ delta: −6.**

## Damage signature (not random regression)

Three structural patterns the design doc's R2 risk register named ("1-epoch fine-tune destabilizes v1c content"):

1. **5/24 truncations** in long-output records (11 recipe, 15 fractal, 19/20/21 rpm_chain). v1c had 0 truncations. H_stop intended to teach "stop after N slots" appears to have done the opposite — the model now runs out of token budget before completing.
2. **Stage-variable copying broken** in rpm_chain (19, 20, 21). Model stalls on a single identifier, repeats it, fails to advance through let-bindings. v1c's identifier-copy path was clean.
3. **Token-level corruption** in records 4 ("ABeing") and 19 ("stageD3_3_0233333"). v1c had no such artifacts. Fresh-init aux-head gradients during the 2× ramp likely perturbed the embedding/decoding boundary.

## Telemetry health vs eval health — the audit point that stuck

The training run was healthy at the process level:
- LM loss stable 0.30–0.62, no spike or collapse
- All 4 aux losses fired per task as designed
- Curriculum ramp-DOWN verified at runtime (0.40 → 0.20 over the epoch)
- Interference monitor armed; did NOT fire (only reached 879/1000 steps)

But: `lm_over_aux_ratio` dipped below the 0.20 threshold three times in the first 13 steps (8791: 0.15; 9000: 0.13; 9050: 0.23). Those moments coincided with fractal/meta-logic batches and are likely where the LM head was perturbed before the curriculum could decay aux α.

**Loss curves are not model-quality. Eval is.** The training looked clean; the model regressed.

## Why decode-time levers and training-side levers BOTH failed

The structural insight that survives v1e:

**The v0 model's prose distribution emits noetic indicators densely in connective tissue.** Closing prose like "...and finally muscle memory took over" adds ^7 (muscle memory) to the extracted sequence. Trailing prose IS structurally identical to sentence-closing prose; suppressing one suppresses the other.

- Decode-side levers tried to mask logits at slot boundaries (Phase 1B/β2). Worked at slot-commit level (35/35) but couldn't separate slot phrases from connective-tissue noetics without producing fragments.
- Training-side levers tried to teach the model to know K + position + when-to-stop via aux supervision (Phase C). Aux heads attached to encoder pool can predict K + position FROM THE FROZEN POOL, but training them END-TO-END perturbs the very prose distribution they're trying to constrain. The encoder pool is shared with the LM head; gradients flow.

Both routes confirm: **the v0 checkpoint's prose distribution is the binding constraint.** Reshaping it from outside (decode) or with small fine-tunes (Phase C) doesn't work without breaking what v0 does well.

## v1e is exhausted

Per the v1e design doc's heuristic exit criteria + the user's stop-and-surface verdict 2026-05-11:

> "If C regresses the 24-pack or fails fractals, stop v1e and pivot simplex."

Kill-switch tripped. v1e ends here.

## What remains canonical

- **v0-rc1** stays the deployed product. `apply_fractal_decoder=False`. Tag at commit `255b2a7`. SHA-pinned checkpoint at `D:\tksCAS-archive\v0_rc1\v1c_VALIDTOK_5ep\`.
- **v0-canary** stays the regression gate for any future PR to `cas-native/inference/**` or `cas-native/model/**`. Last canary pass: 24/24 byte-match after the Phase C `strict=False` patch to `v1_eval_pack_24records.py`.
- **G_baseline** (Phase 1B opt-in shadow mode) lives in code as `apply_fractal_decoder=True + first_n_mode=True + leaf_exit_boundary=True`. **NOT promoted** to production default per the user's β2 verdict.
- **Phase C checkpoint** lives at `D:\tksCAS-archive\v1e_phase_c\v1e_phase_c_aux_1ep_20260511T014257Z\` with `NEGATIVE_RESULT.md`. **NOT promoted.** Available for diagnostic comparison (e.g., what did H_stop actually learn vs what damaged the LM head?), but its outputs are not product-quality.

## What's next

**Simplex Δ°₃₉ rebuild.** Plan-mode doc to follow at `docs/working/simplex_rebuild_plan_2026_05_11.md`. Per user 2026-05-11:

> "First produce a simplex rebuild plan that maps: what v0 proved, what v1d/v1e failed, which failure modes simplex is supposed to solve, what minimum viable simplex checkpoint would look like, how CABS/geodesic memory plugs in later."

Not implementation yet — plan first, then user-gated execution.

## Evidence the experiments DID their job

- v1d: empirically killed "more SDG / cleaner corpus / one-more-epoch" as the lever (Tasks #128-#132).
- v1e Phase 1B / β / β2: empirically killed "decode-time levers can close the fractal-rendering gap on v0 prose distribution" (Tasks #134/#138/#139).
- v1e Phase C: empirically killed "small aux-head fine-tune from v1c can close the gap without regressing v0 content" (Task #141).

Three cheap paths killed with evidence. The remaining architecture-level intervention is simplex. The experiments narrowed the problem and ruled out the easy escapes.
