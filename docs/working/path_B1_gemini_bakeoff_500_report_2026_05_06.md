# Path B-1 — Gemini bakeoff report (500 records, v2)

**Date:** 2026-05-06
**Provider tested:** Google Gemini 2.5 Flash-Lite via `google.generativeai` 0.8.5
**Bakeoff command:**
```
python cas-synthetic/scripts/generate_tier3_dialogue_v1.py \
  --provider gemini --primary-model gemini-2.5-flash-lite \
  --target-records 500 --records-per-shard 500 --concurrency 5 \
  --cost-cap 5 --seed 20260506 \
  --out-prefix cas-synthetic/data/native_nl/v1_dialogue_500_gemini_bakeoff_v2_20260506 \
  --manifest cas-synthetic/data/native_nl/v1_dialogue_500_gemini_bakeoff_v2_20260506_manifest.json
```

## Result summary

- **500 records, 95 conversations, $0.03 actual cost** (v2 — after both regression fixes)
- 1 failure (JSON parse) out of 101 API calls — essentially noise
- Run completed cleanly, no cost-cap hit, no abort

## Two regression fixes landed before v2

The first bakeoff run (v1, ~$1.05 reported) surfaced two bugs in the
provider abstraction. Both fixed in commit `89f7cff` before this v2 run:

1. **Validation-retry leaked Claude SDK call shape.** The
   lower-temperature retry block hardcoded `call_claude_dialogue` against
   `ctx.client`. For Gemini `ctx.client` is None (Gemini uses
   `client_factory`), so the retry raised
   `AttributeError("'NoneType' object has no attribute 'messages'")` and
   silently dropped 5 of 95 conversations. v2: branches on `ctx.provider`
   and routes through `call_dialogue` for both providers.
2. **Cost reporting used Claude pricing.** The seed `CostTracker` reads
   module-level `PRICE_PER_M_INPUT/OUTPUT = 3.00/15.00` constants. A
   Gemini run reported $1.05 against the actual ~$0.03 cost — a ~35×
   over-report at $0.10/$0.40 per 1M. Could have falsely tripped tight
   cost caps. v2: `ProviderCostTracker` parameterized on the active
   provider's per-1M rates.

Regression tests added in `test_tier3_providers.py` to pin both fixes.

## Automated acceptance gates — ALL PASS

| Gate | Required | Achieved | Result |
|---|---|---|---|
| Validator pass rate | ≥98% | 100.00% (500/500) | PASS |
| `CAS` leakage | 0 | 0 | PASS |
| `noetic` leakage | 0 | 0 | PASS |
| `domain` leakage | 0 | 0 | PASS |
| `drive` leakage | 0 | 0 | PASS |
| `register` leakage | 0 | 0 | PASS |
| `^N` caret-state notation leakage | 0 | 0 | PASS |
| `F1`-`F7` drive notation leakage | 0 | 0 | PASS |
| Schema drift (missing required fields) | 0 records | 0 records | PASS |
| Cost materially lower than Claude | <50% | 2% of Claude on 50K | PASS |

**Per-provider failure breakdown**

| Pattern | v1 (buggy) | v2 (fixed) |
|---|---|---|
| `retry_api:unexpected:AttributeError:'NoneType'…` | 5 | 0 |
| `turn_count_mismatch` | 2 | 0 |
| `json_parse:JSONDecodeError` | 1 | 1 |

## Cost frame at scale

```
Run size  | Claude          | Gemini Flash-Lite | Gemini + Batch API
500 rec   | ~$1.51          | $0.03             | $0.015
5K rec    | ~$15.10         | $0.30             | $0.15
50K rec   | ~$150.60        | $2.96             | $1.48
100K rec  | ~$301.20        | $5.92             | $2.96
```

Gemini at 50K saves **$147.64 (98% cheaper)** vs Claude. With Batch API,
saves **$149.12 (99% cheaper)**.

## SIGNAL — Gemini replies are materially shorter than Claude's

Surface statistics on `reply_text` length across the two corpora:

| Stat | Gemini Flash-Lite (500) | Claude Sonnet 4.6 (5K) |
|---|---|---|
| Mean characters | **191.8** | 373.5 |
| Median characters | 185 | 373 |
| Mean word count | **31.5** | 63.5 |
| Median word count | 31 | 63 |
| Mean sentences | 2.37 | 2.55 |
| Length range | 87–357 chars | 159–582 chars |

**Gemini reply length is 51% of Claude's reply length** — about half as
many words per reply, similar sentence count. Each Gemini sentence is
materially shorter than each Claude sentence.

**This is the only quality signal that can't be auto-resolved.** All
formal acceptance gates pass. The conciseness may be fine — Gemini
Flash-Lite is positioned as the cheaper, faster model and shorter
replies are consistent with that — or it may bias the training corpus
toward terse style, losing nuance the larger Claude model carries.

A blind manual review is required.

## Manual review file (must be done by user / Codex before 50K)

`tmp/gemini_bakeoff_blind_review_v2_20260506.md` contains 20 randomly
selected conversations: 10 Gemini + 10 Claude, mixed and shuffled.
Conversation labels (A=Gemini, B=Claude) are at the bottom of the file
in a "don't peek" answer key.

Review protocol:
1. Read all 20 conversations top-to-bottom.
2. For each, label A or B based on tone/style/quality without looking
   at the key.
3. Compare to the answer key.

Decision rules:
- **If A and B feel comparable** (replies grounded, conversational, on
  topic, the conciseness gap doesn't read as flatness): **GO 50K Gemini**.
- **If Gemini reads consistently flatter, more generic, or evasive**:
  **STAY Claude** for Tier 3 50K. Gemini can still be used for cheaper
  auxiliary tasks (e.g., paraphrase generation against a Claude-generated
  reply) where length doesn't load-bear.
- **If mixed**: **NEEDS LARGER REVIEW** — extend bakeoff to 1500 records
  with an unbiased reviewer not aware of the cost-savings incentive.

## Recommendation pending manual review

If the manual review passes:

```
python cas-synthetic/scripts/generate_tier3_dialogue_v1.py \
  --provider gemini --primary-model gemini-2.5-flash-lite \
  --target-records 50000 --records-per-shard 5000 --concurrency 5 \
  --cost-cap 10 --seed 20260506 \
  --out-prefix cas-synthetic/data/native_nl/v1_dialogue_50k_gemini_20260506 \
  --manifest cas-synthetic/data/native_nl/v1_dialogue_50k_gemini_20260506_manifest.json
```

Expected: ~$3 actual cost (cap of $10 leaves 3.3× headroom). Wall-clock
estimate at concurrency=5 and ~95 conversations per 500 records:
~10× the bakeoff time, so 30-90 minutes depending on Gemini's response
latency.

Do **NOT** kick off 50K without explicit user approval. The 99% cost
savings is real, but the corpus is feeding B-3 GPU training that
amortizes much higher GPU cost than the SDG savings; corpus quality
matters more than corpus cost.

## What did NOT change in this commit

- The Claude 5K corpus committed in `478eb3b` remains the known-good
  seed and is unaffected.
- B-2 trainer wiring (`62f0299`) is unchanged.
- B-3 still requires Path B-1 to reach ≥10K records (whichever provider).
- Path C simplex Δ°₃₉ remains parked.
