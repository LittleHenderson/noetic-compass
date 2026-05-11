# Simplex MVP — Diagnostic Replay Findings

**Date:** 2026-05-11
**Run dir:** `/workspace/tksCAS/stage7_diagnostic_replay_20260511T113303Z/`
**Replay duration:** 49 min (config matches v7.1b: batch_size=16, d_model=384, 4/6 layers, 6/6 heads, lr 1e-4, ablation full, 1000 steps, seed 1729)
**Verdict per user decision standard:** **Rule 3 fires + Rule 4 corroborates ⇒ Pause for architectural review.**

## TL;DR

The simplex MVP's decoder/LM head has a structural problem that:

- **Is NOT exposure bias** (Rule 1 ruled out): teacher-forced canary loops 45% of records, top-1 acc 59.7%, canonical stage var recovery 0/4.
- **Is NOT copy-path destabilization** (Rule 2 ruled out): `copy_disabled`, `phrase_bias_disabled`, `lm_only`, and `full` produce **identical** damage profiles (2 clean / 5 warn / 4 kill each).
- **IS a decoder/LM head architecture problem** (Rule 3 fires): even with all auxiliary paths disabled, the lm_head produces loops.
- **Slot gate collapses to CONNECTIVE** (Rule 4 corroborates): rpm_chain_001 shows slot 0 for all 128 generated positions; rpm_chain_002 shows brief STAGE_VAR activation (positions 2–11) then collapse.

Per locked decision standard (`project_simplex_diagnostic_decision_standard_2026_05_11.md`): *"Greedy decode + label smoothing + temperature won't save it."*

## Analysis A — Teacher-forced canary

| Metric | Value |
|---|---|
| mean_loss_lm | 2.27 (nearly identical to greedy 2.14) |
| mean_argmax_top1_acc | **0.597** |
| n_records_with_argmax_loop | **5 / 11** |
| canonical_stage_vars_in_targets | 4 |
| canonical_stage_vars_in_argmax | **0** |
| canonical_recovery_rate | **0.0** |
| mean_loss_copy_at_valid | 0.0385 |
| records_with_valid_copy | 2 |

### Per-record TF results

| Record | Category | TF loss_lm | TF top-1 acc | TF argmax loops |
|---|---|---|---|---|
| canary_rpm_chain_001 | rpm_chain | 1.632 | 0.659 | False |
| canary_rpm_chain_002 | rpm_chain | 1.440 | 0.682 | False |
| canary_fractal_k7_001 | fractal_sequence | 3.861 | 0.459 | True (3) |
| canary_fractal_k8_001 | fractal_sequence | 4.120 | 0.341 | False |
| canary_recipe_001 | recipe | 1.971 | 0.658 | False |
| canary_meta_logic_001 | meta_logic | 2.504 | 0.500 | True (3) |
| canary_state_literal_001 | state_literal | 0.368 | **0.920** | False |
| canary_binary_001 | binary_composition | 1.146 | 0.778 | True (3) |
| canary_cro_001 | cross_register_omega | 3.000 | 0.433 | False |
| canary_invalid_001 | fractal (invalid) | 2.630 | 0.525 | True (5) |
| canary_invalid_002 | fractal (invalid) | 2.350 | 0.610 | True (3) |

**state_literal is the only category where TF performs well (92% top-1, low loss).** That's the simplest pattern in the corpus — a single CAS state mapping to a single sentence. Everything more structured falls apart.

### Side-by-side TF samples

```
canary_rpm_chain_001:
  target:   "Let stageA0_5_0296 name a foundational thought, stageD5_5_0296 name practiced rhythm with agency."
  argmax:   "The stageA0_0_023  name a thought thought, stageD7_0_02   name name something a a"

canary_rpm_chain_002:
  target:   "Let stageA0_4_0049 name a foundational thought, stageD4_4_0049 name what triggered an evaluative judgment."
  argmax:   "Let stageA0_0_020 name a thought thought, stageD7_0_033 name name something a a judgment"

canary_fractal_k7_001:
  target:   "A seven-step fractal sequence starting from the universal idea, progressing through awareness, attraction, and resonance."
  argmax:   "The thought in the the of a a number number, and  and number, and  and and"
```

Even under teacher-forcing, the LM emits malformed stage var identifiers (digits in wrong positions, missing segments) and loops on filler ("the the", "and and", "a a"). **The model never learned to produce the right tokens** — TF just hides the catastrophe partially.

## Analysis C — Decode-time ablations (all 4 modes identical)

| Mode | Clean | Warn | Kill | Mean severity |
|---|---|---|---|---|
| full | 2 | 5 | 4 | (kill) |
| lm_only | 2 | 5 | 4 | (kill) |
| copy_disabled | 2 | 5 | 4 | (kill) |
| phrase_bias_disabled | 2 | 5 | 4 | (kill) |

**Identical damage profiles across all four modes.** Disabling copy, phrase-bias, or both does nothing. The lm_head produces the loops on its own.

## Analysis B — Per-token greedy trace (rpm_chain)

### canary_rpm_chain_001

Generated text starts: `"The expression tries to to multiply two two two two multiplion only of of two two two states of two two states..."`

- **Slot type distribution across 128 generated tokens: slot 0 (CONNECTIVE) = 128/128 (100%)**
- LM entropy bimodal: min 0.07 nats (peaky on space/filler), max 7.3 nats (uniform across vocab on content positions), mean 3.34
- Copy_argmax cycles 2→11→21→22→9→8 rapidly — copy head is unstable and unrelated to lm output
- ngram_repeat_count fires by position 8

