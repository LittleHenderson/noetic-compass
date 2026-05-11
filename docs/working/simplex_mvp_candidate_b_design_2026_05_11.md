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

**Goal:** establish that the LM head can produce non-looping prose when not under joint pressure from slot/copy.

**KILL if** any rpm_chain canary sample produces a phrase-loop (repeated_phrase_loop.found = true) in the post-training canary. If even the simplest joint signal can't be removed without prose collapse, the framework's LM head is the load-bearing problem — staged training won't fix it, and Candidate B is falsified before B2 starts.

**VALIDATE if** rpm_chain canaries produce coherent prose (whatever it says about CAS), no looping. Damage verdict can still be kill on other axes (notation_leak, generic_collapse) — we're only gating on prose stability here.

If B1 kills → Candidate B falsified at stage 1 → next move is Candidate D (SSM decoder) or architectural review reopens. Do NOT tune lr / weight_decay / batch_size on B1 (anti-tuning rule).

### B2 — + slot loss, still no copy

**Goal:** the slot gate develops on a stable LM head and sustains STAGE_VAR on rpm_chain inputs.

**KILL if** the post-training canary `slot_type_trace` is mostly CONNECTIVE across rpm_chain records — specifically, ≥8 of 11 records show slot_trace_counts where slot 0 (CONNECTIVE) accounts for >90% of positions. That's the same fingerprint Candidate C showed; staged training didn't fix the attractor.

**VALIDATE if** ≥3 of 11 records (and at least 1 of 2 rpm_chain records) show slot reaching STAGE_VAR (slot id 2) for at least 5 consecutive positions in identifier spans.

If B2 kills → B falsified at stage 2 → the slot gate has a deeper structural problem (training schedule isn't the issue). Next move: surface for architectural review on slot head design.

### B3 — + copy + hard typed emission

**Goal:** hard routing fires across multiple records (not just 1/11 as in C), STAGE_VAR identifier recovery materially improves, kill count drops below C's baseline.

**Eval gate:** the same battery Candidate C used.
- `emission_routes_pack.copy_fraction` materially above C's 1.63% at step 1000 (target: ≥10%, i.e. hard routing fires on at least multiple records).
- `decode_ablations.json`: `hard_full` outperforms `full` (lower mean_severity, fewer kills, more clean).
- Per-record slot_type_trace shows STAGE_VAR sustained across multiple rpm_chain records.
- TF analysis A: `canonical_stage_vars_in_argmax` ≥ 1 (any improvement over C's 0/4).

**VALIDATE if** all four hold. **FALSIFY if** copy_fraction stays ~zero (same pattern as C) or hard_full is no better than full.

If B3 validates → surface for direction on next-step architecture (productionize, scale, or move to extended training).
If B3 falsifies → Candidate B doesn't solve the slot gate either; next move is reopened architectural review (Candidate D / different decoder topology / SSM).

## Launch commands

The pod has the audit-fixed code from Candidate C plus the new flags. After this commit lands, sync the trainer file and launch B1.

### Sync (single file)

```
scp -P 22026 -i ~/.ssh/id_ed25519 \
  noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py \
  root@194.68.245.88:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/
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
