# Candidate D — SSM Decoder Design (READY for sign-off)

**Date:** 2026-05-12
**Status:** DESIGN LOCKED. Four sign-off items decided by user 2026-05-12 (see "Locked decisions" section below). Authorized to proceed to Stage D code skeleton + CPU smoke. No pod spend until skeleton + smoke pass review.
**Scope:** Research-track. v0-rc1 remains canonical.

## Locked decisions (user 2026-05-12)

1. **SSM choice:** **Mamba (S6) + source cross-attention adapter** (Option 1). Source cross-attention is admissible because the failure mode is copying from source, not hiding source access. Mamba's selective state dynamics is the load-bearing hypothesis under test.
2. **Training schedule:** **D1/D2/D3 mirroring B1/B2/B3.** Same warm-start chain, same loss-weight presets, same anti-tuning rule. Keeps the comparison clean — only the decoder architecture varies; training schedule is held constant.
3. **Eval gate:** **Same broader B3 24-pack, same 7 locked gates, same pass criteria.** The bar B3 failed is the bar D must clear. Do not move the bar.
4. **`max_new_tokens` for Gate 6:** **Raise to 192 + re-run B3 baseline at 192.** The 128 cap creates a truncation confound on longer chains. Re-running B3 baseline at 192 makes Gate 6 fair. If B3 still recovers 0/37 at 192 (which is the main failure mode, not truncation-related), the D comparison remains clean.

## Single claim under test

> **Does an SSM decoder preserve source-grounded typed state across free decode on fresh records, where the transformer decoder (B3) failed?**

The narrower form: can the SSM, plugged into the existing simplex encoder + typed slot head + copy head, achieve ≥ 50% canonical identifier recovery on the broader B3 eval pack (zero training overlap), where B3 returned 0/37?

## Why SSM is the right test now (not earlier)

B1/B2/B3 exhausted the transformer-decoder side of the architectural review:

- **B1** (LM + FR only): transformer LM head stabilizes when joint pressure is removed at step 1. ✓
- **B2** (+ slot): slot head develops on stable LM and acquires real category selectivity. ✓ (holds on fresh records)
- **B3** (+ copy + hard routing): hard typed-fiber emission mechanism fires correctly when slot triggers, AND identifier reconstruction works on training-adjacent canaries. ✗ on fresh records.
- **Broader B3 eval**: 0/37 free-decode canonical recovery on fresh records vs 30% TF. **Exposure-bias signature.** Copy head fires but emits training-distribution-shaped tokens, not source-grounded copies.

The exposure-bias signature is the diagnostic Rule 1 your post-mortem decision standard already locked: TF clean + greedy bad → exposure bias is the right lever. Candidate C tested decode-side fix (hard routing). Candidate B tested training-schedule fix (staged). Both addressed the symptom; neither solved it for fresh records.

