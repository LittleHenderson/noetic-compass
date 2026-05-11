# Candidate B — Staged Training Design (READY for audit)

**Date locked:** 2026-05-11
**Status:** Code + tests offline-complete. Awaiting user audit + pod launch authorization.
**Scope:** Research-track only. v0-rc1 remains canonical. Carries Candidate C's hard-routing mechanism forward at stage B3.

## Hypothesis under test

> Joint training from step 1 causes the decoder hidden space to collapse into
> LM / CONNECTIVE attractors before slot routing can stabilize. Training the
> LM head alone first, then layering slot, then layering copy + hard routing,
> should let each gate develop in a better-conditioned regime.

This is the diagnosis sharpened by Candidate C's findings:

| Component | Status under C |
|---|---|
| copy head | learns (acc 0.94, low copy loss) |
| hard route mechanism | works when reached (rpm_chain_002, 11 copy emissions reconstructing `stageA0_4_0049`) |
| slot gate (free decode) | collapses to CONNECTIVE on 10/11 records |
| LM prose (around copy spans) | corrupts (phrase loops, generic prose) |

The slot gate is the upstream blocker. Hard routing has nothing to route until slot can sustain STAGE_VAR. B tests whether staged training breaks the CONNECTIVE attractor.

## Stage spec

Each stage runs 1000 steps with the same data/tokenizer/seed/batch_size/lr as the diagnostic baseline and Candidate C, so the only intentional deltas are loss weights, warm-start, and (for B3) `--hard-typed-emission`.

| | B1 | B2 | B3 |
|---|---|---|---|
| `--ablation` | `b1` | `b2` | `b3` |
| `lm` | 1.0 | 1.0 | 1.0 |
| `fr` | 1.0 | 1.0 | 1.0 |
| `slot_type` | **0.0** | **1.0** | 1.0 |
| `copy` | **0.0** | **0.0** | **0.5** |
| `phrase_bias_aux` | 0.0 | 0.0 | 0.1 |
| `--hard-typed-emission` | off | off | **on** |
| `--load-model-from` | (none) | B1 ckpt_final | B2 ckpt_final |
| n_steps | 1000 | 1000 | 1000 |

The `lm` and `fr` weights are constant across stages — they're the floor. Each successive stage adds exactly one new gradient signal.

Each stage:
- Runs the same canary at steps 250/500/750/1000 + post-training.
- Saves `ckpt_step_{250,500,750,1000}.pt` + `ckpt_final.pt`.
- Writes `trainer_log.jsonl` and `smoke_report.json`.
- Optimizer state is fresh per stage (different loss landscape ⇒ Adam moments from B1 would mis-condition B2).
- RNG and step counter are fresh per stage.

## Per-stage kill criteria (LOCKED — apply at canary post-training, do not tune mid-run)

### B1 — LM + FR only

**Goal:** establish that the LM head can produce non-trivial, non-looping prose when not under joint pressure from slot/copy.

