# Path B-1 — Gemini Flash-Lite blind-review verdict (2026-05-06)

**Bakeoff:** 500 records, gemini-2.5-flash-lite, $0.0296 cost, 100% validator pass.
**Reviewer:** Codex (verified by user; user separately ratified by directing the next bakeoff to Pro-preview, not Flash).
**Pack:** `tmp/gemini_bakeoff_blind_review_clean_20260506.md` (20 conversations: 10 Gemini + 10 Claude, shuffled, sealed answer key).

## Verdict

**Manual quality gate FAILED — distinguishable 20/20.**

Codex's classification (read before opening the answer key):
- Likely Gemini (weaker / shorter / more generic): conversations **2, 3, 4, 5, 7, 9, 14, 18, 19, 20**
- Likely Claude (stronger / fuller / more conversational): conversations **1, 6, 8, 10, 11, 12, 13, 15, 16, 17**

Match against answer key: **20/20 correct identification**. The reviewer could reliably tell which model produced which conversation purely from style — replies were not interchangeable.

This corroborates the pre-review surface-stat signal: Gemini Flash-Lite replies are ~51% the length of Claude's (192 vs 374 chars; 31 vs 63 words avg). Same sentence count, half the words per sentence. The conciseness reads as flatness in the corpus.

## Decision tree applied

Per the bakeoff report's pre-declared rules:

> - If A and B feel comparable → 50K Gemini ✗ (failed)
> - If Gemini reads consistently flatter → stay Claude for Tier 3 ✓ (this branch)
> - If mixed → extend bakeoff to 1500 records ✗ (no ambiguity to resolve)

**Acted-on decision: do NOT scale gemini-2.5-flash-lite to 50K for core Tier 3 dialogue.**

## What Flash-Lite is still good for

The cost story remains real. Flash-Lite's blind-review failure means it shouldn't be the source of training data the model learns to imitate — but it's still serviceable for:

- Cheap paraphrase drafts where the structured output is post-validated against a Claude-generated reply
- Synthetic variant generation that gets filtered later
- Anything where 51% length and a more generic register is acceptable or even desired

## Forward-track decision

Per user directive 2026-05-06 (saved to memory `feedback_gemini_default_model.md`): the next Gemini bakeoff defaults to **`gemini-3.1-pro-preview`** (not gemini-2.5-flash, despite Codex's recommendation).

Verified pricing from Google's official table at `https://ai.google.dev/gemini-api/docs/gemini-3`:

| Model | Input / Output per 1M | Notes |
|---|---|---|
| gemini-3.1-pro-preview | **$2 / $12** | ≤200k tokens (the regime dialogue generation lives in) |
| gemini-3.1-pro-preview | $4 / $18 | >200k tokens (irrelevant for SDG) |
| gemini-2.5-flash | $0.50 / $3 | Codex's recommendation, overridden |
| gemini-2.5-flash-lite | $0.10 / $0.40 | Failed this review |
| Claude Sonnet 4.6 | $3 / $15 | The quality bar |

Pro-preview at the standard tier is **33% cheaper than Claude on input, 20% cheaper on output**. The 98% savings story is dead, but Pro-preview is still meaningfully cheaper than Claude AND gets quality on par with the bar (validation pending the next bakeoff).

## Next concrete actions (NOT executed yet)

1. Add Pro-preview pricing constants to `cas-synthetic/scripts/tier3_providers.py` (default Gemini path uses Pro-preview when `--english-bpe-path` style flags are not overridden).
2. Run a 500-record gemini-3.1-pro-preview bakeoff at `--cost-cap 5` (estimated cost ~$0.80, generous headroom).
3. Apply the same automated gates + clean blind-review pack against the same Claude 5K corpus.
4. If Pro-preview passes blind review: scale to 50K Gemini Pro-preview at ~$80.
5. If Pro-preview also fails blind review: stay Claude for the 50K Tier 3 corpus (~$150).

Decision on (4) vs (5) waits on the manual blind review; do NOT auto-scale.

## What this changes

- The committed Flash-Lite bakeoff manifest (`60f42f6`) is now historical evidence, not a recommendation. Any future references to that bakeoff should cite this verdict alongside.
- The 500 Flash-Lite records on disk are unsuitable for training data ingestion for core Tier 3 (and have the wrong `source` field anyway from the d8e37d4 fix-prior bug). They can be deleted or kept as a Flash-Lite reference corpus for auxiliary work; either is fine.
- Path B-3 GPU training run remains blocked on B-1 reaching ≥10K records of acceptable quality. The Claude 5K corpus is the current floor; the next bakeoff (Pro-preview) determines whether Gemini can carry the rest.
- Path B-4 chat REPL wiring still waits on B-3.
- Path C simplex Δ°₃₉ remains parked.