**CAS is fundamentally stateful.** Transformers maintain decode state via attention over previously-generated tokens — the exact path that drifts. SSMs maintain a continuous state evolving token-by-token, with built-in mechanisms (in Mamba's case, selective state updates) that can in principle implement typed-slot + copy semantics natively. Whether they actually do better on this task is the empirical question Candidate D answers.

## Architecture sketch

The simplex MVP architecture is already a stack of pluggable layers:
```
cas_expression → SimplexEncoder → (source_hidden, simplex_trajectory)
                                              ↓
                                       TypedFiberDecoder ← (current_token, cas_prefix)
                                              ↓
                                       (lm_head, slot_head, copy_head, phrase_bias)
                                              ↓
                                       next_token (via greedy_decode + optional hard routing)
```

The proposal: **replace `TypedFiberDecoder` (transformer) with `SsmTypedFiberDecoder` (SSM)** while keeping all other components — same simplex encoder, same loss heads, same training pipeline, same eval pack.

Three SSM design choices to commit on before build:

### Option 1 — Mamba (S6) with cross-attention adapter

- Mamba's selective state-space layer as the autoregressive backbone.
- Add a cross-attention adapter for source attention (so the copy head can attend to `cas_prefix_ids` from the encoder).
- Heads (LM, slot, copy) sit on top of the SSM hidden state, same as in TypedFiberDecoder.

**Why:** Mamba is the most-tested 2024+ SSM for language modeling. Its selectivity has empirical support for copy-style behavior. Cross-attention adapter is well-understood.

**Risks:** Mamba's CUDA kernels add deployment complexity. Cross-attention to source partially re-introduces the exposure-bias path.

### Option 2 — S4D + cross-attention

- Older diagonal SSM with cleaner FFT-based formulation.
- Same cross-attention adapter for source.

**Why:** Simpler, well-studied, more straightforward to debug than Mamba.

**Risks:** Less expressive than Mamba's selective updates; may not have enough capacity for copy supervision.

### Option 3 — RWKV-style (linear-attention) hybrid

- RWKV's time-mixing layer (linear attention with exponential decay).
- Source attention via Receptance/Key/Value pointer mechanism.

**Why:** Linear attention scales like SSMs but preserves an explicit attention-like source pointer — directly addresses "source-grounded copy" by construction.

**Risks:** Less standard for this scale; fewer reference implementations.

### My recommendation

**Option 1 (Mamba with cross-attention adapter)** as the first build. Strongest 2024+ language-modeling track record; the cross-attention adapter pattern is a clean addition that preserves the existing copy head's source attention semantics. Option 2 is the simpler fallback if Mamba kernels fight the existing toolchain.

**This is a recommendation, not a commitment.** Flag if you want a different option or want me to research a fourth.

## Training schedule

Carry forward the staged-training lesson from B1/B2 — they demonstrated staged training stabilizes LM head and slot state under joint pressure. The same insight should apply to SSM (an architectural switch doesn't change the gradient-conditioning issue that motivated staging).

Proposed stages:

| Stage | Loss weights | Warm-start | n_steps |
|---|---|---|---|
| D1 | lm=1, fr=1, all others 0 | none (fresh init) | 1000 |
| D2 | lm=1, fr=1, slot=1, copy=0, phrase=0 | D1 ckpt_final | 1000 |
| D3 | lm=1, fr=1, slot=1, copy=0.5, phrase=0.1 + `--hard-typed-emission` | D2 ckpt_final | 1000 |

Identical to B's schedule except the decoder is SSM, not transformer.

**Anti-tuning rule in force.** No varying lr / batch / weight decay across stages. Per-stage kill criteria applied at post-training canary. If D1 produces phrase loops or trivial output, kill D. If D2 collapses slot to CONNECTIVE on fresh records, kill D.

## Eval gate (LOCKED)

**The broader B3 eval pack (`cas-synthetic/data/eval/broader_b3_eval_pack_2026_05_12.jsonl`, 24 records, zero training overlap) is the validation standard for Candidate D.** Same 7 locked gates as B3's broader eval; same pass criteria.

This is the bar B3 failed (0/37 free-decode canonical recovery). For D to validate it must clear:

1. All-rpm recovery ≥ 50% (first bar) / ≥ 70% (strong)
2. hard_full > full on all-rpm
3. Non-rpm copy = 0
4. Non-rpm STAGE_VAR run < 3
5. No trivial outputs (n_tokens ≥ 50 AND text_len ≥ 100)
6. No catastrophic loops; ≤ 2 truncations. **`max_new_tokens = 192`** for both D eval and the B3 baseline re-run (decision 4 locked 2026-05-12). At 192 tokens, all rpm chain lengths in the broader B3 eval pack should fit without truncation.
7. D3 hard_full mean_severity ≤ B2 baseline + 0.10

If D validates: SSM is the production architecture target. Next stage is scale + extended training (with same broader-eval discipline).

If D falsifies on the same gates B3 failed: the gap is deeper than transformer-vs-SSM. Reopens architectural review at a more fundamental layer — possibly the copy supervision objective itself doesn't force source-grounded behavior, regardless of decoder architecture.

## Build plan

| # | Step | Where | Cost | Authorization | Description |
|---|---|---|---|---|---|
| 1 | SSM decoder module | laptop | $0 | **AUTHORIZED** | Add `SsmTypedFiberDecoder` (Mamba/S6 + source cross-attention adapter) mirroring `TypedFiberDecoder` API (same input/output shape, same heads). |
| 2 | CLI flag | laptop | $0 | **AUTHORIZED** | Add `--decoder-arch {transformer,ssm}` to trainer. Default unchanged (transformer). |
| 3 | `d1`/`d2`/`d3` ablation aliases | laptop | $0 | **AUTHORIZED** | Add explicit `d1`/`d2`/`d3` to `ABLATION_OVERRIDES` (aliases of `b1`/`b2`/`b3`) so the CLI history shows D-stage intent. |
| 4 | Unit tests | laptop | $0 | **AUTHORIZED** | SSM forward shape; staged-weight presets; warm-start round-trip; integration with existing collator/encoder. |
| 5 | CPU smoke run | laptop | $0 | **AUTHORIZED** | Tiny config, single batch, confirm pipeline end-to-end. Surfaces results for review before pod. |
| 6 | B3 baseline re-run @ 192 | pod | ~$0.10 | gated on user OK | Re-run broader B3 eval against existing B3 ckpt with `max_new_tokens=192`. Re-establishes apples-to-apples Gate 6 comparison for D. |
| 7 | D1 training | pod | ~$0.50 | gated on user OK | 1000 steps, `--ablation d1 --decoder-arch ssm`. |
| 8 | D1 kill criterion | local | $0 | n/a | Canary phrase loops / triviality check. |
| 9 | D2 training | pod | ~$0.50 | gated on user OK | `--ablation d2 --decoder-arch ssm --load-model-from D1_ckpt_final.pt`. |
| 10 | D2 kill criterion | local | $0 | n/a | Slot stability on canary + leakage check on broader pack sample. |
| 11 | D3 training + postmortem | pod | ~$0.55 | gated on user OK | `--ablation d3 --decoder-arch ssm --load-model-from D2_ckpt_final.pt --hard-typed-emission`. |
| 12 | Broader eval on D3 @ 192 | pod | ~$0.10 | gated on user OK | Run broader B3 eval runner against D3 ckpt with `max_new_tokens=192`. |
| 13 | Gate read | local | $0 | n/a | Apply 7 locked gates. Single yes/no verdict. |
| **D total** | | | **~$1.75** | | Includes B3 re-run @ 192 (~$0.10). |

Cumulative would reach ~$5.20 of $60 after D completes.

**Authorization pattern:** Steps 1–5 are local-only laptop work and pre-authorized by user 2026-05-12. Steps 6 onward involve pod spend and require explicit user OK before each, with the option to bundle authorizations after CPU smoke review.

## What this design does NOT do

- Does NOT modify B-trained checkpoints. They're frozen artifacts; D is built from scratch with fresh init at D1.
- Does NOT change the broader B3 eval pack. The pack is frozen; D is judged against the same fresh records B3 failed.
- Does NOT change the existing transformer decoder or any B-related code. The SSM decoder is an alternative, selectable via `--decoder-arch ssm`.
- Does NOT promote any D-trained checkpoint to production. v0-rc1 stays canonical.

## Sign-off — all four items decided

All four pre-build sign-off items have been decided by the user 2026-05-12. See "Locked decisions" section at top. Stage D code skeleton + CPU smoke are now authorized (steps 1–5 of the build plan). Pod work (steps 6+) is gated on review of the CPU smoke output.

## Companion files

- `docs/working/simplex_mvp_candidate_b3_findings_2026_05_12.md` — 11-canary B3 result (now superseded by broader-eval falsification).
- `docs/working/broader_b3_eval/broader_b3_eval_findings.md` — broader-eval result; the bar D must clear.
- `docs/working/simplex_mvp_staged_training_canonical_recipe_2026_05_12.md` — B staged-training recipe; D inherits the schedule structure.
- `docs/working/simplex_mvp_architecture_review_2026_05_11.md` — original 4-candidate review.
- Memory: `project_b3_broader_eval_falsified_2026_05_12.md`, `feedback_cas_best_lm_six_properties.md`.
