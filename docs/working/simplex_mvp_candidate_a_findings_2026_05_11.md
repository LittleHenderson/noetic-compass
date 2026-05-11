# Candidate A — Findings (FALSIFIED at Criterion 1)

**Date:** 2026-05-11
**Run dir:** `/workspace/tksCAS/stage7_candidate_a_untied_20260511T130552Z/`
**Single delta vs diagnostic:** `--no-tie-lm-head` (lm_head.weight no longer shared with token_emb.weight)
**Verdict:** **FALSIFIED at Criterion 1 (Teacher-forced canary).** Per locked anti-tuning rule: **do not tune A; move to C.**

## TL;DR

Untying lm_head from token_emb made things **dramatically worse**, not better:
- TF top-1 acc dropped 0.597 → **0.114** (5× worse)
- TF mean_loss_lm rose 2.27 → **5.58** (2.5× worse)
- canonical_stage_var_recovery stayed at 0/4
- Copy loss at valid positions exploded 0.04 → **8.83**

The "all clean" canary ablation verdict (11/0/0 across all 4 modes) is a **degeneracy artifact**: the model emits trivial outputs like `"   stage"` or empty strings, too short to trigger the damage detector's signatures.

## Criterion 1 — Teacher-forced canary (FAIL)

| Metric | Diagnostic | Candidate A | Required | Status |
|---|---|---|---|---|
| mean_loss_lm | 2.27 | **5.58** | materially lower | **FAIL** |
| mean_argmax_top1_acc | 0.597 | **0.114** | materially > 0.597 | **FAIL** |
| canonical_stage_var_recovery | 0/4 | **0/4** | > 0/4 | **FAIL** |
| n_records_with_argmax_loop | 5 | 4 | meaningful drop | partial (only 1) |
| mean_loss_copy_at_valid | 0.0385 | **8.83** | — | (exploded) |

**Two gating sub-criteria fail outright. A is falsified at Criterion 1.** Per locked judgment order, evaluation stops here.

### Per-record TF results

| Record | Category | loss_lm | top1 acc | argmax loop |
|---|---|---|---|---|
| canary_rpm_chain_001 | rpm_chain | 6.264 | **0.023** | False |
| canary_rpm_chain_002 | rpm_chain | 6.369 | **0.045** | False |
| canary_fractal_k7_001 | fractal_sequence | 6.274 | 0.108 | False |
| canary_fractal_k8_001 | fractal_sequence | 6.290 | 0.068 | False |
| canary_recipe_001 | recipe | 5.331 | 0.079 | True |
| canary_meta_logic_001 | meta_logic | 5.316 | 0.143 | True |
| canary_state_literal_001 | state_literal | 4.925 | 0.080 | False |
| canary_binary_001 | binary_composition | 4.550 | 0.222 | False |
| canary_cro_001 | cross_register_omega | 5.540 | 0.067 | True |
| canary_invalid_001 | fractal | 4.861 | 0.250 | True |
| canary_invalid_002 | fractal | 5.647 | 0.171 | False |

Even the easiest record (state_literal, which scored 0.92 top-1 under tied baseline) now scores 0.08 — a 91-point drop.

## Side-by-side TF argmax (rpm_chain)

| Record | Target | Diagnostic argmax | Candidate A argmax |
|---|---|---|---|
| 001 | "Let stageA0_5_0296 name a foundational thought, stageD5_5_0296…" | `"The stageA0_0_023 name a thought thought, stageD7_0_02 name name something a a"` | **`"   stage"`** |
| 002 | "Let stageA0_4_0049 name a foundational thought, stageD4_4_0049…" | `"Let stageA0_0_020 name a thought thought, stageD7_0_033 name name something a a judgment"` | **`"   stage"`** |
| fractal_k7 | "A seven-step fractal sequence…" | `"The thought in the the of a a number number, and and…"` | **`""` (empty)** |

The diagnostic produced kill-grade text but **text of substance**. Candidate A produces trivial / empty output, fooling the damage detector.

## Why the canary ablation verdict (11/0/0) does NOT validate

The damage detector's "clean" verdict requires severity < 1.0. For empty or extremely short outputs (e.g. `"   stage"`):
- Repeat-loop detector: needs ≥ 3 consecutive tokens — fails on length
- Truncation detector: fires only with content ending mid-clause — no content
- Stage var corruption: needs canonical-looking patterns to corrupt — no patterns
- Notation leak: needs CAS chars in fluent prose — no prose
- Generic collapse: needs ratio < 0.25 of target — fires technically (`"   stage"` is < 0.05 of target length), but only adds +0.5 severity which doesn't push to "kill"
- Camel fusion: needs alphanumeric tokens — no text

Result: severity stays under 1.0 → verdict "clean" → pack verdict "clean" across all 4 modes.

This is the user's exact warning manifest: *"different failure texture at the same severity is falsification, not recovery."* Candidate A changed the texture (trivial output instead of looping output) but did not recover.

## Hypothesis update

Untying the lm_head **made things worse**. Three possibilities, all interesting:

1. **The tying was helpful, not harmful.** Sharing weights with the input embedding manifold gave the lm_head a sensible inductive bias. Without that bias, the lm_head has 14.9M extra parameters that 1000 steps can't fit. (The optimizer state for the untied path is ~6M extra Adam moments to track.)
2. **The failure mode is deeper than the lm_head's parameterization.** Both tied (loops) and untied (empty/trivial) are manifestations of the lm_head failing to learn a coherent emission distribution under joint loss with copy / FR / slot. Whether lm_head shares weights with token_emb doesn't address the underlying problem.
3. **Optimization issue specific to untied.** 14.9M cold-init parameters joining the optimization at step 0 may need lower lr / warmup / different init scheme. But per the anti-tuning rule, we don't pursue this — pursuing it = "tune A."

## Per anti-tuning rule

> "If A fails, do NOT tune it. Move to C."

No more A. No retuning. No "let me try a smaller lr." No "let me try GPT-2 init for the new lm_head." The diagnostic plus Candidate A together provide enough information to move to Candidate C with stronger conviction:

**Candidate C (hard typed-fiber emission route) is now the right next move.** Both the diagnostic and Candidate A show that the soft-gate competition between lm_head and copy_head is destructive regardless of whether the heads share weights. Hard architectural separation may be required.

## Resource cumulative

| | |
|---|---|
| Diagnostic replay + analyses | ~$0.44 |
| Candidate A replay + analyses | ~$0.44 |
| **Cumulative simplex MVP pod spend** | **~$2.09 of $60 budget** |

v0-rc1 stays canonical. Research-track only.

## Companion files

- `docs/working/candidate_a_smoke_report_2026_05_11.json` — Candidate A's full smoke report (8 scalar gates + canary_history)
- `docs/working/candidate_a_tf_canary_report_2026_05_11.json` — Analysis A (TF eval)
- `docs/working/candidate_a_decode_ablations_2026_05_11.json` — Analysis C (4-mode ablation)
- `docs/working/candidate_a_per_token_trace_2026_05_11.json` — Analysis B (per-token)
- `docs/working/simplex_mvp_diagnostic_replay_findings_2026_05_11.md` — baseline comparison
- Pod artifacts in `/workspace/tksCAS/stage7_candidate_a_untied_20260511T130552Z/` (5 checkpoints × 804 MB + 4 JSONs)
