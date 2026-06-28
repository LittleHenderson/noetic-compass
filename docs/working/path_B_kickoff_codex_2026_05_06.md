# Path B Kickoff — Codex + Claude joint plan (2026-05-06)

User authorized 2026-05-06 morning: lock K=9 as classifier (already 93.2% canonical / 46.9% paraphrase), stop chasing further classifier band-aids, move to **path B = build the demoable conversational v0**, then post-v0 do **path C = simplex Δ°₃₉ rebuild**.

The class-weighted-loss smoke (PID 16433, run dir `v1_smoke_drive_class_weighted_loss_2026_05_06`) continues to completion — let it run, do not interrupt. Cron `2b0d8ee1` is monitoring at 30-min cadence. Whatever it produces is informational; the v0 path forward does not depend on it improving K=9.

## Goal of Path B

A demoable conversational model where: **user types English → CAS classifier predicts CAS state → native NL generator writes English reply grounded in that CAS → full trace surface walks back from output to inputs.**

Calendar: ~3-4 weeks if focused.

## Two parallel tracks (no dependency between them — fire both)

### Track B-1: Tier 3 multi-turn dialogue SDG (Codex-led, laptop / CPU)

**Why now:** generation training needs paired (user prompt, CAS state per turn, fluent reply) data at scale. We have the strategy doc (`docs/working/native_nl_sdg_strategy_2026_05_04.md`) and the seed generator (`cas-synthetic/scripts/generate_native_nl_sdg_v1.py`). Tier 1 + Tier 2 demographic+tonal data already on disk (~108K records). Tier 3 multi-turn dialogue is the gap.

**Output target:** 50,000-200,000 records of `{conversation_id, turn_index, prompt_text, cas_expression, reply_text, demographic_profile, tone, generator_model, generation_timestamp, schema_version, trace_id}`.

**Storage:** `cas-synthetic/data/native_nl/v1_dialogue_*.jsonl` (one shard per ~5K records to allow incremental progress).

**Constraints:**
- HARD COST CAP $500. Print running total every 1,000 records. Abort cleanly if estimate exceeds cap.
- Concurrency 5 parallel Claude API calls.
- Retries with exponential backoff on 429/529.
- Resume capability — if a shard exists, skip already-generated conversation_ids.
- API key from `noetic-compass-scaffold/noetic-compass/.env` `NC_ANTHROPIC_API_KEY` (NC prefix, strip quotes).
- Model: `claude-sonnet-4-6` preferred, fall back to `claude-3-5-sonnet-20241022` on 404.

**Quality guidelines for the prompts to Claude:**
- 3-7 turn conversations covering all 10 Noetics × 4 Domains × 7 Drives × 4 Registers across the corpus
- Each turn's `cas_expression` describes the user's cognitive state at that point
- Each `reply_text` is fluent natural English consistent with the CAS state at that turn (1-3 sentences typical, more for complex states)
- NO CAS jargon ever in `reply_text` — the model is supposed to generate fluent prose, not metaspeak
- Demographic + tonal axes varied per conversation
- Anti-drift annotations preserved: `^3` Negative is VISCERAL not analytical; `^8` Above/Cause is associative TRIGGERING not deductive

**Entry point script:** `cas-synthetic/scripts/generate_tier3_dialogue_v1.py` (new — modeled on existing `generate_native_nl_sdg_v1.py`). Codex builds.

**Pacing:** start with a 500-record proof shard. Validate quality manually. Then scale to 5K, 50K, 100K. Spread over 1-2 weeks.

### Track B-2: Batcher reconciliation (Claude-led, code only)

**Why:** existing `cas-native/training/train_native_nl_gen.py` emits batches as `{input_ids, target_ids}`. Real `NLGenerationHead.forward` (in `cas-native/model/nl_generation_head.py`) consumes `{decoder_input_ids, bottleneck_z, cas_prefix_ids, encoder_outputs, domain_mask, register_id}`. Today the training falls back to `_FallbackNLGenerationHead` which fakes a compatible signature for smoke. Real GPU runs need the bridge.

**Deliverables (Claude side):**
- New file `cas-native/training/datasets/native_nl_collator.py` — `NativeNLCollator` class that takes records, tokenizes via the extended HybridCASTokenizer, builds the 6-field input dict
- New helper `cas-native/training/masked_ce_loss.py` — masked cross-entropy that ignores prompt + CAS prefix positions, computes loss on reply tokens only
- Modify `cas-native/training/train_native_nl_gen.py` — replace `_records_to_batch` with `NativeNLCollator` for the real path; keep `_FallbackNLGenerationHead` for hermetic smoke
- Add a thin helper on `CASNativeModel` if needed: `encode(prompt_ids) → (encoder_outputs, pooled_hidden_state)` to feed the head's `bottleneck_z` + `encoder_outputs`