**KILL if any of the following on the post-training canary:**
- Any rpm_chain canary sample produces a phrase-loop (`repeated_phrase_loop.found = true`).
- Any rpm_chain canary has `n_tokens_generated < 30` (early-EOS collapse — guard against Candidate A's "trivial clean" artifact where an empty or 2-token output passes the damage detector by virtue of having nothing to score).
- Any rpm_chain canary has `text_len < 30` characters.
- Any rpm_chain canary has `hit_eos = true` AND `n_tokens_generated < 50` (the model gave up before producing meaningful output).

If even the simplest joint signal can't be removed without prose collapse OR the model trivializes its outputs to game the damage detector, the LM head is the load-bearing problem — staged training won't fix it.

**VALIDATE if all rpm_chain canaries:**
- Produce ≥30 generated tokens AND ≥30 characters of text.
- No `repeated_phrase_loop.found`.
- Either no `hit_eos` OR `hit_eos` with ≥50 tokens (eos after a real attempt is fine).

Damage verdict can still be kill on other axes (notation_leak, generic_collapse via length_ratio mismatch, stage_var_corruption from absent STAGE_VAR slot signal) — we're only gating on prose ACTIVITY here, not prose quality.

If B1 kills → Candidate B falsified at stage 1 → next move is Candidate D (SSM decoder) or architectural review reopens. Do NOT tune lr / weight_decay / batch_size on B1 (anti-tuning rule).

### B1 result — qualified pass (recorded 2026-05-11)

B1 completed at 20:46Z. Trajectory: mean_severity 3.64 (step 250) → 1.23 (step 750) → 1.82 (post-training). Both rpm_chain canaries produced 128 tokens and 250+ chars; no triviality / early-EOS / catastrophic-loop signatures.

**Literal binary gate:** `repeated_phrase_loop.found = true` on `canary_rpm_chain_002` due to the article `"a"` repeated 3 consecutive times mid-prose (`"... name a a a and evaluative judgment ..."`).

**Spirit-of-gate read:** function-word stutter inside otherwise structured rpm prose. Not the Candidate-C loop attractor (C had `"to" × 13` consuming whole outputs). Macro-structure was preserved (`Let stage<X>_<n>_<dddd> name ... stage<Y>_<n>_<dddd> name ...`) and stage-var-shaped identifiers emerged WITHOUT slot loss active.

**Decision (user, 2026-05-11):** Qualified pass — proceed to B2. The gate exception is recorded; B1 is not re-run; the anti-tuning rule remains in force. The measurement was the detector being more sensitive than the failure it was meant to catch, not the model coasting on a flattering metric.

**B2 regression guard (added 2026-05-11 per user audit):** if any of the following occur at B2 post-training canary, kill B immediately:
- Catastrophic loop returns — any phrase_loop with `count ≥ 5` and a non-function-word phrase, OR `count ≥ 8` of any phrase (real attractor like Candidate C's `"to" × 13`).
- Triviality regression — any rpm_chain with `n_tokens_generated < 50` OR `text_len < 100` (B1 had 128/250+; B2 must not regress this).
- Prose regression — pack-level `mean_severity` higher than B1's post-training value of 1.82.

This guard ensures B2's added slot loss doesn't re-destabilize what B1 established.

### B2 — + slot loss, still no copy

**Goal:** the slot gate develops on a stable LM head and sustains STAGE_VAR on rpm_chain inputs, AND does not misfire on non-rpm_chain inputs (no leakage), AND does not regress B1's prose stability.

Only the rpm_chain canaries have stage_vars in their target text (`canary_rpm_chain_001` and `canary_rpm_chain_002` — 2 records). Other canary categories (fractal_sequence, recipe, meta_logic, state_literal, binary_composition, cross_register_omega, invalid_fractal) have no stage_vars in their targets. A slot head firing STAGE_VAR on those inputs is **leakage**, not progress.

**KILL if any of the following on the post-training canary:**
- Neither rpm_chain canary shows slot reaching STAGE_VAR (slot id 2) for at least 5 consecutive positions during the identifier-span region.
- Either rpm_chain canary has slot_trace_counts where CONNECTIVE (slot 0) accounts for >90% of positions (same fingerprint Candidate C showed).
- **Leakage:** any non-rpm_chain canary record has slot_trace containing STAGE_VAR for ≥3 consecutive positions. The slot gate has overgeneralized — it's firing STAGE_VAR on inputs that shouldn't have any.
- **B1 regression guard (recorded above):** catastrophic loop (phrase_loop `count ≥ 5` with non-function-word phrase, OR `count ≥ 8` any phrase); triviality regression (any rpm_chain `n_tokens < 50` OR `text_len < 100`); pack-level `mean_severity > 1.82` (B1's post-training value).

**VALIDATE if all of the following:**
- At least 1 of 2 rpm_chain canaries shows slot reaching STAGE_VAR for ≥5 consecutive positions covering the identifier span.
- Neither rpm_chain canary has slot_trace_counts with CONNECTIVE >90%.
- No non-rpm_chain canary record shows sustained STAGE_VAR slot output (zero leakage).

If B2 kills due to under-firing on rpm_chain → slot gate has a deeper structural problem (training schedule isn't the issue). If B2 kills due to leakage → slot loss over-generalized; next move is slot supervision review (anchor masking / negative samples), not retraining at the same schedule. Either way, **anti-tuning rule applies**: do not re-run B2 with different lr / slot weight to make the gate pass.

### B3 — + copy + hard typed emission

**Goal:** hard routing fires on BOTH rpm_chain records (not just 1/11 as in C), STAGE_VAR identifier recovery materially improves on rpm_chain specifically, hard_full beats full on rpm_chain, pack-level damage drops below C's baseline.

Only rpm_chain canaries (2 of 11) have stage_vars to copy. Pack-wide `copy_fraction` is the wrong denominator: even perfect routing would put the pack-wide fraction at roughly the ratio of rpm_chain identifier tokens to total emitted tokens (≈5-8%, not anywhere near 100%). The gate must be rpm_chain-scoped.

**Eval gate (read from canary_history step=1000 + decode_ablations.json + tf_canary_report.json):**

**1. rpm_chain-specific hard-route firing.**
- Both `canary_rpm_chain_001` and `canary_rpm_chain_002` show `emission_route_counts.copy ≥ 10` (Candidate C had this on rpm_chain_002 only).
- At least one rpm_chain record reconstructs a canonical-shaped stage_var identifier in `generated_text` (substring match against the target's stage_var pattern, modulo a small Levenshtein tolerance for trailing-digit-stutter).
- Non-rpm_chain records: `emission_route_counts.copy = 0` (no leakage — hard routing should not fire on inputs without copy targets).

**2. TF capability improvement.**
- `tf_canary_report.json.summary.canonical_stage_vars_in_argmax ≥ 1` (Candidate C was 0/4; ANY improvement is real progress).
- `canonical_recovery_rate > 0` (was 0.0 across diagnostic, A, and C).

**3. Decode ablations: hard_full beats full on rpm_chain.**
- `decode_ablations.json.per_record` rpm_chain entries: `hard_full.damage_severity` strictly less than `full.damage_severity` on at least one of two rpm_chain records.
- Pack-level: `hard_full.mean_severity < full.mean_severity` (C had hard_full marginally worse than full — this must invert).

**4. Pack-level damage improvement.**
- Canary at step 1000 `by_verdict.kill` count drops below Candidate C's baseline of 5/11. Target: ≤3/11 kill.

**VALIDATE if all four gates hold.**

**FALSIFY if any of:**
- Either rpm_chain record has `copy ≤ 5` (hard routing didn't take on inputs where it should).
- Any non-rpm_chain record has `copy > 2` (hard routing fired where it shouldn't — leakage at decode).
- TF analysis A still shows `canonical_stage_vars_in_argmax = 0` (no underlying capability change).
- `hard_full.mean_severity ≥ full.mean_severity` pack-wide (routing not helping).

If B3 validates → surface for direction on next-step architecture (productionize the staged-training recipe, scale, or extend training to step 2000+).
If B3 falsifies → Candidate B doesn't solve the slot gate either; next move is reopened architectural review (Candidate D / SSM decoder / different decoder topology). **Do not retune B3** — the staged-training hypothesis itself is what's being tested.

## Launch commands

### Pre-launch sync — files required on pod

Pod state from Candidate C launch is NOT guaranteed to persist (spot pods can recycle). Before every stage, verify the required files are on pod and match local. B1 and B2 need only the trainer; B3 also needs the Candidate C audit-fixed eval files.

**Files required by stage:**

| File | B1 | B2 | B3 |
|---|---|---|---|
| `cas-native/training/train_simplex_mvp.py` (has b1/b2/b3 + `--load-model-from`) | ✓ | ✓ | ✓ |
| `cas-native/evaluation/sample_decoder.py` (hard-emission with STAGE_VAR scope + type-match) | | | ✓ |
| `cas-native/evaluation/decode_ablations.py` (has `hard_full` mode) | | | ✓ |
| `cas-native/evaluation/run_v7_postmortem_analyses.py` (threads hard-emission to `run_decode_ablations_pack`) | | | ✓ |

**Verification (run BEFORE every stage launch):**

```bash
# Local: compute MD5 of each required file (LF-normalized for cross-platform parity)
python -c "
import hashlib
for f in [
  'noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py',
  'noetic-compass-scaffold/noetic-compass/cas-native/evaluation/sample_decoder.py',
  'noetic-compass-scaffold/noetic-compass/cas-native/evaluation/decode_ablations.py',
  'noetic-compass-scaffold/noetic-compass/cas-native/evaluation/run_v7_postmortem_analyses.py',
]:
  data = open(f, 'rb').read().replace(b'\r\n', b'\n')
  print(hashlib.md5(data).hexdigest(), f.split('/')[-1])
"

# Pod: md5sum the same files
ssh -p 22026 -i ~/.ssh/id_ed25519 root@194.68.245.88 'cd /workspace/tksCAS/noetic-compass-scaffold/noetic-compass && md5sum \
  cas-native/training/train_simplex_mvp.py \
  cas-native/evaluation/sample_decoder.py \
  cas-native/evaluation/decode_ablations.py \
  cas-native/evaluation/run_v7_postmortem_analyses.py'
```

If any MD5 differs from local, scp the matching files. For B1/B2 only the trainer needs to match. For B3 all four must match.

### Sync command (used after a mismatch or fresh pod)

```bash
# B1/B2: trainer only
scp -P 22026 -i ~/.ssh/id_ed25519 \
  noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py \
  root@194.68.245.88:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/

# B3: trainer + three Candidate C audit-fixed eval files
scp -P 22026 -i ~/.ssh/id_ed25519 \
  noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py \
  root@194.68.245.88:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/
scp -P 22026 -i ~/.ssh/id_ed25519 \
  noetic-compass-scaffold/noetic-compass/cas-native/evaluation/sample_decoder.py \
  noetic-compass-scaffold/noetic-compass/cas-native/evaluation/decode_ablations.py \
  noetic-compass-scaffold/noetic-compass/cas-native/evaluation/run_v7_postmortem_analyses.py \
  root@194.68.245.88:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/evaluation/
```

### B1 launch

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT=/workspace/tksCAS/stage7_candidate_b1_lmfr_${TS}

nohup python /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py \
  --data-path /workspace/tksCAS/cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl \
  --output-dir ${OUT} \
  --device cuda:0 \
  --d-model 384 --encoder-n-layers 4 --decoder-n-layers 6 \
  --encoder-n-heads 6 --decoder-n-heads 6 \
  --batch-size 16 --limit 7000 --n-steps 1000 \
  --lr 1e-4 --weight-decay 1e-4 --grad-clip 1.0 \
  --ablation b1 --train-log-every-steps 50 \
  --tokenizer-path /workspace/tksCAS/stage6_v6_artifacts/tokenizer.json \
  --english-bpe-path /workspace/tksCAS/stage6_v6_artifacts/english_bpe.json \
  --sample-canary-at 250,500,750,1000 --sample-canary-post-training \
  --save-checkpoints-at 250,500,750,1000 --save-final-checkpoint \
  --canary-max-new-tokens 128 --seed 1729 \
  > ${OUT}.log 2>&1 &
```

### B2 launch (after B1 validates)

Substitute `--ablation b1` → `--ablation b2` and add `--load-model-from /workspace/tksCAS/stage7_candidate_b1_lmfr_<B1_TS>/ckpt_final.pt`. Out dir prefix becomes `stage7_candidate_b2_lmfr_slot_`.

### B3 launch (after B2 validates)

Substitute `--ablation b2` → `--ablation b3`, update `--load-model-from` to B2's `ckpt_final.pt`, add `--hard-typed-emission --copy-confidence-threshold 0.5`. Out dir prefix becomes `stage7_candidate_b3_full_hardemit_`. Postmortem analysis script (the same `run_v7_postmortem_analyses.py` used for C) must also receive `--hard-typed-emission --copy-confidence-threshold 0.5` so decode_ablations runs `hard_full` mode.

## Cost projection

| Item | Wall-clock | Spot cost |
|---|---|---|
| B1 training | ~50 min | ~$0.44 |
| B1 canary + manual audit | minutes | $0 |
| B2 training | ~50 min | ~$0.44 |
| B2 canary + audit | minutes | $0 |
| B3 training | ~50 min | ~$0.44 |
| B3 postmortem (A + B + C with hard_full) | ~5 min | ~$0.05 |
| **Candidate B total** | **~3 hr** | **~$1.37** |

Cumulative since simplex MVP started: would reach ~$3.90 of $60 budget after B completes.

## What this design does NOT do

- Does NOT launch any pod run (awaits explicit user authorization per stage).
- Does NOT promote v0-rc1 to anything else.
- Does NOT auto-chain B1 → B2 → B3 on pod. Each stage launches separately after its kill criterion is applied. The anti-tuning rule applies: if a stage fails its criterion, B is falsified — do not retune.
- Does NOT modify training-time behavior for runs that omit `--load-model-from` (the warm-start path is opt-in; default empty string → fresh init, identical to existing behavior).

## Carry-forward from Candidate C

The hard typed-fiber emission mechanism (Candidate C code) remains in the codebase and is active in B3. The Candidate C verdict was: mechanism sound, slot gate broken upstream. B tests whether the upstream fix unblocks the downstream mechanism. If B succeeds, the architecture as currently committed (Δ°₃₉ + typed slots + hard typed emission + admissibility) is the production target. If B fails, the gap is deeper than training schedule.

## Companion files

- `noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py` — adds `b1/b2/b3` ablation presets and `--load-model-from` warm-start flag.
- `noetic-compass-scaffold/noetic-compass/cas-native/tests/training/test_simplex_mvp_integration.py` — 6 new tests for the staged-training surface.
- `noetic-compass-scaffold/noetic-compass/cas-native/tests/training/test_simplex_checkpoint.py` — 1 new test for warm-start contract (model only, no optimizer, no RNG).
- `docs/working/simplex_mvp_candidate_a_findings_2026_05_11.md` — Candidate A falsified
- `docs/working/candidate_c/` — Candidate C falsified artifacts
- `docs/working/simplex_mvp_architecture_review_2026_05_11.md` — original 4-candidate review (A done, C done, B next, D pending)
