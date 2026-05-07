# Path B-3 — Full 50K GPU Training Run Report

**Date:** 2026-05-07
**Status:** RUN COMPLETE — mixed verdict, B-3.5 follow-up gates B-4
**Cost:** ~$0.54 (RunPod A6000 spot, 65 min wall-clock)

## Run config

```
trace_id:               3fe94cc5-ef64-418e-abd2-213485b9adf0
checkpoint_id:          7ae0a6ab-cac1-4ac7-96d8-605448c282e4
seed:                   42
data:                   v1_dialogue_50k_claude_20260507_full.jsonl (50,000 records)
bpe:                    english_bpe_50k_claude_20260507.json (24K vocab + 5,944 CAS reserved = 29,944)
architecture:           d_model=512, encoder/head 6 layers/8 heads, batch_size=16
epochs:                 5 (completed)
total batches:          14,845
GPU:                    NVIDIA RTX A6000 (49,140 MiB), 67-72% util peak, 14GB VRAM peak
β-curriculum:           0.1 → 1.0 over first 10K steps, then constant at 1.0
sampling cadence:       every 500 steps (29 events total)
sample held-out record: index 0 — embodied-register job-offer-anxiety prompt
```

## Loss trajectory (curriculum-confounded)

```
step    500: 0.49   (β ≈ 0.14, LM loss weighted 14% of total)
step  2,500: 0.74
step  5,000: 0.99
step  7,500: 1.25
step 10,000: 1.53   (β = 1.0 reached)
step 12,500: 1.39
step 14,500: 1.35   (final)
```

**Reading**: Loss rose monotonically through the curriculum ramp (steps 0-10K) — mechanical from β increasing the LM-loss weight 10×. After β saturated at step 10K, loss drifted in 1.30-1.55 range — **some overfit + memorization, but small**. The full 50K corpus + 5 epochs gives ~5× exposure per record, modest by LM standards.

**Loss alone is NOT a reliable signal here** because of the curriculum schedule. The 5-layer eval principle is the right framing: loss says "training continued cleanly," sample quality says whether the checkpoint is keepable.

## Sample quality — the real signal

Held-out prompt (validation split, never in training):

> "Hi, sorry if this is a weird question to start with, but I guess I'm just not sure how to think about this — I have a job offer that seems really good on paper but it also feels kind of risky? Like my stomach is just in knots and I can't tell if that's fear or a warning sign or what."

CAS conditioning: `^9^O_{F3}|E` (Below/Effect Operational, F3 Vitality, Embodied register)

Target reply (from corpus):

> "That tight feeling in your stomach is worth paying attention to — your body is registering something real before your mind has caught up. It might help to notice whether the knot loosens when you picture yourself actually doing the work day-to-day, or stays clenched. Out of nowhere I thought of this: sometimes the gut is flagging the risk, but other times it's just the weight of a big physical life change like moving, new hours, new routines."

### Trajectory across epochs (last sample of each epoch)

**Epoch 0 (step 2,500, loss 0.74)**:
> "  goodwill finallybuilt    what  in leadsof for second  that somewhere ,"
*Function-word soup. No grammatical structure.*

**Epoch 2 (step 8,500, loss 1.47)**:
> "That tightening in your gut is real — your body is holding the weight of that tension in your chest before your mind has caught up. When something keeps pulling you back, that's worth paying attention to rather than brushing it away because it actually means something real in"
*Grammatical, coherent, prompt-relevant, register-grounded ("gut", "body holding weight"). Cut mid-word.*

**Epoch 4 (step 14,500, loss 1.35) — FINAL**:
> "That gut-drop feeling is your body saying this is so real — it's not just your thoughts. One thing leads to another and suddenly your muscles are replaying the old situation before your brain even catches up. Let it sit with that sensation; it's usually pointing at something real."
*Fluent. Embodied register stays grounded. Reflective rhythm matches corpus. Doesn't copy target. **Contains the canonical CO-8 colloquialism "One thing leads to another"** — consistent with ^9 below/effect arising from ^8 above/cause.*

### Quality gradient

- Epoch 0 → Epoch 2: massive jump (function-word soup → fluent grammatical)
- Epoch 2 → Epoch 4: refinement (more confident phrasing, better em dash rhythm, longer-form reasoning)
- Late samples are NOT memorizing the target — they produce different vocabulary and different sentence structure while staying register-grounded

## CAS silence (Layer 3) — PERFECT

Leakage scan across all 29 samples:

| Pattern | Hits |
|---|---|
| `CAS` | 0 |
| `noetic[s]?` | 0 |
| `domain[s]?` | 0 |
| `drive[s]?` | 0 |
| `register[s]?` | 0 |
| `^N` caret-state | 0 |
| `F1`-`F7` | 0 |

The trainer's CAS conditioning never leaks into the surface text. The model speaks naturally about cognitive states without naming them.