**Tests:**
- `cas-native/tests/training/test_native_nl_collator.py` — at least 8 tests covering tokenization correctness, masking correctness, register_id parsing from CAS expressions, domain_mask shape, BOS/EOS handling, empty-record edge cases.
- Smoke test running 1 step of real-model training on CPU (with TinyL... wait — NO foreign weights; smoke uses random-init NLGenerationHead with a tiny config, ~10K params, 4 records).

**Effort estimate:** ~half a day focused work. ~400 LOC + ~150 LOC tests.

**No GPU required.** All testable on CPU.

## Sequence

```
NOW → fire B-1 + B-2 in parallel
  ├─ B-1 produces dialogue corpus over 1-2 weeks (background)
  └─ B-2 produces working bridge in ~1 day, tested on CPU

WHEN B-1 has ≥10K records AND B-2 lands → smoke 1-epoch native gen training
  (proves end-to-end, no fluency expectation yet)

WHEN B-1 has 50K+ records → real native gen training run
  multi-day GPU, ~$50-150
  eval: CAS-grounding, fluency PPL, distinct-2 diversity

WHEN training produces a usable checkpoint → B-4 wire into chat REPL
  ~1 day code, classifier (K=9) + native gen head, two-stage inference

→ v0 conversational model SHIPS

POST-v0 → Path C: simplex Δ°₃₉ rebuild as v1 architecture
  multi-week, joint Codex+Claude effort
```

## Division of labor

| Track | Owner | Why |
|---|---|---|
| B-1 SDG generation script + Claude API runs | Codex | Codex has done Lever 3 paired SDG before; pattern matches |
| B-1 prompt quality + per-shard validation | Claude reviews | Stylistic + CAS-correctness review |
| B-2 collator + masked-CE + training script wiring | Claude | Code architecture, matches Claude's pattern from prior session |
| B-2 testing on pod | Codex | Pod operations |
| Monitoring class-weighted-loss smoke | Claude (cron `2b0d8ee1`) | Already running |
| B-3 GPU run launch + monitoring | Codex (pod ops) + Claude (decision criteria) | Joint |
| B-4 chat REPL wiring | Joint | Code touches both classifier + gen head |

## Hard rules carried forward (do not violate)

- NO foreign pretrained model weights. Random-init only on the generation side. Claude API for SDG data is fine; the trained model is fully ours.
- Object traceability mandatory on every artifact: id, created_at, schema_version, parent_ids, source, trace_id.
- Plain language always.
- Always git-fetch + read CHANGELOG before any expensive op.
- Always pass `--lr 0.001 --batch-size 128 --weight-decay 0.0001` explicitly for any full classifier retrain (the script's defaults are smoke defaults — see `feedback_always_restore_baseline_hparams_for_full_retrains.md`).
- For training scripts: `--train-log-every-steps N` always-prints batches 1, 5, 10 of epoch 0 + every N batches.
- PYTHONFAULTHANDLER=1 alone does NOT make SIGQUIT non-destructive — verify `faulthandler.register(signal.SIGQUIT, ...)` is called before any signal.

## What NOT to do

- Do NOT interrupt the class-weighted-loss smoke (PID 16433). Let it complete naturally.
- Do NOT propose another classifier band-aid. K=9 stays.
- Do NOT propose foreign pretrained models for the gen head.
- Do NOT do simplex redesign yet. After v0 ships.
- Do NOT generate Tier 1 templates again — `level3_canonical_dt_K4.jsonl` (77K records) is already on disk and is BETTER than templates.

## First concrete actions

**Codex (B-1):**
1. Read `docs/working/native_nl_sdg_strategy_2026_05_04.md` Tier 3 spec
2. Read existing `cas-synthetic/scripts/generate_native_nl_sdg_v1.py` for the pattern
3. Draft `cas-synthetic/scripts/generate_tier3_dialogue_v1.py`
4. Run a 500-record proof shard
5. Surface 5 sample conversations for Claude review before scaling

**Claude (B-2):**
1. Read current `train_native_nl_gen.py` + `nl_generation_head.py` + the existing `_FallbackNLGenerationHead`
2. Design `NativeNLCollator` interface — match what `forward_with_lm` actually expects
3. Write the collator + tests
4. Smoke test on CPU with synthetic records
5. Patch `train_native_nl_gen.py` to use real collator when `NLGenerationHead` is available, keep fallback for hermetic CPU smoke

Both fire now, no waiting for the other.

---

End of brief.
