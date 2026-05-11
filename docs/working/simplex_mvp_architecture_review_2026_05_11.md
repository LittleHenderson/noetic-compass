# Simplex MVP — Architectural Review

**Date opened:** 2026-05-11
**Status:** OPEN. Awaiting user decision on which candidate(s) to build.
**No pod spend authorized.** No training experiment will run until the chosen candidate has explicit kill/validate criteria signed off.
**v0-rc1 remains canonical.**

## Why we're here

Per `simplex_mvp_diagnostic_replay_findings_2026_05_11.md`: the 1000-step diagnostic replay showed all four decode ablations (`full`, `lm_only`, `copy_disabled`, `phrase_bias_disabled`) produce identical damage (2 clean / 5 warn / 4 kill). Teacher-forced argmax has top-1 acc 0.597 and recovers 0 of 4 canonical stage variables. Slot gate collapses to CONNECTIVE for 128/128 generated tokens on rpm_chain_001.

**The failure sits in the trained decoder/LM emission geometry**, not in free decoding, copy routing, or a single auxiliary loss weight. Stage 7-bis (loss-grid ablation) is the wrong question.

## Failure properties any candidate must address

1. **lm_head produces degenerate output even with truth prefix.** Top-1 acc 59.7% under TF.
2. **lm_head + copy_head learned antagonistic objectives.** Copy points at right source 95% of training time; lm_head emits wrong tokens at decode 40% of TF positions.
3. **Slot gate collapses to CONNECTIVE** for most of every generated sequence; transiently activates STAGE_VAR (briefly, then collapses).
4. **Sequential instability**: architecture can produce ~10 correct identifier tokens before degenerating into repetition. **Cannot sustain coherent spans.**
5. **Repeat-loop attractors** persist across all decode modes.

Any candidate that doesn't change at least one of the above structural properties is a tuning patch, not a fix.

## Candidate A — Untied LM head replay

**Hypothesis:** weight-tying `lm_head.weight = token_emb.weight` (Stage 6 v4 decision) caused antagonistic gradient flow. Copy gradient flowing through `token_emb` during training corrupted the lm_head's emission distribution. Untying lets the lm_head learn independently of the input embedding geometry.

**Code change:** remove `self.lm_head.weight = self.token_emb.weight` from `TypedFiberDecoder.__init__`. ~3 LOC. Restores ~14.9M params (back to ~70M total). GPU memory still well within budget (1.34 GB vs 20 GB threshold; budget delta absorbs 70M trivially).

**Build effort:** ~30 min (revert tying, retest weight-tying unit tests adjust, restore param-count check target). ~1 pod run × $0.44 to repeat the diagnostic replay protocol.

**Validate (untie hypothesis CONFIRMED) if:**
- Same diagnostic replay produces TF top-1 acc **≥ 0.80** (vs current 0.597)
- canonical_stage_var recovery_rate **≥ 0.5** (vs current 0.0) at step 1000
- All four ablation modes show **non-identical** damage profiles (rules 2/3 differentiate)
- Canary pack verdict moves from "kill" to at least "warn" majority

**Falsify (untie hypothesis DEAD) if:**
- TF top-1 acc stays < 0.65
- canonical_stage_var recovery_rate < 0.25 at step 1000
- Decode ablations remain identical
- Canary pack verdict stays "kill"

**Risk:** untying restores 14.9M params; if it succeeds, we're paying for that capacity. Not a problem on A6000 but worth tracking. Bigger risk: success here might mask a deeper problem (the lm_head can fit data but the architecture still can't generalize to free decode).

## Candidate B — Two-stage decoder training (LM first, copy later)

**Hypothesis:** Even with untied weights, joint LM + FR + slot + copy gradients are antagonistic during training. Decoder hidden states get pulled in conflicting directions. Training LM-only (or LM + FR + slot) to convergence first, then bolting copy on as a frozen-base fine-tune, lets the lm_head learn an emission distribution before the copy head can corrupt it.

**Code change:** add `--training-stage` flag (`lm_first` / `copy_after`) to trainer; stage 1 zeroes copy loss weight; stage 2 unfreezes copy head only, freezes lm_head. ~150 LOC + tests. Two pod runs back-to-back (stage 1: 1000 steps; stage 2: 500 steps). ~$0.65 total.