## Concerns — the two real defects

### 1. EOS never fires (29/29 capped at max_new_tokens=100)

```
EOS-terminated:           0 / 29
Hit max_new_tokens (100): 29 / 29
Tokens: mean=100.0  median=100  range=100-100
```

The model never decides to stop. Every reply hits the cap mid-thought. Some end with hanging prepositions ("rather than brushing it away because it actually means something real **in**"). This is the canonical "always-max-length" failure mode — model learned word patterns but not discourse-end signaling.

**Fix paths** (not in scope for this run, listed for B-3.5 / B-4 planning):
- Top-p (nucleus) sampling at inference — EOS often lives in the long tail that nucleus filters
- Length-aware loss weighting during training (penalize replies that go past target length)
- Training corpus EOS-density check — verify the SDG corpus reliably has EOS-marking patterns
- Beam search with length penalty at inference

### 2. CAS grounding (Layer 4) is unverified

All 29 samples come from `--sample-record-index 0` — same prompt, same register `|E`, every time. We've established the model CAN produce embodied-register replies. We have NOT established that:
- Different conditioning produces different style
- Register `|T` (Transcendent) produces meaning-orienting / abstract replies
- Register `|A` (Analytical) produces step-by-step reason-based replies
- Register `|f` (Affective) produces value-laden / feeling-toned replies
- The reply, fed back through K=9, predicts the conditioning state (round-trip grounding)

**This is the load-bearing test** for "CAS-Native vs LM with fancy corpus." It's a B-3.5 follow-on, not B-4 prerequisite, but no checkpoint should be promoted to production without it.

## Verdict

**Conditional GREENLIGHT for B-4 chat REPL wiring**, gated on:

1. **B-3.5: diverse-CAS sampling + round-trip K=9 grounding eval** (cheap, no GPU). Required before declaring this checkpoint usable. If round-trip ≥80% per axis → grounding works.
2. **EOS fix** in inference: run a top-p/temperature sweep with the existing
   `generate_reply(sampling="top_p")` path and use the best setting for B-4
   instead of pure temperature sampling. `top_p` support already exists; this
   is a checkpoint-behavior test, not a new sampler implementation.
3. **Document the curriculum-loss confound** so future trainers don't read "loss rose, training broke" — they should read "loss rose, β ramp expected, check sample quality."

**If B-3.5 grounding eval passes**: proceed to B-4 chat REPL wiring (K=9 classifier → generate_reply → two-stage inference).

**If B-3.5 grounding eval fails (mode collapse)**: **don't run more training**. Diagnose first. Possible fixes:
- Diverse held-out prompts during training (rotate through registers)
- Stronger conditioning signal (currently `cas_prefix_ids` is OFF due to PAD-leakage guard)
- Per-register reweighting in the loss

## Path B status post-B-3

| Item | State |
|---|---|
| B-1: 50K Tier 3 corpus | ✅ |
| B-2: NativeNLCollator + masked CE | ✅ |
| B-2.5: generate_reply helper | ✅ |
| B-2.6: Trainer sample_reply integration | ✅ |
| **B-3: First production-shape GPU training run** | ✅ — checkpoint at `b3_full_50k_prodshape_20260507/model_final.pt` (585MB) |
| **B-3.5: Diverse-CAS sampling + grounding eval** | **PENDING — load-bearing for B-4 promotion** |
| **B-3.5b: EOS settings sweep for `generate_reply`** | **PENDING — needed before B-4 user-facing chat** |
| B-4: Two-stage chat REPL | Blocked on B-3.5 |
| Path C: Simplex Δ°₃₉ | Parked POST v0 |

## Files

- Checkpoint: `/workspace/tksCAS/.../runs/b3_full_50k_prodshape_20260507/model_final.pt` (585 MB, on pod)
- Tokenizer: `tokenizer.json` (446KB) + `english_bpe.json` (1.5 MB) (in run dir, on pod)
- Manifest: `checkpoint_manifest.json` (3KB)
- Training events: `training_events.jsonl` (108KB, 29 sample events, 0 leakage)
- Launch log (with all 299 train_progress events + samples): `launch.log` (139KB)
- Local copies: `tmp/training_events.jsonl`, `tmp/b3_full_50k_launch.log`, `tmp/b3_full_50k_trajectory.md`

## Open questions for B-4 planning

1. Run B-3.5 grounding eval before EOS fix, or both in parallel?
2. If grounding round-trip ≥80%, is the truncation issue alone enough to block B-4? (probably yes — users seeing mid-word cutoffs is bad UX)
3. Once both are addressed, does B-4 wire K=9 → generate_reply directly, or add a thin orchestrator that handles "if K=9 confidence is low, ask user clarifying question"?
4. Should the v0 demo use `top_p` sampling, temperature-only sampling, or greedy
   decoding (deterministic but often less natural)?

End of report.
