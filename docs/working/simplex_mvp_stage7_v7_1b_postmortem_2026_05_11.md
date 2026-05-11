# Stage 7 v7.1b post-mortem — canary veto trips despite scalar PASS

**Date:** 2026-05-11
**Run timestamp:** 2026-05-11 08:01–08:47 UTC
**Pod:** RTX A6000, run dir `/workspace/tksCAS/stage7_v7_1b_canary_20260511T080149Z/`
**Verdict:** **Stage 7 FAILS** — all 8 scalar gates PASS but canary pack verdict is `kill` at every checkpoint per the v7.1 sample veto.

## Headline

`copy_argmax_acc = 0.9498` during teacher-forced training. Zero canonical stage variables produced during greedy decode.
That gap is the failure.

## Scalar gates (8/8 PASS)

| Gate | Result |
|---|---|
| no_nan_inf | PASS |
| simplex_min_above_floor | PASS |
| entropy_does_not_collapse | PASS |
| lm_does_not_explode | PASS |
| lm_decreasing | PASS |
| fr_finite_and_directional | PASS |
| gradients_flow_both_paths | PASS |
| q4_stage_var_copy | PASS — all 4 criteria True |

## Q4 evidence (now logging copy_entropy_valid_mean)

- `copy_loss`: 2.476 → 0.140 (first/last window means, 529 rpm batches)
- `copy_argmax_acc`: 0.0 → 0.9498 (30× above 1/32 random baseline)
- `copy_entropy_valid_mean`: 2.531 → 0.163 (heavy concentration)
- `copy_valid_count` > 0 on 529 of 1000 batches (53%)

## Canary sample veto (KILL at every checkpoint)

| Step | Clean | Warn | Kill | Mean severity | Total loop events |
|---|---|---|---|---|---|
| 250 | 0 | 1 | 10 | 3.73 | 122 |
| 500 | 0 | 1 | 10 | 3.82 | 87 |
| 750 | 1 | 6 | 4 | 2.45 | 56 |
| 1000 | 2 | 5 | 4 | 2.09 | 66 |
| post-training | 2 | 5 | 4 | 2.09 | 66 |

## Decisive structural signal: ZERO canonical stage variables emitted

The STAGE_VAR copy loss reached 95% argmax accuracy during training. But across 5 checkpoints × 11 canary records = 55 generations, the regex `\bstage[ADWP]\d+_\d+_\d{4}\b` matches **zero** times. The model produces fragments (`stageA0_0_023`, `stageD7_02`, `stageW3_03_03`) — partial identifiers missing a segment or with the wrong digit count.

**This is the load-bearing finding.** Teacher-forced copy supervision rewards picking the right SOURCE INDEX at each output position. Greedy decode multiplies this per-position decision into a multi-token-span sequence. Without span-aware decoding or scheduled sampling, the model has never been forced to maintain coherence across a span.

## The same record (canary_rpm_chain_001) over time

| Step | Generated text (first 200 chars) |
|---|---|
| 250 | `The expression tries to to to to to to to to to to ... the the the the the the the the the ...` |
| 500 | `... to to to to to a a a a the the the the the the the ...` |
| 750 | `... to a destination destination the destination the destination the the the system the the the system ...` |
| 1000 | `... to multiply two two two two multiplion only of of two two two states of two two states but of the of states of the only of of the of is is is is in the the system system ...` |

Lexical diversity grows; loop structure persists.

## What this does NOT mean

- Architecture isn't broken. Copy mechanism works at 95% TF acc, simplex stays in Δ°₃₉, FR converges, slot_type solves. Wiring is sound.
- Not a tokenizer or corpus issue. STAGE_VAR spans matched cleanly during training (529/1000 batches fired).

## Four hypotheses for what items 1-3 of the diagnostic will test

| # | Hypothesis | What the diagnostic shows |
|---|---|---|
| H1 | Exposure bias — TF training never penalizes loops | Item 1 (TF vs greedy): if TF canary loss is healthy but greedy explodes, this is the cause |
| H2 | Copy-head capacity stealing the decoder | Item 3 (decode ablation, copy off): if copy-disabled decode is less loop-y, copy weight needs to drop |
| H3 | slot_type collapsed to CONNECTIVE | Item 2 (per-token trace): if slot_type entropy is near 0 with mass on CONNECTIVE, phrase-bias never fires |
| H4 | lm_head entropy collapse at greedy time | Item 2: if lm_logits entropy drops to ~0 within ~5 tokens of every decode, model is pathologically certain |

**My best-guess prior:** H4 is dominant — greedy decode + cross-entropy + 1000 steps of training is the textbook recipe for early entropy collapse on a tiny corpus. H1 (exposure bias) is a contributor. H2 (copy capacity-stealing) is plausible but the strong TF acc suggests the copy head isn't the corruption source — it's the LM head's surrounding prose that's degenerate.

## What the diagnostic infrastructure needs

Pod ran out of funds mid-investigation. Building offline:

1. **Checkpoint save/load** — `run_cpu_smoke` currently doesn't persist `model.state_dict()`. Need to save at end of run + reload script. Without this, every diagnostic re-trains.
2. **Teacher-forced canary evaluator** — same canary records, but with TF (decoder sees ground-truth prefix instead of greedy prefix). Returns per-record loss + per-token lm_logits/slot_type/copy stats.
3. **Per-token greedy trace** — extends `sample_decoder` to log per-step: chosen token, top-5 lm_logits, lm_entropy, slot_type distribution, copy_argmax + entropy, whether the chosen token "looks copied" (matches source).
4. **Decode-time ablations** — same checkpoint, decode 4 ways: (a) full, (b) copy-disabled (zero p_copy contribution), (c) phrase-bias-disabled, (d) lm-only baseline. Compare canary damage scores.

## Decision rule going forward

- If TF canary is healthy and greedy collapses → exposure bias confirmed. Stage 7-bis should try scheduled sampling / mix-in, not loss-weight ablations.
- If TF canary is ALSO degenerate → architecture-level issue, requires pause for review (per execution plan §Stage 7-bis hard-stop rule).
- If copy-off ablation is materially cleaner than copy-on → copy weight is the culprit. Reduce to 0.1 or drop entirely; rerun training.
- If copy-off is no cleaner → copy is innocent. lm_head + decoding strategy is the load-bearing failure mode.

## Companion artifacts

- `docs/working/simplex_mvp_stage7_v7_1b_canary_report_2026_05_11.json` — full v7.1b smoke report
- `docs/working/simplex_mvp_stage7_v7_1000step_report_2026_05_11.json` — v7 report (scalar-pass formal-incomplete)
- `docs/working/simplex_mvp_stage7_v7_1b_postmortem_2026_05_11.md` — this doc

## Stage 7-bis decision: ON HOLD pending diagnostic

Per execution plan: Stage 7 FAIL triggers Stage 7-bis (ablation grid) OR architectural review. The user has held both. The diagnostic items 1-3 are the smallest information-bearing step before either path.