**Slot gate collapsed entirely.** The phrase-bias gate (which fires only on NOETIC_PHRASE = slot 8) NEVER triggers because slot_type always argmaxes 0.

### canary_rpm_chain_002

Generated text starts: `"Let stageA0_0_023 name a thought in the arena with a stageD7_02 name a name a thought..."`

- Slot type: 111 × CONNECTIVE + **17 × STAGE_VAR** (positions 2–11 during the brief identifier-generation period)
- Mean LM entropy 2.71 (a bit lower than rec 1)
- During the STAGE_VAR span (positions 2–11), slot_argmax = 2 with confidence 0.91–0.99 AND copy_argmax tracks tightly through source positions 2→3→4→5→6 — the model DOES briefly behave correctly

**This is the most diagnostic-rich finding.** The architecture CAN produce span-coherent stage variable generation for ~10 tokens, with both the slot gate and copy head firing correctly. But:

- The generated identifier is *wrong* (`stageA0_0_023` vs target `stageA0_4_0049`) — the copy head is consistent, but it's pointing at the wrong source positions
- After position 11, the slot gate collapses to CONNECTIVE and the model degenerates into repetition
- The model couldn't extend coherent generation beyond ~10 tokens

## Why the four ablations are identical

The model's lm_head produces the same wrong distribution at decode-time **regardless of which auxiliary path is enabled**, because:

1. The lm_head's weights were learned under the joint loss with copy gradient pulling decoder hidden states toward source-position prediction
2. The lm_head + token_emb are tied (weight-sharing), so any copy gradient that flows through token_emb backwards-affects the lm_head's emission distribution
3. By 1000 steps, the lm_head has internalized a degenerate distribution that doesn't depend on the runtime copy/phrase-bias/slot gating

Turning off the auxiliary paths at decode time can't un-train the lm_head. The damage is in the weights, not in the inference path.

## Decision per locked standard

| Rule | Status | Action |
|---|---|---|
| Rule 1: TF clean + greedy bad → exposure bias | NOT FIRING | — |
| Rule 2: `copy_disabled` cleaner → copy destabilizing | NOT FIRING | — |
| **Rule 3: lm_only bad → decoder/LM head architecture problem** | **FIRES** | **Pause for architectural review** |
| **Rule 4: Slot always CONNECTIVE** | **FIRES** (rec 1) / **PARTIAL** (rec 2) | Slot gate needs supervision / weight inspection |
| Rule 5: All modes bad but severity improves | NOT primary | — |

Per the locked standard: **pause for architectural review.** Greedy-decode tweaks, scheduled sampling, label smoothing, temperature, ablation grid — none of these address an lm_head that produces degenerate output even with truth prefix. Stage 7-bis is the wrong move.

## What the architectural review should consider

Not for this commit to decide — surfacing for the next conversation:

1. **Untie lm_head from token_emb.** The tying was done to save 14.9M params (Stage 6 v4). The diagnostic shows the lm_head needs to be free to learn an emission distribution independent of the input embedding geometry.
2. **Drop the typed-fiber decoder's joint training of copy + lm.** The two heads' gradients are antagonistic. Either:
   - Train lm-only first, then bolt on copy as a post-training fine-tune
   - Or use a hard gate (slot_type predicts copy-eligible → emit from copy; else → emit from lm), not a soft mix
3. **Question the v1c paraphrastic corpus fit for this architecture.** Four consecutive failures (Phase C, v1d, v1e Phase 1B, v7.1b/diagnostic) on the same model shape against the same corpus shape suggests the corpus may be the wrong training signal for a pointer-generator decoder. Path D Wave 3 (NL annotation pipeline) was already paused; this may belong to a re-launch of that work.
4. **The 95% copy_argmax_acc was misleading.** It measured "model points at the right source position with 95% confidence", which sounds like learning. But the decode-time output shows the lm_head doesn't translate that into coherent emission. The training metric did not predict the eval behavior.

## v0-rc1 stays canonical

Per user 2026-05-11: research-track only. No simplex MVP artifact is promoted.

## Companion files

- `docs/working/simplex_mvp_diagnostic_replay_smoke_report_2026_05_11.json` — same 8 scalar gates as v7.1b
- `docs/working/diagnostic_replay_tf_canary_report_2026_05_11.json` — Analysis A full per-record
- `docs/working/diagnostic_replay_per_token_trace_2026_05_11.json` — Analysis B per-token detail
- `docs/working/diagnostic_replay_decode_ablations_2026_05_11.json` — Analysis C 4-mode side-by-side
- `docs/working/simplex_mvp_stage7_v7_1b_postmortem_2026_05_11.md` — what we were diagnosing
- `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/run_v7_postmortem_analyses.py` — single script that runs all 3 analyses given a saved checkpoint
- Pod artifacts in `/workspace/tksCAS/stage7_diagnostic_replay_20260511T113303Z/`: 5 checkpoints (634 MB each) + the 4 JSON reports

## Total spend

| Item | Time | Cost |
|---|---|---|
| Diagnostic replay (1000 steps + canary + checkpoints) | 49 min | ~$0.41 |
| 3 analyses on saved checkpoint | ~3 min | ~$0.03 |
| **This investigation** | **~52 min** | **~$0.44** |
| Cumulative simplex MVP pod spend | (all stages) | **~$1.65 of $60 budget** |
