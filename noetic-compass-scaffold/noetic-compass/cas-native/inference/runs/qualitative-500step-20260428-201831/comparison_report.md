# Qualitative Assessment — 500-step v2 Causal Checkpoint

**Checkpoint**: `cas-native/training/runs/v2-fifth-full-20260428-194518/checkpoints/final.pt`
**Tokenizer**: HybridCASTokenizer v1, vocab=698 (15 special + 198 reserved + 485 word/CAS), hash `2339a510d298afed`
**Training config**: 500 steps · batch=32 · lr=1e-4 · warmup=500 · bf16 · `target_mode=cas_expression` · `causal_lm=True` · `production_warmup_steps=100`
**Pod**: RunPod RTX A6000 (49 GB VRAM)
**Wall-clock**: 30.8 min training + ~5 min sample generation
**Generation params**: temperature 0.7 · top-p 0.9 · max 96 new tokens · seed 42

## Headline (per the user's gradient framework)

**Real learning visible — capability emerging at level 2.5–3.** Compared to the smoke baseline (100 steps), this run shows measurable structural-token frequency gains, particularly in compositional operators (`×`, `|R`). The structured-valid count remains 0/30, but that is **not the load-bearing signal** — what matters is whether the model is internalizing CAS structure, and the token-frequency evidence says yes.

This run is **not** "no capability yet." It is "alphabet learned, grammar emerging, low-frequency tokens still below emission threshold."

## Per-token capability gradient

Aggregate counts across 30 generations (5 per bucket × 6 buckets):

| Token type | Smoke (100 steps) | This run (500 steps) | Per-sample | Status |
|---|---|---|---|---|
| Bare `^N` Noetic | ~28 | **28** | 0.93 | Level 2 ✓ stable |
| `\|R` register tag | ~7 | **22** | 0.73 | **3× growth** — Level 2.5 |
| `×` cross integration | ~5 | **32** | 1.07 | **6× growth** — Level 2.5 |
| `^N^D` state pair | ~0 | **4** | 0.13 | Level 3 weak emergence |
| `_{Fk}` drive subscript | 0 | **0** | 0.00 | NOT EMERGED |
| `Θ` recipe head | 0 | **0** | 0.00 | NOT EMERGED |
| `Ω` named emergent | 0 | **0** | 0.00 | NOT EMERGED |
| `*Cluster{` typed cluster | 0 | **0** | 0.00 | NOT EMERGED |

The "3× growth in `|R`" and "6× growth in `×`" are the strongest evidence of structured learning. The model has learned that `×` is not a literary multiplication symbol but a CAS structural element, and that `|R` register tags follow state-shape contexts.

## Bucket-level structured-valid: 0/30

| Bucket | loose-valid | structured-valid | observable structural tokens |
|---|---|---|---|
| v74_baseline | 2/5 | 0/5 | scattered `^N`, occasional `×` |
| v75_register | 1/5 | 0/5 | `|A`, `|T`, `|f` register tags appear; states absent |
| v77_rule_four | 5/5 | 0/5 | `^N^D` pairs (3 occurrences), `×`, `|R` — closest to structural form |
| v77_omega | 4/5 | 0/5 | `^N^D`, `×`, but no `Ω` token emitted |
| v76_production | 0/5 | 0/5 | most degraded; tokens scattered, no `Θ` head |
| meta_logic | 3/5 | 0/5 | `^N^D` pair appeared once; no cluster constructors |

`v77_rule_four` is the most-developed bucket — that's notable because Rule 4 expressions are the simplest compositional form (Noetic+Domain+register pairs joined by `×`), and the model has internalized the operator (`×`) and register (`|R`) parts even if it can't yet glue them into a closed expression.

## Loss dynamics summary (supporting evidence, not headline)

For consistency-check purposes only:

| Metric | step 0 | step 475 | Change |
|---|---|---|---|
| total | 21.7 | 77.3 (post-saturation) | curriculum-ramp shape |
| lm_loss | 7.317 | 3.896 | **−47%** |
| production_loss | 415 (baseline) | 62.6 | **−85%** |
| inversion_penalty | 2.92 | 0.003 | −99.9% |

`production_loss` collapsing from 400+ → 62 is the strongest training-side signal that the production head is internalizing recipe structure. But the lack of `Θ`/`Ω` emission at sampling time means this learning hasn't yet manifested as generation capability — the head's logit distribution presumably puts non-trivial mass on those tokens but not enough to clear top-p=0.9 at temperature 0.7.

Wall-clock: 1846s = 30.8 min for 500 steps = 3.69 s/step. Linear scaling: 1500 steps ≈ 92 min, 2000 steps ≈ 123 min.

## Why low-frequency tokens haven't emerged yet

The HybridCASTokenizer represents `Θ`, `Ω`, `Foundation_*`, and the cluster-constructor keywords as single dedicated tokens. In the training corpus, these appear at much lower frequency than `^N`, `|R`, `×`, so the LM's predicted-distribution mass on them is correspondingly lower. With 500 steps of training, the model's logit mass on these low-frequency structural tokens is still below what top-p=0.9 sampling will draw.

This is the classical "long-tail token under-emission" problem with sampling decoders on undertrained LMs. Two paths to address it:

1. **More steps.** Continued training shifts the predicted distribution toward the training distribution. Audit projection: 1500-2000 steps is when these tokens should clear the top-p threshold for the first time.
2. **Sampling change.** Greedy decoding (or temperature → 0) would force the highest-logit token, which after 500 steps might already include `Θ`/`Ω` in some bucket-specific contexts. Tradeoff: zero diversity, potentially same expression every time.

## Recommendation

**Run a 1500-2000 step continuation.** Same hyperparameters except step count. The structural-token frequency growth from smoke→500-step suggests we're on the right curve; another 3-4× of training should push the low-frequency structural tokens above the top-p threshold. Estimated wall-clock: ~2 hours, cost: ~$1.

Do NOT change the architecture, tokenizer, or v2 flag set. The current configuration is producing real learning at the rate the audit predicted; throwing more compute at the same setup is the right next move.

## Files in this run dir

- `samples.jsonl` — 30 generations with prompts, generated text, ground truth, compile attempts
- `bucket_summary.json` — per-bucket valid counts (loose + structured) and tokenizer metadata
- `comparison_report.md` — this file