**Validate (staged training works) if:**
- Stage-1 checkpoint produces TF top-1 acc ≥ 0.85 on canary (lm_head can fit data when copy doesn't fight it)
- Stage-1 greedy canary verdict ≤ warn (lm-only output is coherent prose, even if missing identifier slots)
- Stage-2 checkpoint produces TF top-1 acc ≥ 0.80 AND canary verdict ≤ warn (adding copy doesn't break the lm)
- canonical_stage_var recovery_rate ≥ 0.5 at end of stage 2

**Falsify (staged training is a patch) if:**
- Stage-1 TF top-1 acc < 0.75 (LM can't fit even when uncontested by copy)
- Stage-2 canary verdict regresses to "kill" (copy fine-tune destroys the lm geometry)

**Risk:** the failure mode might re-emerge in stage 2 just delayed. Or stage 1 might pass spectacularly but then the architecture has effectively become "v0-rc1 + copy head", which is a much smaller delta than the simplex MVP was supposed to be. Could indicate the typed-fiber decoder design is over-engineered.

## Candidate C — Hard typed-fiber emission route

**Hypothesis:** the soft-gate phrase-bias-mixed-into-lm_logits design is the culprit. The model has to learn a continuous tradeoff between "emit from lm_head" and "emit from copy" at every position. The diagnostic showed this tradeoff settled into "always emit from lm_head, ignore copy" (slot always CONNECTIVE). A **hard** gate — slot type ∈ {1..7} ⇒ emit `src_ids[copy.argmax]`; else ⇒ emit `lm.argmax` — removes the competition entirely.

**Code change:** modify `TypedFiberDecoder.forward` to compute slot_type first, then route emission. At training time, use `target_typed_positions` as a teacher-forced gate (so the loss flows to whichever head should have produced this position). At decode time, use `slot_type_logits.argmax`. ~80 LOC + tests. One pod run to retest. ~$0.44.

**Validate (hard gating works) if:**
- canonical_stage_var recovery_rate ≥ 0.7 (slot gate routes to copy → copy emits the right id)
- TF top-1 acc ≥ 0.80 on connective + noetic positions specifically
- slot_type_argmax non-trivial across canary records (not collapsed to one class)
- Free-decode canary verdict ≤ warn

**Falsify (hard gating is a patch) if:**
- slot_type_argmax still collapses to CONNECTIVE on > 90% of decode positions (the gate predictor itself is broken)
- canonical recovery_rate < 0.4
- The model still loops (because connective generation alone loops)

**Risk:** if slot_type can't be reliably predicted at decode time, hard gating breaks completely (no fallback). Soft gating at least produces *some* output even when slot is wrong; hard gating amplifies a wrong gate decision into structured failure.

## Candidate D — SSM typed-fiber decoder

**Hypothesis:** the failure is **sequential stability** — loops, collapse to CONNECTIVE, can't sustain stage-var spans. Transformer decoders attend over the short generated prefix, which is shallow and information-poor early in generation. State-space models (Mamba/S4-like) maintain a learned recurrent state that captures long-range structure. The simplex Δ°₃₉ trajectory is already state-like; an SSM decoder may be a more natural fit than a Transformer decoder.

**Code change:** replace `TypedFiberDecoder`'s self-attention + cross-attention stack with an SSM block (Mamba selective scan + cross-attention into simplex_trajectory and src_emb). Slot type / copy / phrase bias heads stay (typed fibers preserved). ~500-800 LOC + tests. Library dependency: `mamba-ssm` or hand-roll S4 (the hand-roll is ~150 LOC of careful state-update math). Build effort: ~2-3 days. ~$0.50 per pod run × multiple runs to debug.

**Validate (SSM helps) if:**
- TF top-1 acc ≥ 0.80 at step 1000 (SSM can fit the same data Transformer couldn't)
- Free-decode canary shows >5 records "clean" (sustained span generation works)
- canonical_stage_var recovery_rate ≥ 0.5
- LM entropy trajectory shows smooth monotonic decrease across decode positions, NOT the bimodal "peaky-on-filler / uniform-on-content" pattern the Transformer showed

**Falsify (SSM also fails) if:**
- Same damage profile as Transformer (kill on rpm_chain, slot collapse to CONNECTIVE, repetition)
- Architecture changes the failure shape but not the failure rate
- Repetition loops persist (would indicate the corpus paraphrase property is the root cause, regardless of decoder)

**Risk:** highest of the 4. SSM is the largest code delta, the largest architectural commitment, and the most expensive to debug. Per user 2026-05-11 caution: "Don't use SSM as 'try another model.' Use it to test a specific hypothesis: the decoder needs stable recurrent state evolution." If candidates A-C falsify their hypotheses without surfacing a clear "needs recurrent state" signal, SSM is premature.

## Order-of-experiment heuristic (per user 2026-05-11)

> "The next cheapest informative experiment is **untie lm_head and rerun the 1000-step diagnostic replay**, but only after the review doc explicitly says what result would kill or validate that hypothesis."

Recommended sequence:

1. **Candidate A (untied LM head)** first. Smallest code change. Cheapest. Most direct test of the tying-as-cause hypothesis. Kill/validate criteria above.
2. **If A validates:** continue with v0-rc1 as canonical; simplex MVP becomes a research finding ("the v7.1b damage was tying"). Stage 7 can re-launch with untied weights.
3. **If A falsifies:** move to **Candidate C (hard typed-fiber emission)**. Tests whether soft gating is the issue. If it validates, the simplex MVP gets re-launched with hard gating. If it falsifies, both A and C are local patches.
4. **If A and C both falsify:** move to **Candidate B (two-stage training)**. Tests the antagonistic-gradient hypothesis at the training-protocol level.
5. **If A, B, and C all falsify:** then **Candidate D (SSM)** is justified as a genuine architectural change rather than a "try another model." This is when the decoder needs stable recurrent state evolution becomes the working hypothesis.

If at any point a candidate validates, we stop and surface for direction.

## Common preconditions across all candidates

- The diagnostic-replay checkpoint at `/workspace/tksCAS/stage7_diagnostic_replay_20260511T113303Z/ckpt_final.pt` is the baseline. Re-runs of candidates A/B/C/D will run the same 1000-step protocol + same canary pack, so results are directly comparable.
- All re-runs include the 4 diagnostic-infra pieces (checkpoint save, TF canary, per-token trace, decode ablations) so we have apples-to-apples evidence each time.
- Each candidate must produce a `findings.md` documenting which kill/validate criterion was met.
- **No candidate proceeds to Stage 8 (full unified run) without an architectural review committee sign-off.** Stage 7 has failed; Stage 8 is downstream of an unresolved Stage 7 verdict.

## What candidates are NOT being considered

- Stage 7-bis loss-grid ablation (4 weighted-loss reruns of the SAME architecture) — explicitly stale per diagnostic
- Training longer at current weights — diagnostic shows damage is in weights, not undertraining
- Scheduled sampling / teacher-forcing mix-in — Rule 1 ruled out, exposure bias is not the cause
- Tokenizer changes — diagnostic on real v1c tokenizer was clean (Stage 6 v6 passed)
- Corpus changes — out of scope for architectural review; corpus question deferred to a separate decision

## Cost / time projections

| Candidate | Build effort | Pod cost | Total |
|---|---|---|---|
| A — Untied LM head | ~30 min code + tests | ~$0.44 (1 replay) | ~$0.44 |
| B — Two-stage training | ~150 LOC | ~$0.65 (2 runs) | ~$0.65 |
| C — Hard typed-fiber emission | ~80 LOC | ~$0.44 | ~$0.44 |
| D — SSM decoder | 2-3 days build | ~$1.50 (3 runs to debug) | $1.50+ |

Cumulative simplex MVP pod spend to date: ~$1.65 of $60 budget. Plenty of headroom for A → C → B sequence.

## Decision request

Standing by for your direction on:

1. **Confirm the candidate order** (A → C → B → D, or different)
2. **Confirm the kill/validate criteria** for whichever candidate goes first (or amend)
3. **Authorize Candidate A build + replay** once criteria are confirmed (~30 min code + ~50 min pod = ~80 min total, ~$0.44)

OR

- **Pause the simplex MVP track entirely** and pivot to other work (Path D Wave 3/4 was paused mid-investigation; the SGGS backlog from 2026-05-06 was deferred; v0-rc1 is healthy and shipped).

## Companion artifacts

- `docs/working/simplex_mvp_diagnostic_replay_findings_2026_05_11.md` — empirical evidence the review is built on
- `docs/working/simplex_mvp_stage7_v7_1b_postmortem_2026_05_11.md` — Stage 7 failure history
- `docs/working/simplex_mvp_diagnostic_replay_smoke_report_2026_05_11.json` + 3 analysis JSONs
- Memory: `project_simplex_architecture_review_framing_2026_05_11.md` — user's locked framing
- Memory: `project_simplex_diagnostic_decision_standard_2026_05_11.md` — the 5 outcome→action rules
